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


# ── Refunds: now emitted as type='refund' rows, NOT enrichment metadata ──

def test_square_payment_enrichment_no_longer_writes_refund_cents():
    """Refunds moved to discrete type='refund' transaction rows (the single
    source of truth daily_revenue reads). map_payment_enrichment must NOT also
    write metadata.refund_cents, which would double-count net revenue."""
    from src.square.mappers import DataMapper
    mapper = DataMapper(org_id=ORG)
    enr = mapper.map_payment_enrichment({
        "order_id": "o1",
        "refunded_money": {"amount": 4000, "currency": "USD"},
        "card_details": {"card": {"card_brand": "VISA", "last_4": "1234"}},
    })
    assert "refund_cents" not in enr.get("metadata_updates", {})
    # Other enrichment (card metadata) still flows through.
    assert enr["metadata_updates"]["card_brand"] == "VISA"
    assert enr["_order_id"] == "o1"


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


# ── Tax / discount / subtotal breakdown (Finding 5/7) ────────────────────

def test_clover_tax_summed_from_expanded_line_item_taxrates():
    # With expand=lineItems.taxRates, each line carries taxRates.elements[].taxAmount.
    from src.clover.mappers import CloverDataMapper
    mapper = CloverDataMapper(org_id=ORG)
    order = {
        "total": 1100, "state": "paid",
        "lineItems": {"elements": [
            {"id": "li1", "price": 1000,
             "taxRates": {"elements": [{"taxAmount": 100}]}},
        ]},
        "payments": {"elements": [{"tender": {"label": "Cash"}, "amount": 1100}]},
    }
    txn = mapper.map_order_to_transaction(order)
    assert txn["tax_cents"] == 100
    assert txn["total_cents"] == 1100
    assert txn["subtotal_cents"] == 1000  # total - tax - service_charge(0)


def test_clover_subtotal_excludes_tax_and_service_charge():
    from src.clover.mappers import CloverDataMapper
    mapper = CloverDataMapper(org_id=ORG)
    order = {
        "total": 5000, "state": "paid",
        "lineItems": {"elements": [
            {"id": "li1", "price": 3600, "taxRates": {"elements": [{"taxAmount": 500}]}},
        ]},
        "serviceCharges": {"elements": [{"name": "Auto Gratuity", "amount": 900}]},
        "payments": {"elements": [{"tender": {"label": "Credit Card"}, "amount": 5000}]},
    }
    txn = mapper.map_order_to_transaction(order)
    assert txn["tax_cents"] == 500
    assert txn["metadata"]["service_charge_cents"] == 900
    # 5000 total = 3600 subtotal + 500 tax + 900 service charge
    assert txn["subtotal_cents"] == 3600


def test_clover_order_level_discount_summed_from_expanded_discounts():
    from src.clover.mappers import CloverDataMapper
    mapper = CloverDataMapper(org_id=ORG)
    order = {
        "total": 900, "state": "paid",
        "discounts": {"elements": [{"name": "10% off", "amount": -100}]},
        "payments": {"elements": [{"tender": {"label": "Cash"}, "amount": 900}]},
    }
    txn = mapper.map_order_to_transaction(order)
    assert txn["discount_cents"] == 100  # abs() of -100


# ── Line-item refund flag uses `refunded`, not `isRevenue` (Finding 6) ────

def test_clover_line_item_refund_flag_uses_refunded_field():
    from src.clover.mappers import CloverDataMapper
    mapper = CloverDataMapper(org_id=ORG)
    refunded_line = {"id": "li1", "name": "X", "price": 500, "refunded": True}
    out = mapper.map_line_item(refunded_line, "txn-1", "2026-01-01T00:00:00+00:00")
    assert out["is_refund"] is True


def test_clover_non_revenue_item_is_not_flagged_as_refund():
    # isRevenue=false (a non-revenue item) must NOT be treated as a refund.
    from src.clover.mappers import CloverDataMapper
    mapper = CloverDataMapper(org_id=ORG)
    non_rev_line = {"id": "li2", "name": "Gift Card", "price": 2500,
                    "isRevenue": False}  # refunded absent
    out = mapper.map_line_item(non_rev_line, "txn-1", "2026-01-01T00:00:00+00:00")
    assert out["is_refund"] is False


# ── Clover refunds folded into transactions (net revenue accuracy) ──

class _Result:
    def __init__(self, txns):
        self.transactions = txns


