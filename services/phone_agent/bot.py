"""
Pipecat **1.4** phone-agent pipeline (rebuilt).

Telnyx/Twilio Media Streams → Silero VAD → Moonshine STT → DeepSeek LLM (with
order tools) → Kokoro TTS → Media Streams.

Rebuilt from the old 0.0.45 custom pipeline (which used the now-removed
FunctionCallFrame / moved ai_services and was never wired). This version uses
pipecat's **built-in** services (DeepSeek / Moonshine / Kokoro) and the 1.x
function-calling API (register_function + FunctionCallParams.result_callback), so
there's far less custom code and the LLM stage is actually connected.

The order tools call our existing order pipeline unchanged:
  normalize_order → create_pos_order → route_order → log + spoken confirmation.

Phase 2 swaps STT/TTS to NVIDIA Nemotron via `pipecat.services.nvidia` (same
pipeline). Env:
  ENABLE_CALL_RECORDING=1  → WAV archival
  DEEPSEEK_API_KEY / DEEPSEEK_MODEL
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.audio.filters.rnnoise_filter import RNNoiseFilter
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.turns.user_turn_strategies import UserTurnStrategies
from pipecat.turns.user_start.min_words_user_turn_start_strategy import (
    MinWordsUserTurnStartStrategy,
)
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.deepseek.llm import DeepSeekLLMService
from pipecat.services.moonshine.stt import MoonshineSTTService
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.serializers.telnyx import TelnyxFrameSerializer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from merchant_config import MerchantPhoneConfig
from order_normalizer import normalize_order
from pos_connector import create_pos_order  # noqa: F401  (kept for back-compat imports)
from order_router import route_order  # noqa: F401  (kept for back-compat imports)
from pay_on_phone import dispatch_order, resolve_mode
from caller_memory import build_memory_block_for

logger = logging.getLogger("meridian.phone_agent.bot")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")  # V4 flash: low-latency + tool-calling (was V3 deepseek-chat)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
# _log_call writes phone_call_logs → needs service-role (anon lacks INSERT GRANT).
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")

# ─── Order tool schemas (1.x FunctionSchema; same shapes the brain expects) ───
_SUBMIT_ORDER = FunctionSchema(
    name="submit_order",
    description="Call ONLY after the customer confirms the complete order is correct.",
    properties={
        "customer_name": {"type": "string"},
        "order_type": {"type": "string", "enum": ["pickup", "delivery", "dine_in", "appointment", "hold"]},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "size": {"type": "string"},
                    "modifications": {"type": "array", "items": {"type": "string"}},
                    "special_instructions": {"type": "string"},
                },
                "required": ["name", "quantity"],
            },
        },
        "delivery_address": {"type": "string"},
        "special_requests": {"type": "string"},
        "caller_phone": {"type": "string"},
        "pay_choice": {
            "type": "string",
            "enum": ["pay_now", "pay_at_pickup"],
            "description": "Only when payment is optional: the caller's chosen payment timing.",
        },
    },
    required=["customer_name", "order_type", "items"],
)
_TRANSFER = FunctionSchema(
    name="transfer_to_human",
    description="Call when the customer asks to speak to a person.",
    properties={"reason": {"type": "string"}},
    required=[],
)
_END_CALL = FunctionSchema(
    name="end_call_no_order",
    description="Call when the call ends without an order.",
    properties={"reason": {"type": "string", "enum": [
        "order_completed", "customer_declined", "wrong_number", "question_only", "customer_hung_up"]}},
    required=["reason"],
)
_RESERVATION = FunctionSchema(
    name="send_reservation_link",
    description="Text the caller the restaurant's reservation/booking link. "
                "Call when they ask about reserving or booking a table.",
    properties={"party_size": {"type": "integer"}, "requested_time": {"type": "string"}},
    required=[],
)


def _reservations_on(config: MerchantPhoneConfig) -> bool:
    return bool(getattr(config, "reservations_enabled", False)
                and getattr(config, "reservation_url", ""))


def build_system_prompt(config: MerchantPhoneConfig, caller_info: dict, memory_block: str = "") -> str:
    menu_section = ""
    if config.menu_items:
        lines = []
        for item in config.menu_items:
            sizes = ", ".join(item.get("sizes", []))
            line = f"- {item['name']}: ${item.get('price', 0):.2f}"
            if sizes:
                line += f" (sizes: {sizes})"
            if item.get("modifications"):
                line += f" [options: {', '.join(item['modifications'])}]"
            lines.append(line)
        menu_section = "\n\nMENU:\n" + "\n".join(lines)
    memory_section = f"\n\n{memory_block}" if memory_block else ""

    # Per-restaurant personalization brief — injected ONLY when non-empty so an
    # unset brief leaves the prompt byte-for-byte identical (no regression).
    _brief = (getattr(config, "restaurant_brief", "") or "").strip()
    brief_section = (
        "\n\nABOUT THIS RESTAURANT:\n"
        + _brief
        + "\n\nUse this only for tone, warmth, and recommending items that ARE on the menu. "
        "The MENU above is the single source of truth for items, sizes, and prices — "
        "never invent items, prices, hours, or facts from this description."
    ) if _brief else ""

    reservation_section = ""
    if _reservations_on(config):
        platform = config.reservation_platform or "their online booking system"
        reservation_section = (
            "\n- RESERVATIONS: you cannot book tables yourself. When the caller asks about "
            f"a reservation/table, offer to text them the booking link ({platform}) and call "
            "send_reservation_link() — then confirm the text is on its way."
        )

    # PAY ON THE PHONE — tell the agent the payment step for this merchant.
    mode = getattr(config, "payment_mode", "pay_now")
    if mode == "pay_now":
        payment_section = (
            "\n\nPAYMENT (required to send the order):\n"
            "- After the customer confirms the order, call submit_order().\n"
            "- Then tell them: you've just texted a secure payment link to their "
            "phone they can tap to pay with Apple Pay, Google Pay or card, and the "
            "order goes to the kitchen as soon as it's paid.\n"
            "- Do NOT promise the order is being prepared before payment — it's held "
            "until paid."
        )
    elif mode == "optional":
        payment_section = (
            "\n\nPAYMENT:\n"
            "- Before submitting, ask: \"Would you like to pay now by secure text "
            "link, or pay at pickup?\"\n"
            "- Pass their choice as pay_choice (\"pay_now\" or \"pay_at_pickup\") to "
            "submit_order().\n"
            "- If they choose pay now, tell them you've texted a secure link and the "
            "order is sent once it's paid."
        )
    else:  # pay_at_pickup
        payment_section = "\n\nPAYMENT:\n- Let the customer know they can pay at pickup."

    return f"""You are the AI phone assistant for {config.business_name}.
