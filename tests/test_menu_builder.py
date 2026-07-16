"""
AUTO MENU-BUILDER — backend coverage.

When a merchant connects their POS, the phone-agent menu is auto-built from the
POS catalog (read-only) and the customer account can poll a status endpoint to
watch it populate. This proves, from several directions:

  1. Connect auto-triggers the build (a background task targeting the shared
     extraction helper is scheduled by /connect).
  2. The shared extraction helper is called exactly once per connect.
  3. GET /menu/status transitions building → ready and reports item_count + sample.
  4. Error path: extraction failure → connect still succeeds (best-effort), and
     a missing-creds build returns synced=False without raising.

Pattern mirrors tests/api/test_pos_connect_flow.py: call the functions directly
with a fake DB, run via asyncio.run (no pytest-asyncio).

Run:  python -m pytest tests/test_menu_builder.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest
from fastapi import BackgroundTasks

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.pop("TENANCY_ENFORCEMENT_DISABLED", None)

import src.db as db_mod  # noqa: E402
from src.api import auth  # noqa: E402
from src.api.routes import pos_connections as pc_mod  # noqa: E402
from src.api.routes import phone_dashboard as pd_mod  # noqa: E402
from src.api.routes.pos_connections import connect_pos, ConnectRequest  # noqa: E402
from src.api.routes.phone_dashboard import (  # noqa: E402
    auto_build_menu_on_connect,
    get_menu_status,
    sync_menu_from_pos,
)

ORG = "168b6df2-e9af-4b00-8fec-51e51149ff19"
USER = {"id": "user-1", "email": "rep@example.com"}


def _run(coro):
    return asyncio.run(coro)


def _row_matches(row: dict, filters: dict | None) -> bool:
    """Minimal PostgREST filter emulation (eq. / is.true / is.false)."""
    for col, expr in (filters or {}).items():
        if expr.startswith("eq."):
            if str(row.get(col)) != expr[3:]:
                return False
        elif expr in ("is.true", "is.false"):
            if bool(row.get(col)) is not (expr == "is.true"):
                return False
    return True


class FakeDB:
    """Records writes; serves canned reads. `config_row` is the current
    phone_agent_config row state (mutated by update/insert). `menu_rows`
    models the normalized menu_items store the sync now writes through."""

    def __init__(self, config_row=None, connection=None, existing_org=True):
        self.inserts, self.updates, self.batch = [], [], []
        self.config_row = dict(config_row) if config_row else None
        self.menu_rows: list[dict] = []
        self._connection = connection
        self._existing_org = existing_org

    async def select(self, table, filters=None, limit=None, order=None, offset=None):
        if table == "phone_agent_config":
            return [self.config_row] if self.config_row else []
        if table == "pos_connections":
            return [self._connection] if self._connection else []
        if table == "organizations":
            return [{"id": ORG}] if self._existing_org else []
        if table == "menu_items":
            rows = [dict(r) for r in self.menu_rows if _row_matches(r, filters)]
            return rows[:limit] if limit else rows
        return []

    async def insert(self, table, row, return_data=True):
        self.inserts.append((table, row))
        if table == "phone_agent_config":
            self.config_row = dict(row)
        if table == "menu_items":
            import uuid as _uuid
            rows = row if isinstance(row, list) else [row]
            for r in rows:
                r = dict(r)
                r.setdefault("id", str(_uuid.uuid4()))
                self.menu_rows.append(r)
        return [row] if isinstance(row, dict) else row

    async def delete(self, table, filters=None):
        if table == "menu_items":
            self.menu_rows = [r for r in self.menu_rows if not _row_matches(r, filters)]
        return True

    async def update(self, table, vals, filters=None):
        self.updates.append((table, vals, filters))
        if table == "menu_items":
            for r in self.menu_rows:
                if _row_matches(r, filters):
                    r.update(vals)
        if table == "phone_agent_config" and self.config_row is not None:
            self.config_row.update(vals)

    async def batch_upsert(self, table, rows, on_conflict=None):
        self.batch.append((table, rows, on_conflict))


def _set_member(monkeypatch, is_member: bool):
    async def _check(user, org_id):
        return is_member
    monkeypatch.setattr(auth, "_check_org_membership", _check)


def _enable_clover(monkeypatch):
    """Flip the coherent Clover gate on for the manual-connect path. cl_config is
    a frozen dataclass, so swap the module-level reference the route reads."""
    from types import SimpleNamespace
    monkeypatch.setattr(pc_mod, "cl_config", SimpleNamespace(is_enabled=True))


def _patch_extractor(monkeypatch, items, counter):
    """Patch the menu_extractor.extract_menu_items the helper imports lazily."""
    from src.services.pos_connectors import menu_extractor

    async def _fake_extract(system_key, access_token, **kwargs):
        counter.append((system_key, access_token, kwargs))
        return list(items)

    monkeypatch.setattr(menu_extractor, "extract_menu_items", _fake_extract)


# ── 1. Connect schedules the auto menu-build ─────────────────────────────

def test_connect_schedules_menu_autobuild(monkeypatch):
    _set_member(monkeypatch, True)
    _enable_clover(monkeypatch)
    db = FakeDB()
    db_mod._db_instance = db
    bt = BackgroundTasks()
    req = ConnectRequest(org_id=ORG, pos_system="clover",
                         credentials={"access_token": "cl-tok", "merchant_id": "M1"})
    _run(connect_pos(req, bt, user=USER))

    names = [getattr(t.func, "__name__", "") for t in bt.tasks]
    assert "_auto_build_phone_menu" in names, names
    # the auto-build task is dispatched with the org_id (== merchant_id)
    auto = [t for t in bt.tasks if getattr(t.func, "__name__", "") == "_auto_build_phone_menu"][0]
    assert auto.kwargs.get("org_id", None) == ORG or (auto.args and auto.args[0] == ORG)


# ── 2. Shared extraction helper called once per connect ──────────────────

def test_autobuild_calls_shared_extractor_once(monkeypatch):
    db = FakeDB(
        config_row=None,
        connection={"provider": "clover", "external_merchant_id": "M1",
                    "credentials_encrypted": {"access_token": _enc("cl-tok")}},
    )
    db_mod._db_instance = db
    calls: list = []
    _patch_extractor(monkeypatch, [{"name": "Latte", "price": 4.5}], calls)

    _run(auto_build_menu_on_connect(ORG))

    assert len(calls) == 1, calls
    # menu stored onto phone_agent_config
    cfg_writes = [r for (t, r) in db.inserts if t == "phone_agent_config"]
    assert cfg_writes and cfg_writes[0]["menu_items"][0]["name"] == "Latte"


def test_autobuild_ignores_non_uuid_merchant(monkeypatch):
    db = FakeDB()
    db_mod._db_instance = db
    calls: list = []
    _patch_extractor(monkeypatch, [{"name": "X"}], calls)
    _run(auto_build_menu_on_connect("demo"))  # not a UUID → skip
    assert calls == []


# ── 3. status: building → ready ──────────────────────────────────────────

def test_status_building_then_ready(monkeypatch):
    # Empty config to start → idle.
    db = FakeDB(config_row={"merchant_id": ORG})
    db_mod._db_instance = db

    s0 = _run(get_menu_status(ORG, principal={"kind": "admin"}))
    assert s0["state"] == "idle" and s0["item_count"] == 0

    # While a build is in flight the in-process set marks it 'building'.
    pd_mod._MENU_BUILDING.add(ORG)
    try:
        s1 = _run(get_menu_status(ORG, principal={"kind": "admin"}))
        assert s1["state"] == "building"
    finally:
        pd_mod._MENU_BUILDING.discard(ORG)

    # After the menu is stored → ready, with item_count + sample names.
    db.config_row = {
        "merchant_id": ORG,
        "menu_items": [
            {"name": "Espresso", "price": 3.0},
            {"name": "Latte", "price": 4.5},
            {"name": "Cold Brew", "price": 5.0},
        ],
        "updated_at": "2026-06-21T00:00:00Z",
    }
    s2 = _run(get_menu_status(ORG, principal={"kind": "admin"}))
    assert s2["state"] == "ready"
    assert s2["item_count"] == 3
    assert s2["sample"][:3] == ["Espresso", "Latte", "Cold Brew"]


def test_status_clears_building_after_sync(monkeypatch):
    """The shared impl must remove the merchant from the building set when done,
    so a later status poll doesn't report 'building' forever."""
    db = FakeDB(
        config_row={"merchant_id": ORG},
        connection={"provider": "clover", "external_merchant_id": "M1",
                    "credentials_encrypted": {"access_token": _enc("cl-tok")}},
    )
    db_mod._db_instance = db
    calls: list = []
    _patch_extractor(monkeypatch, [{"name": "Soda"}], calls)

    _run(sync_menu_from_pos(ORG, principal={"kind": "admin"}))  # manual endpoint uses the same shared impl
    assert ORG not in pd_mod._MENU_BUILDING

    s = _run(get_menu_status(ORG, principal={"kind": "admin"}))
    assert s["state"] == "ready" and s["item_count"] == 1


