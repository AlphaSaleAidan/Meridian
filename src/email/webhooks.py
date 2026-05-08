"""
Postal webhook handler — tracks delivery, opens, clicks, and bounces.

Postal sends POST requests with event payloads. We verify the webhook
secret header and update email_send_log accordingly.
"""
import hmac
import hashlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger("meridian.email.webhooks")

router = APIRouter(prefix="/webhooks", tags=["email"])


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return True
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/postal")
async def postal_webhook(request: Request):
    """Handle Postal delivery/open/click/bounce webhooks."""
    import os
    secret = os.getenv("POSTAL_WEBHOOK_SECRET", "")
    body = await request.body()
    sig = request.headers.get("X-Postal-Signature", "")

    if secret and not _verify_signature(body, sig, secret):
        raise HTTPException(401, "Invalid webhook signature")

    data = await request.json()
    event = data.get("event")
    payload = data.get("payload", {})
    message_id = payload.get("message", {}).get("id") or payload.get("message_id")

    if not message_id:
        return {"status": "ignored", "reason": "no_message_id"}

    now = datetime.now(timezone.utc).isoformat()

    update_map = {
        "MessageDelivered": {"postal_status": "delivered"},
        "MessageBounced": {"postal_status": "bounced", "bounced_at": now},
        "MessageLinkClicked": {"clicked_at": now},
        "MessageOpened": {"opened_at": now},
        "MessageDeliveryFailed": {"postal_status": "failed", "error_detail": payload.get("details")},
        "MessageHeld": {"postal_status": "held"},
    }

    updates = update_map.get(event)
    if not updates:
        logger.debug("Ignoring Postal event: %s", event)
        return {"status": "ignored", "event": event}

    try:
        from ..db import init_db
        db = await init_db()
        if db:
            await db.execute(
                """UPDATE email_send_log
                   SET postal_status = COALESCE($1, postal_status),
                       opened_at = COALESCE($2, opened_at),
                       clicked_at = COALESCE($3, clicked_at),
                       bounced_at = COALESCE($4, bounced_at),
                       error_detail = COALESCE($5, error_detail)
                   WHERE postal_message_id = $6""",
                updates.get("postal_status"),
                updates.get("opened_at"),
                updates.get("clicked_at"),
                updates.get("bounced_at"),
                updates.get("error_detail"),
                str(message_id),
            )
            logger.info("[Postal webhook] %s for message %s", event, message_id)
    except Exception as exc:
        logger.error("Webhook DB update failed: %s", exc)

    return {"status": "processed", "event": event, "message_id": message_id}
