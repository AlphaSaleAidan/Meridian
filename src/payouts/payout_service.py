"""
Payout Service — Auto-disburse commissions to reps via Stripe Connect.

Batches unpaid commissions per rep, creates a Stripe Transfer to their
Connected Account, and updates payout records.

Requires:
    - STRIPE_SECRET_KEY env var (platform account)
    - Each rep must have stripe_connect_account_id set
"""

import logging
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import httpx

logger = logging.getLogger("meridian.payouts.disbursement")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_API_BASE = "https://api.stripe.com/v1"


@dataclass
class PayoutResult:
    """Result of a payout attempt."""
    payout_id: Optional[str] = None
    stripe_transfer_id: Optional[str] = None
    amount: Decimal = Decimal("0")
    commission_count: int = 0
    success: bool = False
    error: Optional[str] = None


class PayoutService:
    """
    Handles automated payout disbursement to sales reps.
    
    Flow:
    1. Batch all unpaid 'earned' commissions for a rep
    2. Create a Stripe Transfer to rep's Connected Account
    3. Mark commissions as 'paid' and update payout record
    
    Usage:
        service = PayoutService(supabase_client)
        result = await service.process_rep_payout(rep_id="uuid")
    """

    def __init__(self, db_client):
        self.db = db_client

    async def process_rep_payout(self, rep_id: str) -> PayoutResult:
        """
        Process all pending commissions for a rep into a single payout.
        """
        try:
            # 1. Get rep's Stripe Connect account
            rep = self.db.table("sales_reps").select(
                "id, name, stripe_connect_account_id, stripe_connect_onboarded"
            ).eq("id", rep_id).single().execute()

            rep_data = rep.data
            if not rep_data.get("stripe_connect_account_id"):
                return PayoutResult(
                    success=False,
                    error=f"Rep {rep_data['name']} has no Stripe Connect account linked"
                )
            
            if not rep_data.get("stripe_connect_onboarded"):
                return PayoutResult(
                    success=False,
                    error=f"Rep {rep_data['name']} hasn't completed Stripe Connect onboarding"
                )

            # 2. Create payout batch in DB
            batch_result = self.db.rpc("create_payout_batch", {
                "p_rep_id": rep_id
            }).execute()

            payout_id = batch_result.data
            if not payout_id:
                return PayoutResult(success=True, error="No pending commissions to pay out")

            # 3. Get payout details
            payout = self.db.table("payouts").select("*").eq(
                "id", payout_id
            ).single().execute()
            payout_data = payout.data

            amount_cents = int(Decimal(str(payout_data["amount"])) * 100)

            # 4. Create Stripe Transfer to Connected Account
            transfer = await self._create_stripe_transfer(
                amount_cents=amount_cents,
                connected_account_id=rep_data["stripe_connect_account_id"],
                payout_id=payout_id,
                rep_name=rep_data["name"],
            )

            if not transfer.get("id"):
                # Transfer failed — update payout status
                self.db.table("payouts").update({
                    "status": "failed",
                    "failure_reason": transfer.get("error", "Unknown Stripe error"),
                    "failed_at": "now()",
                }).eq("id", payout_id).execute()

                return PayoutResult(
                    payout_id=payout_id,
                    success=False,
                    error=f"Stripe Transfer failed: {transfer.get('error')}"
                )

            # 5. Update payout + commissions status
            self.db.table("payouts").update({
                "status": "completed",
                "stripe_transfer_id": transfer["id"],
                "initiated_at": "now()",
                "completed_at": "now()",
            }).eq("id", payout_id).execute()

            self.db.table("commissions").update({
                "status": "paid",
            }).eq("payout_id", payout_id).execute()

            # Update rep's total_paid
            self.db.table("sales_reps").update({
                "total_paid": self.db.raw(
                    f"total_paid + {payout_data['amount']}"
                ),
            }).eq("id", rep_id).execute()

            logger.info(
                f"Payout completed: ${payout_data['amount']} to {rep_data['name']} "
                f"(transfer: {transfer['id']})"
            )

            return PayoutResult(
                payout_id=payout_id,
                stripe_transfer_id=transfer["id"],
                amount=Decimal(str(payout_data["amount"])),
                commission_count=payout_data["commission_count"],
                success=True,
            )

        except Exception as e:
            logger.error(f"Payout processing failed for rep {rep_id}: {e}")
            return PayoutResult(success=False, error=str(e))

    async def _create_stripe_transfer(
        self,
        amount_cents: int,
        connected_account_id: str,
        payout_id: str,
        rep_name: str,
    ) -> dict:
        """Create a Stripe Transfer to a Connected Account."""
        if not STRIPE_SECRET_KEY:
            return {"error": "STRIPE_SECRET_KEY not configured"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{STRIPE_API_BASE}/transfers",
                    auth=(STRIPE_SECRET_KEY, ""),
                    data={
                        "amount": amount_cents,
                        "currency": "usd",
                        "destination": connected_account_id,
                        "transfer_group": f"payout_{payout_id}",
                        "description": f"Meridian commission payout for {rep_name}",
                        "metadata[payout_id]": payout_id,
                        "metadata[rep_name]": rep_name,
                    },
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    error_data = response.json()
                    return {"error": error_data.get("error", {}).get("message", "Unknown error")}

            except Exception as e:
                return {"error": str(e)}

    async def process_all_payouts(self) -> list[PayoutResult]:
        """Process payouts for all active reps with pending commissions."""
        reps = self.db.table("sales_reps").select("id, name").eq(
            "is_active", True
        ).execute()

        results = []
        for rep in (reps.data or []):
            result = await self.process_rep_payout(rep["id"])
            results.append(result)
            if result.success and result.amount > 0:
                logger.info(f"Paid {rep['name']}: ${result.amount}")

        return results
