"""
Commission Service — Calculate and track rep commissions on inbound payments.

Called by Square/Clover webhook handlers when a payment comes in.
Looks up the assigned sales rep, calculates their commission split, and records it.
No auto-payouts — admin pays reps manually and records it via the dashboard.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

logger = logging.getLogger("meridian.payouts.commissions")


@dataclass
class CommissionResult:
    """Result of a commission calculation."""
    commission_id: Optional[str] = None
    rep_id: Optional[str] = None
    rep_name: Optional[str] = None
    gross_amount: Decimal = Decimal("0")
    commission_rate: Decimal = Decimal("0")
    commission_amount: Decimal = Decimal("0")
    success: bool = False
    error: Optional[str] = None


class CommissionService:
    """
    Handles commission calculation and recording.
    
    Hooks into Square/Clover webhook handlers:
        service = CommissionService(supabase_client)
        result = await service.process_payment(
            org_id="uuid-of-merchant",
            gross_amount=Decimal("250.00"),
            source_type="square_payment",
            source_reference="pay_abc123"
        )
    """

    def __init__(self, db_client):
        self.db = db_client

    async def process_payment(
        self,
        org_id: str,
        gross_amount: Decimal,
        source_type: str = "square_payment",
        source_reference: Optional[str] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
    ) -> CommissionResult:
        """
        Process an inbound payment and calculate commission for the assigned rep.
        """
        try:
            commission_id = await self.db.rpc("calculate_commission", {
                "p_org_id": org_id,
                "p_gross_amount": str(gross_amount),
                "p_source_type": source_type,
                "p_source_reference": source_reference,
                "p_period_start": period_start,
                "p_period_end": period_end,
            })

            if not commission_id:
                logger.info(f"No rep assigned for org {org_id}, skipping commission")
                return CommissionResult(
                    success=True,
                    error="No active rep assignment for this organization"
                )

        except Exception as e:
            logger.error(f"Commission processing failed for org {org_id}: {e}")
            return CommissionResult(success=False, error=str(e))

        # The RPC returned an id — the commission IS recorded. Anything that
        # fails past this point is enrichment-only and must not report failure.
        result = CommissionResult(
            commission_id=commission_id,
            gross_amount=gross_amount,
            success=True,
        )

        try:
            # Fetch the commission details
            rows = await self.db.select(
                "commissions",
                columns="*, sales_reps(name, email, commission_rate)",
                filters={"id": f"eq.{commission_id}"},
                limit=1,
            )

            data = rows[0] if rows else None
            if data:
                result.rep_id = data["rep_id"]
                result.rep_name = (data.get("sales_reps") or {}).get("name")
                result.commission_rate = Decimal(str(data["commission_rate"]))
                result.commission_amount = Decimal(str(data["commission_amount"]))
                logger.info(
                    f"Commission recorded: ${data['commission_amount']} for rep "
                    f"{result.rep_name} on ${gross_amount} from org {org_id}"
                )
        except Exception as e:
            logger.warning(
                f"Commission {commission_id} recorded for org {org_id}, "
                f"but enrichment lookup failed: {e}"
            )

        return result

    async def get_rep_earnings(self, rep_id: str) -> dict:
        """Get earnings summary for a rep."""
        reps = await self.db.select(
            "sales_reps",
            columns="id, name, email, commission_rate, total_earned, total_paid",
            filters={"id": f"eq.{rep_id}"},
            limit=1,
        )
        rep = reps[0] if reps else None
        if rep is None:
            return {"error": "Rep not found", "rep_id": rep_id}

        pending = await self.db.select(
            "commissions",
            columns="commission_amount",
            filters={
                "rep_id": f"eq.{rep_id}",
                "status": "eq.earned",
                "payout_id": "is.null",
            },
        )

        pending_amount = sum(
            Decimal(str(c["commission_amount"])) for c in pending
        )

        return {
            "rep": rep,
            "total_earned": Decimal(str(rep["total_earned"])),
            "total_paid": Decimal(str(rep["total_paid"])),
            "pending_payout": pending_amount,
        }

    async def record_payout(
        self,
        rep_id: str,
        method: str = "manual",
        notes: Optional[str] = None,
    ) -> Optional[str]:
        """
        Record a manual payout to a rep. Marks all unpaid commissions as paid.
        Returns payout ID or None if nothing to pay.
        """
        payout_id = await self.db.rpc("record_manual_payout", {
            "p_rep_id": rep_id,
            "p_method": method,
            "p_notes": notes,
        })

        payout_id = payout_id if payout_id else None
        if payout_id:
            logger.info(f"Manual payout recorded for rep {rep_id}: {payout_id}")
        return payout_id
