"""
Payout API Routes — Endpoints for commission tracking and payout management.

Routes:
    GET  /api/payouts/reps                      - List all reps with earnings
    GET  /api/payouts/reps/{rep_id}/earnings     - Rep earnings summary
    GET  /api/payouts/reps/{rep_id}/commissions  - Rep commission history
    POST /api/payouts/reps/{rep_id}/payout       - Trigger payout for a rep
    POST /api/payouts/process-all                - Process payouts for all reps (cron)
    GET  /api/payouts/history                    - Payout history
"""

import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("meridian.api.payouts")
router = APIRouter(prefix="/api/payouts", tags=["payouts"])


def create_payout_routes(db_client):
    """Factory to create routes with injected DB client."""
    
    from ...payouts.commission_service import CommissionService
    from ...payouts.payout_service import PayoutService

    commission_svc = CommissionService(db_client)
    payout_svc = PayoutService(db_client)

    @router.get("/reps")
    async def list_reps():
        """List all sales reps with their earnings."""
        result = db_client.table("sales_reps").select(
            "id, name, email, phone, commission_rate, recruiter, "
            "stripe_connect_onboarded, is_active, total_earned, total_paid, created_at"
        ).order("created_at", desc=True).execute()
        return {"reps": result.data or []}

    @router.get("/reps/{rep_id}/earnings")
    async def rep_earnings(rep_id: str):
        """Get earnings summary for a specific rep."""
        try:
            earnings = await commission_svc.get_rep_earnings(rep_id)
            return earnings
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

    @router.post("/reps/{rep_id}/payout")
    async def trigger_payout(rep_id: str):
        """Manually trigger a payout for a specific rep."""
        result = await payout_svc.process_rep_payout(rep_id)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        return {
            "payout_id": result.payout_id,
            "amount": float(result.amount),
            "commission_count": result.commission_count,
            "stripe_transfer_id": result.stripe_transfer_id,
        }

    @router.post("/process-all")
    async def process_all_payouts():
        """Process payouts for all reps. Called by cron or manually."""
        results = await payout_svc.process_all_payouts()
        return {
            "processed": len(results),
            "successful": sum(1 for r in results if r.success and r.amount > 0),
            "total_paid": sum(float(r.amount) for r in results if r.success),
        }

    @router.get("/history")
    async def payout_history(limit: int = 50, offset: int = 0):
        """Get payout history across all reps."""
        result = db_client.table("payouts").select(
            "*, sales_reps(name, email)"
        ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return {"payouts": result.data or []}

    return router
