"""
Billing API routes — Square checkout, invoicing, and subscription management.

Endpoints:
  POST /api/billing/create-checkout  → Create Square payment link for onboarding
  POST /api/billing/create-invoice   → Create custom invoice via Square
  POST /api/billing/cancel           → Cancel a subscription
  POST /api/billing/webhook          → Handle Square payment webhooks
  GET  /api/billing/status/:org_id   → Get subscription status
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ...db import get_db

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
async def create_checkout(req: CheckoutRequest):
    """
    Create a Square Checkout (Payment Link) for a new customer subscription.
    Called by the onboarding wizard's payment step.
    Returns a checkout_url to redirect the customer to.
    """
    try:
        from src.billing.billing_service import BillingService

        db = get_db()
        service = BillingService(db)

        result = await service.create_checkout(
            org_id=req.org_id,
            amount_cents=req.monthly_price_cents,
            customer_email=req.customer_email,
            customer_name=req.customer_name,
            business_name=req.business_name,
            plan=req.plan,
            return_url=req.return_url,
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
        raise HTTPException(
            status_code=501,
            detail="Billing service not yet configured. Set SQUARE_ACCESS_TOKEN and SQUARE_LOCATION_ID."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Checkout creation failed")
        raise HTTPException(status_code=500, detail="Checkout creation failed")


@router.post("/create-invoice")
async def create_invoice(req: InvoiceRequest):
    """
    Create a Square Invoice for custom amounts or manual billing.
    Used for non-standard pricing or when the SR sets a custom amount.
    """
    try:
        from src.billing.billing_service import BillingService

        db = get_db()
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
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Invoice creation failed")
        raise HTTPException(status_code=500, detail="Invoice creation failed")


@router.post("/cancel")
async def cancel_subscription(req: CancelRequest):
    """Cancel a subscription. Stops future auto-renewals."""
    try:
        from src.billing.billing_service import BillingService

        db = get_db()
        service = BillingService(db)

        success = await service.cancel_subscription(req.org_id, req.reason)

        if success:
            return {"status": "cancelled", "org_id": req.org_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel subscription")

    except ImportError:
        raise HTTPException(status_code=501, detail="Billing service not yet configured.")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Cancellation failed")
        raise HTTPException(status_code=500, detail="Cancellation failed")


@router.get("/status/{org_id}")
async def get_billing_status(org_id: str):
    """Get current subscription/billing status for an organization."""
    try:
        db = get_db()

        result = db.table("subscriptions").select("*").eq("org_id", org_id).single().execute()

        if result.data:
            sub = result.data
            return {
                "status": sub.get("status"),
                "tier": sub.get("tier"),
                "monthly_price_cents": sub.get("monthly_price_cents"),
                "current_period_start": sub.get("current_period_start"),
                "current_period_end": sub.get("current_period_end"),
                "auto_renew": sub.get("metadata", {}).get("auto_renew", True),
                "canceled_at": sub.get("canceled_at"),
            }
        else:
            return {"status": "none", "tier": None}

    except RuntimeError:
        return {"status": "unavailable", "tier": None}
    except Exception as e:
        logger.exception(f"Status check failed for org {org_id}")
        raise HTTPException(status_code=500, detail="Could not retrieve billing status")


@router.post("/process-renewals")
async def process_renewals():
    """
    Manually trigger subscription renewal processing.
    Creates Square invoices for any subscriptions past their period end.
    Normally run by daily Celery beat task.
    """
    try:
        from src.billing.billing_service import BillingService

        db = get_db()
        service = BillingService(db)
        await service.process_renewals()
        return {"status": "ok"}
    except ImportError:
        raise HTTPException(status_code=501, detail="Billing service not configured.")
    except Exception as e:
        logger.exception("Manual renewal processing failed")
        raise HTTPException(status_code=500, detail="Renewal processing failed")


@router.get("/invoice-url/{org_id}")
async def get_invoice_url(org_id: str):
    """
    Get the latest invoice URL for an org — used for in-platform pay buttons.
    Returns the most recent setup or recurring invoice link.
    """
    try:
        db = get_db()
        result = db.table("subscriptions").select("metadata").eq("org_id", org_id).single().execute()

        if not result.data:
            raise HTTPException(404, "No subscription found")

        meta = result.data.get("metadata") or {}

        renewal_url = meta.get("renewal_invoice_url")
        setup_url = meta.get("setup_invoice_url")
        recurring_url = meta.get("recurring_invoice_url")

        invoice_url = renewal_url or recurring_url or setup_url

        if not invoice_url:
            raise HTTPException(404, "No invoice URL available")

        return {
            "invoice_url": invoice_url,
            "org_id": org_id,
            "type": "renewal" if renewal_url else ("recurring" if recurring_url else "setup"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Invoice URL lookup failed for {org_id}")
        raise HTTPException(500, "Could not retrieve invoice URL")


@router.post("/check-trials")
async def check_expiring_trials():
    """
    Check for trials expiring within the next 3 days and send reminder emails.
    Called by a daily cron job or admin trigger.
    """
    try:
        db = get_db()
        now = datetime.now(timezone.utc)

        for days_out in (3, 1):
            target = now + timedelta(days=days_out)
            target_date = target.strftime("%Y-%m-%d")

            result = db.table("subscriptions").select(
                "*, organizations(name, email, contact_email, owner_name)"
            ).eq("status", "trialing").gte(
                "current_period_end", f"{target_date}T00:00:00Z"
            ).lte(
                "current_period_end", f"{target_date}T23:59:59Z"
            ).execute()

            for sub in (result.data or []):
                org = sub.get("organizations") or {}
                email = org.get("email") or org.get("contact_email")
                if not email:
                    continue
                try:
                    from ...email.send import send_trial_expiring
                    name = (org.get("owner_name") or org.get("name") or "").split()[0] or "there"
                    await send_trial_expiring(
                        to=email,
                        first_name=name,
                        days_remaining=days_out,
                        org_id=sub.get("org_id"),
                    )
                    logger.info(f"Sent trial expiring email ({days_out}d) to {email}")
                except Exception as e:
                    logger.warning(f"Trial expiring email failed for {email}: {e}")

        return {"status": "ok"}
    except Exception as e:
        logger.exception("Trial check failed")
        raise HTTPException(status_code=500, detail="Trial check failed")


@router.post("/webhook")
async def handle_billing_webhook(request: Request):
    """
    Handle Square payment webhook events for subscription billing.
    Activated when a customer completes a checkout payment.

    Key events:
    - payment.completed → Activate subscription
    - invoice.payment_made → Record renewal payment
    """
    try:
        body = await request.json()
        event_type = body.get("type", "")
        data = body.get("data", {}).get("object", {})

        logger.info(f"Billing webhook: {event_type}")

        db = get_db()

        if event_type == "payment.completed":
            payment = data.get("payment", {})
            order_id = payment.get("order_id", "")

            if order_id:
                subs = db.table("subscriptions").select("*, organizations(name, email, contact_email)").execute()
                for sub in (subs.data or []):
                    meta = sub.get("metadata") or {}
                    if meta.get("square_order_id") == order_id:
                        db.table("subscriptions").update({
                            "status": "active",
                            "metadata": {
                                **meta,
                                "payment_completed_at": datetime.now(timezone.utc).isoformat(),
                                "square_payment_id": payment.get("id"),
                            },
                        }).eq("id", sub["id"]).execute()

                        logger.info(f"Activated subscription for order {order_id}")

                        org = sub.get("organizations") or {}
                        recipient = org.get("email") or org.get("contact_email")
                        if recipient:
                            try:
                                from ...email.send import send_payment_receipt
                                amount_cents = payment.get("amount_money", {}).get("amount", sub.get("monthly_price_cents", 0))
                                await send_payment_receipt(
                                    to=recipient,
                                    business_name=org.get("name", "Your Business"),
                                    plan_name=sub.get("tier", "Standard").title(),
                                    amount=f"${amount_cents / 100:.2f}",
                                    period="Monthly",
                                    invoice_url=payment.get("receipt_url", ""),
                                    org_id=sub.get("org_id"),
                                )
                            except Exception as e:
                                logger.warning(f"Payment receipt email failed: {e}")
                        break

        elif event_type == "invoice.payment_made":
            invoice = data.get("invoice", {})
            invoice_id = invoice.get("id", "")

            if invoice_id:
                subs = db.table("subscriptions").select("*").execute()
                for sub in (subs.data or []):
                    meta = sub.get("metadata") or {}
                    if meta.get("renewal_invoice_id") == invoice_id:
                        if sub.get("status") == "past_due":
                            db.table("subscriptions").update({
                                "status": "active",
                            }).eq("id", sub["id"]).execute()
                            logger.info(f"Reactivated subscription from invoice {invoice_id}")
                        break

        return {"status": "ok"}

    except RuntimeError:
        logger.error("Database not available for billing webhook")
        return {"status": "error", "detail": "Database unavailable"}
    except Exception as e:
        logger.exception("Billing webhook processing failed")
        return {"status": "error", "detail": "Webhook processing failed"}
