"""
Twilio Voice webhook routes for Meridian AI Phone Agent.

Twilio handles telephony, STT, and TTS. Claude API provides the brain.
No GPU, no local models, no Pipecat — just Twilio + Claude.

Webhook URL to configure in Twilio Console:
  Voice: https://api.meridian.tips/twilio/voice
  Status: https://api.meridian.tips/twilio/status
"""
import json
import logging
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response

logger = logging.getLogger("meridian.phone")

router = APIRouter(prefix="/twilio", tags=["phone-agent"])

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

_sessions: dict[str, dict[str, Any]] = {}
SESSION_TTL = 600
TWIML = "application/xml"

DEMO_MENU = [
    {"name": "Cheeseburger", "price": 12.99, "sizes": ["regular", "double"]},
    {"name": "Chicken Sandwich", "price": 11.49},
    {"name": "Fish Tacos", "price": 13.99, "sizes": ["2-piece", "3-piece"]},
    {"name": "Caesar Salad", "price": 9.99, "sizes": ["side", "full"]},
    {"name": "French Fries", "price": 4.99, "sizes": ["small", "medium", "large"]},
    {"name": "Onion Rings", "price": 5.99},
    {"name": "Coca-Cola", "price": 2.99, "sizes": ["small", "medium", "large"]},
    {"name": "Lemonade", "price": 3.49, "sizes": ["small", "medium", "large"]},
    {"name": "Milkshake", "price": 6.99, "options": ["chocolate", "vanilla", "strawberry"]},
    {"name": "Apple Pie", "price": 4.49},
]

TOOLS = [
    {
        "name": "submit_order",
        "description": "Call ONLY after customer confirms their complete order.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "order_type": {"type": "string", "enum": ["pickup", "delivery", "dine_in"]},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "size": {"type": "string"},
                            "modifications": {"type": "array", "items": {"type": "string"}},
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
        "description": "Call when conversation is done (no order, or after order placed).",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "enum": ["order_placed", "no_order", "wrong_number", "question_only"]},
                "farewell": {"type": "string"},
            },
            "required": ["reason", "farewell"],
        },
    },
]


def _menu_text() -> str:
    lines = []
    for item in DEMO_MENU:
        line = f"  - {item['name']}: ${item['price']:.2f}"
        if item.get("sizes"):
            line += f" (sizes: {', '.join(item['sizes'])})"
        if item.get("options"):
            line += f" (options: {', '.join(item['options'])})"
        lines.append(line)
    return "\n".join(lines)


SYSTEM_PROMPT = f"""You are a friendly AI phone ordering assistant for Meridian Demo Restaurant.
Keep responses SHORT — 1-2 sentences. Sound warm and natural, not robotic. This is a phone call.

MENU:
{_menu_text()}

RULES:
- Help the customer build their order item by item.
- Suggest sizes or options when relevant.
- When done, read back the order with total price, ask for their name and pickup/delivery/dine-in.
- If delivery, ask for address.
- Once confirmed, call submit_order.
- For items not on menu, let them know politely.
- Keep it brief — phone conversations should be quick."""


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _gather(say: str, timeout: int = 5) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="/twilio/gather" method="POST"
          speechTimeout="auto" timeout="{timeout}" language="en-US">
    <Say voice="Polly.Joanna">{_escape(say)}</Say>
  </Gather>
  <Say voice="Polly.Joanna">I didn't catch that. Could you say that again?</Say>
  <Gather input="speech" action="/twilio/gather" method="POST"
          speechTimeout="auto" timeout="{timeout}" language="en-US" />
</Response>"""


def _hangup(say: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{_escape(say)}</Say>
  <Hangup />
</Response>"""


def _cleanup():
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s.get("ts", 0) > SESSION_TTL]
    for sid in expired:
        del _sessions[sid]