Keep replies SHORT — 1-2 sentences. Sound warm and natural, not robotic. This is a phone call.

RULES:
- Greet the caller warmly using: "{config.greeting}"
- Take their order item by item; confirm name + size + quantity + modifications
- Read back the complete order before submitting
- Only call submit_order() AFTER the customer confirms it's correct
- If the customer asks for a person, call transfer_to_human()
- If the call ends without an order, call end_call_no_order(){reservation_section}
- Available order types: {", ".join(config.order_types)}
- If an item isn't on the menu, say so politely and suggest alternatives{payment_section}

IF THE CALLER SOUNDS DISSATISFIED OR FRUSTRATED — watch for signals like: "no", "that's
not what I said", "that's wrong", "not right", "you're not listening", "I already told you",
"that's not it", "ugh", "this isn't working", repeating themselves, correcting you, or
sounding annoyed:
- STOP and slow down — do NOT push ahead with the order or move to the next step.
- Briefly and sincerely apologize, e.g. "Sorry about that — let me get it right."
- Ask them to repeat ONLY the part that was wrong, listen carefully, and read just that
  part back to confirm before continuing. Never repeat the same mistake or argue.
- If they're still frustrated after a try or two, or clearly want a person, call
  transfer_to_human().
{menu_section}{brief_section}

