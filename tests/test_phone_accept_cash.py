"""
PHONE AGENT "PAY WITH CASH" — warned opt-in, unpaid/cash-on-pickup tickets.

Pins the contract for the accept_cash feature:

  1. Config round-trip: PhoneConfigRequest carries accept_cash and
     save_phone_config persists it; merchant_config.get_merchant_config reads it
     back onto MerchantPhoneConfig.accept_cash (default False when NULL/absent).
  2. Prompt: the assistant offers CASH as a payment option ONLY when the merchant
     enabled accept_cash — the prompt is byte-for-byte unchanged when it's off.
  3. Dispatch: a cash order (pay_choice='cash', accept_cash on) reaches the
     kitchen flagged UNPAID / CASH ON PICKUP, mirrors pay_at_pickup (released
     now), and NO payment link / checkout is ever created.
  4. Kitchen ticket: build_kitchen_note prints "CASH ON PICKUP" for a cash order.
  5. Safety: pay_choice='cash' is ignored (no cash path) when accept_cash is off.

Run:  python -m pytest tests/test_phone_accept_cash.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

_PHONE_AGENT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "services", "phone_agent"))
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

import delivery_channels as dc  # noqa: E402
import merchant_config as mc  # noqa: E402
import pay_on_phone as pop  # noqa: E402
from src.api.routes.vapi_webhook import _system_prompt  # noqa: E402
from src.services.pos_connectors.clover_kitchen import build_kitchen_note  # noqa: E402

from tests.test_menu_store import MID, FakeDB, _run  # noqa: E402

SERVICE = {"kind": "service"}


# ── 1. config round-trip ─────────────────────────────────────────────────

def _patch_membership(monkeypatch):
    from src.api import auth

    async def _ok(user, org_id):
        return True
    monkeypatch.setattr(auth, "_check_org_membership", _ok)


def test_config_accept_cash_round_trips(monkeypatch):
    import src.db as db_mod
    from src.api.routes.phone_dashboard import PhoneConfigRequest, save_phone_config

    _patch_membership(monkeypatch)
    db = FakeDB({"merchant_id": MID})
    monkeypatch.setattr(db_mod, "_db_instance", db)

    req = PhoneConfigRequest(merchant_id=MID, accept_cash=True)
    _run(save_phone_config(req, principal=SERVICE))

    row = db.tables["phone_agent_config"][0]
    assert row["accept_cash"] is True


def test_config_accept_cash_defaults_off_when_absent(monkeypatch):
    import src.db as db_mod
    from src.api.routes.phone_dashboard import PhoneConfigRequest, save_phone_config

    _patch_membership(monkeypatch)
    db = FakeDB({"merchant_id": MID})
    monkeypatch.setattr(db_mod, "_db_instance", db)

    # Omitting accept_cash must leave the stored value untouched (None-skip rule).
    req = PhoneConfigRequest(merchant_id=MID, greeting="hi")
    _run(save_phone_config(req, principal=SERVICE))

    row = db.tables["phone_agent_config"][0]
    assert "accept_cash" not in row  # never written when not sent


def test_merchant_config_reads_accept_cash(monkeypatch):
    """The live config loader surfaces accept_cash (default False)."""
    # No Supabase configured → demo config path; accept_cash defaults False.
    monkeypatch.setattr(mc, "SUPABASE_URL", "")
    cfg = _run(mc.get_merchant_config("demo"))
    assert cfg.accept_cash is False


# ── 2. prompt offers cash only when enabled ──────────────────────────────

def test_prompt_offers_cash_only_when_enabled():
    config = mc._demo_config("demo")
    baseline = _system_prompt(config)
    assert "cash" not in baseline.lower()

    config.accept_cash = True
    prompt = _system_prompt(config)
    assert "cash" in prompt.lower()

    # Turning it back off restores the prompt byte-for-byte.
    config.accept_cash = False
    assert _system_prompt(config) == baseline


# ── 3. dispatch: cash → unpaid/cash-on-pickup, NO payment link ───────────

def _cfg(**kw):
    base = dict(
        merchant_id="m-cash-1",
        business_name="Cashaurant",
        payment_mode="pay_now",
        accept_cash=True,
        sms_checkout_enabled=True,
        sms_pay_template="",
        transfer_number="+15550001111",
        delivery_channels=None,
        pos_system="square",
        pos_access_token="tok",
        pos_location_id="loc",
        demo_safe=False,
        menu_items=[{"name": "Coke", "price": 3.0}],
        language="en",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _order(**kw):
    base = {
        "merchant_id": "m-cash-1",
        "business_name": "Cashaurant",
        "customer_name": "Pat",
        "order_type": "pickup",
        "items": [{"name": "Coke", "quantity": 1, "unit_price": 3.0, "line_total": 3.0}],
        "subtotal": 3.0, "tax": 0.39, "total": 3.39,
        "currency": "usd",
        "delivery_address": "", "special_requests": "",
        "caller_phone": "+15559990000",
        "pos_system": "square",
    }
    base.update(kw)
    return base


@pytest.fixture
def saved_rows(monkeypatch):
    rows: list[dict] = []

    async def _fake_save(row):
        rows.append(row)
        return "row-uuid-cash"

    monkeypatch.setattr(pop, "save_order_row", _fake_save)
    monkeypatch.setattr(dc, "save_order_row", _fake_save)
    return rows


@pytest.fixture
def payment_calls(monkeypatch):
    """A cash order must NEVER call create_checkout / send_checkout_sms.

    These blow up if invoked so the test fails loudly on any payment-link
    attempt. merchant notify SMS is stubbed as a success.
    """
    import payment_links as pl
    import sms_checkout as sc

    calls = {"merchant_sms": []}

    async def _boom_checkout(*a, **kw):  # pragma: no cover - must not run
        raise AssertionError("create_checkout must not be called for a cash order")

    async def _boom_checkout_sms(**kw):  # pragma: no cover - must not run
        raise AssertionError("send_checkout_sms must not be called for a cash order")

    async def _fake_send_sms(to, body):
        calls["merchant_sms"].append({"to": to, "body": body})
        return {"sent": True, "method": "telnyx"}

    monkeypatch.setattr(pl, "create_checkout", _boom_checkout)
    monkeypatch.setattr(sc, "send_checkout_sms", _boom_checkout_sms)
    monkeypatch.setattr(sc, "send_sms", _fake_send_sms)
    monkeypatch.setattr(pop, "create_checkout", _boom_checkout)
    monkeypatch.setattr(pop, "send_checkout_sms", _boom_checkout_sms)
    return calls


def _mock_pos(monkeypatch, result):
    async def _fake(order, config, pos_result=None):
        if pos_result is not None:
            return pos_result
        return result

    monkeypatch.setattr(dc, "create_pos_for_config", _fake)


async def test_cash_order_unpaid_kitchen_released_no_link(monkeypatch, saved_rows, payment_calls):
    _mock_pos(monkeypatch, {"success": True, "pos_order_id": "SQ-CASH", "pos_system": "square"})

    routed = await pop.dispatch_order(
        _order(), _cfg(), {"phone": "+15559990000"}, pay_choice="cash")

    assert routed["mode"] == "cash"
    assert routed["released"] is True          # ticket in the kitchen now
    assert not routed.get("payment_link")      # NO payment link
    assert routed["pos_result"]["pos_order_id"] == "SQ-CASH"

    # Persisted row: unpaid, cash, kitchen released.
    assert saved_rows, "a phone_orders row must be written"
    row = saved_rows[-1]
    assert row["kitchen_released"] is True
    assert row["payment_method"] == "cash"
    assert row["payment_status"] == "unpaid"
    assert not row.get("payment_link")


async def test_cash_ignored_when_accept_cash_off(monkeypatch, saved_rows):
    """pay_choice='cash' with accept_cash OFF must NOT take the cash path —
    it falls through to the merchant's real payment_mode (pay_now here)."""
    _mock_pos(monkeypatch, {"success": False, "method": "deferred", "pos_order_id": "", "deferred": True})

    async def _fake_checkout(order, config, pos_order_id="", **kw):
        return {"url": "https://pay.test/x", "method": "stripe"}

    async def _fake_send_checkout_sms(**kw):
        return {"sent": True, "method": "telnyx"}

    import payment_links as pl
    import sms_checkout as sc
    monkeypatch.setattr(pl, "create_checkout", _fake_checkout)
    monkeypatch.setattr(sc, "send_checkout_sms", _fake_send_checkout_sms)
    monkeypatch.setattr(pop, "create_checkout", _fake_checkout)
    monkeypatch.setattr(pop, "send_checkout_sms", _fake_send_checkout_sms)

    routed = await pop.dispatch_order(
        _order(), _cfg(accept_cash=False), {"phone": "+15559990000"}, pay_choice="cash")

    assert routed["mode"] == "pay_now"   # NOT cash — fell through to anti-scam default


# ── 4. kitchen ticket says CASH ON PICKUP ────────────────────────────────

def test_kitchen_note_cash_on_pickup():
    order = {
        "customer_name": "Pat",
        "order_type": "pickup",
        "items": [{"name": "Coke", "quantity": 1}],
        "total": 3.39,
        "currency": "usd",
        "payment_method": "cash",
    }
    note = build_kitchen_note(order, "Meridian Mobile Order")
    assert "CASH ON PICKUP" in note

    # A normal unpaid (non-cash) order keeps the existing wording.
    plain = build_kitchen_note({**order, "payment_method": ""}, "Meridian Mobile Order")
    assert "CASH ON PICKUP" not in plain
    assert "UNPAID" in plain
