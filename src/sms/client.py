import logging
import os
import re

import httpx

logger = logging.getLogger("meridian.sms")

# Telnyx (primary — cheapest, good CA/US coverage)
TELNYX_API_KEY = os.getenv("TELNYX_API_KEY", "")
TELNYX_FROM = os.getenv("TELNYX_PHONE_NUMBER", "")
TELNYX_PROFILE_ID = os.getenv("TELNYX_MESSAGING_PROFILE_ID", "")

# Twilio (fallback)
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_PHONE_NUMBER", "")


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"[^\d+]", "", phone)
    if not digits.startswith("+"):
        digits = digits.lstrip("1") if len(digits) == 11 and digits.startswith("1") else digits
        digits = f"+1{digits}"
    return digits


async def _send_telnyx(to: str, message: str) -> dict:
    payload = {"from": TELNYX_FROM, "to": to, "text": message}
    if TELNYX_PROFILE_ID:
        payload["messaging_profile_id"] = TELNYX_PROFILE_ID
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.telnyx.com/v2/messages",
            json=payload,
            headers={"Authorization": f"Bearer {TELNYX_API_KEY}", "Content-Type": "application/json"},
            timeout=10,
        )
        if res.status_code in (200, 201):
            msg_id = res.json().get("data", {}).get("id", "")
            logger.info("SMS sent via Telnyx: %s -> %s", msg_id, to)
            return {"sent": True, "method": "telnyx", "message_id": msg_id}
        else:
            logger.error("Telnyx error %d: %s", res.status_code, res.text[:300])
            return {"sent": False, "method": "telnyx", "reason": f"status_{res.status_code}"}


async def _send_twilio(to: str, message: str) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json",
            data={"To": to, "From": TWILIO_FROM, "Body": message},
            auth=(TWILIO_SID, TWILIO_TOKEN),
            timeout=10,
        )
        if res.status_code in (200, 201):
            sid = res.json().get("sid", "")
            logger.info("SMS sent via Twilio: %s -> %s", sid, to)
            return {"sent": True, "method": "twilio", "message_sid": sid}
        else:
            logger.error("Twilio error %d: %s", res.status_code, res.text[:300])
            return {"sent": False, "method": "twilio", "reason": f"status_{res.status_code}"}


async def send_sms(phone: str, message: str) -> dict:
    normalized = _normalize_phone(phone)

    # Try Telnyx first
    if TELNYX_API_KEY and TELNYX_FROM:
        try:
            result = await _send_telnyx(normalized, message)
            if result["sent"]:
                return result
            logger.warning("Telnyx failed, trying Twilio fallback")
        except Exception as e:
            logger.warning("Telnyx exception, trying Twilio: %s", e)

    # Twilio fallback
    if TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM:
        try:
            return await _send_twilio(normalized, message)
        except Exception as e:
            logger.error("Twilio send failed: %s", e)
            return {"sent": False, "method": "twilio", "reason": str(e)}

    logger.info("No SMS provider configured — SMS not sent to %s", phone)
    return {"sent": False, "method": "none", "reason": "not_configured"}


async def send_invoice_sms(
    phone: str,
    owner_name: str,
    business_name: str,
    invoice_url: str | None,
    plan_label: str,
    amount_display: str,
) -> dict:
    first_name = owner_name.split()[0] if owner_name else ""

    if invoice_url:
        message = (
            f"Hi {first_name}! Your Meridian Analytics invoice for "
            f"{business_name} is ready.\n\n"
            f"{plan_label} - {amount_display}\n\n"
            f"Pay here: {invoice_url}\n\n"
            f"Questions? Reply to this text."
        )
    else:
        message = (
            f"Hi {first_name}! Your Meridian Analytics account for "
            f"{business_name} is set up.\n\n"
            f"{plan_label} - {amount_display}\n\n"
            f"Your invoice has been emailed. "
            f"Questions? Reply to this text."
        )

    return await send_sms(phone, message)
