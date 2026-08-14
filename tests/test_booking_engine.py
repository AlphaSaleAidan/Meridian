"""Booking availability engine — slot generation, timezone and race behaviour.

Run:
    python -m pytest tests/test_booking_engine.py -v

The store is stubbed throughout; these tests are about the ENGINE's arithmetic
(what times exist, which resource gets picked, what happens when one is taken
mid-write), not about persistence. The persistence guarantee itself is a
database constraint and is verified against a real Postgres, not from here.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.services import booking_engine as be  # noqa: E402
from src.services.booking_store import SlotTaken  # noqa: E402

TORONTO = "America/Toronto"


class StubStore:
    """In-memory stand-in for BookingStore."""

    def __init__(self, bookings=None, closures=None, busy=None):
        self.bookings = bookings or []
        self.closures = closures or []
        self.busy = busy or []
        self.created: list[dict] = []
        # resource ids that raise SlotTaken on the next write, to simulate a
        # competing writer landing between our read and our insert.
        self.collide_on: set[str] = set()

    async def list_bookings(self, merchant_id, start_iso, end_iso, live_only=True):
        return list(self.bookings)

    async def list_closures(self, merchant_id, start_iso, end_iso):
        return list(self.closures)

    async def list_busy_blocks(self, merchant_id, start_iso, end_iso):
        return list(self.busy)

    async def create_booking(self, fields):
        if str(fields.get("resource_id")) in self.collide_on:
            raise SlotTaken()
        row = {**fields, "id": f"bk-{len(self.created) + 1}"}
        self.created.append(row)
        self.bookings.append(row)
        return row


def _setup(store, *, resources=None, services=None, hours=None, pacing=None,
           tz=TORONTO):
    be_tz, name = be.resolve_timezone(tz)
    return be.MerchantBookingSetup(
        merchant_id="m1", tz=be_tz, tz_name=name,
        resources=resources if resources is not None else [_chair("r1", "Chair 1")],
        services=services if services is not None else [_service()],
        hours=hours if hours is not None else _week(9, 17),
        pacing=pacing or [],
    )


def _chair(rid, name, seats=1, kind="chair", sort_order=0):
    return {"id": rid, "name": name, "seats": seats, "kind": kind,
            "sort_order": sort_order, "active": True}


def _service(duration=30, buffer=0, min_party=1, max_party=1, sid="s1",
             resource_kind=None):
    return {"id": sid, "name": "Cut", "duration_minutes": duration,
            "buffer_minutes": buffer, "min_party": min_party,
            "max_party": max_party, "resource_kind": resource_kind}


def _week(open_h, close_h, slot=15):
    return [{"weekday": d, "opens_at": f"{open_h:02d}:00",
             "closes_at": f"{close_h:02d}:00", "slot_minutes": slot,
             "active": True} for d in range(7)]


@pytest.fixture(autouse=True)
def _patch_store(monkeypatch):
    holder = {}

    def use(store):
        holder["store"] = store
        monkeypatch.setattr(be, "get_booking_store", lambda: store)
        return store

    yield use


# ─── Slot generation ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_generates_slots_across_the_open_window(_patch_store):
    store = _patch_store(StubStore())
    setup = _setup(store, hours=_week(9, 11, slot=30))
    day = date(2026, 9, 14)  # Monday
    now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)

    slots = await be.find_slots(setup, day, party_size=1, now=now)

    # 09:00, 09:30, 10:00, 10:30 — a 30-min service must END by 11:00, so
    # 10:30 is the last one that fits and 11:00 is not offered.
    assert [s.local_label for s in slots] == ["9 AM", "9:30 AM", "10 AM", "10:30 AM"]


@pytest.mark.asyncio
async def test_service_must_finish_before_closing(_patch_store):
    store = _patch_store(StubStore())
    setup = _setup(store, hours=_week(9, 10, slot=15),
                   services=[_service(duration=60)])
    slots = await be.find_slots(setup, date(2026, 9, 14), 1,
                                now=datetime(2026, 9, 13, tzinfo=timezone.utc))
    # Only 09:00 leaves room for a 60-minute service before 10:00.
    assert [s.local_label for s in slots] == ["9 AM"]


@pytest.mark.asyncio
async def test_closed_day_offers_nothing(_patch_store):
    store = _patch_store(StubStore())
    # Open Mondays only (weekday 1 in Sun=0 terms).
    setup = _setup(store, hours=[{"weekday": 1, "opens_at": "09:00",
                                  "closes_at": "17:00", "slot_minutes": 30}])
    sunday = date(2026, 9, 13)
    slots = await be.find_slots(setup, sunday, 1,
                                now=datetime(2026, 9, 1, tzinfo=timezone.utc))
    assert slots == []


@pytest.mark.asyncio
async def test_minimum_lead_time_hides_imminent_slots(_patch_store):
    store = _patch_store(StubStore())
    setup = _setup(store, hours=_week(9, 11, slot=30))
    day = date(2026, 9, 14)
    # 09:10 Toronto = 13:10 UTC. With a 15-minute floor, 09:30 is the first
    # offerable slot; 09:00 is in the past and must not be offered.
    now = datetime(2026, 9, 14, 13, 10, tzinfo=timezone.utc)
    slots = await be.find_slots(setup, day, 1, now=now)
    assert [s.local_label for s in slots] == ["9:30 AM", "10 AM", "10:30 AM"]


# ─── Resource assignment ──────────────────────────────────────

@pytest.mark.asyncio
async def test_existing_booking_blocks_only_its_own_resource(_patch_store):
    taken = {
        "id": "old", "resource_id": "r1", "party_size": 1,
        "starts_at": "2026-09-14T13:00:00+00:00",   # 09:00 Toronto
        "ends_at": "2026-09-14T13:30:00+00:00",
    }
    store = _patch_store(StubStore(bookings=[taken]))
    setup = _setup(store, resources=[_chair("r1", "Chair 1"), _chair("r2", "Chair 2")],
                   hours=_week(9, 10, slot=30))
    slots = await be.find_slots(setup, date(2026, 9, 14), 1,
                                now=datetime(2026, 9, 13, tzinfo=timezone.utc))
    nine = [s for s in slots if s.local_label == "9 AM"]
    assert len(nine) == 1
    assert nine[0].resource_id == "r2", "should fall through to the free chair"


@pytest.mark.asyncio
async def test_fully_booked_time_is_not_offered(_patch_store):
    rows = [
        {"id": f"b{i}", "resource_id": rid, "party_size": 1,
         "starts_at": "2026-09-14T13:00:00+00:00",
         "ends_at": "2026-09-14T13:30:00+00:00"}
        for i, rid in enumerate(("r1", "r2"))
    ]
    store = _patch_store(StubStore(bookings=rows))
    setup = _setup(store, resources=[_chair("r1", "C1"), _chair("r2", "C2")],
                   hours=_week(9, 10, slot=30))
    slots = await be.find_slots(setup, date(2026, 9, 14), 1,
                                now=datetime(2026, 9, 13, tzinfo=timezone.utc))
    assert "9 AM" not in [s.local_label for s in slots]
    assert "9:30 AM" in [s.local_label for s in slots]


@pytest.mark.asyncio
async def test_back_to_back_bookings_are_allowed(_patch_store):
    """Half-open ranges: a 09:00-09:30 booking must not block 09:30."""
    taken = {"id": "old", "resource_id": "r1", "party_size": 1,
             "starts_at": "2026-09-14T13:00:00+00:00",
             "ends_at": "2026-09-14T13:30:00+00:00"}
    store = _patch_store(StubStore(bookings=[taken]))
    setup = _setup(store, hours=_week(9, 11, slot=30))
    slots = await be.find_slots(setup, date(2026, 9, 14), 1,
                                now=datetime(2026, 9, 13, tzinfo=timezone.utc))
    labels = [s.local_label for s in slots]
    assert "9 AM" not in labels
    assert "9:30 AM" in labels


@pytest.mark.asyncio
async def test_smallest_sufficient_table_wins(_patch_store):
    store = _patch_store(StubStore())
    setup = _setup(
        store,
        resources=[_chair("big", "6-top", seats=6, kind="table"),
                   _chair("small", "2-top", seats=2, kind="table")],
        services=[_service(duration=90, min_party=1, max_party=4,
                           resource_kind="table")],
        hours=_week(17, 21, slot=30),
    )
    slots = await be.find_slots(setup, date(2026, 9, 14), party_size=2,
                                now=datetime(2026, 9, 13, tzinfo=timezone.utc))
    assert slots[0].resource_id == "small", "must not burn the 6-top on a party of 2"

    big_party = await be.find_slots(setup, date(2026, 9, 14), party_size=5,
                                    now=datetime(2026, 9, 13, tzinfo=timezone.utc))
    assert big_party[0].resource_id == "big"


@pytest.mark.asyncio
async def test_party_too_large_for_every_resource(_patch_store):
    store = _patch_store(StubStore())
    setup = _setup(store, resources=[_chair("t", "4-top", seats=4, kind="table")],
                   services=[_service(duration=90, min_party=1, max_party=20,
                                      resource_kind="table")],
                   hours=_week(17, 21))
    slots = await be.find_slots(setup, date(2026, 9, 14), party_size=12,
                                now=datetime(2026, 9, 13, tzinfo=timezone.utc))
    assert slots == []


# ─── Closures and imported busy time ──────────────────────────

@pytest.mark.asyncio
async def test_whole_business_closure_removes_the_window(_patch_store):
    closure = {"id": "c1", "resource_id": None,
               "starts_at": "2026-09-14T13:00:00+00:00",
               "ends_at": "2026-09-14T14:00:00+00:00"}
    store = _patch_store(StubStore(closures=[closure]))
    setup = _setup(store, resources=[_chair("r1", "C1"), _chair("r2", "C2")],
                   hours=_week(9, 11, slot=30))
    labels = [s.local_label for s in await be.find_slots(
        setup, date(2026, 9, 14), 1, now=datetime(2026, 9, 13, tzinfo=timezone.utc))]
    assert labels == ["10 AM", "10:30 AM"]


@pytest.mark.asyncio
async def test_synced_busy_block_blocks_that_staff_member(_patch_store):
    """A Google Calendar event on one barber must not close the shop."""
    busy = {"id": "g1", "resource_id": "r1",
            "starts_at": "2026-09-14T13:00:00+00:00",
            "ends_at": "2026-09-14T13:30:00+00:00"}
    store = _patch_store(StubStore(busy=[busy]))
    setup = _setup(store, resources=[_chair("r1", "Sam"), _chair("r2", "Alex")],
                   hours=_week(9, 10, slot=30))
    nine = [s for s in await be.find_slots(
        setup, date(2026, 9, 14), 1,
        now=datetime(2026, 9, 13, tzinfo=timezone.utc)) if s.local_label == "9 AM"]
    assert len(nine) == 1 and nine[0].resource_id == "r2"


# ─── Pacing (restaurants) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_pacing_caps_covers_per_interval(_patch_store):
    seated = {"id": "b1", "resource_id": "t1", "party_size": 4,
              "starts_at": "2026-09-14T23:00:00+00:00",  # 19:00 Toronto
              "ends_at": "2026-09-15T00:30:00+00:00"}
    store = _patch_store(StubStore(bookings=[seated]))
    setup = _setup(
        store,
        resources=[_chair("t1", "T1", seats=4, kind="table"),
                   _chair("t2", "T2", seats=4, kind="table")],
        services=[_service(duration=90, min_party=1, max_party=4,
                           resource_kind="table")],
        hours=_week(17, 22, slot=30),
        pacing=[{"weekday": None, "starts_at": "17:00", "ends_at": "22:00",
                 "max_covers": 6, "interval_minutes": 30}],
    )
    labels = [s.local_label for s in await be.find_slots(
        setup, date(2026, 9, 14), party_size=4,
        now=datetime(2026, 9, 13, tzinfo=timezone.utc))]
    # 4 already seated at 19:00 + 4 more = 8 > cap of 6, and t2 is free, so
    # only pacing can be what removes 7 PM.
    assert "7 PM" not in labels
    assert "7:30 PM" in labels


# ─── Timezone and DST ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_opening_time_is_local_across_a_dst_change(_patch_store):
    """A 9 AM opening is 9 AM in both EDT and EST — the UTC instant moves,
    the wall clock does not. This is the bug that silently shifts a whole
    restaurant's evening twice a year."""
    store = _patch_store(StubStore())
    setup = _setup(store, hours=_week(9, 10, slot=60))

    before = await be.find_slots(setup, date(2026, 10, 20), 1,
                                 now=datetime(2026, 10, 1, tzinfo=timezone.utc))
    after = await be.find_slots(setup, date(2026, 11, 10), 1,
                                now=datetime(2026, 11, 1, tzinfo=timezone.utc))

    assert before[0].local_label == "9 AM" and after[0].local_label == "9 AM"
    assert before[0].starts_at.hour == 13, "EDT: 09:00 local = 13:00 UTC"
    assert after[0].starts_at.hour == 14, "EST: 09:00 local = 14:00 UTC"


