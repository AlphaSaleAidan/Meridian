"""
Billing API routes — Square checkout, invoicing, and subscription management.

Endpoints:
  POST /api/billing/create-checkout  → Create Square payment link for onboarding/proposals
  POST /api/billing/create-invoice   → Create custom invoice via Square
  POST /api/billing/cancel           → Cancel a subscription
  POST /api/billing/webhook          → Handle Square payment webhooks
  GET  /api/billing/status/:org_id   → Get subscription status
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger("meridian.billing.routes")

router = APIRouter(prefix="/api/billing", tags=["billing"])


# ── Request/Response Models ──

class CheckoutRequest(BaseModel):
    org_id: str
    plan: str = "standard"
    monthly_price_cents: int = 25000  # $250.00 default
    customer_email: str
    customer_name: str
    business_name: str
    return_url: str = ""
    setup_fee_cents: int = 0          # One-time setup fee (rep keeps 100%)
    first_month_free: bool = False    # Apply 100% discount to first month
    rep_id: str = ""                  # Sales rep ID for commission tracking
    rep_name: str = ""                # Sales rep name


class InvoiceRequest(BaseModel):
    org_id: str
    amount_cents: int
    customer_email: str
    description: str = "Meridian Analytics Subscription"
    due_days: int = 3


class CancelRequest(BaseModel):
    org_id: str
    reason: str = ""


# ── Route handlers ──

@router.post("/create-checkout")
async def create_checkout(req: CheckoutRequest, request: Request):
    """
    Create a Square Checkout (Payment Link) for a new customer subscription.
    Called by the proposal wizard's payment step.

    Supports:
    - Plan tier selection (standard/premium/command)
    - Custom setup fee as a one-time line item
    - First month free via Square discount
    - Sales rep tracking for commissions

    Returns a checkout_url to redirect the customer to.
    """
    try:
        from src.billing.billing_service import BillingService

        db = request.app.state.db
        service = BillingService(db)

        result = await service.create_checkout(
            org_id=req.org_id,
            amount_cents=req.monthly_price_cents,
            customer_email=req.customer_email,
            customer_name=req.customer_name,
            business_name=req.business_name,
            plan=req.plan,
            return_url=req.return_url,
            setup_fee_cents=req.setup_fee_cents,
            first_month_free=req.first_month_free,
            rep_id=req.rep_id,
            rep_name=req.rep_name,
        )

        if result.success:
            return {
                "checkout_url": result.checkout_url,
                "checkout_id": result.checkout_id,
                "order_id": result.order_id,
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)

    except ImportError:
        # Billing service not yet deployed — return a helpful error
        raise HTTPException(
            status_code=501,
            detail="Billing service not yet configured. Set SQUARE_ACCESS_TOKEN and SQUARE_LOCATION_ID."
        )
    except Exception as e:
        logger.exception("Checkout creation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-invoice")
async def create_invoice(req: InvoiceRequest, request: Request):
    """
    Create a Square Invoice for custom amounts or manual billing.
    Used for non-standard pricing or when the SR sets a custom amount.
    """
    try:
        from src.billing.billing_service import BillingService

        db = request.app.state.db
        service = BillingService(db)

        result = await service.create_invoice(
            org_id=req.org_id,
            amount_cents=req.amount_cents,
            customer_email=req.customer_email,
            description=req.description,
            due_days=req.due_days,
        )

        if result.success:
            return {
                "invoice_id": result.invoice_id,
                "invoice_url": result.invoice_url,
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)

    except ImportError:
        raise HTTPException(status_code=501, detail="Billing service not yet configured.")
    except Exception as e:
        logger.exception("Invoice creation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel")
async def cancel_subscription(req: CancelRequest, request: Request):
    """Cancel a subscription. Stops future auto-renewals."""
    try:
        from src.billing.billing_service import BillingService

        db = request.app.state.db
        service = BillingService(db)

        success = await service.cancel_subscription(req.org_id, req.reason)

        if success:
            return {"status": "cancelled", "org_id": req.org_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel subscription")

    except ImportError:
        raise HTTPException(status_code=501, detail="Billing service not yet configured.")
    except Exception as e:
        logger.exception("Cancellation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{org_id}")
async def get_billing_status(org_id: str, request: Request):
    """Get current subscription/billing status for an organization."""
    try:
        db = request.app.state.db

        result = db.table("subscriptions").select("*").eq("org_id", org_id).single().execute()

        if result.data:
            sub = result.data
            metadata = sub.get("metadata") or {}
            return {
                "status": sub.get("status"),
                "tier": sub.get("tier"),
                "monthly_price_cents": sub.get("monthly_price_cents"),
                "current_period_start": sub.get("current_period_start"),
                "current_period_end": sub.get("current_period_end"),
                "auto_renew": metadata.get("auto_renew", True),
                "canceled_at": sub.get("canceled_at"),
                "setup_fee_cents": metadata.get("setup_fee_cents", 0),
                "first_month_free": metadata.get("first_month_free", False),
                "rep_id": metadata.get("rep_id", ""),
                "rep_name": metadata.get("rep_name", ""),
            }
        else:
            return {"status": "none", "tier": None}

    except Exception as e:
        logger.exception(f"Status check failed for org {org_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def handle_billing_webhook(request: Request):
    """
    Handle Square payment webhook events for subscription billing.
    Activated when a customer completes a checkout payment.

    Key events:
    - payment.completed → Activate subscription, record setup fee commission
    - invoice.payment_made → Record renewal payment
    """
    try:
        body = await request.json()
        event_type = body.get("type", "")
        data = body.get("data", {}).get("object", {})

        logger.info(f"Billing webhook: {event_type}")

        if event_type == "payment.completed":
            payment = data.get("payment", {})
            order_id = payment.get("order_id", "")

            if order_id:
                db = request.app.state.db

                # Find subscription by order ID in metadata
                subs = db.table("subscriptions").select("*").execute()
                for sub in (subs.data or []):
                    meta = sub.get("metadata") or {}
                    if meta.get("square_order_id") == order_id:
                        # Activate the subscription
                        updated_meta = {
                            **meta,
                            "payment_completed_at": datetime.utcnow().isoformat(),
                            "square_payment_id": payment.get("id"),
                        }

                        # If first month free, mark trial active
                        if meta.get("first_month_free"):
                            updated_meta["trial_status"] = "active"

                        db.table("subscriptions").update({
                            "status": "active",
                            "metadata": updated_meta,
                        }).eq("id", sub["id"]).execute()

                        # Record setup fee commission if applicable
                        setup_fee = meta.get("setup_fee_cents", 0)
                        rep_id = meta.get("setup_fee_rep_id") or meta.get("rep_id")
                        if setup_fee and rep_id:
                            try:
                                db.table("commissions").insert({
                                    "rep_id": rep_id,
                                    "org_id": sub["org_id"],
                                    "type": "setup_fee",
                                    "amount_cents": setup_fee,
                                    "commission_rate": 1.0,  # 100% to rep
                                    "commission_cents": setup_fee,
                                    "status": "earned",
                                    "notes": f"Setup fee for {sub.get('tier', 'standard')} plan",
                                }).execute()
                                logger.info(f"Recorded setup fee commission: ${setup_fee/100:.2f} for rep {rep_id}")
                            except Exception as e:
                                logger.warning(f"Failed to record setup fee commission: {e}")

                        logger.info(f"Activated subscription for order {order_id}")
                        break

        elif event_type == "invoice.payment_made":
            invoice = data.get("invoice", {})
            invoice_id = invoice.get("id", "")

            if invoice_id:
                db = request.app.state.db

                # Find subscription by invoice ID in metadata
                subs = db.table("subscriptions").select("*").execute()
                for sub in (subs.data or []):
                    meta = sub.get("metadata") or {}
                    if meta.get("renewal_invoice_id") == invoice_id:
                        # Update status back to active if it was past_due
                        if sub.get("status") == "past_due":
                            db.table("subscriptions").update({
                                "status": "active",
                            }).eq("id", sub["id"]).execute()
                            logger.info(f"Reactivated subscription from invoice {invoice_id}")
                        break

        return {"status": "ok"}

    except Exception as e:
        logger.exception("Billing webhook processing failed")
        return {"status": "error", "detail": str(e)}
