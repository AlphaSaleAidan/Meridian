"""
Canada rep commission API — READ-ONLY, rep-facing.

Backed by the milestone commission engine (migration 045 +
src/services/commission_engine.py). INERT with respect to billing: nothing
here writes the ledger; scheduling/cancellation wiring is a separate
reviewed change.

Auth model (same pattern as the canada_leads rep isolation): the caller
presents a Supabase user JWT (require_jwt); the rep row is resolved by the
verified token email against sales_reps. Queries then scope to that rep_id
using the service-role db client — a rep can only ever read their own rows.
(RLS on commission_milestones enforces the same email-join isolation for
any direct PostgREST access.)

Routes:
    GET /api/canada/commissions/summary     - earned / pending / paid / next payday
    GET /api/canada/commissions/milestones  - the rep's milestone ledger rows
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_jwt

logger = logging.getLogger("meridian.api.commissions")

router = APIRouter(prefix="/api/canada/commissions", tags=["commissions"])


def _get_db():
    from ...db import _db_instance
    if _db_instance is None:
        raise HTTPException(503, "Database not initialized")
    return _db_instance


async def _resolve_rep_id(db, claims: dict) -> str:
    """Map the authenticated Supabase user to their sales_reps row by email.

    auth user id != sales_reps.id (reps are provisioned by the backend, not
    auth signup) — email is the canonical join key, same as the canada_leads
    RLS policies.
    """
    email = (claims.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(403, "No email on session")
    reps = await db.select(
        "sales_reps",
        columns="id,is_active",
        filters={"email": f"eq.{email}"},
        limit=1,
    )
    if not reps:
        raise HTTPException(403, "Not a sales rep account")
    return reps[0]["id"]


@router.get("/summary")
async def commission_summary(claims: dict = Depends(require_jwt)):
    """Rep's own rollup: earned (unpaid) / pending / paid + next payday."""
    from ...services.commission_engine import CommissionEngineService

    db = _get_db()
    rep_id = await _resolve_rep_id(db, claims)

    svc = CommissionEngineService(db=db)
    summary = await svc.rep_summary(rep_id)
    # Keep the summary payload lean; the full ledger has its own endpoint.
    summary.pop("milestones", None)
    return {"rep_id": rep_id, **summary}


@router.get("/milestones")
async def commission_milestones(claims: dict = Depends(require_jwt), limit: int = 200):
    """Rep's own milestone ledger rows (newest account first)."""
    db = _get_db()
    rep_id = await _resolve_rep_id(db, claims)

    rows = await db.select(
        "commission_milestones",
        filters={"rep_id": f"eq.{rep_id}"},
        order="created_at.desc",
        limit=min(max(limit, 1), 500),
    )
    return {"rep_id": rep_id, "milestones": rows}
