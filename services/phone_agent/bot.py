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
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
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
from pos_connector import create_pos_order
from order_router import route_order
from caller_memory import build_memory_block_for

logger = logging.getLogger("meridian.phone_agent.bot")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

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
    return f"""You are the AI phone assistant for {config.business_name}.
Keep replies SHORT — 1-2 sentences. Sound warm and natural, not robotic. This is a phone call.

RULES:
- Greet the caller warmly using: "{config.greeting}"
- Take their order item by item; confirm name + size + quantity + modifications
- Read back the complete order before submitting
- Only call submit_order() AFTER the customer confirms it's correct
- If the customer asks for a person, call transfer_to_human()
- If the call ends without an order, call end_call_no_order()
- Available order types: {", ".join(config.order_types)}
- If an item isn't on the menu, say so politely and suggest alternatives
{menu_section}

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
        normalized = normalize_order(args, merchant_config)
        pos_result = await create_pos_order(
            normalized, merchant_config.pos_system,
            merchant_config.pos_access_token, merchant_config.pos_location_id,
        )
        await route_order(normalized, merchant_config, caller_info, pos_result)
        await _log_call(merchant_id, session_ref, caller_info, "order_placed",
                        order_data=normalized, pos_result=pos_result)
        await params.result_callback({"success": True, "say": _confirmation(normalized, pos_result)})

    async def _on_transfer(params: FunctionCallParams):
        await _log_call(merchant_id, session_ref, caller_info, "transferred",
                        notes=(params.arguments or {}).get("reason", ""))
        await params.result_callback({"say": "Let me transfer you to a team member — one moment."})

    async def _on_end_call(params: FunctionCallParams):
        reason = (params.arguments or {}).get("reason", "unknown")
        await _log_call(merchant_id, session_ref, caller_info, f"no_order_{reason}")
        await params.result_callback({"say": "Thank you for calling. Have a great day!"})

    llm.register_function("submit_order", _on_submit_order)
    llm.register_function("transfer_to_human", _on_transfer)
    llm.register_function("end_call_no_order", _on_end_call)

    memory_block = ""
    if caller_info.get("phone"):
        try:
            memory_block = await build_memory_block_for(merchant_id, caller_info["phone"])
        except Exception as e:
            logger.warning("caller memory lookup failed: %s", e)

    context = LLMContext(
        messages=[{"role": "system", "content": build_system_prompt(merchant_config, caller_info, memory_block)}],
        tools=ToolsSchema(standard_tools=[_SUBMIT_ORDER, _TRANSFER, _END_CALL]),
    )
    user_agg, assistant_agg = LLMContextAggregatorPair(
        context, user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
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
    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))

    @transport.event_handler("on_client_connected")
    async def _on_client_connected(_transport, _client):
        # Greet the instant the call connects, before the caller says anything.
        # Spoken straight through TTS (no LLM round-trip) so the hello is immediate,
        # and recorded in the context so the brain knows it already greeted and
        # doesn't repeat itself on the caller's first turn.
        greeting = (merchant_config.greeting or "").strip() or "Thank you for calling!"
        context.add_message({"role": "assistant", "content": greeting})
        await task.queue_frames([TTSSpeakFrame(greeting)])

    await PipelineRunner().run(task)
