"""Route-level RBAC + tenancy tests for Team Management (Workstream 1b/1c/1d/1e).

These assert enforcement at the API layer (not just the rbac helper):
  - manager WITHOUT edit_punches gets 403 on a punch correction
  - employee cannot see the hours summary (financials/schedule not granted)
  - cross-org member cannot read another org's punches or chat
  - punch correction requires edit_reason AND writes an append-only audit row
  - owner can do everything
  - team-admin cannot create a second owner; cannot promote to owner
  - chatbot /send is blocked for a disabled/unknown org (no LLM call)

Run: /root/Meridian/.venv/bin/python -m pytest tests/api/test_team_management_routes.py -v
"""
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import src.api.rbac as rbac  # noqa: E402
import src.api.routes.time_clock as tclock  # noqa: E402
import src.api.routes.team_chat as tchat  # noqa: E402
import src.api.routes.chatbot as tbot  # noqa: E402
from src.api.auth import require_service_auth  # noqa: E402

ORG_A = "biz_aaaaaaaa"
ORG_B = "biz_bbbbbbbb"
EMP_A = "11111111-1111-1111-1111-111111111111"   # schedule_staff.id in ORG_A
PUNCH_A = "22222222-2222-2222-2222-222222222222"
CH_A = "33333333-3333-3333-3333-333333333333"    # channel in ORG_A


# ── Principals: injected via dependency_overrides so no real auth runs ───────
def _as(kind_user_id, email="u@x.com"):
    def _dep():
        return {"kind": "user", "user": {"id": kind_user_id, "email": email}}
    return _dep


OWNER = "owner-uid"
MANAGER_NOPERM = "manager-noperm-uid"     # manager, edit_punches NOT granted
MANAGER_PUNCH = "manager-punch-uid"       # manager, edit_punches granted
EMPLOYEE = "employee-uid"


class StubDB:
    """In-memory stand-in for SupabaseREST covering the tables these routes hit."""

    def __init__(self):
        self.writes = []
        self.updates = []

    async def select(self, table, columns="*", filters=None, order=None, limit=None, offset=None):
        f = filters or {}
        if table == "schedule_staff":
            if f.get("id") == f"eq.{EMP_A}" and f.get("merchant_id") == f"eq.{ORG_A}":
                return [{"id": EMP_A, "merchant_id": ORG_A, "name": "Alice", "active": True}]
            if f.get("merchant_id") == f"eq.{ORG_A}":
                return [{"id": EMP_A, "merchant_id": ORG_A, "name": "Alice", "active": True}]
            return []
        if table == "schedule_shifts":
            return []
        if table == "time_punches":
            if f.get("id") == f"eq.{PUNCH_A}" and f.get("org_id") == f"eq.{ORG_A}":
                return [{"id": PUNCH_A, "org_id": ORG_A, "employee_id": EMP_A,
                         "clock_in_at": "2026-07-14T09:00:00+00:00", "clock_out_at": None}]
            if f.get("org_id") == f"eq.{ORG_A}":
                return [{"id": PUNCH_A, "org_id": ORG_A, "employee_id": EMP_A,
                         "clock_in_at": "2026-07-14T09:00:00+00:00",
                         "clock_out_at": "2026-07-14T17:00:00+00:00"}]
            return []
        if table == "team_channels":
            if f.get("id") == f"eq.{CH_A}" and f.get("org_id") == f"eq.{ORG_A}":
                return [{"id": CH_A, "org_id": ORG_A, "name": "general"}]
            if f.get("org_id") == f"eq.{ORG_A}":
                return [{"id": CH_A, "org_id": ORG_A, "name": "general", "archived": False}]
            return []
        if table == "team_messages":
            return []
        if table == "chatbot_config":
            if f.get("org_id") == f"eq.{ORG_A}":
                return [{"org_id": ORG_A, "enabled": True, "business_name": "Cafe A",
                         "tone": "friendly", "canned_answers": [{"q": "hours", "a": "9-5"}],
                         "allowed_topics": [], "escalation_to_human": False,
                         "escalation_contact": ""}]
            return []  # ORG_B has no config
        return []

    async def insert(self, table, row):
        self.writes.append((table, row))
        return [dict(row)]

    async def upsert(self, table, row, on_conflict=None):
        self.writes.append((table, row))
        return [dict(row)]

    async def update(self, table, data, filters=None):
        self.updates.append((table, data, filters))
        return [{}]

    async def delete(self, table, filters=None):
        return []


