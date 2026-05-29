"""Credit balance + ledger API for the dashboard and admin tools."""
import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...credits import (
    COSTS,
    LOW_BALANCE_THRESHOLD,
    STARTER_GRANT,
    InsufficientCredits,
    deduct,
    ensure_starter_grant,
    get_balance,
    grant,
)

logger = logging.getLogger("meridian.credits.api")
router = APIRouter(prefix="/api/credits", tags=["credits"])

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_ANON_KEY", "")
)


class BalanceResponse(BaseModel):
    merchant_id: str
    balance: int
    low_balance_threshold: int
    is_low: bool
    costs: dict[str, dict[str, Any]]


class GrantRequest(BaseModel):
    merchant_id: str
    amount: int = Field(gt=0, le=1_000_000)
    action_type: str = "admin_grant"
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeductRequest(BaseModel):
    merchant_id: str
    amount: int = Field(gt=0, le=1_000_000)
    action_type: str
    action_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _serialize_costs() -> dict[str, dict[str, Any]]:
    """Public cost catalog — frontend renders this to show per-action prices."""
    return {
        action: {
            "credits": c.credits,
            "description": c.description,
        }
        for action, c in COSTS.items()
    }


@router.get("/balance/{merchant_id}", response_model=BalanceResponse)
async def get_credit_balance(merchant_id: str):
    """Current balance + the price sheet. Single fetch for the dashboard header."""
    balance = await get_balance(merchant_id)
    return BalanceResponse(
        merchant_id=merchant_id,
        balance=balance,
        low_balance_threshold=LOW_BALANCE_THRESHOLD,
        is_low=balance < LOW_BALANCE_THRESHOLD,
        costs=_serialize_costs(),
    )


@router.get("/ledger/{merchant_id}")
async def get_credit_ledger(
    merchant_id: str,
    limit: int = Query(50, ge=1, le=500),
):
    """Recent ledger entries for the dashboard's billing history view."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"entries": []}

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    select = "id,delta,action_type,action_id,balance_after,metadata,created_at"
    url = (
        f"{SUPABASE_URL}/rest/v1/credit_ledger"
        f"?merchant_id=eq.{merchant_id}&select={select}"
        f"&order=created_at.desc&limit={limit}"
    )
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(url, headers=headers)
            if res.status_code != 200:
                logger.warning("ledger fetch %d: %s", res.status_code, res.text[:120])
                return {"entries": []}
            return {"entries": res.json() or []}
    except Exception as e:
        logger.warning("ledger fetch failed for %s: %s", merchant_id, e)
        return {"entries": []}


@router.post("/grant", status_code=200)
async def post_credit_grant(req: GrantRequest):
    """Admin / Stripe-webhook entry point for adding credits."""
    new_balance = await grant(
        merchant_id=req.merchant_id,
        amount=req.amount,
        action_type=req.action_type,
        metadata=req.metadata,
    )
    return {"merchant_id": req.merchant_id, "balance": new_balance, "granted": req.amount}


@router.post("/deduct", status_code=200)
async def post_credit_deduct(req: DeductRequest):
    """Server-side deduction for content / non-phone actions that meter from
    the frontend. Phone and SMS deduct inline at the route level; this is
    the entry point for everything else (content generation, image regen,
    etc) once they start checking balance."""
    try:
        new_balance = await deduct(
            merchant_id=req.merchant_id,
            amount=req.amount,
            action_type=req.action_type,
            action_id=req.action_id,
            metadata=req.metadata,
        )
    except InsufficientCredits as exc:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credits",
                "balance": exc.available,
                "requested": exc.requested,
                "message": f"Needs {exc.requested - exc.available} more credits",
            },
        )
    return {"merchant_id": req.merchant_id, "balance": new_balance, "deducted": req.amount}


@router.post("/starter-grant/{merchant_id}", status_code=200)
async def post_starter_grant(merchant_id: str):
    """Grant the free signup credits if this merchant has never been credited.

    Safe to call repeatedly — the ledger check inside ensure_starter_grant
    short-circuits if a starter_grant entry already exists.
    """
    new_balance = await ensure_starter_grant(merchant_id)
    return {
        "merchant_id": merchant_id,
        "balance": new_balance,
        "starter_grant": STARTER_GRANT,
    }
