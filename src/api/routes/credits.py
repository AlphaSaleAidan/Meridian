"""Credit balance + ledger + purchase API.

- GET  /api/credits/balance/{merchant_id}        — dashboard widget
- GET  /api/credits/ledger/{merchant_id}         — billing history
- GET  /api/credits/packs                        — public price sheet
- POST /api/credits/grant                        — admin manual add
- POST /api/credits/deduct                       — server-side debit (content gen, etc)
- POST /api/credits/purchase                     — start a Square invoice purchase
- POST /api/credits/webhook/square               — Square webhook (invoice.payment_made → grant)
- POST /api/credits/starter-grant/{merchant_id}  — signup hook (idempotent)
"""
import base64
import hashlib
import hmac
import json as _json
import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, EmailStr, Field

from ..auth import require_admin_jwt, require_jwt, require_org_member
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
from ...credits.purchase import PACKS, create_purchase_invoice, handle_invoice_payment

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
async def get_credit_balance(merchant_id: str, user: dict = Depends(require_jwt)):
    """Current balance + the price sheet. Single fetch for the dashboard header."""
    await require_org_member(user, merchant_id)
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


@router.post("/grant", status_code=200, dependencies=[Depends(require_admin_jwt)])
async def post_credit_grant(req: GrantRequest):
    """Admin entry point for manually adding credits. Webhook-driven grants
    go through handle_invoice_payment, not this route."""
    new_balance = await grant(
        merchant_id=req.merchant_id,
        amount=req.amount,
        action_type=req.action_type,
        metadata=req.metadata,
    )
    return {"merchant_id": req.merchant_id, "balance": new_balance, "granted": req.amount}


@router.post("/deduct", status_code=200, dependencies=[Depends(require_admin_jwt)])
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


# ── Purchase via Square custom invoices ──


class PurchaseRequest(BaseModel):
    merchant_id: str
    pack_id: str
    customer_email: EmailStr
    customer_name: str = ""
    currency: str = Field(default="USD", pattern="^(USD|CAD)$")


@router.get("/packs")
async def get_packs():
    """Public credit-pack catalog. Frontend reads this to render the upsell modal."""
    return {
        "packs": [
            {
                "pack_id": p.pack_id,
                "label": p.label,
                "credits": p.credits,
                "price_usd": p.price_cents_usd / 100,
                "price_cad": p.price_cents_cad / 100,
                "price_per_credit_usd": p.price_cents_usd / 100 / p.credits,
            }
            for p in PACKS.values()
        ]
    }


@router.post("/purchase", status_code=200)
async def post_purchase(req: PurchaseRequest, user: dict = Depends(require_jwt)):
    """Start a credit-pack purchase. Returns the Square hosted invoice URL.

    The frontend should redirect the user to invoice_url; on payment the
    Square webhook will grant credits and the dashboard will reflect the
    new balance on the customer's next poll.
    """
    await require_org_member(user, req.merchant_id)
    result = await create_purchase_invoice(
        merchant_id=req.merchant_id,
        pack_id=req.pack_id,
        customer_email=req.customer_email,
        customer_name=req.customer_name,
        currency=req.currency,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail={"error": result.error})
    return {
        "purchase_id": result.purchase_id,
        "invoice_url": result.invoice_url,
        "invoice_id": result.invoice_id,
        "credit_amount": result.credit_amount,
        "price_cents": result.price_cents,
        "currency": result.currency,
    }


def _verify_square_signature(request: Request, raw_body: bytes) -> bool:
    """Mirror of billing webhook signature check.

    Uses CREDITS_SQUARE_WEBHOOK_SIGNATURE_KEY if set so the credit webhook
    can be a separate Square webhook subscription with its own signing key.
    Falls back to the shared SQUARE_WEBHOOK_SIGNATURE_KEY for ops simplicity.
    """
    sig_key = (
        os.environ.get("CREDITS_SQUARE_WEBHOOK_SIGNATURE_KEY")
        or os.environ.get("SQUARE_WEBHOOK_SIGNATURE_KEY", "")
    )
    if not sig_key:
        logger.warning("Square webhook signature key not configured — rejecting")
        return False
    signature = request.headers.get("x-square-hmacsha256-signature", "")
    if not signature:
        return False
    # Exact URL Square signs against (str(request.url) mismatches behind
    # the Railway proxy — see billing webhook).
    from ...config import app as _app_config
    notification_url = _app_config.credits_webhook_url
    combined = notification_url.encode("utf-8") + raw_body
    digest = hmac.new(
        key=sig_key.encode("utf-8"),
        msg=combined,
        digestmod=hashlib.sha256,
    ).digest()
    expected_b64 = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected_b64, signature)


@router.post("/webhook/square")
async def square_credit_webhook(request: Request):
    """Square posts here when a credit-pack invoice is paid.

    Acks 200 quickly so Square doesn't retry. Filters to invoice.payment_made
    events; ignores anything else (subscription events get handled by the
    existing /api/billing/webhook on its own).
    """
    raw_body = await request.body()
    if not _verify_square_signature(request, raw_body):
        return Response(status_code=403)

    try:
        body = _json.loads(raw_body)
    except ValueError:
        return Response(status_code=400)

    event_type = body.get("type", "")
    data = (body.get("data") or {}).get("object", {})

    if event_type not in ("invoice.payment_made", "invoice.updated"):
        return {"status": "ignored", "event_type": event_type}

    invoice = data.get("invoice") or {}
    invoice_id = invoice.get("id", "")
    if not invoice_id:
        return {"status": "ignored", "reason": "no invoice id"}

    # invoice.updated fires for non-payment changes too. Only proceed if
    # the invoice is actually paid.
    if event_type == "invoice.updated" and invoice.get("status") != "PAID":
        return {"status": "ignored", "reason": "invoice not paid yet"}

    payment_requests = invoice.get("payment_requests") or []
    payment_id = ""
    for pr in payment_requests:
        comp = pr.get("computed_amount_money") or pr.get("total_completed_amount_money")
        if comp:
            payment_id = pr.get("uid", "") or payment_id

    granted = await handle_invoice_payment(invoice_id, square_payment_id=payment_id)
    return {"status": "ok", "granted": granted, "invoice_id": invoice_id}
