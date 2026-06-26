"""
Unified payments — Stripe Connect.

One processor across any POS: each merchant gets a Stripe *connected account*
during onboarding; the customer pays via Stripe Checkout (destination charge →
the merchant's account, minus a Meridian application fee). The order still goes
to whichever POS the merchant runs; "take the money" is always Stripe.

Endpoints:
  POST /api/stripe/connect/onboard/{merchant_id} → create connected account (if
       needed) + return a Stripe onboarding link (used by the onboarding wizard)
  GET  /api/stripe/connect/status/{merchant_id}  → onboarding / charges status
  POST /api/stripe/connect/webhook               → account.updated (mark
       charges_enabled) + checkout.session.completed (mark the order paid)

All Stripe calls are lazy-imported so the module loads with no SDK/key present.
"""
import logging
import os
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import require_service_auth
from ...db import get_db

logger = logging.getLogger("meridian.stripe.connect")

router = APIRouter(prefix="/api/stripe/connect", tags=["stripe-connect"])

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
CONNECT_WEBHOOK_SECRET = os.getenv("STRIPE_CONNECT_WEBHOOK_SECRET", "")
CONNECT_RETURN_URL = os.getenv("CONNECT_RETURN_URL", "https://meridian.tips/canada/portal?payments=connected")
CONNECT_REFRESH_URL = os.getenv("CONNECT_REFRESH_URL", "https://meridian.tips/canada/portal?payments=retry")
CONNECT_COUNTRY = os.getenv("CONNECT_DEFAULT_COUNTRY", "CA")

# phone_agent modules (pay_on_phone.mark_order_paid) live in a sibling dir.
_PHONE_AGENT_DIR = str(Path(__file__).resolve().parents[3] / "services" / "phone_agent")
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)


def _stripe():
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