def test_clover_refunds_appended_as_refund_rows(monkeypatch):
    """_apply_refunds now APPENDS type='refund' rows (so daily_revenue, which
    filters on type='refund', picks them up). It no longer writes
    metadata.refund_cents on the sale transactions — the refund rows are the
    single source of truth."""
    from src.clover import sync_engine as se
    from src.clover.mappers import _stable_id, _clover_ts_to_iso
    eng = se.CloverSyncEngine(client=_FakeOrdersClient(), org_id=ORG, pos_connection_id="C1")

    async def fake_list_refunds(start_time=None, end_time=None, max_items=None):
        return [
            {"id": "RF1", "orderRef": {"id": "ORD1"}, "amount": 4000,
             "taxAmount": 200, "tipAmount": 0, "createdTime": 1700000000000},
            {"id": "RF2", "orderRef": {"id": "ORD2"}, "amount": 1000,
             "createdTime": 1700000100000},
            {"amount": 999},  # no refund id → skipped
        ]
    eng.client.list_refunds = fake_list_refunds

    sale = {"external_id": "ORD1", "type": "sale", "metadata": {"tenders": []}}
    result = _Result([sale])
    _run(eng._apply_refunds(result, None, None))

    # The original sale row is untouched (no metadata.refund_cents).
    assert "refund_cents" not in result.transactions[0].get("metadata", {})
    # Two refund rows appended (the no-id one skipped).
    refunds = [t for t in result.transactions if t.get("type") == "refund"]
    assert len(refunds) == 2
    rf1 = next(t for t in refunds if t["external_id"] == "RF1")
    assert rf1["total_cents"] == 4000
    assert rf1["tax_cents"] == 200
    assert rf1["org_id"] == ORG
    assert rf1["pos_connection_id"] == "C1"
    # Deterministic id keyed on the refund id (re-sync upserts the same row).
    assert rf1["id"] == _stable_id(ORG, "clover", "refund:RF1")
    assert rf1["transaction_at"] == _clover_ts_to_iso(1700000000000)


def test_clover_refund_fetch_failure_is_nonfatal(monkeypatch):
    from src.clover import sync_engine as se
    eng = se.CloverSyncEngine(client=_FakeOrdersClient(), org_id=ORG, pos_connection_id="C1")

    async def boom(**kw):
        raise RuntimeError("clover 500")
    eng.client.list_refunds = boom

    result = _Result([{"external_id": "ORD1", "type": "sale"}])
    _run(eng._apply_refunds(result, None, None))  # must not raise
    assert "refund_cents" not in result.transactions[0].get("metadata", {})
    # No refund rows appended on a fetch failure.
    assert [t for t in result.transactions if t.get("type") == "refund"] == []


# ── Row identity: deterministic + distinct so upserts don't dup or clobber ──

def test_clover_ids_deterministic_and_distinct():
    from src.clover.mappers import CloverDataMapper
    m = CloverDataMapper(org_id=ORG)
    order = {"id": "ORD9", "total": 1000, "state": "paid", "payments": {"elements": []}}
    t1 = m.map_order_to_transaction(order)
    t2 = m.map_order_to_transaction(order)
    assert t1["id"] == t2["id"] and t1["external_id"] == "ORD9"   # re-sync idempotent
    li = lambda lid: m.map_line_item({"id": lid, "name": "X", "price": 500, "unitQty": 1000}, t1["id"], t1["transaction_at"])
    assert li("LI1")["id"] == li("LI1")["id"]                     # same line → same id
    assert li("LI1")["id"] != li("LI2")["id"]                     # distinct lines → distinct id
    assert "external_id" not in li("LI1")                         # no such column on transaction_items


def test_square_ids_deterministic_and_distinct():
    from src.square.mappers import DataMapper
    m = DataMapper(org_id=ORG)
    order = {
        "id": "SQ9", "state": "COMPLETED", "created_at": "2026-01-01T00:00:00Z", "location_id": "L1",
        "total_money": {"amount": 1000}, "total_tax_money": {"amount": 0},
        "total_tip_money": {"amount": 0}, "total_discount_money": {"amount": 0}, "tenders": [],
        "line_items": [
            {"uid": "u1", "name": "A", "quantity": "1", "base_price_money": {"amount": 500}, "total_money": {"amount": 500}},
            {"uid": "u2", "name": "B", "quantity": "1", "base_price_money": {"amount": 500}, "total_money": {"amount": 500}},
        ],
    }
    t1 = m.map_transaction(order)
    t2 = m.map_transaction(order)
    assert t1["id"] == t2["id"]                                   # re-sync idempotent
    r1 = m.map_transaction_items(order, t1["id"], t1["transaction_at"])
    r2 = m.map_transaction_items(order, t2["id"], t2["transaction_at"])
    assert [r["id"] for r in r1] == [r["id"] for r in r2]         # idempotent
    assert len({r["id"] for r in r1}) == 2                        # distinct lines distinct ids


