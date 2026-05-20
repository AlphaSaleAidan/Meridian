"""
Payout Service — Track and manage manual rep payouts.

No auto-disbursement — admin pays reps manually (Venmo, Zelle, bank transfer, etc.)
and records the payout here. The system tracks what's owed and what's been paid.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

logger = logging.getLogger("meridian.payouts.tracking")


@dataclass
class PayoutSummary:
    """Summary of payout status for a rep."""
    rep_id: str
    rep_name: str
    total_earned: Decimal
    total_paid: Decimal
    balance_owed: Decimal
    pending_commissions: int


class PayoutTracker:
    """
    Tracks commission balances and payout history.
    
    Usage:
        tracker = PayoutTracker(supabase_client)
        summary = await tracker.get_all_balances()
    """

    def __init__(self, db_client):
        self.db = db_client

    async def get_all_balances(self) -> list[PayoutSummary]:
        """Get payout balances for all active reps."""
        reps = await self.db.select(
            "sales_reps",
            columns="id, name, total_earned, total_paid",
            filters={"is_active": "eq.true"},
        )

        summaries = []
        for rep in reps:
            pending_count = await self.db.count(
                "commissions",
                filters={
                    "rep_id": f"eq.{rep['id']}",
                    "status": "eq.earned",
                    "payout_id": "is.null",
                },
            )

            summaries.append(PayoutSummary(
                rep_id=rep["id"],
                rep_name=rep["name"],
                total_earned=Decimal(str(rep["total_earned"])),
                total_paid=Decimal(str(rep["total_paid"])),
                balance_owed=Decimal(str(rep["total_earned"])) - Decimal(str(rep["total_paid"])),
                pending_commissions=pending_count,
            ))

        return summaries

    async def get_payout_history(self, rep_id: Optional[str] = None, limit: int = 50) -> list:
        """Get payout history, optionally filtered by rep."""
        filters = {}
        if rep_id:
            filters["rep_id"] = f"eq.{rep_id}"

        return await self.db.select(
            "payouts",
            columns="*, sales_reps(name, email)",
            filters=filters,
            order="created_at.desc",
            limit=limit,
        )
