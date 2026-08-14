"""Outbound .ics feed and the reminder sweep.

Run:
    python -m pytest tests/test_booking_feed_and_reminders.py -v

The feed tests assert RFC 5545 mechanics that calendar clients are strict
about (CRLF, line folding, escaping, stable UIDs). The reminder tests assert
idempotency, which is the property that decides whether a customer gets one
text or four.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.services import booking_reminders as br  # noqa: E402
from src.services.booking_feed import (  # noqa: E402
    build_ics,
    generate_feed_token,
    _fold,
)
from src.services.booking_providers.ics_feed import parse_ics  # noqa: E402


def _booking(**over):
    base = {
        "id": "11111111-1111-1111-1111-111111111111",
        "starts_at": "2026-09-14T23:00:00+00:00",
        "ends_at": "2026-09-15T00:30:00+00:00",
        "customer_name": "Dana Reid",
        "customer_phone": "+15551234567",
        "party_size": 4,
        "confirmation_code": "AB2C3D",
        "status": "confirmed",
        "notes": "",
    }
    base.update(over)
    return base


# ─── Outbound feed ────────────────────────────────────────────

def test_feed_is_a_valid_calendar_our_own_parser_reads_back():
    """Round-trip through the reader proves the writer emits real iCalendar."""
    ics = build_ics("Maple Tandoor", [_booking()])
    blocks = parse_ics(ics)
    assert len(blocks) == 1
    assert blocks[0].starts_at == datetime(2026, 9, 14, 23, 0, tzinfo=timezone.utc)
    assert blocks[0].ends_at == datetime(2026, 9, 15, 0, 30, tzinfo=timezone.utc)


def test_feed_uses_crlf_line_endings():
    """RFC 5545 requires CRLF; bare LF makes strict clients reject the file."""
    ics = build_ics("Shop", [_booking()])
    assert "\r\n" in ics
    assert "\n" not in ics.replace("\r\n", "")


def test_party_size_appears_in_the_title():
    ics = build_ics("Shop", [_booking(party_size=4)])
    assert "Dana Reid (party of 4)" in ics
    solo = build_ics("Shop", [_booking(party_size=1)])
    assert "party of" not in solo


def test_uid_is_stable_across_rebuilds():
    """An unstable UID makes every refresh duplicate the event in the
    merchant's calendar instead of updating it."""
    first = build_ics("Shop", [_booking()])
    second = build_ics("Shop", [_booking()])
    uid_line = [ln for ln in first.split("\r\n") if ln.startswith("UID:")][0]
    assert uid_line in second
    assert "11111111-1111-1111-1111-111111111111" in uid_line


def test_cancelled_bookings_are_published_as_cancelled():
    """The merchant's calendar must learn about the cancellation, or the table
    looks held all evening."""
    ics = build_ics("Shop", [_booking(status="cancelled")])
    assert "STATUS:CANCELLED" in ics
    # And our own reader must then treat it as free.
    assert parse_ics(ics) == []


def test_special_characters_are_escaped():
    ics = build_ics("Shop", [_booking(
        customer_name="O'Neil, Sam", notes="Allergy; nuts\nBack door")])
    assert "\\," in ics
    assert "\\;" in ics
    assert "\\n" in ics


def test_long_lines_are_folded_to_75_octets():
    long_note = "x" * 400
    ics = build_ics("Shop", [_booking(notes=long_note)])
    for line in ics.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75, f"unfolded line: {line[:80]}"


def test_folded_content_survives_a_round_trip():
    ics = build_ics("Shop", [_booking(customer_name="A" * 120)])
    assert parse_ics(ics)[0].summary.startswith("A" * 100)


def test_fold_leaves_short_lines_alone():
    assert _fold("SUMMARY:short") == "SUMMARY:short"


def test_unicode_is_not_split_mid_character():
    """Folding counts octets, so a naive split can cut a multi-byte character
    in half and produce invalid UTF-8."""
    ics = build_ics("Café Ñoño", [_booking(customer_name="日本語のなまえ" * 12)])
    assert ics.encode("utf-8").decode("utf-8")
    for line in ics.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75


def test_empty_booking_list_still_produces_a_valid_calendar():
    ics = build_ics("Shop", [])
    assert ics.startswith("BEGIN:VCALENDAR")
    assert ics.rstrip().endswith("END:VCALENDAR")
    assert parse_ics(ics) == []


def test_malformed_rows_are_skipped_not_fatal():
    ics = build_ics("Shop", [_booking(starts_at=None), _booking()])
    assert len(parse_ics(ics)) == 1


def test_feed_token_is_32_hex_chars_and_unique():
    tokens = {generate_feed_token() for _ in range(200)}
    assert len(tokens) == 200
    for t in tokens:
        assert len(t) == 32 and all(c in "0123456789abcdef" for c in t)


# ─── Reminder sweep ───────────────────────────────────────────

