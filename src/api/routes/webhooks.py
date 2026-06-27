"""
Webhook Routes — Receive and process Square webhook events.

  POST /api/webhooks/square → Square sends events here

IMPORTANT: Square requires a 200 response within 3 seconds.
We acknowledge immediately and process async.
"""
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Request, Response, BackgroundTasks

from ...config import square as sq_config, clover as cl_config, app as app_config
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
        # Same conflict key as the backfill/incremental path (id is deterministic
        # now, so this dedupes idempotently). Was (org_id,external_id) here vs
        # (id,transaction_at) there — that split could double-write a line item.
        await _db_instance.batch_upsert(
            "transaction_items", items,
            on_conflict="id,transaction_at",
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
    """Mark a connection as disconnected (auth revoked) — full gate teardown."""
    from ...db import _db_instance
    if not _db_instance:
        return
    # Reuse the manual-disconnect teardown so a revoked merchant closes BOTH gate
    # fields + clears the token (org_id resolved from the connection row).
    from .pos_connections import teardown_connection
    await teardown_connection(_db_instance, connection_id)


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
            "external_merchant_id": f"eq.{merchant_id}",
            "status": "eq.connected",
        },
        limit=1,
    )
    if not rows:
        return None

    conn = rows[0]
    # Inject access_token for the SquareClient
    conn["access_token"] = conn.get("access_token_enc", "")
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
    
    # The POS webhook subscription has its own Square signature key;
    # fall back to the shared SQUARE_WEBHOOK_SIGNATURE_KEY (used by the
    # billing subscription) for single-subscription setups. Same pattern
    # as the credits webhook.
    signature_key = (
        os.environ.get("POS_SQUARE_WEBHOOK_SIGNATURE_KEY")
        or sq_config.webhook_signature_key
    )
    if not signature_key:
        logger.error("POS_SQUARE_WEBHOOK_SIGNATURE_KEY / SQUARE_WEBHOOK_SIGNATURE_KEY not configured — refusing to process")
        return Response(status_code=503)

    if not verify_webhook_signature(
        body=body,
        signature=signature,
        signature_key=signature_key,
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
            from ...db.cache import dashboard_cache, event_bus
            org_id = connection.get("org_id", "")
            dashboard_cache.invalidate_org(org_id)
            if "order" in event_type or "payment" in event_type:
                event_bus.publish_order(org_id, event_type)
            elif "inventory" in event_type or "catalog" in event_type:
                event_bus.publish_inventory(org_id)
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
        "signature_configured": bool(sq_config.webhook_signature_key),
    }


# ─── Clover Webhooks ─────────────────────────────────────────