def test_same_external_id_across_providers_does_not_collide():
    from src.clover.mappers import CloverDataMapper
    from src.square.mappers import DataMapper
    cl = CloverDataMapper(org_id=ORG).map_order_to_transaction(
        {"id": "DUP", "total": 0, "state": "paid", "payments": {"elements": []}})
    sq = DataMapper(org_id=ORG).map_transaction(
        {"id": "DUP", "state": "COMPLETED", "created_at": "2026-01-01T00:00:00Z", "location_id": "L",
         "total_money": {"amount": 0}, "total_tax_money": {"amount": 0},
         "total_tip_money": {"amount": 0}, "total_discount_money": {"amount": 0}, "tenders": []})
    assert cl["external_id"] == sq["external_id"] == "DUP"
    assert cl["id"] != sq["id"]                                   # provider in id → no clobber


# ── Propagate (Step C): transaction_items conflict key unified everywhere ──

def test_transaction_items_conflict_key_unified():
    """Every transaction_items upsert (backfill, incremental, webhook) must key
    on (id,transaction_at). A split key (some on org_id,external_id) could
    double-write a line item. Pins the unification."""
    import inspect
    import re
    from src.api.routes import pos_connections, webhooks
    for mod in (pos_connections, webhooks):
        src = inspect.getsource(mod)
        keys = re.findall(r'batch_upsert\(\s*"transaction_items".*?on_conflict="([^"]+)"', src, re.S)
        assert keys, f"{mod.__name__}: no transaction_items upsert found"
        for k in keys:
            assert k == "id,transaction_at", f"{mod.__name__}: transaction_items keyed on {k}"


# ── Step C: _write_sync_result — one FK-safe, flag-gated write path ──

class _WriteDB:
    def __init__(self, rpc_raises=False):
        self.calls = []
        self._rpc_raises = rpc_raises
    async def batch_upsert(self, table, rows, on_conflict=None):
        self.calls.append(table)
    async def rpc(self, name, args):
        self.calls.append(("rpc", name))
        if self._rpc_raises:
            raise RuntimeError("no such function: " + name)


class _SyncResult:
    def __init__(self, products, transactions, items):
        self.products = products
        self.transactions = transactions
        self.transaction_items = items


def test_write_sync_result_sequential_by_default(monkeypatch):
    monkeypatch.delenv("POS_ATOMIC_WRITE", raising=False)
    from src.api.routes import pos_connections as pc
    db = _WriteDB()
    _run(pc._write_sync_result(db, _SyncResult([{"a": 1}], [{"b": 2}], [{"c": 3}])))
    assert db.calls == ["products", "transactions", "transaction_items"]  # FK order, no rpc


def test_write_sync_result_atomic_when_enabled(monkeypatch):
    monkeypatch.setenv("POS_ATOMIC_WRITE", "1")
    from src.api.routes import pos_connections as pc
    db = _WriteDB()
    _run(pc._write_sync_result(db, _SyncResult([{"a": 1}], [], [])))
    assert db.calls == [("rpc", "pos_sync_upsert")]  # one atomic call, no sequential


def test_write_sync_result_falls_back_on_rpc_error(monkeypatch):
    monkeypatch.setenv("POS_ATOMIC_WRITE", "1")
    from src.api.routes import pos_connections as pc
    db = _WriteDB(rpc_raises=True)
    _run(pc._write_sync_result(db, _SyncResult([{"a": 1}], [{"b": 2}], [])))
    assert db.calls == [("rpc", "pos_sync_upsert"), "products", "transactions"]  # fell back


def test_write_sync_result_noop_when_empty(monkeypatch):
    monkeypatch.delenv("POS_ATOMIC_WRITE", raising=False)
    from src.api.routes import pos_connections as pc
    db = _WriteDB()
    _run(pc._write_sync_result(db, _SyncResult([], [], [])))
    assert db.calls == []


# ── Clover region support: connect to NA / EU / LATAM merchant hosts ──

def test_clover_region_hosts():
    from src.config import CloverConfig
    # production routes to the merchant's regional host
    assert CloverConfig(environment="production", region="na").api_base_url == "https://api.clover.com"
    assert CloverConfig(environment="production", region="eu").api_base_url == "https://api.eu.clover.com"
    assert CloverConfig(environment="production", region="eu").base_url == "https://eu.clover.com"
    assert CloverConfig(environment="production", region="la").api_base_url == "https://api.la.clover.com"
    # unknown region falls back to NA (US + Canada)
    assert CloverConfig(environment="production", region="xx").api_base_url == "https://api.clover.com"
    # sandbox is region-agnostic
    assert CloverConfig(environment="sandbox", region="eu").api_base_url == "https://apisandbox.dev.clover.com"
