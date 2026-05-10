"""
Order router — routes completed orders to kitchen display, SMS, email,
or webhook based on merchant configuration. Generates payment links and
sends checkout SMS to the customer.
"""
import logging
import os
from typing import Any

import httpx

from merchant_config import MerchantPhoneConfig
from payment_links import create_payment_link
from sms_checkout import send_checkout_sms

logger = logging.getLogger("meridian.phone_agent.router")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")


async def route_order(
    order: dict[str, Any],
    config: MerchantPhoneConfig,
    caller_info: dict,
    pos_result: dict,
):
    order_summary = _format_order_summary(order)

    await _save_to_supabase(order, pos_result)

    if config.transfer_number:
        await _send_sms_notification(config.transfer_number, order_summary)

    payment_result = {}
    sms_result = {}
    if config.sms_checkout_enabled and order.get("caller_phone"):
        pos_order_id = pos_result.get("pos_order_id", "")
        payment_result = await create_payment_link(
            order=order,
            pos_system=config.pos_system,
            pos_order_id=pos_order_id,
            access_token=config.pos_access_token,
            location_id=config.pos_location_id,
        )

        if payment_result.get("url"):
            sms_result = await send_checkout_sms(
                order=order,
                payment_link=payment_result["url"],
                business_name=config.business_name,
            )
            await _update_order_payment(
                order, payment_result, sms_result,
            )

    logger.info(
        "Order routed: merchant=%s customer=%s items=%d total=%.2f pos=%s payment=%s sms=%s",
        config.merchant_id,
        order.get("customer_name", ""),
        len(order.get("items", [])),
        order.get("total", 0),
        "success" if pos_result.get("success") else "fallback",
        payment_result.get("method", "none"),
        "sent" if sms_result.get("sent") else "not_sent",
    )

    return {
        "pos": pos_result,
        "payment_link": payment_result.get("url", ""),
        "sms_sent": sms_result.get("sent", False),
    }


def _format_order_summary(order: dict) -> str:
    lines = [
        f"NEW PHONE ORDER — {order.get('business_name', '')}",
        f"Customer: {order.get('customer_name', 'Unknown')}",
        f"Type: {order.get('order_type', 'pickup').upper()}",
        "",
    ]

    for item in order.get("items", []):
        size = f" ({item['size']})" if item.get("size") else ""
        mods = f" [{', '.join(item['modifications'])}]" if item.get("modifications") else ""
        lines.append(f"  {item['quantity']}x {item['name']}{size}{mods}")
        if item.get("special_instructions"):
            lines.append(f"     → {item['special_instructions']}")

    lines.append("")
    sym = "CA$" if order.get("currency") == "CAD" else "$"
    lines.append(f"Subtotal: {sym}{order.get('subtotal', 0):.2f}")
    lines.append(f"Tax: {sym}{order.get('tax', 0):.2f}")
    lines.append(f"Total: {sym}{order.get('total', 0):.2f}")

    if order.get("delivery_address"):
        lines.append(f"\nDelivery: {order['delivery_address']}")
    if order.get("special_requests"):
        lines.append(f"Note: {order['special_requests']}")
    if order.get("caller_phone"):
        lines.append(f"Phone: {order['caller_phone']}")

    lines.append("\n— Meridian AI Phone Agent")
    return "\n".join(lines)


async def _save_to_supabase(order: dict, pos_result: dict):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{SUPABASE_URL}/rest/v1/phone_orders",
                json={
                    "merchant_id": order.get("merchant_id", ""),
                    "customer_name": order.get("customer_name", ""),
                    "order_type": order.get("order_type", "pickup"),
                    "items": order.get("items", []),
                    "subtotal": order.get("subtotal", 0),
                    "tax": order.get("tax", 0),
                    "total": order.get("total", 0),
                    "delivery_address": order.get("delivery_address", ""),
                    "special_requests": order.get("special_requests", ""),
                    "caller_phone": order.get("caller_phone", ""),
                    "pos_system": order.get("pos_system", ""),
                    "pos_order_id": pos_result.get("pos_order_id", ""),
                    "pos_success": pos_result.get("success", False),
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
        logger.error("Failed to save order to Supabase: %s", e)


async def _update_order_payment(
    order: dict, payment_result: dict, sms_result: dict
):
    """Update the Supabase order record with payment link and SMS status."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    merchant_id = order.get("merchant_id", "")
    caller_phone = order.get("caller_phone", "")
    if not merchant_id or not caller_phone:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{SUPABASE_URL}/rest/v1/phone_orders"
                f"?merchant_id=eq.{merchant_id}&caller_phone=eq.{caller_phone}"
                f"&order=created_at.desc&limit=1",
                json={
                    "payment_link": payment_result.get("url", ""),
                    "payment_method": payment_result.get("method", ""),
                    "payment_status": "pending",
                    "sms_sent": sms_result.get("sent", False),
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
        logger.error("Failed to update order payment info: %s", e)


async def _send_sms_notification(phone: str, message: str):
    logger.info("SMS notification to %s (merchant staff alert)", phone)
