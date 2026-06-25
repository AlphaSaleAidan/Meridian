"""
SMS Text-to-Order — conversational ordering via SMS/text messages.

Customers text a business's Twilio number to browse the menu, build an order,
and receive a payment link — all without calling in.

Flow:
  1. Customer texts the business number
  2. Twilio webhook hits POST /sms/inbound
  3. We look up the merchant by the Twilio number
  4. Claude maintains a multi-turn conversation via SMS
  5. Customer builds their order through text messages
  6. On confirmation, we create the POS order + send a payment link
  7. Customer pays via the link

Conversation state is stored in-memory keyed by (merchant_id, customer_phone).
"""
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response

from merchant_config import MerchantPhoneConfig, get_merchant_config, get_merchant_by_phone
from order_normalizer import normalize_order
from pos_connector import create_pos_order
from payment_links import create_checkout
from sms_checkout import send_checkout_sms

# Credit metering lives in src/credits/. Add the project root to sys.path so
# this sidecar file can import it whether running standalone (python main.py)
# or mounted under the main API app.
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
try:
    from src.credits import (
        SMS_INBOUND,
        SMS_OUTBOUND,
        deduct,
        has_balance,
        InsufficientCredits,
    )
    _CREDITS_AVAILABLE = True
except ImportError:
    _CREDITS_AVAILABLE = False

logger = logging.getLogger("meridian.phone_agent.sms_order")

router = APIRouter(prefix="/sms", tags=["sms-order"])

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_SMS_MODEL", os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"))
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")

TWIML_CONTENT_TYPE = "application/xml"
SESSION_TTL = 1800  # 30 min idle timeout for SMS conversations
MAX_MESSAGES = 40

# In-memory SMS sessions: (merchant_phone, customer_phone) → session
_sms_sessions: dict[str, dict[str, Any]] = {}

SMS_ORDER_TOOLS = [
    {
        "name": "submit_order",
        "description": (
            "Call ONLY after the customer has confirmed their complete order, "
            "name, and order type (pickup/delivery). Include all items with quantities."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "Customer's name"},
                "order_type": {
                    "type": "string",
                    "enum": ["pickup", "delivery"],
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "size": {"type": "string"},
                            "modifications": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["name", "quantity"],
                    },
                },
                "delivery_address": {"type": "string"},
                "special_requests": {"type": "string"},
            },
            "required": ["customer_name", "order_type", "items"],
        },
    },
    {
        "name": "show_menu",
        "description": "Call when the customer asks to see the menu or what's available.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional category filter (e.g. 'drinks', 'sides')",
                },
            },
        },
    },
]


def _build_sms_system_prompt(config: MerchantPhoneConfig) -> str:
    menu_text = ""
    for item in config.menu_items:
        sizes = ", ".join(item.get("sizes", [])) if item.get("sizes") else ""
        mods = ", ".join(item.get("modifications", [])) if item.get("modifications") else ""
        line = f"  - {item['name']}: ${item['price']:.2f}"
        if sizes:
            line += f" (sizes: {sizes})"
        if mods:
            line += f" (options: {mods})"
        menu_text += line + "\n"

    order_types = ", ".join(config.order_types)

    return f"""You are a friendly SMS ordering assistant for {config.business_name}.
You are texting with a customer. Keep every reply SHORT — max 2-3 sentences per text.
Use casual texting tone but stay professional. No emojis overload.

MENU:
{menu_text}
ORDER TYPES: {order_types}

RULES:
- When someone first texts, welcome them and ask what they'd like to order.
- If they ask to see the menu, call show_menu and format it nicely in a text.
- Help them build their order item by item. Confirm quantities.
- When they say they're done, read back the full order with prices and total.
- Ask for their name and pickup or delivery.
- If delivery, ask for the address.
- Once they confirm everything, call submit_order.
- If they ask about something not on the menu, let them know politely.
- Keep texts concise — nobody wants to read a novel via text.
- ALWAYS include prices when mentioning items.
- Tax rate is {config.tax_rate * 100:.1f}%."""


def _session_key(merchant_phone: str, customer_phone: str) -> str:
    return f"{merchant_phone}:{customer_phone}"


def _cleanup_old_sessions():
    now = time.time()
    expired = [k for k, s in _sms_sessions.items() if now - s.get("ts", 0) > SESSION_TTL]
    for k in expired:
        del _sms_sessions[k]


async def _call_claude_sms(messages: list[dict], system: str) -> dict:
    if not ANTHROPIC_API_KEY:
        return {
            "content": [{"type": "text", "text": "Ordering is being set up. Please try again shortly!"}],
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 400,
                "system": system,
                "tools": SMS_ORDER_TOOLS,
                "messages": messages,
            },
        )

        if resp.status_code != 200:
            logger.error("Claude API error %d: %s", resp.status_code, resp.text[:500])
            return {
                "content": [{"type": "text", "text": "Sorry, having a brief issue. Text back in a moment!"}],
            }

        return resp.json()


