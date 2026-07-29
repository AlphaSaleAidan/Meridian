"""Careers recruiting pipeline tests (mock db layer, existing api-test style).

Covers:
  1. CA applications create a pending (inactive) sales_reps row at apply time
     via insert-if-absent — never an upsert, never touching an existing row,
     and never for US applications (owner call, 2026-07-29)
  2. stage transitions append stage_history {stage, by, at}; invalid stage 400;
     'hired' is terminal (409 on re-stage)
  3. stage='hired' creates the rep WITH manager_id = recruiter_id (org tree
     grows from recruiting), role='sales_rep', is_active=True
  4. pipeline + stage/assign-recruiter writes are subtree-scoped — asserted in
     BOTH directions (own branch works, sibling branch 403/hidden)

Run:  python -m pytest tests/api/test_careers_pipeline.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api import hierarchy  # noqa: E402
from src.api.routes import careers as careers_mod  # noqa: E402
from src.api.routes import careers_pipeline as pipeline_mod  # noqa: E402
from src.api.routes.careers_pipeline import AssignRecruiterRequest, StageRequest  # noqa: E402

VP_ID = "bbbbbbbb-0000-4000-8000-000000000002"
DM1_ID = "cccccccc-0000-4000-8000-000000000003"
DM2_ID = "eeeeeeee-0000-4000-8000-000000000005"

REPS = {
    "admin@meridian.test": {"id": "aaaaaaaa-0000-4000-8000-000000000001", "email": "admin@meridian.test", "role": "admin", "path": "aaaaaaaa-0000-4000-8000-000000000001", "manager_id": None},
    "dm1@meridian.test": {"id": DM1_ID, "email": "dm1@meridian.test", "role": "district_manager", "path": f"{VP_ID}.{DM1_ID}", "manager_id": VP_ID},
    "dm2@meridian.test": {"id": DM2_ID, "email": "dm2@meridian.test", "role": "district_manager", "path": f"{VP_ID}.{DM2_ID}", "manager_id": VP_ID},
}

APP_DM1 = {"id": "app-1", "name": "Alice Applicant", "email": "alice@apply.test", "phone": "555",
           "country": "CA", "stage": "applied", "stage_history": [], "recruiter_id": DM1_ID}
APP_DM2 = {"id": "app-2", "name": "Bob Applicant", "email": "bob@apply.test", "phone": "",
           "country": "US", "stage": "screened", "stage_history": [], "recruiter_id": DM2_ID}
APP_NONE = {"id": "app-3", "name": "Cara Applicant", "email": "cara@apply.test", "phone": "",
            "country": "CA", "stage": "applied", "stage_history": [], "recruiter_id": None}


def _run(coro):
    return asyncio.run(coro)


class FakeDB:
    def __init__(self, apps, sales_reps=None):
        self.apps = {a["id"]: dict(a) for a in apps}
        self.sales_reps = [dict(r) for r in (sales_reps or [])]
        self.updates: list = []
        self.upserts: list = []
        self.inserts: list = []

    async def select(self, table, columns="*", filters=None, order=None, limit=None, offset=None):
        if table == "sales_reps":
            if filters and "email" in filters:
                em = filters["email"].removeprefix("eq.")
                return [dict(r) for r in self.sales_reps if r.get("email") == em]
            return [dict(r) for r in self.sales_reps]
        if table != "career_applications":
            return []
        if filters and "id" in filters:
            fid = filters["id"].removeprefix("eq.")
            return [dict(self.apps[fid])] if fid in self.apps else []
        return [dict(a) for a in self.apps.values()]

    async def update(self, table, data, filters):
        self.updates.append((table, data, filters))
        if table == "career_applications" and filters and "id" in filters:
            fid = filters["id"].removeprefix("eq.")
            if fid in self.apps:
                self.apps[fid].update(data)
        return [data]

    async def upsert(self, table, data, on_conflict="", return_data=True):
        self.upserts.append((table, data, on_conflict))
        return [{**data, "id": "new-rep-id"}]

    async def insert(self, table, data, return_data=True):
        self.inserts.append((table, data))
        return [data]


def _wire(monkeypatch, db):
    async def _by_email(email):
        return REPS.get((email or "").lower())

    async def _under(path):
        return [r for r in REPS.values() if r["path"] == path or r["path"].startswith(path + ".")]

    monkeypatch.setattr(hierarchy, "_fetch_rep_by_email", _by_email)
    monkeypatch.setattr(hierarchy, "_fetch_reps_under", _under)
    monkeypatch.setattr(pipeline_mod, "get_db", lambda: db)


# ── 1. Apply-time applicant visibility (owner call, 2026-07-29) ──────────────
# CA applications create an INACTIVE sales_reps row (insert-if-absent, never an
# upsert) so applicants show in Team > Applications immediately. A re-application
# must never touch an existing row, and US applications create no row.

def _wire_apply(monkeypatch, db):
    monkeypatch.setattr(careers_mod, "get_db", lambda: db)
    import src.email.send as email_send

    async def _no_email(*a, **kw):
        return {"status": "skipped"}
    monkeypatch.setattr(email_send, "send_career_application", _no_email)


def test_ca_application_creates_pending_applicant_row(monkeypatch):
    db = FakeDB([])
    _wire_apply(monkeypatch, db)

    req = careers_mod.CareerApplication(
        name="Alice Applicant", email="Alice@Example.com", position="sales_rep", city="Toronto",
    )
    out = _run(careers_mod.submit_application(req, country="CA"))
    assert out["status"] == "received"
    assert ("career_applications" in {t for t, _ in db.inserts}), "application row not saved"
    app_row = next(d for t, d in db.inserts if t == "career_applications")
    assert app_row["stage"] == "applied" and app_row["stage_history"] == []

    assert not any(t == "sales_reps" for t, _, _ in db.upserts), (
        "must be an insert-if-absent, never an upsert — an upsert could rewrite an existing rep"
    )
    rep_rows = [d for t, d in db.inserts if t == "sales_reps"]
    assert len(rep_rows) == 1, "CA application must create exactly one pending sales_reps row"
    row = rep_rows[0]
    assert row["is_active"] is False
    assert row["portal_context"] == "canada"
    assert row["email"] == "alice@example.com", "email must be lowercased for the on-hire upsert join"
    assert "id" not in row, "id must come from the DB default, never rewrite a PK"
    assert row.get("org_id"), "org_id is NOT NULL in the live table — insert fails without it"


def test_ca_reapplication_never_touches_existing_rep_row(monkeypatch):
    db = FakeDB([], sales_reps=[{"id": "rep-1", "email": "alice@example.com", "is_active": True}])
    _wire_apply(monkeypatch, db)

    req = careers_mod.CareerApplication(
        name="Alice Applicant", email="alice@example.com", position="sales_rep", city="Toronto",
    )
    out = _run(careers_mod.submit_application(req, country="CA"))
    assert out["status"] == "received"
    assert not any(t == "sales_reps" for t, _ in db.inserts), (
        "existing rep row (active or pending) must never be re-created or deactivated"
    )
    assert not any(t == "sales_reps" for t, _, _ in db.upserts)


def test_us_application_creates_no_sales_reps_row(monkeypatch):
    db = FakeDB([])
    _wire_apply(monkeypatch, db)

    req = careers_mod.CareerApplication(
        name="Bob Applicant", email="bob@example.com", position="sales_rep", city="Austin",
    )
    out = _run(careers_mod.submit_application(req, country="US"))
    assert out["status"] == "received"
    assert not any(t == "sales_reps" for t, _ in db.inserts)
    assert not any(t == "sales_reps" for t, _, _ in db.upserts)


# ── 2. Stage transitions ─────────────────────────────────────────────────────

def test_stage_advance_appends_history(monkeypatch):
    db = FakeDB([APP_DM1])
    _wire(monkeypatch, db)
    out = _run(pipeline_mod.set_stage("app-1", StageRequest(stage="screened"),
                                      {"email": "dm1@meridian.test"}))
    assert out["ok"] and out["stage"] == "screened"
    hist = db.apps["app-1"]["stage_history"]
    assert len(hist) == 1
    assert hist[0]["stage"] == "screened" and hist[0]["by"] == "dm1@meridian.test" and hist[0]["at"]


def test_unknown_stage_is_400(monkeypatch):
    db = FakeDB([APP_DM1])
    _wire(monkeypatch, db)
    with pytest.raises(HTTPException) as e:
        _run(pipeline_mod.set_stage("app-1", StageRequest(stage="ghosted"),
                                    {"email": "dm1@meridian.test"}))
    assert e.value.status_code == 400


def test_hired_is_terminal(monkeypatch):
    db = FakeDB([{**APP_DM1, "stage": "hired"}])
    _wire(monkeypatch, db)
    with pytest.raises(HTTPException) as e:
        _run(pipeline_mod.set_stage("app-1", StageRequest(stage="rejected"),
                                    {"email": "admin@meridian.test"}))
    assert e.value.status_code == 409


# ── 3. Hire creates the rep in the recruiter's downline ──────────────────────

def test_hired_creates_rep_with_recruiter_as_manager(monkeypatch):
    db = FakeDB([{**APP_DM1, "stage": "offer"}])
    _wire(monkeypatch, db)
    out = _run(pipeline_mod.set_stage("app-1", StageRequest(stage="hired"),
                                      {"email": "dm1@meridian.test"}))
    assert out["rep_id"] == "new-rep-id"
    table, row, conflict = next(u for u in db.upserts if u[0] == "sales_reps")
    assert conflict == "email"
    assert row["manager_id"] == DM1_ID, "hire must land in the recruiter's downline"
    assert row["role"] == "sales_rep"
    assert row["is_active"] is True
    assert row["email"] == "alice@apply.test"
    assert row["portal_context"] == "canada"
    assert row.get("org_id"), "org_id is NOT NULL in the live table — hire upsert fails without it"
    assert db.apps["app-1"]["stage"] == "hired"


# ── 4. Subtree scoping (both directions) ─────────────────────────────────────

def test_pipeline_scoped_to_managers_subtree(monkeypatch):
    db = FakeDB([APP_DM1, APP_DM2, APP_NONE])
    _wire(monkeypatch, db)
    out = _run(pipeline_mod.get_pipeline({"email": "dm1@meridian.test"}))
    ids = {a["id"] for a in out["applications"]}
    assert "app-1" in ids, "manager lost own-branch application"
    assert "app-2" not in ids, "sibling-branch application leaked into pipeline"
    assert "app-3" not in ids, "unassigned applications are admin-only"


def test_pipeline_admin_sees_all(monkeypatch):
    db = FakeDB([APP_DM1, APP_DM2, APP_NONE])
    _wire(monkeypatch, db)
    out = _run(pipeline_mod.get_pipeline({"email": "admin@meridian.test"}))
    assert {a["id"] for a in out["applications"]} == {"app-1", "app-2", "app-3"}


def test_stage_change_outside_subtree_is_403(monkeypatch):
    db = FakeDB([APP_DM1, APP_DM2])
    _wire(monkeypatch, db)
    with pytest.raises(HTTPException) as e:
        _run(pipeline_mod.set_stage("app-2", StageRequest(stage="interview"),
                                    {"email": "dm1@meridian.test"}))
    assert e.value.status_code == 403
    assert db.apps["app-2"]["stage"] == "screened", "cross-branch write must not land"


def test_assign_recruiter_within_subtree_ok_outside_403(monkeypatch):
    db = FakeDB([APP_NONE, APP_DM1])
    _wire(monkeypatch, db)
    # admin can hand an unassigned application to any recruiter
    out = _run(pipeline_mod.assign_recruiter("app-3", AssignRecruiterRequest(recruiter_id=DM2_ID),
                                             {"email": "admin@meridian.test"}))
    assert out["ok"] and db.apps["app-3"]["recruiter_id"] == DM2_ID
    # a manager cannot route an application to a recruiter outside their branch
    with pytest.raises(HTTPException) as e:
        _run(pipeline_mod.assign_recruiter("app-1", AssignRecruiterRequest(recruiter_id=DM2_ID),
                                           {"email": "dm1@meridian.test"}))
    assert e.value.status_code == 403
    # …but within their own branch it works
    out = _run(pipeline_mod.assign_recruiter("app-1", AssignRecruiterRequest(recruiter_id=DM1_ID),
                                             {"email": "dm1@meridian.test"}))
    assert out["ok"] and db.apps["app-1"]["recruiter_id"] == DM1_ID
