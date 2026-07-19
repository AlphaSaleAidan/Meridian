"""Workstream 4 — Cancel Subscription / Cancel Account. Red tests first.

Contract for POST /api/billing/self-cancel:

  1. AUTH: only the authenticated OWNER of the org can cancel. Org is taken
     from the session (owner lookup), never trusted from the body. A member
     who is not the owner is denied; an outsider is denied; unauthenticated
     is denied. Nothing is recorded on a denied call.

  2. RECORD: a successful cancel writes a subscription_cancellations row with
     a timestamp and the captured reason, and flips the subscription to
     canceled/cancel_pending via the existing billing_service path.

  3. TALK-FIRST: the "talk to us first" path (talk_first=true) records NO
     cancellation row and does NOT touch the subscription — it is the
     retention off-ramp, so pressing it must never cancel anything.

  4. WIND-DOWN GATE: access-wind-down enforcement is OFF by default
     (SUBSCRIPTION_WINDDOWN_ENFORCED unset). The recorded row lands in the
     conservative 'recorded' winddown_status and no access is cut.

Pattern mirrors tests/test_security_batch_20260719.py: monkeypatch the
_verify_supabase_token seam, fake DB, minimal TestClient app per router.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.pop("TENANCY_ENFORCEMENT_DISABLED", None)
os.environ.pop("SUBSCRIPTION_WINDDOWN_ENFORCED", None)

import src.db as db_mod  # noqa: E402
from src.api import auth  # noqa: E402
from src.api.routes import billing as billing_mod  # noqa: E402

ORG = "168b6df2-e9af-4b00-8fec-51e51149ff19"
OWNER_ID = "11111111-2222-4333-8444-555555555555"
MEMBER_ID = "22222222-3333-4444-8555-666666666666"

OWNER = {"id": OWNER_ID, "email": "owner@acme.test"}
NON_OWNER_MEMBER = {"id": MEMBER_ID, "email": "staff@acme.test"}
OUTSIDER = {"id": "99999999-8888-4777-8666-555555555555", "email": "intruder@evil.test"}


def _set_token_user(monkeypatch, user):
    async def _verify(_token):
        return user
    monkeypatch.setattr(auth, "_verify_supabase_token", _verify)


class FakeDB:
    """Canned rows + write recording. `businesses` rows drive owner lookup."""

    def __init__(self, owner_id=OWNER_ID):
        self.rows_by_table = {
            "businesses": [{"id": ORG, "owner_user_id": owner_id}],
            "subscriptions": [{"id": "sub-1", "org_id": ORG, "status": "active"}],
        }
        self.inserts: list = []
        self.updates: list = []

    async def select(self, table, columns="*", filters=None, limit=None,
                     order=None, offset=None):
        rows = self.rows_by_table.get(table, [])
        # crude filter emulation for owner_user_id / id / org_id eq lookups
        if filters:
            out = []
            for r in rows:
                ok = True
                for k, v in filters.items():
                    if isinstance(v, str) and v.startswith("eq."):
                        if str(r.get(k)) != v[3:]:
                            ok = False
                            break
                if ok:
                    out.append(r)
            return out
        return rows

    async def insert(self, table, row, return_data=True):
        self.inserts.append((table, row))
        return [row]

    async def update(self, table, vals, filters=None):
        self.updates.append((table, vals, filters))
        return [{"org_id": ORG}]


def _client():
    app = FastAPI()
    app.include_router(billing_mod.router)
    return TestClient(app, raise_server_exceptions=False)


def _no_op_billing_cancel(monkeypatch):
    """Stub billing_service.cancel_subscription so tests don't hit Square."""
    async def _cancel(self, org_id, reason=""):
        return True
    from src.billing.billing_service import BillingService
    monkeypatch.setattr(BillingService, "cancel_subscription", _cancel)


# ─────────────── 1. AUTH: owner-only, org from session ───────────────

