"""Stripe checkout settlement — no silent drop, no double-book.

The activation + rep setup-fee commission on checkout.session.completed used to
be swallowed (log-and-continue) while the event was deduped BEFORE processing
and the handler always returned 200 — so a failed write left a paid customer
inactive / a rep unpaid, permanently (Stripe never retried; a resend was skipped
as a duplicate). Now: idempotent writes (deterministic commission id) that RAISE
on failure, and the webhook un-records the dedupe marker + returns non-2xx so
Stripe retries.
"""
import json
import os
import sys
from uuid import NAMESPACE_URL, uuid5

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from fastapi import HTTPException  # noqa: E402
from src.api.routes import stripe_checkout as sc  # noqa: E402

aio = pytest.mark.asyncio

DATA = {
    "id": "cs_test_1", "customer": "cus_1", "subscription": "sub_1",
    "metadata": {"meridian_org_id": "biz_x", "meridian_plan": "premium",
                 "meridian_rep_id": "rep_1", "setup_fee_cents": "5000"},
}


class _DB:
    def __init__(self):
        self.updates = []
        self.inserts = []
    async def update(self, table, patch, filters=None):
        self.updates.append((table, patch, filters))
        return [patch]
    async def insert(self, table, data, return_data=True):
        self.inserts.append((table, data))
        return [data]
    async def select(self, *a, **k):
        return []


@aio
async def test_activation_books_org_active_and_commission():
    db = _DB()
    await sc._activate_from_checkout(db, DATA)
    org = next(u for u in db.updates if u[0] == "organizations")
    meta = json.loads(org[1]["metadata"])
    assert meta["payment_status"] == "active"
    assert meta["plan_tier"] == "premium"
    comm = next(i for i in db.inserts if i[0] == "commissions")[1]
    assert comm["type"] == "setup_fee" and comm["amount_cents"] == 5000
    assert comm["status"] == "earned"


@aio
async def test_commission_id_deterministic_per_session():
    # Same session → same commission id, so a Stripe retry hits a PK conflict
    # (swallowed) instead of double-booking the rep's setup fee.
    db1, db2 = _DB(), _DB()
    await sc._activate_from_checkout(db1, DATA)
    await sc._activate_from_checkout(db2, DATA)
    id1 = next(i for i in db1.inserts if i[0] == "commissions")[1]["id"]
    id2 = next(i for i in db2.inserts if i[0] == "commissions")[1]["id"]
    assert id1 == id2 == str(uuid5(NAMESPACE_URL, "meridian-setup-fee:cs_test_1"))


@aio
async def test_no_org_id_is_noop_not_failure():
    db = _DB()
    await sc._activate_from_checkout(db, {"id": "cs", "metadata": {}})
    assert db.updates == [] and db.inserts == []


@aio
async def test_activation_raises_on_write_failure():
    # A real write failure must PROPAGATE so the webhook un-records + returns 500.
    class _FailDB(_DB):
        async def update(self, table, patch, filters=None):
            if table == "organizations":
                raise RuntimeError("db down")
            return await super().update(table, patch, filters)
    with pytest.raises(RuntimeError):
        await sc._activate_from_checkout(_FailDB(), DATA)


class _Req:
    def __init__(self, body=b"{}"):
        self._body = body
        self.headers = {"stripe-signature": "sig"}
    async def body(self):
        return self._body


@aio
async def test_webhook_unrecords_and_500_on_activation_failure(monkeypatch):
    monkeypatch.setattr(sc, "STRIPE_WEBHOOK_SECRET", "whsec_test")

    class _Stripe:
        class Webhook:
            @staticmethod
            def construct_event(payload, sig, secret):
                return {"id": "evt_1", "type": "checkout.session.completed",
                        "data": {"object": DATA}}
    monkeypatch.setattr(sc, "_get_stripe", lambda: _Stripe())

    import src.api.routes.webhooks as wh
    async def _rec(eid, provider="square"):
        return True  # first delivery
    forgot = {}
    async def _forget(eid, provider="square"):
        forgot["eid"] = eid
    monkeypatch.setattr(wh, "_record_webhook_event", _rec)
    monkeypatch.setattr(wh, "_forget_webhook_event", _forget)

    async def _boom(db, data):
        raise RuntimeError("activation write failed")
    monkeypatch.setattr(sc, "_activate_from_checkout", _boom)

    with pytest.raises(HTTPException) as exc:
        await sc.stripe_webhook(_Req())
    assert exc.value.status_code == 500          # Stripe will retry
    assert forgot["eid"] == "evt_1"              # dedupe marker un-recorded


@aio
async def test_webhook_duplicate_is_skipped(monkeypatch):
    monkeypatch.setattr(sc, "STRIPE_WEBHOOK_SECRET", "whsec_test")

    class _Stripe:
        class Webhook:
            @staticmethod
            def construct_event(payload, sig, secret):
                return {"id": "evt_dup", "type": "checkout.session.completed",
                        "data": {"object": DATA}}
    monkeypatch.setattr(sc, "_get_stripe", lambda: _Stripe())

    import src.api.routes.webhooks as wh
    async def _rec(eid, provider="square"):
        return False  # already processed
    monkeypatch.setattr(wh, "_record_webhook_event", _rec)

    called = {"n": 0}
    async def _act(db, data):
        called["n"] += 1
    monkeypatch.setattr(sc, "_activate_from_checkout", _act)

    out = await sc.stripe_webhook(_Req())
    assert out == {"status": "ok"}
    assert called["n"] == 0                       # duplicate never re-activates
