"""RED-FIRST cross-branch isolation tests for the 7-level sales hierarchy.

Written BEFORE src/api/hierarchy.py and BEFORE the RLS migration exist, per the
red-test-first doctrine for this portal (RLS regression history: 20260511 wide-
open canada_leads, 20260522/20260603 wide-open us_leads + anon grant).

Two INDEPENDENT control planes are under test:

  Plane 1 — Postgres RLS: covered by tests/rls/hierarchy_policies.test.sql
            (SQL fixture file; requires a live postgres — see its header).
  Plane 2 — Backend API scoping (THIS FILE): src/api/hierarchy.py must filter
            rep-keyed rows to the caller's subtree even when the upstream
            Supabase fetch returns EVERYTHING (i.e. as if it had been made with
            the service-role key / RLS disabled). The backend must never
            delegate to RLS alone.

Every guard is asserted in BOTH directions (allowed ✓ / denied ✓) — a guard
proven in only one direction is decoration, not a control.

Org fixture (materialized path = dot-joined rep ids):

    admin (role=admin)                       path: A
    vp    (role=vp_sales)                    path: V
      dm1 (role=district_manager)            path: V.D1
        rep1 (role=sales_rep)                path: V.D1.R1
      dm2 (role=district_manager)            path: V.D2
        rep2 (role=sales_rep)                path: V.D2.R2

Run:  python -m pytest tests/rls/test_hierarchy_isolation.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api import hierarchy  # noqa: E402  (RED: module does not exist yet)

# ── Fixture tree ──────────────────────────────────────────────────────────────

ADMIN_ID = "aaaaaaaa-0000-4000-8000-000000000001"
VP_ID = "bbbbbbbb-0000-4000-8000-000000000002"
DM1_ID = "cccccccc-0000-4000-8000-000000000003"
REP1_ID = "dddddddd-0000-4000-8000-000000000004"
DM2_ID = "eeeeeeee-0000-4000-8000-000000000005"
REP2_ID = "ffffffff-0000-4000-8000-000000000006"

REPS = {
    "admin@meridian.test": {"id": ADMIN_ID, "email": "admin@meridian.test", "role": "admin", "path": ADMIN_ID, "manager_id": None},
    "vp@meridian.test": {"id": VP_ID, "email": "vp@meridian.test", "role": "vp_sales", "path": VP_ID, "manager_id": None},
    "dm1@meridian.test": {"id": DM1_ID, "email": "dm1@meridian.test", "role": "district_manager", "path": f"{VP_ID}.{DM1_ID}", "manager_id": VP_ID},
    "rep1@meridian.test": {"id": REP1_ID, "email": "rep1@meridian.test", "role": "sales_rep", "path": f"{VP_ID}.{DM1_ID}.{REP1_ID}", "manager_id": DM1_ID},
    "dm2@meridian.test": {"id": DM2_ID, "email": "dm2@meridian.test", "role": "district_manager", "path": f"{VP_ID}.{DM2_ID}", "manager_id": VP_ID},
    "rep2@meridian.test": {"id": REP2_ID, "email": "rep2@meridian.test", "role": "sales_rep", "path": f"{VP_ID}.{DM2_ID}.{REP2_ID}", "manager_id": DM2_ID},
}

LEADS = [
    {"id": "lead-1", "business_name": "Branch1 Pizza", "rep_id": REP1_ID},
    {"id": "lead-2", "business_name": "Branch2 Cafe", "rep_id": REP2_ID},
    {"id": "lead-3", "business_name": "Unassigned Deli", "rep_id": None},
]


def _run(coro):
    return asyncio.run(coro)


def _wire_fixture(monkeypatch):
    """Point hierarchy's DB seams at the in-memory org tree."""
    async def _by_email(email: str):
        return REPS.get((email or "").lower())

    async def _under(path: str):
        return [r for r in REPS.values() if r["path"] == path or r["path"].startswith(path + ".")]

    monkeypatch.setattr(hierarchy, "_fetch_rep_by_email", _by_email)
    monkeypatch.setattr(hierarchy, "_fetch_reps_under", _under)


async def _scope_for(email: str) -> "hierarchy.RepScope":
    return await hierarchy.resolve_scope({"email": email})


# ── Manager subtree: BOTH directions ─────────────────────────────────────────

def test_manager_sees_own_subtree_lead(monkeypatch):
    """dm1 CAN see rep1's lead (rep1 is in dm1's downline)."""
    _wire_fixture(monkeypatch)
    scope = _run(_scope_for("dm1@meridian.test"))
    allowed = _run(hierarchy.visible_rep_ids(scope))
    kept = hierarchy.scope_lead_rows(LEADS, allowed)
    assert any(ld["id"] == "lead-1" for ld in kept), "manager must see own-subtree lead"