class StubStore:
    """Mirrors the real query: window-filtered AND marker-filtered.

    Both filters matter. Without the window, one booking is returned by the
    24-hour pass AND the 2-hour pass in the same sweep, which is not what the
    database does and would hide the very double-send these tests exist to
    catch.
    """

    def __init__(self, due):
        self._due = due
        self.marked: list[tuple[str, str]] = []

    async def due_for_reminder(self, start_iso, end_iso, column):
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
        already = {m[0] for m in self.marked if m[1] == column}
        out = []
        for b in self._due:
            if b.get(column) is not None or str(b["id"]) in already:
                continue
            starts_at = datetime.fromisoformat(b["starts_at"])
            if start <= starts_at <= end:
                out.append(b)
        return out

    async def mark_reminder_sent(self, booking_id, column):
        self.marked.append((str(booking_id), column))


@pytest.fixture
def sms(monkeypatch):
    sent: list[tuple[str, str]] = []

    async def _send(phone, message):
        sent.append((phone, message))
        return {"sent": True, "method": "telnyx", "message_id": "m1"}

    import src.sms.client as client
    monkeypatch.setattr(client, "send_sms", _send)

    async def _info(ids):
        return {"m1": {"name": "Maple Tandoor", "tz": "America/Toronto"}}

    monkeypatch.setattr(br, "_merchant_info", _info)
    return sent


@pytest.mark.asyncio
async def test_sends_one_text_per_booking_and_marks_it(monkeypatch, sms):
    row = _booking(merchant_id="m1", reminder_24h_sent_at=None,
                   reminder_2h_sent_at=None)
    # starts_at 24h out so only the 24h pass matches.
    now = datetime(2026, 9, 13, 23, 0, tzinfo=timezone.utc)
    store = StubStore([row])
    monkeypatch.setattr(br, "get_booking_store", lambda: store)

    result = await br.run_reminder_sweep(now=now)

    assert result["sent"] == 1
    assert len(sms) == 1
    assert sms[0][0] == "+15551234567"
    assert ("11111111-1111-1111-1111-111111111111",
            "reminder_24h_sent_at") in store.marked


@pytest.mark.asyncio
async def test_a_second_sweep_does_not_text_again(monkeypatch, sms):
    """Idempotency: a beat that fires twice must not double-text a customer."""
    row = _booking(merchant_id="m1", reminder_24h_sent_at=None,
                   reminder_2h_sent_at=None)
    now = datetime(2026, 9, 13, 23, 0, tzinfo=timezone.utc)
    store = StubStore([row])
    monkeypatch.setattr(br, "get_booking_store", lambda: store)

    await br.run_reminder_sweep(now=now)
    await br.run_reminder_sweep(now=now)

    assert len(sms) == 1


@pytest.mark.asyncio
async def test_a_failed_send_is_left_unmarked_for_retry(monkeypatch):
    """The opposite trade from double-texting: a failure must NOT burn the
    marker, or the customer silently never gets a reminder."""
    async def _fail(phone, message):
        return {"sent": False, "reason": "status_500"}

    import src.sms.client as client
    monkeypatch.setattr(client, "send_sms", _fail)

    async def _info(ids):
        return {"m1": {"name": "Shop", "tz": "America/Toronto"}}

    monkeypatch.setattr(br, "_merchant_info", _info)

    row = _booking(merchant_id="m1", reminder_24h_sent_at=None,
                   reminder_2h_sent_at=None)
    now = datetime(2026, 9, 13, 23, 0, tzinfo=timezone.utc)
    store = StubStore([row])
    monkeypatch.setattr(br, "get_booking_store", lambda: store)

    result = await br.run_reminder_sweep(now=now)
    assert result["failed"] == 1
    assert store.marked == []


@pytest.mark.asyncio
async def test_booking_without_a_phone_is_marked_not_retried_forever(
        monkeypatch, sms):
    row = _booking(merchant_id="m1", customer_phone=None,
                   reminder_24h_sent_at=None, reminder_2h_sent_at=None)
    now = datetime(2026, 9, 13, 23, 0, tzinfo=timezone.utc)
    store = StubStore([row])
    monkeypatch.setattr(br, "get_booking_store", lambda: store)

    result = await br.run_reminder_sweep(now=now)
    assert result["skipped"] == 1 and sms == []
    assert store.marked, "must be marked so the sweep stops re-examining it"


def test_reminder_copy_uses_local_time_and_names_the_business():
    body = br._compose("Maple Tandoor", _booking(), "America/Toronto", 24)
    assert "Maple Tandoor" in body
    assert "7 PM" in body, "23:00 UTC is 7 PM in Toronto in September"
    assert "Dana" in body
    assert "AB2C3D" in body
    assert "tomorrow" in body


def test_two_hour_reminder_says_today_not_tomorrow():
    body = br._compose("Shop", _booking(), "America/Toronto", 2)
    assert "today" in body and "tomorrow" not in body
