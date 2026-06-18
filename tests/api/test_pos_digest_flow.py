"""
Step B — DIGEST: incremental sync must resolve product_id on line items.

Both providers' incremental sync used to build their mapper with an EMPTY
product lookup (Square's DB-load code existed but was dead — self.db was never
set; Clover had no load at all), so every incremental line item was stored with
product_id=NULL. The fix injects `engine.db` and loads the lookup from the
products table. These tests pin that the lookup is actually populated.

Run:  python -m pytest tests/api/test_pos_digest_flow.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

ORG = "168b6df2-e9af-4b00-8fec-51e51149ff19"


def _run(coro):
    return asyncio.run(coro)


class _FakeOrdersClient:
    async def list_orders(self, **kwargs):
        return []  # no orders → mapper.map_* never invoked; we only assert the lookup load
    async def close(self):
        pass


class _FakeDB:
    def __init__(self, products):
        self._products = products
    async def select(self, table, filters=None, limit=None):
        return self._products if table == "products" else []


def test_clover_incremental_loads_product_lookup(monkeypatch):
    from src.clover import sync_engine as se

    captured = {}

    class FakeMapper:
        def __init__(self, org_id, product_lookup=None, **kw):
            captured["lookup"] = product_lookup
        def map_order_to_transaction(self, order):  # pragma: no cover - no orders
            return {}
        def map_line_item(self, *a, **k):  # pragma: no cover
            return {}

    monkeypatch.setattr(se, "CloverDataMapper", FakeMapper)
    eng = se.CloverSyncEngine(client=_FakeOrdersClient(), org_id=ORG, pos_connection_id="C1")
    eng.db = _FakeDB([{"external_id": "itemA", "id": "prod-1"}, {"external_id": "itemB", "id": "prod-2"}])
    _run(eng.run_incremental_sync())
    assert captured["lookup"] == {"itemA": "prod-1", "itemB": "prod-2"}


def test_clover_incremental_without_db_is_safe(monkeypatch):
    """No db injected → empty lookup, no crash (product_id falls back to None)."""
    from src.clover import sync_engine as se

    captured = {}

    class FakeMapper:
        def __init__(self, org_id, product_lookup=None, **kw):
            captured["lookup"] = product_lookup
        def map_order_to_transaction(self, order):  # pragma: no cover
            return {}
        def map_line_item(self, *a, **k):  # pragma: no cover
            return {}

    monkeypatch.setattr(se, "CloverDataMapper", FakeMapper)
    eng = se.CloverSyncEngine(client=_FakeOrdersClient(), org_id=ORG, pos_connection_id="C1")
    _run(eng.run_incremental_sync())
    assert captured["lookup"] == {}


def test_square_incremental_db_load_is_now_active(monkeypatch):
    """Square's lookup-load was dead (self.db never set). With engine.db injected
    by the runner it now loads — pin that it reads products into the lookup."""
    from src.square import sync_engine as se

    captured = {}

    class FakeMapper:
        def __init__(self, org_id, location_lookup=None, product_lookup=None, employee_cache=None, pos_connection_id=None, **kw):
            captured["lookup"] = product_lookup
        def map_transaction(self, order):  # pragma: no cover
            return {}
        def map_transaction_items(self, *a, **k):  # pragma: no cover
            return []

    # Square's incremental references DataMapper; stub it to capture the lookup.
    monkeypatch.setattr(se, "DataMapper", FakeMapper, raising=False)

    class FakeSquareClient:
        async def list_locations(self):
            return []
        async def search_all_orders(self, **kw):
            return []
        async def close(self):
            pass

    eng = se.SyncEngine(client=FakeSquareClient(), org_id=ORG, pos_connection_id="S1")
    eng.db = _FakeDB([{"external_id": "varX", "id": "prod-9"}])
    _run(eng.run_incremental_sync())
    assert captured.get("lookup") == {"varX": "prod-9"}
