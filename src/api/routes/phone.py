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


def _demo_numbers() -> set[str]:
    """Inbound DIDs that legitimately answer as the demo assistant (the demo /
    test-kitchen line). Comma-separated E.164 in DEMO_PHONE_NUMBERS."""
    return {
        n.strip() for n in os.getenv("DEMO_PHONE_NUMBERS", "").split(",") if n.strip()
    }


def _unmapped_strict() -> bool:
    """When on, an inbound call to a DID we can't map to a real merchant is NOT
    served the demo assistant (which would silently route any order to the demo
    merchant, losing it). Instead the caller hears a polite 'not set up' message.
    DEFAULT OFF — legacy behavior (serve demo) is preserved until an operator
    populates DEMO_PHONE_NUMBERS and flips PHONE_UNMAPPED_STRICT=1."""
    return os.getenv("PHONE_UNMAPPED_STRICT", "0").strip().lower() in (
        "1", "true", "on", "yes",
    )

# Feature flag: when true, /voice returns <Connect><Stream> TwiML and the
# Pipecat sidecar handles the call over WebSocket. When false, the legacy
# stitched <Gather>+Polly path runs (instant rollback).
MEDIA_STREAMS_ENABLED = os.getenv("MEDIA_STREAMS_ENABLED", "0") == "1"
MEDIA_STREAM_HOST = os.getenv("MEDIA_STREAM_HOST", "api.meridian.tips")

# Default per-turn capture method. Telnyx's real-time <Gather input="speech">
# recognizer reads the inbound track that carries the bot's own Polly playback
# on these connections, so it returns empty SpeechResults and the call wastes
# two turns on "I didn't catch that" before self-healing to the <Record>+STT
# path. Default to "record" to skip that and capture the caller from turn one.
# Override to "gather" via env on any connection where the real-time recognizer
# is provisioned (lower latency). The empty-result self-heal still applies.
DEFAULT_CAPTURE = os.getenv("PHONE_CAPTURE_DEFAULT", "record")

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

# ── Polly TTS voice selection by language ──────────────────────────────────────
# French-Canadian merchants use Chantal (fr-CA) instead of Joanna (en-US) so
# after-hours messages, greetings, and reprompts are pronounced correctly.
_EN_VOICE = "Polly.Joanna"   # en-US (default)
_FR_VOICE = "Polly.Chantal"  # fr-CA


def _polly_voice(lang: str) -> str:
    """Return the Amazon Polly voice name for the given BCP-47 language tag."""
    return _FR_VOICE if (lang or "en").lower().startswith("fr") else _EN_VOICE


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
                "order_type": {"type": "string", "enum": ["pickup", "delivery", "dine_in", "reservation"]},
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

# Offered only when the merchant has configured a transfer number (see the
# session build in the call handler). Appended to TOOLS per-call so the demo
# and merchants without a transfer number keep the exact same tool set.
TRANSFER_TOOL = {
    "name": "transfer_call",
    "description": (
        "Hand the call off to a human. Call this when the caller asks for a "
        "person/manager, has a complaint or question you cannot answer, or "
        "explicitly asks to be transferred."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "handoff": {"type": "string", "description": "Short line to say before transferring, e.g. 'Sure, connecting you now.'"},
        },
        "required": ["handoff"],
    },
}


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
- When done, read back the order with total price, ask for their name and pickup/delivery — or reservation details (party size, time) if they're booking a table.
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


def _gather(say: str, timeout: int = 5, speech_timeout: int = 1, hints: str = "", voice: str = _EN_VOICE) -> str:
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
  <Say voice="{voice}">{_escape(say)}</Say>
  <Gather input="speech" action="/twilio/gather" method="POST"
    speechTimeout="{speech_timeout}" timeout="{timeout}" language="en-US"
    transcriptionEngine="A"{hints_attr} />
  <Say voice="{voice}">I didn't catch that. Could you say that again?</Say>
  <Gather input="speech" action="/twilio/gather" method="POST"
    speechTimeout="{speech_timeout}" timeout="{timeout}" language="en-US"
    transcriptionEngine="A"{hints_attr} />
</Response>"""


def _listen(say: str, max_length: int = 15, timeout: int = 1, hints: str = "", voice: str = _EN_VOICE) -> str:
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
  <Say voice="{voice}">{_escape(say)}</Say>
  <Record action="/twilio/gather" method="POST" playBeep="false"
    maxLength="{max_length}" timeout="{timeout}"
    transcription="true" transcriptionEngine="A" transcriptionLanguage="en-US"
    finishOnKey="#" channels="single" format="mp3" />
</Response>"""


