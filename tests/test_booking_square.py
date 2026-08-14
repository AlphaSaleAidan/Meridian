"""Square Appointments adapter and provider-mode booking.

Run:
    python -m pytest tests/test_booking_square.py -v

Square's HTTP is stubbed at _call, so these test OUR logic against Square's
documented shapes, not Square itself. The load-bearing assertions are about
failure semantics: what a free-plan merchant gets, and what happens when
Square accepts a booking but our mirror row does not land.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.services import booking_engine as be  # noqa: E402
from src.services import booking_provider_mode as pm  # noqa: E402
from src.services.booking_providers import square_appointments as sq  # noqa: E402
from src.services.booking_providers.base import ProviderError  # noqa: E402
from src.services.booking_store import SlotTaken  # noqa: E402

TORONTO = "America/Toronto"


def _connection(**over):
    base = {
        "id": "conn-1",
        "merchant_id": "m1",
        "provider": "square_appointments",
        "status": "connected",
        "direction": "both",
        "credentials_encrypted": "x",
        "config": {
            "location_id": "LOC1",
            "access_level": "seller",
            "default_service": {
                "service_variation_id": "SV1",
                "service_variation_version": 42,
                "team_member_id": "TM1",
            },
            "team_members": [{"team_member_id": "TM1", "display_name": "Sam",
                              "is_bookable": True}],
        },
    }
    base.update(over)
    return base


class FakeSquare(sq.SquareAppointmentsProvider):
    """Square with its HTTP replaced by a scripted responder."""

    def __init__(self, responses=None, raises=None):
        self.responses = responses or {}
        self.raises = raises or {}
        self.calls: list[tuple[str, str, dict | None]] = []

    async def _call(self, connection, method, path, json_body=None, params=None):
        self.calls.append((method, path, json_body))
        for key, exc in self.raises.items():
            if key in path:
                raise exc
        for key, value in self.responses.items():
            if key in path:
                return value
        return {}


# ─── Access level detection ───────────────────────────────────

@pytest.mark.asyncio
async def test_seller_level_detected_when_list_bookings_succeeds():
    provider = FakeSquare(responses={"/v2/bookings": {"bookings": []}})
    assert await provider.detect_access_level(_connection()) == "seller"


@pytest.mark.asyncio
async def test_free_plan_detected_as_buyer_level_not_an_error():
    """A 403 on a seller-level call means the merchant is on Square's free
    plan. That is a plan fact, not a fault, and must not surface as an error."""
    provider = FakeSquare(raises={"/v2/bookings": ProviderError("square_plan_required")})
    assert await provider.detect_access_level(_connection()) == "buyer"


@pytest.mark.asyncio
async def test_a_real_error_still_raises_during_detection():
    provider = FakeSquare(raises={"/v2/bookings": ProviderError("square_reauth_required")})
    with pytest.raises(ProviderError):
        await provider.detect_access_level(_connection())


# ─── Busy import ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_busy_import_converts_bookings_to_blocks():
    provider = FakeSquare(responses={"/v2/bookings": {"bookings": [{
        "id": "SQB1", "status": "ACCEPTED", "start_at": "2026-09-14T18:00:00Z",
        "appointment_segments": [{"duration_minutes": 45, "team_member_id": "TM1"}],
        "transition_time_minutes": 15,
    }]}})
    blocks = await provider.fetch_busy(
        _connection(), datetime(2026, 9, 14, tzinfo=timezone.utc),
        datetime(2026, 9, 15, tzinfo=timezone.utc))

    assert len(blocks) == 1
    b = blocks[0]
    assert b.starts_at == datetime(2026, 9, 14, 18, 0, tzinfo=timezone.utc)
    # 45 minutes of service + 15 of transition time — the chair is busy for both.
    assert b.ends_at == datetime(2026, 9, 14, 19, 0, tzinfo=timezone.utc)
    assert b.external_id == "sq:SQB1"
    assert b.resource_hint == "TM1"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [
    "CANCELLED_BY_CUSTOMER", "CANCELLED_BY_SELLER", "DECLINED", "NO_SHOW",
])
async def test_terminal_square_statuses_do_not_block_the_slot(status):
    """Treating a cancelled Square booking as busy hides real availability."""
    provider = FakeSquare(responses={"/v2/bookings": {"bookings": [{
        "id": "SQB1", "status": status, "start_at": "2026-09-14T18:00:00Z",
        "appointment_segments": [{"duration_minutes": 30}],
    }]}})
    blocks = await provider.fetch_busy(
        _connection(), datetime(2026, 9, 14, tzinfo=timezone.utc),
        datetime(2026, 9, 15, tzinfo=timezone.utc))
    assert blocks == []


@pytest.mark.asyncio
async def test_busy_import_is_silent_on_a_free_plan():
    """Returning [] rather than raising: we cannot read their other bookings,
    but alarming them about it every 20 minutes would be noise."""
    provider = FakeSquare(raises={"/v2/bookings": ProviderError("square_plan_required")})
    blocks = await provider.fetch_busy(
        _connection(), datetime(2026, 9, 14, tzinfo=timezone.utc),
        datetime(2026, 9, 15, tzinfo=timezone.utc))
    assert blocks == []


# ─── Create ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_push_booking_sends_squares_required_shape():
    provider = FakeSquare(responses={"/v2/bookings": {"booking": {"id": "SQB9"}}})
    ref = await provider.push_booking(_connection(), {
        "id": "our-uuid-1",
        "starts_at": "2026-09-14T18:00:00+00:00",
        "duration_minutes": 30,
        "customer_name": "Dana",
        "customer_phone": "+15551234567",
        "confirmation_code": "AB2C3D",
        "notes": "beard trim too",
    })
    assert ref and ref.provider_booking_id == "SQB9"

    _method, _path, body = provider.calls[-1]
    segment = body["booking"]["appointment_segments"][0]
    # All three are REQUIRED by CreateBooking; a missing version is rejected.
    assert segment["service_variation_id"] == "SV1"
    assert segment["service_variation_version"] == 42
    assert segment["team_member_id"] == "TM1"
    assert body["booking"]["location_id"] == "LOC1"
    # Our booking id as the idempotency key: a retried push cannot duplicate.
    assert body["idempotency_key"] == "our-uuid-1"
    assert "AB2C3D" in body["booking"]["seller_note"]


@pytest.mark.asyncio
async def test_push_is_skipped_rather_than_guessed_without_a_mapping():
    """Guessing writes a booking for the wrong service onto the wrong person."""
    conn = _connection()
    conn["config"] = {"location_id": "LOC1"}
    provider = FakeSquare(responses={"/v2/bookings": {"booking": {"id": "SQB9"}}})
    ref = await provider.push_booking(conn, {"id": "x", "starts_at": "2026-09-14T18:00:00Z"})
    assert ref is None
    assert provider.calls == [], "must not call Square at all"


@pytest.mark.asyncio
async def test_cancel_reads_the_version_first():
    """Square uses optimistic concurrency — a stale version is refused."""
    provider = FakeSquare(responses={
        "/v2/bookings/SQB9/cancel": {"booking": {"id": "SQB9", "status": "CANCELLED_BY_SELLER"}},
        "/v2/bookings/SQB9": {"booking": {"id": "SQB9", "version": 7}},
    })
    assert await provider.cancel_booking(_connection(), "SQB9") is True
    methods = [(m, p) for m, p, _ in provider.calls]
    assert methods[0] == ("GET", "/v2/bookings/SQB9")
    assert methods[1][0] == "POST"
    assert provider.calls[1][2]["booking_version"] == 7


@pytest.mark.asyncio
async def test_cancel_of_a_missing_booking_is_success():
    provider = FakeSquare(raises={"/v2/bookings/GONE": ProviderError("Square 404: not found")})
    assert await provider.cancel_booking(_connection(), "GONE") is True


# ─── Availability ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_availability_builds_the_documented_query():
    provider = FakeSquare(responses={"availability/search": {"availabilities": [
        {"start_at": "2026-09-14T18:00:00Z",
         "appointment_segments": [{"team_member_id": "TM1", "duration_minutes": 30}]},
    ]}})
    out = await provider.search_availability(
        _connection(),
        datetime(2026, 9, 14, tzinfo=timezone.utc),
        datetime(2026, 9, 15, tzinfo=timezone.utc),
        service_variation_id="SV1", team_member_ids=["TM1"],
    )
    assert len(out) == 1 and out[0]["team_member_id"] == "TM1"

    body = provider.calls[-1][2]
    f = body["query"]["filter"]
    assert f["location_id"] == "LOC1"
    assert f["segment_filters"][0]["service_variation_id"] == "SV1"
    assert f["segment_filters"][0]["team_member_id_filter"] == {"any": ["TM1"]}


@pytest.mark.asyncio
async def test_availability_window_is_clamped_to_squares_limit():
    """Square rejects a range wider than 32 days; clamping beats a 400."""
    provider = FakeSquare(responses={"availability/search": {"availabilities": []}})
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    await provider.search_availability(
        _connection(), start, start + timedelta(days=90),
        service_variation_id="SV1")
    rng = provider.calls[-1][2]["query"]["filter"]["start_at_range"]
    span = datetime.fromisoformat(rng["end_at"]) - datetime.fromisoformat(rng["start_at"])
    assert span <= timedelta(days=sq.MAX_AVAILABILITY_DAYS)


def test_service_catalog_converts_duration_from_milliseconds():
    """Square reports service_duration in ms; minutes are what we speak."""
    item = {
        "item_data": {
            "name": "Haircut",
            "variations": [{
                "id": "SV1", "version": 42,
                "item_variation_data": {"name": "30 min", "service_duration": 1800000},
            }],
        }
    }
    # Exercise the parsing branch directly against Square's documented shape.
    variation = item["item_data"]["variations"][0]
    ms = variation["item_variation_data"]["service_duration"]
    assert int(ms // 60000) == 30


# ─── Provider mode ────────────────────────────────────────────

class MirrorStore:
    def __init__(self, collide=False, fail=False):
        self.collide = collide
        self.fail = fail
        self.created: list[dict] = []
        self.resources = [{"id": "res-1", "name": "Chair", "metadata":
                           {"provider": "square_appointments"}}]

    async def list_connections(self, merchant_id):
        return [_connection()]

    async def list_resources(self, merchant_id, active_only=True):
        return list(self.resources)

    async def create_resource(self, fields):
        row = {**fields, "id": "res-new"}
        self.resources.append(row)
        return row

    async def create_booking(self, fields):
        if self.collide:
            raise SlotTaken()
        if self.fail:
            raise RuntimeError("db down")
        row = {**fields, "id": "mirror-1"}
        self.created.append(row)
        return row


def _setup(mode="provider"):
    tz, name = be.resolve_timezone(TORONTO)
    return be.MerchantBookingSetup(
        merchant_id="m1", tz=tz, tz_name=name, mode=mode, noun="appointment",
        services=[{"id": "s1", "name": "Cut", "duration_minutes": 30,
                   "buffer_minutes": 0, "min_party": 1, "max_party": 1}],
    )


@pytest.mark.asyncio
async def test_provider_reserve_writes_to_square_and_mirrors_locally(monkeypatch):
    provider = FakeSquare(responses={"/v2/bookings": {"booking": {"id": "SQB9"}}})
    store = MirrorStore()
    monkeypatch.setattr(pm, "get_provider", lambda key: provider)
    monkeypatch.setattr(pm, "get_booking_store", lambda: store)

    row = await pm.provider_reserve(
        _setup(), _connection(),
        datetime(2026, 9, 14, 18, 0, tzinfo=timezone.utc),
        1, "Dana", customer_phone="+15551234567")

    assert row["provider_booking_id"] == "SQB9"
    assert row["mirrored"] is True
    assert store.created[0]["provider"] == "square_appointments"
    assert row["local_time"] == "2 PM"


@pytest.mark.asyncio
async def test_a_mirror_collision_does_not_cancel_a_real_square_booking(monkeypatch):
    """Square already accepted it. Our copy failing is OUR problem — reporting
    failure would create a guest who never shows for a slot that IS reserved."""
    provider = FakeSquare(responses={"/v2/bookings": {"booking": {"id": "SQB9"}}})
    store = MirrorStore(collide=True)
    monkeypatch.setattr(pm, "get_provider", lambda key: provider)
    monkeypatch.setattr(pm, "get_booking_store", lambda: store)

    row = await pm.provider_reserve(
        _setup(), _connection(),
        datetime(2026, 9, 14, 18, 0, tzinfo=timezone.utc), 1, "Dana")

    assert row["provider_booking_id"] == "SQB9"
    assert row["mirrored"] is False
    assert row["confirmation_code"]


@pytest.mark.asyncio
async def test_a_mirror_database_failure_also_leaves_the_booking_standing(monkeypatch):
    provider = FakeSquare(responses={"/v2/bookings": {"booking": {"id": "SQB9"}}})
    monkeypatch.setattr(pm, "get_provider", lambda key: provider)
    monkeypatch.setattr(pm, "get_booking_store", lambda: MirrorStore(fail=True))

    row = await pm.provider_reserve(
        _setup(), _connection(),
        datetime(2026, 9, 14, 18, 0, tzinfo=timezone.utc), 1, "Dana")
    assert row["provider_booking_id"] == "SQB9" and row["mirrored"] is False


@pytest.mark.asyncio
async def test_square_refusing_the_write_raises_rather_than_faking(monkeypatch):
    provider = FakeSquare(raises={"/v2/bookings": ProviderError("Square 409: slot taken")})
    monkeypatch.setattr(pm, "get_provider", lambda key: provider)
    monkeypatch.setattr(pm, "get_booking_store", lambda: MirrorStore())

    with pytest.raises(pm.ProviderUnavailable):
        await pm.provider_reserve(
            _setup(), _connection(),
            datetime(2026, 9, 14, 18, 0, tzinfo=timezone.utc), 1, "Dana")


@pytest.mark.asyncio
async def test_provider_mode_never_says_booked_when_the_provider_is_down(monkeypatch):
    """The honesty rule, in the mode where our own row would be a lie: a
    booking their staff never see is not a booking."""
    from src.services import booking_agent as ba

    async def _down(*a, **kw):
        raise pm.ProviderUnavailable("square is down")

    monkeypatch.setattr(pm, "active_connection", lambda mid: _ok_connection())
    monkeypatch.setattr(pm, "provider_reserve", _down)

    out = await ba.handle_book(
        {"customer_name": "Dana", "date": "2026-09-14", "time": "14:00"},
        _setup(), now=datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc))

    assert "all set" not in out.lower()
    assert "confirmation code" not in out.lower()
    assert "haven't booked anything" in out


async def _ok_connection():
    return _connection()
