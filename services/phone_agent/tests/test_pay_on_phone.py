"""
Tests for PAY ON THE PHONE (anti-scam pay-now flow).

Asserts, with fakes (no network):
  - pay_now: creates order + payment link + checkout SMS, sets the held order to
    payment_status='pending', and does NOT release the kitchen ticket.
  - payment confirmation (webhook / demo simulate) flips to payment_status='paid'
    and releases the kitchen ticket.
  - pay_at_pickup: releases to the kitchen NOW via the parallel delivery
    fan-out (POS + customer SMS + merchant SMS legs, per-channel statuses).
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
        self.staff_sms = []      # merchant notification leg
        self.saved_rows = []     # held (pay_now) rows
        self.release_rows = []   # fan-out (pay_at_pickup) rows
        self.patched = []  # (query_or_key, patch_dict)

    def install(self, monkeypatch, *, demo=False):
        import delivery_channels as dc
        import payment_links as pl
        import sms_checkout as sc

        async def fake_create_pos_for_config(order, config, pos_result=None):
            if pos_result is not None:
                return pos_result
            self.pos_calls.append(order)
            return {"success": True, "pos_order_id": "POS-ABC-123", "pos_system": "square"}

        async def fake_create_checkout(order, config, pos_order_id=""):
            self.link_calls.append({"order": order, "pos_order_id": pos_order_id})
            return {"url": "https://sq.link/pay/xyz", "link_id": "PL-1", "method": "square"}

        async def fake_send_checkout_sms(order, payment_link, business_name, **kwargs):
            self.sms_calls.append({"link": payment_link, "phone": order.get("caller_phone")})
            return {"sent": True, "method": "twilio", "message_sid": "SM1"}

        async def fake_send_sms(to, body):
            self.staff_sms.append({"to": to, "body": body})
            return {"sent": True, "method": "twilio"}

        async def fake_save_held(order, pos_result, payment_result, sms_result, outcomes=None):
            self.saved_rows.append({
                "status": "awaiting_payment",
                "kitchen_released": False,
                "payment_status": "pending",
                "payment_link": payment_result.get("url", ""),
                "sms_sent": sms_result.get("sent", False),
                "delivery": outcomes or {},
            })
            return "row-1"

        async def fake_save_row(row):
            # pay_at_pickup fan-out row: the released-to-kitchen record.
            self.release_rows.append(row)
            self.patched.append(
                ("fanout_release", {"kitchen_released": row.get("kitchen_released", False)})
            )
            return "row-1"

        async def fake_mark_paid(merchant_id, caller_phone="", pos_order_id="", simulate=False):
            patch = {"payment_status": "paid", "status": "paid", "kitchen_released": True}
            key = pos_order_id or f"{merchant_id}|{caller_phone}"
            self.patched.append((key, patch))
            return {"released": True, "matched_by": "pos_order_id" if pos_order_id else "merchant_phone"}

        # POS + SMS primitives at the module the fan-out legs resolve them from…
        monkeypatch.setattr(dc, "create_pos_for_config", fake_create_pos_for_config)
        monkeypatch.setattr(pl, "create_checkout", fake_create_checkout)
        monkeypatch.setattr(sc, "send_checkout_sms", fake_send_checkout_sms)
        monkeypatch.setattr(sc, "send_sms", fake_send_sms)
        # …and at the names pay_on_phone bound at import time (pay_now path).
        monkeypatch.setattr(pay_on_phone, "create_checkout", fake_create_checkout)
        monkeypatch.setattr(pay_on_phone, "send_checkout_sms", fake_send_checkout_sms)
        monkeypatch.setattr(pay_on_phone, "_save_held_order", fake_save_held)
        monkeypatch.setattr(pay_on_phone, "save_order_row", fake_save_row)
        monkeypatch.setattr(dc, "save_order_row", fake_save_row)
        monkeypatch.setattr(pay_on_phone, "mark_order_paid", fake_mark_paid)
        monkeypatch.setattr(pay_on_phone, "DEMO_MERCHANT_ID", "demo-merchant")
        self._fake_pos = fake_create_pos_for_config
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
    # pay_now must NOT have written a released fan-out row
    assert all(k != "fanout_release" for k, _ in spy.patched)
    # per-channel ledger: merchant notification is HELD with the ticket
    assert row["delivery"]["merchant_sms"]["status"] in (
        "deferred_pending_payment", "skipped_no_number",
    )


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
    # demo config has sms_checkout_enabled=False → no pay link / checkout SMS
    assert spy.link_calls == []        # no pay link
    assert spy.sms_calls == []         # no checkout SMS from this path
    assert spy.saved_rows == []        # held-order row not written
    assert ("fanout_release", {"kitchen_released": True}) in spy.patched
    # fan-out ledger: POS honored the pre-created ticket, SMS legs recorded
    row = spy.release_rows[0]
    assert row["pos_delivery_status"] == "sent"
    assert row["sms_delivery_status"] == "skipped_disabled"
    assert row["pos_order_id"] == "POS-1"


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


# ─── POS PUSH AFTER PAYMENT (deferred ticket) ────────────────────────────────
def _install_pos_spy(monkeypatch, spy):
    import delivery_channels as dc

    async def fake_create_pos(order, config):
        spy.pos_calls.append(order)
        return {"success": True, "pos_order_id": "POS-DEFERRED-1", "pos_system": "square"}

    async def fake_create_pos_for_config(order, config, pos_result=None):
        if pos_result is not None:
            return pos_result
        return await fake_create_pos(order, config)

    monkeypatch.setattr(pay_on_phone, "_create_pos", fake_create_pos)
    monkeypatch.setattr(dc, "create_pos_for_config", fake_create_pos_for_config)


def _install_patch_client(monkeypatch, patches=None):
    """Stub httpx.AsyncClient so mark_order_paid's PATCH lands in `patches`
    (when given) instead of hitting Supabase."""
    class FakeResp:
        status_code = 204

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False

        async def patch(self, url, json=None, headers=None, timeout=None):
            if patches is not None:
                patches.append({"url": url, "json": json})
            return FakeResp()

    monkeypatch.setattr(pay_on_phone.httpx, "AsyncClient", FakeClient)


async def test_pay_now_defers_pos_push(monkeypatch):
    """Flag ON + no pre-created POS order → no POS call at order time; the
    held row carries no pos_order_id and the result is marked deferred."""
    spy = Spy().install(monkeypatch)
    _install_pos_spy(monkeypatch, spy)
    monkeypatch.setattr(pay_on_phone, "POS_PUSH_AFTER_PAYMENT", True)

    result = await pay_on_phone.dispatch_order(
        _order(), _cfg(mode="pay_now"), {"phone": "+15555550111"},
    )

    assert result["mode"] == "pay_now"
    assert result["released"] is False
    assert result["pos_deferred"] is True
    assert spy.pos_calls == []                                # NO POS push yet
    assert len(spy.link_calls) == 1                           # pay link still goes out
    assert spy.link_calls[0]["pos_order_id"] == ""            # link not tied to a ticket
    assert len(spy.sms_calls) == 1                            # SMS still goes out


async def test_flag_off_restores_upfront_push(monkeypatch):
    """Flag OFF → old behavior: POS order created at order time even for pay_now."""
    spy = Spy().install(monkeypatch)
    _install_pos_spy(monkeypatch, spy)
    monkeypatch.setattr(pay_on_phone, "POS_PUSH_AFTER_PAYMENT", False)

    result = await pay_on_phone.dispatch_order(
        _order(), _cfg(mode="pay_now"), {"phone": "+15555550111"},
    )

    assert result["pos_deferred"] is False
    assert len(spy.pos_calls) == 1                            # pushed up front
    assert spy.link_calls[0]["pos_order_id"] == "POS-DEFERRED-1"


async def test_pickup_pushes_pos_immediately(monkeypatch):
    """pay_at_pickup keeps today's behavior regardless of the flag."""
    spy = Spy().install(monkeypatch)
    _install_pos_spy(monkeypatch, spy)
    monkeypatch.setattr(pay_on_phone, "POS_PUSH_AFTER_PAYMENT", True)

    result = await pay_on_phone.dispatch_order(
        _order(), _cfg(mode="pay_at_pickup"), {"phone": "+15555550111"},
    )

    assert result["mode"] == "pay_at_pickup"
    assert result["released"] is True
    assert len(spy.pos_calls) == 1                            # ticket created now
    assert ("fanout_release", {"kitchen_released": True}) in spy.patched
    assert spy.release_rows[0]["pos_delivery_status"] == "sent"


