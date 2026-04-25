"""
Payout API Routes — Commission tracking and manual payout management.

Routes:
    GET  /api/payouts/reps                       - List all reps with earnings
    GET  /api/payouts/reps/{rep_id}/earnings      - Rep earnings summary  
    GET  /api/payouts/reps/{rep_id}/commissions   - Rep commission history
    POST /api/payouts/reps/{rep_id}/record-payout - Record a manual payout
    GET  /api/payouts/balances                    - All rep balances (what's owed)
    GET  /api/payouts/history                     - Payout history
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("meridian.api.payouts")
router = APIRouter(prefix="/api/payouts", tags=["payouts"])


class RecordPayoutRequest(BaseModel):
    method: str = "manual"  # venmo, zelle, bank_transfer, cash, etc.
    notes: Optional[str] = None


def create_payout_routes(db_client):
    """Factory to create routes with injected DB client."""
    
    from ...payouts.commission_service import CommissionService
    from ...payouts.payout_service import PayoutTracker

    commission_svc = CommissionService(db_client)
    payout_tracker = PayoutTracker(db_client)

    @router.get("/reps")
    async def list_reps():
        """List all sales reps with their earnings."""
        result = db_client.table("sales_reps").select(
            "id, name, email, phone, commission_rate, recruiter, "
            "is_active, total_earned, total_paid, created_at"
        ).order("created_at", desc=True).execute()
        return {"reps": result.data or []}

    @router.get("/reps/{rep_id}/earnings")
    async def rep_earnings(rep_id: str):
        """Get earnings summary for a specific rep."""
        try:
            earnings = await commission_svc.get_rep_earnings(rep_id)
            return {
                "rep": earnings["rep"],
                "total_earned": float(earnings["total_earned"]),
                "total_paid": float(earnings["total_paid"]),
                "pending_payout": float(earnings["pending_payout"]),
            }
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.get("/reps/{rep_id}/commissions")
    async def rep_commissions(rep_id: str, limit: int = 50, offset: int = 0):
        """Get commission history for a rep."""
        result = db_client.table("commissions").select(
            "*, organizations(name)"
        ).eq("rep_id", rep_id).order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()
        return {"commissions": result.data or []}

    @router.post("/reps/{rep_id}/record-payout")
    async def record_payout(rep_id: str, req: RecordPayoutRequest):
        """Record a manual payout to a rep (marks all pending commissions as paid)."""
        payout_id = await commission_svc.record_payout(
            rep_id=rep_id,
            method=req.method,
            notes=req.notes,
        )
        if not payout_id:
            raise HTTPException(status_code=400, detail="No pending commissions to pay out")
        
        # Fetch payout details
        payout = db_client.table("payouts").select("*").eq(
            "id", payout_id
        ).single().execute()
        
        return {
            "payout_id": payout_id,
            "amount": float(payout.data["amount"]),
            "commission_count": payout.data["commission_count"],
            "method": payout.data["method"],
        }

    @router.get("/balances")
    async def all_balances():
        """Get what's owed to each rep."""
        balances = await payout_tracker.get_all_balances()
        return {
            "balances": [
                {
                    "rep_id": b.rep_id,
                    "rep_name": b.rep_name,
                    "total_earned": float(b.total_earned),
                    "total_paid": float(b.total_paid),
                    "balance_owed": float(b.balance_owed),
                    "pending_commissions": b.pending_commissions,
                }
                for b in balances
            ]
        }

    @router.get("/history")
    async def payout_history(limit: int = 50):
        """Get payout history across all reps."""
        history = await payout_tracker.get_payout_history(limit=limit)
        return {"payouts": history}

    return router
