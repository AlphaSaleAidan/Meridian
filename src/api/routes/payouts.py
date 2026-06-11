"""
Payout API Routes — Commission tracking and manual payout management.

Routes:
    GET  /api/payouts/summary                    - Aggregate payout summary
    GET  /api/payouts/reps                       - List all reps with earnings
    GET  /api/payouts/reps/{rep_id}/commissions   - Rep commission history
    GET  /api/payouts/balances                    - All rep balances (what's owed)
    GET  /api/payouts/history                     - Payout history
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_service_auth

logger = logging.getLogger("meridian.api.payouts")
router = APIRouter(prefix="/api/payouts", tags=["payouts"])


def _get_db():
    from ...db import _db_instance
    if _db_instance is None:
        raise HTTPException(503, "Database not initialized")
    return _db_instance


@router.get("/summary", dependencies=[Depends(require_service_auth)])
async def payout_summary():
    """Aggregate payout summary across all reps."""
    db = _get_db()
    reps = await db.select("sales_reps")

    total_earned = sum(float(r.get("total_earned", 0) or 0) for r in reps)
    total_paid = sum(float(r.get("total_paid", 0) or 0) for r in reps)
    active_reps = sum(1 for r in reps if r.get("is_active"))

    return {
        "total_reps": len(reps),
        "active_reps": active_reps,
        "total_earned_cents": int(total_earned * 100),
        "total_paid_cents": int(total_paid * 100),
        "total_pending_cents": int((total_earned - total_paid) * 100),
    }


@router.get("/reps", dependencies=[Depends(require_service_auth)])
async def list_reps():
    """List all sales reps with their earnings."""
    db = _get_db()
    reps = await db.select("sales_reps", order="created_at.desc")
    return {"reps": reps}


@router.get("/reps/{rep_id}/commissions", dependencies=[Depends(require_service_auth)])
async def rep_commissions(rep_id: str, limit: int = 50):
    """Get commission history for a rep."""
    db = _get_db()
    try:
        commissions = await db.select(
            "commissions",
            filters={"rep_id": f"eq.{rep_id}"},
            order="created_at.desc",
            limit=limit,
        )
    except Exception:
        commissions = []
    return {"commissions": commissions}


@router.get("/balances", dependencies=[Depends(require_service_auth)])
async def all_balances():
    """Get what's owed to each rep."""
    db = _get_db()
    reps = await db.select("sales_reps", filters={"is_active": "eq.true"})

    balances = []
    for r in reps:
        earned = float(r.get("total_earned", 0) or 0)
        paid = float(r.get("total_paid", 0) or 0)
        balances.append({
            "rep_id": r.get("id"),
            "rep_name": r.get("name"),
            "total_earned": earned,
            "total_paid": paid,
            "balance_owed": round(earned - paid, 2),
        })

    return {"balances": balances}


@router.get("/history", dependencies=[Depends(require_service_auth)])
async def payout_history(limit: int = 50):
    """Get payout history across all reps."""
    db = _get_db()
    try:
        payouts = await db.select(
            "payouts",
            order="created_at.desc",
            limit=limit,
        )
    except Exception:
        payouts = []
    return {"payouts": payouts}
