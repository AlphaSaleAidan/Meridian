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


def _telnyx_cfg() -> tuple[str, str, str]:
    """(key, from, profile) — Telnyx is the voice provider, so its SMS creds are
    already on the box. Read at call time so tests/env changes take effect."""
    return (
        os.getenv("TELNYX_API_KEY", ""),
        os.getenv("TELNYX_PHONE_NUMBER", ""),
        os.getenv("TELNYX_MESSAGING_PROFILE_ID", ""),
    )


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

    return await send_sms(phone, _format_checkout_sms(order, payment_link, business_name))


async def send_sms(to: str, body: str) -> dict:
    """Generic SMS send (staff alerts, notifications) — same gateway selection
    as the customer checkout SMS: Twilio → Supabase edge function → none.

    Returns {"sent": bool, "method": "telnyx"|"twilio"|"supabase"|"none", ...}.

    Telnyx is preferred — it's the voice provider, so its SMS creds are already
    configured (verified working for CA delivery); Twilio/Supabase remain as
    fallbacks for environments wired the old way.
    """
    if not to or not body:
        return {"sent": False, "method": "none", "reason": "missing_to_or_body"}
    tkey, tfrom, _ = _telnyx_cfg()
    if tkey and tfrom:
        return await _send_via_telnyx(to, body)
    if TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM:
        return await _send_via_twilio(to, body)
    if SUPABASE_URL and SUPABASE_KEY:
        return await _send_via_supabase_function(to, body)
    logger.info("No SMS gateway configured — SMS not sent to %s", to)
    return {"sent": False, "method": "none", "reason": "no_gateway"}


async def _send_via_telnyx(phone: str, message: str) -> dict:
    key, frm, profile = _telnyx_cfg()
    payload: dict[str, Any] = {"from": frm, "to": phone, "text": message}
    if profile:
        payload["messaging_profile_id"] = profile
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(
                "https://api.telnyx.com/v2/messages", json=payload,
                headers={"Authorization": f"Bearer {key}"},
            )
        if res.status_code in (200, 201):
            mid = res.json().get("data", {}).get("id", "")
            logger.info("Checkout SMS sent via Telnyx: %s → %s", mid, phone)
            return {"sent": True, "method": "telnyx", "message_sid": mid}
        logger.error("Telnyx SMS error %d: %s", res.status_code, res.text[:300])
        return {"sent": False, "method": "telnyx", "reason": f"status_{res.status_code}"}
    except Exception as e:  # noqa: BLE001
        logger.error("Telnyx SMS send failed: %s", e)
        return {"sent": False, "method": "telnyx", "reason": str(e)}


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
