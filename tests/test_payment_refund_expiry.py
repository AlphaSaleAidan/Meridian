"""
Refund/dispute + session-expiry handling on the Stripe Connect webhook
(2026-07-21 gap sweep — phone path).

Before this: neither webhook handled charge.refunded / dispute / session
expiry. A refunded phone order stayed 'paid' and kept its service-fee credit;
an expired Stripe pay-link 303'd the customer to a dead page.

  _reverse_paid_order: flips the phone order to refunded/disputed and reverses
  the fee via an idempotent ledger debit; no-ops cleanly when no phone order
  matches (website/other). The webhook routes the new event types here and
  flips checkout_sessions → expired on session expiry.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.api.routes import stripe_connect as sc  # noqa: E402

aio = pytest.mark.asyncio


class _DB:
    def __init__(self, orders=None):
        self.orders = orders or []
        self.updates = []

    async def select(self, table, cols=None, filters=None, limit=None):
        if table == "phone_orders":
            pi = (filters or {}).get("payment_txn_id", "").replace("eq.", "")
            return [o for o in self.orders if o.get("payment_txn_id") == pi][:1]
        return []

    async def update(self, table, patch, filters=None):
        self.updates.append((table, patch, filters))
        return [patch]


def _patch_fee(monkeypatch, cents):
    async def fake_fee(mid):
        return cents
    monkeypatch.setattr(sc, "_merchant_service_fee_cents", fake_fee)


def _patch_ledger(monkeypatch, calls):
    import src.services.voice_ledger as vl

    async def fake_debit(merchant_id, amount_cents, source="", ref=None, note=None):
        calls.append({"merchant_id": merchant_id, "cents": amount_cents,
                      "source": source, "ref": ref})
        return True
    monkeypatch.setattr(vl, "debit", fake_debit)


@aio
async def test_refund_flips_status_and_reverses_fee(monkeypatch):
    db = _DB(orders=[{"id": "ord1", "merchant_id": "biz_x", "status": "paid",
                      "payment_txn_id": "pi_123"}])
    _patch_fee(monkeypatch, 99)
    ledger = []
    _patch_ledger(monkeypatch, ledger)

    await sc._reverse_paid_order(db, "pi_123", disputed=False)

    assert ("phone_orders", {"status": "refunded"}, {"id": "eq.ord1"}) in db.updates
    assert ledger == [{"merchant_id": "biz_x", "cents": 99,
                       "source": "stripe_fee_reversal", "ref": "pi_123"}]


@aio
async def test_partial_refund_reverses_pro_rata_and_marks_partial(monkeypatch):
    # $2 refund on a $60 order, fee 99¢ → reverse round(99 * 200/6000) = 3¢, and
    # the order is 'partially_refunded' (NOT the whole thing marked refunded).
    db = _DB(orders=[{"id": "ordP", "merchant_id": "biz_p", "status": "paid",
                      "payment_txn_id": "pi_P"}])
    _patch_fee(monkeypatch, 99)
    ledger = []
    _patch_ledger(monkeypatch, ledger)

    await sc._reverse_paid_order(
        db, "pi_P", disputed=False,
        amount_charged=6000, amount_refunded=200, fully_refunded=False,
    )

    assert ("phone_orders", {"status": "partially_refunded"}, {"id": "eq.ordP"}) in db.updates
    assert len(ledger) == 1
    assert ledger[0]["cents"] == 3
    assert ledger[0]["ref"] == "pi_P:200"  # cumulative amount in ref for idempotency


@aio
async def test_second_partial_reverses_only_delta(monkeypatch):
    # First refund reversed 3¢; a later cumulative $5 refund (fee 99¢, target
    # round(99*500/6000)=8¢) reverses only the 5¢ delta, not another 8¢.
    class _LedgerDB(_DB):
        async def select(self, table, cols=None, filters=None, limit=None):
            if table == "voice_ledger":
                return [{"amount_cents": 3, "note": "partially_refunded:ordP"}]
            return await super().select(table, cols, filters, limit)

    db = _LedgerDB(orders=[{"id": "ordP", "merchant_id": "biz_p", "status": "paid",
                            "payment_txn_id": "pi_P"}])
    _patch_fee(monkeypatch, 99)
    ledger = []
    _patch_ledger(monkeypatch, ledger)

    await sc._reverse_paid_order(
        db, "pi_P", disputed=False,
        amount_charged=6000, amount_refunded=500, fully_refunded=False,
    )

    assert len(ledger) == 1
    assert ledger[0]["cents"] == 5  # 8¢ target − 3¢ already reversed


@aio
async def test_full_refund_via_amounts_reverses_whole_fee(monkeypatch):
    db = _DB(orders=[{"id": "ordF", "merchant_id": "biz_f", "status": "paid",
                      "payment_txn_id": "pi_F"}])
    _patch_fee(monkeypatch, 99)
    ledger = []
    _patch_ledger(monkeypatch, ledger)

    await sc._reverse_paid_order(
        db, "pi_F", disputed=False,
        amount_charged=6000, amount_refunded=6000, fully_refunded=True,
    )

    assert ("phone_orders", {"status": "refunded"}, {"id": "eq.ordF"}) in db.updates
    assert ledger[0]["cents"] == 99
    assert ledger[0]["ref"] == "pi_F"  # full refund uses the bare PI ref


@aio
async def test_dispute_uses_disputed_status(monkeypatch):
    db = _DB(orders=[{"id": "ord2", "merchant_id": "biz_y", "status": "paid",
                      "payment_txn_id": "pi_9"}])
    _patch_fee(monkeypatch, 50)
    _patch_ledger(monkeypatch, [])

    await sc._reverse_paid_order(db, "pi_9", disputed=True)

    assert ("phone_orders", {"status": "disputed"}, {"id": "eq.ord2"}) in db.updates


@aio
async def test_refund_no_matching_order_is_noop(monkeypatch):
    db = _DB(orders=[])
    _patch_fee(monkeypatch, 99)
    ledger = []
    _patch_ledger(monkeypatch, ledger)

    await sc._reverse_paid_order(db, "pi_unknown", disputed=False)

    assert db.updates == [] and ledger == []


@aio
async def test_refund_empty_pi_is_noop(monkeypatch):
    db = _DB(orders=[{"id": "o", "merchant_id": "m", "payment_txn_id": ""}])
    _patch_fee(monkeypatch, 99)
    ledger = []
    _patch_ledger(monkeypatch, ledger)

    await sc._reverse_paid_order(db, "", disputed=False)
    assert db.updates == [] and ledger == []


@aio
async def test_zero_fee_skips_ledger_but_still_flips(monkeypatch):
    db = _DB(orders=[{"id": "ord3", "merchant_id": "biz_z", "status": "paid",
                      "payment_txn_id": "pi_3"}])
    _patch_fee(monkeypatch, 0)
    ledger = []
    _patch_ledger(monkeypatch, ledger)

    await sc._reverse_paid_order(db, "pi_3", disputed=False)

    assert ("phone_orders", {"status": "refunded"}, {"id": "eq.ord3"}) in db.updates
    assert ledger == [], "no fee credited → nothing to reverse"


# ── webhook routing (mock construct_event, assert dispatch) ──────────────
def _mock_webhook(monkeypatch, event, db):
    class _WH:
        @staticmethod
        def construct_event(payload, sig, secret):
            return event

    class _Stripe:
        Webhook = _WH
    monkeypatch.setattr(sc, "_stripe", lambda: _Stripe())
    monkeypatch.setattr(sc, "CONNECT_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(sc, "get_db", lambda: db)

    # skip the durable-dedupe DB hop
    async def _rec(*a, **k):
        return True
    monkeypatch.setattr("src.api.routes.webhooks._record_webhook_event", _rec, raising=False)


class _Req:
    def __init__(self, body=b"{}"):
        self._body = body
        self.headers = {"stripe-signature": "sig"}

    async def body(self):
        return self._body


@aio
async def test_webhook_routes_refund(monkeypatch):
    db = _DB(orders=[{"id": "ordW", "merchant_id": "biz_w", "status": "paid",
                      "payment_txn_id": "pi_W"}])
    _patch_fee(monkeypatch, 25)
    ledger = []
    _patch_ledger(monkeypatch, ledger)
    event = {
        "id": "evt_1", "type": "charge.refunded",
        "data": {"object": {"id": "ch_1", "payment_intent": "pi_W"}},
    }
    _mock_webhook(monkeypatch, event, db)

    out = await sc.connect_webhook(_Req(json.dumps(event).encode()))
    assert out["received"] is True
    assert any(u[1] == {"status": "refunded"} for u in db.updates)
    assert ledger and ledger[0]["ref"] == "pi_W"


@aio
async def test_webhook_expires_checkout_session(monkeypatch):
    db = _DB()
    event = {
        "id": "evt_2", "type": "checkout.session.expired",
        "data": {"object": {"id": "cs_dead"}},
    }
    _mock_webhook(monkeypatch, event, db)

    out = await sc.connect_webhook(_Req(json.dumps(event).encode()))
    assert out["received"] is True
    assert ("checkout_sessions", {"status": "expired"},
            {"provider_ref": "eq.cs_dead", "status": "neq.complete"}) in db.updates
