"""
Vapi voice-agent webhook — production, multi-tenant.

Vapi (https://vapi.ai) replaces the Telnyx/Pipecat streaming voice agent. One
server URL handles every event; the merchant is resolved per call from the
dialed number, so a single Vapi number config serves all merchants.

Events handled:
  - assistant-request   → look up the merchant by dialed DID, return a dynamic
                          assistant (their menu/greeting + submit_order tool).
  - tool-calls / function-call (submit_order) → run the real order pipeline
                          (normalize → POS create → route = Stripe pay-link + SMS).
  - end-of-call-report  → log.

Phone-agent modules live in a sibling dir (same sys.path trick as
stripe_connect). They're dep-light (no pipecat), so the backend can import them.
build_system_prompt lives in pipecat-heavy bot.py, so the prompt is rebuilt here.
"""
import logging
import os
import sys
from pathlib import Path

from fastapi import APIRouter, Request

logger = logging.getLogger("meridian.api.vapi")

router = APIRouter(prefix="/api/vapi", tags=["vapi"])

_PHONE_AGENT_DIR = str(Path(__file__).resolve().parents[3] / "services" / "phone_agent")
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

WEBHOOK_URL = os.getenv("PUBLIC_PAY_BASE", "https://api.meridian.tips").rstrip("/") + "/api/vapi/webhook"


# ── merchant resolution ──────────────────────────────────────────────

def _dialed_number(msg: dict) -> str:
    """The Meridian DID the customer called (maps to a merchant)."""
    call = msg.get("call", {}) or {}
    for src in (call.get("phoneNumber"), msg.get("phoneNumber")):
        if isinstance(src, dict) and src.get("number"):
            return src["number"]
    return ""


def _caller_number(msg: dict) -> str:
    call = msg.get("call", {}) or {}
    cust = call.get("customer", {}) or msg.get("customer", {}) or {}
    return cust.get("number", "") if isinstance(cust, dict) else ""


async def _resolve_config(dialed: str):
    """MerchantPhoneConfig for the dialed DID; demo config if unmapped."""
    from merchant_config import get_merchant_by_phone, get_merchant_config
    merchant_id = (await get_merchant_by_phone(dialed)) if dialed else None
    return await get_merchant_config(merchant_id or "demo")


def _system_prompt(config) -> str:
    """Mirror of build_system_prompt (bot.py is pipecat-heavy, can't import)."""
    menu = ""
    if getattr(config, "menu_items", None):
        lines = []
        for it in config.menu_items:
            sizes = ", ".join(it.get("sizes", []))
            line = f"- {it['name']}: ${it.get('price', 0):.2f}"
            if sizes:
                line += f" (sizes: {sizes})"
            if it.get("modifications"):
                line += f" [options: {', '.join(it['modifications'])}]"
            lines.append(line)
        menu = "\n\nMENU:\n" + "\n".join(lines)
    order_types = ", ".join(getattr(config, "order_types", ["pickup", "delivery"]))
    return (
        f"You are the AI phone assistant for {config.business_name}.\n"
        "Keep replies SHORT — 1-2 sentences. Warm and natural, not robotic. This is a phone call.\n\n"
        "RULES:\n"
        f"- Greet warmly: \"{config.greeting}\"\n"
        "- Take the order item by item; confirm name + size + quantity + modifications.\n"
        "- Read back the full order before submitting.\n"
        "- Only call submit_order AFTER the customer confirms it's correct.\n"
        f"- Order types: {order_types}.\n"
        "- If an item isn't on the menu, say so politely and suggest an alternative.\n"
        "- If the caller sounds frustrated, STOP, briefly apologize, ask them to repeat ONLY the wrong "
        "part, read it back, never argue."
        f"{menu}"
    )


_SUBMIT_ORDER_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_order",
        "description": "Call ONLY after the customer confirms the complete order is correct.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "order_type": {"type": "string", "enum": ["pickup", "delivery", "dine_in"]},
                "items": {"type": "array", "items": {"type": "object", "properties": {
                    "name": {"type": "string"}, "quantity": {"type": "integer"},
                    "size": {"type": "string"},
                    "modifications": {"type": "array", "items": {"type": "string"}},
                }, "required": ["name", "quantity"]}},
                "delivery_address": {"type": "string"},
            },
            "required": ["customer_name", "order_type", "items"],
        },
    },
    "server": {"url": WEBHOOK_URL},
}


