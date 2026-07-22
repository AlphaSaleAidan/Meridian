"""
connect-pos / verify-pos lead-ownership guard (2026-07-22 sweep):
a rep may only connect/verify POS for a lead assigned to them or unassigned —
previously any logged-in rep could flip another rep's deal (require_jwt only).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.api.routes import onboarding as ob  # noqa: E402

aio = pytest.mark.asyncio


class _DB:
    def __init__(self, lead_rep, reps=None):
        self._lead_rep = lead_rep
        self._reps = reps if reps is not None else [
            {"id": "rep-me", "email": "me@x.com", "is_active": True}]

    async def select(self, table, columns=None, filters=None, limit=None):
        if table == "sales_reps":
            return list(self._reps)
        # lead table
        return [{"rep_id": self._lead_rep}] if self._lead_rep is not None else [{"rep_id": None}]


CLAIMS = {"email": "me@x.com"}  # resolves to rep-me


@aio
async def test_owner_passes():
    await ob._enforce_lead_owner(_DB(lead_rep="rep-me"), "us_leads", "d1", CLAIMS)  # no raise


@aio
async def test_unassigned_lead_passes():
    await ob._enforce_lead_owner(_DB(lead_rep=None), "us_leads", "d1", CLAIMS)  # no raise


@aio
async def test_missing_lead_passes():
    class _Empty(_DB):
        async def select(self, table, columns=None, filters=None, limit=None):
            if table == "sales_reps":
                return self._reps
            return []
    await ob._enforce_lead_owner(_Empty(lead_rep=None), "us_leads", "gone", CLAIMS)  # no raise


@aio
async def test_other_reps_lead_403():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await ob._enforce_lead_owner(_DB(lead_rep="rep-someone-else"), "us_leads", "d1", CLAIMS)
    assert exc.value.status_code == 403


@aio
async def test_non_rep_session_403():
    from fastapi import HTTPException
    db = _DB(lead_rep="rep-x", reps=[])  # caller isn't a rep
    with pytest.raises(HTTPException) as exc:
        await ob._enforce_lead_owner(db, "us_leads", "d1", CLAIMS)
    assert exc.value.status_code == 403
