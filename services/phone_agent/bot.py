"""
Pipecat pipeline with 100% open source services.
Fonoster audio → WhisperLiveKit STT → Ollama LLM → OmniVoice TTS → Fonoster audio.
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

from stt_service import WhisperLiveKitSTT
from tts_service import OmniVoiceTTS
from llm_service import OllamaLLM, OllamaContext, ORDER_TOOLS
from order_processor import OrderProcessor
from merchant_config import MerchantPhoneConfig

logger = logging.getLogger("meridian.phone_agent.bot")

RECORDING_DIR = Path(os.getenv("RECORDING_DIR", "/tmp/meridian_recordings"))
ENABLE_RECORDING = os.getenv("ENABLE_CALL_RECORDING", "0") == "1"
ENABLE_VIDEO = os.environ.get("ENABLE_VIDEO", "0") == "1"
VIDEO_CAMERA_INDEX = int(os.environ.get("VIDEO_CAMERA_INDEX", "0"))


class CallRecorder(FrameProcessor):
    """Records raw audio frames to a WAV file for call archival / QA review."""

    def __init__(
        self,
        merchant_id: str,
        session_ref: str,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2,
    ):
        super().__init__()
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width
        self._wav: wave.Wave_write | None = None
        self._path: Path | None = None

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


class VideoCaptureProcessor(FrameProcessor):
    """Captures webcam frames and injects them into the Pipecat pipeline.

    Only activated when ENABLE_VIDEO=1. Requires opencv-python (cv2).
    Does not affect the audio-only flow when disabled.
    """

    def __init__(self, camera_index: int = 0, fps: int = 15):
        super().__init__()
        self._cap = None
        self._camera_index = camera_index
        self._fps = fps
        self._running = False

    async def start(self):
        try:
            import cv2
            self._cap = cv2.VideoCapture(self._camera_index)
            if not self._cap.isOpened():
                logger.warning("Video capture: camera %d not available", self._camera_index)
                return
            self._running = True
            logger.info("Video capture started (camera %d, %d fps)", self._camera_index, self._fps)
        except ImportError:
            logger.warning("cv2 not installed — video capture disabled")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)

    async def cleanup(self):
        self._running = False
        if self._cap:
            self._cap.release()
        await super().cleanup()


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.3:70b")
OMNIVOICE_PORTAL = os.getenv("OMNIVOICE_PORTAL", "us")
OMNIVOICE_REF_AUDIO = os.getenv("OMNIVOICE_REF_AUDIO", "")


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

    portal = "canada" if merchant_config.language == "fr" else OMNIVOICE_PORTAL
    ref_audio = getattr(merchant_config, "voice_clone_audio", None) or OMNIVOICE_REF_AUDIO or None
    tts = OmniVoiceTTS(portal=portal, ref_audio=ref_audio)
    tts.set_merchant_voice(merchant_config)

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

    recorder = None
    if ENABLE_RECORDING:
        try:
            recorder = CallRecorder(merchant_id=merchant_id, session_ref=session_ref)
        except Exception as e:
            logger.warning("Call recording init failed: %s", e)

    video_capture = None
    if ENABLE_VIDEO:
        try:
            video_capture = VideoCaptureProcessor(camera_index=VIDEO_CAMERA_INDEX)
            await video_capture.start()
            logger.info("Video input enabled (camera %d)", VIDEO_CAMERA_INDEX)
        except Exception as e:
            logger.warning("Video capture init failed: %s — continuing audio-only", e)
            video_capture = None

    pipeline_stages = [
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        order_processor,
        tts,
    ]
    if recorder:
        # Record outbound audio just before sending to transport
        pipeline_stages.append(recorder)
    if video_capture and video_capture._running:
        # Insert video capture before transport output
        pipeline_stages.append(video_capture)
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
        if video_capture:
            await video_capture.cleanup()