def _dial(say: str, number: str, voice: str = _EN_VOICE) -> str:
    """TeXML to speak a handoff line then bridge the caller to a human.

    Telnyx <Dial> connects the inbound caller to the destination number; when
    that leg ends, the call hangs up. Used by the transfer_call tool so the
    agent can escalate to a person when the merchant has a transfer number set.
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="{voice}">{_escape(say)}</Say>
  <Dial>{_escape(number)}</Dial>
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
    voice = _polly_voice((session or {}).get("lang", "en"))
    if session and session.get("capture") == "record":
        return _listen(say, hints=hints, voice=voice)
    return _gather(say, hints=hints, voice=voice)


def _hangup(say: str, voice: str = _EN_VOICE) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="{voice}">{_escape(say)}</Say>
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
    tools: list[dict] = TOOLS,
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
        for t in tools
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


async def _ask_deepseek(
    messages: list[dict], system_prompt: str = SYSTEM_PROMPT, tools: list[dict] = TOOLS
) -> dict | None:
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
        tools=tools,
    )


async def _ask_sambanova(
    messages: list[dict], system_prompt: str = SYSTEM_PROMPT, tools: list[dict] = TOOLS
) -> dict | None:
    """Call SambaNova (OpenAI-compatible). Returns None on failure."""
    return await _ask_openai_tools(
        base_url=SAMBANOVA_BASE_URL,
        api_key=SAMBANOVA_API_KEY,
        model=SAMBANOVA_MODEL,
        label="SambaNova",
        messages=messages,
        system_prompt=system_prompt,
        timeout=20.0,
        tools=tools,
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


async def _ask_ai(
    messages: list[dict], system_prompt: str = SYSTEM_PROMPT, tools: list[dict] = TOOLS
) -> dict:
    """DeepSeek primary, SambaNova secondary, local Qwen fallback."""
    result = await _ask_deepseek(messages, system_prompt, tools)
    if result is not None:
        logger.info("AI response via DeepSeek")
        return result
    result = await _ask_sambanova(messages, system_prompt, tools)
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
            # Pass the filter via params so httpx percent-encodes the leading
            # "+" of E.164 numbers (+1782... -> %2B1782...). Interpolating it
            # raw into the query string lets PostgREST decode "+" as a space,
            # so the eq. filter never matches and every call falls through to
            # the demo merchant (wrong greeting/menu/transfer_number).
            res = await client.get(
                f"{supabase_url}/rest/v1/phone_agent_config",
                params={"phone_number": f"eq.{phone_number}", "select": "*"},
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


async def _fetch_merchant_config_by_id(merchant_id: str) -> dict | None:
    """Same as _fetch_merchant_config but keyed by merchant_id — used by the
    outbound test-call path (which dials OUT, so there's no inbound DID to resolve
    the merchant from). Returns None if not found."""
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_ANON_KEY", "")
    if not supabase_url or not supabase_key or not merchant_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(
                f"{supabase_url}/rest/v1/phone_agent_config",
                params={"merchant_id": f"eq.{merchant_id}", "select": "*"},
                headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
            )
            if res.status_code == 200 and res.json():
                return res.json()[0]
    except Exception as e:
        logger.warning("Failed to fetch merchant config by id %s: %s", merchant_id, e)
    return None


def _menu_text_from(menu_items: list[dict]) -> str:
    lines = []
    for item in menu_items:
        try:
            price = float(item.get("price", 0))
        except (TypeError, ValueError):
            price = 0.0
        # Extracted POS catalogs may not expose a price; render the name alone
        # rather than telling callers an item costs $0.00.
        line = f" - {item.get('name', 'item')}"
        if price > 0:
            line += f": ${price:.2f}"
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

    When the row contains a non-empty ``restaurant_brief``, an "ABOUT THIS
    RESTAURANT" section is appended after the menu with a guard instructing the
    agent to use it only for tone/warmth — the MENU remains the single source of
    truth for items and prices. An empty/absent brief leaves the prompt unchanged.
    """
    business = config.get("business_name") or "our restaurant"
    menu_items = config.get("menu_items") or []
    order_types = config.get("order_types") or ["pickup", "delivery"]
    menu = _menu_text_from(menu_items) if menu_items else _menu_text()

    # Per-restaurant personalization brief — injected ONLY when non-empty so an
    # unset brief leaves the prompt byte-for-byte identical (no regression).
    _brief = (config.get("restaurant_brief") or "").strip()
    brief_section = (
        "\n\nABOUT THIS RESTAURANT:\n"
        + _brief
        + "\n\nUse this only for tone, warmth, and recommending items that ARE on the menu. "
        "The MENU above is the single source of truth for items, sizes, and prices — "
        "never invent items, prices, hours, or facts from this description."
    ) if _brief else ""

    return f"""You are a friendly AI phone ordering assistant for {business}.
Keep responses SHORT - 1-2 sentences. Sound warm and natural, not robotic. This is a phone call.

MENU:
{menu}{brief_section}

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


def _menu_price(name: str, menu_items: list[dict], size: str = "") -> float:
    """Best-effort unit price for an LLM order item by matching the merchant
    menu (case-insensitive exact, then substring). Returns 0.0 when unmatched.
    Mirrors services/phone_agent/order_normalizer pricing without importing the
    sidecar into the API path."""
    n = (name or "").strip().lower()
    if not n:
        return 0.0
    # 3-tier match mirroring the sidecar normalizer's _find_menu_item:
    # exact name, then >=60% word overlap (handles multi-word items), then
    # substring. Pure aliases (e.g. "coke" vs "Coca-Cola") price at 0 here too —
    # display-only best effort, consistent with the streaming path.
    match = next((it for it in (menu_items or [])
                  if (it.get("name") or "").strip().lower() == n), None)
    if match is None:
        input_words = set(n.split())
        for it in menu_items or []:
            iw = set((it.get("name") or "").lower().split())
            if iw and len(iw & input_words) >= len(iw) * 0.6:
                match = it
                break
    if match is None:
        for it in menu_items or []:
            inm = (it.get("name") or "").strip().lower()
            if inm and (inm in n or n in inm):
                match = it
                break
    if not match:
        return 0.0
    size_prices = {str(k).lower(): float(v)
                   for k, v in (match.get("size_prices") or {}).items()}
    if size_prices:
        s = (size or "").strip().lower()
        return float(size_prices.get(s) or next(iter(size_prices.values()), 0.0))
    return float(match.get("price", 0.0) or 0.0)


def _price_order_for_display(order_input: dict, menu_items: list[dict],
                             tax_rate: float = 0.13) -> dict:
    """Attach unit_price/line_total to each item + compute subtotal/tax/total for
    the merchant dashboard. LLM order items carry name/quantity but no price, so
    turn-based phone orders otherwise render as $0.00. Display-only: does NOT
    change what the POS pipeline receives (that path prices independently)."""
    priced = []
    subtotal = 0.0
    for it in (order_input.get("items") or []):
        qty = max(1, int(it.get("quantity", 1) or 1))
        unit = _menu_price(it.get("name", ""), menu_items, it.get("size", ""))
        line = round(unit * qty, 2)
        subtotal += line
        priced.append({**it, "unit_price": unit, "line_total": line})
    subtotal = round(subtotal, 2)
    tax = round(subtotal * (tax_rate or 0.0), 2)
    return {**order_input, "items": priced, "subtotal": subtotal,
            "tax": tax, "total": round(subtotal + tax, 2)}


async def _log_call_end(call_sid: str, status: str, order_data: dict | None = None,
                        pos_result: dict | None = None):
    """Update call log on completion.

    `pos_result` carries the payment outcome (payment_status/sms_sent/
    payment_link/pos_order_id) so the merchant dashboard can show the correct
    paid/pending badge — without it every order rendered as 'none' regardless
    of whether a pay-link was texted or a card was charged.
    """
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
        if pos_result:
            payload["pos_result"] = pos_result
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


def _after_hours_twiml(message: str, lang: str = "en") -> str:
    """TwiML for a call that lands outside the merchant's business hours.

    Speaks the merchant's after-hours message (or a default) once, then hangs
    up. Logged with status 'after_hours' so it shows in the dashboard.
    `lang` selects the Polly voice (fr → Chantal, else Joanna).
    """
    voice = _polly_voice(lang)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="{voice}">{_escape(message)}</Say>
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
    """TwiML that hands the call off to the Pipecat WebSocket.

    Telnyx and Twilio differ for BIDIRECTIONAL streaming: Telnyx's <Stream>
    defaults to bidirectionalMode="mp3", which does NOT send the bot's audio back
    as raw PCMU — so the caller hears nothing. Telnyx needs bidirectionalMode="rtp"
    + PCMU/8k (what TelnyxFrameSerializer speaks), plus a trailing <Pause> to hold
    the call leg. Twilio's <Connect><Stream> is bidirectional by default.
    (Matches pipecat's telnyx-chatbot example.)
    """
    stream_url = f"wss://{MEDIA_STREAM_HOST}/twilio/media-stream/{merchant_id}"
    safe_caller = _escape(caller_phone or "")
    if PHONE_PROVIDER == "telnyx":
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{stream_url}" bidirectionalMode="rtp" bidirectionalCodec="PCMU" bidirectionalSamplingRate="8000">
      <Parameter name="caller_phone" value="{safe_caller}" />
    </Stream>
  </Connect>
  <Pause length="40"/>
</Response>"""
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
    # Outbound TEST calls dial OUT (no inbound merchant DID to resolve from), so the
    # placement script passes ?merchant_id= to target a specific merchant. This
    # override is the only behavior change for outbound; inbound calls (no query
    # param) resolve by the dialed number exactly as before.
    override_merchant = request.query_params.get("merchant_id")
    if override_merchant:
        merchant_id = override_merchant
        if override_merchant != DEMO_MERCHANT_ID:
            config_row = await _fetch_merchant_config_by_id(override_merchant)
        logger.info("Outbound/override merchant_id=%s (config %s)",
                    override_merchant, "found" if config_row else "demo-defaults")
    if not config_row and not override_merchant and twilio_number:
        config_row = await _fetch_merchant_config(twilio_number)
    if config_row and not merchant_id:
        merchant_id = config_row.get("merchant_id")
    if not merchant_id:
        # Unmapped inbound DID. Serving the demo assistant here means any order
        # the caller places is routed to the DEMO merchant — the real business
        # never sees it. Default (legacy) keeps serving demo so the demo/test
        # line and any transient lookup miss are unaffected; but with
        # PHONE_UNMAPPED_STRICT on, a DID that is NOT an allow-listed demo line
        # gets a polite "not set up" hangup instead of silently swallowing an
        # order into the demo merchant.
        if _unmapped_strict() and twilio_number and twilio_number not in _demo_numbers():
            logger.error(
                "Unmapped inbound DID %s and strict mode on — refusing to take an "
                "order to the demo merchant.", twilio_number,
            )
            await _log_call_end(call_sid, "unmapped_number")
            return Response(
                content=_hangup(
                    "Thanks for calling. This number isn't set up to take orders "
                    "yet. Please try again later or contact the business directly."
                ),
                media_type=TWIML,
            )
        merchant_id = DEMO_MERCHANT_ID
        logger.warning("No merchant found for %s — serving demo merchant %s (unmapped DID)",
                       twilio_number, DEMO_MERCHANT_ID)

    await _log_call_start(call_sid, caller_phone, merchant_id=merchant_id)

    # Merchant language (en default; 'fr…' for CA-French). Defined here — before
    # the after-hours gate — because that gate passes it to _after_hours_twiml;
    # it was previously only assigned further down, so an after-hours call to a
    # real merchant raised NameError and 500'd instead of playing the message.
    merchant_lang = ((config_row or {}).get("language") or "en").lower()

    # After-hours gate: if the merchant has configured BOTH business hours and a
    # timezone and we're currently outside them, play their after-hours message
    # and hang up instead of taking an order. Only non-demo merchants who opted
    # in (both fields set) are gated — is_open_now returns True otherwise, so the
    # default and unconfigured merchants are unchanged.
    if merchant_id != DEMO_MERCHANT_ID and config_row:
        from merchant_config import is_open_now

        if not is_open_now(config_row.get("business_hours"), config_row.get("business_timezone")):
            logger.info("Call %s after-hours for merchant %s — playing closed message", call_sid, merchant_id)
            await _log_call_end(call_sid, "after_hours")
            msg = (config_row.get("after_hours_message") or "").strip() or (
                f"Thanks for calling {config_row.get('business_name') or 'us'}. "
                "We're currently closed. Please call back during our business hours."
            )
            return Response(content=_after_hours_twiml(msg, lang=merchant_lang), media_type=TWIML)

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

    # Per-merchant opt-in: stream only when the global switch is on AND this
    # merchant has streaming_enabled (default off, migration 024). Everyone else
    # stays on the proven turn-based path — so rollout is one merchant at a time.
    # The demo merchant can be opted in via STREAMING_TEST_DEMO=1 for live
    # verification without needing a DB row.
    #
    # English-only: the NVCF-hosted Nemotron streaming ASR serves en-US only, so a
    # French merchant must stay on the turn-based path (which transcribes FR) until
    # a French streaming ASR is wired. We never route a 'fr*' merchant to streaming
    # even if the flag is set — that would silently mis-transcribe the call.
    streaming_on = MEDIA_STREAMS_ENABLED and not merchant_lang.startswith("fr") and (
        bool((config_row or {}).get("streaming_enabled"))
        or (merchant_id == DEMO_MERCHANT_ID and os.getenv("STREAMING_TEST_DEMO") == "1")
    )
    if MEDIA_STREAMS_ENABLED and merchant_lang.startswith("fr") and (config_row or {}).get("streaming_enabled"):
        logger.info("Merchant %s is French — keeping on turn-based path (streaming ASR is en-US only)", merchant_id)
    if streaming_on:
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
        "capture": DEFAULT_CAPTURE,  # record by default; auto-falls back from gather on empties
        "empty_count": 0,
        # Only set when the merchant configured a transfer number; gates the
        # transfer_call tool so the demo and unconfigured merchants are unchanged.
        "transfer_number": ((config_row or {}).get("transfer_number") or "").strip(),
        # POS fields stashed from the config row now (already fetched) so the
        # order dispatch can resolve a connection without re-reading config. The
        # pos_connections fallback lookup is done lazily at order time, not here,
        # to keep the greeting off the POS lookup's latency.
        "pos_system_manual": ((config_row or {}).get("pos_system") or "").strip(),
        "pos_token_manual": ((config_row or {}).get("pos_access_token") or "").strip(),
        "pos_location_id": ((config_row or {}).get("pos_location_id") or "").strip(),
        # Owner's cell (their human-handoff number) doubles as the destination for
        # the SMS/email order ticket when a POS push falls back.
        "merchant_phone": ((config_row or {}).get("transfer_number") or "").strip(),
        "merchant_email": ((config_row or {}).get("merchant_email") or "").strip(),
        # Language tag for Polly voice selection and CA disclosure.
        "lang": merchant_lang,
        # Menu (with prices) + tax rate stashed so the turn-based order dispatch
        # can price the captured order for the dashboard (LLM items carry no
        # price, so orders otherwise render as $0.00).
        "menu_items": menu_items,
        "tax_rate": float((config_row or {}).get("tax_rate", 0.13) or 0.13),
    }
    greeting = (
        (config_row or {}).get("greeting")
        or "Thank you for calling Meridian Demo Restaurant! What can I get for you today?"
    )
    # Fix CA-2: mandatory PIPEDA/Law 25 AI + recording disclosure for Canadian
    # merchants. Prepended by the backend so merchants cannot omit it by editing
    # their greeting. Triggered when language is French (fr*) or Canadian English
    # (en-ca / en_ca) and the caller is on a real (non-demo) merchant line.
    is_ca_merchant = merchant_lang.startswith("fr") or "ca" in merchant_lang
    if is_ca_merchant and merchant_id != DEMO_MERCHANT_ID:
        biz_name = (config_row or {}).get("business_name") or "this business"
        ca_disclosure = (
            f"Hi, you've reached {biz_name}. "
            "I'm an automated assistant and this call may be recorded."
        )
        greeting = ca_disclosure + " " + greeting
    return Response(content=_prompt(greeting, _sessions[call_sid]), media_type=TWIML)


