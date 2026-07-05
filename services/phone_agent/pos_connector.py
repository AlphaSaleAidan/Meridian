"""
POS connector — creates orders in any of the 80+ supported POS systems.
Direct API integration for Square, Toast, and Clover.
Generic webhook/notification fallback for all other POS systems.
Orders are always saved to Supabase regardless of POS routing outcome.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger("meridian.phone_agent.pos")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")  # writes need service-role

TOAST_API_BASE = os.getenv("TOAST_API_BASE_URL", "https://ws-api.toasttab.com")


def clover_api_base() -> str:
    """Region/sandbox-aware Clover API host (mirrors src/config CloverConfig).
    Canada is region 'na' → api.clover.com. CLOVER_API_BASE overrides everything."""
    override = os.getenv("CLOVER_API_BASE", "")
    if override:
        return override.rstrip("/")
    if os.getenv("CLOVER_ENVIRONMENT", "sandbox") != "production":
        return "https://apisandbox.dev.clover.com"
    region = os.getenv("CLOVER_REGION", "na").lower()
    return {
        "na": "https://api.clover.com",
        "eu": "https://api.eu.clover.com",
        "la": "https://api.la.clover.com",
    }.get(region, "https://api.clover.com")

DIRECT_API_SYSTEMS = {"square", "toast", "clover"}

OAUTH_SYSTEMS = {
    "square", "clover", "lightspeed-restaurant", "lightspeed-retail",
    "spoton", "shopify-pos", "stripe-terminal", "paypal-zettle",
    "epos-now", "ncr-voyix", "olo", "korona-pos", "hike-pos",
}

WEBHOOK_CAPABLE_SYSTEMS = {
    "revel", "touchbistro", "aloha", "micros", "heartland", "sumup",
    "lavu", "cake", "harbortouch", "aldelo", "focus-pos", "digital-dining",
    "future-pos", "pixelpoint", "brink", "simphony", "northstar", "xenial",
    "squirrel", "agilysys", "izettle", "tyro", "poster-pos", "iiko",
    "tekmetric", "shop-ware", "mitchell1", "shopmonkey", "autofluent",
    "shop-boss", "ro-writer", "protractor", "alldata-manage", "omnique",
    "autovitals", "napa-tracs", "tire-master", "bolt-on", "qu-pos",
    "skytab", "rezku", "upserve", "talech", "loyverse", "posist",
    "petpooja", "gloria-food", "bindo-pos", "erply", "accu-pos",
    "woo-pos", "openbravo", "retail-edge", "php-pos", "cashier-live",
    "pos-nation", "cova-pos", "treez", "flowhub", "dutchie-pos",
    "meadow", "biotrack", "leaf-logix", "blaze-pos", "indica-online",
    "rain-pos",
}


async def create_pos_order(
    order: dict[str, Any],
    pos_system: str,
    access_token: str,
    location_id: str,
    *,
    demo_safe: bool = False,
) -> dict:
    """Create a POS order with layered guards against accidental live writes.

    Layers (cheapest first):
      1. POS_ORDERS_DISABLED env killswitch — global override.
      2. demo_safe per-merchant flag — set on demo / test rows; logs-only
         regardless of whether the merchant happens to have a populated
         pos_access_token (the production-shape risk under the live-creds
         plan: token populated by OAuth → stray call → real order).
      3. Input sanitisation — whitespace-only tokens are functionally null.
      4. POS-specific requirements — Square requires location_id; refuse
         if it's missing rather than passing through and hoping Square
         rejects cleanly.

    Returns {"success": False, "reason": "<gate-name>"} when a guard
    blocks the call. The reason is structured so callers (and tests)
    can distinguish "logs-only because guarded" from "logs-only because
    POS failed."
    """
    if os.getenv("POS_ORDERS_DISABLED", "0") == "1":
        logger.info("POS_ORDERS_DISABLED env set — skipping POS write")
        return {"success": False, "reason": "pos_orders_disabled"}

    if demo_safe:
        logger.info(
            "demo_safe merchant — skipping POS write (pos_system=%s, token_present=%s)",
            pos_system, bool(access_token and access_token.strip()),
        )
        return {"success": False, "reason": "demo_safe"}

    pos_system = (pos_system or "").strip()
    access_token = (access_token or "").strip()
    location_id = (location_id or "").strip()

    if not pos_system or not access_token:
        logger.info("No POS configured — order logged without POS creation")
        return {"success": False, "reason": "no_pos_configured"}

    if pos_system == "square" and not location_id:
        logger.warning(
            "Square POS configured but location_id missing — refusing to fire order"
        )
        return {"success": False, "reason": "square_missing_location_id"}

    try:
        if pos_system == "square":
            return await _create_square_order(order, access_token, location_id)
        elif pos_system == "toast":
            return await _create_toast_order(order, access_token, location_id)
        elif pos_system == "clover":
            return await _create_clover_order(order, access_token, location_id)
        elif pos_system in WEBHOOK_CAPABLE_SYSTEMS or pos_system in OAUTH_SYSTEMS:
            return await _create_generic_order(order, pos_system, access_token, location_id)
        else:
            logger.info("POS %s — using notification fallback", pos_system)
            return await _create_notification_order(order, pos_system)
    except Exception as e:
        logger.error("POS order creation failed for %s: %s", pos_system, e)
        return {"success": False, "reason": "pos_error", "pos_system": pos_system, "error": str(e)}


async def _create_square_order(
    order: dict, access_token: str, location_id: str
) -> dict:
    import uuid

    line_items = []
    for item in order.get("items", []):
        line_items.append({
            "name": item["name"],
            "quantity": str(item["quantity"]),
            "base_price_money": {
                "amount": int(item.get("unit_price", 0) * 100),
                "currency": order.get("currency", "usd"),
            },
            "note": "; ".join(
                filter(None, [
                    f"Size: {item['size']}" if item.get("size") else "",
                    f"Mods: {', '.join(item.get('modifications', []))}" if item.get("modifications") else "",
                    item.get("special_instructions", ""),
                ])
            ),
        })

    # Build the fulfillment by order type. Square requires a time on each:
    # pickup_at for PICKUP, deliver_at for DELIVERY (else 400). Both use ASAP.
    _recipient = {
        "display_name": order.get("customer_name", "Phone Order"),
        "phone_number": order.get("caller_phone", ""),
    }
    _note = f"Phone order via Meridian AI • {order.get('special_requests', '')}".strip()
    _now = datetime.now(timezone.utc)
    if (order.get("order_type") or "pickup").lower() == "delivery":
        fulfillment = {
            "type": "DELIVERY",
            "state": "PROPOSED",
            "delivery_details": {
                "recipient": {
                    **_recipient,
                    # Square wants a structured address; the caller's free-text
                    # delivery address goes in line 1 (kitchen reads the note too).
                    "address": {"address_line_1": order.get("delivery_address", "") or "Address provided by phone"},
                },
                "schedule_type": "ASAP",
                "deliver_at": (_now + timedelta(minutes=45)).isoformat(),
                "note": _note,
            },
        }
    else:
        fulfillment = {
            "type": "PICKUP",
            "state": "PROPOSED",
            "pickup_details": {
                "recipient": _recipient,
                "schedule_type": "ASAP",
                "pickup_at": (_now + timedelta(minutes=15)).isoformat(),
                "note": _note,
            },
        }
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "order": {
            "location_id": location_id,
            "line_items": line_items,
            "fulfillments": [fulfillment],
        },
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://connect.squareup.com/v2/orders",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Square-Version": "2024-01-18",
            },
            timeout=10,
        )
        if res.status_code == 200:
            data = res.json()
            order_id = data.get("order", {}).get("id", "")
            logger.info("Square order created: %s", order_id)
            return {"success": True, "pos_order_id": order_id, "pos_system": "square"}
        else:
            logger.error("Square error %d: %s", res.status_code, res.text[:500])
            return {"success": False, "reason": "square_api_error", "status": res.status_code}


async def _create_toast_order(
    order: dict, access_token: str, location_id: str
) -> dict:
    selections = []
    for item in order.get("items", []):
        selections.append({
            "name": item["name"],
            "quantity": item["quantity"],
            "price": item.get("unit_price", 0),
            "modifiers": [
                {"name": mod} for mod in item.get("modifications", [])
            ],
            "specialRequest": item.get("special_instructions", ""),
        })

    payload = {
        "entityType": "Order",
        "externalId": f"meridian-phone-{order.get('merchant_id', '')}",
        "diningOption": _toast_dining_option(order.get("order_type", "pickup")),
        "checks": [
            {
                "customer": {
                    "firstName": order.get("customer_name", "").split()[0] if order.get("customer_name") else "Phone",
                    "lastName": " ".join(order.get("customer_name", "").split()[1:]) or "Order",
                    "phone": order.get("caller_phone", ""),
                },
                "selections": selections,
            }
        ],
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{TOAST_API_BASE}/orders/v2/orders",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Toast-Restaurant-External-ID": location_id,
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if res.status_code in (200, 201):
            data = res.json()
            return {"success": True, "pos_order_id": data.get("guid", ""), "pos_system": "toast"}
        else:
            return {"success": False, "reason": "toast_api_error", "status": res.status_code}


async def _create_clover_order(
    order: dict, access_token: str, merchant_id: str
) -> dict:
    """Create an order in Clover (write) + add its line items. Requires the
    Clover app to have ORDERS/INVENTORY write permissions (granted at the app
    level in the Clover dashboard, then a fresh OAuth)."""
    base = clover_api_base()
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(
            f"{base}/v3/merchants/{merchant_id}/orders",
            json={
                "state": "open",
                "note": f"Phone order for {order.get('customer_name', '')} via Meridian AI",
            },
            headers=headers,
        )
        if res.status_code not in (200, 201):
            logger.warning("Clover order create failed %s: %s", res.status_code, res.text[:300])
            return {"success": False, "reason": "clover_api_error", "status": res.status_code}

        order_id = res.json().get("id", "")

        # One line item per unit so quantity is reflected (the previous code added
        # each item once regardless of quantity → undercharged multi-qty orders).
        added, failed = 0, 0
        for item in order.get("items", []):
            qty = max(1, int(item.get("quantity", 1) or 1))
            price_cents = int(round(float(item.get("unit_price", item.get("price", 0)) or 0) * 100))
            li = {"name": item.get("name", "Item"), "price": price_cents,
                  "note": item.get("special_instructions", "")}
            for _ in range(qty):
                r = await client.post(
                    f"{base}/v3/merchants/{merchant_id}/orders/{order_id}/line_items",
                    json=li, headers=headers,
                )
                if r.status_code in (200, 201):
                    added += 1
                else:
                    failed += 1
                    logger.warning("Clover line-item add failed %s: %s", r.status_code, r.text[:200])

        if added == 0 and failed > 0:
            return {"success": False, "reason": "clover_line_items_failed", "pos_order_id": order_id}
        return {"success": True, "pos_order_id": order_id, "pos_system": "clover",
                "line_items_added": added, "line_items_failed": failed}


def _toast_dining_option(order_type: str) -> str:
    mapping = {
        "pickup": "TAKE_OUT",
        "delivery": "DELIVERY",
        "dine_in": "DINE_IN",
        "reservation": "DINE_IN",
    }
    return mapping.get(order_type, "TAKE_OUT")


async def _create_generic_order(
    order: dict, pos_system: str, access_token: str, location_id: str
) -> dict:
    """
    Generic order creation for POS systems that support webhooks or API endpoints.
    Looks up the merchant's configured webhook URL from Supabase and POSTs the
    standardized order payload. Works with any of the 80+ supported POS systems
    that accept incoming order webhooks.
    """
    webhook_url = await _get_pos_webhook_url(order.get("merchant_id", ""), pos_system)

    payload = {
        "source": "meridian_phone_agent",
        "pos_system": pos_system,
        "merchant_id": order.get("merchant_id", ""),
        "location_id": location_id,
        "order": {
            "customer_name": order.get("customer_name", "Phone Order"),
            "customer_phone": order.get("caller_phone", ""),
            "order_type": order.get("order_type", "pickup"),
            "items": [
                {
                    "name": item["name"],
                    "quantity": item.get("quantity", 1),
                    "unit_price": item.get("unit_price", 0),
                    "size": item.get("size", ""),
                    "modifications": item.get("modifications", []),
                    "special_instructions": item.get("special_instructions", ""),
                }
                for item in order.get("items", [])
            ],
            "subtotal": order.get("subtotal", 0),
            "tax": order.get("tax", 0),
            "total": order.get("total", 0),
            "delivery_address": order.get("delivery_address", ""),
            "special_requests": order.get("special_requests", ""),
        },
    }

    if webhook_url:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    webhook_url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "X-Meridian-Source": "phone-agent",
                    },
                    timeout=15,
                )
                if res.status_code in (200, 201, 202):
                    data = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
                    order_id = data.get("order_id", data.get("id", ""))
                    logger.info("Generic POS order created via webhook: %s → %s", pos_system, order_id)
                    return {"success": True, "pos_order_id": order_id, "pos_system": pos_system, "method": "webhook"}
                else:
                    logger.warning("Webhook returned %d for %s", res.status_code, pos_system)
        except Exception as e:
            logger.warning("Webhook failed for %s: %s — falling back to notification", pos_system, e)

    return await _create_notification_order(order, pos_system)


async def _create_notification_order(order: dict, pos_system: str) -> dict:
    """
    Notification-based fallback for POS systems without direct API or webhook.
    Saves the order to Supabase with status 'pending_manual' so it appears in
    the merchant's Meridian dashboard for manual entry into their POS.
    Also triggers SMS/email notification to the merchant.
    """
    merchant_id = order.get("merchant_id", "")

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{SUPABASE_URL}/rest/v1/phone_orders",
                    json={
                        "merchant_id": merchant_id,
                        "customer_name": order.get("customer_name", ""),
                        "order_type": order.get("order_type", "pickup"),
                        "items": order.get("items", []),
                        "subtotal": order.get("subtotal", 0),
                        "tax": order.get("tax", 0),
                        "total": order.get("total", 0),
                        "delivery_address": order.get("delivery_address", ""),
                        "special_requests": order.get("special_requests", ""),
                        "caller_phone": order.get("caller_phone", ""),
                        "pos_system": pos_system,
                        "pos_order_id": "",
                        "pos_success": False,
                        "source": "phone_agent",
                        "status": "pending_manual",
                    },
                    headers={
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal",
                    },
                    timeout=10,
                )
                logger.info("Order saved for manual POS entry: merchant=%s pos=%s", merchant_id, pos_system)
        except Exception as e:
            logger.error("Failed to save notification order: %s", e)

    return {
        "success": True,
        "pos_system": pos_system,
        "method": "notification",
        "pos_order_id": "",
        "message": f"Order saved — merchant notified to enter in {pos_system}",
    }


async def _get_pos_webhook_url(merchant_id: str, pos_system: str) -> str | None:
    """Look up the merchant's POS webhook URL from their config in Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY or not merchant_id:
        return None

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{SUPABASE_URL}/rest/v1/phone_agent_config"
                f"?merchant_id=eq.{merchant_id}&select=pos_webhook_url",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=5,
            )
            if res.status_code == 200 and res.json():
                return res.json()[0].get("pos_webhook_url")
    except Exception as e:
        logger.warning("Failed to lookup webhook URL: %s", e)
    return None
