"""
Clover order creation — coverage for the write path.

Mocks httpx so no network. Pins the bug fix (one line-item POST PER UNIT, not
one per item regardless of quantity) + region-aware base URL + error handling.
"""
import sys
from pathlib import Path

import pytest

_DIR = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import pos_connector as pc  # noqa: E402

aio = pytest.mark.asyncio

ORDER = {
    "customer_name": "Sam",
    "items": [
        {"name": "Cheeseburger", "quantity": 2, "unit_price": 9.5},
        {"name": "Fries", "quantity": 1, "price": 3.5},
    ],
}


class _Resp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._d = data or {}
        self.text = ""

    def json(self):
        return self._d


class _Client:
    def __init__(self, calls, order_status=200, li_status=200):
        self.calls = calls
        self.order_status = order_status
        self.li_status = li_status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append((url, json))
        if url.endswith("/orders"):
            return _Resp(self.order_status, {"id": "ORD1"})
        return _Resp(self.li_status, {"id": "LI"})


def test_clover_api_base_env(monkeypatch):
    monkeypatch.setenv("CLOVER_ENVIRONMENT", "sandbox")
    assert pc.clover_api_base() == "https://apisandbox.dev.clover.com"
    monkeypatch.setenv("CLOVER_ENVIRONMENT", "production")
    monkeypatch.setenv("CLOVER_REGION", "na")
    assert pc.clover_api_base() == "https://api.clover.com"
    monkeypatch.setenv("CLOVER_API_BASE", "https://x.example")
    assert pc.clover_api_base() == "https://x.example"


@aio
async def test_create_order_one_line_item_per_unit(monkeypatch):
    monkeypatch.delenv("CLOVER_API_BASE", raising=False)
    monkeypatch.setenv("CLOVER_ENVIRONMENT", "production")
    monkeypatch.setenv("CLOVER_REGION", "na")
    calls: list = []
    monkeypatch.setattr(pc.httpx, "AsyncClient", lambda *a, **k: _Client(calls))

    out = await pc._create_clover_order(ORDER, "tok", "MID")
    assert out["success"] is True
    assert out["pos_order_id"] == "ORD1"
    # 1 order POST + (2 + 1) line-item POSTs
    order_calls = [c for c in calls if c[0].endswith("/orders")]
    li_calls = [c for c in calls if "/line_items" in c[0]]
    assert len(order_calls) == 1
    assert len(li_calls) == 3
    assert out["line_items_added"] == 3
    # correct host + price in cents
    assert calls[0][0].startswith("https://api.clover.com/v3/merchants/MID/orders")
    assert any(c[1].get("price") == 950 for c in li_calls)
    assert any(c[1].get("price") == 350 for c in li_calls)


@aio
async def test_create_order_fails_cleanly(monkeypatch):
    calls: list = []
    monkeypatch.setattr(pc.httpx, "AsyncClient", lambda *a, **k: _Client(calls, order_status=403))
    out = await pc._create_clover_order(ORDER, "tok", "MID")
    assert out["success"] is False
    assert out["status"] == 403  # e.g. missing write permission
