"""
Stripe Checkout API — Dynamic checkout session generator for proposals.

Creates Stripe Checkout Sessions that combine:
  - Recurring subscription (plan tier)
  - One-time setup fee (if applicable)
  - First-month-free trial (if applicable)

Endpoints:
  POST /api/stripe/create-checkout  → Create checkout session, return URL
  POST /api/stripe/webhook          → Handle Stripe webhook events
"""

import logging
import os
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger("meridian.stripe")

router = APIRouter(prefix="/api/stripe", tags=["stripe"])

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Plan tier → Stripe Price IDs (set in env after creating products in Stripe)
# These map to recurring monthly prices
STRIPE_PRICE_IDS = {
    "standard": os.getenv("STRIPE_PRICE_STANDARD", ""),
    "premium": os.getenv("STRIPE_PRICE_PREMIUM", ""),
    "command": os.getenv("STRIPE_PRICE_COMMAND", ""),
}

# Plan tier → default price in cents (fallback for ad-hoc prices)
PLAN_PRICES = {
    "standard": 25000,   # $250
    "premium": 50000,    # $500
    "command": 100000,   # $1000
}


# ── Models ──

class CheckoutSessionRequest(BaseModel):
    """Request body for creating a Stripe Checkout Session."""
    plan: str = "premium"                   # standard | premium | command
    custom_price_cents: Optional[int] = None  # Override monthly price
    setup_fee_cents: int = 0                # One-time setup fee (rep keeps 100%)
    first_month_free: bool = False          # Apply trial period
    customer_email: str
    customer_name: str
    business_name: str
    rep_id: Optional[str] = None
    rep_name: Optional[str] = None
    org_id: Optional[str] = None
    success_url: str = ""
    cancel_url: str = ""


class CheckoutSessionResponse(BaseModel):
    """Response with checkout session details."""
    checkout_url: str
    session_id: str
    plan: str
    monthly_amount: int
    setup_fee: int
    first_month_free: bool


# ── Helpers ──

def _get_stripe():
    """Lazy-import stripe to avoid import errors when key isn't set."""
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        return stripe
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="stripe package not installed. Run: pip install stripe"
        )


def _get_monthly_amount(plan: str, custom_price_cents: Optional[int]) -> int:
    """Resolve the monthly amount in cents."""
    if custom_price_cents and custom_price_cents > 0:
        return custom_price_cents
    return PLAN_PRICES.get(plan, 25000)


# ── Routes ──

