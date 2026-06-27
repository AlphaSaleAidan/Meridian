"""Cross-tenant BOLA regression tests for service-auth merchant-scoped endpoints.

Branch: fix/tenant-isolation-bola.

`require_service_auth` authenticates (admin-key / service-token / any valid
Supabase session) but does NOT, on its own, authorize against a specific org.
The fix adds `enforce_service_member(principal, org_id)` as the first line of
every merchant-self-scoped endpoint so a logged-in user can no longer read or
mutate ANOTHER tenant's data.

These tests prove, with `_check_org_membership` / `_verify_supabase_token`
monkeypatched (the same seam used by tests/api/test_pos_connect_flow.py):

  1. a member user passes,
  2. a non-member user is rejected with 403,
  3. an admin-key principal passes WITHOUT any membership,
  4. TENANCY_ENFORCEMENT_DISABLED=1 lets a non-member through (rollback works).

They exercise the guard both directly (`enforce_service_member`) and through
representative real endpoints — one path-param read (phone config), and one
sub-resource endpoint keyed by its own id (schedule shift update), which
resolves the owning merchant_id from the row before authorizing.

Pattern: call the route functions directly with a fake DB, run via asyncio.run
(no pytest-asyncio), mirroring the existing api test suite.

Run:  python -m pytest tests/api/test_tenant_isolation_bola.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

os.environ.pop("TENANCY_ENFORCEMENT_DISABLED", None)  # ensure enforcement ON

import src.db as db_mod  # noqa: E402
from src.api import auth  # noqa: E402
from src.api.routes import phone_dashboard as phone_mod  # noqa: E402
from src.api.routes import schedule as sched_mod  # noqa: E402

ORG = "168b6df2-e9af-4b00-8fec-51e51149ff19"
OTHER_ORG = "0d6a1b2c-3e4f-4a5b-8c7d-9e0f1a2b3c4d"
SHIFT_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"

MEMBER = {"id": "owner-1", "email": "owner@acme.test"}
OUTSIDER = {"id": "intruder-9", "email": "intruder@evil.test"}


def _run(coro):
    return asyncio.run(coro)


def _set_member(monkeypatch, is_member: bool):
    """Monkeypatch the single membership lookup every guard funnels through."""
    async def _check(user, org_id):
        return is_member
    monkeypatch.setattr(auth, "_check_org_membership", _check)


def _set_token_user(monkeypatch, user: dict | None):
    """Make `Bearer usertoken` resolve to a given Supabase session user."""
    async def _verify(_token):
        return user
    monkeypatch.setattr(auth, "_verify_supabase_token", _verify)


class FakeDB:
    """Returns a canned row for ORG; records writes."""

    def __init__(self, merchant_id: str = ORG):
        self._merchant_id = merchant_id
        self.updates: list = []
        self.deletes: list = []

    async def select(self, table, filters=None, limit=None, order=None, offset=None):
        if table == "phone_agent_config":
            return [{"merchant_id": self._merchant_id, "active": True,
                     "menu_items": [], "pos_access_token": "secret"}]
        if table == "schedule_shifts":
            return [{"id": SHIFT_ID, "merchant_id": self._merchant_id}]
        if table == "schedule_staff":
            return [{"id": SHIFT_ID, "merchant_id": self._merchant_id}]
        return []

    async def update(self, table, vals, filters=None):
        self.updates.append((table, vals, filters))

    async def delete(self, table, filters=None):
        self.deletes.append((table, filters))


async def _user_principal(monkeypatch, user: dict) -> dict:
    """Build a real {'kind':'user', ...} principal via require_service_auth."""
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret")
    monkeypatch.setenv("MERIDIAN_SERVICE_TOKEN", "svc")
    monkeypatch.setattr(auth, "ADMIN_EMAILS", [], raising=False)
    _set_token_user(monkeypatch, user)
    principal = await auth.require_service_auth(admin_key="", auth_header="Bearer usertoken")
    assert principal["kind"] == "user"
    return principal


async def _admin_principal(monkeypatch) -> dict:
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret")
    principal = await auth.require_service_auth(admin_key="topsecret", auth_header="")
    assert principal["kind"] == "admin"
    return principal


# ── enforce_service_member: the shared guard, all four scenarios ───────────

def test_enforce_member_user_passes(monkeypatch):
    _set_member(monkeypatch, True)
    principal = {"kind": "user", "user": MEMBER}
    # Should not raise.
    _run(auth.enforce_service_member(principal, ORG))


def test_enforce_non_member_user_403(monkeypatch):
    _set_member(monkeypatch, False)
    principal = {"kind": "user", "user": OUTSIDER}
    with pytest.raises(HTTPException) as e:
        _run(auth.enforce_service_member(principal, ORG))
    assert e.value.status_code == 403


def test_enforce_admin_principal_passes_without_membership(monkeypatch):
    # Membership lookup would say NO, but admin/service principals skip it.
    _set_member(monkeypatch, False)
    _run(auth.enforce_service_member({"kind": "admin"}, ORG))
    _run(auth.enforce_service_member({"kind": "service"}, ORG))


def test_enforce_killswitch_lets_non_member_through(monkeypatch):
    _set_member(monkeypatch, False)
    monkeypatch.setenv("TENANCY_ENFORCEMENT_DISABLED", "1")
    principal = {"kind": "user", "user": OUTSIDER}
    # Rollback knob: non-member is allowed through (logged, not blocked).
    _run(auth.enforce_service_member(principal, ORG))


# ── Representative endpoint: phone config GET (path-param merchant_id) ─────

def test_phone_config_member_passes(monkeypatch):
    _set_member(monkeypatch, True)
    db_mod._db_instance = FakeDB()
    principal = _run(_user_principal(monkeypatch, MEMBER))
    out = _run(phone_mod.get_phone_config(ORG, principal=principal))
    assert out["exists"] is True
    # secret never leaks back to the client
    assert "pos_access_token" not in out


def test_phone_config_non_member_403(monkeypatch):
    _set_member(monkeypatch, False)
    db_mod._db_instance = FakeDB()
    principal = _run(_user_principal(monkeypatch, OUTSIDER))
    with pytest.raises(HTTPException) as e:
        _run(phone_mod.get_phone_config(ORG, principal=principal))
    assert e.value.status_code == 403


def test_phone_config_admin_passes_without_membership(monkeypatch):
    _set_member(monkeypatch, False)  # would deny a plain user
    db_mod._db_instance = FakeDB()
    principal = _run(_admin_principal(monkeypatch))
    out = _run(phone_mod.get_phone_config(ORG, principal=principal))
    assert out["exists"] is True


def test_phone_config_killswitch_lets_non_member_through(monkeypatch):
    _set_member(monkeypatch, False)
    monkeypatch.setenv("TENANCY_ENFORCEMENT_DISABLED", "1")
    db_mod._db_instance = FakeDB()
    principal = _run(_user_principal(monkeypatch, OUTSIDER))
    out = _run(phone_mod.get_phone_config(ORG, principal=principal))
    assert out["exists"] is True


# ── Sub-resource endpoint: schedule shift update (keyed by shift_id) ───────
# Proves _enforce_row_member resolves the owning merchant_id from the row
# before authorizing — the BOLA hole on id-keyed mutations.

def test_update_shift_non_member_403(monkeypatch):
    _set_member(monkeypatch, False)
    db = FakeDB()
    db_mod._db_instance = db
    principal = _run(_user_principal(monkeypatch, OUTSIDER))
    body = sched_mod.ShiftUpdate(notes="hijack")
    with pytest.raises(HTTPException) as e:
        _run(sched_mod.update_shift(SHIFT_ID, body, principal=principal))
    assert e.value.status_code == 403
    # The mutation must NOT have run.
    assert db.updates == []


def test_update_shift_member_passes(monkeypatch):
    _set_member(monkeypatch, True)
    db = FakeDB()
    db_mod._db_instance = db
    principal = _run(_user_principal(monkeypatch, MEMBER))
    body = sched_mod.ShiftUpdate(notes="cover")
    out = _run(sched_mod.update_shift(SHIFT_ID, body, principal=principal))
    assert out["shift_id"] == SHIFT_ID
    assert any(t == "schedule_shifts" for (t, _v, _f) in db.updates), db.updates


def test_update_shift_admin_passes_without_membership(monkeypatch):
    _set_member(monkeypatch, False)
    db = FakeDB()
    db_mod._db_instance = db
    principal = _run(_admin_principal(monkeypatch))
    body = sched_mod.ShiftUpdate(notes="support edit")
    out = _run(sched_mod.update_shift(SHIFT_ID, body, principal=principal))
    assert out["shift_id"] == SHIFT_ID
