"""
Clover Hosted Checkout payment webhook.

  POST /api/clover/hco/webhook

Clover's HCO webhook is configured PER MERCHANT in their dashboard
(Settings → Ecommerce → Hosted Checkout): the merchant pastes our URL and
generates a signing secret, which is stored on their phone_agent_config row
as `clover_hco_webhook_secret`. Payload shape:

  {"status": "APPROVED"|"DECLINED", "type": "PAYMENT", "id": <payment uuid>,
   "merchantId": ..., "data": <checkoutSessionId>, "createdTime", "message"}

Signature: HMAC-SHA256 in the `Clover-Signature` header (see
services/clover_hco.verify_hco_signature for the tolerantly-handled format).

On APPROVED PAYMENT the matching checkout_sessions row (provider_ref ==
checkoutSessionId) is marked paid and pay_on_phone.mark_order_paid releases
the held order — the SAME path the Stripe Connect webhook drives, so
POS-push-after-payment fires identically. Idempotent under Clover retries.
"""
import json
import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from ...db import get_db
from ...services.clover_hco import verify_hco_signature

logger = logging.getLogger("meridian.api.clover_hco")

router = APIRouter(prefix="/api/clover/hco", tags=["clover-hco"])

# phone_agent modules (pay_on_phone.mark_order_paid) live in a sibling dir —
# same import trick as stripe_connect.py.
_PHONE_AGENT_DIR = str(Path(__file__).resolve().parents[3] / "services" / "phone_agent")
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)


@router.post("/webhook")
async def hco_webhook(request: Request):
    """Verify + process a Clover Hosted Checkout payment event."""
    body = await request.body()
    signature = request.headers.get("clover-signature", "")
    try:
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("not an object")
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid payload")

    session_ref = str(payload.get("data") or "").strip()
    if not session_ref:
        # Not an HCO checkout event we can act on — ack so Clover stops retrying.
        return {"received": True, "ignored": "no_checkout_session_id"}

    db = get_db()
    rows = await db.select(
        "checkout_sessions",
        filters={"provider": "eq.clover", "provider_ref": f"eq.{session_ref}"},
        limit=1,
    )
    if not rows:
        # Unknown session: nothing to release, nothing to leak. Ack (200) —
        # this also covers sessions whose provider_ref persist failed at tap
        # time (logged loudly there for manual reconciliation).
        logger.warning("Clover HCO webhook for unknown session %s (merchantId=%s)",
                       session_ref, payload.get("merchantId"))
        return {"received": True, "ignored": "unknown_session"}
    row = rows[0]
    merchant_id = (row.get("merchant_id") or "").strip()

    # Per-merchant signing secret — WITHOUT it we cannot trust the event.
    # Fail closed: a spoofed APPROVED would release an unpaid order.
    cfg_rows = await db.select(
        "phone_agent_config",
        columns="clover_hco_webhook_secret",
        filters={"merchant_id": f"eq.{merchant_id}"},
        limit=1,
    ) if merchant_id else []
    secret = ((cfg_rows[0].get("clover_hco_webhook_secret") if cfg_rows else "") or "").strip()
    if not secret:
        logger.error(
            "CLOVER HCO WEBHOOK REJECTED — merchant %s has NO clover_hco_webhook_secret "
            "configured (set it from the merchant's Clover dashboard: Settings → "
            "Ecommerce → Hosted Checkout). Refusing to trust event %s.",
            merchant_id or "<unknown>", payload.get("id"),
        )
        raise HTTPException(status_code=401, detail="Webhook secret not configured")
    if not verify_hco_signature(secret, body, signature):
        logger.error("Clover HCO webhook signature verify FAILED for merchant %s "
                     "(session %s)", merchant_id, session_ref)
        raise HTTPException(status_code=401, detail="Invalid signature")

    etype = str(payload.get("type") or "").upper()
    status = str(payload.get("status") or "").upper()
    if etype != "PAYMENT":
        return {"received": True, "ignored": f"type_{etype or 'missing'}"}

    if status == "APPROVED":
        # Idempotent under retries: the row's paid flag is the guard —
        # mark_order_paid runs at most once per checkout session.
        if (row.get("status") or "").lower() == "paid":
            return {"received": True, "already_paid": True}
        await db.update(
            "checkout_sessions",
            {"status": "paid"},
            filters={"id": f"eq.{row.get('id')}"},
        )
        try:
            from pay_on_phone import mark_order_paid

            result = await mark_order_paid(
                merchant_id=merchant_id,
                caller_phone=row.get("caller_phone") or "",
                pos_order_id=row.get("pos_order_id") or "",
                method="clover",
                payment_txn_id=str(payload.get("id") or ""),
            )
            logger.info("Clover HCO payment confirmed → order released: %s", result)
        except Exception as e:  # noqa: BLE001 — webhook must still 200 so Clover
            # stops retrying; the session row is already marked paid.
            logger.error("mark_order_paid failed for %s: %s", merchant_id, e)
        return {"received": True, "released": True}

    if status == "DECLINED":
        # No release. Record the decline; 'declined' is NOT a terminal status
        # for /p (only paid/expired/canceled block), so the customer can retap
        # the link and try another card on the same or a fresh HCO session.
        if (row.get("status") or "").lower() != "paid":
            await db.update(
                "checkout_sessions",
                {"status": "declined"},
                filters={"id": f"eq.{row.get('id')}"},
            )
        logger.info("Clover HCO payment DECLINED for merchant %s (session %s): %s",
                    merchant_id, session_ref, payload.get("message"))
        return {"received": True, "declined": True}

    return {"received": True, "ignored": f"status_{status or 'missing'}"}