@router.post("/create-checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(req: CheckoutSessionRequest, request: Request):
    """
    Create a Stripe Checkout Session.

    Combines subscription + optional one-time setup fee in a single checkout.
    If first_month_free is True, adds a 30-day trial to the subscription.
    """
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=501,
            detail="Stripe not configured. Set STRIPE_SECRET_KEY env var."
        )

    stripe = _get_stripe()
    monthly_amount = _get_monthly_amount(req.plan, req.custom_price_cents)

    try:
        line_items = []
        mode = "subscription"
        subscription_data = None

        # -- Recurring subscription line item --
        price_id = STRIPE_PRICE_IDS.get(req.plan)

        if price_id and not req.custom_price_cents:
            # Use pre-created Stripe Price object
            line_items.append({
                "price": price_id,
                "quantity": 1,
            })
        else:
            # Create an ad-hoc price for custom amounts
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Meridian {req.plan.title()} Plan",
                        "description": f"Monthly analytics subscription for {req.business_name}",
                    },
                    "unit_amount": monthly_amount,
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            })

        # -- One-time setup fee line item --
        if req.setup_fee_cents > 0:
            # Stripe allows mixing subscription + one-time items in subscription mode
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Setup Fee",
                        "description": "One-time account setup and onboarding",
                    },
                    "unit_amount": req.setup_fee_cents,
                },
                "quantity": 1,
            })

        # -- Trial period for first month free --
        if req.first_month_free:
            subscription_data = {
                "trial_period_days": 30,
                "metadata": {
                    "first_month_free": "true",
                    "plan": req.plan,
                    "business_name": req.business_name,
                    "rep_id": req.rep_id or "",
                    "rep_name": req.rep_name or "",
                },
            }
        else:
            subscription_data = {
                "metadata": {
                    "plan": req.plan,
                    "business_name": req.business_name,
                    "rep_id": req.rep_id or "",
                    "rep_name": req.rep_name or "",
                },
            }

        # -- Default URLs --
        base_url = req.success_url.rsplit("/", 1)[0] if req.success_url else "https://meridian.tips"
        success_url = req.success_url or f"{base_url}/onboard?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = req.cancel_url or f"{base_url}/onboard?checkout=cancelled"

        # -- Create the session --
        session = stripe.checkout.Session.create(
            mode=mode,
            line_items=line_items,
            subscription_data=subscription_data,
            customer_email=req.customer_email,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "meridian_org_id": req.org_id or "",
                "meridian_plan": req.plan,
                "meridian_rep_id": req.rep_id or "",
                "meridian_rep_name": req.rep_name or "",
                "business_name": req.business_name,
                "setup_fee_cents": str(req.setup_fee_cents),
                "first_month_free": str(req.first_month_free),
            },
            allow_promotion_codes=True,
            billing_address_collection="required",
            phone_number_collection={"enabled": True},
        )

        logger.info(
            f"Checkout session created: {session.id} | "
            f"plan={req.plan} monthly=${monthly_amount/100:.0f} "
            f"setup=${req.setup_fee_cents/100:.0f} "
            f"trial={'30d' if req.first_month_free else 'none'} "
            f"rep={req.rep_name or 'unknown'}"
        )

        # Optionally record in DB
        try:
            db = getattr(request.app.state, "db", None)
            if db:
                db.table("checkout_sessions").insert({
                    "id": str(uuid4()),
                    "stripe_session_id": session.id,
                    "org_id": req.org_id,
                    "plan": req.plan,
                    "monthly_amount_cents": monthly_amount,
                    "setup_fee_cents": req.setup_fee_cents,
                    "first_month_free": req.first_month_free,
                    "customer_email": req.customer_email,
                    "business_name": req.business_name,
                    "rep_id": req.rep_id,
                    "status": "pending",
                    "checkout_url": session.url,
                    "created_at": datetime.utcnow().isoformat(),
                }).execute()
        except Exception as e:
            # Don't fail the checkout if DB recording fails
            logger.warning(f"Failed to record checkout session: {e}")

        return CheckoutSessionResponse(
            checkout_url=session.url,
            session_id=session.id,
            plan=req.plan,
            monthly_amount=monthly_amount,
            setup_fee=req.setup_fee_cents,
            first_month_free=req.first_month_free,
        )

    except Exception as e:
        logger.exception("Stripe checkout session creation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.

    Key events:
    - checkout.session.completed → Activate subscription, record setup fee
    - customer.subscription.created → Log new subscription
    - invoice.paid → Record successful payment
    - customer.subscription.deleted → Handle cancellation
    """
    stripe = _get_stripe()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        else:
            # Dev mode — parse without verification
            import json
            event = json.loads(payload)
            logger.warning("Stripe webhook signature verification skipped (no secret configured)")
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    logger.info(f"Stripe webhook: {event_type}")

    try:
        db = getattr(request.app.state, "db", None)

        if event_type == "checkout.session.completed":
            session_id = data.get("id", "")
            metadata = data.get("metadata", {})
            org_id = metadata.get("meridian_org_id")
            plan = metadata.get("meridian_plan", "standard")
            rep_id = metadata.get("meridian_rep_id")
            setup_fee = int(metadata.get("setup_fee_cents", "0"))

            logger.info(
                f"Checkout completed: session={session_id} "
                f"org={org_id} plan={plan} rep={rep_id}"
            )

            if db and org_id:
                # Update org to active with plan
                try:
                    db.table("organizations").update({
                        "metadata": {
                            "plan_tier": plan,
                            "stripe_session_id": session_id,
                            "stripe_customer_id": data.get("customer"),
                            "stripe_subscription_id": data.get("subscription"),
                            "payment_status": "active",
                            "setup_fee_cents": setup_fee,
                            "activated_at": datetime.utcnow().isoformat(),
                        },
                    }).eq("id", org_id).execute()
                except Exception as e:
                    logger.warning(f"Failed to update org {org_id}: {e}")

                # Record commission for the rep
                if rep_id and setup_fee > 0:
                    try:
                        db.table("commissions").insert({
                            "id": str(uuid4()),
                            "rep_id": rep_id,
                            "org_id": org_id,
                            "type": "setup_fee",
                            "amount_cents": setup_fee,
                            "status": "earned",
                            "metadata": {
                                "stripe_session_id": session_id,
                                "note": "Setup fee — 100% to rep",
                            },
                        }).execute()
                    except Exception as e:
                        logger.warning(f"Failed to record setup fee commission: {e}")

                # Update checkout session status
                try:
                    db.table("checkout_sessions").update({
                        "status": "completed",
                        "completed_at": datetime.utcnow().isoformat(),
                    }).eq("stripe_session_id", session_id).execute()
                except Exception as e:
                    logger.error(f"Webhook processing error: {e}")

        elif event_type == "invoice.paid":
            subscription_id = data.get("subscription", "")
            amount = data.get("amount_paid", 0)
            logger.info(f"Invoice paid: sub={subscription_id} amount=${amount/100:.2f}")

        elif event_type == "customer.subscription.deleted":
            subscription_id = data.get("id", "")
            logger.info(f"Subscription cancelled: {subscription_id}")

            if db:
                # Find and deactivate the org
                try:
                    sessions = db.table("checkout_sessions").select("org_id").eq(
                        "stripe_subscription_id", subscription_id
                    ).execute()
                    for s in (sessions.data or []):
                        if s.get("org_id"):
                            db.table("organizations").update({
                                "metadata": {"payment_status": "cancelled"},
                            }).eq("id", s["org_id"]).execute()
                except Exception as e:
                    logger.error(f"Webhook processing error: {e}")

    except Exception as e:
        logger.exception(f"Webhook processing error for {event_type}")

    return {"status": "ok"}