@router.post("/gather")
async def twilio_gather(request: Request):
    """Process caller speech and return AI response."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    # Telnyx posts the transcript as SpeechResult (Twilio-compatible). Keep a couple
    # of fallbacks in case a transcriptionEngine variant labels it differently.
    session = _sessions.setdefault(
        call_sid, {"messages": [], "ts": time.time(), "capture": DEFAULT_CAPTURE, "empty_count": 0}
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

    # Offer the human-handoff tool only when this merchant has a transfer number.
    transfer_number = (session.get("transfer_number") or "").strip()
    tools = TOOLS + [TRANSFER_TOOL] if transfer_number else TOOLS
    result = await _ask_ai(session["messages"], session.get("system_prompt", SYSTEM_PROMPT), tools)
    text, tool = _parse(result)

    if tool:
        _sess_voice = _polly_voice(session.get("lang", "en"))
        if tool["name"] == "transfer_call":
            handoff = tool["input"].get("handoff", "One moment, connecting you now.")
            if transfer_number:
                await _log_call_end(call_sid, "transferred")
                del _sessions[call_sid]
                return Response(content=_dial(handoff, transfer_number, voice=_sess_voice), media_type=TWIML)
            # No number on file: don't drop the call — keep the conversation going.
            session["messages"].append({"role": "assistant", "content": handoff})
            return Response(content=_prompt(handoff, session), media_type=TWIML)

        if tool["name"] == "end_call":
            farewell = tool["input"].get("farewell", "Thank you for calling Meridian! Have a great day!")
            await _log_call_end(call_sid, "no_order")
            del _sessions[call_sid]
            return Response(content=_hangup(farewell, voice=_sess_voice), media_type=TWIML)

        if tool["name"] == "submit_order":
            items = tool["input"].get("items", [])
            order_summary = ", ".join(f"{i['quantity']}x {i['name']}" for i in items)

            order_result = await _dispatch_order(call_sid, session, tool["input"])

            # Order integrity: never confirm an order that didn't actually reach
            # the merchant. If dispatch failed, tell the caller honestly and flag
            # it for staff instead of reading back a fabricated order number.
            if not getattr(order_result, "success", False):
                logger.error(
                    "submit_order FAILED call=%s reason=%s items=%s",
                    call_sid, getattr(order_result, "fallback_reason", "") or "unknown", order_summary,
                )
                await _log_call_end(call_sid, "order_failed", tool["input"])
                _sessions.pop(call_sid, None)
                apology = (
                    "I'm so sorry — I'm having trouble sending your order to the "
                    "kitchen right now. I've flagged it for the team. Please try "
                    "calling back in a few minutes and we'll get you taken care of."
                )
                return Response(content=_hangup(apology, voice=_sess_voice), media_type=TWIML)

            order_id = order_result.order_id or f"MRD-{abs(hash(call_sid)) % 9000 + 1000}"

            # Menu-price the captured order for the dashboard (LLM items carry no
            # price → every phone order rendered as $0.00). Display-only: the POS
            # pipeline prices independently in _dispatch_order/create_pos_order.
            _priced_order = _price_order_for_display(
                tool["input"], session.get("menu_items") or [],
                session.get("tax_rate", 0.13),
            )

            # PAY ON THE PHONE (keypad backup): when enabled + the merchant takes
            # payment up front, collect the card on the call before confirming, so
            # the kitchen only ever sees a paid order (anti-scam). Gated by
            # PHONE_CARD_PAYMENT — default off, so live behavior is unchanged.
            try:
                from card_on_phone import CARD_PAYMENT_ENABLED, start_capture
            except ImportError:
                CARD_PAYMENT_ENABLED = False
            payment_mode = session.get("payment_mode", "pay_now")
            if CARD_PAYMENT_ENABLED and payment_mode == "pay_now":
                # Charge the menu-priced total (incl. tax). The old per-item
                # i["price"] sum was always 0 (LLM items have no price), so
                # card-on-phone would have captured $0.
                amount_cents = int(round(_priced_order.get("total", 0.0) * 100))
                start_capture(
                    call_sid,
                    order_ref=order_id,
                    merchant_id=session.get("merchant_id", ""),
                    amount_cents=amount_cents,
                    caller_phone=session.get("caller_phone", ""),
                )
                await _log_call_end(
                    call_sid, "order_placed_awaiting_card", _priced_order,
                    pos_result={"payment_status": "pending", "pos_order_id": order_id},
                )
                # Keep the session alive through the payment IVR.
                say = (f"Great — that's {order_summary}, order number {order_id}. "
                       f"Now let's take payment to lock it in.")
                return Response(content=f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="{_sess_voice}">{_escape(say)}</Say>
  <Redirect method="POST">/twilio/pay/start</Redirect>
</Response>""", media_type=TWIML)

            # Fix 1: no-POS SMS path tells caller a link was texted instead of
            # falsely claiming the order hit a kitchen.
            if getattr(order_result, "pos_system", "") == "sms_link":
                confirmation = (
                    f"Got it! I've texted a payment link to your phone for {order_summary}. "
                    f"Your reference is {order_id}. Check your texts to complete the order!"
                )
            else:
                confirmation = f"Great! I've placed your order for {order_summary}. Your order number is {order_id}. Thank you and enjoy your meal!"
            session["messages"].append({"role": "assistant", "content": confirmation})
            # Pay-link texted (no-POS SMS path) → payment is pending the caller's
            # tap; a direct POS order is pay-at-pickup so we assert nothing about
            # its payment state (stays 'none') rather than falsely show 'pending'.
            _sms_link = getattr(order_result, "pos_system", "") == "sms_link"
            await _log_call_end(
                call_sid, "order_placed", _priced_order,
                pos_result={
                    "payment_status": "pending" if _sms_link else "none",
                    "sms_sent": _sms_link,
                    "pos_order_id": order_id,
                },
            )
            del _sessions[call_sid]
            return Response(content=_hangup(confirmation, voice=_sess_voice), media_type=TWIML)

    reply = text or "Could you repeat that please?"
    session["messages"].append({"role": "assistant", "content": reply})
    return Response(content=_prompt(reply, session), media_type=TWIML)


