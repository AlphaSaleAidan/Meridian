"""Regression: the Stripe webhooks must read the event as PLAIN DICTS.

This SDK's StripeObject is not dict-subclassed, so `event.get(...)` raises
`AttributeError: get` and 500s EVERY webhook delivery (caught + silently
swallowed by the security middleware). The live $0.75 test on 2026-08-06
caught it: charge succeeded, but the confirm webhook 500'd on every event.
The fix verifies the signature via construct_event, then reads the already-
verified raw payload with json.loads. These tests make a construct_event that
returns a no-`.get()` object and assert the handler still processes.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.api.routes import stripe_connect as sc  # noqa: E402

aio = pytest.mark.asyncio


class _NoGetStripeObject:
    """Mimics this SDK's StripeObject: attribute/subscript access, but `.get`
    resolves through __getattr__ and raises AttributeError — exactly what blew
    up in prod."""
    def __init__(self, d):
        self._d = d

    def __getitem__(self, k):
        return self._d[k]

    def __getattr__(self, name):
        raise AttributeError(name)


class _DB:
    def __init__(self):
        self.updates = []

    async def select(self, *a, **k):
        return []

    async def update(self, table, patch, filters=None):
        self.updates.append((table, patch, filters))
        return [patch]


class _Req:
    def __init__(self, payload: bytes):
        self._payload = payload
        self.headers = {"stripe-signature": "t=1,v1=deadbeef"}

    async def body(self):
        return self._payload


@aio
@pytest.mark.parametrize("etype,obj", [
    ("account.updated", {"id": "acct_x", "object": "account", "charges_enabled": True}),
    ("checkout.session.completed", {"id": "cs_x", "object": "checkout.session",
                                    "amount_total": 75, "currency": "cad", "metadata": {}}),
    ("checkout.session.expired", {"id": "cs_y", "object": "checkout.session"}),
])
async def test_webhook_processes_when_construct_event_has_no_get(monkeypatch, etype, obj):
    event = {"id": "evt_1", "object": "event", "type": etype, "data": {"object": obj}}
    payload = json.dumps(event).encode()

    # construct_event verifies the signature and returns a StripeObject with NO
    # working .get() — the prod failure shape. The handler must ignore its
    # return and read the raw payload as a dict.
    monkeypatch.setattr(sc, "_construct_event",
                        lambda stripe, p, s: _NoGetStripeObject(event))
    monkeypatch.setattr(sc, "get_db", lambda: _DB())
    # dedupe + downstream imports fail-open; force the dedupe to say "new"
    import src.api.routes.webhooks as wh
    async def _new(*a, **k):
        return True
    monkeypatch.setattr(wh, "_record_webhook_event", _new)
    monkeypatch.setattr(sc, "CONNECT_WEBHOOK_SECRET", "whsec_test")

    # Must NOT raise AttributeError and must return the ack.
    result = await sc.connect_webhook(_Req(payload))
    assert result == {"received": True}


@aio
async def test_bad_signature_still_400(monkeypatch):
    def _boom(stripe, p, s):
        raise ValueError("bad sig")
    monkeypatch.setattr(sc, "_construct_event", _boom)
    monkeypatch.setattr(sc, "CONNECT_WEBHOOK_SECRET", "whsec_test")
    from fastapi import HTTPException
    payload = json.dumps({"id": "e", "type": "account.updated", "data": {"object": {}}}).encode()
    with pytest.raises(HTTPException) as ei:
        await sc.connect_webhook(_Req(payload))
    assert ei.value.status_code == 400