def test_unknown_timezone_falls_back_without_raising():
    tz, name = be.resolve_timezone("Mars/Olympus_Mons")
    assert name == be.DEFAULT_TIMEZONE
    tz2, name2 = be.resolve_timezone("")
    assert name2 == be.DEFAULT_TIMEZONE


def test_spoken_time_has_no_leading_zero():
    tz, _ = be.resolve_timezone(TORONTO)
    assert be._speak_time(datetime(2026, 9, 14, 9, 5, tzinfo=tz)) == "9:05 AM"
    assert be._speak_time(datetime(2026, 9, 14, 13, 0, tzinfo=tz)) == "1 PM"
    assert be._speak_time(datetime(2026, 9, 14, 0, 30, tzinfo=tz)) == "12:30 AM"
    assert be._speak_time(datetime(2026, 9, 14, 12, 0, tzinfo=tz)) == "12 PM"


# ─── reserve(): the part that promises ────────────────────────

@pytest.mark.asyncio
async def test_reserve_writes_a_confirmed_booking(_patch_store):
    store = _patch_store(StubStore())
    setup = _setup(store, hours=_week(9, 17))
    start = datetime(2026, 9, 14, 13, 0, tzinfo=timezone.utc)

    row = await be.reserve(setup, start, 1, "Dana", customer_phone="+15551234567")

    assert row["status"] == "confirmed"
    assert row["resource_id"] == "r1"
    assert len(row["confirmation_code"]) == 6
    assert row["local_time"] == "9 AM"
    # ends_at must carry the buffer, not just the customer-facing duration.
    assert row["ends_at"] == "2026-09-14T13:30:00+00:00"