def test_manager_cannot_see_sibling_branch_lead(monkeypatch):
    """dm1 CANNOT see rep2's lead (rep2 is in dm2's branch, a sibling)."""
    _wire_fixture(monkeypatch)
    scope = _run(_scope_for("dm1@meridian.test"))
    allowed = _run(hierarchy.visible_rep_ids(scope))
    kept = hierarchy.scope_lead_rows(LEADS, allowed)
    assert not any(ld["id"] == "lead-2" for ld in kept), "sibling-branch lead leaked to manager"


def test_manager_upline_cannot_be_widened_downward(monkeypatch):
    """dm1's visible rep ids never include the sibling manager or their rep."""
    _wire_fixture(monkeypatch)
    scope = _run(_scope_for("dm1@meridian.test"))
    allowed = _run(hierarchy.visible_rep_ids(scope))
    assert allowed is not None
    assert DM1_ID in allowed and REP1_ID in allowed
    assert DM2_ID not in allowed and REP2_ID not in allowed
    assert VP_ID not in allowed, "upline must not be in the *lead-visibility* set"


# ── Plain rep: self only, BOTH directions ────────────────────────────────────

def test_rep_sees_only_self(monkeypatch):
    _wire_fixture(monkeypatch)
    scope = _run(_scope_for("rep1@meridian.test"))
    allowed = _run(hierarchy.visible_rep_ids(scope))
    kept = hierarchy.scope_lead_rows(LEADS, allowed)
    assert any(ld["id"] == "lead-1" for ld in kept), "rep must keep own lead"
    assert not any(ld["id"] == "lead-2" for ld in kept), "rep must not see another rep's lead"


def test_unknown_user_sees_nothing_assigned(monkeypatch):
    """A JWT with no sales_reps row (and not allowlisted) gets an EMPTY scope — fail closed."""
    _wire_fixture(monkeypatch)
    scope = _run(_scope_for("stranger@evil.test"))
    allowed = _run(hierarchy.visible_rep_ids(scope))
    kept = hierarchy.scope_lead_rows(LEADS, allowed)
    assert all(ld["rep_id"] is None for ld in kept), "assigned leads leaked to a non-rep session"


# ── Admin: sees all ──────────────────────────────────────────────────────────

def test_admin_sees_all(monkeypatch):
    _wire_fixture(monkeypatch)
    scope = _run(_scope_for("admin@meridian.test"))
    allowed = _run(hierarchy.visible_rep_ids(scope))
    assert allowed is None, "admin scope is unrestricted (None sentinel)"
    kept = hierarchy.scope_lead_rows(LEADS, allowed)
    assert {ld["id"] for ld in kept} == {"lead-1", "lead-2", "lead-3"}


def test_allowlist_email_is_admin_without_rep_row(monkeypatch):
    """Belt-and-suspenders: ADMIN_EMAILS keeps admin access even with no rep row."""
    _wire_fixture(monkeypatch)
    scope = _run(_scope_for("aidanpierce72@gmail.com"))
    assert scope.is_admin


# ── Roster scoping (team page): subtree + upline names, nothing lateral ─────

def test_roster_includes_subtree_and_upline_but_not_siblings(monkeypatch):
    _wire_fixture(monkeypatch)
    scope = _run(_scope_for("dm1@meridian.test"))
    allowed = _run(hierarchy.visible_rep_ids(scope))
    roster = hierarchy.scope_roster_rows(list(REPS.values()), scope, allowed)
    ids = {r["id"] for r in roster}
    assert DM1_ID in ids and REP1_ID in ids, "own subtree missing from roster"
    assert VP_ID in ids, "upline chain (manager names) missing from roster"
    assert DM2_ID not in ids and REP2_ID not in ids, "sibling branch leaked into roster"


# ── Cross-branch WRITE (role management) blocked ─────────────────────────────

def test_assign_requires_admin_role_or_allowlist(monkeypatch):
    """A manager (non-admin) calling the assign guard gets 403; an admin passes."""
    _wire_fixture(monkeypatch)
    with pytest.raises(HTTPException) as e:
        _run(hierarchy.require_org_admin({"email": "dm1@meridian.test"}))
    assert e.value.status_code == 403
    admin = _run(hierarchy.require_org_admin({"email": "admin@meridian.test"}))
    assert admin["email"] == "admin@meridian.test"


def test_assign_manager_must_outrank_assignee():
    """office_manager cannot manage a vp_sales; vp_sales can manage a district_manager."""
    om = {"id": DM1_ID, "role": "office_manager", "path": f"{VP_ID}.{DM1_ID}"}
    with pytest.raises(HTTPException) as e:
        hierarchy.check_assignment("vp_sales", REP1_ID, om)
    assert e.value.status_code == 400
    vp = {"id": VP_ID, "role": "vp_sales", "path": VP_ID}
    hierarchy.check_assignment("district_manager", REP1_ID, vp)  # must not raise


