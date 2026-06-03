"""
Pinning tests for the narrow exception handling in
src/api/routes/dashboard.py::get_notifications.

The handler converts SupabaseRESTError with status 401/403/404 into a
graceful HTTPException(404); anything else (PostgREST 400 malformed query,
5xx upstream outage, network/unknown) MUST re-raise so observability isn't
laundered into a calm 404.

This branch is not externally forcible against the deployed backend — every
caller-controlled input is validated upstream by FastAPI before reaching
db.select. These tests pin the behavior in CI so a future maintainer who
widens the catch (or replaces the typed except with a broad Exception)
breaks the build instead of silently swallowing real failures.

Run:
    cd <repo> && python -m pytest tests/api/test_notifications_exception_handling.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

# Ensure the src package is importable when running from the repo root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api.routes.dashboard import get_notifications  # noqa: E402
from src.db.supabase_rest import SupabaseRESTError  # noqa: E402


def _run(coro):
    """Run an async coroutine in a fresh event loop — keeps the test suite
    pytest-asyncio-free (which isn't in requirements)."""
    return asyncio.run(coro)


def _fake_db(side_effect):
    """Return an object whose .select() coroutine raises or returns as configured."""
    db = AsyncMock()
    db.select = AsyncMock(side_effect=side_effect)
    return db


VALID_ORG = "biz_9f349894e8aa498081fa7e2af8e42f80"


# ─── Happy path ──────────────────────────────────────────────────────────

def test_happy_path_returns_notifications():
    db = _fake_db(side_effect=None)
    db.select.return_value = [
        {
            "id": "00000000-0000-4000-8000-000000000000",
            "title": "ok",
            "body": "ok body",
            "priority": "low",
            "source_type": "test",
            "status": "new",
            "created_at": "2026-01-01T00:00:00Z",
            "acknowledged_at": None,
        }
    ]

    result = _run(get_notifications(org_id=VALID_ORG, limit=20, unread_only=False, db=db))

    assert result["total"] == 1
    assert result["notifications"][0]["title"] == "ok"


# ─── 401/403/404 → graceful HTTPException(404) ──────────────────────────

@pytest.mark.parametrize(
    "status_code,message",
    [
        (401, "JWT expired"),
        (403, 'permission denied for table "notifications"'),
        (404, 'relation "notifications" does not exist'),
    ],
)
def test_postgrest_not_found_or_denied_becomes_404(status_code, message):
    """The three statuses that mean 'this caller can't read this row set' are
    converted to a graceful HTTPException(404). The detail string MUST mention
    the underlying store status so ops can distinguish RLS-denied (401/403)
    from missing-table (404) from logs alone."""
    db = _fake_db(SupabaseRESTError(status_code, message, details="ctx"))

    with pytest.raises(HTTPException) as excinfo:
        _run(get_notifications(org_id=VALID_ORG, limit=20, unread_only=False, db=db))

    assert excinfo.value.status_code == 404, (
        f"status={status_code} should map to HTTP 404 with our graceful detail"
    )
    assert f"store returned {status_code}" in excinfo.value.detail


# ─── 400 / 5xx / unknown → re-raise as the original SupabaseRESTError ──
# This is the critical assertion: a non-not-found store error MUST NOT be
# laundered into a 404. FastAPI's default exception handler will turn the
# re-raised SupabaseRESTError into a 5xx, surfacing the real outage.

@pytest.mark.parametrize(
    "status_code,scenario",
    [
        (400, "malformed PostgREST query — undefined_column / invalid_param"),
        (409, "conflict — not a normal read state but valid 4xx that isn't not-found"),
        (500, "upstream DB internal error"),
        (502, "Supabase edge bad-gateway"),
        (503, "PostgREST upstream unavailable / replica down"),
        (504, "DB timeout"),
    ],
)
def test_non_not_found_status_reraises(status_code, scenario):
    """The whole point of the narrow-by-type design: only 401/403/404 are
    swallowed. Anything else re-raises so FastAPI converts it to a real 5xx
    and observability picks it up. A future maintainer widening the catch
    (e.g., adding `or exc.status_code >= 500` to the gate, or replacing the
    typed except with `except Exception`) breaks this test."""
    err = SupabaseRESTError(status_code, f"upstream {scenario}", details="ctx")
    db = _fake_db(err)

    with pytest.raises(SupabaseRESTError) as excinfo:
        _run(get_notifications(org_id=VALID_ORG, limit=20, unread_only=False, db=db))

    assert excinfo.value.status_code == status_code
    # Critically: this MUST be the original SupabaseRESTError, NOT an HTTPException.
    # If a future patch wraps it in HTTPException(404, ...), this assertion fails.
    assert not isinstance(excinfo.value, HTTPException), (
        "Non-not-found errors must propagate as SupabaseRESTError so FastAPI's "
        "default handler converts them to a real 5xx. Wrapping them in "
        "HTTPException(404) launders the failure and breaks observability."
    )


# ─── Non-SupabaseRESTError exceptions also propagate ────────────────────

def test_arbitrary_exception_propagates():
    """The except clause is typed (SupabaseRESTError), so completely
    unrelated exceptions like network/asyncio errors fall through entirely.
    This pins that no broad `except Exception` was added."""

    class FakeNetworkError(Exception):
        pass

    db = _fake_db(FakeNetworkError("connection reset"))

    with pytest.raises(FakeNetworkError):
        _run(get_notifications(org_id=VALID_ORG, limit=20, unread_only=False, db=db))
