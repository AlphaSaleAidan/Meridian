"""
Marketplace webhook hardening (2026-07-22 sweep):
  - fail CLOSED when SQUARE_MARKETPLACE_WEBHOOK_SECRET is unset (was fail-open:
    an unsigned payment.completed could trigger a real dataset download email).
  - reject a bad signature.
  - idempotency: a duplicate event id is skipped (no double download/sale).
Plus the Tekmetric registry prod-host fix.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

import marketplace.webhook as mw  # noqa: E402

aio = pytest.mark.asyncio


class _Req:
    def __init__(self, body: bytes, headers=None, url="https://api.meridian.tips/api/marketplace/webhook"):
        self._body = body
        self.headers = headers or {}
        self.url = url

    async def body(self):
        return self._body


@aio
async def test_fail_closed_without_secret(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.delenv("SQUARE_MARKETPLACE_WEBHOOK_SECRET", raising=False)
    with pytest.raises(HTTPException) as exc:
        await mw.square_marketplace_webhook(_Req(b'{"type":"payment.completed"}'))
    assert exc.value.status_code == 503


@aio
async def test_bad_signature_rejected(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setenv("SQUARE_MARKETPLACE_WEBHOOK_SECRET", "sekret")
    with pytest.raises(HTTPException) as exc:
        await mw.square_marketplace_webhook(
            _Req(b'{"type":"payment.completed"}', {"x-square-hmacsha256-signature": "wrong"}))
    assert exc.value.status_code == 400


@aio
async def test_duplicate_event_skipped(monkeypatch):
    monkeypatch.setenv("SQUARE_MARKETPLACE_WEBHOOK_SECRET", "sekret")
    monkeypatch.setattr(mw, "_verify_square_signature", lambda *a: True)

    async def dup(event_id, provider="square"):
        return False  # already recorded → duplicate
    monkeypatch.setattr("src.api.routes.webhooks._record_webhook_event", dup, raising=False)

    body = json.dumps({"type": "payment.completed", "event_id": "evt_1"}).encode()
    res = await mw.square_marketplace_webhook(_Req(body, {"x-square-hmacsha256-signature": "ok"}))
    assert res.get("dedup") is True


def test_tekmetric_registry_prod_host():
    from src.services.pos_connectors.registry import SYSTEM_CONFIGS
    assert "sandbox" not in SYSTEM_CONFIGS["tekmetric"]["base_url"]
    assert SYSTEM_CONFIGS["tekmetric"]["base_url"].startswith("https://shop.tekmetric.com")
