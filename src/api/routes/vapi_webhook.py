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
import hmac
import logging
import os
import sys
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("meridian.api.vapi")

router = APIRouter(prefix="/api/vapi", tags=["vapi"])

_PHONE_AGENT_DIR = str(Path(__file__).resolve().parents[3] / "services" / "phone_agent")
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

WEBHOOK_URL = os.getenv("PUBLIC_PAY_BASE", "https://api.meridian.tips").rstrip("/") + "/api/vapi/webhook"

# Telnyx fallback: an existing Telnyx/Pipecat agent DID that Vapi forwards the
# call to when a merchant's voice ledger is underwater (revenue hasn't covered
# usage). Vapi's own card-on-file handles the GLOBAL float; this is the
# per-merchant policy gate. Disabled unless BOTH env vars are set — default is
# fail-open (always serve via Vapi).
# Shared secret Vapi sends as the `x-vapi-secret` header on every server request
# (set as server.secret on the assistant/phone-number). When set here, every
# inbound webhook must present it or it's rejected — closes the open-order hole.
# Unset → not enforced (safe rollout: deploy code, configure Vapi + this env,
# then enforcement turns on without a gap).
VAPI_SERVER_SECRET = os.getenv("VAPI_SERVER_SECRET", "").strip()

TELNYX_FALLBACK_NUMBER = os.getenv("TELNYX_FALLBACK_NUMBER", "").strip()
# Only forward when balance is at/below this many cents (negative = underwater).
# Unset → no gate. e.g. -2000 forwards once a merchant is $20 in the red.
_floor_raw = os.getenv("VOICE_BALANCE_FLOOR_CENTS", "").strip()
VOICE_BALANCE_FLOOR_CENTS = int(_floor_raw) if _floor_raw.lstrip("-").isdigit() else None

# Per-order fee = flat MERIDIAN_SERVICE_FEE_CENTS ($2.50). On top of that, calls
# longer than VOICE_INCLUDED_MIN minutes of AI time bill an overage of
# VOICE_OVERAGE_CENTS_PER_MIN ($0.45) per minute over the included block. The
# overage is computed at end-of-call (the order's Stripe fee is locked mid-call,
# before the duration is known), so it's tracked per-merchant in the voice ledger
# as billable revenue rather than added to the customer's order charge.
VOICE_INCLUDED_MIN = int(os.getenv("MERIDIAN_VOICE_INCLUDED_MIN", "3") or 3)
VOICE_OVERAGE_CENTS_PER_MIN = int(os.getenv("MERIDIAN_VOICE_OVERAGE_CENTS_PER_MIN", "45") or 45)


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
    """MerchantPhoneConfig for the dialed DID; demo config if unmapped.

    NB: in prod Supabase IS configured, so get_merchant_config("demo") returns
    None (no 'demo' row) rather than the demo fallback — guard against that
    explicitly or submit_order crashes on a None config."""
    from merchant_config import get_merchant_by_phone, get_merchant_config, _demo_config
    merchant_id = (await get_merchant_by_phone(dialed)) if dialed else None
    cfg = await get_merchant_config(merchant_id) if merchant_id else None
    return cfg or _demo_config(merchant_id or "demo")


