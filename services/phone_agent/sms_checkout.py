"""
SMS checkout — sends order confirmation + payment link to the customer.
Uses Twilio or a generic SMS gateway. Falls back to Supabase edge function
for SMS delivery if no direct gateway is configured.
"""
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("meridian.phone_agent.sms_checkout")

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_PHONE_NUMBER", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")


async def send_checkout_sms(
    order: dict[str, Any],
    payment_link: str,
    business_name: str,
) -> dict:
    """
    Send order confirmation + payment link to the customer's phone.
    Returns {"sent": True/False, "method": "twilio"|"supabase"|"none"}.
    """
    phone = order.get("caller_phone", "")
    if not phone:
        logger.warning("No phone number for checkout SMS")
        return {"sent": False, "method": "none", "reason": "no_phone"}

    message = _format_checkout_sms(order, payment_link, business_name)

    if TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM:
        return await _send_via_twilio(phone, message)

    if SUPABASE_URL and SUPABASE_KEY:
        return await _send_via_supabase_function(phone, message)

    logger.info("No SMS gateway configured — checkout SMS not sent to %s", phone)
    return {"sent": False, "method": "none", "reason": "no_gateway"}


def _format_checkout_sms(
    order: dict, payment_link: str, business_name: str
) -> str:
    sym = "CA$" if order.get("currency") == "CAD" else "$"
    total = order.get("total", 0)
    item_count = sum(i.get("quantity", 1) for i in order.get("items", []))
    order_type = order.get("order_type", "pickup").replace("_", " ").title()
    customer_name = order.get("customer_name", "").split()[0] if order.get("customer_name") else ""

    lines = []
    if customer_name:
        lines.append(f"Hi {customer_name}!")
    lines.append(f"Your {order_type.lower()} order from {business_name} is confirmed.")
    lines.append(f"")
    lines.append(f"{item_count} item{'s' if item_count != 1 else ''} — {sym}{total:.2f}")
    lines.append(f"")
    lines.append(f"Pay here: {payment_link}")
    lines.append(f"")
    lines.append(f"Thank you! — {business_name}")

    return "\n".join(lines)


async def _send_via_twilio(phone: str, message: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json",
                data={
                    "To": phone,
                    "From": TWILIO_FROM,
                    "Body": message,
                },
                auth=(TWILIO_SID, TWILIO_TOKEN),
                timeout=10,
            )
            if res.status_code in (200, 201):
                sid = res.json().get("sid", "")
                logger.info("Checkout SMS sent via Twilio: %s → %s", sid, phone)
                return {"sent": True, "method": "twilio", "message_sid": sid}
            else:
                logger.error("Twilio error %d: %s", res.status_code, res.text[:300])
                return {"sent": False, "method": "twilio", "reason": f"status_{res.status_code}"}
    except Exception as e:
        logger.error("Twilio send failed: %s", e)
        return {"sent": False, "method": "twilio", "reason": str(e)}


async def _send_via_supabase_function(phone: str, message: str) -> dict:
    """Invoke a Supabase Edge Function to send SMS (Twilio, MessageBird, etc.)."""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{SUPABASE_URL}/functions/v1/send-sms",
                json={"to": phone, "body": message},
                headers={
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            if res.status_code in (200, 201):
                logger.info("Checkout SMS sent via Supabase function to %s", phone)
                return {"sent": True, "method": "supabase"}
            else:
                logger.warning("Supabase SMS function error %d", res.status_code)
                return {"sent": False, "method": "supabase", "reason": f"status_{res.status_code}"}
    except Exception as e:
        logger.error("Supabase SMS function failed: %s", e)
        return {"sent": False, "method": "supabase", "reason": str(e)}
