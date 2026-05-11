import logging
import os
import re

import httpx

logger = logging.getLogger("meridian.sms")

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_PHONE_NUMBER", "")


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"[^\d+]", "", phone)
    if not digits.startswith("+"):
        digits = digits.lstrip("1") if len(digits) == 11 and digits.startswith("1") else digits
        digits = f"+1{digits}"
    return digits


async def send_sms(phone: str, message: str) -> dict:
    if not (TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM):
        logger.info("Twilio not configured — SMS not sent to %s", phone)
        return {"sent": False, "method": "none", "reason": "not_configured"}

    normalized = _normalize_phone(phone)
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json",
                data={"To": normalized, "From": TWILIO_FROM, "Body": message},
                auth=(TWILIO_SID, TWILIO_TOKEN),
                timeout=10,
            )
            if res.status_code in (200, 201):
                sid = res.json().get("sid", "")
                logger.info("SMS sent via Twilio: %s -> %s", sid, normalized)
                return {"sent": True, "method": "twilio", "message_sid": sid}
            else:
                logger.error("Twilio error %d: %s", res.status_code, res.text[:300])
                return {"sent": False, "method": "twilio", "reason": f"status_{res.status_code}"}
    except Exception as e:
        logger.error("Twilio send failed: %s", e)
        return {"sent": False, "method": "twilio", "reason": str(e)}


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