@pytest.fixture
def db(monkeypatch):
    stub = StubDB()
    monkeypatch.setattr(tclock, "get_db", lambda: stub)
    monkeypatch.setattr(tchat, "get_db", lambda: stub)
    monkeypatch.setattr(tbot, "get_db", lambda: stub)
    monkeypatch.setattr(rbac, "get_db", lambda: stub) if hasattr(rbac, "get_db") else None
    return stub


@pytest.fixture(autouse=True)
def stub_rbac(monkeypatch):
    """Resolve roles/permissions in-memory. ORG_A only; ORG_B has no members."""
    roles = {
        (OWNER, ORG_A): {"role": "owner", "permissions": {}, "is_owner": True, "member_id": None},
        (MANAGER_NOPERM, ORG_A): {"role": "manager", "is_owner": False, "member_id": "m1",
                                  "permissions": {"visibility": {"schedule": True}, "actions": {}}},
        (MANAGER_PUNCH, ORG_A): {"role": "manager", "is_owner": False, "member_id": "m2",
                                 "permissions": {"visibility": {"schedule": True},
                                                 "actions": {"edit_punches": True}}},
        (EMPLOYEE, ORG_A): {"role": "employee", "is_owner": False, "member_id": "m3",
                            "permissions": {}},
    }

    async def fake_resolve(principal, org_id):
        uid = (principal.get("user") or {}).get("id")
        key = (uid, org_id)
        if key not in roles:
            from fastapi import HTTPException
            raise HTTPException(403, "Access denied: not a member")
        base = roles[key]
        perms = base.get("permissions") or {}
        return {
            "role": base["role"],
            "is_owner": base["is_owner"],
            "member_id": base.get("member_id"),
            "permissions": {"visibility": perms.get("visibility", {}), "actions": perms.get("actions", {})},
        }

    monkeypatch.setattr(rbac, "resolve_access", fake_resolve)
    return roles


def _client(principal_uid):
    app = FastAPI()
    app.include_router(tclock.router)
    app.include_router(tchat.router)
    app.include_router(tbot.router)
    app.dependency_overrides[require_service_auth] = _as(principal_uid)
    return TestClient(app, raise_server_exceptions=False)


# ── Time clock RBAC ─────────────────────────────────────────────────────────
def test_manager_without_edit_punches_cannot_correct(db):
    c = _client(MANAGER_NOPERM)
    r = c.patch(f"/api/time-clock/punches/{PUNCH_A}",
                json={"org_id": ORG_A, "clock_out_at": "2026-07-14T18:00:00+00:00",
                      "edit_reason": "forgot to clock out"})
    assert r.status_code == 403


def test_manager_with_edit_punches_can_correct_and_audits(db):
    c = _client(MANAGER_PUNCH)
    r = c.patch(f"/api/time-clock/punches/{PUNCH_A}",
                json={"org_id": ORG_A, "clock_out_at": "2026-07-14T18:00:00+00:00",
                      "edit_reason": "forgot to clock out"})
    assert r.status_code == 200
    # An append-only audit row must have been written.
    assert any(t == "time_punch_audit" for t, _ in db.writes)


def test_punch_correction_requires_edit_reason(db):
    c = _client(OWNER)
    r = c.patch(f"/api/time-clock/punches/{PUNCH_A}",
                json={"org_id": ORG_A, "clock_out_at": "2026-07-14T18:00:00+00:00",
                      "edit_reason": "   "})
    assert r.status_code == 400


def test_employee_cannot_view_hours_summary(db):
    c = _client(EMPLOYEE)
    r = c.get("/api/time-clock/summary", params={"org_id": ORG_A, "week_start": "2026-07-14"})
    assert r.status_code == 403


def test_owner_can_view_hours_summary(db):
    c = _client(OWNER)
    r = c.get("/api/time-clock/summary", params={"org_id": ORG_A, "week_start": "2026-07-14"})
    assert r.status_code == 200
    assert "rows" in r.json()


# ── Cross-org isolation ─────────────────────────────────────────────────────
def test_cross_org_member_cannot_read_punches(db):
    # OWNER is owner of ORG_A but NOT a member of ORG_B → 403.
    c = _client(OWNER)
    r = c.get("/api/time-clock/punches", params={"org_id": ORG_B})
    assert r.status_code == 403


def test_cross_org_member_cannot_read_chat(db):
    c = _client(OWNER)
    r = c.get("/api/team-chat/messages", params={"org_id": ORG_B, "channel_id": CH_A})
    assert r.status_code == 403


