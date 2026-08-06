"""
SMS checkout — sends order confirmation + payment link to the customer.
Sent via Telnyx (the voice provider, so its SMS creds are already on the box;
verified working for CA delivery).
"""
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("meridian.phone_agent.sms_checkout")

# Destination-aware from-number lives in src/sms/. Add the project root to
# sys.path so this sidecar can import it whether running standalone
# (python main.py) or mounted under the main API app.
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
try:
    from src.sms.from_number import sms_from_number
except ImportError:  # fail open — keep the pre-existing single-number behavior

    def sms_from_number(destination: str, default: str | None = None) -> str:  # type: ignore[misc]
        return default if default is not None else os.getenv("TELNYX_PHONE_NUMBER", "")


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
    sms_pay_template: str = "",
) -> dict:
    """
    Send order confirmation + payment link to the customer's phone.
    ``sms_pay_template`` is the merchant's optional custom body
    (phone_agent_config.sms_pay_template) — empty falls back to default copy.
    Returns {"sent": True/False, "method": "telnyx"|"none"}.
    """
    phone = order.get("caller_phone", "")
    if not phone:
        logger.warning("No phone number for checkout SMS")
        return {"sent": False, "method": "none", "reason": "no_phone"}

    return await send_sms(
        phone, _format_checkout_sms(order, payment_link, business_name, sms_pay_template)
    )


async def send_sms(to: str, body: str) -> dict:
    """Generic SMS send (staff alerts, notifications, checkout link) via Telnyx.
    Returns {"sent": bool, "method": "telnyx"|"none", ...}."""
    if not to or not body:
        return {"sent": False, "method": "none", "reason": "missing_to_or_body"}
    tkey, tfrom, _ = _telnyx_cfg()
    if tkey and tfrom:
        return await _send_via_telnyx(to, body)
    logger.info("No SMS gateway configured — SMS not sent to %s", to)
    return {"sent": False, "method": "none", "reason": "no_gateway"}


async def _send_via_telnyx(phone: str, message: str) -> dict:
    key, default_frm, profile = _telnyx_cfg()
    frm = sms_from_number(phone, default_frm)
    payload: dict[str, Any] = {"from": frm, "to": phone, "text": message}
    # TELNYX_MESSAGING_PROFILE_ID pins the default number's profile; a
    # country-specific DID lives on its own, so let Telnyx infer it from `from`.
    if profile and frm == default_frm:
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
    order: dict, payment_link: str, business_name: str, template: str = ""
) -> str:
    sym = "CA$" if (order.get("currency") or "").upper() == "CAD" else "$"
    total = order.get("total", 0)
    item_count = sum(i.get("quantity", 1) for i in order.get("items", []))
    order_type = order.get("order_type", "pickup").replace("_", " ").title()
    customer_name = order.get("customer_name", "").split()[0] if order.get("customer_name") else ""

    # Merchant-customized template (phone_agent_config.sms_pay_template).
    # Rendered with sequential .replace — NEVER .format — so braces in
    # customer-supplied values or in the template itself can't raise or be
    # re-interpreted as placeholders.
    if (template or "").strip():
        body = template
        # The payment link is the whole point of the SMS: if the merchant's
        # template omits {link}, append it so the customer can always pay.
        if "{link}" not in body:
            body = f"{body.rstrip()}\n\nPay here: {{link}}"
        replacements = {
            "{name}": customer_name,
            "{business}": business_name,
            "{total}": f"{sym}{total:.2f}",
            "{link}": payment_link,
        }
        # Single pass so substituted VALUES are never re-scanned for
        # placeholders (a customer named "{link}" stays literal).
        body = re.sub(
            r"\{(?:name|business|total|link)\}",
            lambda m: replacements[m.group(0)],
            body,
        )
        return body

    lines = []
    if customer_name:
        lines.append(f"Hi {customer_name}!")
    lines.append(f"Your {order_type.lower()} order from {business_name} is confirmed.")
    lines.append("")
    lines.append(f"{item_count} item{'s' if item_count != 1 else ''} — {sym}{total:.2f}")
    lines.append("")
    lines.append(f"Pay here: {payment_link}")
    lines.append("")
    lines.append(f"Thank you! — {business_name}")

    return "\n".join(lines)