@pytest.mark.asyncio
async def test_reserve_falls_through_when_a_resource_is_taken_mid_write(_patch_store):
    """The race the exclusion constraint exists to catch: our read said r1 was
    free, someone else won it, and the write bounced. That is not "no
    availability" — it means try the next chair."""
    store = _patch_store(StubStore())
    store.collide_on = {"r1"}
    setup = _setup(store, resources=[_chair("r1", "C1"), _chair("r2", "C2")],
                   hours=_week(9, 17))
    start = datetime(2026, 9, 14, 13, 0, tzinfo=timezone.utc)

    row = await be.reserve(setup, start, 1, "Dana")
    assert row["resource_id"] == "r2"


@pytest.mark.asyncio
async def test_reserve_raises_rather_than_faking_when_all_collide(_patch_store):
    store = _patch_store(StubStore())
    store.collide_on = {"r1", "r2"}
    setup = _setup(store, resources=[_chair("r1", "C1"), _chair("r2", "C2")],
                   hours=_week(9, 17))
    with pytest.raises(be.NoAvailability):
        await be.reserve(setup, datetime(2026, 9, 14, 13, 0, tzinfo=timezone.utc),
                         1, "Dana")
    assert store.created == [], "nothing may be persisted when every write failed"


@pytest.mark.asyncio
async def test_reserve_refuses_during_a_whole_business_closure(_patch_store):
    closure = {"id": "c1", "resource_id": None,
               "starts_at": "2026-09-14T12:00:00+00:00",
               "ends_at": "2026-09-14T18:00:00+00:00"}
    store = _patch_store(StubStore(closures=[closure]))
    setup = _setup(store, hours=_week(9, 17))
    with pytest.raises(be.BookingClosed):
        await be.reserve(setup, datetime(2026, 9, 14, 13, 0, tzinfo=timezone.utc),
                         1, "Dana")


