"""
Twilio Voice webhook routes for Meridian AI Phone Agent.
Twilio handles telephony, STT, and TTS. SambaNova (primary) + local Qwen (fallback) provide the brain.
No external AI APIs required — Qwen 2.5 7B runs locally on port 8002.

Webhook URL to configure in Twilio Console:
    Voice: https://api.meridian.tips/twilio/voice
        Status: https://api.meridian.tips/twilio/status
        """
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import Response

from ...services.pos_connectors.order_dispatcher import create_pos_order
from ...services.pos_connectors.base import OrderResult
from ...db import get_db
from ...credits import (
    PHONE_CALL_PER_MIN,
    cost_for_phone_call,
    deduct,
    has_balance,
    InsufficientCredits,
)

logger = logging.getLogger("meridian.phone")

router = APIRouter(prefix="/twilio", tags=["phone-agent"])

DEMO_MERCHANT_ID = os.getenv("DEMO_MERCHANT_ID", "demo-merchant")

# Feature flag: when true, /voice returns <Connect><Stream> TwiML and the
# Pipecat sidecar handles the call over WebSocket. When false, the legacy
# stitched <Gather>+Polly path runs (instant rollback).
MEDIA_STREAMS_ENABLED = os.getenv("MEDIA_STREAMS_ENABLED", "0") == "1"
MEDIA_STREAM_HOST = os.getenv("MEDIA_STREAM_HOST", "api.meridian.tips")

# Telephony provider for the media-stream path. Telnyx and Twilio send
# different WS handshake envelopes, so the serializer + drain branch on this.
PHONE_PROVIDER = os.getenv("PHONE_PROVIDER", "twilio").lower()

_PHONE_AGENT_DIR = str(Path(__file__).resolve().parents[3] / "services" / "phone_agent")
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

# --- AI Provider config ---
# Primary: DeepSeek (OpenAI-compatible, cheap + good at multi-turn dialogue).
# Falls through to SambaNova then local Qwen if its key is unset or it errors.
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Secondary: SambaNova (OpenAI-compatible endpoint)
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "")
SAMBANOVA_BASE_URL = "https://api.sambanova.ai/v1"
SAMBANOVA_MODEL = os.getenv("SAMBANOVA_MODEL", "Meta-Llama-3.3-70B-Instruct")

# Fallback: Local Qwen 2.5 7B (same server as Garry)
QWEN_URL = os.getenv("GARRY_LLM_URL", "http://localhost:8002")

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
        line = f" - {item['name']}: ${item['price']:.2f}"
        if item.get("sizes"):
            line += f" (sizes: {', '.join(item['sizes'])})"
        if item.get("options"):
            line += f" (options: {', '.join(item['options'])})"
        lines.append(line)
    return "\n".join(lines)


SYSTEM_PROMPT = f"""You are a friendly AI phone ordering assistant for Meridian Demo Restaurant.
Keep responses SHORT - 1-2 sentences. Sound warm and natural, not robotic. This is a phone call.

MENU:
{_menu_text()}

RULES:
- Help the customer build their order item by item.
- Suggest sizes or options when relevant.
- When done, read back the order with total price, ask for their name and pickup/delivery/dine-in.
- If delivery, ask for address.
- Once confirmed, call submit_order.
- For items not on menu, let them know politely.
- Keep it brief - phone conversations should be quick."""


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# Common ordering phrases that bias speech recognition on every call.
_BASE_HINTS = [
    "yes", "no", "no thanks", "that's it", "that's all", "that's everything",
    "pickup", "delivery", "dine in", "add", "remove", "cancel",
    "small", "medium", "large", "one", "two", "three",
]


def _menu_hints(menu_items: list[dict]) -> str:
    """Comma-separated speech-recognition hints from the menu + common phrases.

    Telnyx biases its transcriber toward these phrases, so menu-specific terms
    ('milkshake', 'fish tacos', 'extra cheese') are recognized far more
    reliably than with a generic model. Caps the list — hints have practical
    limits and a huge list dilutes the bias.
    """
    terms: list[str] = list(_BASE_HINTS)
    for item in menu_items or []:
        if item.get("name"):
            terms.append(item["name"])
        terms.extend(item.get("sizes") or [])
        terms.extend(item.get("options") or item.get("modifications") or [])
    seen: set[str] = set()
    uniq: list[str] = []
    for t in terms:
        key = str(t).lower().strip()
        if key and key not in seen:
            seen.add(key)
            uniq.append(str(t))
    return ", ".join(uniq[:100])


