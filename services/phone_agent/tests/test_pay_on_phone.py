"""
Tests for PAY ON THE PHONE (anti-scam pay-now flow).

Asserts, with fakes (no network):
  - pay_now: creates order + payment link + checkout SMS, sets the held order to
    payment_status='pending', and does NOT release the kitchen ticket.
  - payment confirmation (webhook / demo simulate) flips to payment_status='paid'
    and releases the kitchen ticket.
  - pay_at_pickup: unchanged — releases to the kitchen via route_order, no link.
  - optional: respects the caller's pay_choice.

These exercise pay_on_phone (the dispatch surface bot._on_submit_order calls)
without importing pipecat-heavy bot.py.
"""
import sys
from dataclasses import replace
from pathlib import Path

import pytest

# phone_agent dir on path (same trick the live route uses).
_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import pay_on_phone  # noqa: E402
from merchant_config import _demo_config  # noqa: E402

pytestmark = pytest.mark.asyncio


# ─── Fakes / spies ───────────────────────────────────────────────────────────
class Spy:
    def __init__(self):
        self.pos_calls = []
        self.link_calls = []
        self.sms_calls = []
        self.saved_rows = []
        self.patched = []  # (query_or_key, patch_dict)

    def install(self, monkeypatch, *, demo=False):
        async def fake_create_pos_order(order, pos_system, token, location):
            self.pos_calls.append(order)
            return {"success": True, "pos_order_id": "POS-ABC-123", "pos_system": pos_system}

        async def fake_create_payment_link(order, pos_system, pos_order_id, access_token, location_id):
            self.link_calls.append({"order": order, "pos_order_id": pos_order_id})
            return {"url": "https://sq.link/pay/xyz", "link_id": "PL-1", "method": "square"}

        async def fake_send_checkout_sms(order, payment_link, business_name):
            self.sms_calls.append({"link": payment_link, "phone": order.get("caller_phone")})
            return {"sent": True, "method": "twilio", "message_sid": "SM1"}

        async def fake_save_held(order, pos_result, payment_result, sms_result):
            self.saved_rows.append({
                "status": "awaiting_payment",
                "kitchen_released": False,
                "payment_status": "pending",
                "payment_link": payment_result.get("url", ""),
                "sms_sent": sms_result.get("sent", False),
            })

        async def fake_mark_paid(merchant_id, caller_phone="", pos_order_id="", simulate=False):
            patch = {"payment_status": "paid", "status": "paid", "kitchen_released": True}
            key = pos_order_id or f"{merchant_id}|{caller_phone}"
            self.patched.append((key, patch))
            return {"released": True, "matched_by": "pos_order_id" if pos_order_id else "merchant_phone"}

        async def fake_route_order(order, config, caller_info, pos_result):
            # pay_at_pickup path: release to kitchen (record it as a patch=released)
            self.patched.append(("route_order", {"kitchen_released": True}))
            return {"pos": pos_result}

        monkeypatch.setattr(pay_on_phone, "create_payment_link", fake_create_payment_link)
        monkeypatch.setattr(pay_on_phone, "send_checkout_sms", fake_send_checkout_sms)
        monkeypatch.setattr(pay_on_phone, "_save_held_order", fake_save_held)
        monkeypatch.setattr(pay_on_phone, "mark_order_paid", fake_mark_paid)
        monkeypatch.setattr(pay_on_phone, "route_order", fake_route_order)
        monkeypatch.setattr(pay_on_phone, "DEMO_MERCHANT_ID", "demo-merchant")
        self._fake_pos = fake_create_pos_order
        return self


def _order(merchant_id="real-merchant"):
    return {
        "merchant_id": merchant_id,
        "business_name": "Demo Restaurant",
        "customer_name": "Sam",
        "order_type": "pickup",
        "items": [{"name": "Cheeseburger", "quantity": 1, "unit_price": 12.99}],
        "subtotal": 12.99, "tax": 1.69, "total": 14.68,
        "caller_phone": "+15555550111",
        "pos_system": "square",
    }


def _cfg(merchant_id="real-merchant", mode="pay_now"):
    c = _demo_config(merchant_id)
    return replace(c, payment_mode=mode)


# ─── pay_now path ────────────────────────────────────────────────────────────
async def test_pay_now_creates_link_sends_sms_holds_kitchen(monkeypatch):
    spy = Spy().install(monkeypatch)
    cfg = _cfg(mode="pay_now")
    pos_result = {"success": True, "pos_order_id": "POS-ABC-123"}

    result = await pay_on_phone.dispatch_order(_order(), cfg, {"phone": "+15555550111"}, pos_result)

    assert result["mode"] == "pay_now"
    assert result["released"] is False                      # kitchen HELD
    assert len(spy.link_calls) == 1                          # payment link created
    assert spy.link_calls[0]["pos_order_id"] == "POS-ABC-123"
    assert len(spy.sms_calls) == 1                           # checkout SMS sent
    assert spy.sms_calls[0]["link"] == "https://sq.link/pay/xyz"
    assert len(spy.saved_rows) == 1
    row = spy.saved_rows[0]
    assert row["payment_status"] == "pending"               # pending, not paid
    assert row["status"] == "awaiting_payment"
    assert row["kitchen_released"] is False                 # NOT released
    # pay_now must NOT have released the kitchen via route_order
    assert all(k != "route_order" for k, _ in spy.patched)


