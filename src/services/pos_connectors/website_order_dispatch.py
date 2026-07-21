"""
Website Order → POS Dispatch — pushes a PAID mobile/website food order into
the merchant's connected POS so the kitchen gets a normal ticket tagged
"Meridian Mobile Order" with the notes they need to make it.

Routing (every paid order reaches the merchant SOMEWHERE — no silent drops):
  clover (+ bank rebrands) → clover_kitchen: tagged order + line items + print
  square (+ variants)      → square_kitchen: order + fulfillment (KDS/printing)
  other API-capable        → generic REST connector (best effort)
  API failed / CSV-only / no POS connected
                           → SMS (then email) the full kitchen ticket to the
                             merchant's contact from their website record

Runs after the order row is safely stored and (since the pay-first flow) only
once Stripe has confirmed payment: mark_paid_and_dispatch is the webhook
entry. A POS failure never loses the order — the outcome is recorded on the
row (pos_status / pos_order_id / pos_error, migrations 039/040) and the order
stays visible in the merchant dashboard either way.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone

from .clover_kitchen import build_kitchen_note, submit_clover_kitchen_order
from .order_dispatcher import create_pos_order
from .registry import get_connector_config, resolve_alias
from .square_kitchen import submit_square_kitchen_order

logger = logging.getLogger("meridian.pos.website_dispatch")

SOURCE_TAG = "Meridian Mobile Order"

# Strong refs for background dispatch tasks spawned by the payment webhook —
# without them the event loop may garbage-collect a task mid-flight.
_DISPATCH_TASKS: set = set()


async def mark_paid_and_dispatch(website_order_id: str, payment_txn_id: str = "") -> dict:
    """Called by the Stripe Connect webhook when a website order's checkout
    completes: flip the row to paid (idempotently — Stripe retries and the
    payment_intent.succeeded twin both land here), then release the kitchen
    ticket in the background so the webhook answers Stripe fast.

    The status flip IS the idempotency gate: `status=neq.paid` matches once,
    so a second event finds nothing to update and never double-prints."""
    from ...db import get_db

    db = get_db()
    patch = {
        "status": "paid",
        "paid_at": datetime.now(timezone.utc).isoformat(),
    }
    if payment_txn_id:
        patch["stripe_session_id"] = payment_txn_id
    filters = {"id": f"eq.{website_order_id}", "status": "neq.paid"}
    try:
        updated = await db.update("website_orders", patch, filters)
    except Exception as e:  # noqa: BLE001 — pre-migration-040 schema: retry the critical flip alone
        logger.warning("paid-flip full patch failed for %s (%s); retrying status only",
                       website_order_id, e)
        updated = await db.update("website_orders", {"status": "paid"}, filters)

    if not updated:
        logger.info("website order %s already paid/released — duplicate event ignored",
                    website_order_id)
        return {"released": False, "reason": "already_paid_or_missing"}

    row = updated[0]
    task = asyncio.create_task(dispatch_website_order_to_pos(dict(row)))
    _DISPATCH_TASKS.add(task)
    task.add_done_callback(_DISPATCH_TASKS.discard)
    logger.info("website order %s marked PAID → kitchen dispatch released", website_order_id)
    return {"released": True, "order_id": website_order_id}


async def dispatch_website_order_to_pos(order_row: dict) -> dict:
    """Best-effort push of a stored website_orders row into the merchant's
    POS, with a guaranteed SMS/email ticket fallback. Returns
    {dispatched, method?, pos_system?, pos_order_id?, reason?}, records the
    outcome on the row, never raises."""
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
    # Meridian-originated POS writes AND the notify fallback.
    if os.environ.get("POS_ORDERS_DISABLED", "").strip() in ("1", "true", "yes"):
        return {"dispatched": False, "reason": "pos_orders_disabled"}

    conn = await _resolve_connection(merchant_id)
    system_key = resolve_alias(conn["system"]) if conn else ""
    order_id = order_row.get("id", "")

    api_result: dict | None = None
    if conn:
        if system_key == "clover":
            # Map order line items to real Clover inventory itemIds (from the
            # merchant's POS-imported menu) so the sale attributes to real
            # menu items in Clover's reports. Enrichment only — a lookup
            # failure yields {} and every line falls back to freeform.
            item_id_map = await _clover_inventory_map(merchant_id)
            api_result = await submit_clover_kitchen_order(
                access_token=conn["token"],
                external_merchant_id=conn["external_merchant_id"],
                order={**order_row, "order_ref": order_id},
                source_tag=SOURCE_TAG,
                item_id_map=item_id_map,
            )
        elif system_key == "square":
            api_result = await submit_square_kitchen_order(
                access_token=conn["token"],
                location_id=conn["location_id"],
                order={**order_row, "order_ref": order_id},
                source_tag=SOURCE_TAG,
            )
        else:
            api_result = await _generic_api_dispatch(system_key, order_row, conn)

    if api_result and api_result.get("success"):
        logger.info("website order %s → %s order %s", order_id, system_key,
                    api_result.get("pos_order_id"))
        out = {
            "dispatched": True,
            "method": "api",
            "pos_system": system_key,
            "pos_order_id": api_result.get("pos_order_id", ""),
        }
        if "kitchen_print_fired" in api_result:
            out["kitchen_print_fired"] = api_result["kitchen_print_fired"]
        return out

    # Universal fallback: a PAID order must never be stranded. Text (then
    # email) the full kitchen ticket to the merchant's own contact info.
    api_reason = (api_result or {}).get("reason", "") if conn else "no_pos_connection"
    notify = await _notify_merchant(order_row, api_reason)
    if notify.get("delivered"):
        return {
            "dispatched": True,
            "method": notify["method"],
            "pos_system": system_key or "none",
            "pos_order_id": "",
            "delivery_note": f"POS unavailable ({api_reason}); ticket sent via {notify['method']}",
        }
    return {
        "dispatched": False,
        "pos_system": system_key or "none",
        "reason": f"{api_reason}; notify failed: {notify.get('reason', 'no merchant contact')}",
    }


async def _generic_api_dispatch(system_key: str, order_row: dict, conn: dict) -> dict:
    """Non-Clover/Square API systems: best effort via the generic REST
    connector. Merchant contact is deliberately NOT passed here — its internal
    SMS/email fallback would race ours; we own the notify path."""
    api_config = get_connector_config(system_key)
    if not api_config or not api_config.get("supports_orders") \
            or api_config.get("auth_type") == "csv_only":
        return {"success": False, "reason": f"no_order_api:{system_key}"}

    pos_config = _build_pos_config(system_key, conn, api_config)
    paid = order_row.get("status") == "paid"
    tag_note = f"{SOURCE_TAG} #{order_row.get('id', '')[:8].upper()} — {order_row.get('customer_name', '')}"
    if paid:
        tag_note = f"{tag_note} — PAID ONLINE, do not collect"
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
        return {"success": True, "pos_order_id": result.order_id or ""}
    return {"success": False, "reason": result.fallback_reason or "pos_error"}


async def _notify_merchant(order_row: dict, api_reason: str) -> dict:
    """Deliver the full kitchen ticket to the merchant by SMS, then email.
    Contact comes from their website record (phone/email shown on the site),
    falling back to phone_agent_config."""
    contact = await _merchant_contact(order_row)
    if not (contact["phone"] or contact["email"]):
        return {"delivered": False, "reason": "no_merchant_contact"}

    ticket = build_kitchen_note(order_row, SOURCE_TAG)
    header = f"🍽 NEW PAID MOBILE ORDER — {contact['name'] or 'your restaurant'}"
    if api_reason and api_reason != "no_pos_connection":
        header += "\n(POS delivery failed — ticket below; also in your Meridian dashboard)"
    else:
        header += "\n(ticket below; also in your Meridian dashboard)"
    body = f"{header}\n\n{ticket}"

    if contact["phone"]:
        try:
            from ...sms.client import send_sms

            res = await send_sms(contact["phone"], body)
            if res.get("sent"):
                return {"delivered": True, "method": "sms"}
            logger.warning("mobile-order SMS notify failed: %s", res.get("reason"))
        except Exception as e:  # noqa: BLE001 — fall through to email
            logger.warning("mobile-order SMS notify error: %s", e)

    if contact["email"]:
        try:
            from ...email.postal_client import PostalClient

            html = "<pre style='font-size:14px;line-height:1.5'>" + (
                body.replace("&", "&amp;").replace("<", "&lt;")) + "</pre>"
            res = await PostalClient().send(
                to=contact["email"],
                subject=f"New PAID mobile order — {order_row.get('customer_name', 'customer')}",
                html=html,
                tag="mobile-order",
            )
            if res.get("status") in ("sent", "queued") or res.get("id"):
                return {"delivered": True, "method": "email"}
            logger.warning("mobile-order email notify failed: %s", res)
        except Exception as e:  # noqa: BLE001
            logger.warning("mobile-order email notify error: %s", e)

    return {"delivered": False, "reason": "sms_and_email_failed"}


async def _merchant_contact(order_row: dict) -> dict:
    from ...db import get_db

    db = get_db()
    phone = email = name = ""
    try:
        website_id = order_row.get("website_id", "")
        if website_id:
            rows = await db.select(
                "merchant_websites", "phone,email,business_name",
                filters={"id": f"eq.{website_id}"}, limit=1,
            )
            if rows:
                phone = (rows[0].get("phone") or "").strip()
                email = (rows[0].get("email") or "").strip()
                name = (rows[0].get("business_name") or "").strip()
        if not (phone or email):
            rows = await db.select(
                "phone_agent_config", "merchant_phone,merchant_email,business_name",
                filters={"merchant_id": f"eq.{order_row.get('merchant_id', '')}"}, limit=1,
            )
            if rows:
                phone = phone or (rows[0].get("merchant_phone") or "").strip()
                email = email or (rows[0].get("merchant_email") or "").strip()
                name = name or (rows[0].get("business_name") or "").strip()
    except Exception as e:  # noqa: BLE001 — no contact just means notify can't deliver
        logger.warning("merchant contact lookup failed: %s", e)
    return {"phone": phone, "email": email, "name": name}


async def _clover_inventory_map(merchant_id: str) -> dict:
    """{lower(name): clover_item_id} from the merchant's POS-imported menu, for
    booking order line items against real Clover inventory. Best-effort: any
    failure (or no store rows) returns {} so the order dispatches with freeform
    line items exactly as before — mapping never blocks an order."""
    if not merchant_id:
        return {}
    try:
        from ...db import get_db
        from ...services.menu_store import get_pos_item_id_map

        return await get_pos_item_id_map(get_db(), merchant_id)
    except Exception as e:  # noqa: BLE001 — enrichment only, never a dispatch gate
        logger.warning("clover inventory map lookup failed for %s: %s", merchant_id, e)
        return {}


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
    token = await _connection_token(conn)
    system = (conn.get("provider") or "").strip()
    if not (token and system):
        return None
    return {
        "system": system,
        "token": token,
        "external_merchant_id": (conn.get("external_merchant_id") or "").strip(),
        "location_id": (conn.get("external_location_id") or "").strip(),
    }


async def _connection_token(conn: dict) -> str:
    # Lazy import: phone_dashboard is an api.routes module and this is a
    # service — importing at call time keeps module import acyclic.
    # _fresh_connection_token refreshes expiring Clover v2 (1-click OAuth)
    # tokens inline; all other providers/shapes get the stored token.
    from ...api.routes.phone_dashboard import _fresh_connection_token

    return (await _fresh_connection_token(conn) or "").strip()


def _build_pos_config(system_key: str, conn: dict, api_config: dict):
    from .base import POSConnectionConfig

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
                "skipped" if result.get("reason") == "pos_orders_disabled" else "failed"
            ),
        }
        if result.get("pos_order_id"):
            update["pos_order_id"] = result["pos_order_id"]
        if result.get("dispatched"):
            update["pos_sent_at"] = datetime.now(timezone.utc).isoformat()
            if result.get("delivery_note"):
                update["pos_error"] = result["delivery_note"][:500]
        elif result.get("reason"):
            update["pos_error"] = str(result["reason"])[:500]
        await db.update("website_orders", update, {"id": f"eq.{order_id}"})
    except Exception as e:  # noqa: BLE001 — pre-migration schema or transient DB error
        logger.warning("website order %s: could not record POS outcome: %s", order_id, e)
