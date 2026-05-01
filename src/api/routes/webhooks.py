"""
Webhook Routes — Receive and process Square webhook events.

  POST /api/webhooks/square → Square sends events here

IMPORTANT: Square requires a 200 response within 3 seconds.
We acknowledge immediately and process async.
"""
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Request, Response, BackgroundTasks

from ...config import square as sq_config, app as app_config
from ...square.webhook_handlers import WebhookProcessor, verify_webhook_signature

logger = logging.getLogger("meridian.api.webhooks")

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# ─── DB Callbacks for WebhookProcessor ────────────────────

async def _upsert_transaction(txn: dict, items: list[dict]):
    """Store a transaction + line items from webhook."""
    from ...db import _db_instance
    if not _db_instance:
        logger.warning("DB unavailable — skipping transaction upsert")
        return

    await _db_instance.upsert(
        "transactions", txn,
        on_conflict="org_id,external_id",
    )
    if items:
        await _db_instance.batch_upsert(
            "transaction_items", items,
            on_conflict="org_id,external_id",
        )


async def _upsert_catalog(categories: list[dict], products: list[dict]):
    """Store catalog updates from webhook."""
    from ...db import _db_instance
    if not _db_instance:
        return

    if categories:
        await _db_instance.batch_upsert(
            "categories", categories,
            on_conflict="org_id,external_id",
        )
    if products:
        await _db_instance.batch_upsert(
            "products", products,
            on_conflict="org_id,external_id",
        )


async def _upsert_inventory(snapshots: list[dict]):
    """Store inventory snapshots from webhook."""
    from ...db import _db_instance
    if not _db_instance:
        return

    if snapshots:
        await _db_instance.batch_upsert(
            "inventory_snapshots", snapshots,
            on_conflict="org_id,product_id,location_id",
        )


async def _disconnect_merchant(connection_id: str):
    """Mark a connection as disconnected (auth revoked)."""
    from ...db import _db_instance
    if not _db_instance:
        return

    await _db_instance.update(
        "pos_connections",
        {
            "status": "disconnected",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        filters={"id": f"eq.{connection_id}"},
    )


async def _send_notification(
    org_id: str,
    title: str,
    body: str,
    priority: str = "normal",
):
    """Create an in-app notification."""
    from ...db import _db_instance
    if not _db_instance:
        return

    await _db_instance.insert("notifications", {
        "id": str(uuid4()),
        "org_id": org_id,
        "title": title,
        "body": body,
        "priority": priority,
        "source_type": "alert",
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


async def _get_connection_by_merchant(merchant_id: str) -> dict | None:
    """Look up an active connection by Square merchant ID."""
    from ...db import _db_instance
    if not _db_instance:
        return None

    rows = await _db_instance.select(
        "pos_connections",
        filters={
            "merchant_id": f"eq.{merchant_id}",
            "status": "eq.connected",
        },
        limit=1,
    )
    if not rows:
        return None

    conn = rows[0]
    # Inject access_token for the SquareClient
    conn["access_token"] = conn.get("access_token_encrypted", "")
    return conn


# Initialize processor with real DB callbacks
processor = WebhookProcessor(
    get_connection=_get_connection_by_merchant,
    upsert_transaction=_upsert_transaction,
    upsert_catalog=_upsert_catalog,
    upsert_inventory=_upsert_inventory,
    disconnect_merchant=_disconnect_merchant,
    send_notification=_send_notification,
)


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

    # ── Step 2: Parse event ───────────────────────────────
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook body")
        return Response(status_code=400)

    event_type = event.get("type", "unknown")
    merchant_id = event.get("merchant_id", "")
    event_id = event.get("event_id", "")

    # ── Step 2b: Idempotency check ───────────────────────
    if event_id and await processor.is_duplicate(event_id):
        logger.info(f"Duplicate webhook event_id={event_id} — skipping")
        return Response(status_code=200)
    
    logger.info(f"Webhook received: {event_type} (event_id={event_id}, merchant={merchant_id})")
    
    # ── Step 3: Look up connection ────────────────────────
    connection = await _get_connection_by_merchant(merchant_id) if merchant_id else None
    
    if not connection and event_type != "oauth.authorization.revoked":
        logger.warning(f"No active connection for merchant {merchant_id}")
    
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
        if connection:
            from ...db.cache import dashboard_cache
            dashboard_cache.invalidate_org(connection.get("org_id", ""))
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}", exc_info=True)
        # Create error notification if we have a connection
        if connection:
            try:
                await _send_notification(
                    org_id=connection.get("org_id", ""),
                    title=f"Webhook Error: {event_type}",
                    body=f"Failed to process {event_type} event: {str(e)[:200]}",
                    priority="high",
                )
            except Exception:
                pass


@router.get("/square/health")
async def webhook_health():
    """Health check for webhook endpoint — useful for Square verification."""
    return {
        "status": "ready",
        "signature_key_configured": bool(sq_config.webhook_signature_key),
        "webhook_url": app_config.webhook_url,
    }
