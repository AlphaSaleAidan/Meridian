"""
Step A — POS CONNECT flow, multiple angles, both providers (Square + Clover).

Proves the connect/disconnect functionality holds up from several directions:
  1. Tenancy: /connect + /disconnect reject a caller who isn't an org member.
  2. Storage: connect writes a pos_connections row + mirrors the gate flags.
  3. Teardown: disconnect closes BOTH gate fields and clears the token (manual
     path with org_id, and webhook path that resolves org_id from the row).
  4. OAuth CSRF state: sign→verify round-trips; a tampered state is rejected —
     for Square AND Clover.
  5. Version/region: SquareClient honors environment (sandbox vs prod); Clover
     client uses its configured base URL. A known gap (the connect/test path
     hardcodes the Square PROD URL + a stale API version) is pinned as xfail so
     it can't be forgotten.

Pattern mirrors tests/api/test_notifications_exception_handling.py: call the
functions directly with a fake DB, run via asyncio.run (no pytest-asyncio).

Run:  python -m pytest tests/api/test_pos_connect_flow.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# A throwaway key so encrypt_token works offline in the connect storage test.
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.pop("TENANCY_ENFORCEMENT_DISABLED", None)  # ensure enforcement ON

import src.db as db_mod  # noqa: E402
from src.api import auth  # noqa: E402
from src.api.routes import oauth, clover_oauth  # noqa: E402
from src.api.routes.pos_connections import (  # noqa: E402
    connect_pos,
    disconnect_pos,
    teardown_connection,
    ConnectRequest,
    DisconnectRequest,
)
from fastapi import BackgroundTasks  # noqa: E402

ORG = "168b6df2-e9af-4b00-8fec-51e51149ff19"
USER = {"id": "user-1", "email": "rep@example.com"}
PROVIDERS = ["square", "clover"]


def _run(coro):
    return asyncio.run(coro)


class FakeDB:
    """Records every write; returns canned reads."""
    def __init__(self, existing_connection=None, existing_org=True):
        self.inserts, self.updates, self.batch = [], [], []
        self._existing_connection = existing_connection
        self._existing_org = existing_org

    async def select(self, table, filters=None, limit=None):
        if table == "organizations":
            return [{"id": ORG}] if self._existing_org else []
        if table == "pos_connections":
            return [self._existing_connection] if self._existing_connection else []
        return []

    async def insert(self, table, row, return_data=True):
        self.inserts.append((table, row))
        return [row] if isinstance(row, dict) else row

    async def update(self, table, vals, filters=None):
        self.updates.append((table, vals, filters))

    async def batch_upsert(self, table, rows, on_conflict=None):
        self.batch.append((table, rows, on_conflict))


def _set_member(monkeypatch, is_member: bool):
    async def _check(user, org_id):
        return is_member
    monkeypatch.setattr(auth, "_check_org_membership", _check)


# ── 1. Tenancy guard ────────────────────────────────────────────────────

@pytest.mark.parametrize("provider", PROVIDERS)
def test_connect_rejects_non_member(monkeypatch, provider):
    _set_member(monkeypatch, False)
    db_mod._db_instance = FakeDB()
    req = ConnectRequest(org_id=ORG, pos_system=provider, credentials={})
    with pytest.raises(HTTPException) as e:
        _run(connect_pos(req, BackgroundTasks(), user=USER))
    assert e.value.status_code == 403


@pytest.mark.parametrize("provider", PROVIDERS)
def test_disconnect_rejects_non_member(monkeypatch, provider):
    _set_member(monkeypatch, False)
    db_mod._db_instance = FakeDB()
    req = DisconnectRequest(org_id=ORG, pos_system=provider)
    with pytest.raises(HTTPException) as e:
        _run(disconnect_pos(req, user=USER))
    assert e.value.status_code == 403


# ── 2. Connect storage + gate propagation ───────────────────────────────

@pytest.mark.parametrize("provider", PROVIDERS)
def test_connect_stores_connection_and_opens_gate(monkeypatch, provider):
    _set_member(monkeypatch, True)
    db = FakeDB()
    db_mod._db_instance = db
    # clover carries a token (exercises the access_token_enc mirror); square
    # uses empty creds so the prod business-type HTTP block is skipped (offline).
    creds = {"access_token": "tok", "merchant_id": "M1"} if provider == "clover" else {}
    req = ConnectRequest(org_id=ORG, pos_system=provider, credentials=creds)
    out = _run(connect_pos(req, BackgroundTasks(), user=USER))
    assert out["success"] is True and out["syncing"] is True
    # pos_connections row written
    assert any(t == "pos_connections" for t, _ in db.inserts), db.inserts
    # gate opened on both organizations + businesses
    org_upd = [v for (t, v, f) in db.updates if t == "organizations"]
    biz_upd = [v for (t, v, f) in db.updates if t == "businesses"]
    assert any(v.get("pos_connection_status") == "connected" for v in org_upd), org_upd
    assert any(v.get("pos_connected") is True for v in biz_upd), biz_upd


# ── 3. Disconnect teardown closes BOTH gate fields + clears token ────────

def test_teardown_with_org_id():
    db = FakeDB()
    _run(teardown_connection(db, "CONN1", ORG))
    tables = [t for (t, _, _) in db.updates]
    assert tables == ["pos_connections", "businesses", "organizations"], tables
    pc = db.updates[0][1]
    assert pc["status"] == "disconnected"
    assert pc["access_token_enc"] is None and pc["credentials_encrypted"] is None
    assert pc["historical_import_complete"] is False
    assert db.updates[1][1] == {"pos_connected": False}
    assert db.updates[2][1]["pos_connection_status"] is None


def test_teardown_resolves_org_from_row():
    # webhook path passes only connection_id; org_id must be resolved from the row.
    db = FakeDB(existing_connection={"org_id": ORG})
    _run(teardown_connection(db, "CONN2"))
    assert [t for (t, _, _) in db.updates] == ["pos_connections", "businesses", "organizations"]
    assert db.updates[1][2] == {"id": f"eq.{ORG}"}


# ── 4. OAuth CSRF state round-trip + tamper (both providers) ─────────────

@pytest.mark.parametrize("mod", [oauth, clover_oauth], ids=["square", "clover"])
def test_state_roundtrips(mod):
    state = mod._sign_state(ORG, "/canada/merchant")
    result = mod._verify_state(state)
    assert result is not None
    assert result[0] == ORG


@pytest.mark.parametrize("mod", [oauth, clover_oauth], ids=["square", "clover"])
def test_tampered_state_rejected(mod):
    state = mod._sign_state(ORG, "")
    tampered = state[:-3] + ("000" if state[-3:] != "000" else "111")
    assert mod._verify_state(tampered) is None


# ── 5. Version / region handling ─────────────────────────────────────────

def test_square_client_honors_environment():
    from src.square.client import SquareClient
    assert SquareClient(access_token="x", environment="production").base_url == "https://connect.squareup.com"
    assert "sandbox" in SquareClient(access_token="x", environment="sandbox").base_url


def test_clover_client_uses_configured_base():
    from src.clover.client import CloverClient
    base = CloverClient(access_token="x", merchant_id="m").base_url
    assert "clover.com" in base


@pytest.mark.xfail(reason="KNOWN GAP: pos_connections test/connect hardcodes PROD "
                          "connect.squareup.com + Square-Version 2024-01-18, ignoring "
                          "environment — sandbox merchants can't test/connect. Fix: route "
                          "through SquareClient.", strict=False)
def test_connect_path_should_not_hardcode_prod_square_url():
    import inspect
    from src.api.routes import pos_connections
    src = inspect.getsource(pos_connections)
    assert "connect.squareup.com" not in src, "connect path still hardcodes the prod Square URL"
