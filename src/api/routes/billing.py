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
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from ...db import get_db

logger = logging.getLogger("meridian.billing.routes")

router = APIRouter(prefix="/api/billing", tags=["billing"])

MAX_AMOUNT_CENTS = 10_000_00  # $10,000 safety cap


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

    @field_validator("monthly_price_cents")
    @classmethod
    def validate_monthly_price(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("monthly_price_cents must be positive")
        if v > MAX_AMOUNT_CENTS:
            raise ValueError(f"monthly_price_cents exceeds maximum ({MAX_AMOUNT_CENTS})")
        return v

    @field_validator("setup_fee_cents")
    @classmethod
    def validate_setup_fee(cls, v: int) -> int:
        if v < 0:
            raise ValueError("setup_fee_cents cannot be negative")
        if v > MAX_AMOUNT_CENTS:
            raise ValueError(f"setup_fee_cents exceeds maximum ({MAX_AMOUNT_CENTS})")
        return v


class InvoiceRequest(BaseModel):
    org_id: str
    amount_cents: int
    customer_email: str
    description: str = "Meridian Analytics Subscription"
    due_days: int = 3

    @field_validator("amount_cents")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount_cents must be positive")
        if v > MAX_AMOUNT_CENTS:
            raise ValueError(f"amount_cents exceeds maximum ({MAX_AMOUNT_CENTS})")
        return v


class CancelRequest(BaseModel):
    org_id: str
    reason: str = ""


class UpdatePaymentMethodRequest(BaseModel):
    org_id: str
    customer_email: str
    customer_name: str
    business_name: str


class PaymentNotifyRequest(BaseModel):
    org_id: str
    customer_email: str
    contact_name: str
    business_name: str
    rep_name: str = ""
    rep_email: str = ""


# ── Route handlers ──

@router.post("/create-checkout")
async def create_checkout(req: CheckoutRequest):
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

    except RuntimeError:
        return {"status": "unavailable", "tier": None}
    except Exception as e:
        logger.exception(f"Status check failed for org {org_id}")
        raise HTTPException(status_code=500, detail="Could not retrieve billing status")


@router.post("/update-payment-method")
async def update_payment_method(req: UpdatePaymentMethodRequest):
    """
    Generate a new Square invoice so the customer can update their card on file.
    Creates a fresh invoice at the current subscription price with card storage enabled.
    Returns the invoice URL to send to the customer.
    """
    try:
        from src.billing.billing_service import BillingService

        db = get_db()

        result = db.table("subscriptions").select("*").eq("org_id", req.org_id).single().execute()
        amount_cents = 25000
        plan = "standard"
        if result.data:
            amount_cents = result.data.get("monthly_price_cents", 25000)
            plan = result.data.get("tier", "standard")

        service = BillingService(db)
        inv_result = await service.create_invoice(
            org_id=req.org_id,
            amount_cents=amount_cents,
            customer_email=req.customer_email,
            description=f"Meridian Analytics - {plan.title()} Plan (Payment Update)",
            due_days=7,
            store_card=True,
        )

        if inv_result.success:
            meta = (result.data or {}).get("metadata", {})
            db.table("subscriptions").update({
                "metadata": {
                    **meta,
                    "update_invoice_id": inv_result.invoice_id,
                    "update_invoice_url": inv_result.invoice_url,
                    "update_requested_at": datetime.now(timezone.utc).isoformat(),
                },
            }).eq("org_id", req.org_id).execute()

            return {
                "ok": True,
                "invoice_url": inv_result.invoice_url,
                "invoice_id": inv_result.invoice_id,
                "amount_cents": amount_cents,
            }
        else:
            raise HTTPException(400, inv_result.error or "Could not create payment update link")

    except ImportError:
        raise HTTPException(501, "Billing service not configured")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Payment method update failed")
        raise HTTPException(500, "Could not create payment update link")


@router.post("/notify-payment-failed")
async def notify_payment_failed(req: PaymentNotifyRequest):
    """
    Send a 'payment failed' email to the customer with a link to update their card.
    Auto-generates a new invoice link if one doesn't already exist.
    """
    try:
        db = get_db()
        sub = db.table("subscriptions").select("*").eq("org_id", req.org_id).single().execute()

        meta = (sub.data or {}).get("metadata", {}) if sub.data else {}
        update_url = meta.get("update_invoice_url") or meta.get("renewal_invoice_url")
        amount_cents = (sub.data or {}).get("monthly_price_cents", 25000) if sub.data else 25000

        if not update_url:
            try:
                from src.billing.billing_service import BillingService
                service = BillingService(db)
                inv = await service.create_invoice(
                    org_id=req.org_id,
                    amount_cents=amount_cents,
                    customer_email=req.customer_email,
                    description="Meridian Analytics - Payment Update",
                    due_days=7,
                    store_card=True,
                )
                if inv.success:
                    update_url = inv.invoice_url
            except ImportError:
                pass

        if not update_url:
            update_url = f"https://meridian.tips/canada/login"

        from ...email.send import send_payment_failed
        amount_display = f"${amount_cents / 100:.2f}"
        result = await send_payment_failed(
            to=req.customer_email,
            business_name=req.business_name,
            contact_name=req.contact_name,
            amount=amount_display,
            update_url=update_url,
            rep_name=req.rep_name,
            org_id=req.org_id,
        )

        email_sent = result.get("status") == "sent" or result.get("id") is not None
        return {"ok": True, "email_sent": email_sent, "update_url": update_url}

    except RuntimeError:
        raise HTTPException(503, "Database not available")
    except Exception as e:
        logger.exception("Payment failed notification error")
        raise HTTPException(500, "Could not send payment notification")


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

    Key events:
    - payment.completed → Activate subscription, record setup fee commission
    - payment.updated → Handle Square renamed event (same as completed if status=COMPLETED)
    - invoice.payment_made → Record renewal payment
    """
    try:
        body = await request.json()
        event_type = body.get("type", "")
        data = body.get("data", {}).get("object", {})

        logger.info(f"Billing webhook: {event_type}")

        db = get_db()

        if event_type in ("payment.completed", "payment.updated"):
            payment = data.get("payment", {})

            # For payment.updated, only process if status is COMPLETED
            if event_type == "payment.updated" and payment.get("status") != "COMPLETED":
                return {"status": "ignored", "reason": "payment not completed yet"}

            order_id = payment.get("order_id", "")

            if order_id:
                subs = db.table("subscriptions").select(
                    "*, organizations(name, email, contact_email, owner_name)"
                ).execute()
                for sub in (subs.data or []):
                    meta = sub.get("metadata") or {}
                    if meta.get("square_order_id") == order_id:
                        updated_meta = {
                            **meta,
                            "payment_completed_at": datetime.now(timezone.utc).isoformat(),
                            "square_payment_id": payment.get("id"),
                        }

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
                subs = db.table("subscriptions").select(
                    "*, organizations(name, email, contact_email, owner_name)"
                ).execute()
                for sub in (subs.data or []):
                    meta = sub.get("metadata") or {}
                    matched = (
                        meta.get("setup_invoice_id") == invoice_id
                        or meta.get("renewal_invoice_id") == invoice_id
                    )
                    if not matched:
                        continue

                    now = datetime.now(timezone.utc)
                    org = sub.get("organizations") or {}

                    # Activate if pending/past_due
                    if sub.get("status") in ("pending_payment", "past_due"):
                        db.table("subscriptions").update({
                            "status": "active",
                            "metadata": {
                                **meta,
                                "payment_completed_at": now.isoformat(),
                            },
                        }).eq("id", sub["id"]).execute()
                        logger.info(f"Activated subscription from invoice {invoice_id}")

                    # Create Square auto-subscription if awaiting
                    if meta.get("awaiting_auto_subscription") and not meta.get("square_subscription_id"):
                        try:
                            from src.billing.billing_service import BillingService
                            billing = BillingService(db)
                            amount = meta.get("target_monthly_cents") or sub.get("monthly_price_cents", 0)

                            sub_result = await billing.create_auto_subscription(
                                org_id=sub["org_id"],
                                amount_cents=amount,
                                customer_email=org.get("email") or org.get("contact_email", ""),
                                customer_name=org.get("owner_name", ""),
                                business_name=org.get("name", ""),
                                plan=sub.get("tier", "starter"),
                            )

                            if sub_result.success:
                                db.table("subscriptions").update({
                                    "metadata": {
                                        **meta,
                                        "square_subscription_id": sub_result.subscription_id,
                                        "auto_billing": True,
                                        "awaiting_auto_subscription": False,
                                        "subscription_start_date": sub_result.start_date,
                                        "payment_completed_at": now.isoformat(),
                                    },
                                }).eq("id", sub["id"]).execute()
                                logger.info(
                                    f"Auto-subscription created for org {sub['org_id']}: "
                                    f"{sub_result.subscription_id}, starts {sub_result.start_date}"
                                )
                            else:
                                logger.warning(
                                    f"Auto-subscription failed for org {sub['org_id']}: "
                                    f"{sub_result.error} — will fall back to cron renewals"
                                )
                        except Exception as e:
                            logger.warning(f"Auto-subscription setup error: {e}")

                    break

        return {"status": "ok"}

    except RuntimeError:
        logger.error("Database not available for billing webhook")
        return {"status": "error", "detail": "Database unavailable"}
    except Exception as e:
        logger.exception("Billing webhook processing failed")
        return {"status": "error", "detail": "Webhook processing failed"}
