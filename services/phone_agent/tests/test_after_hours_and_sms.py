"""
Tests for the after-hours gate + the staff-alert SMS (no network).

after-hours (is_open_now):
  - no business_hours          → open (never gate)
  - business_hours but no tz   → open (refuse to guess; old code mis-gated on UTC)
  - inside hours (local tz)    → open
  - outside hours / closed day → closed
  - bad tz name                → open (fail safe)

staff-alert SMS (send_sms / _send_sms_notification):
  - no gateway configured      → not sent, reason no_gateway, no raise
  - empty recipient            → no-op
  - send error                 → swallowed (order routing must not break)
"""
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import order_router  # noqa: E402
import sms_checkout  # noqa: E402
from merchant_config import is_open_now  # noqa: E402

aio = pytest.mark.asyncio

# Mon-Fri 09:00–17:00 in Toronto; weekend closed.
HOURS = {
    "monday": {"open": "09:00", "close": "17:00"},
    "tuesday": {"open": "09:00", "close": "17:00"},
    "wednesday": {"open": "09:00", "close": "17:00"},
    "thursday": {"open": "09:00", "close": "17:00"},
    "friday": {"open": "09:00", "close": "17:00"},
    "saturday": {"closed": True},
    "sunday": {"closed": True},
}
TOR = "America/Toronto"


def _at(y, mo, d, h, mi, tz=TOR):
    return datetime(y, mo, d, h, mi, tzinfo=ZoneInfo(tz))


def test_no_hours_is_open():
    assert is_open_now(None, TOR) is True
    assert is_open_now({}, TOR) is True


def test_hours_but_no_timezone_is_open():
    # Old code compared local hours to UTC and mis-gated; we refuse to guess.
    assert is_open_now(HOURS, "") is True
    assert is_open_now(HOURS, None) is True


def test_bad_timezone_fails_open():
    assert is_open_now(HOURS, "Not/AZone") is True


def test_inside_hours_open():
    # Wed 2026-06-24 12:00 local → open.
    assert is_open_now(HOURS, TOR, now=_at(2026, 6, 24, 12, 0)) is True


def test_outside_hours_closed():
    # Wed 2026-06-24 18:30 local → closed.
    assert is_open_now(HOURS, TOR, now=_at(2026, 6, 24, 18, 30)) is False
    # 08:00 before open → closed.
    assert is_open_now(HOURS, TOR, now=_at(2026, 6, 24, 8, 0)) is False


def test_closed_day():
    # Saturday 2026-06-27 12:00 → closed.
    assert is_open_now(HOURS, TOR, now=_at(2026, 6, 27, 12, 0)) is False


def test_timezone_actually_matters():
    # 23:00 UTC on Wed = 19:00 Toronto (closed). A UTC-naive check would call it
    # open (23:00 < ... no), so assert the tz conversion drives the result:
    utc_now = datetime(2026, 6, 24, 23, 0, tzinfo=ZoneInfo("UTC"))  # 19:00 Toronto
    assert is_open_now(HOURS, TOR, now=utc_now) is False
    # Same instant, Vancouver = 16:00 → open.
    assert is_open_now(HOURS, "America/Vancouver", now=utc_now) is True


@aio
async def test_send_sms_no_gateway(monkeypatch):
    monkeypatch.setattr(sms_checkout, "TWILIO_SID", "")
    monkeypatch.setattr(sms_checkout, "SUPABASE_URL", "")
    res = await sms_checkout.send_sms("+15551234567", "hi")
    assert res == {"sent": False, "method": "none", "reason": "no_gateway"}


@aio
async def test_send_sms_missing_args():
    assert (await sms_checkout.send_sms("", "body"))["sent"] is False
    assert (await sms_checkout.send_sms("+1555", ""))["sent"] is False


@aio
async def test_send_sms_uses_twilio_when_configured(monkeypatch):
    monkeypatch.setattr(sms_checkout, "TWILIO_SID", "AC1")
    monkeypatch.setattr(sms_checkout, "TWILIO_TOKEN", "tok")
    monkeypatch.setattr(sms_checkout, "TWILIO_FROM", "+15550000000")
    calls = {}

    async def fake_twilio(to, body):
        calls["to"], calls["body"] = to, body
        return {"sent": True, "method": "twilio", "message_sid": "SM1"}

    monkeypatch.setattr(sms_checkout, "_send_via_twilio", fake_twilio)
    res = await sms_checkout.send_sms("+15551234567", "order up")
    assert res["sent"] and res["method"] == "twilio"
    assert calls == {"to": "+15551234567", "body": "order up"}


@aio
async def test_staff_notification_noop_on_empty_phone():
    # Should simply return without attempting a send.
    assert await order_router._send_sms_notification("", "msg") is None


@aio
async def test_staff_notification_swallows_errors(monkeypatch):
    async def boom(to, body):
        raise RuntimeError("gateway down")

    monkeypatch.setattr(sms_checkout, "send_sms", boom)
    # Must not raise — order routing already persisted the order.
    assert await order_router._send_sms_notification("+15551234567", "msg") is None