async def _resolve_pos_for_session(session: dict) -> dict:
    """Resolve the merchant's POS at order time so submit_order can push the
    order into their POS (or fall back to SMS/email).

    Resolved lazily here, not at call start, so the greeting and ordering turns
    aren't slowed by a POS lookup — it runs once, only when an order is actually
    placed (the last turn). Resolution mirrors phone_dashboard.sync_menu_from_pos:
    manual creds stashed on the session from phone_agent_config win; otherwise the
    OAuth connection in pos_connections (decrypted) is used. In this system
    merchant_id IS the org_id.

    Returns pos_system (""=nothing connected -> demo path), pos_config for the
    REST connector, and the merchant contact for the SMS/email fallback. A POS is
    only reported when we hold a usable token, so submit_order never claims a POS
    it cannot authenticate to.
    """
    system = (session.get("pos_system_manual") or "").strip()
    token = (session.get("pos_token_manual") or "").strip()
    location_id = (session.get("pos_location_id") or "").strip()
    external_merchant_id = ""
    merchant_id = (session.get("merchant_id") or "").strip()
    fallback = {
        "pos_system": "",
        "pos_config": None,
        "merchant_phone": (session.get("merchant_phone") or "").strip(),
        "merchant_email": (session.get("merchant_email") or "").strip(),
    }

    if not (system and token) and merchant_id and merchant_id != DEMO_MERCHANT_ID:
        try:
            db = get_db()
            from ...db.org_ids import connection_org_id
            conns = await db.select(
                "pos_connections",
                # biz_ ids map to the companion UUID the callback stores under
                filters={"org_id": f"eq.{connection_org_id(merchant_id) or merchant_id}",
                         "status": "eq.connected"},
                order="updated_at.desc",
                limit=1,
            )
            if conns:
                from .phone_dashboard import _fresh_connection_token
                conn = conns[0]
                system = system or (conn.get("provider") or "").strip()
                external_merchant_id = (conn.get("external_merchant_id") or "").strip()
                location_id = location_id or (conn.get("external_location_id") or "").strip()
                token = token or await _fresh_connection_token(conn)
        except Exception as e:
            logger.warning("phone: POS resolution failed for %s: %s", merchant_id, e)

    if not (system and token):
        return fallback

    try:
        from ...services.pos_connectors.base import POSConnectionConfig
        from ...services.pos_connectors.registry import get_connector_config
        api_config = get_connector_config(system) or {}
        pos_config = POSConnectionConfig(
            system_key=system,
            system_name=api_config.get("system_name") or system,
            tier=api_config.get("tier", 1),
            auth_method=api_config.get("auth_type", "bearer"),
            base_url=api_config.get("base_url", ""),
            # merchant_id/location_id fill {merchant_id}/{location_id} URL
            # templates (Clover's base_url needs the merchant id).
            credentials={
                "access_token": token,
                "merchant_id": external_merchant_id,
                "location_id": location_id,
            },
            merchant_id=external_merchant_id,
            org_id=merchant_id,
            category=api_config.get("category", "restaurant"),
            supports_order_creation=bool(api_config.get("supports_orders")),
            order_creation_endpoint=api_config.get("order_create_endpoint", ""),
        )
    except Exception as e:
        logger.warning("phone: building POS config failed for %s: %s", system, e)
        return fallback

    return {
        "pos_system": system,
        "pos_config": pos_config,
        "merchant_phone": fallback["merchant_phone"],
        "merchant_email": fallback["merchant_email"],
    }


