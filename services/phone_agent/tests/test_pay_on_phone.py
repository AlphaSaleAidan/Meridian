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


async def test_pay_at_pickup_checkout_carries_pos_order_id(monkeypatch):
    """P1 regression (post-#332): with checkout SMS enabled, the pay-at-pickup
    checkout link is created AFTER the POS leg and carries its pos_order_id —
    Stripe webhook matching stays precise instead of merchant+phone-latest."""
    spy = Spy().install(monkeypatch)
    cfg = replace(_cfg("real-merchant", "pay_at_pickup"), sms_checkout_enabled=True)

    result = await pay_on_phone.dispatch_order(_order(), cfg, {"phone": "+15555550111"})

    assert result["mode"] == "pay_at_pickup"
    assert result["released"] is True
    assert len(spy.link_calls) == 1
    assert spy.link_calls[0]["pos_order_id"] == "POS-ABC-123"   # real id, not ""
    row = spy.release_rows[0]
    assert row["pos_order_id"] == "POS-ABC-123"
    assert row["sms_delivery_status"] == "sent"


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


def _row_id_from_url(url: str) -> str:
    return url.split("id=eq.")[1].split("&")[0] if "id=eq." in url else "row"


def _install_patch_client(monkeypatch, patches=None):
    """Stub httpx.AsyncClient so mark_order_paid's PATCHes land in `patches`
    (when given) instead of hitting Supabase. The CAS claim (url carries
    status=neq.paid) echoes a representation row so the flip 'matches'."""
    class FakeResp:
        def __init__(self, code=204, rows=None):
            self.status_code = code
            self._rows = rows or []
            self.content = b"x" if rows else b""
        def json(self): return self._rows

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False

        async def patch(self, url, json=None, headers=None, timeout=None):
            if patches is not None:
                patches.append({"url": url, "json": json})
            if "status=neq.paid" in url:  # the CAS claim → matched one row
                return FakeResp(200, [{"id": _row_id_from_url(url)}])
            return FakeResp(204)

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

    async def fake_fetch_list(query):
        return [dict(held_row)]
    monkeypatch.setattr(pay_on_phone, "_fetch_orders", fake_fetch_list)

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
    # CLAIM-THEN-FANOUT: the CAS claim (status=neq.paid) flips paid/kitchen
    # first and gates the fan-out; the pos ids + telemetry land in the
    # best-effort post-claim PATCH so a column 400 can't un-commit the money.
    assert len(patches) == 2
    assert "id=eq.row-42" in patches[0]["url"]                # claim by primary key
    assert "status=neq.paid" in patches[0]["url"]             # ...guarded (CAS)
    p = patches[0]["json"]
    assert p["payment_status"] == "paid"
    assert p["kitchen_released"] is True
    # the CLAIM carries NO pos ids / fan-out telemetry (those come post-claim)
    assert "pos_order_id" not in p
    assert "pos_delivery_status" not in p
    assert "merchant_notify_status" not in p
    assert "delivery_detail" not in p
    # post-claim PATCH: POS pushed on payment; merchant notification attempted
    # (demo config has no transfer_number → recorded as skipped).
    assert "id=eq.row-42" in patches[1]["url"]
    t = patches[1]["json"]
    assert "payment_status" not in t                          # post-claim only
    assert t["pos_order_id"] == "POS-DEFERRED-1"
    assert t["pos_success"] is True
    assert t["pos_delivery_status"] == "sent"
    assert t["merchant_notify_status"] == "skipped_no_number"
    assert t["delivery_detail"]["pos"]["released_at_payment"] is True


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


# ─── Repeat-caller: pay the RIGHT open order (amount disambiguation) ──────────

