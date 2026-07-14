"""
Website Order → POS Dispatch — pushes a completed mobile/website food order
into the merchant's connected POS so the kitchen gets a normal ticket with a
"Meridian Mobile Order" tag and the notes they need to make it.

Runs after the order row is safely stored in website_orders: a POS failure
never loses the order or breaks the customer's confirmation — the outcome is
recorded on the row (pos_status / pos_order_id / pos_error, migration 039)
and the order stays visible in the merchant dashboard either way.

Clover goes through the dedicated clover_kitchen submitter (tagged order +
line items + kitchen print event). Other connected systems reuse the generic
order dispatcher with the tag folded into the order notes.
"""
import logging
import os
from datetime import datetime, timezone

from .clover_kitchen import submit_clover_kitchen_order
from .order_dispatcher import create_pos_order
from .registry import get_connector_config, resolve_alias

logger = logging.getLogger("meridian.pos.website_dispatch")

SOURCE_TAG = "Meridian Mobile Order"


async def dispatch_website_order_to_pos(order_row: dict) -> dict:
    """Best-effort push of a stored website_orders row into the merchant's
    POS. Returns {dispatched, pos_system?, pos_order_id?, reason?} and
    records the outcome on the row. Never raises."""
    order_id = order_row.get("id", "")
    merchant_id = order_row.get("merchant_id", "")
    try:
        result = await _dispatch(order_row, merchant_id)
    except Exception as e:  # noqa: BLE001 — POS push must never take down ordering
        logger.error("website order %s: POS dispatch error: %s", order_id, e)
        result = {"dispatched": False, "reason": str(e)[:200]}

    await _record_outcome(order_id, result)
    return result


async def _dispatch(order_row: dict, merchant_id: str) -> dict:
    # Same killswitch the phone path honors — one env var stops all
    # Meridian-originated POS writes.
    if os.environ.get("POS_ORDERS_DISABLED", "").strip() in ("1", "true", "yes"):
        return {"dispatched": False, "reason": "pos_orders_disabled"}

    conn = await _resolve_connection(merchant_id)
    if not conn:
        return {"dispatched": False, "reason": "no_pos_connection"}

    system_key = resolve_alias(conn["system"])
    order_id = order_row.get("id", "")

    if system_key == "clover":
        result = await submit_clover_kitchen_order(
            access_token=conn["token"],
            external_merchant_id=conn["external_merchant_id"],
            order={**order_row, "order_ref": order_id},
            source_tag=SOURCE_TAG,
        )
        if result.get("success"):
            logger.info(
                "website order %s → clover order %s (kitchen print %s)",
                order_id, result.get("pos_order_id"),
                "fired" if result.get("kitchen_print_fired") else "NOT fired",
            )
            return {
                "dispatched": True,
                "pos_system": "clover",
                "pos_order_id": result.get("pos_order_id", ""),
                "kitchen_print_fired": result.get("kitchen_print_fired", False),
            }
        return {
            "dispatched": False,
            "pos_system": "clover",
            "reason": result.get("reason", "clover_error"),
        }

    # Non-Clover systems: reuse the generic dispatcher; the tag rides in the
    # order-level notes so it still shows on the ticket.
    pos_config = _build_pos_config(system_key, conn)
    if pos_config is None:
        return {"dispatched": False, "reason": f"unsupported_system:{system_key}"}

    tag_note = f"{SOURCE_TAG} #{order_id[:8].upper()} — {order_row.get('customer_name', '')}"
    existing_notes = (order_row.get("special_instructions") or "").strip()
    order_data = {
        "customer_name": order_row.get("customer_name", ""),
        "order_type": order_row.get("order_type", "pickup"),
        "items": order_row.get("items", []),
        "special_instructions": f"{tag_note}. {existing_notes}".strip(". "),
        "source": "meridian_mobile_order",
    }
    result = await create_pos_order(system_key, order_data, config=pos_config)
    if result.success and not result.fallback_used:
        return {
            "dispatched": True,
            "pos_system": system_key,
            "pos_order_id": result.order_id or "",
        }
    return {
        "dispatched": False,
        "pos_system": system_key,
        "reason": result.fallback_reason or "pos_error",
    }


async def _resolve_connection(merchant_id: str) -> dict | None:
    """Newest connected pos_connections row for this org, with a decrypted
    token. Mirrors phone.py's order-time resolution (merchant_id IS org_id)."""
    if not merchant_id:
        return None
    from ...db import get_db

    db = get_db()
    conns = await db.select(
        "pos_connections",
        filters={"org_id": f"eq.{merchant_id}", "status": "eq.connected"},
        order="updated_at.desc",
        limit=1,
    )
    if not conns:
        return None
    conn = conns[0]
    token = _connection_token(conn)
    system = (conn.get("provider") or "").strip()
    if not (token and system):
        return None
    return {
        "system": system,
        "token": token,
        "external_merchant_id": (conn.get("external_merchant_id") or "").strip(),
        "location_id": (conn.get("external_location_id") or "").strip(),
    }


def _connection_token(conn: dict) -> str:
    # Lazy import: phone_dashboard is an api.routes module and this is a
    # service — importing at call time keeps module import acyclic.
    from ...api.routes.phone_dashboard import _decrypt_connection_token

    return (_decrypt_connection_token(conn) or "").strip()


def _build_pos_config(system_key: str, conn: dict):
    from .base import POSConnectionConfig

    api_config = get_connector_config(system_key)
    if not api_config or not api_config.get("supports_orders"):
        return None
    return POSConnectionConfig(
        system_key=system_key,
        system_name=api_config.get("system_name") or system_key,
        tier=api_config.get("tier", 1),
        auth_method=api_config.get("auth_type", "bearer"),
        base_url=api_config.get("base_url", ""),
        credentials={
            "access_token": conn["token"],
            "merchant_id": conn["external_merchant_id"],
            "location_id": conn["location_id"],
        },
        merchant_id=conn["external_merchant_id"],
        category=api_config.get("category", "restaurant"),
        supports_order_creation=True,
        order_creation_endpoint=api_config.get("order_create_endpoint", ""),
    )


async def _record_outcome(order_id: str, result: dict) -> None:
    """Persist the POS outcome on the website_orders row. Columns ship in
    migration 039; tolerate their absence so deploys don't order-depend on
    the migration."""
    if not order_id:
        return
    try:
        from ...db import get_db

        db = get_db()
        update: dict = {
            "pos_status": "sent" if result.get("dispatched") else (
                "skipped" if result.get("reason") in ("no_pos_connection", "pos_orders_disabled")
                else "failed"
            ),
        }
        if result.get("pos_order_id"):
            update["pos_order_id"] = result["pos_order_id"]
        if result.get("dispatched"):
            update["pos_sent_at"] = datetime.now(timezone.utc).isoformat()
        elif result.get("reason"):
            update["pos_error"] = str(result["reason"])[:500]
        await db.update("website_orders", update, {"id": f"eq.{order_id}"})
    except Exception as e:  # noqa: BLE001 — pre-migration schema or transient DB error
        logger.warning("website order %s: could not record POS outcome: %s", order_id, e)