def _assistant_for(config) -> dict:
    return {
        "name": f"{config.business_name} — Order Taker",
        "firstMessage": config.greeting or f"Thanks for calling {config.business_name}! What can I get for you?",
        "transcriber": {"provider": "deepgram", "model": "nova-3"},
        "voice": {"provider": "vapi", "voiceId": "Elliot"},
        "model": {"provider": "openai", "model": "gpt-4.1",
                  "messages": [{"role": "system", "content": _system_prompt(config)}],
                  "tools": [_SUBMIT_ORDER_TOOL]},
        "endCallFunctionEnabled": True,
    }


def _confirm(args: dict, routed: dict) -> str:
    items = args.get("items") or []
    n = sum(int(i.get("quantity", 1) or 1) for i in items)
    who = args.get("customer_name") or "there"
    otype = (args.get("order_type") or "pickup").replace("_", " ")
    base = f"Thanks {who}! Your {otype} order — {n} item{'s' if n != 1 else ''} — is in."
    if routed.get("sms_sent"):
        return base + " I've texted you a secure link to pay. See you soon!"
    return base + " It'll be ready shortly. See you soon!"


async def _place_order(args: dict, config, caller_phone: str) -> str:
    """Run the real order pipeline: normalize → POS create → route (Stripe + SMS)."""
    from order_normalizer import normalize_order
    from pos_connector import create_pos_order
    from order_router import route_order
    if caller_phone and not args.get("caller_phone"):
        args["caller_phone"] = caller_phone
    normalized = normalize_order(args, config)
    pos_token = getattr(config, "pos_access_token", "") or ""
    pos_loc = getattr(config, "pos_location_id", "") or ""
    if getattr(config, "pos_system", "") == "square" and not pos_token:
        pos_token = os.getenv("SQUARE_ACCESS_TOKEN", "")
        pos_loc = pos_loc or os.getenv("SQUARE_LOCATION_ID", "")
    pos_result = await create_pos_order(normalized, getattr(config, "pos_system", "") or "", pos_token, pos_loc)
    routed = await route_order(normalized, config, {"phone": caller_phone}, pos_result)
    logger.info("VAPI order placed: merchant=%s items=%d pos=%s sms=%s",
                config.merchant_id, len(normalized.get("items", [])),
                pos_result.get("success"), routed.get("sms_sent"))
    return _confirm(args, routed or {})


@router.post("/webhook")
async def vapi_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return {"received": True}
    msg = (payload or {}).get("message", {}) or {}
    mtype = msg.get("type", "")

    # Inbound call → hand Vapi the merchant's dynamic assistant.
    if mtype == "assistant-request":
        try:
            config = await _resolve_config(_dialed_number(msg))
            return {"assistant": _assistant_for(config)}
        except Exception as e:  # noqa: BLE001 — never strand the call
            logger.error("assistant-request failed: %s", e)
            return {"error": "Sorry, we couldn't connect your call. Please try again."}

    # Order submitted mid-call.
    if mtype in ("tool-calls",):
        results = []
        config = None
        for tc in msg.get("toolCallList", []) or msg.get("toolCalls", []) or []:
            fn = tc.get("function", {}) or {}
            args = fn.get("arguments", {}) or {}
            if isinstance(args, str):
                import json
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            if fn.get("name") == "submit_order":
                try:
                    if config is None:
                        config = await _resolve_config(_dialed_number(msg))
                    res = await _place_order(args, config, _caller_number(msg))
                except Exception as e:  # noqa: BLE001
                    logger.error("submit_order failed: %s", e)
                    res = "Your order is in — we'll follow up by text shortly."
                results.append({"toolCallId": tc.get("id"), "result": res})
            else:
                results.append({"toolCallId": tc.get("id"), "result": "ok"})
        return {"results": results}

    if mtype == "function-call":  # legacy shape
        fc = msg.get("functionCall", {}) or {}
        if fc.get("name") == "submit_order":
            try:
                config = await _resolve_config(_dialed_number(msg))
                return {"result": await _place_order(fc.get("parameters", {}) or {}, config, _caller_number(msg))}
            except Exception as e:  # noqa: BLE001
                logger.error("submit_order (legacy) failed: %s", e)
                return {"result": "Your order is in — we'll follow up by text shortly."}
        return {"result": "ok"}

    if mtype == "end-of-call-report":
        logger.info("VAPI end-of-call: ended=%s", msg.get("endedReason"))

    return {"received": True}