async def _ask_claude(messages: list[dict]) -> dict:
    if not ANTHROPIC_API_KEY:
        return {"content": [{"type": "text", "text": "Our ordering system is starting up. Please call back in a moment!"}]}

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
                "system": SYSTEM_PROMPT,
                "tools": TOOLS,
                "messages": messages,
            },
        )
        if resp.status_code != 200:
            logger.error("Claude API %d: %s", resp.status_code, resp.text[:300])
            return {"content": [{"type": "text", "text": "One moment please."}]}
        return resp.json()


def _parse(result: dict) -> tuple[str, dict | None]:
    texts = []
    tool = None
    for block in result.get("content", []):
        if block.get("type") == "text":
            texts.append(block["text"])
        elif block.get("type") == "tool_use":
            tool = {"name": block["name"], "input": block["input"]}
    return " ".join(texts), tool


@router.post("/voice")
async def incoming_call(request: Request):
    _cleanup()
    form = await request.form()
    sid = form.get("CallSid", "unknown")
    caller = form.get("From", "unknown")
    logger.info("Incoming call: sid=%s from=%s", sid, caller)

    _sessions[sid] = {"messages": [], "caller": caller, "ts": time.time(), "order": None}

    return Response(
        content=_gather("Thank you for calling Meridian Demo Restaurant! What can I get for you today?", timeout=8),
        media_type=TWIML,
    )


@router.post("/gather")
async def speech_result(request: Request):
    form = await request.form()
    sid = form.get("CallSid", "unknown")
    speech = form.get("SpeechResult", "")

    logger.info("Speech: sid=%s text='%s'", sid, speech)

    if not speech:
        return Response(content=_gather("I didn't quite catch that. What would you like to order?"), media_type=TWIML)

    session = _sessions.get(sid)
    if not session:
        session = {"messages": [], "caller": form.get("From", ""), "ts": time.time(), "order": None}
        _sessions[sid] = session

    session["ts"] = time.time()
    session["messages"].append({"role": "user", "content": speech})

    result = await _ask_claude(session["messages"])
    text, tool = _parse(result)

    if tool:
        if tool["name"] == "submit_order":
            session["order"] = tool["input"]
            items = tool["input"].get("items", [])
            summary = ", ".join(f"{i.get('quantity', 1)} {i.get('name')}" for i in items)
            name = tool["input"].get("customer_name", "")
            otype = tool["input"].get("order_type", "pickup")
            msg = text or f"Great {name}!"
            msg += f" I've got {summary} for {otype}. Your order is placed! Thank you for calling, enjoy your meal!"
            logger.info("Order placed: sid=%s order=%s", sid, json.dumps(tool["input"])[:500])
            session["messages"].append({"role": "assistant", "content": msg})
            return Response(content=_hangup(msg), media_type=TWIML)

        elif tool["name"] == "end_call":
            farewell = tool["input"].get("farewell", "Thank you for calling! Goodbye.")
            if text:
                farewell = f"{text} {farewell}"
            return Response(content=_hangup(farewell), media_type=TWIML)

    if not text:
        text = "I'm here! What would you like to order?"

    session["messages"].append({"role": "assistant", "content": text})

    if len(session["messages"]) > 20:
        session["messages"] = session["messages"][-20:]

    return Response(content=_gather(text), media_type=TWIML)


@router.post("/status")
async def call_status(request: Request):
    form = await request.form()
    sid = form.get("CallSid", "unknown")
    status = form.get("CallStatus", "unknown")
    duration = form.get("CallDuration", "0")
    logger.info("Call ended: sid=%s status=%s duration=%ss", sid, status, duration)

    session = _sessions.pop(sid, None)
    if session and session.get("order"):
        logger.info("Completed order: %s", json.dumps(session["order"])[:500])

    return Response(content="<Response/>", media_type=TWIML)


@router.get("/health")
async def phone_health():
    return {
        "status": "ok",
        "active_calls": len(_sessions),
        "api_key_set": bool(ANTHROPIC_API_KEY),
        "model": ANTHROPIC_MODEL,
    }
