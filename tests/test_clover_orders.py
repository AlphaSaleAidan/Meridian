"""
Clover order creation — coverage for the write path.

Mocks httpx so no network. Pins the bug fix (one line-item POST PER UNIT, not
one per item regardless of quantity) + region-aware base URL + error handling
+ the kitchen fire: after order + line items, a print_event POST fires the
ticket to the merchant's order printer (an API-created Clover order never
prints on its own). Print failure is non-fatal; CLOVER_KITCHEN_FIRE_ENABLED=0
is the kill-switch.
"""
import sys
from pathlib import Path

import pytest

_DIR = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import clover_orders as co  # noqa: E402
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
    def __init__(self, calls, order_status=200, li_status=200, pe_status=200):
        self.calls = calls
        self.order_status = order_status
        self.li_status = li_status
        self.pe_status = pe_status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append((url, json))
        if url.endswith("/orders"):
            return _Resp(self.order_status, {"id": "ORD1"})
        if url.endswith("/print_event"):
            return _Resp(self.pe_status, {"id": "PE1"})
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
    monkeypatch.delenv("CLOVER_KITCHEN_FIRE_ENABLED", raising=False)
    monkeypatch.setenv("CLOVER_ENVIRONMENT", "production")
    monkeypatch.setenv("CLOVER_REGION", "na")
    calls: list = []
    monkeypatch.setattr(co.httpx, "AsyncClient", lambda *a, **k: _Client(calls))

    out = await co.create_clover_order(ORDER, "tok", "MID")
    assert out["success"] is True
    assert out["pos_order_id"] == "ORD1"
    # 1 order POST + (2 + 1) line-item POSTs + 1 kitchen print event
    order_calls = [c for c in calls if c[0].endswith("/orders")]
    li_calls = [c for c in calls if "/line_items" in c[0]]
    pe_calls = [c for c in calls if c[0].endswith("/print_event")]
    assert len(order_calls) == 1
    assert len(li_calls) == 3
    assert out["line_items_added"] == 3
    # correct host + price in cents
    assert calls[0][0].startswith("https://api.clover.com/v3/merchants/MID/orders")
    assert any(c[1].get("price") == 950 for c in li_calls)
    assert any(c[1].get("price") == 350 for c in li_calls)
    # kitchen fire: exact URL + body, and it fires AFTER the line items
    assert len(pe_calls) == 1
    assert pe_calls[0][0] == "https://api.clover.com/v3/merchants/MID/print_event"
    assert pe_calls[0][1] == {"orderRef": {"id": "ORD1"}}
    assert calls[-1][0].endswith("/print_event")
    assert out["kitchen_fired"] is True
    assert out["kitchen_fire_status"] == "200"


@aio
async def test_create_order_fails_cleanly(monkeypatch):
    calls: list = []
    monkeypatch.setattr(co.httpx, "AsyncClient", lambda *a, **k: _Client(calls, order_status=403))
    out = await co.create_clover_order(ORDER, "tok", "MID")
    assert out["success"] is False
    assert out["status"] == 403  # e.g. missing write permission
    # no order → no print event attempted
    assert not any(c[0].endswith("/print_event") for c in calls)


@aio
async def test_print_failure_does_not_fail_order(monkeypatch):
    """Print 4xx (no printer configured / no device online) → order still
    succeeds, kitchen_fired=False, status code surfaced for support."""
    monkeypatch.delenv("CLOVER_KITCHEN_FIRE_ENABLED", raising=False)
    calls: list = []
    monkeypatch.setattr(co.httpx, "AsyncClient", lambda *a, **k: _Client(calls, pe_status=400))

    out = await co.create_clover_order(ORDER, "tok", "MID")
    assert out["success"] is True
    assert out["pos_order_id"] == "ORD1"
    assert out["kitchen_fired"] is False
    assert out["kitchen_fire_status"] == "400"


@aio
async def test_print_exception_does_not_fail_order(monkeypatch):
    class _Boom(_Client):
        async def post(self, url, json=None, headers=None):
            if url.endswith("/print_event"):
                raise RuntimeError("device offline")
            return await super().post(url, json=json, headers=headers)

    monkeypatch.delenv("CLOVER_KITCHEN_FIRE_ENABLED", raising=False)
    calls: list = []
    monkeypatch.setattr(co.httpx, "AsyncClient", lambda *a, **k: _Boom(calls))

    out = await co.create_clover_order(ORDER, "tok", "MID")
    assert out["success"] is True
    assert out["kitchen_fired"] is False
    assert out["kitchen_fire_status"] == "error"


@aio
async def test_kill_switch_skips_print_event(monkeypatch):
    monkeypatch.setenv("CLOVER_KITCHEN_FIRE_ENABLED", "0")
    calls: list = []
    monkeypatch.setattr(co.httpx, "AsyncClient", lambda *a, **k: _Client(calls))

    out = await co.create_clover_order(ORDER, "tok", "MID")
    assert out["success"] is True
    assert not any(c[0].endswith("/print_event") for c in calls)
    assert out["kitchen_fired"] is False
    assert out["kitchen_fire_status"] == "skipped_disabled"
