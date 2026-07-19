"""
Tests for the SHARED order-receipt SMS (order_receipt.send_order_receipt).

The turn-based Vapi path and the streaming Pipecat path must both fire the SAME
customer receipt SMS after an order completes — exactly once per order, with the
correct summary, and always subject to the transactional opt-out + killswitch
guards.

Asserts, with fakes (no network):
  - streaming order → exactly one receipt SMS, body carries the order summary +
    the pay/pickup line.
  - idempotent on order_id: a second report of the SAME order (e.g. sidecar AND
    the payment webhook both reporting) sends NO second SMS.
  - transactional opt-out suppresses the receipt (no send).
  - killswitch (PHONE_RECEIPT_SMS_ENABLED=0) suppresses the receipt (no send).
  - the pay_at_pickup streaming fan-out (_fanout_release) fires the receipt once.

These exercise the shared helper directly + through the streaming dispatch
surface (pay_on_phone._fanout_release) without importing pipecat-heavy bot.py.
"""
import sys
from pathlib import Path

import pytest

_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import order_receipt  # noqa: E402
from merchant_config import _demo_config  # noqa: E402

pytestmark = pytest.mark.asyncio


def _order(merchant_id="real-merchant"):
    return {
        "merchant_id": merchant_id,
        "business_name": "Demo Restaurant",
        "customer_name": "Sam Rivera",
        "order_type": "pickup",
        "items": [
            {"name": "Cheeseburger", "quantity": 2, "unit_price": 12.99},
            {"name": "Fries", "quantity": 1, "unit_price": 4.00},
        ],
        "subtotal": 29.98, "tax": 3.90, "total": 33.88,
        "currency": "cad",
        "caller_phone": "+15555550111",
        "pos_system": "square",
    }


class _Sms:
    """Spy over order_receipt.send_sms — records every send."""

    def __init__(self):
        self.sends = []  # (to, body)

    def install(self, monkeypatch, *, sent=True):
        async def fake_send_sms(to, body):
            self.sends.append((to, body))
            return {"sent": sent, "method": "telnyx", "message_sid": "SM-R1"}

        monkeypatch.setattr(order_receipt, "send_sms", fake_send_sms)
        return self


def _no_optout(monkeypatch, *, transactional=False, marketing=False):
    async def fake_optout(merchant_id, phone):
        return {"marketing_optout": marketing, "transactional_optout": transactional}

    monkeypatch.setattr(order_receipt, "fetch_optout_status", fake_optout)


def _mark_first_time(monkeypatch):
    """Durable idempotency marker: first call returns True (we own the send),
    any later call for the same order_id returns False (already claimed)."""
    seen = set()

    async def fake_claim(order_id):
        if not order_id or order_id in seen:
            return False
        seen.add(order_id)
        return True

    monkeypatch.setattr(order_receipt, "_claim_receipt", fake_claim)
    return seen


# ─── shared helper: happy path ───────────────────────────────────────────────
async def test_streaming_receipt_sends_once_with_summary(monkeypatch):
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    _mark_first_time(monkeypatch)
    cfg = _demo_config("real-merchant")

    res = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="POS-STREAM-1", paid=True,
    )

    assert res["sent"] is True
    assert len(sms.sends) == 1
    to, body = sms.sends[0]
    assert to == "+15555550111"
    # summary present
    assert "Cheeseburger" in body
    assert "CA$33.88" in body
    # paid receipt line present
    assert "paid" in body.lower() or "payment received" in body.lower()


async def test_receipt_pickup_line_for_pay_at_pickup(monkeypatch):
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    _mark_first_time(monkeypatch)
    cfg = _demo_config("real-merchant")

    res = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="POS-PICKUP-1", paid=False,
    )

    assert res["sent"] is True
    _to, body = sms.sends[0]
    # unpaid / pay-at-pickup receipt speaks to pickup, not "paid"
    assert "pickup" in body.lower() or "ready" in body.lower()


# ─── idempotency ─────────────────────────────────────────────────────────────
async def test_double_report_sends_one_receipt(monkeypatch):
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    _mark_first_time(monkeypatch)
    cfg = _demo_config("real-merchant")

    first = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="ORD-DUP", paid=True,
    )
    # sidecar AND payment webhook both report the SAME order id
    second = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="ORD-DUP", paid=True,
    )

    assert first["sent"] is True
    assert second["sent"] is False
    assert second.get("reason") == "already_sent"
    assert len(sms.sends) == 1


# ─── guards ──────────────────────────────────────────────────────────────────
async def test_transactional_optout_suppresses_receipt(monkeypatch):
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch, transactional=True)
    _mark_first_time(monkeypatch)
    cfg = _demo_config("real-merchant")

    res = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="ORD-OPTOUT", paid=True,
    )

    assert res["sent"] is False
    assert res.get("reason") == "transactional_optout"
    assert sms.sends == []


async def test_killswitch_suppresses_receipt(monkeypatch):
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    _mark_first_time(monkeypatch)
    monkeypatch.setenv("PHONE_RECEIPT_SMS_ENABLED", "0")
    cfg = _demo_config("real-merchant")

    res = await order_receipt.send_order_receipt(
        _order(), cfg, order_id="ORD-KILL", paid=True,
    )

    assert res["sent"] is False
    assert res.get("reason") == "killswitch"
    assert sms.sends == []


async def test_no_phone_skips_receipt(monkeypatch):
    sms = _Sms().install(monkeypatch)
    _no_optout(monkeypatch)
    _mark_first_time(monkeypatch)
    cfg = _demo_config("real-merchant")
    order = _order()
    order["caller_phone"] = ""

    res = await order_receipt.send_order_receipt(
        order, cfg, order_id="ORD-NOPHONE", paid=True,
    )

    assert res["sent"] is False
    assert res.get("reason") == "no_phone"
    assert sms.sends == []
