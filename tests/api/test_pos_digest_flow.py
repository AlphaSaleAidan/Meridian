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


# ── Multi-tender: split payments must not be reduced to the first tender ──

def test_clover_split_payment_captures_all_tenders():
    from src.clover.mappers import CloverDataMapper
    mapper = CloverDataMapper(org_id=ORG)
    order = {
        "total": 3000, "state": "paid",
        "payments": {"elements": [
            {"tender": {"label": "Cash"}, "amount": 1000, "tipAmount": 0},
            {"tender": {"label": "Credit Card"}, "amount": 2000, "tipAmount": 300},
        ]},
    }
    txn = mapper.map_order_to_transaction(order)
    assert txn["payment_method"] == "cash"  # primary = first tender
    assert txn["metadata"]["tenders"] == [
        {"type": "cash", "amount_cents": 1000, "tip_cents": 0},
        {"type": "card", "amount_cents": 2000, "tip_cents": 300},
    ]


def test_square_split_payment_captures_all_tenders():
    from src.square.mappers import DataMapper
    mapper = DataMapper(org_id=ORG)
    order = {
        "id": "o1", "state": "COMPLETED", "created_at": "2026-01-01T00:00:00Z",
        "location_id": "L1",
        "total_money": {"amount": 3000, "currency": "USD"},
        "total_tax_money": {"amount": 0}, "total_tip_money": {"amount": 0},
        "total_discount_money": {"amount": 0},
        "tenders": [
            {"type": "CARD", "amount_money": {"amount": 2000}, "employee_id": "e1",
             "card_details": {"card": {"card_brand": "VISA"}}},
            {"type": "CASH", "amount_money": {"amount": 1000}, "employee_id": "e1"},
        ],
    }
    txn = mapper.map_transaction(order)
    assert txn["payment_method"] == "credit_card"  # primary = first tender
    assert txn["metadata"]["tenders"] == [
        {"type": "credit_card", "amount_cents": 2000, "employee_id": "e1"},
        {"type": "cash", "amount_cents": 1000, "employee_id": "e1"},
    ]
    assert txn["metadata"]["card_brand"] == "VISA"


# ── Refunds: Square refunded_money captured so net revenue isn't overstated ──

def test_square_payment_enrichment_captures_refund():
    from src.square.mappers import DataMapper
    mapper = DataMapper(org_id=ORG)
    enr = mapper.map_payment_enrichment({
        "order_id": "o1",
        "refunded_money": {"amount": 4000, "currency": "USD"},
        "card_details": {"card": {"card_brand": "VISA", "last_4": "1234"}},
    })
    assert enr["metadata_updates"]["refund_cents"] == 4000
    assert enr["_order_id"] == "o1"


def test_square_payment_enrichment_no_refund_omits_field():
    from src.square.mappers import DataMapper
    mapper = DataMapper(org_id=ORG)
    enr = mapper.map_payment_enrichment({"order_id": "o2"})
    assert "refund_cents" not in enr.get("metadata_updates", {})


# ── Clover service charges + device: revenue + multi-register attribution ──

def test_clover_captures_service_charge_and_device():
    from src.clover.mappers import CloverDataMapper
    mapper = CloverDataMapper(org_id=ORG)
    order = {
        "total": 5000, "state": "paid",
        "payments": {"elements": [{"tender": {"label": "Credit Card"}, "amount": 5000}]},
        "serviceCharges": {"elements": [{"name": "Auto Gratuity", "amount": 900}]},
        "device": {"id": "DEV-7"},
    }
    txn = mapper.map_order_to_transaction(order)
    assert txn["metadata"]["service_charge_cents"] == 900
    assert txn["metadata"]["device_id"] == "DEV-7"


def test_clover_no_service_charge_or_device_omits_fields():
    from src.clover.mappers import CloverDataMapper
    mapper = CloverDataMapper(org_id=ORG)
    order = {"total": 1000, "state": "paid",
             "payments": {"elements": [{"tender": {"label": "Cash"}, "amount": 1000}]}}
    txn = mapper.map_order_to_transaction(order)
    assert "service_charge_cents" not in txn["metadata"]
    assert "device_id" not in txn["metadata"]