@router.post("/clover")
async def clover_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Receive Clover webhook events.

    Clover payload: {appId, merchants: {MERCHANT_ID: [{type, objectId, ts}]}}
    Must respond 200 within 5 seconds.
    """
    body = await request.body()

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        return Response(status_code=400)

    # ── Initial callback-URL validation handshake ──
    # Clover POSTs {verificationCode: ...} (no X-Clover-Auth yet) when you first
    # register the URL. Log it so it can be pasted into the Dashboard, ack 200.
    verification_code = event.get("verificationCode")
    if verification_code:
        logger.info(f"Clover webhook verificationCode received: {verification_code}")
        return Response(status_code=200)

    # ── Authenticate real events: X-Clover-Auth carries the static Clover Auth
    #    Code verbatim — compare (constant-time), do NOT HMAC the payload. ──
    if not cl_config.webhook_auth_code:
        logger.error("CLOVER_WEBHOOK_AUTH_CODE not configured — refusing Clover webhook (fail closed)")
        return Response(status_code=503)

    received = request.headers.get("x-clover-auth", "")
    if not hmac.compare_digest(received, cl_config.webhook_auth_code):
        logger.warning("Clover webhook auth code mismatch")
        return Response(status_code=403)

    merchants = event.get("merchants", {})
    if not merchants:
        return Response(status_code=200)

    background_tasks.add_task(_process_clover_webhook, merchants)
    return Response(status_code=200)


async def _process_clover_webhook(merchants: dict):
    """Process Clover webhook events asynchronously."""
    from ...clover.webhook_handlers import CloverWebhookProcessor

    clover_processor = CloverWebhookProcessor(
        get_connection=_get_connection_by_provider_merchant,
        upsert_transaction=_upsert_transaction,
        upsert_catalog=_upsert_catalog,
        upsert_inventory=_upsert_inventory,
        disconnect_merchant=_disconnect_merchant,
        send_notification=_send_notification,
    )

    for merchant_id, events in merchants.items():
        connection = await _get_connection_by_provider_merchant("clover", merchant_id)
        if not connection and events:
            logger.warning(f"No Clover connection for merchant {merchant_id}")
            continue

        try:
            results = await clover_processor.handle(merchant_id, events, connection)
            logger.info(f"Clover webhook for {merchant_id}: {len(results)} events processed")
            if connection:
                from ...db.cache import dashboard_cache
                dashboard_cache.invalidate_org(connection.get("org_id", ""))
        except Exception as e:
            logger.error(f"Clover webhook failed for {merchant_id}: {e}", exc_info=True)


# ─── Toast Webhooks ──────────────────────────────────────────

@router.post("/toast")
async def toast_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Receive Toast webhook events.

    Toast sends: {eventType, restaurantGuid, webhookId, data: {...}}
    Must respond 200 quickly.
    """
    body = await request.body()

    # ── Fail closed: require the webhook secret to be configured ──
    toast_secret = os.environ.get("TOAST_WEBHOOK_SECRET", "")
    if not toast_secret:
        logger.error("TOAST_WEBHOOK_SECRET not configured — refusing to process Toast webhook (fail closed)")
        return Response(status_code=503)

    # Verify the HMAC-SHA256 signature Toast sends in the Toast-Signature header.
    # https://doc.toasttab.com/openapi/webhooks/ — reject forged/unsigned payloads.
    from ...toast.webhook_verify import verify_signature
    provided_sig = request.headers.get("Toast-Signature") or request.headers.get("toast-signature")
    if not verify_signature(toast_secret, body, provided_sig):
        logger.warning("Toast webhook rejected: missing/invalid Toast-Signature")
        return Response(status_code=401)

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        return Response(status_code=400)

    event_type = event.get("eventType", "unknown")
    restaurant_guid = event.get("restaurantGuid", "")

    logger.info(f"Toast webhook: {event_type} (restaurant={restaurant_guid})")

    background_tasks.add_task(
        _process_toast_webhook,
        event_type=event_type,
        event=event,
        restaurant_guid=restaurant_guid,
    )
    return Response(status_code=200)


async def _process_toast_webhook(event_type: str, event: dict, restaurant_guid: str):
    """Process Toast webhook event asynchronously."""
    connection = await _get_connection_by_provider_merchant("toast", restaurant_guid)
    if not connection:
        logger.warning(f"No Toast connection for restaurant {restaurant_guid}")
        return

    org_id = connection.get("org_id", "")

    try:
        if event_type in ("order.created", "order.updated", "order.closed"):
            from ...services.pos_sync_runner import run_incremental
            await run_incremental(org_id, "toast", connection)
        elif event_type == "restaurant.disconnected":
            await _disconnect_merchant(connection.get("id", ""))
            await _send_notification(
                org_id=org_id,
                title="Toast Disconnected",
                body="Your Toast POS connection was removed. Reconnect in Settings.",
                priority="urgent",
            )
        else:
            logger.info(f"Toast event {event_type} — no handler, syncing as fallback")
            from ...services.pos_sync_runner import run_incremental
            await run_incremental(org_id, "toast", connection)

        from ...db.cache import dashboard_cache
        dashboard_cache.invalidate_org(org_id)
    except Exception as e:
        logger.error(f"Toast webhook processing failed: {e}", exc_info=True)


# ─── Shared Helpers ──────────────────────────────────────────

async def _get_connection_by_provider_merchant(provider: str, merchant_id: str) -> dict | None:
    """Look up an active connection by provider + merchant ID."""
    from ...db import _db_instance
    if not _db_instance:
        return None

    rows = await _db_instance.select(
        "pos_connections",
        filters={
            "provider": f"eq.{provider}",
            "external_merchant_id": f"eq.{merchant_id}",
            "status": "eq.connected",
        },
        limit=1,
    )
    if not rows:
        return None

    conn = rows[0]
    conn["access_token"] = conn.get("access_token_enc", "")
    return conn
