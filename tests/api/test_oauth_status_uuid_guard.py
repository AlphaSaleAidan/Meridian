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
NON_UUID_VALUES = ["", "demo", "not-a-uuid", "12345", "168b6df2-e9af"]


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
