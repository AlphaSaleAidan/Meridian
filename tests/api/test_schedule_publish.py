"""Schedule publish + CRUD regression tests (Workstream 1f).

The schedule route had NO test coverage. After the Team Management rename +
RBAC additions we lock in the publish flow end-to-end and regression-test the
shift/staff CRUD paths that the schedule UI depends on.

Publish specifically:
  draft shifts → POST /publish → all marked published, a published_schedules row
  written, notified_count returned, notify failures never break the publish.

Run: /root/Meridian/.venv/bin/python -m pytest tests/api/test_schedule_publish.py -v
"""
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import src.api.routes.schedule as sched  # noqa: E402
from src.api.auth import require_service_auth  # noqa: E402

MERCHANT = "11111111-1111-1111-1111-111111111111"
STAFF = "22222222-2222-2222-2222-222222222222"
SHIFT = "33333333-3333-3333-3333-333333333333"
WEEK = "2026-07-13"


class StubDB:
    def __init__(self):
        self.inserts = []
        self.updates = []
        self.deletes = []
        # A published table that starts empty.
        self.published_rows = []

    async def select(self, table, columns="*", filters=None, order=None, limit=None, offset=None):
        f = filters or {}
        if table == "schedule_staff":
            return [{"id": STAFF, "merchant_id": MERCHANT, "name": "Alice",
                     "active": True, "phone": None}]
        if table == "schedule_shifts":
            # id-keyed lookup (BOLA guard for update/delete)
            if f.get("id") == f"eq.{SHIFT}":
                return [{"id": SHIFT, "merchant_id": MERCHANT}]
            return [{"id": SHIFT, "merchant_id": MERCHANT, "staff_member_id": STAFF,
                     "week_start_date": WEEK, "day_of_week": 0, "start_time": "09:00",
                     "end_time": "17:00", "status": "published"}]
        return []

    async def insert(self, table, row):
        self.inserts.append((table, row))
        return [dict(row)]

    async def update(self, table, data, filters=None):
        self.updates.append((table, data, filters))
        return [{}]

    async def delete(self, table, filters=None):
        self.deletes.append((table, filters))
        return []


@pytest.fixture
def client(monkeypatch):
    stub = StubDB()
    monkeypatch.setattr(sched, "get_db", lambda: stub)
    # enforce_service_member is called inside handlers; stub it to a no-op so we
    # test the route logic, not membership (RBAC is covered elsewhere).
    async def _noop(*a, **k):
        return None
    monkeypatch.setattr(sched, "enforce_service_member", _noop)
    app = FastAPI()
    app.include_router(sched.router)
    app.dependency_overrides[require_service_auth] = lambda: {"kind": "service"}
    c = TestClient(app, raise_server_exceptions=False)
    c._stub = stub
    return c


# ── Publish ─────────────────────────────────────────────────────────────────
def test_publish_marks_drafts_and_records(client):
    r = client.post("/api/schedule/publish", json={
        "merchant_id": MERCHANT, "portal_context": "ca",
        "week_start_date": WEEK, "published_by": "Cafe A", "notify_staff": False,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "published"
    assert body["week_start_date"] == WEEK

    stub = client._stub
    # Draft shifts for the week were flipped to published.
    assert any(
        t == "schedule_shifts" and data.get("status") == "published"
        for t, data, _ in stub.updates
    )
    # A published_schedules row was written.
    assert any(t == "published_schedules" for t, _ in stub.inserts)


def test_publish_notify_failure_does_not_break(client, monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("twilio down")
    monkeypatch.setattr(sched, "_notify_published_staff", boom)
    r = client.post("/api/schedule/publish", json={
        "merchant_id": MERCHANT, "week_start_date": WEEK,
        "published_by": "Cafe A", "notify_staff": True,
    })
    # Publish still succeeds; notified_count falls back to 0.
    assert r.status_code == 200
    assert r.json()["notified_count"] == 0


def test_publish_rejects_bad_merchant_id(client):
    r = client.post("/api/schedule/publish", json={
        "merchant_id": "not-a-uuid", "week_start_date": WEEK,
    })
    assert r.status_code == 400


# ── Shift CRUD regression ───────────────────────────────────────────────────
def test_create_shift(client):
    r = client.post("/api/schedule/shifts", json={
        "merchant_id": MERCHANT, "portal_context": "ca", "staff_member_id": STAFF,
        "week_start_date": WEEK, "day_of_week": 0, "shift_date": "2026-07-13",
        "start_time": "09:00", "end_time": "17:00",
    })
    assert r.status_code == 200
    assert any(t == "schedule_shifts" for t, _ in client._stub.inserts)


def test_update_shift(client):
    r = client.put(f"/api/schedule/shifts/{SHIFT}", json={"end_time": "18:00"})
    assert r.status_code == 200
    assert any(t == "schedule_shifts" and data.get("end_time") == "18:00"
               for t, data, _ in client._stub.updates)


def test_delete_shift(client):
    r = client.delete(f"/api/schedule/shifts/{SHIFT}")
    assert r.status_code == 200
    assert any(t == "schedule_shifts" for t, _ in client._stub.deletes)


def test_update_shift_no_fields_400(client):
    r = client.put(f"/api/schedule/shifts/{SHIFT}", json={})
    assert r.status_code == 400


# ── Staff CRUD regression ───────────────────────────────────────────────────
def test_create_staff(client):
    r = client.post("/api/schedule/staff", json={
        "merchant_id": MERCHANT, "portal_context": "ca", "name": "Bob",
    })
    assert r.status_code == 200
    assert any(t == "schedule_staff" for t, _ in client._stub.inserts)


def test_list_shifts(client):
    r = client.get(f"/api/schedule/shifts/{MERCHANT}", params={"week_start": WEEK})
    assert r.status_code == 200
    assert "shifts" in r.json()
