"""
Square Webhook Handlers â Process real-time events from Square.

Square sends webhooks for:
  - order.created / order.updated
  - payment.created / payment.updated
  - catalog.version.updated
  - inventory.count.updated
  - oauth.authorization.revoked

All handlers are async and designed to be enqueued (respond 200 first, process later).
"""
import base64
import hashlib
import hmac
import logging
import time
from typing import Any, Callable

from .client import SquareClient
from .mappers import DataMapper
from src.security.encryption import decrypt_token

logger = logging.getLogger("meridian.square.webhooks")


def verify_webhook_signature(
    body: bytes,
    signature: str,
    signature_key: str,
    notification_url: str,
) -> bool:
    """
    Verify Square webhook HMAC-SHA256 signature.
    
    Square signs: notification_url + raw_body
    Then base64 encodes the HMAC.
    """
    combined = notification_url.encode("utf-8") + body
    expected = hmac.new(
        key=signature_key.encode("utf-8"),
        msg=combined,
        digestmod=hashlib.sha256,
    ).digest()
    expected_b64 = base64.b64encode(expected).decode("utf-8")

    return hmac.compare_digest(expected_b64, signature)


class WebhookProcessor:
    """
    Processes Square webhook events.
    
    Usage:
        processor = WebhookProcessor(
            get_connection=my_db_lookup,
            upsert_transaction=my_db_upsert,
        )
        
        await processor.handle(event_type, event_data, merchant_id)
    """

    # In-process webhook dedupe window. NOTE: this only dedupes within a
    # single process — a DB-backed `webhook_events` table (insert-or-conflict
    # on event_id) is needed for dedupe across restarts/workers; no such
    # table exists yet (requires a migration).
    DEDUPE_TTL_SECONDS = 24 * 60 * 60
    DEDUPE_MAX_ENTRIES = 50_000

    def __init__(
        self,
        get_connection: Callable | None = None,
        upsert_transaction: Callable | None = None,
        upsert_catalog: Callable | None = None,
        upsert_inventory: Callable | None = None,
        disconnect_merchant: Callable | None = None,
        send_notification: Callable | None = None,
    ):
        """
        Inject database/notification callbacks.
        In production, these would be bound to your Supabase client.
        """
        self._get_connection = get_connection
        self._upsert_transaction = upsert_transaction
        self._upsert_catalog = upsert_catalog
        self._upsert_inventory = upsert_inventory
        self._disconnect_merchant = disconnect_merchant
        self._send_notification = send_notification

        # event_id → first-seen unix timestamp (insertion-ordered, oldest first)
        self._seen_events: dict[str, float] = {}

        self._handlers: dict[str, Callable] = {
            "order.created": self._handle_order_created,
            "order.updated": self._handle_order_updated,
            "payment.created": self._handle_payment_created,
            "payment.updated": self._handle_payment_updated,
            "catalog.version.updated": self._handle_catalog_updated,
            "inventory.count.updated": self._handle_inventory_updated,
            "oauth.authorization.revoked": self._handle_auth_revoked,
        }

    async def is_duplicate(self, event_id: str) -> bool:
        """
        Check whether this webhook event_id was already seen, and mark it seen.

        In-process bounded TTL set: entries expire after DEDUPE_TTL_SECONDS
        and the set is capped at DEDUPE_MAX_ENTRIES (oldest evicted first).
        """
        now = time.time()

        # Prune expired entries from the front (insertion order == time order)
        while self._seen_events:
            oldest_id = next(iter(self._seen_events))
            if now - self._seen_events[oldest_id] <= self.DEDUPE_TTL_SECONDS:
                break
            del self._seen_events[oldest_id]

        if event_id in self._seen_events:
            return True

        # Enforce size cap — evict oldest
        while len(self._seen_events) >= self.DEDUPE_MAX_ENTRIES:
            del self._seen_events[next(iter(self._seen_events))]

        self._seen_events[event_id] = now
        return False

    async def handle(
        self,
        event_type: str,
        event: dict,
        connection: dict | None = None,
    ) -> dict[str, Any]:
        """
        Dispatch webhook event to appropriate handler.
        
        Returns a result dict with action taken.
        """
        handler = self._handlers.get(event_type)
        if not handler:
            logger.info(f"Unhandled webhook event type: {event_type}")
            return {"action": "ignored", "reason": f"Unhandled event type: {event_type}"}

        try:
            result = await handler(event, connection)
            logger.info(f"Webhook {event_type} processed: {result}")
            return result
        except Exception as e:
            logger.error(f"Webhook {event_type} handler failed: {e}", exc_info=True)
            return {"action": "error", "error": str(e)}

    # âââ Order Handlers âââââââââââââââââââââââââââââââââââââââ

    async def _handle_order_created(
        self, event: dict, connection: dict | None
    ) -> dict:
        """New order â fetch full details and insert."""
        order_id = event.get("data", {}).get("id")
        if not order_id or not connection:
            return {"action": "skipped", "reason": "Missing order_id or connection"}

        access_token = decrypt_token(connection.get("access_token_enc", ""))
        client = SquareClient(access_token=access_token)
        mapper = self._build_mapper(connection)

        # Fetch full order (webhook only has summary)
        try:
            resp = await client.get(f"/v2/orders/{order_id}")
            order = resp.get("order", {})
        finally:
            await client.close()

        if not order:
            return {"action": "skipped", "reason": "Order not found"}

        txn = mapper.map_transaction(order)
        items = mapper.map_transaction_items(order, txn["id"], txn["transaction_at"])

        if self._upsert_transaction:
            await self._upsert_transaction(txn, items)

        return {
            "action": "inserted",
            "transaction_id": txn["id"],
            "items_count": len(items),
            "total_cents": txn["total_cents"],
        }

    async def _handle_order_updated(
        self, event: dict, connection: dict | None
    ) -> dict:
        """Order updated â re-fetch and upsert (same logic as created)."""
        return await self._handle_order_created(event, connection)

    # âââ Payment Handlers âââââââââââââââââââââââââââââââââââââ

    async def _handle_payment_created(
        self, event: dict, connection: dict | None
    ) -> dict:
        """Payment created â enrich corresponding transaction with card details.

        NOTE: this webhook fires for every customer purchase on a connected
        merchant's POS. Rep commissions accrue on Meridian SUBSCRIPTION
        payments only, so the commission hook (on_payment_received) must NOT
        be triggered here â it belongs in the billing-side payment
        confirmation flow.
        """
        return await self._enrich_payment(event, connection)

    async def _handle_payment_updated(
        self, event: dict, connection: dict | None
    ) -> dict:
        """Payment updated â re-enrich transaction."""
        return await self._enrich_payment(event, connection)

    async def _enrich_payment(
        self, event: dict, connection: dict | None
    ) -> dict:
        """Common payment enrichment logic."""
        payment_id = (event.get("data", {}).get("object", {})
                      .get("payment", {}).get("id"))
        if not payment_id or not connection:
            return {"action": "skipped", "reason": "Missing payment_id or connection"}

        access_token = decrypt_token(connection.get("access_token_enc", ""))
        client = SquareClient(access_token=access_token)
        mapper = self._build_mapper(connection)

        try:
            payment = await client.get_payment(payment_id)
        finally:
            await client.close()

        enrichment = mapper.map_payment_enrichment(payment)
        
        # In production: UPDATE transactions SET ... WHERE external_id = order_id
        return {
            "action": "enriched",
            "order_id": enrichment.get("_order_id"),
            "fields_updated": list(enrichment.get("metadata_updates", {}).keys()),
        }

    # âââ Catalog Handler ââââââââââââââââââââââââââââââââââââââ

    async def _handle_catalog_updated(
        self, event: dict, connection: dict | None
    ) -> dict:
        """Catalog changed â resync affected items."""
        if not connection:
            return {"action": "skipped", "reason": "No connection"}

        access_token = decrypt_token(connection.get("access_token_enc", ""))
        client = SquareClient(access_token=access_token)
        mapper = self._build_mapper(connection)

        try:
            # Fetch recently updated catalog objects
            updated_at = (event.get("data", {}).get("object", {})
                         .get("catalog_version", {}).get("updated_at"))
            
            objects = await client.list_all_catalog(
                types=["ITEM", "ITEM_VARIATION", "CATEGORY"]
            )
        finally:
            await client.close()

        categories = [o for o in objects if o.get("type") == "CATEGORY"]
        items = [o for o in objects if o.get("type") == "ITEM"]

        mapped_categories = [mapper.map_category(c) for c in categories]
        mapped_products = []
        for item in items:
            mapped_products.extend(mapper.map_products(item))

        if self._upsert_catalog:
            await self._upsert_catalog(mapped_categories, mapped_products)

        return {
            "action": "catalog_resynced",
            "categories": len(mapped_categories),
            "products": len(mapped_products),
        }

    # âââ Inventory Handler ââââââââââââââââââââââââââââââââââââ

    async def _handle_inventory_updated(
        self, event: dict, connection: dict | None
    ) -> dict:
        """Inventory count changed â upsert snapshot."""
        if not connection:
            return {"action": "skipped", "reason": "No connection"}

        mapper = self._build_mapper(connection)
        
        counts = (event.get("data", {}).get("object", {})
                  .get("inventory_counts", []))
        
        snapshots = []
        for count in counts:
            snapshot = mapper.map_inventory_count(count)
            snapshots.append(snapshot)

        if self._upsert_inventory and snapshots:
            await self._upsert_inventory(snapshots)

        return {
            "action": "inventory_updated",
            "snapshots": len(snapshots),
        }

    # âââ Auth Revocation Handler ââââââââââââââââââââââââââââââ

    async def _handle_auth_revoked(
        self, event: dict, connection: dict | None
    ) -> dict:
        """
        Merchant disconnected us from their Square Dashboard.
        Mark connection as disconnected and notify the merchant.
        """
        merchant_id = event.get("merchant_id", "")
        
        if self._disconnect_merchant and connection:
            await self._disconnect_merchant(connection.get("id"))

        if self._send_notification and connection:
            await self._send_notification(
                org_id=connection.get("org_id"),
                title="Square Disconnected",
                body=(
                    "Your Square POS connection was revoked. "
                    "Please reconnect in Settings to continue receiving insights."
                ),
                priority="urgent",
            )

        return {
            "action": "disconnected",
            "merchant_id": merchant_id,
        }

    # âââ Helpers ââââââââââââââââââââââââââââââââââââââââââââââ

    def _build_mapper(self, connection: dict) -> DataMapper:
        """Build a DataMapper from connection context."""
        return DataMapper(
            org_id=connection.get("org_id", ""),
            location_lookup=connection.get("_location_lookup", {}),
            product_lookup=connection.get("_product_lookup", {}),
            employee_cache=connection.get("_employee_cache", {}),
            pos_connection_id=connection.get("id"),
        )