def test_self_cancel_unauthenticated_rejected(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(db_mod, "_db_instance", db)
    r = _client().post("/api/billing/self-cancel", json={"reason": "x"})
    assert r.status_code in (401, 403), r.text
    assert db.inserts == []


def test_self_cancel_non_owner_member_rejected(monkeypatch):
    db = FakeDB(owner_id=OWNER_ID)
    monkeypatch.setattr(db_mod, "_db_instance", db)
    _set_token_user(monkeypatch, NON_OWNER_MEMBER)
    monkeypatch.setattr(auth, "ADMIN_EMAILS", [], raising=False)
    r = _client().post("/api/billing/self-cancel", json={"reason": "x"},
                       headers={"Authorization": "Bearer t"})
    assert r.status_code == 403, r.text
    assert db.inserts == []          # nothing recorded
    assert db.updates == []          # subscription untouched


def test_self_cancel_outsider_rejected(monkeypatch):
    db = FakeDB(owner_id=OWNER_ID)
    monkeypatch.setattr(db_mod, "_db_instance", db)
    _set_token_user(monkeypatch, OUTSIDER)
    monkeypatch.setattr(auth, "ADMIN_EMAILS", [], raising=False)
    r = _client().post("/api/billing/self-cancel", json={"reason": "x"},
                       headers={"Authorization": "Bearer t"})
    assert r.status_code == 403, r.text
    assert db.inserts == []


def test_self_cancel_body_org_id_is_ignored(monkeypatch):
    """Even if the body names ANOTHER org, the endpoint cancels the session
    owner's own org — the body org is never trusted."""
    db = FakeDB(owner_id=OWNER_ID)
    monkeypatch.setattr(db_mod, "_db_instance", db)
    _set_token_user(monkeypatch, OWNER)
    _no_op_billing_cancel(monkeypatch)
    r = _client().post("/api/billing/self-cancel",
                       json={"reason": "moving on", "org_id": "some-other-org"},
                       headers={"Authorization": "Bearer t"})
    assert r.status_code == 200, r.text
    # the recorded cancellation is for the OWNER's org, not the injected one
    assert db.inserts, "a cancellation should have been recorded"
    table, row = db.inserts[0]
    assert table == "subscription_cancellations"
    assert row["org_id"] == ORG


# ─────────────── 2. RECORD: timestamp + reason ───────────────

def test_self_cancel_owner_records_row(monkeypatch):
    db = FakeDB(owner_id=OWNER_ID)
    monkeypatch.setattr(db_mod, "_db_instance", db)
    _set_token_user(monkeypatch, OWNER)
    _no_op_billing_cancel(monkeypatch)
    r = _client().post("/api/billing/self-cancel",
                       json={"reason": "too expensive"},
                       headers={"Authorization": "Bearer t"})
    assert r.status_code == 200, r.text
    assert db.inserts, "cancellation row should be written"
    table, row = db.inserts[0]
    assert table == "subscription_cancellations"
    assert row["org_id"] == ORG
    assert row["reason"] == "too expensive"
    assert row.get("canceled_at"), "must record a cancellation timestamp"
    assert row.get("canceled_by_user_id") == OWNER_ID


# ─────────────── 3. TALK-FIRST: records NO cancellation ───────────────

def test_talk_first_records_no_cancellation(monkeypatch):
    db = FakeDB(owner_id=OWNER_ID)
    monkeypatch.setattr(db_mod, "_db_instance", db)
    _set_token_user(monkeypatch, OWNER)
    _no_op_billing_cancel(monkeypatch)
    r = _client().post("/api/billing/self-cancel",
                       json={"reason": "maybe", "talk_first": True},
                       headers={"Authorization": "Bearer t"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("canceled") is False
    assert body.get("talk_first") is True
    # NOTHING recorded, subscription untouched
    assert db.inserts == [], "talk-first must not record a cancellation"
    assert db.updates == [], "talk-first must not touch the subscription"


# ─────────────── 4. WIND-DOWN GATE: off by default ───────────────

def test_winddown_access_change_gated_off_by_default(monkeypatch):
    monkeypatch.delenv("SUBSCRIPTION_WINDDOWN_ENFORCED", raising=False)
    db = FakeDB(owner_id=OWNER_ID)
    monkeypatch.setattr(db_mod, "_db_instance", db)
    _set_token_user(monkeypatch, OWNER)
    _no_op_billing_cancel(monkeypatch)
    r = _client().post("/api/billing/self-cancel",
                       json={"reason": "done"},
                       headers={"Authorization": "Bearer t"})
    assert r.status_code == 200, r.text
    _, row = db.inserts[0]
    # conservative default: recorded only, no access change
    assert row["winddown_status"] == "recorded"
    body = r.json()
    assert body.get("winddown_enforced") is False


def test_winddown_helper_reports_flag(monkeypatch):
    """The gate helper reads the env flag and defaults OFF."""
    monkeypatch.delenv("SUBSCRIPTION_WINDDOWN_ENFORCED", raising=False)
    assert billing_mod._winddown_enforced() is False
    monkeypatch.setenv("SUBSCRIPTION_WINDDOWN_ENFORCED", "true")
    assert billing_mod._winddown_enforced() is True
    monkeypatch.setenv("SUBSCRIPTION_WINDDOWN_ENFORCED", "0")
    assert billing_mod._winddown_enforced() is False
