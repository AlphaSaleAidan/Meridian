"""
Refunds-as-rows + reconciliation + connection-status lifecycle.

Plain functions + asyncio.run (no pytest-asyncio), mirroring
tests/api/test_pos_digest_flow.py.

Covers:
  - Square refund fetch → type='refund' rows (only COMPLETED), deterministic id.
  - reconcile_square: match (diff 0 → ok) and mismatch (→ not ok).
  - Connection status lifecycle: backfill success → historical_import_complete,
    failure → status='error' + last_error.

Run:  python -m pytest tests/api/test_refunds_reconcile.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

ORG = "168b6df2-e9af-4b00-8fec-51e51149ff19"


def _run(coro):
    return asyncio.run(coro)


# ── Square refunds → type='refund' rows ──────────────────────────────────────

class _Result:
    def __init__(self, txns=None):
        self.transactions = txns or []
        self.errors = []


def test_square_refunds_appended_as_refund_rows():
    from src.square.sync_engine import SyncEngine
    from src.square.mappers import _stable_id

    class FakeClient:
        async def list_all_refunds(self, begin_time=None, end_time=None, location_id=None):
            return [
                {"id": "RF1", "amount_money": {"amount": 4000}, "status": "COMPLETED",
                 "created_at": "2026-01-02T00:00:00Z", "location_id": "LSQ1"},
                {"id": "RF2", "amount_money": {"amount": 1500}, "status": "PENDING",
                 "created_at": "2026-01-03T00:00:00Z", "location_id": "LSQ1"},  # not COMPLETED → skip
                {"amount_money": {"amount": 999}, "status": "COMPLETED"},        # no id → skip
            ]

    eng = SyncEngine(client=FakeClient(), org_id=ORG, pos_connection_id="S1")
    result = _Result()
    _run(eng._apply_refunds(
        result,
        location_ids=["LSQ1"],
        begin_time="2026-01-01T00:00:00Z",
        location_lookup={"LSQ1": "loc-uuid-1"},
    ))

    refunds = [t for t in result.transactions if t.get("type") == "refund"]
    assert len(refunds) == 1  # only the COMPLETED, id-bearing one
    rf = refunds[0]
    assert rf["external_id"] == "RF1"
    assert rf["total_cents"] == 4000
    assert rf["type"] == "refund"
    assert rf["org_id"] == ORG
    assert rf["pos_connection_id"] == "S1"
    assert rf["location_id"] == "loc-uuid-1"   # resolved via lookup
    assert rf["transaction_at"] == "2026-01-02T00:00:00Z"
    assert rf["id"] == _stable_id(ORG, "square", "refund:RF1")


def test_square_refund_fetch_failure_is_nonfatal():
    from src.square.sync_engine import SyncEngine

    class BoomClient:
        async def list_all_refunds(self, **kw):
            raise RuntimeError("square 500")

    eng = SyncEngine(client=BoomClient(), org_id=ORG, pos_connection_id="S1")
    result = _Result([{"external_id": "o1", "type": "sale"}])
    _run(eng._apply_refunds(result, location_ids=["L"], begin_time="x"))  # must not raise
    assert [t for t in result.transactions if t.get("type") == "refund"] == []


def test_square_refund_id_is_deterministic_and_distinct_from_clover():
    """Same refund id across providers must not collide (provider is in the key);
    re-running yields the same id (idempotent upsert)."""
    from src.square.mappers import _stable_id as sq_id
    from src.clover.mappers import _stable_id as cl_id
    a = sq_id(ORG, "square", "refund:DUP")
    b = sq_id(ORG, "square", "refund:DUP")
    c = cl_id(ORG, "clover", "refund:DUP")
    assert a == b          # idempotent
    assert a != c          # provider-namespaced → no clobber


# ── reconcile_square: match / mismatch ───────────────────────────────────────

class _FakeReconcileDB:
    """get_daily_revenue returns net per-day rows (total_revenue_cents)."""
    def __init__(self, daily_rows):
        self._daily = daily_rows
    async def get_daily_revenue(self, org_id, days=30):
        return self._daily
    async def select(self, table, columns="*", filters=None, **kw):  # pragma: no cover
        return []


class _FakeSquareForReconcile:
    """list_payments paginates; only COMPLETED count toward truth."""
    def __init__(self, pages):
        self._pages = list(pages)
    async def list_payments(self, cursor=None, **kw):
        if not self._pages:
            return [], None
        page = self._pages.pop(0)
        next_cursor = "c" if self._pages else None
        return page, next_cursor


def test_reconcile_square_match():
    from src.services.reconcile import reconcile_square
    db = _FakeReconcileDB([
        {"total_revenue_cents": 6000},
        {"total_revenue_cents": 4000},
    ])  # ours = 10000
    client = _FakeSquareForReconcile([
        [{"status": "COMPLETED", "amount_money": {"amount": 7000}}],
        [{"status": "COMPLETED", "amount_money": {"amount": 3000}},
         {"status": "FAILED", "amount_money": {"amount": 9999}}],  # ignored
    ])  # truth = 10000
    report = _run(reconcile_square(db, ORG, client))
    assert report["ours_cents"] == 10000
    assert report["truth_cents"] == 10000
    assert report["diff_cents"] == 0
    assert report["ok"] is True
    assert report["org_id"] == ORG


def test_reconcile_square_mismatch():
    from src.services.reconcile import reconcile_square
    db = _FakeReconcileDB([{"total_revenue_cents": 10000}])  # ours = 10000
    client = _FakeSquareForReconcile([
        [{"status": "COMPLETED", "amount_money": {"amount": 5000}}],  # truth = 5000
    ])
    report = _run(reconcile_square(db, ORG, client))
    assert report["ours_cents"] == 10000
    assert report["truth_cents"] == 5000
    assert report["diff_cents"] == 5000
    assert report["ok"] is False


def test_reconcile_square_within_tolerance_is_ok():
    from src.services.reconcile import reconcile_square
    db = _FakeReconcileDB([{"total_revenue_cents": 10050}])
    client = _FakeSquareForReconcile([
        [{"status": "COMPLETED", "amount_money": {"amount": 10000}}],
    ])
    report = _run(reconcile_square(db, ORG, client))  # diff 50 <= tol 100
    assert report["ok"] is True


def test_reconcile_square_falls_back_to_sale_sum(monkeypatch):
    """If daily_revenue read fails, ours = sum of type='sale' transactions."""
    from src.services.reconcile import reconcile_square

    class FallbackDB:
        async def get_daily_revenue(self, org_id, days=30):
            raise RuntimeError("matview missing")
        async def select(self, table, columns="*", filters=None, **kw):
            assert filters.get("type") == "eq.sale"
            return [{"total_cents": 3000}, {"total_cents": 2000}]  # 5000

    client = _FakeSquareForReconcile([
        [{"status": "COMPLETED", "amount_money": {"amount": 5000}}],
    ])
    report = _run(reconcile_square(FallbackDB(), ORG, client))
    assert report["ours_cents"] == 5000
    assert report["ok"] is True


# ── Connection status lifecycle (pending / complete / failed) ────────────────

class _FakeConnDB:
    """Captures pos_connections.update payloads + supports the backfill writes."""
    def __init__(self):
        self.conn_updates: list[dict] = []
        self.other = []
    async def update(self, table, payload, filters=None):
        if table == "pos_connections":
            self.conn_updates.append(payload)
        else:
            self.other.append((table, payload))
    async def batch_upsert(self, table, rows, on_conflict=None):
        self.other.append(("upsert", table))
    async def select(self, table, filters=None, limit=None, **kw):
        return []
    async def insert(self, table, rows, return_data=True):
        self.other.append(("insert", table))


def test_clover_backfill_success_sets_import_complete(monkeypatch):
    from src.api.routes import pos_connections as pc

    db = _FakeConnDB()
    monkeypatch.setattr(pc, "get_db", lambda: db, raising=False)
    # get_db is imported inside the function from ...db; patch that source too.
    import src.db as dbmod
    monkeypatch.setattr(dbmod, "get_db", lambda: db, raising=False)

    class FakeResult:
        products = []
        transactions = []
        transaction_items = []
        employee_cache = {}
        summary = {}

    class FakeEngine:
        def __init__(self, **kw):
            pass
        async def run_initial_backfill(self):
            return FakeResult()

    class FakeClient:
        def __init__(self, **kw):
            pass
        async def close(self):
            pass

    import src.clover.client as clc
    import src.clover.sync_engine as clse
    monkeypatch.setattr(clc, "CloverClient", FakeClient, raising=False)
    monkeypatch.setattr(clse, "CloverSyncEngine", FakeEngine, raising=False)
    # Skip the AI pipeline (imported lazily) — make it a no-op import failure path.
    import src.live_pipeline as lp

    class NoopPipeline:
        def __init__(self, **kw):
            pass
        async def run_analysis_only(self):
            return None
    monkeypatch.setattr(lp, "MeridianPipeline", NoopPipeline, raising=False)

    _run(pc._run_clover_backfill(ORG, "CONN1", access_token="t", merchant_id="m"))

    # The terminal pos_connections update marks the import complete + clears error.
    success = [u for u in db.conn_updates if u.get("historical_import_complete") is True]
    assert success, f"no success update found in {db.conn_updates}"
    assert success[-1]["status"] == "connected"
    assert success[-1]["last_error"] is None


def test_clover_backfill_failure_sets_error_status(monkeypatch):
    from src.api.routes import pos_connections as pc

    db = _FakeConnDB()
    import src.db as dbmod
    monkeypatch.setattr(dbmod, "get_db", lambda: db, raising=False)

    class FakeClient:
        def __init__(self, **kw):
            pass
        async def close(self):
            pass

    class BoomEngine:
        def __init__(self, **kw):
            pass
        async def run_initial_backfill(self):
            raise RuntimeError("clover token expired")

    import src.clover.client as clc
    import src.clover.sync_engine as clse
    monkeypatch.setattr(clc, "CloverClient", FakeClient, raising=False)
    monkeypatch.setattr(clse, "CloverSyncEngine", BoomEngine, raising=False)

    _run(pc._run_clover_backfill(ORG, "CONN1", access_token="t", merchant_id="m"))

    # On failure the connection is flipped to status='error' with last_error set.
    failures = [u for u in db.conn_updates if u.get("status") == "error"]
    assert failures, f"no error update found in {db.conn_updates}"
    assert "clover token expired" in failures[-1]["last_error"]
    # And it must NOT have been marked import-complete.
    assert not any(u.get("historical_import_complete") is True for u in db.conn_updates)


def test_derive_connection_state():
    from src.api.routes.pos_connections import _derive_connection_state
    assert _derive_connection_state("connected", False) == "pending"
    assert _derive_connection_state("connected", True) == "complete"
    assert _derive_connection_state("error", True) == "failed"
    assert _derive_connection_state("error", False) == "failed"
    assert _derive_connection_state("disconnected", False) == "disconnected"
    assert _derive_connection_state(None, False) == "unknown"
