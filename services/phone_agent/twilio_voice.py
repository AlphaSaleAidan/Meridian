"""
Twilio Voice webhook handler for Meridian AI Phone Agent.

Uses Twilio's built-in speech recognition + TTS so no GPU or
local models are needed. Claude API provides the conversational brain.

Flow:
  1. Inbound call → Twilio hits POST /twilio/voice
  2. Return TwiML greeting + <Gather input="speech">
  3. Customer speaks → Twilio transcribes → POST /twilio/gather
  4. Transcript → Claude API → response text
  5. Return <Say response> + <Gather> → loop

Conversation state lives in-memory keyed by CallSid.
"""
import json
import logging
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response

from merchant_config import MerchantPhoneConfig, get_merchant_config

logger = logging.getLogger("meridian.phone_agent.twilio")

router = APIRouter(prefix="/twilio", tags=["twilio"])

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
DEMO_MERCHANT_ID = os.getenv("DEMO_MERCHANT_ID", "demo-merchant")

# In-memory call sessions: CallSid → conversation messages
_sessions: dict[str, dict[str, Any]] = {}

SESSION_TTL = 600  # clean up sessions older than 10 minutes

TWIML_CONTENT_TYPE = "application/xml"

ORDER_TOOLS = [
    {
        "name": "submit_order",
        "description": (
            "Call ONLY after the customer confirms their complete order. "
            "Summarize what they ordered, confirm the total, and then call this."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "Customer name"},
                "order_type": {
                    "type": "string",
                    "enum": ["pickup", "delivery", "dine_in"],
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
                "special_requests": {"type": "string"},
            },
            "required": ["customer_name", "order_type", "items"],
        },
    },
    {
        "name": "end_call",
        "description": "Call when the conversation is complete and no order was placed, or after order confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "enum": ["order_placed", "no_order", "wrong_number", "question_only"],
                },
                "farewell": {"type": "string", "description": "Goodbye message to say"},
            },
            "required": ["reason", "farewell"],
        },
    },
]


def _build_system_prompt(config: MerchantPhoneConfig) -> str:
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

    return f"""You are a friendly, efficient AI phone ordering assistant for {config.business_name}.
You are speaking to a customer on the phone. Keep responses SHORT and natural — 1-2 sentences max.
Sound warm and conversational, not robotic.

MENU:
{menu_text}
ORDER TYPES: {order_types}
{"Special instructions are allowed." if config.special_instructions_enabled else ""}

RULES:
- Greet the customer warmly and ask what they'd like to order.
- Help them build their order item by item.
- Suggest sizes or modifications when relevant.
- When they're done ordering, read back the full order with the total price.
- Ask for their name and whether it's pickup, delivery, or dine-in.
- If delivery, ask for the address.
- Once they confirm, call submit_order with the details.
- If they ask about something not on the menu, let them know politely.
- If they want to speak to a person, apologize and let them know you'll transfer them.
- Keep it brief. This is a phone call, not a chat. People don't want long responses."""


def _twiml_gather(say_text: str, timeout: int = 5) -> str:
    escaped = (
        say_text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="/twilio/gather" method="POST"
          speechTimeout="auto" timeout="{timeout}" language="en-US">
    <Say voice="Polly.Joanna">{escaped}</Say>
  </Gather>
  <Say voice="Polly.Joanna">I didn't catch that. Could you say that again?</Say>
  <Gather input="speech" action="/twilio/gather" method="POST"
          speechTimeout="auto" timeout="{timeout}" language="en-US" />
</Response>"""


def _twiml_say_hangup(text: str) -> str:
    escaped = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{escaped}</Say>
  <Hangup />
</Response>"""


def _cleanup_old_sessions():
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s.get("ts", 0) > SESSION_TTL]
    for sid in expired:
        del _sessions[sid]


async def _call_claude(messages: list[dict], system: str) -> dict:
    if not ANTHROPIC_API_KEY:
        return {
            "type": "text",
            "text": "I'm sorry, the ordering system is being set up. Please call back shortly!",
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
                "max_tokens": 300,
                "system": system,
                "tools": ORDER_TOOLS,
                "messages": messages,
            },
        )

        if resp.status_code != 200:
            logger.error("Claude API error %d: %s", resp.status_code, resp.text[:500])
            return {"type": "text", "text": "One moment please, let me think about that."}

        data = resp.json()
        return data


def _extract_response(api_result: dict) -> tuple[str, dict | None]:
    """Extract text response and optional tool call from Claude API result."""
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


