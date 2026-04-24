"""
Commission Service — Calculate and track rep commissions on inbound payments.

Called by webhook handlers when a subscription payment or POS transaction comes in.
Looks up the assigned sales rep, calculates their commission split, and records it.
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
    
    Usage:
        service = CommissionService(supabase_client)
        result = await service.process_payment(
            org_id="uuid-of-merchant",
            gross_amount=Decimal("250.00"),
            source_type="subscription",
            source_reference="inv_abc123"
        )
    """

    def __init__(self, db_client):
        """
        Args:
            db_client: Supabase client with access to commissions tables.
        """
        self.db = db_client

    async def process_payment(
        self,
        org_id: str,
        gross_amount: Decimal,
        source_type: str = "subscription",
        source_reference: Optional[str] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
    ) -> CommissionResult:
        """
        Process an inbound payment and calculate commission for the assigned rep.
        
        1. Look up active rep assignment for this org
        2. Calculate commission based on rep's rate
        3. Record commission in DB
        4. Update rep's total_earned
        
        Returns CommissionResult with details.
        """
        try:
            # Call the DB function that handles everything atomically
            result = self.db.rpc("calculate_commission", {
                "p_org_id": org_id,
                "p_gross_amount": float(gross_amount),
                "p_source_type": source_type,
                "p_source_reference": source_reference,
                "p_period_start": period_start,
                "p_period_end": period_end,
            }).execute()

            commission_id = result.data if result.data else None

            if not commission_id:
                logger.info(f"No rep assigned for org {org_id}, skipping commission")
                return CommissionResult(
                    success=True,
                    error="No active rep assignment for this organization"
                )

            # Fetch the commission details
            commission = self.db.table("commissions").select(
                "*, sales_reps(name, email, commission_rate)"
            ).eq("id", commission_id).single().execute()

            data = commission.data
            logger.info(
                f"Commission recorded: {data['commission_amount']} for rep "
                f"{data['sales_reps']['name']} on {gross_amount} from org {org_id}"
            )

            return CommissionResult(
                commission_id=commission_id,
                rep_id=data["rep_id"],
                rep_name=data["sales_reps"]["name"],
                gross_amount=gross_amount,
                commission_rate=Decimal(str(data["commission_rate"])),
                commission_amount=Decimal(str(data["commission_amount"])),
                success=True,
            )

        except Exception as e:
            logger.error(f"Commission processing failed for org {org_id}: {e}")
            return CommissionResult(success=False, error=str(e))

    async def get_rep_earnings(self, rep_id: str) -> dict:
        """Get earnings summary for a rep."""
        result = self.db.table("sales_reps").select(
            "id, name, email, commission_rate, total_earned, total_paid"
        ).eq("id", rep_id).single().execute()

        rep = result.data
        pending = self.db.table("commissions").select(
            "commission_amount"
        ).eq("rep_id", rep_id).eq("status", "earned").is_("payout_id", "null").execute()

        pending_amount = sum(
            Decimal(str(c["commission_amount"])) for c in (pending.data or [])
        )

        return {
            "rep": rep,
            "total_earned": Decimal(str(rep["total_earned"])),
            "total_paid": Decimal(str(rep["total_paid"])),
            "pending_payout": pending_amount,
            "balance": Decimal(str(rep["total_earned"])) - Decimal(str(rep["total_paid"])),
        }