def _gather(say: str, timeout: int = 5, speech_timeout: int = 1, hints: str = "") -> str:
    # Telnyx TeXML requires speechTimeout as an INTEGER (seconds of silence after
    # speech ends). The Twilio-ism speechTimeout="auto" is rejected by Telnyx and
    # makes Gather fire its action with an empty SpeechResult -> the reprompt loop.
    # transcriptionEngine only accepts "A" (Google, default) or "B" (Telnyx in-house);
    # the literal "Telnyx" is invalid. "B" stops Gather posting its action; use "A".
    #
    # The prompt <Say> is kept OUTSIDE <Gather>. When it is nested inside, the gather's
    # transcription window opens while the Polly greeting is still playing, and the
    # playback bleeds onto the inbound track -> the recognizer finalizes on the bot's
    # own words (e.g. " Thank you for calling.") instead of the caller. Playing <Say>
    # first means the gather only listens after the prompt finishes, so the inbound
    # track carries caller audio alone. (Trade-off: no barge-in, which we want here.)
    hints_attr = f' hints="{_escape(hints)}"' if hints else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{_escape(say)}</Say>
  <Gather input="speech" action="/twilio/gather" method="POST"
    speechTimeout="{speech_timeout}" timeout="{timeout}" language="en-US"
    transcriptionEngine="A"{hints_attr} />
  <Say voice="Polly.Joanna">I didn't catch that. Could you say that again?</Say>
  <Gather input="speech" action="/twilio/gather" method="POST"
    speechTimeout="{speech_timeout}" timeout="{timeout}" language="en-US"
    transcriptionEngine="A"{hints_attr} />
</Response>"""


def _listen(say: str, max_length: int = 15, timeout: int = 1, hints: str = "") -> str:
    # Per-turn capture via <Record> instead of <Gather input="speech">.
    # <Gather input="speech"> reads the default *inbound* track, which on these
    # Telnyx calls carries the bot's own Polly playback — so the caller is never
    # transcribed and the call loops on "I didn't catch that". <Gather> has no
    # track selector, so no Gather config fixes it. <Record> captures only the
    # audio that arrives while the bot is silent (the caller), then the /gather
    # action handler downloads it and transcribes it synchronously via the
    # Telnyx STT endpoint.
    #
    # CRITICAL for latency: Telnyx ends the recording on `timeout` seconds of
    # silence ONLY when transcription="true" — it uses the transcription engine
    # to detect silence. Without transcription enabled the timeout is ignored and
    # every turn runs the full maxLength (~15s of dead air). So we enable
    # transcription here purely for silence detection (the async transcription
    # callback is unused — we transcribe the recording synchronously in /gather).
    # timeout=1: end ~1s after the caller stops talking (snappy turn-taking for
    # a live demo). maxLength caps a runaway turn; finishOnKey lets a caller end
    # early.
    #
    # No trim="trim-silence": trimming makes Telnyx post-process the whole file
    # before delivering the recording, adding finalization latency. The STT
    # endpoint handles leading/trailing silence fine, so we skip it to get the
    # recording (and therefore the response) out faster.
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{_escape(say)}</Say>
  <Record action="/twilio/gather" method="POST" playBeep="false"
    maxLength="{max_length}" timeout="{timeout}"
    transcription="true" transcriptionEngine="A" transcriptionLanguage="en-US"
    finishOnKey="#" channels="single" format="mp3" />
</Response>"""


async def _transcribe_recording(recording_url: str) -> str:
    """Download a Telnyx call recording and transcribe it synchronously via the
    Telnyx STT endpoint (deepgram/nova-3). Returns the caller's text, or "" on
    any failure so the turn loop reprompts instead of crashing. The recording
    can lag the <Record> action callback by a moment, so the fetch is retried.
    """
    api_key = os.getenv("TELNYX_API_KEY", "")
    if not api_key or not recording_url:
        return ""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            audio = b""
            for _ in range(6):
                r = await client.get(recording_url)
                if r.status_code in (401, 403):
                    r = await client.get(
                        recording_url, headers={"Authorization": f"Bearer {api_key}"}
                    )
                if r.status_code == 200 and r.content:
                    audio = r.content
                    break
                await asyncio.sleep(0.4)
            if not audio:
                logger.warning("phone listen: recording not ready url=%s", recording_url)
                return ""
            res = await client.post(
                "https://api.telnyx.com/v2/ai/audio/transcriptions",
                data={
                    "model": "deepgram/nova-3",
                    "language": "en",
                    "response_format": "json",
                },
                files={"file": ("turn.mp3", audio, "audio/mpeg")},
                headers={"Authorization": f"Bearer {api_key}"},
            )
        if res.status_code != 200:
            logger.error("phone listen: Telnyx STT %d: %s", res.status_code, res.text[:200])
            return ""
        return (res.json().get("text") or "").strip()
    except Exception as e:
        logger.error("phone listen: transcription failed: %s", e)
        return ""


