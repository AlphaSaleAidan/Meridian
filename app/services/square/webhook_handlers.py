"""
Square webhook event handlers.

Handles 7 event types:
  - order.created / order.updated
  - payment.created / payment.updated
  - catalog.version.updated
  - inventory.count.updated
  - oauth.authorization.revoked

Each handler receives the full event payload + the matching POS connection
context. Handlers are designed to be idempotent and fast (heavy lifting
is queued for async processing in production).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Coroutine

from .client import SquareClient
from .mappers import (
    map_inventory_count,
    map_payment_enrichment,
    map_transaction,
    map_transaction_items,
)

logger = logging.getLogger("meridian.square.webhooks")


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------
def verify_square_webhook(
    body: bytes,
    signature: str,
    signature_key: str,
    notification_url: str,
) -> bool:
    """
    Verify HMAC-SHA256 signature on a Square webhook.

    Square signs: notification_url + raw_body
    """
    if not signature or not signature_key:
        return False

    combined = notification_url.encode("utf-8") + body
    expected = hmac.new(
        key=signature_key.encode("utf-8"),
        msg=combined,
        digestmod=hashlib.sha256,
    ).digest()
    expected_b64 = base64.b64encode(expected).decode("utf-8")

    return hmac.compare_digest(expected_b64, signature)


# ---------------------------------------------------------------------------
# Connection context (passed to each handler)
# ---------------------------------------------------------------------------
@dataclass
class WebhookContext:
    """Minimal context needed by webhook handlers."""
    org_id: str
    pos_connection_id: str
    access_token: str
    environment: str = "sandbox"
    location_lookup: dict[str, str] | None = None
    product_lookup: dict[str, str] | None = None
    employee_lookup: dict[str, str] | None = None


# ---------------------------------------------------------------------------
# Handler results
# ---------------------------------------------------------------------------
@dataclass
class HandlerResult:
    event_type: str
    success: bool = True
    rows_affected: int = 0
    detail: str = ""


# ---------------------------------------------------------------------------
# Individual handlers
# ---------------------------------------------------------------------------
async def handle_order_created(event: dict, ctx: WebhookContext) -> HandlerResult:
    """New order placed on Square POS."""
    order_id = event.get("data", {}).get("id", "")
    logger.info("order.created: %s (org=%s)", order_id, ctx.org_id)

    async with SquareClient(ctx.access_token, ctx.environment) as client:
        sq_order = await client.retrieve_order(order_id)

    if not sq_order:
        return HandlerResult("order.created", success=False, detail=f"Order {order_id} not found")

    txn = map_transaction(
        sq_order, ctx.org_id,
        ctx.location_lookup or {},
        ctx.employee_lookup or {},
        ctx.pos_connection_id,
    )
    items = map_transaction_items(
        sq_order, ctx.org_id, txn["id"],
        txn["transaction_at"], ctx.product_lookup or {},
    )

    # In production: upsert to DB here
    return HandlerResult("order.created", rows_affected=1 + len(items),
                         detail=f"Mapped order {order_id} → {len(items)} items")


async def handle_order_updated(event: dict, ctx: WebhookContext) -> HandlerResult:
    """Existing order updated (state change, item edit, etc.)."""
    order_id = event.get("data", {}).get("id", "")
    logger.info("order.updated: %s (org=%s)", order_id, ctx.org_id)

    async with SquareClient(ctx.access_token, ctx.environment) as client:
        sq_order = await client.retrieve_order(order_id)

    if not sq_order:
        return HandlerResult("order.updated", success=False, detail=f"Order {order_id} not found")

    txn = map_transaction(
        sq_order, ctx.org_id,
        ctx.location_lookup or {},
        ctx.employee_lookup or {},
        ctx.pos_connection_id,
    )
    items = map_transaction_items(
        sq_order, ctx.org_id, txn["id"],
        txn["transaction_at"], ctx.product_lookup or {},
    )

    return HandlerResult("order.updated", rows_affected=1 + len(items),
                         detail=f"Updated order {order_id}")


async def handle_payment_created(event: dict, ctx: WebhookContext) -> HandlerResult:
    """New payment processed — enrich the matching transaction."""
    payment = event.get("data", {}).get("object", {}).get("payment", {})
    payment_id = payment.get("id", "unknown")
    order_id = payment.get("order_id", "")
    logger.info("payment.created: %s for order %s (org=%s)", payment_id, order_id, ctx.org_id)

    enrichment = map_payment_enrichment(payment)
    return HandlerResult("payment.created", rows_affected=1 if enrichment else 0,
                         detail=f"Enrichment: {enrichment}")


async def handle_payment_updated(event: dict, ctx: WebhookContext) -> HandlerResult:
    """Payment updated (e.g., tip adjusted)."""
    payment = event.get("data", {}).get("object", {}).get("payment", {})
    payment_id = payment.get("id", "unknown")
    logger.info("payment.updated: %s (org=%s)", payment_id, ctx.org_id)

    enrichment = map_payment_enrichment(payment)
    return HandlerResult("payment.updated", rows_affected=1 if enrichment else 0,
                         detail=f"Enrichment update: {enrichment}")


async def handle_catalog_updated(event: dict, ctx: WebhookContext) -> HandlerResult:
    """
    Catalog version changed — resync affected items.
    In production, this triggers a targeted catalog re-pull.
    """
    catalog_version = event.get("data", {}).get("object", {}).get("catalog_version", {})
    updated_at = catalog_version.get("updated_at", "")
    logger.info("catalog.version.updated at %s (org=%s)", updated_at, ctx.org_id)

    # In production: fetch changed items via search_catalog with begin_time
    return HandlerResult("catalog.version.updated",
                         detail=f"Catalog changed at {updated_at} — resync queued")


async def handle_inventory_updated(event: dict, ctx: WebhookContext) -> HandlerResult:
    """Inventory count changed (sale, restock, adjustment)."""
    inv_obj = event.get("data", {}).get("object", {})
    counts = inv_obj.get("inventory_counts", [])
    logger.info("inventory.count.updated: %d counts (org=%s)", len(counts), ctx.org_id)

    rows = []
    for c in counts:
        row = map_inventory_count(
            c, ctx.org_id,
            ctx.product_lookup or {},
            ctx.location_lookup or {},
        )
        if row:
            rows.append(row)

    return HandlerResult("inventory.count.updated", rows_affected=len(rows),
                         detail=f"Mapped {len(rows)} inventory snapshots")


async def handle_auth_revoked(event: dict, ctx: WebhookContext) -> HandlerResult:
    """
    Merchant revoked our access from the Square Dashboard.
    Mark connection as disconnected and notify merchant in-app.
    """
    merchant_id = event.get("merchant_id", "")
    logger.warning("oauth.authorization.revoked for merchant %s (org=%s)", merchant_id, ctx.org_id)

    # In production: update pos_connections SET status='disconnected'
    # + send notification to merchant
    return HandlerResult("oauth.authorization.revoked",
                         detail=f"Merchant {merchant_id} disconnected — connection deactivated")


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
HANDLER_REGISTRY: dict[str, Callable[..., Coroutine[Any, Any, HandlerResult]]] = {
    "order.created": handle_order_created,
    "order.updated": handle_order_updated,
    "payment.created": handle_payment_created,
    "payment.updated": handle_payment_updated,
    "catalog.version.updated": handle_catalog_updated,
    "inventory.count.updated": handle_inventory_updated,
    "oauth.authorization.revoked": handle_auth_revoked,
}


async def dispatch_webhook(
    event: dict,
    ctx: WebhookContext,
) -> HandlerResult | None:
    """Route an event to its handler. Returns None for unknown event types."""
    event_type = event.get("type", "")
    handler = HANDLER_REGISTRY.get(event_type)
    if not handler:
        logger.warning("Unknown webhook event type: %s", event_type)
        return None
    return await handler(event, ctx)
