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


def _toast_writer_enabled() -> bool:
    """Gate for the real Toast Orders-API writer. Default OFF — Toast routes to
    the notification fallback until this is flipped on post-sandbox-verification."""
    return os.environ.get("TOAST_ORDER_WRITER_ENABLED", "").strip().lower() in (
        "1", "true", "yes", "on")


def _square_orders_url() -> str:
    """Square Orders endpoint — honor SQUARE_ENVIRONMENT so a sandbox/test
    merchant on the phone path doesn't fire against the real production POS
    (the host was hardcoded to prod). Mirrors src/config.SquareConfig."""
    if os.getenv("SQUARE_ENVIRONMENT", "").strip().lower() == "sandbox":
        return "https://connect.squareupsandbox.com/v2/orders"
    return "https://connect.squareup.com/v2/orders"


# Clover write path (order + line items + kitchen print event) lives in its
# own module; clover_api_base is re-exported here for existing callers.
from clover_orders import clover_api_base, create_clover_order  # noqa: E402,F401

# Systems with an always-on direct order writer on the phone path. Toast has a
# real GUID-referenced writer now (_create_toast_order) but stays OUT of this
# set: it's gated behind TOAST_ORDER_WRITER_ENABLED (default OFF) and dispatched
# explicitly, falling back to notification on any miss, until it's verified
# against a real Toast sandbox. (Square/Clover are on unconditionally.)
DIRECT_API_SYSTEMS = {"square", "clover"}

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
        elif pos_system == "clover":
            return await create_clover_order(order, access_token, location_id)
        elif pos_system == "toast":
            # Toast direct write is gated OFF until verified against a real Toast
            # sandbox. When on, try the real GUID-referenced writer; on ANY
            # miss (unresolved item, menu unavailable, API error) fall back to
            # the notification path so the order is never silently dropped.
            if _toast_writer_enabled():
                result = await _create_toast_order(order, access_token, location_id)
                if result.get("success"):
                    return result
                logger.info("Toast writer miss (%s) — notification fallback", result.get("reason"))
            return await _create_notification_order(order, "toast")
        elif pos_system in WEBHOOK_CAPABLE_SYSTEMS or pos_system in OAUTH_SYSTEMS:
            return await _create_generic_order(order, pos_system, access_token, location_id)
        else:
            logger.info("POS %s — using notification fallback", pos_system)
            return await _create_notification_order(order, pos_system)
    except Exception as e:
        logger.error("POS order creation failed for %s: %s", pos_system, e)
        return {"success": False, "reason": "pos_error", "pos_system": pos_system, "error": str(e)}


def _order_idempotency_key(order: dict) -> str:
    """Deterministic Square idempotency key for a phone order.

    A fresh uuid4 per call meant a timeout-then-retry (where Square actually
    created the order) generated a NEW key, so Square couldn't dedup → duplicate
    order, double-cooked food. Derive the key from the STABLE order content
    (explicit ref if present, else merchant + caller + items) so a retry of the
    same order reuses the same key. Max 45 chars (Square limit)."""
    import hashlib

    ref = str(order.get("order_ref") or order.get("id") or "").strip()
    if not ref:
        stable = "{}|{}|{}".format(
            order.get("merchant_id", ""),
            order.get("caller_phone", ""),
            ",".join(f"{i.get('name', '')}:{i.get('quantity', 1)}:{i.get('size', '')}"
                     for i in order.get("items", [])),
        )
        ref = hashlib.sha256(stable.encode()).hexdigest()
    return f"mmo-{ref}"[:45]


async def _create_square_order(
    order: dict, access_token: str, location_id: str
) -> dict:
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
        "idempotency_key": _order_idempotency_key(order),
        "order": {
            "location_id": location_id,
            "line_items": line_items,
            "fulfillments": [fulfillment],
        },
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            _square_orders_url(),
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


def _toast_headers(access_token: str, location_id: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Toast-Restaurant-External-ID": location_id,
        "Content-Type": "application/json",
    }


