"""
Payment link generator — creates checkout URLs from connected POS systems.
Square, Toast, and Clover have native payment link APIs.
All other POS systems get a Meridian-hosted checkout page.
"""
import logging
import os
import uuid
from typing import Any

import httpx

logger = logging.getLogger("meridian.phone_agent.payments")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
MERIDIAN_CHECKOUT_BASE = os.getenv("MERIDIAN_CHECKOUT_URL", "https://pay.meridian.ai")


async def create_payment_link(
    order: dict[str, Any],
    pos_system: str,
    pos_order_id: str,
    access_token: str,
    location_id: str,
) -> dict:
    """
    Generate a payment link for a phone order.
    Returns {"url": "...", "method": "square|toast|clover|meridian"} on success.
    """
    if not pos_system:
        return await _create_meridian_checkout(order)

    try:
        if pos_system == "square":
            return await _square_payment_link(order, access_token, location_id, pos_order_id)
        elif pos_system == "toast":
            return await _toast_payment_link(order, access_token, location_id, pos_order_id)
        elif pos_system == "clover":
            return await _clover_payment_link(order, access_token, location_id, pos_order_id)
        else:
            return await _create_meridian_checkout(order, pos_system)
    except Exception as e:
        logger.error("Payment link creation failed for %s: %s", pos_system, e)
        return await _create_meridian_checkout(order, pos_system)


async def _square_payment_link(
    order: dict, access_token: str, location_id: str, pos_order_id: str
) -> dict:
    line_items = []
    for item in order.get("items", []):
        line_items.append({
            "name": item["name"],
            "quantity": str(item.get("quantity", 1)),
            "base_price_money": {
                "amount": int(item.get("unit_price", 0) * 100),
                "currency": order.get("currency", "USD"),
            },
        })

    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "quick_pay": None,
        "order": {
            "location_id": location_id,
            "line_items": line_items,
            "reference_id": pos_order_id,
        },
        "checkout_options": {
            "redirect_url": f"{MERIDIAN_CHECKOUT_BASE}/confirmation/{pos_order_id}",
            "ask_for_shipping_address": order.get("order_type") == "delivery",
        },
        "pre_populated_data": {
            "buyer_phone": order.get("caller_phone", ""),
        },
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://connect.squareup.com/v2/online-checkout/payment-links",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Square-Version": "2024-01-18",
            },
            timeout=10,
        )
        if res.status_code in (200, 201):
            data = res.json()
            url = data.get("payment_link", {}).get("url", "")
            link_id = data.get("payment_link", {}).get("id", "")
            logger.info("Square payment link created: %s", link_id)
            return {"url": url, "link_id": link_id, "method": "square"}
        else:
            logger.warning("Square payment link error %d: %s", res.status_code, res.text[:300])
            return await _create_meridian_checkout(order, "square")


async def _toast_payment_link(
    order: dict, access_token: str, location_id: str, pos_order_id: str
) -> dict:
    payload = {
        "orderGuid": pos_order_id,
        "amount": int(order.get("total", 0) * 100),
        "customerPhone": order.get("caller_phone", ""),
        "redirectUrl": f"{MERIDIAN_CHECKOUT_BASE}/confirmation/{pos_order_id}",
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://toast-api-server/orders/v2/paymentLinks",
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
            url = data.get("paymentUrl", data.get("url", ""))
            logger.info("Toast payment link created for order %s", pos_order_id)
            return {"url": url, "link_id": pos_order_id, "method": "toast"}
        else:
            logger.warning("Toast payment link error %d", res.status_code)
            return await _create_meridian_checkout(order, "toast")


async def _clover_payment_link(
    order: dict, access_token: str, merchant_id: str, pos_order_id: str
) -> dict:
    payload = {
        "amount": int(order.get("total", 0) * 100),
        "note": f"Phone order for {order.get('customer_name', '')}",
        "redirectUrl": f"{MERIDIAN_CHECKOUT_BASE}/confirmation/{pos_order_id}",
        "customer": {
            "phoneNumber": order.get("caller_phone", ""),
        },
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api.clover.com/v3/merchants/{merchant_id}/pay_links",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if res.status_code in (200, 201):
            data = res.json()
            url = data.get("url", data.get("paymentUrl", ""))
            link_id = data.get("id", "")
            logger.info("Clover payment link created: %s", link_id)
            return {"url": url, "link_id": link_id, "method": "clover"}
        else:
            logger.warning("Clover payment link error %d", res.status_code)
            return await _create_meridian_checkout(order, "clover")


async def _create_meridian_checkout(order: dict, pos_system: str = "") -> dict:
    """
    Create a Meridian-hosted checkout page for POS systems without
    native payment link APIs. Saves a checkout session to Supabase
    and returns the URL.
    """
    checkout_id = str(uuid.uuid4())[:12]

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{SUPABASE_URL}/rest/v1/checkout_sessions",
                    json={
                        "id": checkout_id,
                        "merchant_id": order.get("merchant_id", ""),
                        "customer_name": order.get("customer_name", ""),
                        "customer_phone": order.get("caller_phone", ""),
                        "order_type": order.get("order_type", "pickup"),
                        "items": order.get("items", []),
                        "subtotal": order.get("subtotal", 0),
                        "tax": order.get("tax", 0),
                        "total": order.get("total", 0),
                        "currency": order.get("currency", "USD"),
                        "pos_system": pos_system,
                        "status": "pending",
                        "source": "phone_agent",
                    },
                    headers={
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal",
                    },
                    timeout=10,
                )
        except Exception as e:
            logger.error("Failed to create checkout session: %s", e)

    url = f"{MERIDIAN_CHECKOUT_BASE}/checkout/{checkout_id}"
    logger.info("Meridian checkout created: %s (pos=%s)", checkout_id, pos_system or "none")
    return {"url": url, "link_id": checkout_id, "method": "meridian"}
