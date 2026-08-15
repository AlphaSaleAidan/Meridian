"""Recurring appointments: the dates, and what happens when one is taken.

Run:
    python -m pytest tests/test_booking_series.py -v

The load-bearing test is test_a_clash_skips_and_never_evicts. A series that
could bump an existing booking would be a hole straight through the
double-booking guarantee, and the first merchant it happened to would never
trust the calendar again.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.services import booking_engine as be  # noqa: E402
from src.services import booking_series as bs  # noqa: E402
from src.services.booking_store import SlotTaken  # noqa: E402

# 2026-09-01 is a Tuesday. Sunday=0 in our weekday convention, so Tuesday=2.
TODAY = date(2026, 9, 1)


def _series(**over):
    base = {
        "id": "sr-1",
        "merchant_id": "m1",
        "customer_name": "Dana",
        "customer_phone": "+16045550100",
        "party_size": 1,
        "interval_weeks": 4,
        "weekday": 2,
        "local_time": "14:00:00",
        "starts_on": "2026-09-01",
        "ends_on": None,
        "generate_weeks": 12,
        "status": "active",
        "skipped_dates": [],
    }
    base.update(over)
    return base


# ── the dates ───────────────────────────────────────────────────────────

def test_every_four_weeks_on_the_right_weekday():
    dates = bs.occurrence_dates(_series(), today=TODAY)
    assert dates[0] == date(2026, 9, 1)
    assert dates[1] == date(2026, 9, 29)
    assert dates[2] == date(2026, 10, 27)
    # All Tuesdays.
    assert all(d.weekday() == 1 for d in dates)


def test_weekly_is_just_interval_one():
    dates = bs.occurrence_dates(_series(interval_weeks=1), today=TODAY)
    assert dates[1] - dates[0] == (date(2026, 9, 8) - date(2026, 9, 1))


def test_the_rhythm_survives_a_gap_in_generation():
    """Dates come from starts_on and the interval, not from "the last one we
    made" — so a series that stopped for a month resumes on its own rhythm
    instead of drifting by however long the outage was."""
    late = bs.occurrence_dates(_series(), today=date(2026, 10, 15))
    assert date(2026, 10, 27) in late
    assert all(((d - date(2026, 9, 1)).days % 28) == 0 for d in late)


def test_an_end_date_stops_it():
    dates = bs.occurrence_dates(_series(ends_on="2026-10-01"), today=TODAY)
    assert dates == [date(2026, 9, 1), date(2026, 9, 29)]


def test_past_dates_are_not_regenerated():
    dates = bs.occurrence_dates(_series(starts_on="2026-01-06"), today=TODAY)
    assert all(d >= TODAY for d in dates)


def test_the_horizon_is_capped_however_greedy_the_series():
    """A year of rows locks a calendar nobody has planned yet."""
    dates = bs.occurrence_dates(
        _series(interval_weeks=1, generate_weeks=999), today=TODAY)
    assert len(dates) <= bs.MAX_GENERATE_WEEKS + 1


# ── generation ──────────────────────────────────────────────────────────

class Setup:
    tz = timezone.utc
    merchant_id = "m1"


@pytest.fixture
def svc(monkeypatch):
    s = bs.SeriesService.__new__(bs.SeriesService)

    class Store:
        def __init__(self):
            self.patches: list[dict] = []
            self.existing: set[str] = set()
            self.cancelled: list[str] = []
            self.rows: list[dict] = []

        async def _req(self, method, table, params=None, json=None, **kw):
            if method == "GET" and table == "bookings":
                return [{"starts_at": f"{d}T14:00:00+00:00"} for d in self.existing] \
                    if "series_id" in (params or {}) and "select" in (params or {}) \
                    and (params or {}).get("select") == "starts_at" else self.rows
            if method == "PATCH":
                self.patches.append(json or {})
            return []

        async def cancel_booking(self, booking_id, reason=""):
            self.cancelled.append(booking_id)
            return {"id": booking_id}

    s._store = Store()
    return s


@pytest.mark.asyncio
async def test_generation_creates_one_booking_per_date(svc, monkeypatch):
    made: list[datetime] = []

    async def fake_reserve(setup, start_utc, party, name, **kw):
        made.append(start_utc)
        assert kw["extra"]["series_id"] == "sr-1"
        return {"id": f"bk-{len(made)}"}

    monkeypatch.setattr(be, "reserve", fake_reserve)
    out = await svc.generate(_series(), Setup(), today=TODAY)
    assert out["created"] == len(made) > 0
    assert out["skipped"] == []
    # The standing 2pm stays 2pm.
    assert all(m.time() == time(14, 0) for m in made)


@pytest.mark.asyncio
async def test_a_clash_skips_and_never_evicts(svc, monkeypatch):
    """THE test. A regular losing one week is recoverable; a walk-in being
    silently cancelled to make room is not."""
    calls: list[datetime] = []

    async def fake_reserve(setup, start_utc, party, name, **kw):
        calls.append(start_utc)
        if len(calls) == 2:
            raise SlotTaken()
        return {"id": "bk"}

    monkeypatch.setattr(be, "reserve", fake_reserve)
    out = await svc.generate(_series(), Setup(), today=TODAY)

    assert len(out["skipped"]) == 1
    assert out["created"] >= 1
    # Nothing was cancelled to make room.
    assert svc._store.cancelled == []
    # The skip is recorded so a human can offer them something else.
    assert any("skipped_dates" in p for p in svc._store.patches)


@pytest.mark.asyncio
async def test_closed_days_skip_rather_than_fail_the_series(svc, monkeypatch):
    async def fake_reserve(setup, start_utc, party, name, **kw):
        raise be.BookingClosed("closed")

    monkeypatch.setattr(be, "reserve", fake_reserve)
    out = await svc.generate(_series(), Setup(), today=TODAY)
    assert out["created"] == 0
    assert len(out["skipped"]) > 0


@pytest.mark.asyncio
async def test_a_paused_series_generates_nothing(svc, monkeypatch):
    async def fake_reserve(*a, **kw):
        raise AssertionError("should not be called")

    monkeypatch.setattr(be, "reserve", fake_reserve)
    out = await svc.generate(_series(status="paused"), Setup(), today=TODAY)
    assert out["created"] == 0


@pytest.mark.asyncio
async def test_a_pinned_resource_is_passed_through(svc, monkeypatch):
    seen: list[dict] = []

    async def fake_reserve(setup, start_utc, party, name, **kw):
        seen.append(kw["extra"])
        return {"id": "bk"}

    monkeypatch.setattr(be, "reserve", fake_reserve)
    await svc.generate(
        _series(resource_id="res-9", resource_strict=True), Setup(), today=TODAY)
    assert seen[0]["resource_id"] == "res-9"


@pytest.mark.asyncio
async def test_a_preferred_resource_is_not_pinned(svc, monkeypatch):
    """A regular would rather see somebody else than lose the week."""
    seen: list[dict] = []

    async def fake_reserve(setup, start_utc, party, name, **kw):
        seen.append(kw["extra"])
        return {"id": "bk"}

    monkeypatch.setattr(be, "reserve", fake_reserve)
    await svc.generate(
        _series(resource_id="res-9", resource_strict=False), Setup(), today=TODAY)
    assert "resource_id" not in seen[0]


@pytest.mark.asyncio
async def test_cancelling_keeps_the_visits_already_had(svc, monkeypatch):
    svc._store.rows = [{"id": "bk-future", "starts_at": "2026-10-27T14:00:00+00:00"}]
    out = await svc.cancel("sr-1", future_only=True)
    assert out["released"] == 1
    assert svc._store.cancelled == ["bk-future"]
    assert any(p.get("status") == "cancelled" for p in svc._store.patches)