def _system_prompt(config) -> str:
    """Build a polished, money-flow-showcasing call script for any merchant.

    Improvements over the previous version:
    - Renders size_prices correctly so per-size items (e.g. pizzas) show real
      prices instead of $0.00.
    - Adds ONE suggestive upsell if the caller hasn't added a drink or side.
    - Explicitly collects the delivery address when order_type == delivery.
    - Instructs the assistant to read back the complete order with the total
      before calling submit_order.
    - Tells the caller about the pay-by-text link + receipt after the order
      is placed, making the full money flow visible in every demo call.
    """
    menu_lines: list[str] = []
    if getattr(config, "menu_items", None):
        for it in config.menu_items:
            name = it.get("name", "item")
            size_prices: dict = it.get("size_prices") or {}
            price = it.get("price")
            topping_price = it.get("topping_price")
            sizes: list = it.get("sizes") or []
            modifications: list = it.get("modifications") or []

            if size_prices:
                # Per-size pricing (e.g. pizzas): "medium $14 / large $18 (+$2/topping)"
                price_parts = [
                    f"{s} ${size_prices[s]:.0f}"
                    for s in sizes
                    if s in size_prices
                ]
                line = f"- {name}: {' / '.join(price_parts)}"
                if topping_price:
                    line += f" (+${topping_price:.0f}/topping)"
            elif price:
                line = f"- {name}: ${float(price):.2f}"
                if sizes:
                    line += f" (sizes: {', '.join(sizes)})"
            else:
                line = f"- {name}"
                if sizes:
                    line += f" (sizes: {', '.join(sizes)})"

            if modifications:
                line += f" [options: {', '.join(modifications)}]"
            menu_lines.append(line)

    menu = ("\n\nMENU:\n" + "\n".join(menu_lines)) if menu_lines else ""
    order_types = ", ".join(getattr(config, "order_types", ["pickup", "delivery"]))
    business = config.business_name

    return (
        f"You are the AI phone order-taker for {business}.\n"
        "Keep every reply to 1-2 sentences — warm, friendly, phone-natural. Never robotic.\n\n"
        "CALL FLOW (follow this order every time):\n"
        f"1. Greet: \"{config.greeting}\"\n"
        "2. Take the order item by item. For each item confirm: name, size (if applicable), "
        "quantity, and any extra toppings or modifications.\n"
        "3. Once the caller finishes ordering, check whether they have added a drink or a side. "
        "If not, offer ONE natural upsell — e.g. 'Can I throw in a drink or a side for you?' "
        "Do this ONCE only; move on if they decline.\n"
        "4. Ask: pickup or delivery? Get their name.\n"
        "5. If delivery: ask for their delivery address before proceeding.\n"
        "6. Calculate the total (size price + per-topping charge × number of toppings for each "
        "item, then add sides and drinks). Read back the COMPLETE order — every item, size, "
        "and toppings — with the total, then ask 'Does that all look right?'\n"
        "7. Call submit_order ONLY after the customer confirms the order is correct.\n"
        "8. After submit_order returns, tell the caller: 'I've sent a secure payment link to "
        "your phone — you'll get a receipt once it goes through.'\n\n"
        "GUARD RULES:\n"
        f"- Available order types: {order_types}.\n"
        "- Delivery without an address → ask for the address before calling submit_order.\n"
        "- Off-menu items → say so warmly and suggest a similar item.\n"
        "- Mishear → ask the caller to repeat just THAT item; never restart the order from scratch.\n"
        "- Frustrated caller → brief apology, repeat back only the unclear part, ask once to clarify."
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
        return (
            base
            + " I've sent a secure payment link to your phone"
            + " — you'll get a receipt once it goes through. See you soon!"
        )
    return base + " We'll have it ready for you shortly — see you soon!"


async def _place_order(args: dict, config, caller_phone: str) -> str:
    """Run the real order pipeline: normalize → POS create → route (Stripe + SMS)."""
    from order_normalizer import normalize_order
    from pos_connector import create_pos_order
    from order_router import route_order
    if caller_phone and not args.get("caller_phone"):
        args["caller_phone"] = caller_phone
    normalized = normalize_order(args, config)
    # route_order only texts the pay link when the order carries caller_phone —
    # force it from the call's caller id so the SMS always fires.
    if caller_phone:
        normalized["caller_phone"] = caller_phone
    pos_token = getattr(config, "pos_access_token", "") or ""
    pos_loc = getattr(config, "pos_location_id", "") or ""
    if getattr(config, "pos_system", "") == "square" and not pos_token:
        pos_token = os.getenv("SQUARE_ACCESS_TOKEN", "")
        pos_loc = pos_loc or os.getenv("SQUARE_LOCATION_ID", "")
    pos_result = await create_pos_order(normalized, getattr(config, "pos_system", "") or "", pos_token, pos_loc)
    routed = await route_order(normalized, config, {"phone": caller_phone}, pos_result)
    logger.info("VAPI order placed: merchant=%s caller=%s items=%d pos=%s sms=%s",
                config.merchant_id, caller_phone or "?", len(normalized.get("items", [])),
                pos_result.get("success"), routed.get("sms_sent"))
    return _confirm(args, routed or {})


@router.post("/webhook")
async def vapi_webhook(request: Request):
    # Auth: reject anyone who can't present Vapi's shared secret. Fail-closed
    # only when the secret is configured (so the live line never breaks during
    # rollout). Without this, the order-placing webhook is open to the internet.
    if VAPI_SERVER_SECRET:
        presented = request.headers.get("x-vapi-secret", "")
        if not hmac.compare_digest(presented, VAPI_SERVER_SECRET):
            logger.warning("vapi_webhook rejected: missing/invalid x-vapi-secret")
            return JSONResponse(status_code=401, content={"error": "unauthorized"})
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
            # Voice-ledger gate: if this merchant is underwater past the floor,
            # forward the call to the Telnyx/Pipecat agent instead of burning
            # Vapi minutes. Fail-open — any error/None balance serves via Vapi.
            if TELNYX_FALLBACK_NUMBER and VOICE_BALANCE_FLOOR_CENTS is not None:
                try:
                    from ...services.voice_ledger import balance_cents
                    bal = await balance_cents(getattr(config, "merchant_id", "") or "")
                    if bal is not None and bal <= VOICE_BALANCE_FLOOR_CENTS:
                        logger.info("VAPI fallback→Telnyx: merchant=%s balance=%d¢ floor=%d¢",
                                    config.merchant_id, bal, VOICE_BALANCE_FLOOR_CENTS)
                        return {"destination": {"type": "number", "number": TELNYX_FALLBACK_NUMBER}}
                except Exception as e:  # noqa: BLE001 — fallback check never strands the call
                    logger.error("voice-ledger fallback check failed: %s", e)
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
        import math
        ended = msg.get("endedReason")
        # Vapi reports the all-in call cost (USD) + duration on the report message.
        call = msg.get("call", {}) or {}
        cost = msg.get("cost", call.get("cost"))
        call_id = call.get("id") or msg.get("callId") or ""
        dur_sec = (msg.get("durationSeconds") or call.get("durationSeconds")
                   or (msg.get("durationMinutes") or 0) * 60 or 0)
        dur_min = float(dur_sec) / 60.0
        logger.info("VAPI end-of-call: ended=%s cost=%s dur=%.1fmin call=%s",
                    ended, cost, dur_min, call_id)
        try:
            config = await _resolve_config(_dialed_number(msg))
            merchant_id = getattr(config, "merchant_id", "") or "demo"
            from ...services.voice_ledger import credit, debit
            # Our cost (Vapi) — debit.
            cents = int(round(float(cost) * 100)) if cost is not None else 0
            if cents > 0:
                await debit(merchant_id, cents, source="vapi_call",
                            ref=call_id or None, note=str(ended or ""))
            # Duration overage we bill the merchant: $0.45/min over 3 min (billed
            # per whole minute over the included block). Credit = billable revenue.
            over_min = max(0, math.ceil(dur_min) - VOICE_INCLUDED_MIN)
            overage = over_min * VOICE_OVERAGE_CENTS_PER_MIN
            if overage > 0:
                await credit(merchant_id, overage, source="duration_overage",
                             ref=call_id or None, note=f"{over_min}min over @ {dur_min:.1f}min")
                logger.info("Duration overage billed: merchant=%s %dmin over → %d¢",
                            merchant_id, over_min, overage)
        except Exception as e:  # noqa: BLE001 — accounting never affects the call
            logger.error("voice_ledger end-of-call failed: %s", e)

    return {"received": True}