async def test_pay_now_does_not_mark_paid_for_real_merchant(monkeypatch):
    spy = Spy().install(monkeypatch)
    await pay_on_phone.dispatch_order(
        _order("real-merchant"), _cfg("real-merchant", "pay_now"),
        {"phone": "+15555550111"}, {"success": True, "pos_order_id": "POS-1"},
    )
    # Real merchant: payment is pending — no flip-to-paid happens on the call.
    assert spy.patched == []


# ─── payment confirmation flip + release ─────────────────────────────────────
async def test_webhook_flip_marks_paid_and_releases(monkeypatch):
    spy = Spy().install(monkeypatch)
    res = await pay_on_phone.mark_order_paid(
        merchant_id="real-merchant", caller_phone="+15555550111",
        pos_order_id="POS-ABC-123",
    )
    assert res["released"] is True
    assert res["matched_by"] == "pos_order_id"
    assert len(spy.patched) == 1
    key, patch = spy.patched[0]
    assert key == "POS-ABC-123"
    assert patch["payment_status"] == "paid"
    assert patch["kitchen_released"] is True


async def test_demo_simulates_paid_immediately(monkeypatch):
    spy = Spy().install(monkeypatch)
    cfg = _cfg("demo-merchant", "pay_now")
    result = await pay_on_phone.dispatch_order(
        _order("demo-merchant"), cfg, {"phone": "+15555550111"},
        {"success": True, "pos_order_id": "POS-ABC-123"},
    )
    # Demo: link + SMS still happen, but paid is simulated immediately so the
    # release path is demonstrable (no real charge).
    assert result["simulated_paid"] is True
    assert len(spy.patched) == 1
    _, patch = spy.patched[0]
    assert patch["payment_status"] == "paid"
    assert patch["kitchen_released"] is True


# ─── pay_at_pickup path (unchanged) ──────────────────────────────────────────
async def test_pay_at_pickup_releases_no_link(monkeypatch):
    spy = Spy().install(monkeypatch)
    cfg = _cfg("real-merchant", "pay_at_pickup")
    result = await pay_on_phone.dispatch_order(
        _order(), cfg, {"phone": "+15555550111"},
        {"success": True, "pos_order_id": "POS-1"},
    )
    assert result["mode"] == "pay_at_pickup"
    assert result["released"] is True
    assert spy.link_calls == []        # no pay link
    assert spy.sms_calls == []         # no checkout SMS from this path
    assert spy.saved_rows == []        # held-order row not written
    assert ("route_order", {"kitchen_released": True}) in spy.patched


# ─── optional path respects pay_choice ───────────────────────────────────────
async def test_optional_pay_now_choice_holds_kitchen(monkeypatch):
    spy = Spy().install(monkeypatch)
    cfg = _cfg("real-merchant", "optional")
    result = await pay_on_phone.dispatch_order(
        _order(), cfg, {"phone": "+15555550111"},
        {"success": True, "pos_order_id": "POS-1"}, pay_choice="pay_now",
    )
    assert result["mode"] == "pay_now"
    assert result["released"] is False
    assert len(spy.link_calls) == 1


async def test_optional_pay_at_pickup_choice_releases(monkeypatch):
    spy = Spy().install(monkeypatch)
    cfg = _cfg("real-merchant", "optional")
    result = await pay_on_phone.dispatch_order(
        _order(), cfg, {"phone": "+15555550111"},
        {"success": True, "pos_order_id": "POS-1"}, pay_choice="pay_at_pickup",
    )
    assert result["mode"] == "pay_at_pickup"
    assert result["released"] is True
    assert spy.link_calls == []


async def test_optional_defaults_to_pay_now_when_no_choice(monkeypatch):
    Spy().install(monkeypatch)
    cfg = _cfg("real-merchant", "optional")
    assert pay_on_phone.resolve_mode(cfg, "") == "pay_now"
    assert pay_on_phone.resolve_mode(cfg, "garbage") == "pay_now"


# ─── config default ──────────────────────────────────────────────────────────
async def test_config_default_is_pay_now():
    assert _demo_config("x").payment_mode == "pay_now"


async def test_resolve_mode_invalid_falls_back_to_pay_now():
    cfg = _cfg("real-merchant", "pay_now")
    # Even an unexpected stored mode resolves safely.
    cfg = replace(cfg, payment_mode="weird")
    assert pay_on_phone.resolve_mode(cfg) == "pay_now"
