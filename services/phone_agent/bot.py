"""
Pipecat pipeline with 100% open source services.
Fonoster audio → WhisperLiveKit STT → Ollama LLM → Kokoro TTS → Fonoster audio.
"""
import logging
import os
from typing import Any

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)
from pipecat.audio.vad.silero import SileroVADAnalyzer

from stt_service import WhisperLiveKitSTT
from tts_service import KokoroTTS
from llm_service import OllamaLLM, OllamaContext, ORDER_TOOLS
from order_processor import OrderProcessor
from merchant_config import MerchantPhoneConfig

logger = logging.getLogger("meridian.phone_agent.bot")

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.3:70b")
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "af_bella")
KOKORO_SPEED = float(os.getenv("KOKORO_SPEED", "1.1"))


def build_system_prompt(config: MerchantPhoneConfig, caller_info: dict) -> str:
    menu_section = ""
    if config.menu_items:
        menu_lines = []
        for item in config.menu_items:
            sizes = ", ".join(item.get("sizes", []))
            price = f"${item.get('price', 0):.2f}"
            line = f"- {item['name']}: {price}"
            if sizes:
                line += f" (sizes: {sizes})"
            if item.get("modifications"):
                line += f" [options: {', '.join(item['modifications'])}]"
            menu_lines.append(line)
        menu_section = "\n\nMENU:\n" + "\n".join(menu_lines)

    order_types = ", ".join(config.order_types)

    return f"""You are the AI phone assistant for {config.business_name}.
Your job is to take orders over the phone, be friendly and efficient.

RULES:
- Greet the caller warmly
- Take their order item by item
- Confirm each item (name, size, quantity, modifications)
- Read back the complete order before submitting
- Only call submit_order() AFTER the customer confirms the order is correct
- If the customer asks to speak to a person, call transfer_to_human()
- If the call ends without an order, call end_call_no_order()
- Available order types: {order_types}
- Be concise — phone calls should be quick
- If an item is not on the menu, politely say it's not available and suggest alternatives
{menu_section}

CALLER INFO:
Phone: {caller_info.get('phone', 'unknown')}

Start by greeting the caller with: "{config.greeting}" """


async def run_call_bot(
    websocket: Any,
    merchant_id: str,
    session_ref: str,
    merchant_config: MerchantPhoneConfig,
    caller_info: dict,
):
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_out_enabled=True,
            add_wav_header=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
        ),
    )

    stt = WhisperLiveKitSTT(
        model=WHISPER_MODEL,
        language=merchant_config.language,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE,
    )

    llm = OllamaLLM(
        model=OLLAMA_MODEL,
        temperature=0.3,
    )

    tts = KokoroTTS(
        voice=merchant_config.voice or KOKORO_VOICE,
        speed=KOKORO_SPEED,
    )

    order_processor = OrderProcessor(
        merchant_id=merchant_id,
        call_sid=session_ref,
        merchant_config=merchant_config,
        caller_info=caller_info,
    )

    system_prompt = build_system_prompt(merchant_config, caller_info)

    context = OllamaContext(
        messages=[{"role": "system", "content": system_prompt}],
        tools=ORDER_TOOLS,
    )
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            order_processor,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

    runner = PipelineRunner()
    await runner.run(task)