async def _create_toast_order(
    order: dict, access_token: str, location_id: str
) -> dict:
    """Write a real GUID-referenced order to Toast (Orders API v2).

    Toast rejects name/price selections — every selection must reference a live
    menu-item GUID (+ its menu-group GUID) and the order a dining-option GUID.
    So we fetch the merchant's live menu + dining options, resolve the phone
    order's item names → GUIDs, and only POST when everything resolves. If any
    item can't be mapped we return a structured failure so the caller falls back
    to the SMS/dashboard path — an honest miss beats a mis-charged order.

    Gated OFF by TOAST_ORDER_WRITER_ENABLED at the dispatch site; verified
    against a real Toast sandbox before that flag is ever flipped on. Toast
    tokens are short-lived (client_credentials) — token refresh is a
    sandbox-verification follow-up, out of scope for the mapping layer here.
    """
    # Import the pure resolver from src/ (same sys.path trick as sms_order.py).
    import sys
    from pathlib import Path
    _root = str(Path(__file__).resolve().parents[2])
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from src.toast.order_writer import ToastMenuResolver, build_toast_order

    headers = _toast_headers(access_token, location_id)
    async with httpx.AsyncClient(timeout=15) as client:
        menu_res, dining_res = None, None
        try:
            menu_raw = await client.get(f"{TOAST_API_BASE}/menus/v2/menus", headers=headers)
            dining_raw = await client.get(
                f"{TOAST_API_BASE}/config/v2/diningOptions", headers=headers)
            menu_res = menu_raw.json() if menu_raw.status_code == 200 else None
            dining_res = dining_raw.json() if dining_raw.status_code == 200 else None
        except Exception as e:
            logger.warning("Toast menu/dining fetch failed: %s — falling back", e)
            return {"success": False, "reason": "toast_menu_fetch_failed", "pos_system": "toast"}

        if not menu_res or dining_res is None:
            return {"success": False, "reason": "toast_menu_unavailable", "pos_system": "toast"}

        # Flatten menus → items with group GUID (mirrors client.get_menu_items).
        menu_items = []
        for menu in (menu_res if isinstance(menu_res, list) else [menu_res]):
            for group in menu.get("groups", []):
                for it in group.get("items", []):
                    it["_menu_group_guid"] = group.get("guid", "")
                    menu_items.append(it)

        resolver = ToastMenuResolver(menu_items, dining_res)
        built = build_toast_order(order, resolver)
        if not built.get("ok"):
            logger.info("Toast order not built (%s, unresolved=%s) — notification fallback",
                        built.get("reason"), built.get("unresolved"))
            return {"success": False, "reason": f"toast_{built.get('reason')}",
                    "pos_system": "toast", "unresolved": built.get("unresolved", [])}

        res = await client.post(
            f"{TOAST_API_BASE}/orders/v2/orders",
            json=built["payload"], headers=headers,
        )
        if res.status_code in (200, 201):
            data = res.json()
            return {"success": True, "pos_order_id": data.get("guid", ""), "pos_system": "toast"}
        logger.warning("Toast order POST %d: %s", res.status_code, res.text[:300])
        return {"success": False, "reason": "toast_api_error",
                "status": res.status_code, "pos_system": "toast"}


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
    Fallback for POS systems without direct API or webhook: save the order to
    Supabase with status 'pending_manual' so it appears in the merchant's
    Meridian dashboard for manual entry into their POS.

    This function does NOT itself send SMS/email — merchant notification is the
    separate merchant_sms/email leg (delivery_channels / order_router). So it
    reports success ONLY when the row actually saved (a dashboard row is the one
    thing it guarantees), and flags requires_merchant_notification so the caller
    knows a delivery leg still has to fire — a save alone must not read as
    "the kitchen got it".
    """
    merchant_id = order.get("merchant_id", "")

    saved = False
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
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
                saved = resp.status_code in (200, 201, 204)
                if saved:
                    logger.info("Order saved for manual POS entry: merchant=%s pos=%s", merchant_id, pos_system)
                else:
                    logger.error("Notification order save failed HTTP %s: %s",
                                 resp.status_code, resp.text[:200])
        except Exception as e:
            logger.error("Failed to save notification order: %s", e)

    return {
        "success": saved,
        "pos_system": pos_system,
        "method": "notification",
        "pos_order_id": "",
        # A dashboard row is NOT delivery — the caller must still fire the
        # merchant SMS/email leg and treat a skipped leg as non-delivery.
        "requires_merchant_notification": True,
        "reason": None if saved else "notification_order_save_failed",
        "message": (f"Order saved to dashboard for {pos_system} — merchant must be notified"
                    if saved else f"Could not save order for {pos_system}"),
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
