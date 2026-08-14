"""iCalendar feed parsing — the universal read-only booking integration.

Run:
    python -m pytest tests/test_booking_ics.py -v

Fixtures below are the shapes real exporters actually emit: Google's UTC
stamps, Outlook's TZID-qualified local times, folded 75-character lines,
all-day DATE values, and the CANCELLED/TRANSPARENT flags that must NOT block
a merchant's calendar.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.services.booking_providers.ics_feed import (  # noqa: E402
    _parse_duration,
    parse_ics,
)


def _wrap(body: str) -> str:
    return ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//EN\r\n"
            + body + "\r\nEND:VCALENDAR\r\n")


def test_parses_a_utc_event():
    ics = _wrap(
        "BEGIN:VEVENT\r\nUID:abc-1\r\nSUMMARY:Haircut\r\n"
        "DTSTART:20260914T190000Z\r\nDTEND:20260914T193000Z\r\nEND:VEVENT"
    )
    blocks = parse_ics(ics)
    assert len(blocks) == 1
    b = blocks[0]
    assert b.starts_at == datetime(2026, 9, 14, 19, 0, tzinfo=timezone.utc)
    assert b.ends_at == datetime(2026, 9, 14, 19, 30, tzinfo=timezone.utc)
    assert b.external_id == "abc-1"
    assert b.summary == "Haircut"


def test_tzid_local_time_converts_to_utc():
    """Outlook's shape. 19:00 in Toronto in September is 23:00 UTC."""
    ics = _wrap(
        "BEGIN:VEVENT\r\nUID:tz-1\r\n"
        "DTSTART;TZID=America/Toronto:20260914T190000\r\n"
        "DTEND;TZID=America/Toronto:20260914T203000\r\nEND:VEVENT"
    )
    b = parse_ics(ics)[0]
    assert b.starts_at == datetime(2026, 9, 14, 23, 0, tzinfo=timezone.utc)
    assert b.ends_at == datetime(2026, 9, 15, 0, 30, tzinfo=timezone.utc)


def test_tzid_respects_standard_time_offset():
    """The same wall clock in January is a different UTC instant. Getting this
    wrong shifts every imported block by an hour for half the year."""
    ics = _wrap(
        "BEGIN:VEVENT\r\nUID:tz-2\r\n"
        "DTSTART;TZID=America/Toronto:20260115T190000\r\n"
        "DTEND;TZID=America/Toronto:20260115T200000\r\nEND:VEVENT"
    )
    b = parse_ics(ics)[0]
    assert b.starts_at == datetime(2026, 1, 16, 0, 0, tzinfo=timezone.utc)


def test_all_day_event_blocks_a_full_day():
    ics = _wrap(
        "BEGIN:VEVENT\r\nUID:day-1\r\nSUMMARY:Closed for the holiday\r\n"
        "DTSTART;VALUE=DATE:20261225\r\nDTEND;VALUE=DATE:20261226\r\nEND:VEVENT"
    )
    b = parse_ics(ics)[0]
    assert (b.ends_at - b.starts_at).days == 1


def test_all_day_event_without_dtend_still_blocks_a_day():
    ics = _wrap(
        "BEGIN:VEVENT\r\nUID:day-2\r\nDTSTART;VALUE=DATE:20261225\r\nEND:VEVENT"
    )
    b = parse_ics(ics)[0]
    assert (b.ends_at - b.starts_at).days == 1


def test_duration_is_used_when_dtend_is_absent():
    ics = _wrap(
        "BEGIN:VEVENT\r\nUID:dur-1\r\nDTSTART:20260914T190000Z\r\n"
        "DURATION:PT1H30M\r\nEND:VEVENT"
    )
    b = parse_ics(ics)[0]
    assert b.ends_at == datetime(2026, 9, 14, 20, 30, tzinfo=timezone.utc)


def test_folded_lines_are_rejoined():
    """RFC 5545 folds at 75 octets; a naive parser truncates the value."""
    ics = _wrap(
        "BEGIN:VEVENT\r\nUID:fold-1\r\n"
        "SUMMARY:Colour and cut for a returning client with a very long\r\n"
        "  description that got folded\r\n"
        "DTSTART:20260914T190000Z\r\nDTEND:20260914T200000Z\r\nEND:VEVENT"
    )
    b = parse_ics(ics)[0]
    assert b.summary.endswith("that got folded")


