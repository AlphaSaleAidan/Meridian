"""
FastAPI route: Square webhook receiver.

POST /api/webhooks/square

Receives real-time events from Square (order.created, payment.created, etc.).
Verifies HMAC-SHA256 signature, then dispatches to the appropriate handler.

Square requires a 200 response within 3 seconds — all heavy processing is
queued for async execution.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Request, Response

from ...services.square.webhook_handlers import (
    HandlerResult,
    WebhookContext,
    dispatch_webhook,
    verify_square_webhook,
)

logger = logging.getLogger("meridian.api.square.webhook")
router = APIRouter(tags=["square-webhooks"])

WEBHOOK_SIGNATURE_KEY = os.getenv("SQUARE_WEBHOOK_SIGNATURE_KEY", "")
WEBHOOK_URL = os.getenv("SQUARE_WEBHOOK_URL", "https://app.meridianpos.ai/api/webhooks/square")

# In sandbox / dev, optionally skip signature verification
SKIP_SIGNATURE_CHECK = os.getenv("SQUARE_SKIP_SIGNATURE_CHECK", "false").lower() == "true"


@router.post("/api/webhooks/square")
async def square_webhook(request: Request) -> Response:
    """
    Receive and process Square webhook events.

    Steps:
      1. Read raw body
      2. Verify HMAC-SHA256 signature (unless dev override)
      3. Parse event JSON
      4. Find matching pos_connection by merchant_id
      5. Dispatch to handler (async in production)
      6. Return 200 immediately (Square re-sends on non-200)
    """
    body = await request.body()

    # -- 1. Signature verification ----------------------------------------
    if not SKIP_SIGNATURE_CHECK:
        signature = request.headers.get("x-square-hmacsha256-signature", "")
        if not verify_square_webhook(body, signature, WEBHOOK_SIGNATURE_KEY, WEBHOOK_URL):
            logger.warning("Webhook signature verification failed")
            return Response(status_code=403, content="Invalid signature")

    # -- 2. Parse event ---------------------------------------------------
    try:
        event: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Webhook body is not valid JSON")
        return Response(status_code=400, content="Invalid JSON")

    event_type = event.get("type", "unknown")
    merchant_id = event.get("merchant_id", "unknown")
    event_id = event.get("event_id", "unknown")

    logger.info("Webhook received: type=%s merchant=%s event_id=%s",
                event_type, merchant_id, event_id)

    # -- 3. Find connection -----------------------------------------------
    # In production:
    #   conn = await db.query(
    #       "SELECT * FROM pos_connections WHERE external_merchant_id = $1 AND status IN ('connected','syncing')",
    #       merchant_id
    #   )
    #   if not conn: return Response(status_code=200)  # ACK but ignore
    #
    # For sandbox testing, we build a minimal context:
    ctx = WebhookContext(
        org_id="sandbox-org",
        pos_connection_id="sandbox-conn",
        access_token=os.getenv("SQUARE_ACCESS_TOKEN", ""),
        environment=os.getenv("SQUARE_ENVIRONMENT", "sandbox"),
    )

    # -- 4. Dispatch (in production this goes to a task queue) -----------
    try:
        result = await dispatch_webhook(event, ctx)
        if result:
            logger.info("Webhook handled: %s → %s (rows=%d)",
                        event_type, result.detail, result.rows_affected)
        else:
            logger.info("Webhook event type '%s' has no handler — ignored", event_type)
    except Exception as exc:
        # Log but don't fail — always return 200 to prevent Square retries
        logger.error("Webhook handler error for %s: %s", event_type, exc, exc_info=True)

    # -- 5. Always respond 200 within 3 seconds --------------------------
    return Response(status_code=200, content="OK")