@pytest.mark.asyncio
async def test_reserve_skips_a_resource_it_can_see_is_busy(_patch_store):
    taken = {"id": "old", "resource_id": "r1", "party_size": 1,
             "starts_at": "2026-09-14T13:00:00+00:00",
             "ends_at": "2026-09-14T13:30:00+00:00"}
    store = _patch_store(StubStore(bookings=[taken]))
    setup = _setup(store, resources=[_chair("r1", "C1"), _chair("r2", "C2")],
                   hours=_week(9, 17))
    row = await be.reserve(setup, datetime(2026, 9, 14, 13, 15, tzinfo=timezone.utc),
                           1, "Dana")
    assert row["resource_id"] == "r2"


# ─── Service selection ────────────────────────────────────────

def test_narrowest_party_band_wins():
    setup = be.MerchantBookingSetup(
        merchant_id="m1", tz=be.resolve_timezone(TORONTO)[0], tz_name=TORONTO,
        services=[
            _service(sid="any", duration=60, min_party=1, max_party=99),
            _service(sid="large", duration=120, min_party=5, max_party=8),
        ],
    )
    assert be.select_service(setup, 6)["id"] == "large"
    assert be.select_service(setup, 2)["id"] == "any"


def test_explicit_service_id_overrides_the_band():
    setup = be.MerchantBookingSetup(
        merchant_id="m1", tz=be.resolve_timezone(TORONTO)[0], tz_name=TORONTO,
        services=[_service(sid="a", max_party=99), _service(sid="b", max_party=99)],
    )
    assert be.select_service(setup, 2, service_id="b")["id"] == "b"