async def _dispatch_order(call_sid: str, session: dict, order_input: dict) -> OrderResult:
    pos = await _resolve_pos_for_session(session)
    system_key = pos["pos_system"]
    if not system_key:
        merchant_id = session.get("merchant_id", "")
        if merchant_id == DEMO_MERCHANT_ID:
            # Demo: fabricated order id is intentional — the agent is in demo mode
            # and no real kitchen exists to receive the order.
            return OrderResult(
                success=True,
                order_id=f"MRD-{abs(hash(call_sid)) % 9000 + 1000}",
                pos_system="demo",
            )
        # Fix 1 — real merchant with no POS configured: never claim success with a
        # fabricated id. Attempt the SMS pay-link handoff so the caller gets a
        # payment link by text. Returns success=True only when the SMS was actually
        # dispatched; otherwise returns failure so the gather handler plays an honest
        # apology (the caller is told to call back, not given a fake order number).
        order_id = f"MRD-{abs(hash(call_sid)) % 9000 + 1000}"
        caller_phone = (session.get("caller_phone") or "").strip()
        sms_sent = False
        if caller_phone:
            try:
                import types as _types
                from voice_sms_handoff import send_payment_link_to_caller  # sidecar module
                _conf = _types.SimpleNamespace(
                    pos_system="",
                    pos_access_token="",
                    pos_location_id="",
                    business_name=session.get("merchant_name") or "",
                    merchant_id=merchant_id,
                    menu_items=[],
                    tax_rate=0.13,
                    sms_checkout_enabled=True,
                    demo_safe=False,
                    stripe_account_id="",
                    stripe_charges_enabled=False,
                )
                sms_result = await send_payment_link_to_caller(
                    merchant_config=_conf,
                    order_input=order_input,
                    caller_phone=caller_phone,
                    merchant_id=merchant_id,
                )
                sms_sent = not sms_result.get("skipped_reason")
                if not sms_sent:
                    logger.warning(
                        "phone no-POS: SMS pay-link skipped (reason=%s merchant=%s)",
                        sms_result.get("skipped_reason"), merchant_id,
                    )
                else:
                    logger.info(
                        "phone no-POS: SMS pay-link sent (merchant=%s order=%s)",
                        merchant_id, order_id,
                    )
            except Exception as _sms_err:
                logger.error(
                    "phone no-POS: SMS pay-link handoff failed (merchant=%s): %s",
                    merchant_id, _sms_err,
                )
        if sms_sent:
            return OrderResult(success=True, order_id=order_id, pos_system="sms_link")
        # SMS could not be sent — honest failure so the caller gets an apology
        # rather than a fabricated confirmation.
        return OrderResult(
            success=False,
            order_id=order_id,
            pos_system="",
            fallback_used=True,
            fallback_reason="no_pos_no_sms",
        )

    order_data = {
        "customer_name": order_input.get("customer_name", ""),
        "order_type": order_input.get("order_type", "pickup"),
        "items": order_input.get("items", []),
        "special_instructions": order_input.get("special_requests", ""),
        "merchant_phone": pos["merchant_phone"],
        "merchant_email": pos["merchant_email"],
        "merchant_name": session.get("merchant_name") or system_key,
    }

    try:
        return await create_pos_order(system_key, order_data, config=pos["pos_config"])
    except Exception as e:
        logger.error(f"Order dispatch failed for {system_key}: {e}")
        # A real POS that threw is a FAILURE — do not report success with a
        # fabricated order id, or the caller is told the order is placed while
        # nothing reaches the kitchen. (The no-POS demo path above stays success.)
        return OrderResult(
            success=False,
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


# ─── PAY ON THE PHONE: payment confirmation webhook ──────────────────────────
# Square POSTs here when a payment link is paid. On payment.updated/order.updated
# → COMPLETED/paid we flip the held phone_orders row to paid and release the
# kitchen ticket (anti-scam: the kitchen only ever sees PAID tickets).
#
# The main POS-sync webhook (/api/webhooks/square) enriches transactions but does
# NOT touch phone_orders, so this is a dedicated, minimal flip endpoint.
#
# ponytail: a poll-fallback (Square /v2/payments?order_id=... every N s for orders
# stuck in awaiting_payment) could back this up if a webhook is ever missed; not
# built now since the webhook is the supported path.
@router.post("/payment-webhook")
async def phone_payment_webhook(request: Request):
    """Square payment webhook → release the held phone order once paid."""
    body = await request.body()

    # Verify the Square signature when a key is configured (reuse the shared
    # helper + key resolution used by /api/webhooks/square). If no key is set we
    # only accept the demo simulate path (below) — never an unsigned real flip.
    sig_ok = False
    try:
        from ...config import square as sq_config, app as app_config
        from ...square.webhook_handlers import verify_webhook_signature
        signature_key = (
            os.environ.get("POS_SQUARE_WEBHOOK_SIGNATURE_KEY")
            or sq_config.webhook_signature_key
        )
        if signature_key:
            sig_ok = verify_webhook_signature(
                body=body,
                signature=request.headers.get("x-square-hmacsha256-signature", ""),
                signature_key=signature_key,
                notification_url=app_config.webhook_url,
            )
    except Exception as e:
        logger.warning("Payment webhook signature check unavailable: %s", e)

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        return Response(content='{"error":"bad_json"}', status_code=400,
                        media_type="application/json")

    # `simulate` is a DEMO-ONLY convenience so the release flow is demonstrable
    # without a real charge — it must NEVER release a real merchant's held
    # order. Honor it ONLY for the demo merchant; a real merchant requires a
    # valid Square signature. Without this gate an unauthenticated
    # {"simulate": true, "merchant_id": <victim>, ...} body released any held
    # order with no signature (CONFIRMED bypass, 2026-07-22).
    simulate_req = bool(event.get("simulate"))
    _wh_merchant = event.get("merchant_id", "")
    simulate = simulate_req and _wh_merchant == DEMO_MERCHANT_ID
    if simulate_req and not simulate:
        logger.warning("Payment webhook: simulate rejected for non-demo merchant %r", _wh_merchant)
        return Response(content='{"error":"forbidden"}', status_code=403,
                        media_type="application/json")
    if not sig_ok and not simulate:
        logger.warning("Payment webhook rejected (no valid signature, not simulate)")
        return Response(content='{"error":"unauthorized"}', status_code=403,
                        media_type="application/json")

    event_type = event.get("type", "")
    obj = event.get("data", {}).get("object", {})
    payment = obj.get("payment", {}) if isinstance(obj, dict) else {}
    order_obj = obj.get("order", {}) if isinstance(obj, dict) else {}

    # Treat it as paid on a COMPLETED payment or a paid order update.
    status = (payment.get("status") or order_obj.get("state") or "").upper()
    is_paid = (
        simulate
        or event_type in ("payment.created", "payment.updated") and status in ("COMPLETED", "APPROVED")
        or event_type == "order.updated" and status in ("COMPLETED", "PAID")
    )
    if not is_paid:
        # Acknowledge non-paid events so Square doesn't retry.
        return Response(content='{"ok":true,"action":"ignored"}', status_code=200,
                        media_type="application/json")

    # Square's payment carries the order_id it was created against; that's our
    # phone_orders.pos_order_id. Fall back to merchant+phone for the simulate path.
    pos_order_id = (
        payment.get("order_id")
        or order_obj.get("id")
        or event.get("pos_order_id", "")
    )
    merchant_id = event.get("merchant_id", "")
    caller_phone = event.get("caller_phone", payment.get("buyer_phone_number", ""))

    # Idempotency: dedupe on the Square event id via the durable webhook_events
    # table (the same guard /api/webhooks/square uses). Square retries on any
    # non-2xx, so without this a single retried event re-enters the release
    # path. (mark_order_paid's CAS is the last line of defense and also collapses
    # the payment.created + payment.updated twin; this layer stops retry storms
    # and the redundant SELECT/config/POS work.) Skipped for the demo simulate
    # path (no event id). Fail-open to the CAS on a DB hiccup.
    if not simulate:
        import hashlib
        event_id = event.get("event_id") or event.get("id") or (
            "sqpay-" + hashlib.sha256(
                f"{event_type}:{pos_order_id}:{merchant_id}:{status}".encode()
            ).hexdigest()[:24]
        )
        try:
            from .webhooks import _record_webhook_event
            if await _record_webhook_event(event_id, provider="square_phone") is False:
                logger.info("phone payment webhook: duplicate event %s ignored", event_id)
                return {"ok": True, "dedup": True}
        except Exception as e:  # noqa: BLE001 — fall through to the CAS on a DB hiccup
            logger.warning("phone payment webhook dedup unavailable: %s", e)

    try:
        from pay_on_phone import mark_order_paid
    except ImportError as e:
        logger.error("pay_on_phone not importable: %s", e)
        return Response(content='{"error":"unavailable"}', status_code=503,
                        media_type="application/json")

    result = await mark_order_paid(
        merchant_id=merchant_id,
        caller_phone=caller_phone,
        pos_order_id=pos_order_id,
        simulate=simulate,
    )
    return {"ok": True, "released": result.get("released", False),
            "matched_by": result.get("matched_by", "")}


# ─── CARD ON THE PHONE: keypad (DTMF) backup payment IVR ─────────────────────
# When the SMS pay-link can't be delivered (landline / send failed), the agent
# takes the card on the call by keypad, charges it, and tells the caller approved
# or declined before they hang up. Multi-step gather: number → expiry → CVV → ZIP
# → charge. Card data lives only in card_on_phone's in-memory capture (never
# logged, never persisted; only the last-4 is stored on the order).
#
# Gated by PHONE_CARD_PAYMENT (default off) so wiring it into submit_order never
# changes live behavior unreviewed. PCI: production must use a DTMF-masking
# capture — see card_on_phone.py header.

def _pay_gather(say: str, action: str, reprompt: str, num_digits: str = "",
                finish: str = "#", timeout: int = 9) -> str:
    """A single DTMF capture step. On no input, re-posts to `reprompt`."""
    nd = f' numDigits="{num_digits}"' if num_digits else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="dtmf" action="{action}" method="POST" finishOnKey="{finish}" timeout="{timeout}"{nd}>
    <Say voice="Polly.Joanna">{_escape(say)}</Say>
  </Gather>
  <Say voice="Polly.Joanna">I didn't get that.</Say>
  <Redirect method="POST">{reprompt}</Redirect>
</Response>"""


@router.post("/pay/start")
async def pay_start(request: Request):
    """Entry into the keypad payment flow. Ensures a capture exists for the call
    (seeded from the live session when present) and asks for the card number."""
    form = await request.form()
    call_sid = form.get("CallSid", "")
    try:
        from card_on_phone import get_capture, start_capture
    except ImportError:
        return Response(content=_hangup("Card payments aren't available right now."), media_type=TWIML)

    if not get_capture(call_sid):
        sess = _sessions.get(call_sid, {})
        start_capture(
            call_sid,
            order_ref=sess.get("pending_pay_order_ref", ""),
            merchant_id=sess.get("merchant_id", ""),
            amount_cents=int(sess.get("pending_pay_amount_cents", 0) or 0),
            caller_phone=sess.get("caller_phone", "") or form.get("From", ""),
        )
    say = ("To pay by card, enter your card number using the keypad, then press pound. "
           "Your card information stays private and is never read aloud.")
    return Response(content=_pay_gather(say, "/twilio/pay/number", "/twilio/pay/start"),
                    media_type=TWIML)


@router.post("/pay/number")
async def pay_number(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid", "")
    digits = form.get("Digits", "")
    from card_on_phone import get_capture, luhn_ok
    cap = get_capture(call_sid)
    if not cap:
        return Response(content=_hangup("Let's start over — please call back to pay."), media_type=TWIML)
    if not luhn_ok(digits):
        return Response(content=_pay_gather(
            "That card number didn't check out. Please enter it again, then press pound.",
            "/twilio/pay/number", "/twilio/pay/start"), media_type=TWIML)
    cap.pan = digits
    return Response(content=_pay_gather(
        "Got it. Now enter the card's expiration as four digits — two for the month, two for the year — then pound.",
        "/twilio/pay/expiry", "/twilio/pay/number", num_digits="4"), media_type=TWIML)


@router.post("/pay/expiry")
async def pay_expiry(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid", "")
    digits = form.get("Digits", "")
    from card_on_phone import get_capture, parse_expiry, expiry_in_future
    cap = get_capture(call_sid)
    if not cap:
        return Response(content=_hangup("Let's start over — please call back to pay."), media_type=TWIML)
    exp = parse_expiry(digits)
    if not exp or not expiry_in_future(*exp):
        return Response(content=_pay_gather(
            "That expiration didn't look right. Enter the month and year as four digits, then pound.",
            "/twilio/pay/expiry", "/twilio/pay/expiry", num_digits="4"), media_type=TWIML)
    cap.expiry = digits
    return Response(content=_pay_gather(
        "Now enter the three or four digit security code from the card, then press pound.",
        "/twilio/pay/cvv", "/twilio/pay/expiry"), media_type=TWIML)


@router.post("/pay/cvv")
async def pay_cvv(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid", "")
    digits = form.get("Digits", "")
    from card_on_phone import get_capture, valid_cvv
    cap = get_capture(call_sid)
    if not cap:
        return Response(content=_hangup("Let's start over — please call back to pay."), media_type=TWIML)
    if not valid_cvv(digits):
        return Response(content=_pay_gather(
            "That code didn't look right. Enter the three or four digit security code, then pound.",
            "/twilio/pay/cvv", "/twilio/pay/cvv"), media_type=TWIML)
    cap.cvv = digits
    return Response(content=_pay_gather(
        "Last step — enter the billing postal or zip code, then press pound.",
        "/twilio/pay/zip", "/twilio/pay/cvv"), media_type=TWIML)


@router.post("/pay/zip")
async def pay_zip(request: Request):
    """Final step: run the card and tell the caller approved or declined."""
    form = await request.form()
    call_sid = form.get("CallSid", "")
    digits = form.get("Digits", "")
    from card_on_phone import (
        get_capture, clear_capture, charge, attempts_exhausted,
    )
    cap = get_capture(call_sid)
    if not cap:
        return Response(content=_hangup("Let's start over — please call back to pay."), media_type=TWIML)
    cap.postal = digits

    result = await charge(
        cap.pan, cap.expiry, cap.cvv, cap.postal, cap.amount_cents,
        merchant_id=cap.merchant_id,
    )

    if result.approved:
        try:
            from pay_on_phone import mark_order_paid
            await mark_order_paid(
                merchant_id=cap.merchant_id,
                caller_phone=cap.caller_phone,
                pos_order_id=cap.order_ref,
                method="card_on_phone",
                card_brand=result.brand,
                card_last4=result.last4,
                payment_txn_id=result.txn_id,
            )
        except Exception as e:
            logger.error("card pay: mark_order_paid failed: %s", e)
        clear_capture(call_sid)
        if call_sid in _sessions:
            await _log_call_end(
                call_sid, "order_paid_card",
                pos_result={"payment_status": "paid", "pos_order_id": cap.order_ref},
            )
            _sessions.pop(call_sid, None)
        return Response(content=_hangup(result.spoken + " Thank you, and enjoy!"),
                        media_type=TWIML)

    # Declined — count the attempt and let them retry, else bow out gracefully.
    cap.attempts += 1
    cap.pan = cap.cvv = cap.expiry = cap.postal = ""  # wipe the failed card
    if attempts_exhausted(cap):
        clear_capture(call_sid)
        if call_sid in _sessions:
            await _log_call_end(call_sid, "payment_failed")
            _sessions.pop(call_sid, None)
        return Response(content=_hangup(
            "I wasn't able to process a card today. Your order isn't confirmed — "
            "please call back to try again. Thanks for your patience."), media_type=TWIML)
    return Response(content=_pay_gather(
        result.spoken + " Let's try again — enter the card number, then press pound.",
        "/twilio/pay/number", "/twilio/pay/start"), media_type=TWIML)
