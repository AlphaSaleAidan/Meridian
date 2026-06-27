"""Lock regression tests for service/global endpoints with no rep/merchant caller.

Branch: fix/lock-flagged-service-endpoints.

Follow-up to the cross-tenant BOLA fix (#185). That change left several
`require_service_auth` endpoints flagged AMBIGUOUS because their callers might be
reps (ordinary user JWTs) or service/cron. Investigation (grep over frontend/src)
found these four have NO rep/merchant frontend caller — they are service/cron/admin
only — so they were switched to `require_admin_auth`:

  * POST /api/billing/cancel
  * POST /api/portal/generate
  * POST /api/onboarding/create-account
  * the /api/inference router (global ops: ingest/rebuild/generate/search/stats/...)

`require_admin_auth` accepts ONLY the admin key, MERIDIAN_SERVICE_TOKEN, or a user
in ADMIN_EMAILS — so cron/service-token automation keeps working while an ordinary
logged-in rep is rejected.

These tests prove, with `_verify_supabase_token` monkeypatched (the same seam the
rest of the api suite uses):

  1. anon (no creds)                 → 403
  2. admin key                       → passes
  3. MERIDIAN_SERVICE_TOKEN          → passes
  4. ordinary (non-admin) user JWT   → 403   (the rep we must not lock out elsewhere)
  5. ADMIN_EMAILS user JWT           → passes

and that each of the four locked routes is in fact wired to `require_admin_auth`
(and no longer to `require_service_auth`).

Pattern mirrors tests/api/test_tenant_isolation_bola.py: call the dependency
directly via asyncio.run, no pytest-asyncio.

Run:  python -m pytest tests/api/test_admin_lock_service_endpoints.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api import auth  # noqa: E402
from src.api.routes import billing as billing_mod  # noqa: E402
from src.api.routes import portal as portal_mod  # noqa: E402
from src.api.routes import onboarding as onboarding_mod  # noqa: E402
from src.api.routes import inference as inference_mod  # noqa: E402

ADMIN_USER = {"id": "admin-1", "email": "aidanpierce72@gmail.com"}
REP_USER = {"id": "rep-7", "email": "rep@merchant.test"}


def _run(coro):
    return asyncio.run(coro)


def _set_token_user(monkeypatch, user):
    async def _verify(_token):
        return user
    monkeypatch.setattr(auth, "_verify_supabase_token", _verify)


# ── require_admin_auth: the guard now protecting all four endpoints ─────────

def test_admin_auth_anon_403(monkeypatch):
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret")
    monkeypatch.setenv("MERIDIAN_SERVICE_TOKEN", "svc")
    with pytest.raises(HTTPException) as e:
        _run(auth.require_admin_auth(admin_key="", auth_header=""))
    assert e.value.status_code == 403


def test_admin_auth_admin_key_passes(monkeypatch):
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret")
    principal = _run(auth.require_admin_auth(admin_key="topsecret", auth_header=""))
    assert principal["kind"] == "admin"


def test_admin_auth_service_token_passes(monkeypatch):
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret")
    monkeypatch.setenv("MERIDIAN_SERVICE_TOKEN", "svc")
    principal = _run(auth.require_admin_auth(admin_key="", auth_header="Bearer svc"))
    assert principal["kind"] == "service"


def test_admin_auth_ordinary_rep_user_403(monkeypatch):
    """A logged-in rep (valid JWT, not in ADMIN_EMAILS) must be rejected."""
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret")
    monkeypatch.setenv("MERIDIAN_SERVICE_TOKEN", "svc")
    monkeypatch.setattr(auth, "ADMIN_EMAILS", ["aidanpierce72@gmail.com"], raising=False)
    _set_token_user(monkeypatch, REP_USER)
    with pytest.raises(HTTPException) as e:
        _run(auth.require_admin_auth(admin_key="", auth_header="Bearer usertoken"))
    assert e.value.status_code == 403


def test_admin_auth_admin_email_user_passes(monkeypatch):
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret")
    monkeypatch.setattr(auth, "ADMIN_EMAILS", ["aidanpierce72@gmail.com"], raising=False)
    _set_token_user(monkeypatch, ADMIN_USER)
    principal = _run(auth.require_admin_auth(admin_key="", auth_header="Bearer usertoken"))
    assert principal["kind"] == "user"


# ── Wiring: each locked route uses require_admin_auth, not require_service_auth ─

def _route_dep_calls(router, path: str, methods={"POST"}):
    """Collect every dependency callable resolved for the matching route,
    including router-level dependencies (FastAPI merges them into route.dependant)."""
    for route in router.routes:
        if getattr(route, "path", None) == path and methods & set(getattr(route, "methods", set()) or set()):
            calls = []

            def _walk(dependant):
                for sub in dependant.dependencies:
                    if sub.call is not None:
                        calls.append(sub.call)
                    _walk(sub)

            _walk(route.dependant)
            return calls
    raise AssertionError(f"route {path} {methods} not found in router")


def test_billing_cancel_wired_to_admin_auth():
    calls = _route_dep_calls(billing_mod.router, "/api/billing/cancel")
    assert auth.require_admin_auth in calls
    assert auth.require_service_auth not in calls


def test_portal_generate_wired_to_admin_auth():
    calls = _route_dep_calls(portal_mod.router, "/api/portal/generate")
    assert auth.require_admin_auth in calls
    assert auth.require_service_auth not in calls


def test_onboarding_create_account_wired_to_admin_auth():
    calls = _route_dep_calls(onboarding_mod.router, "/api/onboarding/create-account")
    assert auth.require_admin_auth in calls
    assert auth.require_service_auth not in calls


def test_inference_router_wired_to_admin_auth():
    # Router-level guard — sample a representative global-ops endpoint.
    for path in ("/api/inference/ingest", "/api/inference/generate", "/api/inference/search"):
        calls = _route_dep_calls(inference_mod.router, path)
        assert auth.require_admin_auth in calls, path
        assert auth.require_service_auth not in calls, path


# ── Guardrail: endpoints WITH a rep/merchant caller must stay require_service_auth ─
# These are exercised by reps via the portal with a user JWT (getAuthHeaders); locking
# them to admin would 403 live reps. Confirm we did NOT touch them.

def test_rep_facing_endpoints_left_as_service_auth():
    cases = [
        (billing_mod.router, "/api/billing/create-invoice"),
        (billing_mod.router, "/api/billing/update-payment-method"),
        (billing_mod.router, "/api/billing/notify-payment-failed"),
        (onboarding_mod.router, "/api/onboarding/provision-customer"),
    ]
    for router, path in cases:
        calls = _route_dep_calls(router, path)
        assert auth.require_service_auth in calls, path
        assert auth.require_admin_auth not in calls, path
