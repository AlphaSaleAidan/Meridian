"""
Stripe Checkout API — Subscription link management and webhook handling.

Endpoints:
  POST /api/stripe/subscribe-link   → Generate stable subscription short-link + QR
  POST /api/stripe/webhook          → Handle Stripe webhook events
"""

import json
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth import enforce_service_member, require_service_auth

logger = logging.getLogger("meridian.stripe")

router = APIRouter(prefix="/api/stripe", tags=["stripe"])

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

PUBLIC_PAY_BASE = os.getenv("PUBLIC_PAY_BASE", "https://meridian.tips")


# ── Models ──

class SubscribeLinkRequest(BaseModel):
    """Request body for generating a stable subscription short-link + QR."""
    org_id: Optional[str] = None
    lead_id: Optional[str] = None
    monthly_amount_cents: int           # Amount in smallest currency unit (e.g. 49900 = CA$499)
    currency: str = "cad"
    business_name: Optional[str] = None
    setup_fee_cents: int = 0
    first_month_free: bool = False


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


# ── Routes ──

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

    # Fail closed: never process an unverified payment event. Without the signing
    # secret a spoofed event could mark a subscription paid.
    if not STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET not set — refusing Stripe webhook (fail closed)")
        raise HTTPException(status_code=503, detail="Webhook not configured")
    try:
        stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )  # verify signature (raises if bad)
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    # Read the VERIFIED payload as plain dicts — this SDK's StripeObject is not
    # dict-subclassed, so event.get(...) raises AttributeError and 500s the
    # webhook. Bytes are signature-verified above, so json.loads is safe.
    event = json.loads(payload)

    event_id = event.get("id", "")
    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    # ── Idempotency: dedupe via the same webhook_events table used by Square/Clover ──
    # Returns True (first delivery), False (duplicate), or None (DB unavailable → process).
    if event_id:
        try:
            from .webhooks import _record_webhook_event
            is_new = await _record_webhook_event(event_id, provider="stripe")
            if is_new is False:
                logger.info(f"Duplicate Stripe webhook event_id={event_id} — skipping")
                return {"status": "ok"}
        except Exception as _dedup_err:
            logger.warning(f"Stripe webhook dedup failed ({_dedup_err}) — processing anyway")

    logger.info(f"Stripe webhook: {event_type} (event_id={event_id})")

    try:
        from ...db import _db_instance as db

        if event_type == "checkout.session.completed":
            # CRITICAL money path — raises on failure (see helper). The money
            # already moved, so a swallowed activation/commission is not
            # acceptable; on failure we un-record the dedupe marker and return a
            # non-2xx below so Stripe retries.
            await _activate_from_checkout(db, data)

        elif event_type == "invoice.paid":
            subscription_id = data.get("subscription", "")
            amount = data.get("amount_paid", 0)
            logger.info(f"Invoice paid: sub={subscription_id} amount=${amount/100:.2f}")

        elif event_type == "customer.subscription.deleted":
            subscription_id = data.get("id", "")
            logger.info(f"Subscription cancelled: {subscription_id}")

            if db:
                try:
                    import json as json_mod
                    sessions = await db.select("checkout_sessions", "org_id", filters={"stripe_subscription_id": f"eq.{subscription_id}"})
                    for s in (sessions or []):
                        if s.get("org_id"):
                            # Read-modify-write: only flip payment_status —
                            # don't wipe setup_fee_cents/plan_tier/etc.
                            org_rows = await db.select("organizations", "metadata", filters={"id": f"eq.{s['org_id']}"}, limit=1)
                            meta = (org_rows[0].get("metadata") if org_rows else None) or {}
                            if isinstance(meta, str):
                                try:
                                    meta = json_mod.loads(meta)
                                except Exception:
                                    meta = {}
                            await db.update("organizations", {
                                "metadata": json_mod.dumps({**meta, "payment_status": "cancelled"}),
                            }, filters={"id": f"eq.{s['org_id']}"})
                            # Stop the phone agent — INDEPENDENT safety plane, so
                            # a reclaim hiccup can't leave a Stripe-cancelled /
                            # dunned merchant's agent live burning Vapi/Telnyx.
                            try:
                                from src.services.number_pool import deactivate_phone_agent
                                await deactivate_phone_agent(db, s["org_id"])
                            except Exception:
                                logger.exception("phone-agent deactivate failed for cancelled org %s",
                                                 s.get("org_id"))
                            # Reclaim the merchant's phone number to the pool for
                            # reassignment (Stripe-side / dunning cancellation).
                            # Best-effort — a reclaim hiccup never fails the webhook.
                            try:
                                from src.services.number_pool import release_to_pool
                                await release_to_pool(db, s["org_id"])
                            except Exception:
                                logger.exception("number reclaim failed for cancelled org %s",
                                                 s.get("org_id"))
                except Exception as e:
                    logger.error(f"Webhook processing error: {e}")

    except Exception:
        logger.exception(f"Webhook processing error for {event_type}")
        # A critical write failed. Un-record the dedupe marker so Stripe's retry
        # is NOT skipped as a duplicate, and return a non-2xx so Stripe actually
        # retries — instead of silently leaving a paid customer inactive / a rep
        # unpaid with no recovery path. The activation + commission writes are
        # idempotent, so the retry is safe.
        if event_id:
            from .webhooks import _forget_webhook_event
            await _forget_webhook_event(event_id, provider="stripe")
        raise HTTPException(status_code=500, detail="processing failed — will retry")

    return {"status": "ok"}


