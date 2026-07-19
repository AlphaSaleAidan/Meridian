"""Regression tests for the POS waitlist org-id-from-body write (WS8 reconcile).

Finding (org_id-from-body class): POST /api/pos/waitlist is an intentionally
PUBLIC endpoint (a prospect joins a waitlist by email, no JWT). It accepts an
optional `org_id` in the request body and, before the fix, performed a
privileged side-effect:

    UPDATE organizations SET pos_waitlist_email = <caller email>
    WHERE id = <caller-supplied org_id>

Because the caller supplies `org_id` and the endpoint required no auth, ANY
unauthenticated caller could stamp an arbitrary email onto ANY organization
row — a cross-tenant write keyed on a client-supplied identifier.

Fix: the public waitlist INSERT still happens for everyone, but the
`organizations` UPDATE only fires when the request carries a principal that is
a VERIFIED member of that org (or a machine principal). An unauthenticated /
non-member caller gets a normal 200 (they joined the waitlist) but no
cross-tenant write occurs.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.pop("TENANCY_ENFORCEMENT_DISABLED", None)

from src.api import auth  # noqa: E402
from src.api.routes import pos as pos_mod  # noqa: E402
import src.db as db_mod  # noqa: E402

ORG = "168b6df2-e9af-4b00-8fec-51e51149ff19"


class _FakeDB:
    def __init__(self):
        self.inserts: list = []
        self.updates: list = []

    async def insert(self, table, row):
        self.inserts.append((table, row))
        return [row]

    async def update(self, table, vals, filters=None):
        self.updates.append((table, vals, filters))
        return []

    async def select(self, *a, **k):
        return []


def _client(monkeypatch):
    db = _FakeDB()
    monkeypatch.setattr(db_mod, "_db_instance", db, raising=False)
    app = FastAPI()
    app.include_router(pos_mod.router)
    return TestClient(app, raise_server_exceptions=False), db


def test_waitlist_unauthenticated_does_not_write_foreign_org(monkeypatch):
    """The public insert still works, but NO cross-tenant organizations UPDATE
    happens for an unauthenticated caller who names an arbitrary org_id."""
    c, db = _client(monkeypatch)
    r = c.post("/api/pos/waitlist",
               json={"email": "attacker@evil.test", "pos_system": "toast", "org_id": ORG})
    assert r.status_code == 200, r.text
    # Waitlist row is still recorded (public signup preserved).
    assert any(t == "pos_waitlist" for t, _ in db.inserts)
    # But the privileged organizations write must NOT have fired.
    assert not any(t == "organizations" for t, _, _ in db.updates), (
        "unauthenticated caller wrote to organizations with a body-supplied org_id"
    )


def test_waitlist_authenticated_member_stamps_own_org(monkeypatch):
    """A verified member CAN stamp their own org — feature preserved for the
    legitimate in-portal path."""
    async def _verify(_t):
        return {"id": "u1", "email": "owner@acme.test"}

    async def _member(_u, _o):
        return True

    monkeypatch.setattr(auth, "_verify_supabase_token", _verify)
    monkeypatch.setattr(auth, "_check_org_membership", _member)
    c, db = _client(monkeypatch)
    r = c.post("/api/pos/waitlist",
               json={"email": "owner@acme.test", "pos_system": "toast", "org_id": ORG},
               headers={"Authorization": "Bearer sess"})
    assert r.status_code == 200, r.text
    assert any(t == "organizations" for t, _, _ in db.updates), (
        "verified member should still be able to stamp their own org"
    )


def test_waitlist_no_org_is_pure_public_signup(monkeypatch):
    """No org_id → pure public waitlist signup, no org write."""
    c, db = _client(monkeypatch)
    r = c.post("/api/pos/waitlist",
               json={"email": "prospect@lead.test", "pos_system": "clover"})
    assert r.status_code == 200, r.text
    assert any(t == "pos_waitlist" for t, _ in db.inserts)
    assert not any(t == "organizations" for t, _, _ in db.updates)