CALLER:
Phone: {caller_info.get('phone', 'unknown')}{memory_section}"""


def _confirmation(order: dict, pos_result: dict) -> str:
    items = ", ".join(
        f"{i['quantity']} {i.get('size', '')} {i['name']}".strip() for i in order.get("items", [])
    )
    msg = f"Great, {order.get('customer_name', '')}! I've placed your order for {items} for {order.get('order_type', 'pickup')}."
    eta = pos_result.get("estimated_ready_minutes")
    msg += f" It should be ready in about {eta} minutes." if (pos_result.get("success") and eta) else " The kitchen has been notified."
    return msg + " Anything else?"


def _pay_now_confirmation(order: dict) -> str:
    """Spoken line for the pay-now (anti-scam) path: order taken, link texted,
    kitchen released once paid."""
    name = order.get("customer_name", "")
    lead = f"Thanks, {name}! " if name else "Thanks! "
    return (
        lead
        + "I've just texted a secure payment link to your phone — tap it to pay "
        "with Apple Pay, Google Pay or card, and your order goes straight to the "
        "kitchen. Anything else?"
    )


async def _log_call(merchant_id: str, call_sid: str, caller: dict, status: str, **extra: Any) -> None:
    entry = {"merchant_id": merchant_id, "call_sid": call_sid, "caller_phone": caller.get("phone", ""),
             "status": status, "created_at": datetime.now(timezone.utc).isoformat(), **extra}
    if not (SUPABASE_URL and SUPABASE_KEY):
        logger.info("Call log (no Supabase): %s", json.dumps(entry, default=str))
        return
    try:
        import httpx
        async with httpx.AsyncClient() as c:
            await c.post(f"{SUPABASE_URL}/rest/v1/phone_call_logs", json=entry,
                         headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                                  "Content-Type": "application/json", "Prefer": "return=minimal"})
    except Exception as e:
        logger.error("Call log failed: %s", e)


def _vad_analyzer() -> SileroVADAnalyzer:
    """Silero VAD tuned for noisy phone environments.

    The library defaults (confidence 0.7 / start_secs 0.2 / min_volume 0.6) are
    very sensitive — a TV or background chatter just above a low volume floor reads
    as the caller speaking and interrupts the bot mid-sentence. We require louder,
    more-confident, slightly-sustained speech before it counts as a turn (rejects
    background), while keeping stop_secs short so turn-end stays snappy. All four
    are overridable per-deploy via VAD_* env vars for live tuning without a code change.
    """
    return SileroVADAnalyzer(params=VADParams(
        confidence=float(os.getenv("VAD_CONFIDENCE", "0.85")),   # was 0.70 — surer it's speech
        start_secs=float(os.getenv("VAD_START_SECS", "0.30")),   # was 0.20 — must be sustained
        stop_secs=float(os.getenv("VAD_STOP_SECS", "0.30")),     # was 0.20 — keep responsive
        min_volume=float(os.getenv("VAD_MIN_VOLUME", "0.70")),   # was 0.60 — ignore quiet noise
    ))


def _nemotron_on() -> bool:
    """Use NVIDIA Nemotron (NVCF-hosted) STT/TTS when a key is present and not
    explicitly disabled. Falls back to local Moonshine/Kokoro otherwise."""
    return bool(os.getenv("NVIDIA_API_KEY")) and os.getenv("NEMOTRON_DISABLED", "").lower() not in ("1", "true", "yes")


def _language(config: MerchantPhoneConfig) -> "Language":
    """Map the merchant's configured language to a pipecat Language. Canada-first:
    any 'fr*' code → Canadian French; everything else → US English."""
    from pipecat.transcriptions.language import Language
    code = (getattr(config, "language", "") or "en").lower()
    return Language.FR_CA if code.startswith("fr") else Language.EN_US


def _build_stt(config: MerchantPhoneConfig):
    """STT: Nemotron 3.5 ASR (streaming, NVCF-hosted) → Moonshine (local).

    IMPORTANT: the NVCF-hosted `nemotron-asr-streaming` (online) model only serves
    en-US today — requesting language_code=fr makes the gRPC stream drop in a
    reconnect loop (verified). So the streaming ASR is English-only; French
    merchants stay on the turn-based path (see phone.py /voice gate). We clamp to
    en-US defensively here too, so a French config can never wedge a live call."""
    if _nemotron_on():
        try:
            from pipecat.services.nvidia.stt import NvidiaSTTService
            from pipecat.transcriptions.language import Language
            lang = _language(config)
            if lang != Language.EN_US:
                logger.warning("Nemotron streaming ASR is en-US only; '%s' unsupported — using en-US", lang)
                lang = Language.EN_US
            logger.info("STT: Nemotron 3.5 ASR (NVCF, lang=%s)", lang)
            return NvidiaSTTService(
                api_key=os.environ["NVIDIA_API_KEY"],
                params=NvidiaSTTService.InputParams(language=lang),
            )
        except Exception as e:
            logger.warning("Nemotron STT unavailable, falling back to Moonshine: %s", e)
    return MoonshineSTTService()


def _build_tts(config: MerchantPhoneConfig):
    """TTS: Magpie-TTS-multilingual (NVCF-hosted, EN+FR for Canada) → Kokoro (local)."""
    if _nemotron_on():
        try:
            from pipecat.services.nvidia.tts import NvidiaTTSService
            lang = _language(config)
            logger.info("TTS: Nemotron MagpieTTS multilingual (NVCF, lang=%s)", lang)
            return NvidiaTTSService(
                api_key=os.environ["NVIDIA_API_KEY"],
                params=NvidiaTTSService.InputParams(language=lang),
            )
        except Exception as e:
            logger.warning("Nemotron TTS unavailable, falling back to Kokoro: %s", e)
    return KokoroTTSService()


async def _start_noise_suppression(call_control_id: str | None, provider: str) -> None:
    """Carrier-side noise suppression (Telnyx) — Telnyx cleans the caller's audio
    BEFORE it streams to us, using a telephony-tuned engine (Krisp/DeepFilterNet).
    This is the right fix for narrowband phone noise (local RNNoise is wideband and
    mangles 8 kHz mu-law). No local deps/keys. Best-effort + flag-gated:
    set NOISE_SUPPRESSION_ENGINE (e.g. "Krisp" or "DeepFilterNet") to enable.
    """
    engine = os.getenv("NOISE_SUPPRESSION_ENGINE", "").strip()
    api_key = os.getenv("TELNYX_API_KEY", "")
    if provider != "telnyx" or not call_control_id or not engine or not api_key:
        return
    try:
        import httpx
        async with httpx.AsyncClient() as c:
            res = await c.post(
                f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/suppression_start",
                json={"direction": "inbound", "noise_suppression_engine": engine},
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=8,
            )
        logger.info("Telnyx noise suppression (%s, inbound) → HTTP %s %s",
                    engine, res.status_code, res.text[:120] if res.status_code >= 300 else "")
    except Exception as e:
        logger.warning("Telnyx noise suppression start failed: %s", e)


def _build_serializer(provider: str, stream_sid: str, call_sid: str | None,
                      call_control_id: str | None, outbound_encoding: str | None):
    if provider == "telnyx":
        # inbound_encoding is REQUIRED in pipecat 1.x (the old code omitted it → TypeError).
        # auto_hang_up (default on) calls Telnyx's REST API to end the call when the
        # bot stops — that needs an api_key, so only enable it when one is present.
        api_key = os.getenv("TELNYX_API_KEY", "")
        return TelnyxFrameSerializer(
            stream_id=stream_sid,
            outbound_encoding=outbound_encoding or "PCMU",
            inbound_encoding="PCMU",
            call_control_id=call_control_id or "",
            api_key=api_key,
            params=TelnyxFrameSerializer.InputParams(auto_hang_up=bool(api_key)),
        )
    # Twilio auto_hang_up needs account_sid + auth_token; without them the
    # serializer raises on init. Pass creds when configured, else disable it
    # (the call still ends when the media WebSocket closes).
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    if account_sid and auth_token:
        return TwilioFrameSerializer(
            stream_sid=stream_sid, call_sid=call_sid or "",
            account_sid=account_sid, auth_token=auth_token,
        )
    return TwilioFrameSerializer(
        stream_sid=stream_sid, call_sid=call_sid or "",
        params=TwilioFrameSerializer.InputParams(auto_hang_up=False),
    )


async def run_call_bot(
    websocket: Any,
    merchant_id: str,
    session_ref: str,
    merchant_config: MerchantPhoneConfig,
    caller_info: dict,
    stream_sid: str | None = None,
    call_sid: str | None = None,
    provider: str = "twilio",
    call_control_id: str | None = None,
    outbound_encoding: str | None = None,
):
    serializer = _build_serializer(provider, stream_sid, call_sid, call_control_id, outbound_encoding) if stream_sid else None

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
            # Inbound noise cancellation. OFF by default: pipecat's RNNoise filter
            # mangled even clean 16 kHz speech in this pipeline (sample-rate/frame
            # mismatch — "cheeseburger" → "bean"), so it's opt-in only via
            # RNNOISE_ENABLED=1 pending a fix or a keyed filter (Krisp/Koala).
            audio_in_filter=(
                RNNoiseFilter() if os.getenv("RNNOISE_ENABLED", "").lower() in ("1", "true", "yes")
                else None
            ),
        ),
    )

    stt = _build_stt(merchant_config)   # Nemotron 3.5 ASR (NVCF) → Moonshine fallback
    tts = _build_tts(merchant_config)   # Magpie-TTS multilingual (NVCF) → Kokoro fallback
    llm = DeepSeekLLMService(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, model=DEEPSEEK_MODEL)

    # ── Order tools as registered LLM functions (call our existing pipeline) ──
    state = {"submitted": False}

    async def _on_submit_order(params: FunctionCallParams):
        args = params.arguments or {}
        if state["submitted"]:
            await params.result_callback({"status": "already_submitted"})
            return
        state["submitted"] = True
        # The LLM can't know the caller's number — inject the real one from the
        # Telnyx start event so the POS order recipient + checkout SMS have it.
        if caller_info.get("phone") and not args.get("caller_phone"):
            args["caller_phone"] = caller_info["phone"]
        normalized = normalize_order(args, merchant_config)

        # ── PAY ON THE PHONE: branch on the merchant's payment_mode ──────────
        # pay_now (default): POS push is DEFERRED — mark_order_paid() creates
        #   the ticket only after the caller pays via the secure texted link,
        #   so an unpaid order never reaches the POS or the kitchen.
        # optional: the caller's pay_choice decides (defaults to pay_now).
        # pay_at_pickup: legacy behavior — POS ticket now, unpaid.
        # dispatch_order owns POS creation (creds incl. the Square env fallback
        # live in pay_on_phone._create_pos).
        mode = resolve_mode(merchant_config, args.get("pay_choice", ""))
        dispatched = await dispatch_order(
            normalized, merchant_config, caller_info,
            pay_choice=args.get("pay_choice", ""),
        )
        pos_result = dispatched.get("pos_result") or {
            "success": False, "method": "deferred", "pos_order_id": "",
        }
        if mode == "pay_now":
            say = _pay_now_confirmation(normalized)
            log_status = "awaiting_payment"
        else:
            say = _confirmation(normalized, pos_result)
            log_status = "order_placed"

        await _log_call(merchant_id, session_ref, caller_info, log_status,
                        order_data=normalized, pos_result=pos_result, payment_mode=mode)
        await params.result_callback({"success": True, "say": say})

    async def _on_transfer(params: FunctionCallParams):
        await _log_call(merchant_id, session_ref, caller_info, "transferred",
                        notes=(params.arguments or {}).get("reason", ""))
        await params.result_callback({"say": "Let me transfer you to a team member — one moment."})

    async def _on_end_call(params: FunctionCallParams):
        reason = (params.arguments or {}).get("reason", "unknown")
        await _log_call(merchant_id, session_ref, caller_info, f"no_order_{reason}")
        await params.result_callback({"say": "Thank you for calling. Have a great day!"})

    async def _on_reservation(params: FunctionCallParams):
        """Text the caller the merchant's EXISTING booking link (we never book)."""
        say = "You can book a table on our website."
        if _reservations_on(merchant_config):
            phone = caller_info.get("phone", "")
            if phone:
                try:
                    from sms_checkout import send_sms
                    res = await send_sms(
                        phone,
                        f"Book your table at {merchant_config.business_name}: "
                        f"{merchant_config.reservation_url}",
                    )
                    say = ("I've just texted you our booking link — pick your time and "
                           "party size there." if res.get("sent")
                           else f"You can book online at {merchant_config.reservation_url}.")
                except Exception as e:  # noqa: BLE001
                    logger.error("reservation SMS failed: %s", e)
                    say = f"You can book online at {merchant_config.reservation_url}."
            else:
                say = f"You can book a table online at {merchant_config.reservation_url}."
        await _log_call(merchant_id, session_ref, caller_info, "reservation_link_sent")
        await params.result_callback({"say": say})

    llm.register_function("submit_order", _on_submit_order)
    llm.register_function("transfer_to_human", _on_transfer)
    llm.register_function("end_call_no_order", _on_end_call)
    if _reservations_on(merchant_config):
        llm.register_function("send_reservation_link", _on_reservation)

    memory_block = ""
    if caller_info.get("phone"):
        try:
            memory_block = await build_memory_block_for(merchant_id, caller_info["phone"])
        except Exception as e:
            logger.warning("caller memory lookup failed: %s", e)

    context = LLMContext(
        messages=[{"role": "system", "content": build_system_prompt(merchant_config, caller_info, memory_block)}],
        tools=ToolsSchema(standard_tools=(
            [_SUBMIT_ORDER, _TRANSFER, _END_CALL]
            + ([_RESERVATION] if _reservations_on(merchant_config) else [])
        )),
    )
    user_agg, assistant_agg = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=_vad_analyzer(),
            # Selective barge-in: the bot is only interrupted mid-sentence by a
            # real, multi-word interjection — background voices / a TV / a stray
            # sound (which transcribe to 0-1 words) don't cut it off. pipecat
            # applies min_words ONLY while the bot is speaking; once it's the
            # caller's turn a single word responds normally. So noise is ignored
            # but a genuine "no, that's wrong" still gets through. Tune the
            # threshold live via INTERRUPT_MIN_WORDS (lower = easier to interrupt).
            user_turn_strategies=UserTurnStrategies(
                start=[MinWordsUserTurnStartStrategy(
                    min_words=int(os.getenv("INTERRUPT_MIN_WORDS", "3")),
                )],
            ),
        ),
    )

    pipeline = Pipeline([
        transport.input(),
        stt,
        user_agg,
        llm,
        tts,
        transport.output(),
        assistant_agg,
    ])
    # Interruptions are governed by the AlwaysUserMuteStrategy on the user
    # aggregator above (allow_interruptions is not a real pipecat 1.4 param — it
    # was silently ignored). The bot speaks its full turn, then listens.
    task = PipelineTask(pipeline, params=PipelineParams())

    @transport.event_handler("on_client_connected")
    async def _on_client_connected(_transport, _client):
        # Greet the instant the call connects, before the caller says anything.
        # Spoken straight through TTS (no LLM round-trip) so the hello is immediate,
        # and recorded in the context (now, not after the bot finishes speaking) so
        # a caller who talks over the greeting doesn't get greeted twice.
        # Carrier-side noise suppression (Telnyx) the instant the call connects —
        # cleans the caller's audio before it reaches STT (fire-and-forget).
        asyncio.create_task(_start_noise_suppression(call_control_id, provider))
        greeting = (merchant_config.greeting or "").strip() or "Thank you for calling!"
        context.add_message({"role": "assistant", "content": greeting})
        await task.queue_frames([TTSSpeakFrame(greeting)])

    await PipelineRunner().run(task)
