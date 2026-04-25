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
        reps = self.db.table("sales_reps").select(
            "id, name, total_earned, total_paid"
        ).eq("is_active", True).execute()

        summaries = []
        for rep in (reps.data or []):
            pending = self.db.table("commissions").select(
                "id", count="exact"
            ).eq("rep_id", rep["id"]).eq("status", "earned").is_(
                "payout_id", "null"
            ).execute()

            summaries.append(PayoutSummary(
                rep_id=rep["id"],
                rep_name=rep["name"],
                total_earned=Decimal(str(rep["total_earned"])),
                total_paid=Decimal(str(rep["total_paid"])),
                balance_owed=Decimal(str(rep["total_earned"])) - Decimal(str(rep["total_paid"])),
                pending_commissions=pending.count or 0,
            ))

        return summaries

    async def get_payout_history(self, rep_id: Optional[str] = None, limit: int = 50) -> list:
        """Get payout history, optionally filtered by rep."""
        query = self.db.table("payouts").select(
            "*, sales_reps(name, email)"
        ).order("created_at", desc=True).limit(limit)

        if rep_id:
            query = query.eq("rep_id", rep_id)

        result = query.execute()
        return result.data or []