# ── 4. Error / no-creds paths never break connect ────────────────────────

def test_autobuild_swallows_extractor_error(monkeypatch):
    db = FakeDB(
        config_row=None,
        connection={"provider": "clover", "external_merchant_id": "M1",
                    "credentials_encrypted": {"access_token": _enc("cl-tok")}},
    )
    db_mod._db_instance = db

    from src.services.pos_connectors import menu_extractor

    async def _boom(*a, **k):
        raise RuntimeError("POS down")
    monkeypatch.setattr(menu_extractor, "extract_menu_items", _boom)

    # Must NOT raise — auto-build is best-effort.
    _run(auto_build_menu_on_connect(ORG))
    # and the building flag is cleared even on failure
    assert ORG not in pd_mod._MENU_BUILDING


def test_sync_no_credentials_returns_unsynced():
    db = FakeDB(config_row={"merchant_id": ORG})  # no creds, no connection
    db_mod._db_instance = db
    out = _run(sync_menu_from_pos(ORG, principal={"kind": "admin"}))
    assert out["synced"] is False
    assert out["item_count"] == 0


def test_connect_succeeds_even_if_autobuild_would_fail(monkeypatch):
    """Connect returns success regardless of the menu build outcome — the build
    is a scheduled background task, decoupled from the connect response."""
    _set_member(monkeypatch, True)
    _enable_clover(monkeypatch)
    db = FakeDB()
    db_mod._db_instance = db
    bt = BackgroundTasks()
    req = ConnectRequest(org_id=ORG, pos_system="clover",
                         credentials={"access_token": "t", "merchant_id": "M1"})
    out = _run(connect_pos(req, bt, user=USER))
    assert out["success"] is True and out["syncing"] is True


# ── helper: encrypt a token so _decrypt_connection_token can read it ──────

def _enc(plaintext: str) -> str:
    from src.security.encryption import encrypt_token
    return encrypt_token(plaintext)