def test_assign_cycle_guard():
    """Assigning a manager whose path already contains the assignee = cycle → 400."""
    dm1 = {"id": DM1_ID, "role": "district_manager", "path": f"{VP_ID}.{DM1_ID}"}
    with pytest.raises(HTTPException) as e:
        hierarchy.check_assignment("sales_rep", VP_ID, dm1)  # VP under their own descendant
    assert e.value.status_code == 400


# ── INDEPENDENCE: backend filters even when the fetch is a superset ──────────
# Simulates RLS being broken/bypassed (service-role fetch): the upstream call
# returns EVERY row; the API layer must still strip the sibling branch. This is
# what makes the two planes independent — different inputs, different failure
# modes, both tested in both directions.

class _FakeResp:
    def __init__(self, rows):
        self.status_code = 200
        self._rows = rows

    def json(self):
        return self._rows


class _FakeAsyncClient:
    """httpx.AsyncClient stand-in: returns ALL rows regardless of auth header."""

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, **kw):
        if "sales_reps" in url:
            return _FakeResp(list(REPS.values()))
        if "canada_leads" in url or "deals" in url or "us_leads" in url:
            return _FakeResp(list(LEADS))
        return _FakeResp([])


class _FakeRequest:
    headers = {"authorization": "Bearer user-token"}


def _wire_route_env(monkeypatch):
    _wire_fixture(monkeypatch)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)


def test_canada_team_endpoint_filters_service_role_superset(monkeypatch):
    """GET /api/canada/team must NOT return sibling-branch reps to a manager even
    when Supabase (RLS plane) hands back everything."""
    from src.api.routes import canada as canada_mod
    _wire_route_env(monkeypatch)
    out = _run(canada_mod.get_team(_FakeRequest(), {"email": "dm1@meridian.test"}))
    ids = {r["id"] for r in out["reps"]} | {r["id"] for r in out["applicants"]}
    assert REP1_ID in ids, "manager lost own subtree in team endpoint"
    assert REP2_ID not in ids and DM2_ID not in ids, (
        "BACKEND PLANE MISSING: /api/canada/team returned sibling-branch reps "
        "when the DB fetch was unfiltered — endpoint is delegating to RLS alone"
    )


def test_canada_team_endpoint_admin_still_sees_all(monkeypatch):
    from src.api.routes import canada as canada_mod
    _wire_route_env(monkeypatch)
    out = _run(canada_mod.get_team(_FakeRequest(), {"email": "admin@meridian.test"}))
    ids = {r["id"] for r in out["reps"]} | {r["id"] for r in out["applicants"]}
    assert {ADMIN_ID, VP_ID, DM1_ID, REP1_ID, DM2_ID, REP2_ID} <= ids


def test_us_leads_endpoint_filters_service_role_superset(monkeypatch):
    """GET /api/us/leads: us_leads RLS is backend-enforced — the API filter IS the
    primary guard there, so it must hold with an unfiltered fetch."""
    from src.api.routes import us as us_mod
    _wire_route_env(monkeypatch)
    out = _run(us_mod.get_leads(_FakeRequest(), {"email": "rep1@meridian.test"}))
    ids = {ld["id"] for ld in out["leads"]}
    assert "lead-2" not in ids, "us_leads leaked a sibling rep's lead through the backend plane"
    assert "lead-1" in ids, "rep lost their own lead in /api/us/leads"


# ── SECURITY: _fetch_rep_by_email must narrow ilike matches to an EXACT compare ──
# Reps self-signup with attacker-chosen emails; PostgREST ilike treats _ and %
# as wildcards. A plain ilike + rows[0] would let a_min@corp.com bind to
# admin@corp.com's row (privilege escalation via resolve_scope's is_admin).

def test_fetch_rep_by_email_ignores_wildcard_matches(monkeypatch):
    # _service_get simulates PostgREST ilike.'a_min@corp.com' matching BOTH the
    # attacker's own row and admin@corp.com ('_' matches 'd').
    async def _svc(params):
        return [
            {"id": "admin-1", "email": "admin@corp.com", "role": "admin", "path": "admin-1"},
            {"id": "att-1", "email": "a_min@corp.com", "role": "sales_rep", "path": "att-1"},
        ]
    monkeypatch.setattr(hierarchy, "_service_get", _svc)
    row = _run(hierarchy._fetch_rep_by_email("a_min@corp.com"))
    assert row is not None
    assert row["id"] == "att-1"           # the attacker's OWN row, never admin's
    assert row["role"] == "sales_rep"


def test_fetch_rep_by_email_none_when_no_exact(monkeypatch):
    async def _svc(params):
        return [{"id": "admin-1", "email": "admin@corp.com", "role": "admin", "path": "admin-1"}]
    monkeypatch.setattr(hierarchy, "_service_get", _svc)
    # ilike matched admin@ only (wildcard), but no exact match for the attacker.
    assert _run(hierarchy._fetch_rep_by_email("a_min@corp.com")) is None
