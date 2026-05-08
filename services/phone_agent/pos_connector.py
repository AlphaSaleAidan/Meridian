"""
POS connector — creates orders in Square, Toast, or Clover via their APIs.
Falls back gracefully if POS is not configured or unavailable.
"""
import logging
from typing import Any

import httpx

logger = logging.getLogger("meridian.phone_agent.pos")


async def create_pos_order(
    order: dict[str, Any],
    pos_system: str,
    access_token: str,
    location_id: str,
) -> dict:
    if not pos_system or not access_token:
        logger.info("No POS configured — order logged without POS creation")
        return {"success": False, "reason": "no_pos_configured"}

    try:
        if pos_system == "square":
            return await _create_square_order(order, access_token, location_id)
        elif pos_system == "toast":
            return await _create_toast_order(order, access_token, location_id)
        elif pos_system == "clover":
            return await _create_clover_order(order, access_token, location_id)
        else:
            logger.warning("Unsupported POS system: %s", pos_system)
            return {"success": False, "reason": f"unsupported_pos_{pos_system}"}
    except Exception as e:
        logger.error("POS order creation failed: %s", e)
        return {"success": False, "reason": "pos_error", "error": str(e)}


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
                "currency": "USD",
            },
            "note": "; ".join(
                filter(None, [
                    f"Size: {item['size']}" if item.get("size") else "",
                    f"Mods: {', '.join(item.get('modifications', []))}" if item.get("modifications") else "",
                    item.get("special_instructions", ""),
                ])
            ),
        })

    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "order": {
            "location_id": location_id,
            "line_items": line_items,
            "fulfillments": [
                {
                    "type": "PICKUP" if order.get("order_type") == "pickup" else "SHIPMENT",
                    "state": "PROPOSED",
                    "pickup_details": {
                        "recipient": {
                            "display_name": order.get("customer_name", "Phone Order"),
                            "phone_number": order.get("caller_phone", ""),
                        },
                        "note": f"Phone order via Meridian AI • {order.get('special_requests', '')}".strip(),
                    },
                }
            ],
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
            f"https://toast-api-server/orders/v2/orders",
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
    line_items_payload = []
    for item in order.get("items", []):
        line_items_payload.append({
            "name": item["name"],
            "price": int(item.get("unit_price", 0) * 100),
            "note": item.get("special_instructions", ""),
        })

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api.clover.com/v3/merchants/{merchant_id}/orders",
            json={
                "state": "open",
                "manualTransaction": False,
                "note": f"Phone order for {order.get('customer_name', '')} via Meridian AI",
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if res.status_code in (200, 201):
            clover_order = res.json()
            order_id = clover_order.get("id", "")

            for li in line_items_payload:
                await client.post(
                    f"https://api.clover.com/v3/merchants/{merchant_id}/orders/{order_id}/line_items",
                    json=li,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    timeout=10,
                )

            return {"success": True, "pos_order_id": order_id, "pos_system": "clover"}
        else:
            return {"success": False, "reason": "clover_api_error", "status": res.status_code}


def _toast_dining_option(order_type: str) -> str:
    mapping = {
        "pickup": "TAKE_OUT",
        "delivery": "DELIVERY",
        "dine_in": "DINE_IN",
    }
    return mapping.get(order_type, "TAKE_OUT")
