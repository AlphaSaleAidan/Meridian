"""fee-mode routes must wrap the raw require_jwt user in the principal shape.

Regression: get_fee_mode / create_fee_change_request passed the raw JWT user
dict straight into _enforce_billing_org_access, which reads principal["user"].
The raw dict has no "user" key, so the membership check ran with an empty
user ({} -> user_id "") and denied 403 — even for the org OWNER. Live symptom:
TENANCY_DENY user=None email=None on every merchant Settings page load.
"""
import pytest
from fastapi import HTTPException

from src.api.routes import billing

OWNER = {"id": "u-owner", "email": "owner@example.com"}
ORG = "org-1"


class _FakeDB:
    async def select(self, table, columns="*", filters=None, order=None,
                     limit=None, offset=None):
        return []

    async def insert(self, table, rows):
        return rows


def _membership(member_ids):
    async def _require_org_member(user, org_id):
        # The whole bug: user must be the REAL jwt dict, not {}.
        if user.get("id") not in member_ids:
            raise HTTPException(403, "Access denied: you are not a member of this organization")
    return _require_org_member


@pytest.mark.asyncio
async def test_get_fee_mode_allows_org_owner(monkeypatch):
    monkeypatch.setattr(billing, "require_org_member", _membership({"u-owner"}))
    monkeypatch.setattr(billing, "get_db", lambda: _FakeDB())
    result = await billing.get_fee_mode(ORG, user=OWNER)
    assert result["org_id"] == ORG
    assert result["editable"] is False


@pytest.mark.asyncio
async def test_get_fee_mode_still_denies_non_member(monkeypatch):
    monkeypatch.setattr(billing, "require_org_member", _membership({"someone-else"}))

    async def _not_a_rep(user):
        return False
    monkeypatch.setattr(billing, "_is_active_sales_rep", _not_a_rep)
    monkeypatch.setattr(billing, "get_db", lambda: _FakeDB())
    with pytest.raises(HTTPException) as exc:
        await billing.get_fee_mode(ORG, user=OWNER)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_change_request_allows_org_owner(monkeypatch):
    monkeypatch.setattr(billing, "require_org_member", _membership({"u-owner"}))
    monkeypatch.setattr(billing, "get_db", lambda: _FakeDB())
    req = billing.FeeChangeRequestBody(org_id=ORG, requested_mode="business_pays")
    result = await billing.create_fee_change_request(req, user=OWNER)
    assert result.get("status") in ("submitted", "ok", "created") or result


@pytest.mark.asyncio
async def test_change_request_still_denies_non_member(monkeypatch):
    monkeypatch.setattr(billing, "require_org_member", _membership({"someone-else"}))

    async def _not_a_rep(user):
        return False
    monkeypatch.setattr(billing, "_is_active_sales_rep", _not_a_rep)
    monkeypatch.setattr(billing, "get_db", lambda: _FakeDB())
    req = billing.FeeChangeRequestBody(org_id=ORG, requested_mode="business_pays")
    with pytest.raises(HTTPException) as exc:
        await billing.create_fee_change_request(req, user=OWNER)
    assert exc.value.status_code == 403