async def _activate_from_checkout(db, data: dict) -> None:
    """Activate the org + book the rep setup-fee commission for a completed
    checkout. Both writes are IDEMPOTENT — activation is a full metadata
    overwrite, and the commission id is derived deterministically from the
    session id so a retry conflicts on the primary key (swallowed) instead of
    double-booking. RAISES on a real write failure so the webhook can un-record
    the dedupe marker and return a non-2xx: the money moved, so a silent drop is
    not acceptable and Stripe must retry."""
    session_id = data.get("id", "")
    metadata = data.get("metadata", {}) or {}
    # The live subscribe flow (pay_redirect._create_sub_session) writes org_id /
    # lead_id / business_name / setup_fee_cents. Older sessions used a meridian_*
    # prefix — accept either so no in-flight checkout is dropped.
    org_id = metadata.get("org_id") or metadata.get("meridian_org_id")
    plan = (metadata.get("plan") or metadata.get("plan_tier")
            or metadata.get("meridian_plan") or "standard")
    rep_id = metadata.get("rep_id") or metadata.get("meridian_rep_id")
    try:
        setup_fee = int(metadata.get("setup_fee_cents", "0") or 0)
    except (TypeError, ValueError):
        setup_fee = 0

    logger.info("Checkout completed: session=%s org=%s plan=%s rep=%s",
                session_id, org_id, plan, rep_id)
    if not (db and org_id):
        return  # no db / no org in metadata — nothing to activate (not a failure)

    import json as json_mod

    # 1) Activate the org (idempotent full overwrite of the payment metadata).
    await db.update("organizations", {
        "metadata": json_mod.dumps({
            "plan_tier": plan,
            "stripe_session_id": session_id,
            "stripe_customer_id": data.get("customer"),
            "stripe_subscription_id": data.get("subscription"),
            "payment_status": "active",
            "setup_fee_cents": setup_fee,
            "activated_at": datetime.now(timezone.utc).isoformat(),
        }),
    }, filters={"id": f"eq.{org_id}"})

    # 2) Book the rep setup-fee commission — deterministic id per checkout
    #    session, so a retry (or the un-record→reprocess path) hits a PK conflict
    #    (swallowed) rather than inserting a second commission row.
    if rep_id and setup_fee > 0:
        await db.insert("commissions", {
            "id": str(uuid5(NAMESPACE_URL, f"meridian-setup-fee:{session_id}")),
            "rep_id": rep_id,
            "org_id": org_id,
            "type": "setup_fee",
            "amount_cents": setup_fee,
            "status": "earned",
            "metadata": json_mod.dumps({
                "stripe_session_id": session_id,
                "note": "Setup fee — 100% to rep",
            }),
        })

    # 3) Bookkeeping only (non-critical): mark the checkout_sessions row done.
    try:
        await db.update("checkout_sessions", {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }, filters={"stripe_session_id": f"eq.{session_id}"})
    except Exception as e:  # noqa: BLE001 — bookkeeping never blocks activation
        logger.warning("checkout_sessions completed-flip failed for %s: %s", session_id, e)

    # 4) The money landed → put every adder this merchant bought on the Foundry
    # dev marketplace (migration 079). Payment is the trigger by design: nobody
    # should do spec work against a deal that never paid. Idempotent on retry —
    # only orders still awaiting_payment are posted.
    #
    # Non-critical on purpose: the payment is verified and the org is already
    # active, so a marketplace hiccup must not make Stripe retry the whole
    # event. A failed posting stays visible as `failed` on the work order.
    try:
        from ...services.setup_services import dispatch_paid_orders
        await dispatch_paid_orders(org_id=org_id, session_id=session_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("work-order dispatch failed for org %s: %s", org_id, e)


# ── Subscribe-link management ──────────────────────────────────────────────

@router.post("/subscribe-link", dependencies=[Depends(require_service_auth)])
async def create_subscribe_link(req: SubscribeLinkRequest, principal=Depends(require_service_auth)):
    """
    Generate a stable subscription short-link (and QR) for a merchant.

    The returned ``url`` is always ``{PUBLIC_PAY_BASE}/subscribe/{token}``.
    GET /subscribe/{token}      → creates a fresh Stripe Checkout Session + redirects
    The rep portal renders the QR from this URL client-side (no server QR endpoint).

    Auth: service-role key or rep JWT (Bearer).  If org_id is present the
    principal must belong to that org (enforced by enforce_service_member).

    This flow is SEPARATE from the per-order $1.50 Connect fee:
      - No application_fee_amount / transfer_data
      - Direct charge to Meridian's Stripe account
      - mode=subscription, metadata.kind=subscription
    """
    if req.org_id:
        await enforce_service_member(principal, req.org_id)

    if req.monthly_amount_cents <= 0:
        raise HTTPException(status_code=422, detail="monthly_amount_cents must be > 0")

    token = secrets.token_urlsafe(16)  # ~22 url-safe chars, 128 bits of entropy
    subscribe_url = f"{PUBLIC_PAY_BASE}/subscribe/{token}"

    try:
        from ...db import _db_instance as db
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        await db.insert("subscribe_links", {
            "token": token,
            "org_id": req.org_id,
            "lead_id": req.lead_id,
            "monthly_amount_cents": req.monthly_amount_cents,
            "currency": req.currency.lower(),
            "business_name": req.business_name,
            "setup_fee_cents": req.setup_fee_cents,
            "first_month_free": req.first_month_free,
            "status": "active",
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create subscribe_link row")
        raise HTTPException(status_code=500, detail=str(e))

    logger.info(
        f"Subscribe link created: token={token} org={req.org_id} "
        f"monthly={req.monthly_amount_cents} currency={req.currency}"
    )
    return {"token": token, "url": subscribe_url}
