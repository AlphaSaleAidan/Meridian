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
from payment_links import create_checkout
from sms_checkout import send_checkout_sms

logger = logging.getLogger("meridian.phone_agent.router")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
# Writes (phone_orders inserts/updates) need the service-role key — the anon role
# lacks INSERT GRANT on phone_orders (42501 permission denied). Fall back to anon.
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")


async def route_order(
    order: dict[str, Any],
    config: MerchantPhoneConfig,
    caller_info: dict,
    pos_result: dict,
):
    order_summary = _format_order_summary(order)

    order_row_id = await _save_to_supabase(order, pos_result)

    if config.transfer_number:
        await _send_sms_notification(config.transfer_number, order_summary)

    payment_result = {}
    sms_result = {}
    if config.sms_checkout_enabled and order.get("caller_phone"):
        pos_order_id = pos_result.get("pos_order_id", "")
        # Unified checkout: Stripe (CAD, card+Apple/Google Pay) when enabled +
        # configured, else falls back to the per-POS link inside create_checkout.
        payment_result = await create_checkout(
            order=order,
            merchant_config=config,
            pos_order_id=pos_order_id,
        )

        if payment_result.get("url"):
            sms_result = await send_checkout_sms(
                order=order,
                payment_link=payment_result["url"],
                business_name=config.business_name,
                sms_pay_template=getattr(config, "sms_pay_template", "") or "",
            )
            await _update_order_payment(
                order, payment_result, sms_result,
                order_row_id=order_row_id,
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
    sym = "CA$" if (order.get("currency") or "").upper() == "CAD" else "$"
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


async def _save_to_supabase(order: dict, pos_result: dict) -> str | None:
    """Insert the phone order; return its row id so the later payment update can
    target the exact row (PostgREST PATCH ignores order/limit, so scoping by
    merchant+caller would update ALL of that caller's orders)."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
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
                    "Prefer": "return=representation",
                },
                timeout=10,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                if isinstance(data, list) and data:
                    return data[0].get("id")
    except Exception as e:
        logger.error("Failed to save order to Supabase: %s", e)
    return None


async def _update_order_payment(
    order: dict, payment_result: dict, sms_result: dict,
    order_row_id: str | None = None,
):
    """Update the saved order with payment link + SMS status, scoped to the
    EXACT row by id. Without the id we skip rather than PATCH by
    merchant+caller_phone: PostgREST ignores order/limit on PATCH, so that
    filter would overwrite the payment status of ALL of that caller's orders."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    if not order_row_id:
        logger.warning(
            "skip payment update: no order row id (insert returned none) — "
            "not PATCHing by merchant+caller to avoid clobbering prior orders"
        )
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{SUPABASE_URL}/rest/v1/phone_orders?id=eq.{order_row_id}",
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
    """Text the merchant's staff line the order ticket. Best-effort: a send
    failure must never break order routing (the order is already in the POS)."""
    if not phone:
        return
    try:
        from sms_checkout import send_sms

        result = await send_sms(phone, message)
        if result.get("sent"):
            logger.info("Staff alert SMS sent to %s via %s", phone, result.get("method"))
        else:
            logger.info("Staff alert SMS not sent to %s: %s", phone, result.get("reason"))
    except Exception as e:  # noqa: BLE001 — never break routing on an SMS error
        logger.warning("Staff alert SMS failed for %s: %s", phone, e)