async def test_two_open_orders_matched_by_paid_amount(monkeypatch):
    """A caller with two open orders ($30 and $12) pays $30 → the $30 order is
    the one marked paid, not blindly the latest (which was the $12)."""
    monkeypatch.setattr(pay_on_phone, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(pay_on_phone, "SUPABASE_KEY", "fake-key")
    monkeypatch.setattr(pay_on_phone, "POS_PUSH_AFTER_PAYMENT", False)

    order_12 = {"id": "row-12", "merchant_id": "m1", "caller_phone": "+15555550111",
                "total": 12.00, "kitchen_released": False, "payment_status": "pending",
                "status": "awaiting_payment", "items": []}
    order_30 = {"id": "row-30", "merchant_id": "m1", "caller_phone": "+15555550111",
                "total": 30.00, "kitchen_released": False, "payment_status": "pending",
                "status": "awaiting_payment", "items": []}

    async def fake_fetch_list(query):
        return [dict(order_12), dict(order_30)]  # created_at.desc → $12 latest
    monkeypatch.setattr(pay_on_phone, "_fetch_orders", fake_fetch_list)

    claimed = {}
    async def fake_claim(row_id, patch):
        claimed["row_id"] = row_id
        return [{"id": row_id}]  # CAS matched
    monkeypatch.setattr(pay_on_phone, "_claim_order_paid", fake_claim)

    # $30 order + a small surcharge that rode the Stripe charge.
    res = await pay_on_phone.mark_order_paid(
        merchant_id="m1", caller_phone="+15555550111", paid_amount_cents=3130,
    )
    assert res["matched_by"] == "merchant_phone_amount"
    assert claimed["row_id"] == "row-30"  # NOT the latest ($12) row


async def test_already_paid_order_excluded_from_match(monkeypatch):
    """A finalized (paid) order is never re-matched — the open one wins even
    without an amount to disambiguate."""
    monkeypatch.setattr(pay_on_phone, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(pay_on_phone, "SUPABASE_KEY", "fake-key")
    monkeypatch.setattr(pay_on_phone, "POS_PUSH_AFTER_PAYMENT", False)

    paid = {"id": "row-paid", "merchant_id": "m1", "caller_phone": "+1555",
            "total": 20.0, "kitchen_released": True, "payment_status": "paid",
            "status": "paid", "items": []}
    open_row = {"id": "row-open", "merchant_id": "m1", "caller_phone": "+1555",
                "total": 20.0, "kitchen_released": False, "payment_status": "pending",
                "status": "awaiting_payment", "items": []}

    async def fake_fetch_list(query):
        return [dict(paid), dict(open_row)]  # paid is "latest"
    monkeypatch.setattr(pay_on_phone, "_fetch_orders", fake_fetch_list)

    claimed = {}
    async def fake_claim(row_id, patch):
        claimed["row_id"] = row_id
        return [{"id": row_id}]  # CAS matched
    monkeypatch.setattr(pay_on_phone, "_claim_order_paid", fake_claim)

    await pay_on_phone.mark_order_paid(merchant_id="m1", caller_phone="+1555")
    assert claimed["row_id"] == "row-open"  # the finalized row is skipped


# ─── PATCH split: paid flag isolated from fan-out telemetry ──────────────────

def _held_row():
    return {
        "id": "row-42", "merchant_id": "real-merchant", "customer_name": "Sam",
        "order_type": "pickup", "items": [{"name": "Cheeseburger", "quantity": 1}],
        "subtotal": 12.99, "tax": 1.69, "total": 14.68,
        "delivery_address": "", "special_requests": "",
        "caller_phone": "+15555550111", "pos_order_id": "",
        "kitchen_released": False,
        "merchant_notify_status": "deferred_pending_payment",
    }


def _install_release_env(monkeypatch, spy):
    """Common mark_order_paid release fixture: deferred POS + held row + config."""
    _install_pos_spy(monkeypatch, spy)
    monkeypatch.setattr(pay_on_phone, "POS_PUSH_AFTER_PAYMENT", True)
    monkeypatch.setattr(pay_on_phone, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(pay_on_phone, "SUPABASE_KEY", "fake-key")

    async def fake_fetch(query):
        return _held_row()
    monkeypatch.setattr(pay_on_phone, "_fetch_held_order", fake_fetch)

    async def fake_fetch_list(query):
        return [_held_row()]
    monkeypatch.setattr(pay_on_phone, "_fetch_orders", fake_fetch_list)

    import merchant_config as mc
    async def fake_get_config(merchant_id):
        return _demo_config(merchant_id)
    monkeypatch.setattr(mc, "get_merchant_config", fake_get_config)


def _install_scripted_patch_client(monkeypatch, patches, fail_when):
    """PATCH client that fails (400) any request matching `fail_when(json)`.
    The CAS claim (status=neq.paid) still honors fail_when, else echoes a matched
    representation row so the release fan-out proceeds."""
    class FakeResp:
        def __init__(self, code, text="", rows=None):
            self.status_code = code
            self.text = text
            self._rows = rows or []
            self.content = b"x" if rows else b""
        def json(self): return self._rows

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False

        async def patch(self, url, json=None, headers=None, timeout=None):
            patches.append({"url": url, "json": json})
            if fail_when(json or {}):
                return FakeResp(400, 'column "does_not_exist" of relation "phone_orders"')
            if "status=neq.paid" in url:  # the CAS claim → matched one row
                return FakeResp(200, rows=[{"id": _row_id_from_url(url)}])
            return FakeResp(204)

    monkeypatch.setattr(pay_on_phone.httpx, "AsyncClient", FakeClient)


async def test_telemetry_patch_failure_never_blocks_kitchen_release(monkeypatch):
    """Hardening: the telemetry PATCH (fan-out ledger columns) failing with a
    400 is logged and swallowed — the paid/kitchen_released PATCH already
    committed and the release is reported as successful."""
    spy = Spy()
    _install_release_env(monkeypatch, spy)
    patches: list[dict] = []
    _install_scripted_patch_client(
        monkeypatch, patches,
        fail_when=lambda body: "delivery_detail" in body,   # telemetry PATCH only
    )

    res = await pay_on_phone.mark_order_paid(
        merchant_id="real-merchant", caller_phone="+15555550111", method="stripe",
    )

    assert res["released"] is True                          # NOT held hostage
    assert res["pos_pushed"] is True
    assert len(patches) == 2                                # both attempted
    assert patches[0]["json"]["payment_status"] == "paid"   # critical committed first
    assert patches[0]["json"]["kitchen_released"] is True
    assert "delivery_detail" in patches[1]["json"]          # telemetry tried + failed


async def test_duplicate_event_loses_cas_and_skips_fanout(monkeypatch):
    """The whole point of the CAS: a SECOND payment event for the same order
    (Square payment.created + payment.updated, or a Stripe retry) finds the row
    already paid, the claim matches zero rows, and the release fan-out (POS push
    + merchant SMS) does NOT run again — no double kitchen ticket."""
    spy = Spy()
    _install_release_env(monkeypatch, spy)  # sets POS_PUSH_AFTER_PAYMENT, held row, config

    # Claim returns [] → another worker/event already paid this order.
    async def fake_claim(row_id, patch):
        return []
    monkeypatch.setattr(pay_on_phone, "_claim_order_paid", fake_claim)

    res = await pay_on_phone.mark_order_paid(
        merchant_id="real-merchant", caller_phone="+15555550111", method="stripe",
    )

    assert res["released"] is False
    assert res.get("duplicate") is True
    assert spy.pos_calls == []          # NO second POS push
    assert spy.sms_calls == []          # NO second merchant SMS


async def test_cas_claim_guards_on_status_neq_paid(monkeypatch):
    """The claim PATCH must carry the status<>paid guard in its URL (the CAS
    gate) — without it, concurrent events double-release."""
    monkeypatch.setattr(pay_on_phone, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(pay_on_phone, "SUPABASE_KEY", "fake-key")
    seen = {}

    class _Resp:
        status_code = 200
        content = b"x"
        def json(self): return [{"id": "row-1"}]

    class _Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def patch(self, url, json=None, headers=None, timeout=None):
            seen["url"] = url
            seen["prefer"] = (headers or {}).get("Prefer")
            return _Resp()

    monkeypatch.setattr(pay_on_phone.httpx, "AsyncClient", _Client)
    rows = await pay_on_phone._claim_order_paid("row-1", {"status": "paid"})
    assert rows == [{"id": "row-1"}]
    assert "status=neq.paid" in seen["url"]
    assert seen["prefer"] == "return=representation"


async def test_critical_patch_failure_reports_not_released(monkeypatch):
    """Converse guard: a 400 on the CRITICAL paid-flag PATCH is a real failure
    — released=False, and the telemetry PATCH is not even attempted."""
    spy = Spy()
    _install_release_env(monkeypatch, spy)
    patches: list[dict] = []
    _install_scripted_patch_client(
        monkeypatch, patches,
        fail_when=lambda body: "payment_status" in body,    # critical PATCH
    )

    res = await pay_on_phone.mark_order_paid(
        merchant_id="real-merchant", caller_phone="+15555550111",
    )

    assert res["released"] is False
    assert len(patches) == 1                                # stopped at the critical PATCH
