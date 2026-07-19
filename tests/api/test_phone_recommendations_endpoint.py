"""GET /api/phone/recommendations/{merchant_id} — advisory, org-scoped, read-only.

Locks in:
  * org-membership is enforced (non-member → 403, before any recommendation);
  * a member gets ranked, evidence-backed recs derived from that merchant's
    call-ending telemetry;
  * the endpoint is READ-ONLY — the stub DB records zero writes;
  * a merchant with no telemetry in the window returns an empty rec list, 200;
  * a malformed merchant_id is rejected (400) before touching the DB.

Run: /root/Meridian/.venv/bin/python -m pytest tests/api/test_phone_recommendations_endpoint.py -v
"""
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import src.api.routes.phone_activation as pa  # noqa: E402

MERCHANT = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
OTHER = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


class StubDB:
    """Async DB stub returning cutoff-heavy voice_call_endings rows + write log."""

    def __init__(self, rows):
        self._rows = rows
        self.writes = []

    async def select(self, table, columns="*", filters=None, order=None, limit=None, offset=None):
        if table == "voice_call_endings":
            mid = (filters or {}).get("merchant_id")
            if mid and mid != f"eq.{MERCHANT}":
                return []
            return list(self._rows)
        return []

    async def insert(self, table, row):
        self.writes.append((table, row))
        return [row]

    async def update(self, table, data, filters=None):
        self.writes.append((table, data))
        return []

    async def upsert(self, table, row, on_conflict=None):
        self.writes.append((table, row))
        return [row]


def _rows():
    # 30 cutoff-without-order calls out of 100 → 30% → RAISE_CAP fires.
    rows = []
    for _ in range(30):
        rows.append({"merchant_id": MERCHANT, "disposition": "cutoff",
                     "had_order": False, "duration_seconds": 300})
    for _ in range(70):
        rows.append({"merchant_id": MERCHANT, "disposition": "agent_hangup",
                     "had_order": True, "duration_seconds": 120})
    return rows


def _make_client(monkeypatch, *, member: bool, rows=None):
    stub = StubDB(rows if rows is not None else _rows())
    monkeypatch.setattr(pa, "get_db", lambda: stub)

    async def _org_member(user, org_id):
        if not member:
            raise HTTPException(403, "Access denied")
    monkeypatch.setattr(pa, "require_org_member", _org_member)

    app = FastAPI()
    app.include_router(pa.router)
    # bypass real JWT verification; identity is a fixed test user
    app.dependency_overrides[pa.require_jwt] = lambda: {"id": "u1", "email": "t@t.co"}
    c = TestClient(app, raise_server_exceptions=False)
    c._stub = stub
    return c


def test_member_gets_ranked_recommendations(monkeypatch):
    c = _make_client(monkeypatch, member=True)
    r = c.get(f"/api/phone/recommendations/{MERCHANT}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["merchant_id"] == MERCHANT
    assert body["total_calls"] == 100
    signals = [rec["signal"] for rec in body["recommendations"]]
    assert "RAISE_CAP" in signals
    # advisory + evidence present
    cap = next(rec for rec in body["recommendations"] if rec["signal"] == "RAISE_CAP")
    assert cap["advisory"] is True
    assert cap["evidence"]["cutoff_without_order"] == 30


def test_endpoint_is_read_only(monkeypatch):
    c = _make_client(monkeypatch, member=True)
    c.get(f"/api/phone/recommendations/{MERCHANT}")
    assert c._stub.writes == []


def test_non_member_forbidden(monkeypatch):
    c = _make_client(monkeypatch, member=False)
    r = c.get(f"/api/phone/recommendations/{MERCHANT}")
    assert r.status_code == 403


def test_no_telemetry_returns_empty(monkeypatch):
    c = _make_client(monkeypatch, member=True, rows=[])
    r = c.get(f"/api/phone/recommendations/{MERCHANT}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_calls"] == 0
    assert body["recommendations"] == []


def test_malformed_merchant_id_rejected(monkeypatch):
    c = _make_client(monkeypatch, member=True)
    r = c.get("/api/phone/recommendations/not-a-uuid")
    assert r.status_code == 400
