"""Vapi order-integrity regression tests.

Guards the same rule the Twilio path enforces (test_phone_order_integrity.py):
the Vapi agent must never read back a confirmation for an order that didn't
actually reach the merchant. Previously _place_order always called _confirm and
the tool-call/legacy exception handlers fabricated "Your order is in", so a POS
rejection, a pay_now with no pay link, or a pipeline exception all produced a
false confirmation while the order vanished.

Run:  python -m pytest tests/test_vapi_order_integrity.py -v
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

_PHONE_AGENT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "services", "phone_agent"))
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

import pytest  # noqa: E402

from src.api.routes import vapi_webhook as vw  # noqa: E402


# ─── _order_reached (pure) ───────────────────────────────────────────────────

def test_pay_now_no_link_is_not_reached():
    """pay_now with no pay link texted → order never placed → not reached."""
    assert vw._order_reached({"mode": "pay_now", "sms_sent": False}) is False


def test_pay_now_link_texted_is_reached():
    assert vw._order_reached({"mode": "pay_now", "sms_sent": True}) is True


def test_pay_now_demo_simulated_is_reached():
    assert vw._order_reached(
        {"mode": "pay_now", "sms_sent": False, "simulated_paid": True}) is True


def test_pay_at_pickup_pos_failed_and_no_staff_sms_is_not_reached():
    """POS push failed AND merchant notification failed → kitchen never sees it."""
    routed = {
        "mode": "pay_at_pickup",
        "delivery": {
            "pos": {"status": "failed"},
            "merchant_sms": {"status": "failed"},
        },
    }
    assert vw._order_reached(routed) is False


def test_pay_at_pickup_pos_sent_is_reached():
    routed = {"mode": "pay_at_pickup", "delivery": {"pos": {"status": "sent"}}}
    assert vw._order_reached(routed) is True


def test_pay_at_pickup_pos_failed_but_staff_sms_sent_is_reached():
    """POS down but staff still got the SMS → merchant knows → reached."""
    routed = {
        "mode": "pay_at_pickup",
        "delivery": {
            "pos": {"status": "failed"},
            "merchant_sms": {"status": "sent"},
        },
    }
    assert vw._order_reached(routed) is True


def test_demo_safe_pos_is_reached():
    """demo_safe is a guarded/logs-only merchant, not a failure."""
    routed = {"mode": "cash", "delivery": {"pos": {"status": "demo_safe"}}}
    assert vw._order_reached(routed) is True


# ─── _place_order (gate wired) ───────────────────────────────────────────────

class _Cfg:
    merchant_id = "biz_test"
    business_name = "Test Diner"


@pytest.mark.asyncio
async def test_place_order_apologizes_when_not_reached(monkeypatch):
    """A POS reject with no staff SMS must yield an honest apology, never a
    fabricated 'Your order is in'."""
    import order_normalizer
    import pay_on_phone

    monkeypatch.setattr(
        order_normalizer, "normalize_order",
        lambda args, config: {"items": [{"name": "Pizza", "quantity": 1}],
                              "is_empty": False, "unavailable_items": []},
    )

    async def _fake_dispatch(order, config, caller_info, pay_choice=""):
        return {
            "mode": "pay_at_pickup",
            "delivery": {"pos": {"status": "failed"},
                         "merchant_sms": {"status": "failed"}},
            "pos_result": {"success": False},
            "sms_sent": False,
        }

    monkeypatch.setattr(pay_on_phone, "dispatch_order", _fake_dispatch)

    out = await vw._place_order({"items": [{"name": "Pizza", "quantity": 1}]},
                                _Cfg(), "+15551234567")
    assert "is in" not in out.lower()
    assert "sorry" in out.lower()


@pytest.mark.asyncio
async def test_place_order_confirms_when_reached(monkeypatch):
    import order_normalizer
    import pay_on_phone

    monkeypatch.setattr(
        order_normalizer, "normalize_order",
        lambda args, config: {"items": [{"name": "Pizza", "quantity": 1}],
                              "is_empty": False, "unavailable_items": []},
    )

    async def _fake_dispatch(order, config, caller_info, pay_choice=""):
        return {
            "mode": "pay_at_pickup",
            "delivery": {"pos": {"status": "sent"}},
            "pos_result": {"success": True},
            "sms_sent": False,
        }

    monkeypatch.setattr(pay_on_phone, "dispatch_order", _fake_dispatch)

    out = await vw._place_order({"items": [{"name": "Pizza", "quantity": 1}],
                                 "customer_name": "Sam"},
                                _Cfg(), "+15551234567")
    assert "sorry" not in out.lower()
    assert "is in" in out.lower()
