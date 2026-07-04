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
