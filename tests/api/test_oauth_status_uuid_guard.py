"""
Regression: GET /api/square/status and /api/clover/status must NOT 500 when
org_id is not a UUID.

org_id maps to a Postgres `uuid` column. A non-uuid value (demo/edge callers,
e.g. org_id="" or "demo") previously reached the DB lookup and raised an
invalid-uuid cast error, surfacing as a 500. The status handlers now validate
the org_id shape first and return a 200 {"connected": false, ...} instead.

Pattern mirrors tests/api/test_pos_connect_flow.py: call the route functions
directly and drive them with asyncio.run (no pytest-asyncio).

Run:  python -m pytest tests/api/test_oauth_status_uuid_guard.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import src.db as db_mod  # noqa: E402
from src.api.routes import oauth, clover_oauth  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


VALID_UUID = "168b6df2-e9af-4b00-8fec-51e51149ff19"
# Real merchant/org id shape: businesses.id is TEXT `biz_<32 hex>`.
VALID_BIZ_ID = "biz_9e066503fe6b43c1b8a50cc0c3989e6c"
VALID_BIZ_ID_SHORT = "biz_1cee43eb2ce5431a"  # frontend 16-hex variant
NON_UUID_VALUES = ["", "demo", "not-a-uuid", "12345", "168b6df2-e9af"]
# Must STILL be rejected even after we relax to accept biz_ ids — no injection.
BAD_BIZ_SHAPED = ["biz_", "biz_../etc/passwd", "biz_' OR '1'='1", "biz_zzzz", "../etc"]


@pytest.fixture(autouse=True)
def _no_db(monkeypatch):
    # Force the DB to look unavailable so the ONLY thing that can make a non-uuid
    # org_id pass the guard would be a real bug — and so a valid uuid takes the
    # safe db_unavailable branch rather than hitting a live connection.
    monkeypatch.setattr(db_mod, "_db_instance", None, raising=False)


@pytest.mark.parametrize("org_id", NON_UUID_VALUES)
def test_square_status_non_uuid_does_not_500(org_id):
    result = _run(oauth.connection_status(org_id))
    assert result["connected"] is False
    assert result.get("reason") == "invalid_org_id"


@pytest.mark.parametrize("org_id", NON_UUID_VALUES)
def test_clover_status_non_uuid_does_not_500(org_id):
    result = _run(clover_oauth.connection_status(org_id))
    assert result["connected"] is False
    assert result.get("reason") == "invalid_org_id"
    # Clover status always surfaces capability flags, even on the guarded path.
    assert "oauth_available" in result
    assert "clover_available" in result


def test_square_status_valid_uuid_is_not_rejected_by_guard():
    # A well-formed uuid must pass the uuid guard and fall through to the
    # (here unavailable) DB branch — proving the guard only rejects bad shapes.
    result = _run(oauth.connection_status(VALID_UUID))
    assert result["connected"] is False
    assert result.get("reason") == "db_unavailable"


def test_clover_status_valid_uuid_is_not_rejected_by_guard():
    result = _run(clover_oauth.connection_status(VALID_UUID))
    assert result["connected"] is False
    assert result.get("reason") == "db_unavailable"


# --- BUG-3: real merchant ids are `biz_<hex>`, not UUIDs ---------------------
# The status guards previously rejected the real businesses.id shape with
# reason="invalid_org_id", which blocked the Clover connected-check (and the
# Square one) for every real merchant. They must now fall through to the DB
# branch (here db_unavailable) instead of being rejected by the shape guard.

@pytest.mark.parametrize("org_id", [VALID_BIZ_ID, VALID_BIZ_ID_SHORT])
def test_clover_status_accepts_biz_id(org_id):
    result = _run(clover_oauth.connection_status(org_id))
    assert result["connected"] is False
    assert result.get("reason") == "db_unavailable"
    assert result.get("reason") != "invalid_org_id"


@pytest.mark.parametrize("org_id", [VALID_BIZ_ID, VALID_BIZ_ID_SHORT])
def test_square_status_accepts_biz_id(org_id):
    result = _run(oauth.connection_status(org_id))
    assert result["connected"] is False
    assert result.get("reason") == "db_unavailable"
    assert result.get("reason") != "invalid_org_id"


@pytest.mark.parametrize("org_id", BAD_BIZ_SHAPED)
def test_clover_status_still_rejects_bad_shapes(org_id):
    result = _run(clover_oauth.connection_status(org_id))
    assert result["connected"] is False
    assert result.get("reason") == "invalid_org_id"


@pytest.mark.parametrize("org_id", BAD_BIZ_SHAPED)
def test_square_status_still_rejects_bad_shapes(org_id):
    result = _run(oauth.connection_status(org_id))
    assert result["connected"] is False
    assert result.get("reason") == "invalid_org_id"


# --- biz_ org ids must not 500 the read-only status endpoints ----------------
# pos_connections.org_id is a UUID column in prod; biz_ ids are the TEXT
# businesses.id with no businesses→organizations mapping. Querying the uuid
# column with a biz_ id raised 22P02 → 500 → SettingsPage ErrorState + the
# onboarding wizard hid the Clover 1-click (oauth_available defaulted false).
# The handlers now short-circuit non-uuid org ids to the graceful empty shape
# (with REAL capability flags) and soft-fail 22P02 as a backstop.

from types import SimpleNamespace  # noqa: E402

from src.api.routes import dashboard  # noqa: E402
from src.db.supabase_rest import SupabaseRESTError  # noqa: E402

UUID_CAST_ERROR = SupabaseRESTError(
    400,
    'invalid input syntax for type uuid: "biz_43e5ff96db22436096c83c9280a4009f"',
    "22P02",
)


class _StubDB:
    """Minimal pos_connections store stub for the status routes."""

    def __init__(self, rows=None, error: Exception | None = None):
        self.rows = rows or []
        self.error = error
        self.calls: list = []

    async def select(self, table, **kwargs):
        self.calls.append((table, kwargs))
        if self.error:
            raise self.error
        return self.rows

    async def get_pos_connection(self, org_id):
        self.calls.append(("pos_connections", {"org_id": org_id}))
        if self.error:
            raise self.error
        return self.rows[0] if self.rows else None


@pytest.fixture
def _clover_flags(monkeypatch):
    # Real capability flags as computed from env on the happy path.
    monkeypatch.setattr(
        clover_oauth, "clover_config",
        SimpleNamespace(has_oauth_credentials=True, is_enabled=True),
    )


CONNECTED_ROW = {
    "id": "conn-1",
    "provider": "clover",
    "status": "connected",
    "external_merchant_id": "MID123",
    "last_sync_at": "2026-07-16T00:00:00Z",
    "historical_import_complete": True,
}


# dashboard /api/dashboard/connection ----------------------------------------

def test_dashboard_connection_uuid_org_unchanged(monkeypatch):
    stub = _StubDB(rows=[CONNECTED_ROW])
    result = _run(dashboard.get_connection(org_id=VALID_UUID, db=stub))
    assert len(result["connections"]) == 1
    assert result["connections"][0]["merchant_id"] == "MID123"
    assert stub.calls, "uuid org must still hit the store"


@pytest.mark.parametrize("org_id", [VALID_BIZ_ID, VALID_BIZ_ID_SHORT])
def test_dashboard_connection_biz_org_returns_empty_without_query(org_id):
    stub = _StubDB(rows=[CONNECTED_ROW])
    result = _run(dashboard.get_connection(org_id=org_id, db=stub))
    assert result == {"connections": []}
    assert stub.calls == [], "biz_ ids must never reach the uuid column"


def test_dashboard_connection_uuid_cast_error_soft_fails():
    # Backstop: even if a non-uuid shape reaches the store, 22P02 → empty, not 500.
    stub = _StubDB(error=UUID_CAST_ERROR)
    result = _run(dashboard.get_connection(org_id=VALID_UUID, db=stub))
    assert result == {"connections": []}


def test_dashboard_connection_other_store_errors_still_raise():
    stub = _StubDB(error=SupabaseRESTError(500, "connection pool exhausted"))
    with pytest.raises(SupabaseRESTError):
        _run(dashboard.get_connection(org_id=VALID_UUID, db=stub))


def test_dashboard_validate_org_id_rejects_garbage():
    from fastapi import HTTPException as HTTPExc
    with pytest.raises(HTTPExc) as exc:
        dashboard._validate_org_id("not-a-uuid-or-biz-id")
    assert exc.value.status_code == 422


# clover /api/clover/status ---------------------------------------------------

@pytest.mark.parametrize("org_id", [VALID_BIZ_ID, VALID_BIZ_ID_SHORT])
def test_clover_status_biz_org_queries_mapped_uuid(monkeypatch, _clover_flags, org_id):
    # biz_ ids now resolve through their deterministic companion UUID
    # (db.org_ids.connection_org_id) — the SAME id the OAuth callback stores
    # under — so a connected biz_ merchant sees their real state. The raw biz_
    # string itself must still never reach the uuid column.
    from src.db.org_ids import connection_org_id
    stub = _StubDB(rows=[CONNECTED_ROW])
    monkeypatch.setattr(db_mod, "_db_instance", stub, raising=False)
    result = _run(clover_oauth.connection_status(org_id))
    assert result["connected"] is True
    assert result["oauth_available"] is True
    assert result["clover_available"] is True
    assert stub.calls, "mapped uuid must be queried"
    queried = str(stub.calls)
    assert org_id not in queried
    assert connection_org_id(org_id) in queried


def test_clover_status_uuid_org_unchanged(monkeypatch, _clover_flags):
    stub = _StubDB(rows=[CONNECTED_ROW])
    monkeypatch.setattr(db_mod, "_db_instance", stub, raising=False)
    result = _run(clover_oauth.connection_status(VALID_UUID))
    assert result["connected"] is True
    assert result["merchant_id"] == "MID123"
    assert result["oauth_available"] is True


def test_clover_status_uuid_cast_error_soft_fails(monkeypatch, _clover_flags):
    stub = _StubDB(error=UUID_CAST_ERROR)
    monkeypatch.setattr(db_mod, "_db_instance", stub, raising=False)
    result = _run(clover_oauth.connection_status(VALID_UUID))
    assert result["connected"] is False
    assert result["oauth_available"] is True


def test_clover_status_other_store_errors_still_raise(monkeypatch, _clover_flags):
    stub = _StubDB(error=SupabaseRESTError(500, "connection pool exhausted"))
    monkeypatch.setattr(db_mod, "_db_instance", stub, raising=False)
    with pytest.raises(SupabaseRESTError):
        _run(clover_oauth.connection_status(VALID_UUID))


# square /api/square/status ---------------------------------------------------

@pytest.mark.parametrize("org_id", [VALID_BIZ_ID, VALID_BIZ_ID_SHORT])
def test_square_status_biz_org_queries_mapped_uuid(monkeypatch, org_id):
    # biz_ ids resolve through their deterministic companion UUID (db.org_ids)
    # — the id the OAuth callback stores under — so a connected biz_ merchant
    # sees their real state. The raw biz_ string never reaches the uuid column.
    from src.db.org_ids import connection_org_id
    stub = _StubDB(rows=[CONNECTED_ROW])
    monkeypatch.setattr(db_mod, "_db_instance", stub, raising=False)
    result = _run(oauth.connection_status(org_id))
    assert result["connected"] is True
    assert stub.calls, "mapped uuid must be queried"
    queried = str(stub.calls)
    assert org_id not in queried
    assert connection_org_id(org_id) in queried


def test_square_status_uuid_org_unchanged(monkeypatch):
    stub = _StubDB(rows=[CONNECTED_ROW])
    monkeypatch.setattr(db_mod, "_db_instance", stub, raising=False)
    result = _run(oauth.connection_status(VALID_UUID))
    assert result["connected"] is True
    assert result["merchant_id"] == "MID123"


def test_square_status_uuid_cast_error_soft_fails(monkeypatch):
    stub = _StubDB(error=UUID_CAST_ERROR)
    monkeypatch.setattr(db_mod, "_db_instance", stub, raising=False)
    result = _run(oauth.connection_status(VALID_UUID))
    assert result["connected"] is False


def test_square_status_other_store_errors_still_raise(monkeypatch):
    stub = _StubDB(error=SupabaseRESTError(500, "connection pool exhausted"))
    monkeypatch.setattr(db_mod, "_db_instance", stub, raising=False)
    with pytest.raises(SupabaseRESTError):
        _run(oauth.connection_status(VALID_UUID))


# --- BUG-3: phone_dashboard._validate_merchant_id ---------------------------
from fastapi import HTTPException  # noqa: E402
from src.api.routes import phone_dashboard  # noqa: E402


@pytest.mark.parametrize("mid", [VALID_UUID, VALID_BIZ_ID, VALID_BIZ_ID_SHORT])
def test_phone_validate_merchant_id_accepts_real_ids(mid):
    # Must not raise for a real UUID or biz_ merchant id.
    phone_dashboard._validate_merchant_id(mid)


@pytest.mark.parametrize(
    "mid",
    ["", "../etc/passwd", "biz_", "biz_' OR '1'='1", "'; DROP TABLE businesses;--",
     "demo", "biz_zzzz", "not-an-id"],
)
def test_phone_validate_merchant_id_rejects_garbage(mid):
    with pytest.raises(HTTPException) as exc:
        phone_dashboard._validate_merchant_id(mid)
    assert exc.value.status_code == 400