@router.post("/voice")
async def handle_incoming_call(request: Request):
    """First webhook hit when a call comes in."""
    _cleanup_old_sessions()

    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    caller = form.get("From", "unknown")
    called = form.get("To", "unknown")

    logger.info("Incoming call: sid=%s from=%s to=%s", call_sid, caller, called)

    config = await get_merchant_config(DEMO_MERCHANT_ID)
    if not config:
        return Response(
            content=_twiml_say_hangup("Sorry, this number is not currently accepting orders. Goodbye."),
            media_type=TWIML_CONTENT_TYPE,
        )

    system_prompt = _build_system_prompt(config)

    _sessions[call_sid] = {
        "messages": [],
        "system": system_prompt,
        "config": config,
        "caller": caller,
        "ts": time.time(),
        "order": None,
    }

    greeting = config.greeting or f"Thank you for calling {config.business_name}! What can I get for you today?"

    return Response(
        content=_twiml_gather(greeting, timeout=8),
        media_type=TWIML_CONTENT_TYPE,
    )


@router.post("/gather")
async def handle_speech(request: Request):
    """Called each time Twilio captures speech from the caller."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    speech = form.get("SpeechResult", "")
    confidence = form.get("Confidence", "0")

    logger.info("Speech: sid=%s confidence=%s text='%s'", call_sid, confidence, speech)

    if not speech:
        return Response(
            content=_twiml_gather("I didn't quite catch that. What would you like to order?"),
            media_type=TWIML_CONTENT_TYPE,
        )

    session = _sessions.get(call_sid)
    if not session:
        config = await get_merchant_config(DEMO_MERCHANT_ID)
        system_prompt = _build_system_prompt(config) if config else "You are a restaurant ordering assistant."
        session = {
            "messages": [],
            "system": system_prompt,
            "config": config,
            "caller": form.get("From", "unknown"),
            "ts": time.time(),
            "order": None,
        }
        _sessions[call_sid] = session

    session["ts"] = time.time()
    session["messages"].append({"role": "user", "content": speech})

    api_result = await _call_claude(session["messages"], session["system"])

    if isinstance(api_result, dict) and "content" not in api_result:
        text = api_result.get("text", "I'm sorry, could you repeat that?")
        return Response(
            content=_twiml_gather(text),
            media_type=TWIML_CONTENT_TYPE,
        )

    text, tool_call = _extract_response(api_result)

    if tool_call:
        if tool_call["name"] == "submit_order":
            session["order"] = tool_call["input"]
            order_items = tool_call["input"].get("items", [])
            item_summary = ", ".join(
                f"{i.get('quantity', 1)} {i.get('name', 'item')}" for i in order_items
            )
            name = tool_call["input"].get("customer_name", "")
            order_type = tool_call["input"].get("order_type", "pickup")

            confirm_text = text or f"Great {name}! I've got {item_summary} for {order_type}."
            confirm_text += " Your order has been placed. Thank you for calling and enjoy your meal!"

            logger.info("Order placed: sid=%s order=%s", call_sid, json.dumps(tool_call["input"])[:500])

            session["messages"].append({"role": "assistant", "content": confirm_text})

            return Response(
                content=_twiml_say_hangup(confirm_text),
                media_type=TWIML_CONTENT_TYPE,
            )

        elif tool_call["name"] == "end_call":
            farewell = tool_call["input"].get("farewell", "Thank you for calling. Goodbye!")
            if text:
                farewell = f"{text} {farewell}"
            return Response(
                content=_twiml_say_hangup(farewell),
                media_type=TWIML_CONTENT_TYPE,
            )

    if not text:
        text = "I'm here! What would you like to order?"

    session["messages"].append({"role": "assistant", "content": text})

    # Keep conversation history manageable (last 20 turns)
    if len(session["messages"]) > 20:
        session["messages"] = session["messages"][-20:]

    return Response(
        content=_twiml_gather(text),
        media_type=TWIML_CONTENT_TYPE,
    )


@router.post("/status")
async def handle_status(request: Request):
    """Twilio status callback — logs call completion."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    status = form.get("CallStatus", "unknown")
    duration = form.get("CallDuration", "0")

    logger.info("Call status: sid=%s status=%s duration=%ss", call_sid, status, duration)

    session = _sessions.pop(call_sid, None)
    if session and session.get("order"):
        logger.info("Completed order for call %s: %s", call_sid, json.dumps(session["order"])[:500])

    return Response(content="<Response/>", media_type=TWIML_CONTENT_TYPE)


@router.get("/health")
async def twilio_health():
    return {
        "status": "ok",
        "mode": "twilio",
        "active_calls": len(_sessions),
        "api_key_set": bool(ANTHROPIC_API_KEY),
        "model": ANTHROPIC_MODEL,
        "demo_merchant": DEMO_MERCHANT_ID,
    }
