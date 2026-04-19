"""
Webhook Routes — Receive and process Square webhook events.

  POST /api/webhooks/square → Square sends events here

IMPORTANT: Square requires a 200 response within 3 seconds.
We acknowledge immediately and process async.
"""
import json
import logging
from typing import Any

from fastapi import APIRouter, Request, Response, BackgroundTasks

from ...config import square as sq_config, app as app_config
from ...square.webhook_handlers import WebhookProcessor, verify_webhook_signature

logger = logging.getLogger("meridian.api.webhooks")

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

# Initialize processor (inject DB callbacks in production)
processor = WebhookProcessor()


@router.post("/square")
async def square_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Receive Square webhook event.
    
    Flow:
      1. Verify HMAC-SHA256 signature
      2. Parse event
      3. Acknowledge with 200 (must be <3 seconds)
      4. Process event asynchronously
    """
    body = await request.body()
    
    # ── Step 1: Verify signature ──────────────────────────
    signature = request.headers.get("x-square-hmacsha256-signature", "")
    
    if not sq_config.webhook_signature_key:
        logger.error("SQUARE_WEBHOOK_SIGNATURE_KEY not configured — refusing to process")
        return Response(status_code=503)

    if not verify_webhook_signature(
        body=body,
        signature=signature,
        signature_key=sq_config.webhook_signature_key,
        notification_url=app_config.webhook_url,
    ):
        logger.warning("Webhook signature verification failed")
        return Response(status_code=403)

    # ── Step 1b: Idempotency check ───────────────────────
    try:
        event_parsed = json.loads(body)
    except json.JSONDecodeError:
        return Response(status_code=400)

    event_id = event_parsed.get("event_id", "")
    if event_id and hasattr(processor, "is_duplicate") and await processor.is_duplicate(event_id):
        logger.info(f"Duplicate webhook event_id={event_id} — skipping")
        return Response(status_code=200)
    
    # ── Step 2: Parse event ───────────────────────────────
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook body")
        return Response(status_code=400)
    
    event_type = event.get("type", "unknown")
    merchant_id = event.get("merchant_id", "")
    event_id = event.get("event_id", "")
    
    logger.info(f"Webhook received: {event_type} (event_id={event_id}, merchant={merchant_id})")
    
    # ── Step 3: Quick lookup for connection ───────────────
    # In production: query pos_connections by external_merchant_id
    connection = None  # await db.find_connection_by_merchant(merchant_id)
    
    # ── Step 4: Acknowledge + process async ───────────────
    background_tasks.add_task(
        _process_webhook,
        event_type=event_type,
        event=event,
        connection=connection,
    )
    
    return Response(status_code=200)


async def _process_webhook(
    event_type: str,
    event: dict,
    connection: dict | None,
):
    """Process webhook event asynchronously (after 200 response)."""
    try:
        result = await processor.handle(event_type, event, connection)
        logger.info(f"Webhook {event_type} result: {result}")
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}", exc_info=True)
        # In production: push to dead letter queue