async def _set_config(db, merchant_id: str, patch: dict) -> None:
    rows = await db.select("phone_agent_config", filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    if rows:
        await db.update("phone_agent_config", patch, filters={"merchant_id": f"eq.{merchant_id}"})
    else:
        await db.insert("phone_agent_config", {"merchant_id": merchant_id, **patch})


@router.post("/onboard/{merchant_id}")
async def onboard(merchant_id: str, _auth=Depends(require_service_auth)):
    """Create the merchant's Stripe connected account (once) and return a hosted
    onboarding link. Called from the onboarding wizard's Payments step."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    stripe = _stripe()
    db = get_db()
    rows = await db.select("phone_agent_config", filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    row = rows[0] if rows else {}
    acct = (row.get("stripe_account_id") or "").strip()

    if not acct:
        try:
            account = stripe.Account.create(
                type="express",
                country=CONNECT_COUNTRY,
                email=(row.get("merchant_email") or None),
                capabilities={"card_payments": {"requested": True}, "transfers": {"requested": True}},
                business_profile={"name": row.get("business_name") or None},
                # Pay the merchant out DAILY — after we auto-take the service fee
                # (application_fee on each destination charge), Stripe settles the
                # remainder to them on a daily schedule.
                settings={"payouts": {"schedule": {"interval": "daily"}}},
                metadata={"merchant_id": merchant_id},
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Stripe account create failed for %s: %s", merchant_id, e)
            raise HTTPException(status_code=502, detail="Could not create Stripe account") from e
        acct = account["id"]
        await _set_config(db, merchant_id, {"stripe_account_id": acct})

    link = stripe.AccountLink.create(
        account=acct,
        refresh_url=CONNECT_REFRESH_URL,
        return_url=CONNECT_RETURN_URL,
        type="account_onboarding",
    )
    return {"account_id": acct, "onboarding_url": link["url"]}


@router.get("/status/{merchant_id}")
async def status(merchant_id: str, _auth=Depends(require_service_auth)):
    """Onboarding status for the wizard — refreshes charges_enabled from Stripe."""
    db = get_db()
    rows = await db.select("phone_agent_config", filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    acct = (rows[0].get("stripe_account_id") if rows else "") or ""
    if not acct:
        return {"connected": False, "charges_enabled": False}
    if not STRIPE_SECRET_KEY:
        return {"connected": True, "account_id": acct, "charges_enabled": bool(rows[0].get("stripe_charges_enabled"))}
    stripe = _stripe()
    acc = stripe.Account.retrieve(acct)
    charges = bool(acc.get("charges_enabled"))
    # keep our copy in sync so the checkout gate is accurate
    await _set_config(db, merchant_id, {"stripe_charges_enabled": charges})
    return {
        "connected": True,
        "account_id": acct,
        "charges_enabled": charges,
        "details_submitted": bool(acc.get("details_submitted")),
        "payouts_enabled": bool(acc.get("payouts_enabled")),
    }


@router.post("/webhook")
async def connect_webhook(request: Request):
    """Stripe Connect webhook: keep charges_enabled in sync and mark orders paid."""
    stripe = _stripe()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    # Fail closed: a spoofed checkout.session.completed could mark a CAD order
    # paid and release it. Never process an unverified Connect event.
    if not CONNECT_WEBHOOK_SECRET:
        logger.error("STRIPE_CONNECT_WEBHOOK_SECRET not set — refusing Connect webhook (fail closed)")
        raise HTTPException(status_code=503, detail="Webhook not configured")
    try:
        event = stripe.Webhook.construct_event(payload, sig, CONNECT_WEBHOOK_SECRET)
    except Exception as e:  # noqa: BLE001
        logger.error("Connect webhook verify failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")

    etype = event.get("type", "")
    obj = event.get("data", {}).get("object", {})
    db = get_db()

    if etype == "account.updated":
        acct = obj.get("id", "")
        charges = bool(obj.get("charges_enabled"))
        rows = await db.select("phone_agent_config", filters={"stripe_account_id": f"eq.{acct}"}, limit=1)
        if rows:
            await db.update("phone_agent_config", {"stripe_charges_enabled": charges},
                            filters={"stripe_account_id": f"eq.{acct}"})
            logger.info("Connect account %s charges_enabled=%s", acct, charges)

    elif etype in ("checkout.session.completed", "payment_intent.succeeded"):
        meta = obj.get("metadata", {}) or {}
        merchant_id = meta.get("merchant_id", "")
        pos_order_id = meta.get("pos_order_id", "")
        caller_phone = meta.get("caller_phone", "")
        txn = obj.get("payment_intent") or obj.get("id", "")
        try:
            from pay_on_phone import mark_order_paid
            result = await mark_order_paid(
                merchant_id=merchant_id, caller_phone=caller_phone,
                pos_order_id=pos_order_id, method="stripe", payment_txn_id=str(txn),
            )
            logger.info("Stripe payment confirmed → order released: %s", result)
        except Exception as e:  # noqa: BLE001 — webhook must still 200 so Stripe stops retrying spuriously
            logger.error("mark_order_paid failed for %s: %s", merchant_id, e)

        # Text the customer a paid receipt. Only on checkout.session.completed
        # (canonical, fires once) so payment_intent.succeeded can't double-send.
        if etype == "checkout.session.completed" and caller_phone:
            try:
                from merchant_config import get_merchant_config, _demo_config
                from sms_checkout import send_sms
                cfg = (await get_merchant_config(merchant_id)) if merchant_id else None
                cfg = cfg or _demo_config(merchant_id or "demo")
                biz = getattr(cfg, "business_name", "") or "the restaurant"
                cents = obj.get("amount_total")
                cur = (obj.get("currency") or "cad").upper()
                name = ((obj.get("customer_details") or {}).get("name") or "").split(" ")[0]
                hi = f" {name}" if name else ""
                amt = f" — {cur} ${cents/100:.2f}" if isinstance(cents, (int, float)) else ""
                body = (f"Payment received ✓ Thanks{hi}! Your order at {biz} is "
                        f"confirmed and paid{amt}. We'll have it ready shortly.")
                res = await send_sms(caller_phone, body)
                logger.info("Receipt SMS to %s: sent=%s", caller_phone, res.get("sent"))
            except Exception as e:  # noqa: BLE001 — receipt never blocks the webhook
                logger.error("receipt SMS failed for %s: %s", merchant_id, e)

        # Credit our service-fee revenue to this merchant's voice ledger. Only on
        # checkout.session.completed (the one canonical event per order — the
        # session id is a stable idempotency ref); payment_intent.succeeded fires
        # for the same order and would double-post under a different ref.
        if etype == "checkout.session.completed" and merchant_id:
            fee_cents = int(os.getenv("MERIDIAN_SERVICE_FEE_CENTS", "0") or 0)
            if fee_cents > 0:
                try:
                    from ...services.voice_ledger import credit
                    await credit(merchant_id, fee_cents, source="stripe_fee",
                                 ref=str(obj.get("id") or txn), note=pos_order_id or None)
                except Exception as e:  # noqa: BLE001 — ledger never blocks the webhook
                    logger.error("voice_ledger credit failed for %s: %s", merchant_id, e)

    return {"received": True}
