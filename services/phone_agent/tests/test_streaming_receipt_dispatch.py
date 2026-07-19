"""
Streaming order-completion → receipt SMS reconciliation.

The streaming (Pipecat) phone path completes pay_at_pickup orders through
pay_on_phone._fanout_release. That release path MUST fire the shared customer
receipt SMS exactly once — the reconciliation this branch closes.

Asserts, with fakes (no network):
  - a pay_at_pickup fan-out fires the shared receipt helper exactly once, keyed
    on the real pos_order_id.
  - a receipt-helper failure never strands the order (fan-out still returns).
  - the pay_now (turn-based) held path does NOT fire the pay_at_pickup receipt
    at order time (the receipt for pay_now comes from the payment webhook) —
    turn-based behavior unchanged.
"""
import sys
from pathlib import Path

import pytest

_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)
_TESTDIR = str(Path(__file__).resolve().parent)
if _TESTDIR not in sys.path:
    sys.path.insert(0, _TESTDIR)

import pay_on_phone  # noqa: E402
from merchant_config import _demo_config  # noqa: E402
from test_pay_on_phone import Spy, _order  # noqa: E402

pytestmark = pytest.mark.asyncio


class _ReceiptSpy:
    def __init__(self):
        self.calls = []  # (order_id, paid)

    def install(self, monkeypatch, *, raises=False):
        async def fake_receipt(order, config, *, order_id, paid=True, **kw):
            self.calls.append((order_id, paid))
            if raises:
                raise RuntimeError("receipt blew up")
            return {"sent": True, "order_id": order_id}

        monkeypatch.setattr(pay_on_phone, "send_order_receipt", fake_receipt)
        return self


async def test_pay_at_pickup_fires_receipt_once(monkeypatch):
    Spy().install(monkeypatch)
    receipt = _ReceiptSpy().install(monkeypatch)
    cfg = _demo_config("real-merchant")
    # pay_at_pickup so the release fan-out runs now.
    cfg = _replace_mode(cfg, "pay_at_pickup")

    result = await pay_on_phone.dispatch_order(
        _order(), cfg, {"phone": "+15555550111"},
    )

    assert result["mode"] == "pay_at_pickup"
    assert len(receipt.calls) == 1
    order_id, paid = receipt.calls[0]
    assert order_id == "POS-ABC-123"   # the real pos_order_id from the pos leg
    assert paid is False               # pay_at_pickup → unpaid receipt


async def test_receipt_failure_never_strands_release(monkeypatch):
    Spy().install(monkeypatch)
    _ReceiptSpy().install(monkeypatch, raises=True)
    cfg = _replace_mode(_demo_config("real-merchant"), "pay_at_pickup")

    # must not raise; the order is already released to the kitchen
    result = await pay_on_phone.dispatch_order(
        _order(), cfg, {"phone": "+15555550111"},
    )
    assert result["released"] is True


async def test_pay_now_does_not_fire_pickup_receipt(monkeypatch):
    Spy().install(monkeypatch)
    receipt = _ReceiptSpy().install(monkeypatch)
    # real (non-demo) merchant on pay_now → held, no simulate, no receipt now.
    cfg = _replace_mode(_demo_config("real-merchant"), "pay_now")

    await pay_on_phone.dispatch_order(
        _order(), cfg, {"phone": "+15555550111"},
    )
    assert receipt.calls == []


def _replace_mode(cfg, mode):
    from dataclasses import replace
    return replace(cfg, payment_mode=mode)
