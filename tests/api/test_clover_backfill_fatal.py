"""Regression tests: Clover backfill must not report success after a fatal error.

CloverSyncEngine.run_initial_backfill never raises — it folds fatal exceptions
into result.errors ("fatal: ..."). _run_clover_backfill then unconditionally
wrote historical_import_complete=true / status=connected, so a backfill whose
orders pull died wholesale surfaced as "connected, no data" with no reason why —
the exact Square bug fixed in f0609688 (workers/backfill.py), unmirrored for
Clover.

Fix under test (src/api/routes/pos_connections.py::_run_clover_backfill):
  1. fatal entry in result.errors  → status=error + last_error, NO
     historical_import_complete write, and the connected flags the dashboard
     gates on are reverted (businesses.pos_connected=false,
     organizations.pos_connection_status=error).
  2. clean result                  → historical_import_complete=true,
     status=connected, last_error cleared.
  3. non-fatal errors only (e.g. "inventory: ...") → still completes; phase
     errors are best-effort by design.

Run:  python -m pytest tests/api/test_clover_backfill_fatal.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import src.clover.client as clover_client_mod  # noqa: E402
import src.clover.sync_engine as sync_engine_mod  # noqa: E402
import src.db as db_mod  # noqa: E402
from src.api.routes import pos_connections as pc  # noqa: E402
from src.integrations.base.models import SyncResult  # noqa: E402

ORG = "biz_test_clover"
CONN = "conn-1"


class FakeDB:
    """Records every write; returns empty results for reads."""

    def __init__(self):
        self.updates: list[tuple[str, dict, dict]] = []

    async def update(self, table, data, filters=None):
        self.updates.append((table, data, filters or {}))
        return []

    async def upsert(self, *a, **kw):
        return []

    async def insert(self, *a, **kw):
        return []

    async def select(self, *a, **kw):
        return []

    async def rpc(self, *a, **kw):
        raise RuntimeError("no RPC in tests")

    def updates_for(self, table):
        return [d for t, d, _ in self.updates if t == table]


class FakeClient:
    def __init__(self, **kw):
        pass

    async def close(self):
        pass


def _fake_engine_returning(errors: list[str]):
    class FakeEngine:
        def __init__(self, **kw):
            pass

        async def run_initial_backfill(self):
            r = SyncResult()
            r.errors.extend(errors)
            return r

    return FakeEngine


def _run_backfill(monkeypatch, errors: list[str]) -> FakeDB:
    db = FakeDB()
    monkeypatch.setattr(db_mod, "get_db", lambda: db)
    monkeypatch.setattr(clover_client_mod, "CloverClient", FakeClient)
    monkeypatch.setattr(sync_engine_mod, "CloverSyncEngine", _fake_engine_returning(errors))
    asyncio.run(pc._run_clover_backfill(ORG, CONN, "tok", "MID"))
    return db


def test_fatal_error_marks_connection_error_not_complete(monkeypatch):
    db = _run_backfill(monkeypatch, ["fatal: orders pull 401"])

    conn_updates = db.updates_for("pos_connections")
    assert conn_updates, "connection must be updated on fatal failure"
    final = conn_updates[-1]
    assert final["status"] == "error"
    assert "fatal: orders pull 401" in final["last_error"]
    assert not any(
        u.get("historical_import_complete") for u in conn_updates
    ), "a fatally failed backfill must never be marked complete"

    # dashboard-gating flags reverted so the portal prompts a reconnect (f0609688)
    assert {"pos_connected": False} in db.updates_for("businesses")
    assert {"pos_connection_status": "error"} in db.updates_for("organizations")


def test_clean_result_marks_complete_and_connected(monkeypatch):
    db = _run_backfill(monkeypatch, [])

    conn_updates = db.updates_for("pos_connections")
    assert any(u.get("historical_import_complete") is True for u in conn_updates)
    final = next(u for u in conn_updates if u.get("historical_import_complete"))
    assert final["status"] == "connected"
    assert final["last_error"] is None
    assert not db.updates_for("businesses"), "no flag reverts on success"


def test_nonfatal_phase_errors_still_complete(monkeypatch):
    db = _run_backfill(monkeypatch, ["inventory: item_stocks 404", "employees: timeout"])

    conn_updates = db.updates_for("pos_connections")
    assert any(u.get("historical_import_complete") is True for u in conn_updates)
    assert not any(u.get("status") == "error" for u in conn_updates)
