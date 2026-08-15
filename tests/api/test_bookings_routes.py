"""Bookings API routes — auth, tenancy, validation and the 409 contract.

Run: python -m pytest tests/api/test_bookings_routes.py -v

The heart of this file is the tenancy assertions. A booking row carries a
customer's name and phone number, and every sub-resource route takes that
row's uuid straight from the URL — which is a textbook BOLA unless the handler
resolves the OWNING merchant from the row first and authorizes against that.
These tests fail if anyone ever removes that step.

The other load-bearing assertion is that a double-book collision surfaces as
HTTP 409 and not as a 500. The portal distinguishes them: 409 means "pick
another time", 500 means "something is broken". Collapsing the two would make
the host stand's add-a-walk-in flow lie about which one happened.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

import src.api.routes.bookings as br  # noqa: E402
from src.api.auth import require_service_auth  # noqa: E402
from src.services.booking_store import SlotTaken  # noqa: E402

MERCHANT = "biz_abc123"
OTHER_MERCHANT = "biz_someone_else"
RESOURCE = "11111111-1111-1111-1111-111111111111"
SERVICE = "22222222-2222-2222-2222-222222222222"
BOOKING = "33333333-3333-3333-3333-333333333333"


class StubDB:
    """Only the reads the router itself performs (tenancy + config lookup)."""

    async def update(self, table, fields, filters):
        return []

    async def select(self, table, columns="*", filters=None, order=None,
                     limit=None, offset=None):
        f = filters or {}
        if table == "phone_agent_config":
            return [{"business_timezone": "America/Toronto",
                     "booking_noun": "table", "booking_mode": "native"}]
        if table == "bookings" and f.get("id") == f"eq.{BOOKING}":
            return [{"id": BOOKING, "merchant_id": MERCHANT}]
        if table == "booking_resources" and f.get("id") == f"eq.{RESOURCE}":
            return [{"id": RESOURCE, "merchant_id": MERCHANT}]
        if table == "booking_services" and f.get("id") == f"eq.{SERVICE}":
            return [{"id": SERVICE, "merchant_id": MERCHANT}]
        return []


class StubStore:
    def __init__(self):
        self.created: list[dict] = []
        self.updates: list[tuple[str, dict]] = []
        self.raise_on_update: Exception | None = None

    async def list_resources(self, merchant_id, active_only=True):
        return [{"id": RESOURCE, "merchant_id": merchant_id, "name": "T1",
                 "kind": "table", "seats": 4, "sort_order": 0, "active": True}]

    async def create_resource(self, fields):
        self.created.append(fields)
        return {**fields, "id": RESOURCE}

    async def update_resource(self, rid, fields):
        self.updates.append((rid, fields))
        return {"id": rid, **fields}

    async def list_services(self, merchant_id, active_only=True):
        return [{"id": SERVICE, "merchant_id": merchant_id, "name": "Dinner",
                 "duration_minutes": 90, "buffer_minutes": 0,
                 "min_party": 1, "max_party": 8}]

    async def create_service(self, fields):
        self.created.append(fields)
        return {**fields, "id": SERVICE}

    async def update_service(self, sid, fields):
        self.updates.append((sid, fields))
        return {"id": sid, **fields}

    async def list_hours(self, merchant_id):
        return [{"weekday": 1, "opens_at": "17:00:00", "closes_at": "22:00:00",
                 "slot_minutes": 15}]

    async def replace_hours(self, merchant_id, rows):
        self.created.append({"hours": rows})
        return rows

    async def list_pacing_rules(self, merchant_id):
        return []

    async def list_closures(self, *a, **kw):
        return []

    async def list_busy_blocks(self, *a, **kw):
        return []

    async def list_bookings(self, *a, **kw):
        return [{"id": BOOKING, "merchant_id": MERCHANT, "starts_at":
                 "2026-09-14T23:00:00+00:00", "ends_at": "2026-09-15T00:30:00+00:00",
                 "customer_name": "Dana", "party_size": 2, "status": "confirmed",
                 "confirmation_code": "AB2C3D", "resource_id": RESOURCE}]

    async def get_booking(self, booking_id):
        return {"id": booking_id, "merchant_id": MERCHANT,
                "starts_at": "2026-09-14T23:00:00+00:00",
                "ends_at": "2026-09-15T00:30:00+00:00", "duration_minutes": 90}

    async def update_booking(self, booking_id, fields):
        if self.raise_on_update:
            raise self.raise_on_update
        self.updates.append((booking_id, fields))
        return {"id": booking_id, **fields}

    async def create_booking(self, fields):
        self.created.append(fields)
        return {**fields, "id": BOOKING}

    async def list_connections(self, merchant_id):
        return []


@pytest.fixture
def client(monkeypatch):
    store = StubStore()
    monkeypatch.setattr(br, "get_db", lambda: StubDB())
    monkeypatch.setattr(br, "get_booking_store", lambda: store)
    import src.services.booking_engine as be
    monkeypatch.setattr(be, "get_booking_store", lambda: store)

    app = FastAPI()
    app.include_router(br.router)
    app.dependency_overrides[require_service_auth] = lambda: {"kind": "admin"}

    c = TestClient(app)
    c.store = store  # type: ignore[attr-defined]
    return c


# ─── Tenancy: the BOLA guards ─────────────────────────────────

def test_every_merchant_scoped_read_enforces_membership(client, monkeypatch):
    seen: list[str] = []

    async def _record(principal, merchant_id):
        seen.append(merchant_id)

    monkeypatch.setattr(br, "enforce_service_member", _record)

    client.get(f"/api/bookings/resources/{MERCHANT}")
    client.get(f"/api/bookings/services/{MERCHANT}")
    client.get(f"/api/bookings/hours/{MERCHANT}")
    client.get(f"/api/bookings/list/{MERCHANT}",
               params={"start": "2026-09-14T00:00:00Z", "end": "2026-09-15T00:00:00Z"})
    client.get(f"/api/bookings/availability/{MERCHANT}", params={"day": "2026-09-14"})

    assert seen == [MERCHANT] * 5


def test_sub_resource_routes_authorize_against_the_rows_owner(client, monkeypatch):
    """A booking id in the URL is a BOLA unless the owning merchant is
    resolved from the row FIRST. This asserts that resolution happens."""
    seen: list[str] = []

    async def _record(principal, merchant_id):
        seen.append(merchant_id)

    monkeypatch.setattr(br, "enforce_service_member", _record)

    client.patch(f"/api/bookings/resources/{RESOURCE}", json={"name": "T2"})
    client.patch(f"/api/bookings/services/{SERVICE}", json={"name": "Lunch"})
    client.patch(f"/api/bookings/{BOOKING}", json={"status": "seated"})
    client.get(f"/api/bookings/detail/{BOOKING}")

    # Every one resolved MERCHANT from the row rather than trusting the URL.
    assert seen == [MERCHANT] * 4


def test_membership_denial_blocks_the_request(client, monkeypatch):
    from fastapi import HTTPException

    async def _deny(principal, merchant_id):
        raise HTTPException(403, "not your merchant")

    monkeypatch.setattr(br, "enforce_service_member", _deny)
    r = client.get(f"/api/bookings/resources/{OTHER_MERCHANT}")
    assert r.status_code == 403


# ─── Validation ───────────────────────────────────────────────

@pytest.mark.parametrize("bad", ["../etc/passwd", "a b", "x" * 65, "drop;table"])
def test_malformed_merchant_ids_are_rejected(client, monkeypatch, bad):
    monkeypatch.setattr(br, "enforce_service_member",
                        lambda *a, **kw: _noop())
    r = client.get(f"/api/bookings/resources/{bad}")
    assert r.status_code in (400, 404)


async def _noop():
    return None


def test_non_uuid_sub_resource_id_is_rejected(client, monkeypatch):
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.patch("/api/bookings/resources/not-a-uuid", json={"name": "x"})
    assert r.status_code == 400


def test_unknown_resource_kind_is_rejected(client, monkeypatch):
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.post("/api/bookings/resources", json={
        "merchant_id": MERCHANT, "name": "Thing", "kind": "spaceship", "seats": 2})
    assert r.status_code == 422


def test_unknown_booking_status_is_rejected(client, monkeypatch):
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.patch(f"/api/bookings/{BOOKING}", json={"status": "vibing"})
    assert r.status_code == 422


def test_closing_before_opening_is_rejected_with_the_overnight_hint(client, monkeypatch):
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.put("/api/bookings/hours", json={
        "merchant_id": MERCHANT,
        "rows": [{"weekday": 5, "opens_at": "17:00", "closes_at": "02:00",
                  "slot_minutes": 30}],
    })
    assert r.status_code == 400
    # The merchant needs to know WHAT to do, not just that it failed.
    assert "midnight" in r.json()["detail"].lower()


def test_max_party_below_min_party_is_rejected(client, monkeypatch):
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.post("/api/bookings/services", json={
        "merchant_id": MERCHANT, "name": "Odd", "duration_minutes": 60,
        "min_party": 8, "max_party": 2})
    assert r.status_code == 400


def test_hours_are_saved_as_a_whole_week(client, monkeypatch):
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.put("/api/bookings/hours", json={
        "merchant_id": MERCHANT,
        "rows": [{"weekday": d, "opens_at": "09:00", "closes_at": "17:00",
                  "slot_minutes": 30} for d in range(3)],
    })
    assert r.status_code == 200
    assert r.json()["total"] == 3


# ─── The 409 contract ─────────────────────────────────────────

def test_a_collision_on_reschedule_is_409_not_500(client, monkeypatch):
    """The portal shows a different message for each. Collapsing them makes
    the add-a-walk-in flow lie about what happened."""
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    client.store.raise_on_update = SlotTaken()
    r = client.patch(f"/api/bookings/{BOOKING}",
                     json={"starts_at": "2026-09-14T23:30:00Z"})
    assert r.status_code == 409
    assert "taken" in r.json()["detail"].lower()


def test_moving_a_booking_moves_its_end_time_too(client, monkeypatch):
    """Patching only starts_at would leave the old end and silently overlap
    whatever follows."""
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.patch(f"/api/bookings/{BOOKING}",
                     json={"starts_at": "2026-09-15T01:00:00Z"})
    assert r.status_code == 200
    _bid, fields = client.store.updates[-1]
    assert "starts_at" in fields and "ends_at" in fields
    start = datetime.fromisoformat(fields["starts_at"])
    end = datetime.fromisoformat(fields["ends_at"])
    # The original booking was 90 minutes long; the move must preserve that.
    assert (end - start).total_seconds() == 90 * 60


def test_cancelling_stamps_the_cancellation_time(client, monkeypatch):
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.patch(f"/api/bookings/{BOOKING}", json={"status": "cancelled"})
    assert r.status_code == 200
    _bid, fields = client.store.updates[-1]
    assert fields["status"] == "cancelled" and fields.get("cancelled_at")


def test_empty_patch_is_rejected_rather_than_silently_doing_nothing(client, monkeypatch):
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.patch(f"/api/bookings/{BOOKING}", json={})
    assert r.status_code == 400


# ─── Availability + create ────────────────────────────────────

def test_availability_reports_the_merchants_timezone(client, monkeypatch):
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.get(f"/api/bookings/availability/{MERCHANT}",
                   params={"day": "2026-09-15", "party_size": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["timezone"] == "America/Toronto"
    assert body["day"] == "2026-09-15"
    for slot in body["slots"]:
        assert slot["local_label"] and slot["resource_id"]


def test_portal_created_booking_is_sourced_correctly(client, monkeypatch):
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.post("/api/bookings/create", json={
        "merchant_id": MERCHANT,
        "starts_at": "2026-09-15T22:00:00Z",
        "party_size": 2, "customer_name": "Walk In",
        "source": "walk_in",
    })
    assert r.status_code == 200
    assert client.store.created[-1]["source"] == "walk_in"


def test_a_bogus_source_falls_back_rather_than_being_stored(client, monkeypatch):
    """source is CHECK-constrained in the schema; an unknown value would be a
    500 at insert time instead of a 400 here."""
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.post("/api/bookings/create", json={
        "merchant_id": MERCHANT, "starts_at": "2026-09-15T22:00:00Z",
        "party_size": 2, "customer_name": "X", "source": "carrier_pigeon",
    })
    assert r.status_code == 200
    assert client.store.created[-1]["source"] == "portal"


def test_integrations_never_leak_encrypted_credentials(client, monkeypatch):
    """Nothing in the portal needs the token, and an authorized merchant is
    still not a reason to hand one out."""
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())

    async def _conns(merchant_id):
        return [{"id": "c1", "provider": "ics_feed", "status": "connected",
                 "direction": "read", "credentials_encrypted": "SUPERSECRET"}]

    client.store.list_connections = _conns  # type: ignore[assignment]
    r = client.get(f"/api/bookings/integrations/{MERCHANT}")
    assert r.status_code == 200
    assert "SUPERSECRET" not in r.text
    assert "credentials_encrypted" not in r.text


# ─── The public feed ──────────────────────────────────────────

def test_feed_rejects_a_malformed_token_without_touching_the_database():
    """The feed URL is public and will be scanned; the length/charset check
    runs before any query."""
    from src.services.booking_feed import feed_for_token
    import asyncio

    for junk in ("", "short", "z" * 32, "../../etc/passwd", "A" * 33):
        assert asyncio.run(feed_for_token(junk)) is None


# ─── Freeing a table from the host stand ──────────────────────

def test_no_show_withdraws_from_their_calendar_and_works_the_waitlist(
    client, monkeypatch,
):
    """Marking a no-show at the host stand has to do everything a phone
    cancellation does.

    Both of these were phone-only once: a table freed at the stand left a
    ghost on the merchant's Square calendar AND quietly recovered nothing,
    which is the moment the waiting list is worth the most — 7:10pm, table
    empty, somebody wants it now.
    """
    withdrawn: list[tuple[str, str]] = []
    recovered: list[tuple[str, str]] = []
    import src.services.booking_agent as ba
    monkeypatch.setattr(ba, "_spawn_withdraw",
                        lambda m, row: withdrawn.append((m, row["id"])))
    monkeypatch.setattr(ba, "_spawn_recovery",
                        lambda m, row: recovered.append((m, row["id"])))
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())

    r = client.patch(f"/api/bookings/{BOOKING}", json={"status": "no_show"})
    assert r.status_code == 200
    assert [b for _, b in withdrawn] == [BOOKING]
    assert [b for _, b in recovered] == [BOOKING]


def test_seating_a_guest_does_neither(client, monkeypatch):
    """Seating occupies the table — withdrawing it from their calendar or
    offering it to the waitlist would be actively wrong."""
    called: list[str] = []
    import src.services.booking_agent as ba
    monkeypatch.setattr(ba, "_spawn_withdraw", lambda m, row: called.append("w"))
    monkeypatch.setattr(ba, "_spawn_recovery", lambda m, row: called.append("r"))
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())

    r = client.patch(f"/api/bookings/{BOOKING}", json={"status": "seated"})
    assert r.status_code == 200
    assert called == []


def test_undoing_a_no_show_puts_it_back_on_their_calendar(client, monkeypatch):
    """Marking the no-show took the booking OFF the merchant's calendar, so
    undoing has to put it back. A mis-tap that leaves the guest missing from
    Square is worse than having no undo at all."""
    pushed: list[str] = []
    import src.services.booking_agent as ba
    monkeypatch.setattr(ba, "_spawn_push", lambda m, row: pushed.append(row["id"]))
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())

    async def _get(booking_id):
        return {"id": booking_id, "merchant_id": MERCHANT, "status": "no_show"}

    client.store.get_booking = _get  # type: ignore[assignment]
    r = client.patch(f"/api/bookings/{BOOKING}", json={"status": "confirmed"})
    assert r.status_code == 200
    assert pushed == [BOOKING]


def test_unseating_a_guest_does_not_duplicate_them_in_square(client, monkeypatch):
    """seated -> confirmed never left their calendar, so re-pushing would
    create a SECOND booking for the same guest."""
    pushed: list[str] = []
    import src.services.booking_agent as ba
    monkeypatch.setattr(ba, "_spawn_push", lambda m, row: pushed.append(row["id"]))
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())

    async def _get(booking_id):
        return {"id": booking_id, "merchant_id": MERCHANT, "status": "seated"}

    client.store.get_booking = _get  # type: ignore[assignment]
    r = client.patch(f"/api/bookings/{BOOKING}", json={"status": "confirmed"})
    assert r.status_code == 200
    assert pushed == []


# ─── The wizard's commit ──────────────────────────────────────

def test_wizard_writes_booking_mode_last(client, monkeypatch):
    """THE ordering guarantee. If booking_mode is switched on before the
    tables and hours exist, the phone agent starts offering times against an
    empty calendar. Writing it last means a failure part-way through leaves
    the merchant OFF rather than live and broken."""
    order: list[str] = []
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())

    async def _create_resource(fields):
        order.append("resource")
        return fields

    async def _create_service(fields):
        order.append("service")
        return fields

    async def _replace_hours(merchant_id, rows):
        order.append("hours")
        return rows

    client.store.create_resource = _create_resource  # type: ignore[assignment]
    client.store.create_service = _create_service  # type: ignore[assignment]
    client.store.replace_hours = _replace_hours  # type: ignore[assignment]

    class TrackingDB(StubDB):
        async def update(self, table, fields, filters):
            order.append(f"config:{fields.get('booking_mode')}")
            return []

    monkeypatch.setattr(br, "get_db", lambda: TrackingDB())

    r = client.post("/api/bookings/setup", json={
        "merchant_id": MERCHANT, "mode": "native", "noun": "table",
        "resources": [{"name": "Table 9", "kind": "table", "seats": 4}],
        "services": [{"name": "Dinner sitting", "duration_minutes": 90}],
        "hours": [{"weekday": 5, "opens_at": "17:00", "closes_at": "22:00"}],
    })
    assert r.status_code == 200
    assert order[-1] == "config:native"
    assert order.index("resource") < order.index("config:native")
    assert order.index("hours") < order.index("config:native")


def test_wizard_is_re_runnable_without_duplicating_tables(client, monkeypatch):
    """A merchant who walks back through the wizard should end up with one set
    of tables, not two. StubStore already reports a resource named T1 and a
    service named Dinner."""
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    created: list[str] = []

    async def _create_resource(fields):
        created.append(fields["name"])
        return fields

    client.store.create_resource = _create_resource  # type: ignore[assignment]

    r = client.post("/api/bookings/setup", json={
        "merchant_id": MERCHANT, "mode": "native", "noun": "table",
        "resources": [{"name": "t1", "kind": "table", "seats": 4},
                      {"name": "Table 2", "kind": "table", "seats": 2}],
    })
    assert r.status_code == 200
    # "t1" matched the existing "T1" case-insensitively and was skipped.
    assert created == ["Table 2"]


def test_wizard_refuses_link_mode_without_a_link(client, monkeypatch):
    """An external_link merchant with no destination is an agent promising a
    text it cannot send."""
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.post("/api/bookings/setup", json={
        "merchant_id": MERCHANT, "mode": "external_link", "noun": "table",
    })
    assert r.status_code == 400


def test_wizard_rejects_an_unknown_mode(client, monkeypatch):
    monkeypatch.setattr(br, "enforce_service_member", lambda *a, **kw: _noop())
    r = client.post("/api/bookings/setup", json={
        "merchant_id": MERCHANT, "mode": "whatever", "noun": "table",
    })
    assert r.status_code == 422
