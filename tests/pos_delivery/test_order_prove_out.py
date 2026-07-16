"""
ORDER DELIVERY FAN-OUT + KITCHEN PROVE-OUT — integration harness (no live calls).

Pins the contract of the parallel dispatch path and the Square fulfillment
verifier:

  1. pay_at_pickup fan-out: POS + customer SMS + merchant SMS all fire and all
     three outcomes land on the phone_orders row.
  2. POS failure is isolated: the SMS legs still send, and the POS error is
     recorded (never either/or, never silent).
  3. A leg that RAISES is contained (exception isolation) — siblings still run.
  4. pay_now keeps the anti-scam deferral: pos_delivery_status =
     'deferred_pending_payment', merchant notify deferred with it.
  5. delivery_channels JSONB toggles disable individual legs.
  6. Square poll: state OPEN + line items ⇒ confirmed ⇒
     fulfillment_confirmed_at recorded; non-Square POSes report 'unsupported'.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PHONE_AGENT_DIR = str(_ROOT / "services" / "phone_agent")
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

import delivery_channels as dc  # noqa: E402
import pay_on_phone as pop  # noqa: E402


def _cfg(**kw):
    base = dict(
        merchant_id="m-test-1",
        business_name="Testaurant",
        payment_mode="pay_at_pickup",
        sms_checkout_enabled=True,
        sms_pay_template="",
        transfer_number="+15550001111",
        delivery_channels=None,
        pos_system="square",
        pos_access_token="tok",
        pos_location_id="loc",
        demo_safe=False,
        menu_items=[{"name": "Coke", "price": 3.0}, {"name": "Pizza", "price": 14.0}],
        language="en",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _order(**kw):
    base = {
        "merchant_id": "m-test-1",
        "business_name": "Testaurant",
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
    """Capture phone_orders inserts instead of hitting Supabase."""
    rows: list[dict] = []

    async def _fake_save(row):
        rows.append(row)
        return "row-uuid-1"

    monkeypatch.setattr(pop, "save_order_row", _fake_save)
    monkeypatch.setattr(dc, "save_order_row", _fake_save)
    return rows


@pytest.fixture
def sms_calls(monkeypatch):
    """Stub both SMS paths (customer checkout + merchant notify) as successes."""
    import payment_links as pl
    import sms_checkout as sc

    calls = {"checkout": [], "customer_sms": [], "merchant_sms": []}

    async def _fake_checkout(order, config, pos_order_id="", **kw):
        calls["checkout"].append(pos_order_id)
        return {"url": "https://pay.test/abc", "method": "stripe"}

    async def _fake_send_checkout_sms(**kw):
        calls["customer_sms"].append(kw)
        return {"sent": True, "method": "telnyx"}

    async def _fake_send_sms(to, body):
        calls["merchant_sms"].append({"to": to, "body": body})
        return {"sent": True, "method": "telnyx"}

    monkeypatch.setattr(pl, "create_checkout", _fake_checkout)
    monkeypatch.setattr(sc, "send_checkout_sms", _fake_send_checkout_sms)
    monkeypatch.setattr(sc, "send_sms", _fake_send_sms)
    # pay_on_phone binds these names at import time (pay_now path) — patch both.
    monkeypatch.setattr(pop, "create_checkout", _fake_checkout)
    monkeypatch.setattr(pop, "send_checkout_sms", _fake_send_checkout_sms)
    return calls


def _mock_pos(monkeypatch, result=None, exc: Exception | None = None):
    async def _fake(order, config, pos_result=None):
        if pos_result is not None:
            return pos_result
        if exc is not None:
            raise exc
        return result

    monkeypatch.setattr(dc, "create_pos_for_config", _fake)


# ─── 1. Parallel fan-out records every channel ───────────────────────────────

async def test_fanout_records_all_channels(monkeypatch, saved_rows, sms_calls):
    _mock_pos(monkeypatch, {"success": True, "pos_order_id": "SQ123", "pos_system": "square"})

    routed = await pop.dispatch_order(_order(), _cfg(), {"phone": "+15559990000"})

    assert routed["mode"] == "pay_at_pickup"
    assert routed["released"] is True
    assert routed["sms_sent"] is True
    assert routed["pos_result"]["pos_order_id"] == "SQ123"
    assert routed["phone_order_id"] == "row-uuid-1"

    d = routed["delivery"]
    assert d["pos"]["status"] == "sent"
    assert d["customer_sms"]["status"] == "sent"
    assert d["merchant_sms"]["status"] == "sent"

    # …and the row carries the per-channel ledger for support.
    assert len(saved_rows) == 1
    row = saved_rows[0]
    assert row["pos_delivery_status"] == "sent"
    assert row["sms_delivery_status"] == "sent"
    assert row["merchant_notify_status"] == "sent"
    assert row["pos_order_id"] == "SQ123"
    assert row["kitchen_released"] is True
    assert set(row["delivery_detail"]) == {"pos", "customer_sms", "merchant_sms"}
    # both SMS legs actually fired
    assert len(sms_calls["customer_sms"]) == 1
    assert sms_calls["merchant_sms"][0]["to"] == "+15550001111"


# ─── 2. POS failure still sends SMS + records the error ──────────────────────

async def test_pos_failure_still_sends_sms_and_records_error(monkeypatch, saved_rows, sms_calls):
    _mock_pos(monkeypatch, {"success": False, "reason": "square_api_error", "status": 500})

    routed = await pop.dispatch_order(_order(), _cfg(), {"phone": "+15559990000"})

    d = routed["delivery"]
    assert d["pos"]["status"] == "failed"
    assert "square_api_error" in d["pos"]["error"]
    # SMS legs unaffected by the POS failure — no more either/or.
    assert d["customer_sms"]["status"] == "sent"
    assert d["merchant_sms"]["status"] == "sent"
    assert len(sms_calls["customer_sms"]) == 1
    assert len(sms_calls["merchant_sms"]) == 1

    row = saved_rows[0]
    assert row["pos_delivery_status"] == "failed"
    assert row["pos_success"] is False
    assert row["delivery_detail"]["pos"]["error"] == "square_api_error"
    assert row["sms_delivery_status"] == "sent"


# ─── 3. Exception isolation: a raising leg never kills its siblings ──────────

async def test_leg_exception_is_isolated(monkeypatch, saved_rows, sms_calls):
    _mock_pos(monkeypatch, exc=RuntimeError("token decrypt exploded"))

    routed = await pop.dispatch_order(_order(), _cfg(), {"phone": "+15559990000"})

    d = routed["delivery"]
    assert d["pos"]["status"] == "failed"
    assert "token decrypt exploded" in d["pos"]["error"]
    assert d["customer_sms"]["status"] == "sent"
    assert d["merchant_sms"]["status"] == "sent"


# ─── 4. pay_now defers the POS ticket (anti-scam preserved) ──────────────────

async def test_pay_now_defers_pos_with_deferred_status(monkeypatch, saved_rows, sms_calls):
    monkeypatch.setattr(pop, "POS_PUSH_AFTER_PAYMENT", True)

    async def _boom(order, config, pos_result=None):  # POS must NOT be called now
        raise AssertionError("pay_now must not push the POS ticket at order time")

    monkeypatch.setattr(dc, "create_pos_for_config", _boom)

    routed = await pop.dispatch_order(
        _order(), _cfg(payment_mode="pay_now"), {"phone": "+15559990000"},
    )

    assert routed["mode"] == "pay_now"
    assert routed["released"] is False
    assert routed["pos_deferred"] is True
    assert routed["sms_sent"] is True  # pay-link SMS goes out NOW

    row = saved_rows[0]
    assert row["status"] == "awaiting_payment"
    assert row["kitchen_released"] is False
    assert row["pos_delivery_status"] == "deferred_pending_payment"
    assert row["sms_delivery_status"] == "sent"
    # merchant notification held with the ticket, released on payment
    assert row["merchant_notify_status"] == "deferred_pending_payment"


# ─── 5. delivery_channels toggles ────────────────────────────────────────────

def test_resolve_channels_defaults_and_overrides():
    assert dc.resolve_channels(_cfg(delivery_channels=None)) == {
        "pos": True, "customer_sms": True, "merchant_sms": True,
    }
    assert dc.resolve_channels(_cfg(delivery_channels={"merchant_sms": False})) == {
        "pos": True, "customer_sms": True, "merchant_sms": False,
    }
    # junk values never kill a leg
    assert dc.resolve_channels(_cfg(delivery_channels={"pos": "no", "customer_sms": 0})) == {
        "pos": True, "customer_sms": True, "merchant_sms": True,
    }


async def test_disabled_merchant_sms_is_skipped(monkeypatch, saved_rows, sms_calls):
    _mock_pos(monkeypatch, {"success": True, "pos_order_id": "SQ9", "pos_system": "square"})

    routed = await pop.dispatch_order(
        _order(), _cfg(delivery_channels={"merchant_sms": False}), {"phone": "+15559990000"},
    )

    assert routed["delivery"]["merchant_sms"]["status"] == "skipped_disabled"
    assert sms_calls["merchant_sms"] == []
    assert saved_rows[0]["merchant_notify_status"] == "skipped_disabled"
    # the other legs are untouched
    assert saved_rows[0]["pos_delivery_status"] == "sent"
    assert saved_rows[0]["sms_delivery_status"] == "sent"


# ─── 6. Kitchen prove-out: Square poll + per-POS dispatcher ──────────────────

from src.services import pos_fulfillment as pf  # noqa: E402


class _FakeSquareClient:
    """Stands in for SquareClient — no HTTP. Class-level script of responses."""
    orders: list[dict] = []
    calls: int = 0

    def __init__(self, *a, **kw):
        pass

    async def get_order(self, order_id: str) -> dict:
        cls = type(self)
        idx = min(cls.calls, len(cls.orders) - 1)
        cls.calls += 1
        return cls.orders[idx]

    async def close(self):
        pass


@pytest.fixture
def fake_square(monkeypatch):
    _FakeSquareClient.orders = []
    _FakeSquareClient.calls = 0
    monkeypatch.setattr(pf, "SquareClient", _FakeSquareClient)
    return _FakeSquareClient


async def test_square_poll_confirms_open_order(fake_square):
    fake_square.orders = [
        {"state": "DRAFT", "line_items": []},  # first poll: not ready yet
        {"state": "OPEN", "line_items": [{"name": "Coke"}]},
    ]
    result = await pf.verify_fulfillment(
        "square", "SQ123", "tok", "loc", attempts=3, delay_seconds=0,
    )
    assert result == {
        "supported": True, "confirmed": True, "state": "OPEN",
        "detail": "1 line item(s)",
    }
    assert fake_square.calls == 2


async def test_square_poll_times_out_unconfirmed(fake_square):
    fake_square.orders = [{"state": "DRAFT", "line_items": []}]
    result = await pf.verify_fulfillment(
        "square", "SQ123", "tok", attempts=2, delay_seconds=0,
    )
    assert result["confirmed"] is False
    assert result["supported"] is True


async def test_verify_and_record_sets_confirmed_at(fake_square, monkeypatch):
    fake_square.orders = [{"state": "OPEN", "line_items": [{"name": "Coke"}]}]
    patches: list[tuple] = []

    class _FakeDB:
        async def update(self, table, patch, filters=None):
            patches.append((table, patch, filters))

    import src.db as db_mod
    monkeypatch.setattr(db_mod, "get_db", lambda: _FakeDB())

    result = await pf.verify_and_record(
        "square", "SQ123", "tok", "row-uuid-1", attempts=1, delay_seconds=0,
    )
    assert result["confirmed"] is True
    assert len(patches) == 1
    table, patch, filters = patches[0]
    assert table == "phone_orders"
    assert patch["fulfillment_state"] == "OPEN"
    assert patch["fulfillment_confirmed_at"]  # stamped
    assert filters == {"id": "eq.row-uuid-1"}


async def test_non_square_verifier_reports_unsupported():
    # clover left this list 2026-07-16: it now has a real read-back verifier
    # (tests/pos_delivery/test_clover_kitchen_fire.py).
    for system in ("toast", "", "some-webhook-pos"):
        result = await pf.verify_fulfillment(system, "X1", "tok")
        assert result["supported"] is False
        assert result["confirmed"] is False
        assert result["state"] == "unsupported"


# ─── 7. Test-order builder marks itself unmistakably ─────────────────────────

def test_build_test_order_is_clearly_marked_and_cheap():
    order = dc.build_test_order(_cfg())
    assert order["customer_name"] == "MERIDIAN TEST ORDER"
    assert order["source"] == "test_order"
    assert "do not make" in order["special_requests"].lower()
    # cheapest priced real menu item picked (Coke @ 3.0, not Pizza @ 14.0)
    assert order["items"][0]["name"] == "Coke"
    assert order["total"] == 3.0

    # no priced menu → $0.01 synthetic line, never $0.00
    bare = dc.build_test_order(_cfg(menu_items=[]))
    assert bare["items"][0]["name"] == "Meridian Test Item"
    assert bare["total"] == 0.01
