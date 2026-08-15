"""Phone booking handlers — argument parsing and what the agent SAYS.

Run:
    python -m pytest tests/test_booking_agent.py -v

The assertions here are mostly about copy, which is unusual for a test suite
and deliberate: these strings are read aloud to a paying customer by a
synthetic voice, and the difference between "you're all set" and "that time
just went" is the difference between a kept table and a walk-out. The most
important tests in this file are the ones asserting that a FAILED booking
never produces a confirming sentence.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.services import booking_agent as ba  # noqa: E402
from src.services import booking_engine as be  # noqa: E402
from src.services.booking_store import SlotTaken  # noqa: E402

TORONTO = "America/Toronto"
MONDAY = date(2026, 9, 14)
# 08:00 Toronto on that Monday.
NOW = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)


class StubStore:
    def __init__(self, bookings=None):
        self.bookings = bookings or []
        self.cancelled: list[tuple[str, str]] = []
        self.collide_all = False

    async def list_bookings(self, *a, **kw):
        return list(self.bookings)

    async def list_closures(self, *a, **kw):
        return []

    async def list_busy_blocks(self, *a, **kw):
        return []

    async def create_booking(self, fields):
        if self.collide_all:
            raise SlotTaken()
        row = {**fields, "id": "bk-1"}
        self.bookings.append(row)
        return row

    async def find_by_code(self, merchant_id, code):
        for b in self.bookings:
            if str(b.get("confirmation_code", "")).lower() == code.strip().lower():
                return b
        return None

    async def find_upcoming_by_phone(self, merchant_id, phone):
        return [b for b in self.bookings if b.get("customer_phone") == phone]

    async def cancel_booking(self, booking_id, reason=""):
        self.cancelled.append((booking_id, reason))
        return {}


def _setup(noun="reservation"):
    tz, name = be.resolve_timezone(TORONTO)
    return be.MerchantBookingSetup(
        merchant_id="m1", tz=tz, tz_name=name, noun=noun,
        resources=[{"id": "r1", "name": "Chair 1", "seats": 4, "kind": "chair",
                    "sort_order": 0}],
        services=[{"id": "s1", "name": "Cut", "duration_minutes": 30,
                   "buffer_minutes": 0, "min_party": 1, "max_party": 8}],
        hours=[{"weekday": d, "opens_at": "09:00", "closes_at": "17:00",
                "slot_minutes": 30} for d in range(7)],
    )


@pytest.fixture
def store(monkeypatch):
    s = StubStore()
    monkeypatch.setattr(be, "get_booking_store", lambda: s)
    monkeypatch.setattr(ba, "get_booking_store", lambda: s)
    return s


# ─── Date parsing ─────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("2026-09-14", MONDAY),
    ("2026-9-4", date(2026, 9, 4)),
    ("today", MONDAY),
    ("tonight", MONDAY),
    ("tomorrow", date(2026, 9, 15)),
    ("friday", date(2026, 9, 18)),
    ("Friday", date(2026, 9, 18)),
    ("next friday", date(2026, 9, 18)),
    ("monday", MONDAY),          # today IS Monday
    ("next monday", date(2026, 9, 21)),
])
def test_parse_date(text, expected):
    assert ba.parse_date(text, MONDAY) == expected


@pytest.mark.parametrize("text", ["", None, "sometime", "the usual", "2026-13-45"])
def test_parse_date_refuses_the_unknowable(text):
    assert ba.parse_date(text, MONDAY) is None


@pytest.mark.parametrize("text,expected", [
    ("19:00", time(19, 0)),
    ("7pm", time(19, 0)),
    ("7 pm", time(19, 0)),
    ("7:30pm", time(19, 30)),
    ("12am", time(0, 0)),
    ("12pm", time(12, 0)),
    ("09:15", time(9, 15)),
    ("9", time(9, 0)),
])
def test_parse_time(text, expected):
    assert ba.parse_time(text) == expected


@pytest.mark.parametrize("text", ["", None, "evening", "25:00", "7:99", "13pm"])
def test_parse_time_refuses_the_unknowable(text):
    assert ba.parse_time(text) is None


# ─── check_availability ───────────────────────────────────────

@pytest.mark.asyncio
async def test_availability_offers_at_most_three_times(store):
    out = await ba.handle_check_availability(
        {"date": "2026-09-14"}, _setup(), now=NOW)
    # A voice reading eight options is unusable; three is the cap.
    assert out.count(":") + out.count("AM") + out.count("PM") > 0
    assert out.count(",") <= 2


@pytest.mark.asyncio
async def test_availability_confirms_an_exact_requested_time(store):
    out = await ba.handle_check_availability(
        {"date": "2026-09-14", "time": "14:00"}, _setup(), now=NOW)
    assert "2 PM is open" in out


@pytest.mark.asyncio
async def test_availability_offers_alternatives_when_the_exact_time_is_gone(store):
    store.bookings.append({
        "id": "x", "resource_id": "r1", "party_size": 1,
        "starts_at": "2026-09-14T18:00:00+00:00",   # 14:00 Toronto
        "ends_at": "2026-09-14T18:30:00+00:00",
    })
    out = await ba.handle_check_availability(
        {"date": "2026-09-14", "time": "14:00"}, _setup(), now=NOW)
    assert "isn't open" in out
    assert "2 PM is open" not in out


@pytest.mark.asyncio
async def test_availability_asks_again_when_the_date_is_missing(store):
    out = await ba.handle_check_availability({}, _setup(), now=NOW)
    assert out == "What day were you thinking?"


@pytest.mark.asyncio
async def test_availability_refuses_a_past_date(store):
    out = await ba.handle_check_availability(
        {"date": "2026-09-01"}, _setup(), now=NOW)
    assert "already passed" in out


@pytest.mark.asyncio
async def test_availability_refuses_absurd_lead_time(store):
    out = await ba.handle_check_availability(
        {"date": "2028-01-01"}, _setup(), now=NOW)
    assert "six months" in out


# ─── book ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_book_confirms_with_a_spelled_out_code(store):
    out = await ba.handle_book(
        {"customer_name": "Dana Reid", "date": "2026-09-14", "time": "14:00",
         "party_size": 2},
        _setup(), caller_phone="+15551234567", now=NOW)
    assert "You're all set, Dana" in out
    assert "2 PM" in out
    assert "for 2" in out
    assert "Monday" in out
    row = store.bookings[-1]
    code = row["confirmation_code"]
    # Spelled with spaces so a TTS voice reads letters, not a word.
    assert " ".join(code) in out
    assert row["customer_phone"] == "+15551234567"
    assert row["source"] == "phone"


@pytest.mark.asyncio
async def test_book_asks_for_a_name_rather_than_inventing_one(store):
    out = await ba.handle_book(
        {"date": "2026-09-14", "time": "14:00"}, _setup(), now=NOW)
    assert out == "Can I get a name for the booking?"
    assert store.bookings == []


@pytest.mark.asyncio
async def test_book_asks_again_when_time_is_unparseable(store):
    out = await ba.handle_book(
        {"customer_name": "Dana", "date": "2026-09-14", "time": "sometime"},
        _setup(), now=NOW)
    assert "What day and time" in out
    assert store.bookings == []


@pytest.mark.asyncio
async def test_book_refuses_a_slot_that_is_too_soon(store):
    # 08:00 Toronto now; asking for 08:05 leaves five minutes.
    out = await ba.handle_book(
        {"customer_name": "Dana", "date": "2026-09-14", "time": "08:05"},
        _setup(), now=NOW)
    assert "too soon" in out
    assert store.bookings == []


@pytest.mark.asyncio
async def test_book_never_confirms_when_every_resource_collides(store):
    """The honesty guarantee. A caller must not hang up believing they have a
    table when the write failed."""
    store.collide_all = True
    out = await ba.handle_book(
        {"customer_name": "Dana", "date": "2026-09-14", "time": "14:00"},
        _setup(), now=NOW)
    assert "all set" not in out.lower()
    assert "confirmation code" not in out.lower()
    assert "just went" in out or "full" in out


@pytest.mark.asyncio
async def test_book_offers_alternatives_after_a_collision(store):
    store.collide_all = True
    out = await ba.handle_book(
        {"customer_name": "Dana", "date": "2026-09-14", "time": "14:00"},
        _setup(), now=NOW)
    # find_slots still reports open times (the stub only fails WRITES), so the
    # caller should be given somewhere to go rather than a dead end.
    assert "would any of those work" in out.lower()


@pytest.mark.asyncio
async def test_book_uses_the_merchant_noun_in_refusals(store):
    out = await ba.handle_book(
        {"customer_name": "Dana", "date": "2030-01-01", "time": "14:00"},
        _setup(noun="table"), now=NOW)
    assert "tables" in out


# ─── cancel / lookup ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_by_code(store):
    store.bookings.append({
        "id": "bk-9", "confirmation_code": "ABC123", "party_size": 2,
        "starts_at": "2026-09-14T18:00:00+00:00",
        "ends_at": "2026-09-14T19:00:00+00:00",
    })
    out = await ba.handle_cancel({"confirmation_code": "abc123"}, _setup())
    assert store.cancelled and store.cancelled[0][0] == "bk-9"
    assert "cancelled" in out and "2 PM" in out


@pytest.mark.asyncio
async def test_cancel_with_an_unknown_code_cancels_nothing(store):
    out = await ba.handle_cancel({"confirmation_code": "ZZZZZZ"}, _setup())
    assert store.cancelled == []
    assert "couldn't find" in out


@pytest.mark.asyncio
async def test_cancel_refuses_to_guess_between_several_bookings(store):
    """Cancelling the wrong booking is unrecoverable mid-call."""
    for i in range(2):
        store.bookings.append({
            "id": f"bk-{i}", "customer_phone": "+15551234567",
            "confirmation_code": f"CODE{i}",
            "starts_at": "2026-09-14T18:00:00+00:00",
            "ends_at": "2026-09-14T19:00:00+00:00",
        })
    out = await ba.handle_cancel({}, _setup(), caller_phone="+15551234567")
    assert store.cancelled == []
    assert "more than one" in out


@pytest.mark.asyncio
async def test_cancel_by_caller_number_when_unambiguous(store):
    store.bookings.append({
        "id": "bk-solo", "customer_phone": "+15551234567",
        "confirmation_code": "SOLO11",
        "starts_at": "2026-09-14T18:00:00+00:00",
        "ends_at": "2026-09-14T19:00:00+00:00",
    })
    await ba.handle_cancel({}, _setup(), caller_phone="+15551234567")
    assert store.cancelled and store.cancelled[0][0] == "bk-solo"


@pytest.mark.asyncio
async def test_cancel_also_takes_it_off_the_merchants_calendar(store, monkeypatch):
    """The original bug was not a broken withdraw — it was that NOTHING CALLED
    the withdraw. Both adapters implemented cancel_booking and no code path
    ever reached it, so a phone cancellation left the guest sitting on the
    shop's Square calendar and staff held the table. This asserts the wiring,
    which is the part that was missing."""
    withdrawn: list[tuple[str, str]] = []
    monkeypatch.setattr(
        ba, "_spawn_withdraw",
        lambda merchant_id, row: withdrawn.append((merchant_id, row["id"])),
    )
    store.bookings.append({
        "id": "bk-w", "confirmation_code": "WITH01", "party_size": 2,
        "starts_at": "2026-09-14T18:00:00+00:00",
        "ends_at": "2026-09-14T19:00:00+00:00",
    })
    await ba.handle_cancel({"confirmation_code": "WITH01"}, _setup())
    assert withdrawn == [("m1", "bk-w")]


@pytest.mark.asyncio
async def test_lookup_reads_back_day_and_time(store):
    store.bookings.append({
        "id": "bk-1", "confirmation_code": "AAA111", "party_size": 4,
        "starts_at": "2026-09-14T23:00:00+00:00",   # 19:00 Toronto
        "ends_at": "2026-09-15T00:30:00+00:00",
    })
    out = await ba.handle_lookup({"confirmation_code": "AAA111"}, _setup())
    assert "Monday" in out and "7 PM" in out and "for 4" in out


@pytest.mark.asyncio
async def test_lookup_with_nothing_found_offers_to_book(store):
    out = await ba.handle_lookup({"confirmation_code": "NOPE11"}, _setup())
    assert "Would you like to make one" in out
