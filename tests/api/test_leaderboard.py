"""GET /api/leaderboard — peer-visible aggregate board.

The SR-portal audit gap: #334's hierarchy scoping correctly scoped ROSTER data
to self+downline+upline, but the Leaderboard tab rendered from that same
scoped roster, so a leaf rep saw a board of one. The fix is a separate
endpoint that returns ALL active reps in the caller's portal_context with
ONLY leaderboard-safe aggregate fields.

What is asserted here (both directions, per the portal doctrine):

  1. A LEAF rep gets the FULL active board for their portal (peers included) —
     the board must NOT collapse to self.
  2. The serialized payload contains NO email / phone / lead-row / commission
     keys — the response shape IS the security boundary.
  3. portal_context filtering: a US caller never sees Canada-only reps and
     vice versa; inactive reps never appear.
  4. Unauthenticated → 401. Session with no rep profile → 403 (fail closed).

Run: python -m pytest tests/api/test_leaderboard.py -v
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api import hierarchy  # noqa: E402
from src.api.routes import leaderboard as lb  # noqa: E402

# ── Fixture: two portals, one shared 'all' admin, one inactive applicant ──────

DM1_ID = "cccccccc-0000-4000-8000-000000000003"
REP1_ID = "dddddddd-0000-4000-8000-000000000004"
REP2_ID = "ffffffff-0000-4000-8000-000000000006"
PENDING_ID = "99999999-0000-4000-8000-000000000009"
USREP_ID = "12121212-0000-4000-8000-000000000012"
ADMIN_ID = "aaaaaaaa-0000-4000-8000-000000000001"

SALES_REPS = [
    {"id": DM1_ID, "name": "DM One", "email": "dm1@meridian.test", "phone": "+1555000001",
     "role": "district_manager", "portal_context": "canada", "is_active": True},
    {"id": REP1_ID, "name": "Rep One", "email": "rep1@meridian.test", "phone": "+1555000002",
     "role": "sales_rep", "portal_context": "canada", "is_active": True},
    {"id": REP2_ID, "name": "Rep Two", "email": "rep2@meridian.test", "phone": "+1555000003",
     "role": "sales_rep", "portal_context": "canada", "is_active": True},
    {"id": PENDING_ID, "name": "Pending Applicant", "email": "pending@meridian.test", "phone": "",
     "role": "sales_rep", "portal_context": "canada", "is_active": False},
    {"id": USREP_ID, "name": "US Rep", "email": "usrep@meridian.test", "phone": "+1555000004",
     "role": "sales_rep", "portal_context": "us", "is_active": True},
    {"id": ADMIN_ID, "name": "Admin", "email": "admin@meridian.test", "phone": "",
     "role": "admin", "portal_context": "all", "is_active": True},
]

CANADA_LEADS = [
    {"rep_id": REP1_ID, "stage": "closed_won", "monthly_value": 500},
    {"rep_id": REP1_ID, "stage": "prospecting", "monthly_value": 300},
    {"rep_id": REP2_ID, "stage": "closed_lost", "monthly_value": 800},
    {"rep_id": DM1_ID, "stage": "pos_connected", "monthly_value": 200},
]

US_LEADS = [
    {"rep_id": USREP_ID, "stage": "closed_won", "monthly_value": 700},
    {"rep_id": USREP_ID, "stage": "negotiation", "monthly_value": 100},
]


class _FakeResp:
    def __init__(self, rows, status=200):
        self.status_code = status
        self._rows = rows
        self.text = json.dumps(rows)

    def json(self):
        return self._rows


class _FakeAsyncClient:
    """httpx.AsyncClient stand-in emulating just enough PostgREST filtering."""

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, headers=None, params=None, **kw):
        params = params or {}
        if "sales_reps" in url:
            rows = list(SALES_REPS)
            if params.get("is_active") == "eq.true":
                rows = [r for r in rows if r["is_active"]]
            portal = params.get("portal_context", "")
            m = re.match(r"in\.\((.+)\)", portal)
            if m:
                allowed = {p.strip() for p in m.group(1).split(",")}
                rows = [r for r in rows if r["portal_context"] in allowed]
            return _FakeResp(rows)
        if "canada_leads" in url:
            return _FakeResp(list(CANADA_LEADS))
        if "us_leads" in url:
            return _FakeResp(list(US_LEADS))
        return _FakeResp([])


def _run(coro):
    return asyncio.run(coro)


def _wire(monkeypatch):
    async def _by_email(email: str):
        for r in SALES_REPS:
            if r["email"] == (email or "").lower():
                return dict(r)
        return None

    monkeypatch.setattr(hierarchy, "_fetch_rep_by_email", _by_email)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)


# ── 1. Leaf rep sees the WHOLE portal board (the board-of-one regression) ─────

def test_leaf_rep_gets_all_active_portal_reps(monkeypatch):
    _wire(monkeypatch)
    out = _run(lb.get_leaderboard({"email": "rep1@meridian.test"}))
    ids = {r["id"] for r in out["leaderboard"]}
    # Peers + managers + the 'all'-portal admin are ON the board…
    assert {REP1_ID, REP2_ID, DM1_ID, ADMIN_ID} <= ids, (
        "BOARD OF ONE: leaf rep's leaderboard is missing peers — the board "
        "collapsed back to the scoped roster"
    )
    # …but the other portal and inactive applicants are NOT.
    assert USREP_ID not in ids, "US rep leaked onto the Canada board"
    assert PENDING_ID not in ids, "inactive applicant leaked onto the board"
    assert out["viewer"] == {"rep_id": REP1_ID}


def test_aggregates_match_the_ui_stage_buckets(monkeypatch):
    """won = customer_walkthrough/pos_connected/closed_won (MRR counts);
    open = anything else except closed_lost; closed_lost counts nowhere."""
    _wire(monkeypatch)
    out = _run(lb.get_leaderboard({"email": "rep1@meridian.test"}))
    by_id = {r["id"]: r for r in out["leaderboard"]}
    assert by_id[REP1_ID] == {
        "id": REP1_ID, "name": "Rep One", "role": "sales_rep",
        "deals_won": 1, "deals_open": 1, "total_mrr": 500,
    }
    assert by_id[DM1_ID]["deals_won"] == 1 and by_id[DM1_ID]["total_mrr"] == 200
    assert by_id[REP2_ID] == {
        "id": REP2_ID, "name": "Rep Two", "role": "sales_rep",
        "deals_won": 0, "deals_open": 0, "total_mrr": 0,
    }
    # Sorted: MRR desc, then deals_won desc.
    mrrs = [r["total_mrr"] for r in out["leaderboard"]]
    assert mrrs == sorted(mrrs, reverse=True)


# ── 2. Response shape is the boundary: NO sensitive keys, ever ────────────────

def test_serialized_payload_has_no_sensitive_keys(monkeypatch):
    _wire(monkeypatch)
    out = _run(lb.get_leaderboard({"email": "rep1@meridian.test"}))
    payload = json.dumps(out)
    for forbidden in ('"email"', '"phone"', '"contact_email"', '"contact_phone"',
                      '"commission_rate"', '"commission"', '"business_name"',
                      '"notes"', '"path"', '"manager_id"'):
        assert forbidden not in payload, f"sensitive key {forbidden} leaked into /api/leaderboard"
    # Positive direction: exactly the allowlisted fields per entry.
    for entry in out["leaderboard"]:
        assert set(entry.keys()) == {"id", "name", "role", "deals_won", "deals_open", "total_mrr"}


# ── 3. portal_context filtering, other direction ──────────────────────────────

def test_us_caller_gets_us_board_only(monkeypatch):
    _wire(monkeypatch)
    out = _run(lb.get_leaderboard({"email": "usrep@meridian.test"}))
    ids = {r["id"] for r in out["leaderboard"]}
    assert USREP_ID in ids and ADMIN_ID in ids  # us + all
    assert REP1_ID not in ids and DM1_ID not in ids, "Canada reps leaked onto the US board"
    by_id = {r["id"]: r for r in out["leaderboard"]}
    assert by_id[USREP_ID]["total_mrr"] == 700 and by_id[USREP_ID]["deals_open"] == 1
    assert out["portal"] == "us"


# ── 4. Auth: 401 unauthenticated, 403 with no rep profile ─────────────────────

def test_unauthenticated_request_is_401(monkeypatch):
    _wire(monkeypatch)
    app = FastAPI()
    app.include_router(lb.router)
    client = TestClient(app)
    resp = client.get("/api/leaderboard")
    assert resp.status_code == 401, "leaderboard must require a valid rep JWT"


def test_session_without_rep_profile_is_403(monkeypatch):
    _wire(monkeypatch)
    with pytest.raises(HTTPException) as e:
        _run(lb.get_leaderboard({"email": "stranger@evil.test"}))
    assert e.value.status_code == 403, "unknown sessions must fail closed"
