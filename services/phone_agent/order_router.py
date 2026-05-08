"""
Order router — routes completed orders to kitchen display, SMS, email,
or webhook based on merchant configuration.
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Any, Optional

import httpx

from merchant_config import MerchantPhoneConfig

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

    logger.info(
        "Order routed: merchant=%s customer=%s items=%d total=%.2f pos=%s",
        config.merchant_id,
        order.get("customer_name", ""),
        len(order.get("items", [])),
        order.get("total", 0),
        "success" if pos_result.get("success") else "fallback",
    )


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
    lines.append(f"Subtotal: ${order.get('subtotal', 0):.2f}")
    lines.append(f"Tax: ${order.get('tax', 0):.2f}")
    lines.append(f"Total: ${order.get('total', 0):.2f}")

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


async def _send_sms_notification(phone: str, message: str):
    logger.info("SMS notification to %s (stub — needs SIP trunk or SMS gateway)", phone)