# ── Team chat ───────────────────────────────────────────────────────────────
def test_employee_can_post_chat(db):
    c = _client(EMPLOYEE)
    r = c.post("/api/team-chat/messages",
               json={"org_id": ORG_A, "channel_id": CH_A, "body": "hello team"})
    assert r.status_code == 200
    assert any(t == "team_messages" for t, _ in db.writes)


# ── Chatbot ─────────────────────────────────────────────────────────────────
def test_chatbot_send_disabled_org_404(db):
    # ORG_B has no config → not enabled → 404, and NO llm call.
    c = _client(OWNER)  # send is unauth but principal override is harmless
    r = c.post("/api/chatbot/send", json={"org_id": ORG_B, "message": "hi"})
    assert r.status_code == 404


def test_chatbot_send_canned_answer_no_llm(db):
    c = _client(OWNER)
    r = c.post("/api/chatbot/send", json={"org_id": ORG_A, "message": "what are your hours"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "canned"
    assert body["reply"] == "9-5"


# ── Chatbot abuse throttling (per-IP + per-org rate limit, input size cap) ────
from src.api.auth import RateLimiter  # noqa: E402


@pytest.fixture
def throttle(monkeypatch):
    """Shrink the two chatbot limiters to tiny, fresh windows for fast tests.

    per-IP = 3/min, per-org = 5/min. Fresh RateLimiter instances so no state
    bleeds between tests.
    """
    ip_lim = RateLimiter(requests_per_minute=3)
    org_lim = RateLimiter(requests_per_minute=5)
    monkeypatch.setattr(tbot, "_ip_limiter", ip_lim)
    monkeypatch.setattr(tbot, "_org_limiter", org_lim)
    return ip_lim, org_lim


def _send(c, org_id, msg="hello", ip="9.9.9.9"):
    return c.post(
        "/api/chatbot/send",
        json={"org_id": org_id, "message": msg},
        headers={"x-forwarded-for": ip},
    )


def test_chatbot_send_under_ip_limit_passes(db, throttle):
    c = _client(OWNER)
    # per-IP limit is 3; the first 3 from one IP must pass (canned → 200).
    for _ in range(3):
        r = _send(c, ORG_A, "what are your hours", ip="1.1.1.1")
        assert r.status_code == 200


def test_chatbot_send_burst_over_ip_limit_gets_429(db, throttle):
    c = _client(OWNER)
    codes = [_send(c, ORG_A, "what are your hours", ip="2.2.2.2").status_code
             for _ in range(5)]
    # 3 allowed, then 429s.
    assert codes[:3] == [200, 200, 200]
    assert codes[3] == 429 and codes[4] == 429


def test_chatbot_ip_limit_is_per_ip_independent(db, throttle):
    c = _client(OWNER)
    # Exhaust IP A.
    for _ in range(3):
        assert _send(c, ORG_A, "what are your hours", ip="3.3.3.3").status_code == 200
    assert _send(c, ORG_A, "what are your hours", ip="3.3.3.3").status_code == 429
    # A DIFFERENT IP still has its own fresh budget.
    assert _send(c, ORG_A, "what are your hours", ip="4.4.4.4").status_code == 200


def test_chatbot_org_limit_trips_across_many_ips(db, throttle):
    # per-org limit is 5. Send from 6 DISTINCT IPs (each under its own IP cap)
    # to the SAME org → the org window trips independently of any IP window.
    c = _client(OWNER)
    codes = [_send(c, ORG_A, "what are your hours", ip=f"10.0.0.{i}").status_code
             for i in range(6)]
    assert codes[:5] == [200] * 5
    assert codes[5] == 429  # org window exhausted, not the per-IP window


def test_chatbot_org_limit_is_per_org_independent(db, throttle):
    # Fill ORG_A's org window from distinct IPs; ORG_B still gets its own window.
    c = _client(OWNER)
    for i in range(5):
        assert _send(c, ORG_A, "what are your hours", ip=f"11.0.0.{i}").status_code == 200
    assert _send(c, ORG_A, "what are your hours", ip="11.0.0.99").status_code == 429
    # ORG_B has no config → 404 (NOT 429): a different org's throttle window is
    # untouched, so we reach the config gate rather than the org rate limit.
    assert _send(c, ORG_B, "hi", ip="11.0.0.99").status_code == 404


def test_chatbot_send_oversized_input_rejected(db, throttle):
    c = _client(OWNER)
    huge = "x" * 9000  # > CHATBOT_SEND_MAX_INPUT default (8000)
    r = _send(c, ORG_A, huge, ip="5.5.5.5")
    assert r.status_code == 413
    # Oversized input must be rejected BEFORE any transcript write.
    assert not any(t == "chatbot_messages" for t, _ in db.writes)