async def test_mark_paid_pushes_deferred_ticket(monkeypatch):
    """Payment confirmed → the REAL mark_order_paid creates the deferred POS
    ticket and patches the row by primary key with pos_order_id + paid."""
    spy = Spy()
    _install_pos_spy(monkeypatch, spy)
    monkeypatch.setattr(pay_on_phone, "POS_PUSH_AFTER_PAYMENT", True)
    monkeypatch.setattr(pay_on_phone, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(pay_on_phone, "SUPABASE_KEY", "fake-key")

    held_row = {
        "id": "row-42", "merchant_id": "real-merchant", "customer_name": "Sam",
        "order_type": "pickup", "items": [{"name": "Cheeseburger", "quantity": 1}],
        "subtotal": 12.99, "tax": 1.69, "total": 14.68,
        "delivery_address": "", "special_requests": "",
        "caller_phone": "+15555550111", "pos_order_id": "",
        "kitchen_released": False,
        "merchant_notify_status": "deferred_pending_payment",
    }

    async def fake_fetch(query):
        return dict(held_row)
    monkeypatch.setattr(pay_on_phone, "_fetch_held_order", fake_fetch)

    import merchant_config as mc
    async def fake_get_config(merchant_id):
        return _demo_config(merchant_id)
    monkeypatch.setattr(mc, "get_merchant_config", fake_get_config)

    patches = []
    _install_patch_client(monkeypatch, patches)

    res = await pay_on_phone.mark_order_paid(
        merchant_id="real-merchant", caller_phone="+15555550111",
        method="stripe", payment_txn_id="pi_123",
    )

    assert res["released"] is True
    assert res["pos_pushed"] is True
    assert len(spy.pos_calls) == 1                            # ticket pushed on payment
    assert spy.pos_calls[0]["items"][0]["name"] == "Cheeseburger"
    assert len(patches) == 1
    assert "id=eq.row-42" in patches[0]["url"]                # patched by primary key
    p = patches[0]["json"]
    assert p["payment_status"] == "paid"
    assert p["kitchen_released"] is True
    assert p["pos_order_id"] == "POS-DEFERRED-1"
    assert p["pos_success"] is True
    # release fan-out ledger: POS pushed on payment; merchant notification
    # attempted (demo config has no transfer_number → recorded as skipped).
    assert p["pos_delivery_status"] == "sent"
    assert p["merchant_notify_status"] == "skipped_no_number"
    assert p["delivery_detail"]["pos"]["released_at_payment"] is True


async def test_mark_paid_skips_push_when_ticket_exists(monkeypatch):
    """Webhook retry / already-created ticket → no second POS order."""
    spy = Spy()
    _install_pos_spy(monkeypatch, spy)
    monkeypatch.setattr(pay_on_phone, "POS_PUSH_AFTER_PAYMENT", True)
    monkeypatch.setattr(pay_on_phone, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(pay_on_phone, "SUPABASE_KEY", "fake-key")

    async def fake_fetch(query):
        return {"id": "row-7", "merchant_id": "real-merchant",
                "caller_phone": "+15555550111", "pos_order_id": "POS-EXISTING",
                "kitchen_released": True, "merchant_notify_status": "sent"}
    monkeypatch.setattr(pay_on_phone, "_fetch_held_order", fake_fetch)

    _install_patch_client(monkeypatch)

    res = await pay_on_phone.mark_order_paid(
        merchant_id="real-merchant", pos_order_id="POS-EXISTING")

    assert res["released"] is True
    assert res["pos_pushed"] is False
    assert spy.pos_calls == []                                # idempotent — no duplicate
