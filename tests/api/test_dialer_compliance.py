"""Dial-time compliance gate — window math and store side-effect basics.

The windows under test are the legal envelopes the auto dialer hard-blocks
against (docs/AUTODIALER_PLAN.md §6):
  Canada CRTC UTRs: Mon-Fri 09:00-21:30, Sat-Sun 10:00-18:00 local.
  US TCPA:          08:00-21:00 local, all days.
Fail-safe: toll-free / unknown / non-NANP numbers are blocked.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.services.dialer_compliance import area_code_of, check_calling_window
from src.services.dialer_store import MemoryDialerStore

TORONTO = ZoneInfo("America/Toronto")
VANCOUVER = ZoneInfo("America/Vancouver")
NEW_YORK = ZoneInfo("America/New_York")

# 2026-08-11 = Tuesday, 2026-08-15 = Saturday (weekday() 1 and 5).


def _at(tz, y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=tz)


def test_area_code_extraction():
    assert area_code_of("416-555-0134") == "416"
    assert area_code_of("+14165550134") == "416"
    assert area_code_of("+442071234567") == ""  # non-NANP
    assert area_code_of("") == ""


@pytest.mark.parametrize("hh,mm,allowed", [
    (8, 59, False),   # before CRTC weekday open
    (9, 0, True),     # open edge
    (21, 29, True),   # last minute inside
    (21, 30, False),  # close edge (exclusive)
])
def test_crtc_weekday_window_toronto(hh, mm, allowed):
    check = check_calling_window("+14165550134", _at(TORONTO, 2026, 8, 11, hh, mm))
    assert check.country == "CA"
    assert check.allowed is allowed
    if not allowed:
        assert check.reason == "calling_window"


@pytest.mark.parametrize("hh,mm,allowed", [
    (9, 59, False),   # weekend opens at 10
    (10, 0, True),
    (17, 59, True),
    (18, 0, False),   # weekend closes at 18
])
def test_crtc_weekend_window_toronto(hh, mm, allowed):
    check = check_calling_window("+14165550134", _at(TORONTO, 2026, 8, 15, hh, mm))
    assert check.allowed is allowed


def test_window_is_lead_local_not_caller_local():
    # 20:00 in Toronto is 17:00 in Vancouver: a 604 number is still callable
    # when a 416 number is approaching close.
    now = _at(TORONTO, 2026, 8, 11, 20, 0)
    assert check_calling_window("+16045550134", now).allowed is True
    assert check_calling_window("+16045550134", now).tz == "America/Vancouver"


@pytest.mark.parametrize("hh,mm,allowed", [
    (7, 59, False),
    (8, 0, True),
    (20, 59, True),
    (21, 0, False),
])
def test_tcpa_window_new_york(hh, mm, allowed):
    check = check_calling_window("+12125550134", _at(NEW_YORK, 2026, 8, 11, hh, mm))
    assert check.country == "US"
    assert check.allowed is allowed


def test_tcpa_applies_on_weekends_too():
    # US window is the same envelope all days; 09:00 Saturday is fine.
    assert check_calling_window("+12125550134", _at(NEW_YORK, 2026, 8, 15, 9, 0)).allowed


def test_fail_safe_blocks():
    now = _at(TORONTO, 2026, 8, 11, 12, 0)
    assert check_calling_window("+18005550134", now).reason == "unknown_area_code"
    assert check_calling_window("+15555550134", now).reason == "unknown_area_code"
    assert check_calling_window("not-a-number", now).reason == "invalid_number"
    assert check_calling_window("+442071234567", now).reason == "invalid_number"


@pytest.mark.asyncio
async def test_memory_store_dnc_and_callbacks():
    store = MemoryDialerStore()
    await store.dnc_add("+14165550134", "canada", "asked to stop", "rep-1")
    hits = await store.dnc_filter(["+14165550134", "+16045550134"])
    assert hits == {"+14165550134"}
    await store.dnc_remove("+14165550134")
    assert await store.dnc_filter(["+14165550134"]) == set()

    await store.create_callback({"rep_id": "rep-1", "phone_e164": "+16045550134",
                                 "due_at": "2026-08-13T17:00:00+00:00"})
    await store.create_callback({"rep_id": "rep-1", "phone_e164": "+14165550134",
                                 "due_at": "2026-08-13T15:00:00+00:00"})
    rows = await store.list_callbacks(rep_ids=["rep-1"])
    assert [r["phone_e164"] for r in rows] == ["+14165550134", "+16045550134"]  # due order


@pytest.mark.asyncio
async def test_memory_store_session_counters_and_attempts():
    store = MemoryDialerStore()
    session = await store.create_session({"rep_id": "rep-1", "market": "canada",
                                          "wrap_up_seconds": 15})
    assert (await store.current_session("rep-1"))["id"] == session["id"]
    call = await store.create_call({"session_id": session["id"], "rep_id": "rep-1",
                                    "lead_id": "lead-1", "phone_e164": "+14165550134"})
    attempts = await store.last_attempts("rep-1", "2000-01-01T00:00:00")
    assert "lead-1" in attempts
    await store.update_call(call["id"], {"status": "connected"})
    live = await store.list_calls(live_only=True)
    assert [c["id"] for c in live] == [call["id"]]
