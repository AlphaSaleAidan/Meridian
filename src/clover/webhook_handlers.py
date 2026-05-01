"""
Clover Webhook Handlers — Process real-time events from Clover.

Clover sends webhooks for:
  - ORDER (create, update, delete)
  - ITEM (create, update, delete)
  - INVENTORY (update)
  - MERCHANT (disconnect)

Clover webhooks are simpler than Square:
  - Payload: {appId, merchants: {merchant_id: [{type, objectId, ts}]}}
  - No full object in payload — always need to re-fetch from API
  - HMAC-SHA256 signed with app secret

All handlers are async and designed to be enqueued (respond 200 first, process later).
"""
import hashlib
import hmac
import logging
from typing import Any, Callable

from .client import CloverClient
from .mappers import CloverDataMapper

logger = logging.getLogger("meridian.clover.webhooks")


def verify_webhook_signature(
    body: bytes,
    signature: str,
    app_secret: str,
) -> bool:
    """
    Verify Clover webhook HMAC-SHA256 signature.

    Clover signs the raw body with the app secret.
    """
    expected = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


class CloverWebhookProcessor:
    """
    Processes Clover webhook events.

    Usage:
        processor = CloverWebhookProcessor(
            get_connection=my_db_lookup,
            upsert_transaction=my_db_upsert,
        )

        # Called from FastAPI webhook endpoint
        await processor.handle(merchant_id, events)
    """

    def __init__(
        self,
        get_connection: Callable | None = None,
        upsert_transaction: Callable | None = None,
        upsert_catalog: Callable | None = None,
        upsert_inventory: Callable | None = None,
        disconnect_merchant: Callable | None = None,
        send_notification: Callable | None = None,
    ):
        self._get_connection = get_connection
        self._upsert_transaction = upsert_transaction
        self._upsert_catalog = upsert_catalog
        self._upsert_inventory = upsert_inventory
        self._disconnect_merchant = disconnect_merchant
        self._send_notification = send_notification

        self._handlers: dict[str, Callable] = {
            "CREATE": self._handle_create,
            "UPDATE": self._handle_update,
            "DELETE": self._handle_delete,
        }

    async def handle(
        self,
        merchant_id: str,
        events: list[dict],
        connection: dict | None = None,
    ) -> list[dict[str, Any]]:
        """
        Process a batch of Clover webhook events for one merchant.

        Clover batches events: {merchants: {MID: [{type, objectId, ts}]}}

        Args:
            merchant_id: Clover merchant ID
            events: List of {type: "CREATE|UPDATE|DELETE", objectId: "xxx", ts: 1234}
            connection: DB connection record (access_token, org_id, etc.)

        Returns list of results (one per event).
        """
        results = []

        for event in events:
            event_type = event.get("type", "").upper()
            object_id = event.get("objectId", "")

            # Determine entity type from objectId prefix or event context
            # Clover object IDs encode their type in the webhook subscription
            # The webhook payload groups by type based on subscription

            try:
                result = await self._dispatch_event(
                    event_type=event_type,
                    object_id=object_id,
                    merchant_id=merchant_id,
                    connection=connection,
                    raw_event=event,
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Event handler failed: {event_type} {object_id}: {e}", exc_info=True)
                results.append({"action": "error", "object_id": object_id, "error": str(e)})

        return results

    async def _dispatch_event(
        self,
        event_type: str,
        object_id: str,
        merchant_id: str,
        connection: dict | None,
        raw_event: dict,
    ) -> dict:
        """Route event to handler based on type."""
        # Clover organizes webhooks by subscription type
        # We need the "verificationCode" to determine entity
        entity_type = raw_event.get("_entity_type", "")  # Set during parsing

        if entity_type == "ORDER" or "/orders/" in object_id:
            return await self._handle_order_event(event_type, object_id, merchant_id, connection)
        elif entity_type == "ITEM" or "/items/" in object_id:
            return await self._handle_item_event(event_type, object_id, merchant_id, connection)
        elif entity_type == "INVENTORY":
            return await self._handle_inventory_event(object_id, merchant_id, connection)
        elif entity_type == "APP" and event_type == "DELETE":
            return await self._handle_disconnect(merchant_id, connection)
        else:
            handler = self._handlers.get(event_type)
            if handler:
                return await handler(object_id, merchant_id, connection, raw_event)
            return {"action": "ignored", "reason": f"Unhandled: {entity_type}/{event_type}"}

    # ─── Order Handlers ───────────────────────────────────────

    async def _handle_order_event(
        self,
        event_type: str,
        order_id: str,
        merchant_id: str,
        connection: dict | None,
    ) -> dict:
        """Handle order CREATE/UPDATE — fetch full order and upsert."""
        if not connection:
            return {"action": "skipped", "reason": "No connection"}

        if event_type == "DELETE":
            # Mark transaction as voided
            return {"action": "order_deleted", "order_id": order_id}

        client = CloverClient(
            access_token=connection.get("access_token", ""),
            merchant_id=merchant_id,
        )
        mapper = self._build_mapper(connection)

        try:
            order = await client.get_order(order_id)
        except Exception as e:
            logger.error(f"Failed to fetch order {order_id}: {e}")
            return {"action": "error", "error": str(e)}
        finally:
            await client.close()

        txn = mapper.map_order_to_transaction(order)
        items = []
        for li in order.get("lineItems", {}).get("elements", []):
            li_row = mapper.map_line_item(li, txn["id"], txn["transaction_time"])
            items.append(li_row)

        if self._upsert_transaction:
            await self._upsert_transaction(txn, items)

        return {
            "action": "order_upserted",
            "transaction_id": txn["id"],
            "items_count": len(items),
            "total_cents": txn["total_cents"],
        }

    # ─── Item (Product) Handlers ──────────────────────────────

    async def _handle_item_event(
        self,
        event_type: str,
        item_id: str,
        merchant_id: str,
        connection: dict | None,
    ) -> dict:
        """Handle item CREATE/UPDATE — fetch and upsert product."""
        if not connection:
            return {"action": "skipped", "reason": "No connection"}

        if event_type == "DELETE":
            return {"action": "item_deleted", "item_id": item_id}

        client = CloverClient(
            access_token=connection.get("access_token", ""),
            merchant_id=merchant_id,
        )

        try:
            item = await client._get(f"/items/{item_id}", params={"expand": "categories,tags"})
        except Exception as e:
            logger.error(f"Failed to fetch item {item_id}: {e}")
            return {"action": "error", "error": str(e)}
        finally:
            await client.close()

        mapper = self._build_mapper(connection)
        product = mapper.map_product(item)

        if self._upsert_catalog:
            await self._upsert_catalog([], [product])

        return {
            "action": "item_upserted",
            "product_id": product["id"],
            "name": product["name"],
        }

    # ─── Inventory Handler ────────────────────────────────────

    async def _handle_inventory_event(
        self,
        object_id: str,
        merchant_id: str,
        connection: dict | None,
    ) -> dict:
        """Handle inventory update — fetch current stock and snapshot."""
        if not connection:
            return {"action": "skipped", "reason": "No connection"}

        client = CloverClient(
            access_token=connection.get("access_token", ""),
            merchant_id=merchant_id,
        )
        mapper = self._build_mapper(connection)

        try:
            stocks = await client.list_item_stocks()
        except Exception as e:
            logger.error(f"Failed to fetch inventory: {e}")
            return {"action": "error", "error": str(e)}
        finally:
            await client.close()

        snapshots = [mapper.map_item_stock(s) for s in stocks]

        if self._upsert_inventory and snapshots:
            await self._upsert_inventory(snapshots)

        return {
            "action": "inventory_updated",
            "snapshots": len(snapshots),
        }

    # ─── Disconnect Handler ───────────────────────────────────

    async def _handle_disconnect(
        self,
        merchant_id: str,
        connection: dict | None,
    ) -> dict:
        """Merchant uninstalled the app — mark disconnected, notify."""
        if self._disconnect_merchant and connection:
            await self._disconnect_merchant(connection.get("id"))

        if self._send_notification and connection:
            await self._send_notification(
                org_id=connection.get("org_id"),
                title="Clover Disconnected",
                body=(
                    "Your Clover POS connection was removed. "
                    "Please reconnect in Settings to continue receiving insights."
                ),
                priority="urgent",
            )

        return {
            "action": "disconnected",
            "merchant_id": merchant_id,
        }

    # ─── Generic Handlers ─────────────────────────────────────

    async def _handle_create(self, object_id, merchant_id, connection, raw_event):
        return {"action": "generic_create", "object_id": object_id}

    async def _handle_update(self, object_id, merchant_id, connection, raw_event):
        return {"action": "generic_update", "object_id": object_id}

    async def _handle_delete(self, object_id, merchant_id, connection, raw_event):
        return {"action": "generic_delete", "object_id": object_id}

    # ─── Helpers ──────────────────────────────────────────────

    def _build_mapper(self, connection: dict) -> CloverDataMapper:
        """Build a CloverDataMapper from connection context."""
        return CloverDataMapper(
            org_id=connection.get("org_id", ""),
            location_id=connection.get("_location_id"),
            product_lookup=connection.get("_product_lookup", {}),
            category_lookup=connection.get("_category_lookup", {}),
            employee_cache=connection.get("_employee_cache", {}),
            pos_connection_id=connection.get("id"),
        )