def _extract_sms_response(api_result: dict) -> tuple[str, dict | None]:
    text_parts = []
    tool_call = None

    for block in api_result.get("content", []):
        if block.get("type") == "text":
            text_parts.append(block["text"])
        elif block.get("type") == "tool_use":
            tool_call = {
                "id": block["id"],
                "name": block["name"],
                "input": block["input"],
            }

    return " ".join(text_parts), tool_call


def _format_menu_sms(config: MerchantPhoneConfig, category: str = "") -> str:
    lines = [f"📋 {config.business_name} Menu\n"]
    cats: dict[str, list[str]] = {}

    for item in config.menu_items:
        cat = item.get("category", "Other")
        if category and cat.lower() != category.lower():
            continue
        if cat not in cats:
            cats[cat] = []
        cats[cat].append(f"  {item['name']} — ${item['price']:.2f}")

    for cat, items in cats.items():
        lines.append(f"{cat}:")
        lines.extend(items)
        lines.append("")

    lines.append("Text what you'd like to order!")
    return "\n".join(lines)


async def _send_sms_reply(to: str, from_: str, body: str):
    if not TWILIO_SID or not TWILIO_TOKEN:
        logger.info("SMS reply (no Twilio): to=%s body=%s", to, body[:100])
        return

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json",
                data={"To": to, "From": from_, "Body": body},
                auth=(TWILIO_SID, TWILIO_TOKEN),
                timeout=10,
            )
            if res.status_code in (200, 201):
                logger.info("SMS reply sent to %s", to)
            else:
                logger.error("Twilio SMS error %d: %s", res.status_code, res.text[:300])
    except Exception as e:
        logger.error("Failed to send SMS reply: %s", e)


async def _handle_order_submission(
    session: dict,
    order_input: dict,
    config: MerchantPhoneConfig,
    customer_phone: str,
    merchant_phone: str,
) -> str:
    order_input["caller_phone"] = customer_phone
    normalized = normalize_order(order_input, config)

    pos_result = await create_pos_order(
        normalized,
        config.pos_system,
        config.pos_access_token,
        config.pos_location_id,
    )

    payment_link_result: dict = {}
    if config.sms_checkout_enabled:
        pos_order_id = pos_result.get("pos_order_id", "")
        # Unified checkout: Stripe (CAD, card+Apple/Google Pay) when enabled +
        # configured, else falls back to the per-POS link inside create_checkout.
        payment_link_result = await create_checkout(
            order=normalized,
            merchant_config=config,
            pos_order_id=pos_order_id,
        )

    await _log_sms_order(normalized, pos_result, customer_phone)

    items = normalized.get("items", [])
    sym = "CA$" if normalized.get("currency") == "CAD" else "$"
    total = normalized.get("total", 0)
    order_type = normalized.get("order_type", "pickup")
    name = normalized.get("customer_name", "")

    item_lines = []
    for item in items:
        qty = item.get("quantity", 1)
        item_lines.append(f"  {qty}x {item['name']} — {sym}{item.get('line_total', 0):.2f}")

    reply = f"Order confirmed, {name}! 🎉\n\n"
    reply += "\n".join(item_lines)
    reply += f"\n\nTotal: {sym}{total:.2f} ({order_type})\n"

    pay_url = payment_link_result.get("url", "")
    if pay_url:
        reply += f"\nPay here: {pay_url}\n"

    if order_type == "pickup":
        reply += f"\nYour order will be ready in 15-20 min."
    elif order_type == "delivery":
        reply += f"\nEstimated delivery: 35-45 min."

    reply += f"\n\nThank you! — {config.business_name}"

    session["order_placed"] = True

    return reply


async def _log_sms_order(order: dict, pos_result: dict, customer_phone: str):
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_ANON_KEY", "")
    if not supabase_url or not supabase_key:
        return

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{supabase_url}/rest/v1/phone_orders",
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
                    "caller_phone": customer_phone,
                    "pos_system": order.get("pos_system", ""),
                    "pos_order_id": pos_result.get("pos_order_id", ""),
                    "pos_success": pos_result.get("success", False),
                    "source": "sms_order",
                },
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                timeout=10,
            )
    except Exception as e:
        logger.error("Failed to log SMS order: %s", e)


