"""Regression tests for BUG-1: POST /api/onboarding/mark-onboarded.

The "Skip — I'll connect later" onboarding step 403'd because the route required
service auth (admin/service token) while the customer frontend calls it with the
customer's own session JWT. The step only persisted in localStorage, so on every
reload the customer was bounced back to /canada/setup.

Fix: authorize the owner via require_jwt + require_org_member(user, org_id). A
customer can mark THEIR OWN org onboarded (200); they cannot mark another org
(require_org_member raises 403). Admins in ADMIN_EMAILS retain access via
_check_org_membership.

These tests prove, with `_check_org_membership` monkeypatched (the same seam used
by tests/api/test_tenant_isolation_bola.py):

  1. the route is wired to require_jwt and NO LONGER to require_service_auth
  2. owner / org member         → require_org_member passes (endpoint proceeds)
  3. non-member (other org)     → require_org_member raises 403

Run:  python -m pytest tests/api/test_mark_onboarded_owner_auth.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api import auth  # noqa: E402
from src.api.routes import onboarding as onboarding_mod  # noqa: E402

OWNER = {"id": "owner-1", "email": "owner@merchant.test"}
OTHER = {"id": "intruder-9", "email": "intruder@evil.test"}


def _run(coro):
    return asyncio.run(coro)


def _set_member(monkeypatch, is_member: bool):
    async def _check(_user, _org_id):
        return is_member
    monkeypatch.setattr(auth, "_check_org_membership", _check)


# ── Wiring: route uses require_jwt, not require_service_auth ─────────────────

def _route_dep_calls(router, path: str, methods={"POST"}):
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


def test_mark_onboarded_wired_to_require_jwt():
    calls = _route_dep_calls(onboarding_mod.router, "/api/onboarding/mark-onboarded")
    assert auth.require_jwt in calls
    assert auth.require_service_auth not in calls


# ── Ownership: owner passes, non-member is rejected 403 ─────────────────────

def test_owner_can_mark_own_org(monkeypatch):
    """The org owner/member sails through the membership guard (no exception)."""
    _set_member(monkeypatch, True)
    # returns None on success — the point is that it does NOT raise.
    result = _run(auth.require_org_member(OWNER, "org-abc"))
    assert result is None


def test_non_member_cannot_mark_other_org(monkeypatch):
    """A JWT holder who is not a member of the target org gets 403 (no cross-tenant)."""
    monkeypatch.delenv("TENANCY_ENFORCEMENT_DISABLED", raising=False)
    _set_member(monkeypatch, False)
    with pytest.raises(HTTPException) as e:
        _run(auth.require_org_member(OTHER, "org-abc"))
    assert e.value.status_code == 403