def test_cancelled_events_do_not_block():
    ics = _wrap(
        "BEGIN:VEVENT\r\nUID:c-1\r\nSTATUS:CANCELLED\r\n"
        "DTSTART:20260914T190000Z\r\nDTEND:20260914T200000Z\r\nEND:VEVENT"
    )
    assert parse_ics(ics) == []


def test_transparent_events_do_not_block():
    """An all-day "Q3 planning" banner marked free must not close the shop."""
    ics = _wrap(
        "BEGIN:VEVENT\r\nUID:t-1\r\nTRANSP:TRANSPARENT\r\n"
        "DTSTART:20260914T190000Z\r\nDTEND:20260914T200000Z\r\nEND:VEVENT"
    )
    assert parse_ics(ics) == []


def test_vtimezone_dtstart_is_not_read_as_an_event():
    """Every real Google/Outlook feed carries a VTIMEZONE block whose DTSTART
    is 1970-ish. Reading it would invent busy time decades ago."""
    ics = _wrap(
        "BEGIN:VTIMEZONE\r\nTZID:America/Toronto\r\n"
        "BEGIN:DAYLIGHT\r\nDTSTART:19700308T020000\r\nTZOFFSETFROM:-0500\r\n"
        "TZOFFSETTO:-0400\r\nEND:DAYLIGHT\r\nEND:VTIMEZONE\r\n"
        "BEGIN:VEVENT\r\nUID:real-1\r\nDTSTART:20260914T190000Z\r\n"
        "DTEND:20260914T200000Z\r\nEND:VEVENT"
    )
    blocks = parse_ics(ics)
    assert len(blocks) == 1 and blocks[0].external_id == "real-1"


def test_multiple_events_are_all_returned():
    body = "\r\n".join(
        f"BEGIN:VEVENT\r\nUID:m-{i}\r\nDTSTART:2026091{i}T190000Z\r\n"
        f"DTEND:2026091{i}T200000Z\r\nEND:VEVENT"
        for i in range(1, 5)
    )
    assert len(parse_ics(_wrap(body))) == 4


def test_event_without_uid_gets_a_stable_synthetic_id():
    """The busy-block table is unique on (connection_id, external_id), so a
    missing UID must still produce the SAME id across resyncs or every sweep
    would churn rows."""
    ics = _wrap(
        "BEGIN:VEVENT\r\nSUMMARY:Walk-in\r\nDTSTART:20260914T190000Z\r\n"
        "DTEND:20260914T200000Z\r\nEND:VEVENT"
    )
    first = parse_ics(ics)[0].external_id
    second = parse_ics(ics)[0].external_id
    assert first and first == second


def test_zero_length_and_backwards_events_are_dropped():
    ics = _wrap(
        "BEGIN:VEVENT\r\nUID:z-1\r\nDTSTART:20260914T190000Z\r\n"
        "DTEND:20260914T190000Z\r\nEND:VEVENT\r\n"
        "BEGIN:VEVENT\r\nUID:z-2\r\nDTSTART:20260914T200000Z\r\n"
        "DTEND:20260914T190000Z\r\nEND:VEVENT"
    )
    assert parse_ics(ics) == []


def test_garbage_input_returns_nothing_rather_than_raising():
    """The feed URL is merchant-supplied; a 404 page must not take down sync."""
    for junk in ("", "not a calendar", "<html><body>404</body></html>",
                 "BEGIN:VEVENT\r\nDTSTART:garbage\r\nEND:VEVENT"):
        assert parse_ics(junk) == []


def test_unknown_tzid_falls_back_without_raising():
    ics = _wrap(
        "BEGIN:VEVENT\r\nUID:u-1\r\nDTSTART;TZID=Mars/Olympus:20260914T190000\r\n"
        "DTEND;TZID=Mars/Olympus:20260914T200000\r\nEND:VEVENT"
    )
    blocks = parse_ics(ics)
    assert len(blocks) == 1 and blocks[0].starts_at.tzinfo is not None


@pytest.mark.parametrize("value,seconds", [
    ("PT1H", 3600), ("PT30M", 1800), ("PT1H30M", 5400),
    ("P1D", 86400), ("P1W", 604800), ("PT45S", 45),
])
def test_parse_duration(value, seconds):
    assert _parse_duration(value).total_seconds() == seconds


def test_parse_duration_falls_back_on_nonsense():
    assert _parse_duration("banana").total_seconds() == 3600