def _prompt(say: str, session: dict | None) -> str:
    """Render the next caller-capture turn, picking the capture method per call.

    Default is <Gather input="speech"> — Telnyx's real-time recognizer returns
    the transcript inline in the action POST, so it's the lowest-latency path
    (no recording finalize, no file download, no separate STT call) and it
    honors `hints` for menu-term accuracy. BUT the real-time recognizer may not
    be provisioned on every connection; when it isn't, Gather posts empty
    SpeechResults. twilio_gather detects repeated empties and flips
    session["capture"] to "record", after which we use the slower-but-reliable
    <Record> + synchronous Telnyx STT path. So a call self-heals to a working
    capture method instead of looping on "I didn't catch that"."""
    hints = (session or {}).get("hints", "")
    if session and session.get("capture") == "record":
        return _listen(say, hints=hints)
    return _gather(say, hints=hints)


def _hangup(say: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{_escape(say)}</Say>
  <Hangup />
</Response>"""


def _record_diag_twiml() -> str:
    # Flag-gated (PHONE_RECORD_DIAG=1) one-shot media diagnostic. Records the
    # caller (channels="dual": caller on channel A, bot on B) and asks Telnyx to
    # transcribe the recording. The bot is silent during the record window, so a
    # populated transcript proves the caller's audio reaches Telnyx and a Record-
    # based capture works -> we then rebuild the turn loop on <Record> instead of
    # <Gather input="speech"> (which has no track selector and reads the wrong
    # leg). NOTE: Telnyx TeXML <Record> uses transcription=/transcriptionCallback/
    # channels (NOT Twilio's transcribe/transcribeCallback/recordingChannels) and
    # trim only accepts "trim-silence" — the prior diagnostic used the Twilio
    # names + an invalid trim, so the verb never executed (no beep, no callback).
    # Revert by unsetting the env var.
    return """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">Diagnostic mode. After the beep, please say: testing one two three, I am the caller. Then wait.</Say>
  <Record maxLength="8" playBeep="true" trim="trim-silence" channels="dual"
    transcription="true" transcriptionEngine="A" transcriptionLanguage="en-US"
    recordingStatusCallback="/twilio/record_diag" recordingStatusCallbackMethod="POST"
    transcriptionCallback="/twilio/transcribe_diag" />
  <Say voice="Polly.Joanna">Thanks. Diagnostic complete. Goodbye.</Say>
  <Hangup />
</Response>"""


def _cleanup():
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s.get("ts", 0) > SESSION_TTL]
    for sid in expired:
        del _sessions[sid]


async def _ask_openai_tools(
    *,
    base_url: str,
    api_key: str,
    model: str,
    label: str,
    messages: list[dict],
    system_prompt: str,
    timeout: float = 20.0,
    temperature: float | None = None,
) -> dict | None:
    """Call an OpenAI-compatible chat endpoint with tool-calling.

    Returns Anthropic-style content blocks, or None on any failure so the
    caller can fall through to the next provider.
    """
    if not api_key:
        return None
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in TOOLS
    ]
    openai_messages = [{"role": "system", "content": system_prompt}] + messages
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": 300,
        "messages": openai_messages,
        "tools": openai_tools,
        "tool_choice": "auto",
    }
    if temperature is not None:
        payload["temperature"] = temperature
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code != 200:
                logger.warning("%s API %d: %s", label, resp.status_code, resp.text[:200])
                return None
            data = resp.json()
            choice = data["choices"][0]["message"]
            content = []
            if choice.get("content"):
                content.append({"type": "text", "text": choice["content"]})
            for tc in choice.get("tool_calls") or []:
                content.append({
                    "type": "tool_use",
                    "name": tc["function"]["name"],
                    "input": json.loads(tc["function"]["arguments"]),
                })
            return {"content": content}
    except Exception as exc:
        logger.warning("%s error: %s", label, exc)
        return None


async def _ask_deepseek(messages: list[dict], system_prompt: str = SYSTEM_PROMPT) -> dict | None:
    """Call DeepSeek (OpenAI-compatible). Low temperature keeps order-taking
    focused and reduces misheard-item drift. Returns None on failure."""
    return await _ask_openai_tools(
        base_url=DEEPSEEK_BASE_URL,
        api_key=DEEPSEEK_API_KEY,
        model=DEEPSEEK_MODEL,
        label="DeepSeek",
        messages=messages,
        system_prompt=system_prompt,
        timeout=15.0,
        temperature=0.3,
    )


async def _ask_sambanova(messages: list[dict], system_prompt: str = SYSTEM_PROMPT) -> dict | None:
    """Call SambaNova (OpenAI-compatible). Returns None on failure."""
    return await _ask_openai_tools(
        base_url=SAMBANOVA_BASE_URL,
        api_key=SAMBANOVA_API_KEY,
        model=SAMBANOVA_MODEL,
        label="SambaNova",
        messages=messages,
        system_prompt=system_prompt,
        timeout=20.0,
    )


async def _ask_qwen(messages: list[dict], system_prompt: str = SYSTEM_PROMPT) -> dict:
    """Call local Qwen 2.5 7B as fallback. Returns Anthropic-style content blocks."""
    openai_messages = [{"role": "system", "content": system_prompt}] + messages
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{QWEN_URL}/v1/chat/completions",
                json={
                    "messages": openai_messages,
                    "max_tokens": 300,
                    "temperature": 0.5,
                },
            )
            if resp.status_code != 200:
                logger.error("Qwen API %d: %s", resp.status_code, resp.text[:200])
                return {"content": [{"type": "text", "text": "One moment please."}]}
            data = resp.json()
            text = data["choices"][0]["message"].get("content", "")
            return {"content": [{"type": "text", "text": text}]}
    except Exception as exc:
        logger.warning("Qwen fallback error: %s", exc)
        return {"content": [{"type": "text", "text": "One moment please."}]}


async def _ask_ai(messages: list[dict], system_prompt: str = SYSTEM_PROMPT) -> dict:
    """DeepSeek primary, SambaNova secondary, local Qwen fallback."""
    result = await _ask_deepseek(messages, system_prompt)
    if result is not None:
        logger.info("AI response via DeepSeek")
        return result
    result = await _ask_sambanova(messages, system_prompt)
    if result is not None:
        logger.info("AI response via SambaNova")
        return result
    logger.warning("DeepSeek + SambaNova unavailable, falling back to local Qwen")
    return await _ask_qwen(messages, system_prompt)


def _parse(result: dict) -> tuple[str, dict | None]:
    texts = []
    tool = None
    for block in result.get("content", []):
        if block.get("type") == "text":
            texts.append(block["text"])
        elif block.get("type") == "tool_use":
            tool = {"name": block["name"], "input": block["input"]}
    return " ".join(texts).strip(), tool


async def _lookup_merchant_by_phone(phone_number: str) -> str | None:
    """Look up merchant_id by the Twilio phone number (To field) from Supabase."""
    config = await _fetch_merchant_config(phone_number)
    return config.get("merchant_id") if config else None


async def _fetch_merchant_config(phone_number: str) -> dict | None:
    """Fetch the full phone_agent_config row for the dialed number from Supabase.

    Returns the row (incl. menu_items, greeting, order_types, business_name) so
    the live turn-based path can take orders against the merchant's own menu
    instead of the hardcoded demo menu. Returns None if not found / not configured.
    """
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_ANON_KEY", "")
    if not supabase_url or not supabase_key or not phone_number:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(
                f"{supabase_url}/rest/v1/phone_agent_config"
                f"?phone_number=eq.{phone_number}&select=*",
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                },
            )
            if res.status_code == 200 and res.json():
                return res.json()[0]
    except Exception as e:
        logger.warning("Failed to fetch merchant config for %s: %s", phone_number, e)
    return None


def _menu_text_from(menu_items: list[dict]) -> str:
    lines = []
    for item in menu_items:
        try:
            line = f" - {item['name']}: ${float(item.get('price', 0)):.2f}"
        except (TypeError, ValueError, KeyError):
            line = f" - {item.get('name', 'item')}"
        sizes = item.get("sizes") or []
        if sizes:
            line += f" (sizes: {', '.join(sizes)})"
        opts = item.get("options") or item.get("modifications") or []
        if opts:
            line += f" (options: {', '.join(opts)})"
        lines.append(line)
    return "\n".join(lines)


def _build_merchant_prompt(config: dict) -> str:
    """Build a system prompt from a merchant's phone_agent_config row.

    Falls back to the demo menu text when the merchant has no menu_items yet so
    the agent always has something to work with.
    """
    business = config.get("business_name") or "our restaurant"
    menu_items = config.get("menu_items") or []
    order_types = config.get("order_types") or ["pickup", "delivery"]
    menu = _menu_text_from(menu_items) if menu_items else _menu_text()
    return f"""You are a friendly AI phone ordering assistant for {business}.
Keep responses SHORT - 1-2 sentences. Sound warm and natural, not robotic. This is a phone call.

MENU:
{menu}

RULES:
- Help the customer build their order item by item.
- Suggest sizes or options when relevant.
- When done, read back the order with total price, ask for their name and order type ({', '.join(order_types)}).
- If delivery, ask for their address.
- Once confirmed, call submit_order.
- For items not on the menu, let them know politely.
- Keep it brief - phone conversations should be quick."""


async def _log_call_start(call_sid: str, caller_phone: str, merchant_id: str = ""):
    """Log a new call to phone_call_logs."""
    try:
        db = get_db()
        await db.insert("phone_call_logs", {
            "merchant_id": merchant_id or "demo",
            "call_sid": call_sid,
            "caller_phone": caller_phone,
            "status": "in_progress",
            "transcript": [],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
    except Exception as e:
        logger.warning("Failed to log call start: %s", e)


async def _log_call_end(call_sid: str, status: str, order_data: dict | None = None):
    """Update call log on completion."""
    try:
        db = get_db()
        session = _sessions.get(call_sid, {})
        transcript = session.get("messages", [])
        duration = int(time.time() - session.get("ts", time.time()))
        payload: dict = {
            "status": status,
            "duration_seconds": duration,
            "transcript": transcript,
        }
        if order_data:
            payload["order_data"] = order_data
        await db.update(
            "phone_call_logs",
            payload,
            filters={"call_sid": f"eq.{call_sid}"},
        )
    except Exception as e:
        logger.warning("Failed to log call end: %s", e)


def _credits_paused_twiml() -> str:
    """TwiML for when the merchant has run out of credits.

    Spoken once, then hang up. The merchant sees the bounced call in their
    dashboard (status = 'credits_paused') with a top-up CTA.
    """
    msg = (
        "Sorry, this number's account is temporarily paused. "
        "Please contact the business directly to place your order."
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{_escape(msg)}</Say>
  <Hangup />
</Response>"""


async def _charge_for_call(merchant_id: str, call_sid: str, duration_seconds: int) -> None:
    """Post-call: deduct the metered cost. Logs but does not raise on failure."""
    cost = cost_for_phone_call(duration_seconds)
    if cost <= 0:
        return
    try:
        new_balance = await deduct(
            merchant_id=merchant_id,
            amount=cost,
            action_type="phone_call",
            action_id=call_sid,
            metadata={"duration_seconds": duration_seconds},
        )
        logger.info(
            "Charged %d credits for call %s (%ds) — new balance %d",
            cost, call_sid, duration_seconds, new_balance,
        )
    except InsufficientCredits:
        # Best-effort: the merchant ran the call past their balance during
        # the conversation. We still want the ledger to reflect what we
        # owe Twilio for — flag it for dashboard reconciliation.
        logger.warning(
            "Call %s for merchant %s went %d credits negative (over-run)",
            call_sid, merchant_id, cost,
        )
    except Exception as e:
        logger.error("Failed to charge for call %s: %s", call_sid, e)


def _media_stream_twiml(merchant_id: str, caller_phone: str) -> str:
    """TwiML that hands the call off to the Pipecat WebSocket."""
    stream_url = f"wss://{MEDIA_STREAM_HOST}/twilio/media-stream/{merchant_id}"
    safe_caller = _escape(caller_phone or "")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{stream_url}">
      <Parameter name="caller_phone" value="{safe_caller}" />
    </Stream>
  </Connect>
</Response>"""


@router.post("/voice")
async def twilio_voice(request: Request):
    """Initial call webhook — greet the caller.
    Looks up the merchant by the incoming Twilio phone number (To field).
    Falls back to DEMO_MERCHANT_ID if no merchant is found.

    When MEDIA_STREAMS_ENABLED, returns <Connect><Stream> so the Pipecat
    sidecar takes over via WebSocket. Otherwise runs the stitched
    Twilio-STT / SambaNova / Polly path.
    """
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    caller_phone = form.get("From", "")
    twilio_number = form.get("To", "")
    _cleanup()

    # Resolve the merchant + its phone-agent config from the dialed number, so
    # the live path takes orders against the merchant's own menu/greeting.
    config_row = None
    merchant_id = None
    if twilio_number:
        config_row = await _fetch_merchant_config(twilio_number)
    if config_row:
        merchant_id = config_row.get("merchant_id")
    if not merchant_id:
        merchant_id = DEMO_MERCHANT_ID
        logger.info("No merchant found for %s — using demo merchant %s", twilio_number, DEMO_MERCHANT_ID)

    await _log_call_start(call_sid, caller_phone, merchant_id=merchant_id)

    # Pre-call gate: refuse if the merchant can't cover even one minute.
    # Demo merchant bypasses (the canonical test number always works).
    if merchant_id != DEMO_MERCHANT_ID:
        if not await has_balance(merchant_id, PHONE_CALL_PER_MIN.credits):
            logger.info(
                "Refusing call %s — merchant %s has insufficient credits",
                call_sid, merchant_id,
            )
            await _log_call_end(call_sid, "credits_paused")
            return Response(content=_credits_paused_twiml(), media_type=TWIML)

    if MEDIA_STREAMS_ENABLED:
        logger.info("Routing call %s to Pipecat media stream (merchant=%s)", call_sid, merchant_id)
        return Response(content=_media_stream_twiml(merchant_id, caller_phone), media_type=TWIML)

    # Pull caller history once per call so every /gather turn reuses it.
    memory_block = ""
    if caller_phone:
        try:
            from caller_memory import build_memory_block_for
            memory_block = await build_memory_block_for(merchant_id, caller_phone)
        except Exception as e:
            logger.warning("caller memory lookup failed: %s", e)

    base_prompt = _build_merchant_prompt(config_row) if config_row else SYSTEM_PROMPT
    session_prompt = base_prompt + (f"\n\n{memory_block}" if memory_block else "")
    menu_items = (config_row or {}).get("menu_items") or DEMO_MENU
    hints = _menu_hints(menu_items)
    _sessions[call_sid] = {
        "messages": [],
        "ts": time.time(),
        "caller_phone": caller_phone,
        "merchant_id": merchant_id,
        "merchant_name": (config_row or {}).get("business_name", ""),
        "system_prompt": session_prompt,
        "hints": hints,
        "capture": "gather",  # start on the fast real-time path; auto-falls back to record
        "empty_count": 0,
    }
    greeting = (
        (config_row or {}).get("greeting")
        or "Thank you for calling Meridian Demo Restaurant! What can I get for you today?"
    )
    return Response(content=_prompt(greeting, _sessions[call_sid]), media_type=TWIML)


@router.post("/gather")
async def twilio_gather(request: Request):
    """Process caller speech and return AI response."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    # Telnyx posts the transcript as SpeechResult (Twilio-compatible). Keep a couple
    # of fallbacks in case a transcriptionEngine variant labels it differently.
    session = _sessions.setdefault(
        call_sid, {"messages": [], "ts": time.time(), "capture": "gather", "empty_count": 0}
    )

    # <Gather> posts the transcript inline as SpeechResult. <Record> (the fallback
    # capture) posts a RecordingUrl instead, which we transcribe synchronously.
    speech = (
        form.get("SpeechResult")
        or form.get("UnstableSpeechResult")
        or form.get("TranscriptionText")
        or ""
    ).strip()
    if not speech:
        recording_url = form.get("RecordingUrl") or form.get("RecordingUrls") or ""
        if recording_url:
            speech = await _transcribe_recording(recording_url)

    if not speech:
        session["empty_count"] = session.get("empty_count", 0) + 1
        # If the real-time recognizer keeps coming back empty, it's likely not
        # provisioned on this connection — switch this call to the reliable
        # <Record> + STT path so it stops looping.
        if session.get("capture") == "gather" and session["empty_count"] >= 2:
            session["capture"] = "record"
            logger.warning(
                "phone gather: %d empty results for %s — falling back to record capture",
                session["empty_count"], call_sid,
            )
        else:
            logger.warning(
                "phone gather: empty speech for call %s (capture=%s count=%d); keys=%s",
                call_sid, session.get("capture"), session["empty_count"], sorted(form.keys()),
            )
        return Response(
            content=_prompt("Sorry, I didn't catch that. What can I get for you?", session),
            media_type=TWIML,
        )

    session["empty_count"] = 0
    session["ts"] = time.time()
    session["messages"].append({"role": "user", "content": speech})

    result = await _ask_ai(session["messages"], session.get("system_prompt", SYSTEM_PROMPT))
    text, tool = _parse(result)

    if tool:
        if tool["name"] == "end_call":
            farewell = tool["input"].get("farewell", "Thank you for calling Meridian! Have a great day!")
            await _log_call_end(call_sid, "no_order")
            del _sessions[call_sid]
            return Response(content=_hangup(farewell), media_type=TWIML)

        if tool["name"] == "submit_order":
            items = tool["input"].get("items", [])
            order_summary = ", ".join(f"{i['quantity']}x {i['name']}" for i in items)

            order_result = await _dispatch_order(call_sid, session, tool["input"])
            order_id = order_result.order_id or f"MRD-{abs(hash(call_sid)) % 9000 + 1000}"

            confirmation = f"Great! I've placed your order for {order_summary}. Your order number is {order_id}. Thank you and enjoy your meal!"
            session["messages"].append({"role": "assistant", "content": confirmation})
            await _log_call_end(call_sid, "order_placed", tool["input"])
            del _sessions[call_sid]
            return Response(content=_hangup(confirmation), media_type=TWIML)

    reply = text or "Could you repeat that please?"
    session["messages"].append({"role": "assistant", "content": reply})
    return Response(content=_prompt(reply, session), media_type=TWIML)


async def _dispatch_order(call_sid: str, session: dict, order_input: dict) -> OrderResult:
    system_key = session.get("pos_system", os.getenv("DEFAULT_POS_SYSTEM", ""))
    if not system_key:
        return OrderResult(
            success=True,
            order_id=f"MRD-{abs(hash(call_sid)) % 9000 + 1000}",
            pos_system="demo",
        )

    order_data = {
        "customer_name": order_input.get("customer_name", ""),
        "order_type": order_input.get("order_type", "pickup"),
        "items": order_input.get("items", []),
        "special_instructions": order_input.get("special_requests", ""),
        "merchant_phone": session.get("merchant_phone"),
        "merchant_email": session.get("merchant_email"),
        "merchant_name": session.get("merchant_name", system_key),
    }

    try:
        return await create_pos_order(system_key, order_data, config=session.get("pos_config"))
    except Exception as e:
        logger.error(f"Order dispatch failed for {system_key}: {e}")
        return OrderResult(
            success=True,
            order_id=f"MRD-{abs(hash(call_sid)) % 9000 + 1000}",
            pos_system=system_key,
            fallback_used=True,
            fallback_reason=str(e)[:200],
        )


@router.post("/status")
async def twilio_status(request: Request):
    """Call status callback — clean up session, log, and charge credits."""
    form = await request.form()
    call_sid = form.get("CallSid", "")
    status = form.get("CallStatus", "")
    # Twilio sends duration on completion; fall back to session start_ts
    # so we still bill correctly if the duration param is missing.
    duration_str = form.get("CallDuration", "") or "0"
    try:
        duration_seconds = int(duration_str)
    except ValueError:
        duration_seconds = 0

    if status in ("completed", "failed", "busy", "no-answer", "canceled"):
        session = _sessions.get(call_sid, {})
        merchant_id = session.get("merchant_id", "")
        if duration_seconds == 0 and session.get("ts"):
            duration_seconds = int(time.time() - session["ts"])

        if call_sid in _sessions:
            await _log_call_end(call_sid, status)

        # Only charge for completed, billable calls. failed / busy / no-answer
        # cost us nothing meaningful and we don't pass them on.
        if status == "completed" and merchant_id and merchant_id != DEMO_MERCHANT_ID and duration_seconds > 0:
            await _charge_for_call(merchant_id, call_sid, duration_seconds)

        _sessions.pop(call_sid, None)
    return Response(content="", status_code=204)


@router.post("/record_diag")
async def twilio_record_diag(request: Request):
    """Flag-gated diagnostic: log the dual-channel recording URL + metadata so
    we can listen to whether the caller's channel actually carries audio."""
    form = await request.form()
    logger.warning(
        "phone record-diag RECORDING: call=%s url=%r duration=%r channels=%r keys=%s",
        form.get("CallSid"),
        form.get("RecordingUrl") or form.get("RecordingUrls"),
        form.get("RecordingDuration"),
        form.get("RecordingChannels"),
        sorted(form.keys()),
    )
    return Response(content="<Response/>", media_type=TWIML)


@router.post("/transcribe_diag")
async def twilio_transcribe_diag(request: Request):
    """Flag-gated diagnostic: log Telnyx's transcription of the recording. If
    this captures the caller's words but <Gather input=speech> does not, the
    fault is the Gather speech path, not the audio reaching Telnyx."""
    form = await request.form()
    logger.warning(
        "phone record-diag TRANSCRIPT: call=%s status=%r transcript=%r confidence=%r track=%r keys=%s",
        form.get("CallSid"),
        form.get("TranscriptionStatus") or form.get("Status"),
        form.get("Transcript") or form.get("TranscriptionText"),
        form.get("Confidence"),
        form.get("TranscriptionTrack") or form.get("Track"),
        sorted(form.keys()),
    )
    return Response(content="", status_code=204)


@router.websocket("/media-stream/{merchant_id}")
async def twilio_media_stream(websocket: WebSocket, merchant_id: str):
    """Twilio Media Streams WebSocket → Pipecat phone-agent pipeline.

    Pipecat reads mu-law 8 kHz audio off the WebSocket, runs Silero VAD →
    Moonshine STT → SambaNova LLM → Kokoro TTS, and writes mu-law audio back.
    Only active when MEDIA_STREAMS_ENABLED=1 and the merchant has a config.
    """
    await websocket.accept()
    logger.info("Media stream connected: merchant=%s", merchant_id)

    try:
        from bot import run_call_bot
        from merchant_config import get_merchant_config
    except ImportError as e:
        logger.error("Pipecat sidecar not importable: %s", e)
        await websocket.close(code=1011, reason="Phone agent not available")
        return

    config = await get_merchant_config(merchant_id)
    if not config:
        logger.warning("No config for merchant %s — rejecting", merchant_id)
        await websocket.close(code=1008, reason="Merchant not configured")
        return
    if not getattr(config, "active", True):
        logger.info("Phone agent disabled for merchant %s", merchant_id)
        await websocket.close(code=1008, reason="Phone agent disabled")
        return

    # Pre-call credit gate — same as the TwiML voice route. The /voice
    # webhook fires first and would have returned the paused TwiML, so
    # in practice we only reach here when the merchant had credits at
    # /voice time. This is a defense-in-depth check for race conditions.
    if merchant_id != DEMO_MERCHANT_ID:
        if not await has_balance(merchant_id, PHONE_CALL_PER_MIN.credits):
            logger.info("WebSocket refused — merchant %s has insufficient credits", merchant_id)
            await websocket.close(code=1008, reason="Insufficient credits")
            return

    # Drain the provider's prelude (connected → start) to capture the stream id
    # plus the id the serializer needs to address outbound media frames. Twilio
    # and Telnyx use different envelopes, so branch on PHONE_PROVIDER.
    stream_sid: str | None = None
    call_sid: str = ""
    caller_phone: str = ""
    call_control_id: str = ""
    outbound_encoding: str = "PCMU"
    try:
        for _ in range(5):
            msg = await websocket.receive_json()
            if msg.get("event") != "start":
                continue
            start = msg.get("start", {})
            if PHONE_PROVIDER == "telnyx":
                # Telnyx: stream_id + call_control_id; encoding under media_format.
                stream_sid = start.get("stream_id") or msg.get("stream_id")
                call_control_id = start.get("call_control_id", "")
                call_sid = call_control_id
                fmt = start.get("media_format", {}) or {}
                outbound_encoding = (fmt.get("encoding") or "PCMU").upper()
                params = start.get("custom_parameters", {}) or start.get("customParameters", {}) or {}
                caller_phone = params.get("caller_phone", "") or start.get("from", "")
            else:
                stream_sid = start.get("streamSid")
                call_sid = start.get("callSid", "")
                params = start.get("customParameters", {}) or {}
                caller_phone = params.get("caller_phone", "")
            break
    except Exception as e:
        logger.error("Failed to read %s start event: %s", PHONE_PROVIDER, e)
        await websocket.close(code=1011, reason="Bad media handshake")
        return

    if not stream_sid:
        logger.error("No stream id in %s handshake — aborting", PHONE_PROVIDER)
        await websocket.close(code=1011, reason="Missing stream id")
        return

    session_ref = call_sid or f"mstream-{int(time.time() * 1000)}"
    caller_info = {"phone": caller_phone, "session_ref": session_ref}

    # Populate session bookkeeping so /twilio/status can charge for the call.
    # Without this, the status handler reads an empty session and skips billing.
    if call_sid:
        _sessions[call_sid] = {
            "merchant_id": merchant_id,
            "ts": time.time(),
            "caller_phone": caller_phone,
            "mode": "media-streams",
        }

    try:
        await run_call_bot(
            websocket=websocket,
            merchant_id=merchant_id,
            session_ref=session_ref,
            merchant_config=config,
            caller_info=caller_info,
            stream_sid=stream_sid,
            call_sid=call_sid,
            provider=PHONE_PROVIDER,
            call_control_id=call_control_id,
            outbound_encoding=outbound_encoding,
        )
    except Exception as e:
        logger.error("Media stream pipeline error: %s", e, exc_info=True)
    finally:
        logger.info("Media stream ended: merchant=%s session=%s", merchant_id, session_ref)


@router.get("/health")
async def twilio_health():
    import importlib.util

    samba_ok = bool(SAMBANOVA_API_KEY)
    deepseek_ok = bool(DEEPSEEK_API_KEY)

    # Probe the media-stream import chain without executing heavy modules. These
    # install best-effort from requirements-ml.txt (torch deps can OOM-skip on
    # Railway), so this is the one-curl post-deploy check that the Pipecat path
    # will actually come up.
    def _have(mod: str) -> bool:
        try:
            return importlib.util.find_spec(mod) is not None
        except Exception:
            return False

    pipecat_ok = _have("pipecat")
    media_stream_ready = pipecat_ok and _have("silero_vad")

    return {
        "status": "ok",
        "mode": "media-streams" if MEDIA_STREAMS_ENABLED else "twilio-gather",
        "media_streams_enabled": MEDIA_STREAMS_ENABLED,
        "media_stream_host": MEDIA_STREAM_HOST if MEDIA_STREAMS_ENABLED else None,
        "media_stream_ready": media_stream_ready,
        "deps": {
            "pipecat": pipecat_ok,
            "silero_vad": _have("silero_vad"),
            "telnyx_serializer": _have("pipecat.serializers.telnyx"),
            "numpy": _have("numpy"),
            "scipy": _have("scipy"),
            "httpx": _have("httpx"),
        },
        "providers": {
            "phone": PHONE_PROVIDER,
            "stt": os.getenv("STT_PROVIDER", "local").lower(),
            "tts": os.getenv("TTS_PROVIDER", "local").lower(),
        },
        "telnyx_speech_configured": bool(os.getenv("TELNYX_API_KEY", "")),
        "primary_llm": "deepseek" if deepseek_ok else "sambanova" if samba_ok else "qwen-local",
        "llm_chain": [
            *(["deepseek"] if deepseek_ok else []),
            *(["sambanova"] if samba_ok else []),
            "qwen-local",
        ],
        "deepseek_configured": deepseek_ok,
        "deepseek_model": DEEPSEEK_MODEL,
        "sambanova_configured": samba_ok,
        "qwen_url": QWEN_URL,
        "active_sessions": len(_sessions),
    }
