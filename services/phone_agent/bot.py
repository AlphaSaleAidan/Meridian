"""
Pipecat phone-agent pipeline.

Default stack (CPU-only, commercial-friendly):
  Twilio Media Streams → Silero VAD → Moonshine STT → SambaNova LLM →
  Kokoro TTS → Twilio Media Streams

Env overrides:
  USE_OLLAMA=1            → Ollama LLM instead of SambaNova
  USE_WHISPER=1           → WhisperLiveKit STT instead of Moonshine
  ENABLE_CALL_RECORDING=1 → WAV recording of inbound + outbound audio
"""
import logging
import os
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipecat.frames.frames import AudioRawFrame, Frame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.serializers.twilio import TwilioFrameSerializer

from stt_service import build_stt
from tts_service import build_tts
from llm_service import build_llm, LLMContext, ORDER_TOOLS
from order_processor import OrderProcessor
from merchant_config import MerchantPhoneConfig

logger = logging.getLogger("meridian.phone_agent.bot")

RECORDING_DIR = Path(os.getenv("RECORDING_DIR", "/tmp/meridian_recordings"))
ENABLE_RECORDING = os.getenv("ENABLE_CALL_RECORDING", "0") == "1"


class CallRecorder(FrameProcessor):
    """Records raw audio frames to a WAV file for call archival / QA review."""

    def __init__(
        self,
        merchant_id: str,
        session_ref: str,
        sample_rate: int = 8000,
        channels: int = 1,
        sample_width: int = 2,
    ):
        super().__init__()
        self._wav: wave.Wave_write | None = None
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_dir = RECORDING_DIR / merchant_id
        out_dir.mkdir(parents=True, exist_ok=True)
        self._path = out_dir / f"{session_ref}_{ts}.wav"
        self._wav = wave.open(str(self._path), "wb")
        self._wav.setnchannels(channels)
        self._wav.setsampwidth(sample_width)
        self._wav.setframerate(sample_rate)
        logger.info("Recording to %s", self._path)

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, AudioRawFrame) and self._wav:
            try:
                self._wav.writeframes(frame.audio)
            except Exception as e:
                logger.debug("Recording write failed: %s", e)
        await self.push_frame(frame, direction)

    async def cleanup(self):
        if self._wav:
            try:
                self._wav.close()
                logger.info("Recording saved: %s", self._path)
            except Exception as e:
                logger.warning("Recording close failed: %s", e)
            self._wav = None
        await super().cleanup()


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
Keep replies SHORT — 1-2 sentences. Sound warm and natural, not robotic. This is a phone call.

RULES:
- Greet the caller warmly using: "{config.greeting}"
- Take their order item by item, confirm name + size + quantity + modifications
- Read back the complete order before submitting
- Only call submit_order() AFTER the customer confirms the order is correct
- If the customer asks to speak to a person, call transfer_to_human()
- If the call ends without an order, call end_call_no_order()
- Available order types: {order_types}
- If an item is not on the menu, say so politely and suggest alternatives
{menu_section}

CALLER:
Phone: {caller_info.get('phone', 'unknown')}"""


async def run_call_bot(
    websocket: Any,
    merchant_id: str,
    session_ref: str,
    merchant_config: MerchantPhoneConfig,
    caller_info: dict,
    stream_sid: str | None = None,
    call_sid: str | None = None,
):
    serializer = None
    if stream_sid:
        # Twilio mu-law 8 kHz frame envelope: decoded to 16-bit linear inbound,
        # re-encoded to mu-law on the way out. Without this the audio is unintelligible.
        serializer = TwilioFrameSerializer(stream_sid=stream_sid, call_sid=call_sid or "")

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
            serializer=serializer,
        ),
    )

    stt = build_stt(merchant_config.language)
    llm = build_llm()
    tts = build_tts(merchant_config)

    order_processor = OrderProcessor(
        merchant_id=merchant_id,
        call_sid=session_ref,
        merchant_config=merchant_config,
        caller_info=caller_info,
    )

    system_prompt = build_system_prompt(merchant_config, caller_info)
    context = LLMContext(
        messages=[{"role": "system", "content": system_prompt}],
        tools=ORDER_TOOLS,
    )
    context_aggregator = llm.create_context_aggregator(context)

    recorder = None
    if ENABLE_RECORDING:
        try:
            recorder = CallRecorder(merchant_id=merchant_id, session_ref=session_ref)
        except Exception as e:
            logger.warning("Call recording init failed: %s", e)

    pipeline_stages = [
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        order_processor,
        tts,
    ]
    if recorder:
        pipeline_stages.append(recorder)
    pipeline_stages.extend([
        transport.output(),
        context_aggregator.assistant(),
    ])

    pipeline = Pipeline(pipeline_stages)
    task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

    runner = PipelineRunner()
    try:
        await runner.run(task)
    finally:
        if recorder:
            await recorder.cleanup()