@router.post("/inbound")
async def handle_inbound_sms(request: Request):
    """Twilio SMS webhook — receives incoming text messages."""
    _cleanup_old_sessions()

    form = await request.form()
    customer_phone = form.get("From", "")
    merchant_phone = form.get("To", "")
    body = str(form.get("Body", "")).strip()
    message_sid = form.get("MessageSid", "")

    logger.info("SMS inbound: from=%s to=%s body='%s'", customer_phone, merchant_phone, body[:100])

    if not body:
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response/>',
            media_type=TWIML_CONTENT_TYPE,
        )

    merchant_id = await get_merchant_by_phone(merchant_phone)
    if not merchant_id:
        return _twiml_sms("Sorry, this number isn't set up for text ordering yet.")

    config = await get_merchant_config(merchant_id)
    if not config or not config.active:
        return _twiml_sms("Text ordering is currently unavailable. Please call instead.")

    if not getattr(config, "sms_ordering_enabled", True):
        return _twiml_sms(
            f"Text ordering isn't enabled for {config.business_name}. "
            f"Please call {config.phone_number} to place an order."
        )

    # Credit metering: one deduction per exchange (1 inbound processed +
    # 1 outbound reply). Multi-segment replies eat the extra cost — fine
    # at our margins, and keeps the merchant's mental model simple.
    is_demo = merchant_id == os.getenv("DEMO_MERCHANT_ID", "demo-merchant")
    if _CREDITS_AVAILABLE and not is_demo:
        exchange_cost = SMS_INBOUND.credits + SMS_OUTBOUND.credits
        try:
            await deduct(
                merchant_id=merchant_id,
                amount=exchange_cost,
                action_type="sms_exchange",
                action_id=message_sid,
                metadata={
                    "customer_phone": customer_phone,
                    "merchant_phone": merchant_phone,
                    "inbound_chars": len(body),
                },
            )
        except InsufficientCredits:
            logger.info("SMS refused — merchant %s has insufficient credits", merchant_id)
            # One last courtesy reply to inform the caller, then we stop responding.
            # We don't deduct for this notice since the merchant is already out.
            return _twiml_sms(
                "Sorry, this number's account is temporarily paused. "
                "Please contact the business directly."
            )

    key = _session_key(merchant_phone, customer_phone)
    session = _sms_sessions.get(key)

    restart_keywords = {"restart", "start over", "new order", "cancel"}
    if body.lower() in restart_keywords and session:
        del _sms_sessions[key]
        session = None

    if not session:
        system_prompt = _build_sms_system_prompt(config)
        session = {
            "messages": [],
            "system": system_prompt,
            "config": config,
            "customer_phone": customer_phone,
            "merchant_phone": merchant_phone,
            "ts": time.time(),
            "order_placed": False,
        }
        _sms_sessions[key] = session

    if session.get("order_placed"):
        if body.lower() in {"yes", "new order", "order again", "another"}:
            session["messages"] = []
            session["order_placed"] = False
            session["ts"] = time.time()
        else:
            return _twiml_sms(
                f"Your order is confirmed! Text 'new order' to place another. "
                f"— {config.business_name}"
            )

    session["ts"] = time.time()
    session["messages"].append({"role": "user", "content": body})

    if len(session["messages"]) > MAX_MESSAGES:
        session["messages"] = session["messages"][-MAX_MESSAGES:]

    api_result = await _call_claude_sms(session["messages"], session["system"])
    text, tool_call = _extract_sms_response(api_result)

    if tool_call:
        if tool_call["name"] == "submit_order":
            reply = await _handle_order_submission(
                session, tool_call["input"], config, customer_phone, merchant_phone,
            )
            session["messages"].append({"role": "assistant", "content": reply})
            return _twiml_sms(reply)

        elif tool_call["name"] == "show_menu":
            category = tool_call["input"].get("category", "")
            menu_text = _format_menu_sms(config, category)
            session["messages"].append({"role": "assistant", "content": menu_text})
            return _twiml_sms(menu_text)

    if not text:
        text = f"Welcome to {config.business_name}! Text 'menu' to see what we have, or just tell me what you'd like to order."

    session["messages"].append({"role": "assistant", "content": text})

    return _twiml_sms(text)


@router.post("/status")
async def handle_sms_status(request: Request):
    """Twilio SMS status callback."""
    form = await request.form()
    status = form.get("SmsStatus", form.get("MessageStatus", "unknown"))
    sid = form.get("SmsSid", form.get("MessageSid", "unknown"))
    logger.debug("SMS status: sid=%s status=%s", sid, status)
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response/>',
        media_type=TWIML_CONTENT_TYPE,
    )


@router.get("/health")
async def sms_order_health():
    return {
        "status": "ok",
        "mode": "sms_order",
        "active_sessions": len(_sms_sessions),
        "api_key_set": bool(ANTHROPIC_API_KEY),
        "twilio_configured": bool(TWILIO_SID and TWILIO_TOKEN),
        "model": ANTHROPIC_MODEL,
    }


def _twiml_sms(body: str) -> Response:
    escaped = (
        body
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return Response(
        content=f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escaped}</Message></Response>',
        media_type=TWIML_CONTENT_TYPE,
    )
