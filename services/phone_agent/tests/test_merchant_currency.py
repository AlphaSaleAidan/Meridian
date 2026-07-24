"""Charge currency derivation for phone-order checkout.

_stripe_checkout used to default to CAD when the order carried no currency,
charging US merchants in Canadian dollars. _merchant_currency now derives it
from merchant_billing_terms.source_market ('us' → usd), failing open to cad.
"""
import sys
from pathlib import Path

import pytest

_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import payment_links as pl  # noqa: E402

pytestmark = pytest.mark.asyncio


class _FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, resp):
        self._resp = resp
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        return False
    async def get(self, *a, **k):
        return self._resp


def _patch(monkeypatch, resp):
    monkeypatch.setattr(pl, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(pl, "SUPABASE_KEY", "fake-key")
    monkeypatch.setattr(pl.httpx, "AsyncClient", lambda *a, **k: _FakeClient(resp))


async def test_us_market_gives_usd(monkeypatch):
    _patch(monkeypatch, _FakeResp(200, [{"source_market": "us"}]))
    assert await pl._merchant_currency("biz_us") == "usd"


async def test_ca_market_gives_cad(monkeypatch):
    _patch(monkeypatch, _FakeResp(200, [{"source_market": "ca"}]))
    assert await pl._merchant_currency("biz_ca") == "cad"


async def test_no_terms_defaults_cad(monkeypatch):
    _patch(monkeypatch, _FakeResp(200, []))
    assert await pl._merchant_currency("biz_none") == "cad"


async def test_no_supabase_defaults_cad(monkeypatch):
    monkeypatch.setattr(pl, "SUPABASE_URL", "")
    assert await pl._merchant_currency("biz_x") == "cad"


async def test_lookup_error_fails_open_cad(monkeypatch):
    class _BoomClient(_FakeClient):
        async def get(self, *a, **k):
            raise RuntimeError("network down")
    monkeypatch.setattr(pl, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(pl, "SUPABASE_KEY", "fake-key")
    monkeypatch.setattr(pl.httpx, "AsyncClient", lambda *a, **k: _BoomClient(None))
    assert await pl._merchant_currency("biz_boom") == "cad"
