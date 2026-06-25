"""
Order-receipt SMS for the phone agent — extracted from bot.py so the logic is
unit-testable without importing the heavy pipecat stack (bot.py pulls pipecat at
module load, which isn't available in CI).

Telnyx-only here (the sidecar's voice provider, env already set); the full
Telnyx+Twilio client in src/sms isn't importable from this process.
"""
import logging
import os

logger = logging.getLogger("meridian.phone_agent.sms")


def order_receipt_text(order: dict, merchant_config) -> str:
    """Plain-text order receipt for the caller's SMS."""
    biz = getattr(merchant_config, "business_name", "") or "Your order"
    lines, total = [], 0.0
    for i in order.get("items", []):
        qty = int(i.get("quantity", 1) or 1)
        size = f" ({i['size']})" if i.get("size") else ""
        lines.append(f"{qty}x {i['name']}{size}")
        total += qty * float(i.get("unit_price", i.get("price", 0)) or 0)
    body = f"{biz} — your order:\n" + "\n".join(lines)
    if total > 0:
        body += f"\nTotal: ${total:.2f}"
    return body + "\nThanks for ordering by phone!"


async def send_order_sms(to: str, text: str, frm: str = "") -> None:
    """Best-effort: text the caller their order receipt via Telnyx. Never raises —
    a failed text must not affect the call or order. `frm` is the sending number —
    pass the merchant's own DID so a CA caller gets the text from the (domestic)
    number they called; falls back to the env number."""
    import httpx
    key = os.getenv("TELNYX_API_KEY", "")
    frm = frm or os.getenv("TELNYX_PHONE_NUMBER", "")
    if not (to and key and frm):
        logger.info("order receipt SMS skipped (missing to/key/from)")
        return
    payload = {"from": frm, "to": to, "text": text}
    profile = os.getenv("TELNYX_MESSAGING_PROFILE_ID", "")
    if profile:
        payload["messaging_profile_id"] = profile
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.telnyx.com/v2/messages", json=payload,
                headers={"Authorization": f"Bearer {key}"},
            )
        logger.info("order receipt SMS -> %s: %s", to, r.status_code)
    except Exception as e:  # noqa: BLE001 — best-effort, never break the call
        logger.warning("order receipt SMS failed for %s: %s", to, e)
