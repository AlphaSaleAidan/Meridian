"""
STT adapters for the Pipecat phone agent pipeline.

Primary: Moonshine (Useful Sensors, MIT) — English-only, ~107 ms CPU latency,
~5x faster than Whisper on the same hardware. Built for streaming voice agents.

Fallback: WhisperLiveKit (faster-whisper backend) for non-English calls.
"""
import asyncio
import io
import json
import logging
import os
import wave
from typing import Optional

import httpx
import numpy as np

from pipecat.services.ai_services import STTService
from pipecat.frames.frames import (
    AudioRawFrame,
    TranscriptionFrame,
    InterimTranscriptionFrame,
    StartFrame,
    EndFrame,
)

logger = logging.getLogger("meridian.phone_agent.stt")

# Moonshine is trained on 16 kHz mono float32 in [-1, 1].
_MOONSHINE_RATE = 16000

# Sliding-window decode parameters for streaming.
# Moonshine doesn't have a built-in streaming API; we batch on VAD-released
# utterances upstream and run a single inference per turn.
_MAX_UTTERANCE_SEC = 30.0


def _bytes_to_float32(audio_bytes: bytes) -> np.ndarray:
    return np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0


def _resample_to_16k(audio: np.ndarray, source_rate: int) -> np.ndarray:
    if source_rate == _MOONSHINE_RATE:
        return audio
    from scipy.signal import resample_poly
    return resample_poly(audio, _MOONSHINE_RATE, source_rate)


class MoonshineSTT(STTService):
    """English-only streaming STT using Moonshine.

    Expects upstream Silero VAD to release a complete utterance as a single
    AudioRawFrame; runs one transcription per utterance. This trades incremental
    interim transcripts for ~3x throughput vs Whisper on CPU.
    """

    def __init__(
        self,
        model: str = "moonshine/base",
        sample_rate: int = _MOONSHINE_RATE,
    ):
        super().__init__()
        self._model_name = model
        self._sample_rate = sample_rate
        self._transcribe_fn = None

    async def start(self, frame: StartFrame):
        await super().start(frame)
        await self._init_model()

    async def _init_model(self):
        import moonshine
        self._transcribe_fn = moonshine.transcribe
        logger.info("Moonshine STT initialized: model=%s", self._model_name)

    async def run_stt(self, audio: AudioRawFrame) -> Optional[str]:
        if self._transcribe_fn is None:
            await self._init_model()

        audio_float = _bytes_to_float32(audio.audio)
        audio_16k = _resample_to_16k(audio_float, audio.sample_rate or _MOONSHINE_RATE)
        if len(audio_16k) > int(_MAX_UTTERANCE_SEC * _MOONSHINE_RATE):
            audio_16k = audio_16k[: int(_MAX_UTTERANCE_SEC * _MOONSHINE_RATE)]

        text = await asyncio.to_thread(self._transcribe_fn, audio_16k, self._model_name)
        if isinstance(text, (list, tuple)):
            text = " ".join(t for t in text if t)
        text = (text or "").strip()
        return text or None

    async def process_audio(self, frame: AudioRawFrame):
        text = await self.run_stt(frame)
        if text:
            await self.push_frame(
                TranscriptionFrame(text=text, user_id="caller", timestamp=0)
            )

    async def stop(self, frame: EndFrame):
        self._transcribe_fn = None
        await super().stop(frame)


class WhisperLiveKitSTT(STTService):
    """Streaming Whisper STT via WhisperLiveKit (CTranslate2 backend).

    Use this for non-English calls or when caller accents trip Moonshine.
    """

    def __init__(
        self,
        model: str = "medium",
        language: str = "en",
        device: str = "auto",
        compute_type: str = "int8",
        sample_rate: int = _MOONSHINE_RATE,
        min_chunk_size: float = 0.5,
    ):
        super().__init__()
        self._model_name = model
        self._language = language
        self._device = device
        self._compute_type = compute_type
        self._sample_rate = sample_rate
        self._min_chunk_size = min_chunk_size
        self._processor = None

    async def start(self, frame: StartFrame):
        await super().start(frame)
        await self._init_processor()

    async def _init_processor(self):
        from whisperlivekit.audio_processor import AudioProcessor
        self._processor = AudioProcessor(
            model=self._model_name,
            language=self._language,
            device=self._device,
            compute_type=self._compute_type,
            sample_rate=self._sample_rate,
            min_chunk_size=self._min_chunk_size,
        )
        logger.info("WhisperLiveKit STT initialized: model=%s device=%s", self._model_name, self._device)

    async def run_stt(self, audio: AudioRawFrame) -> Optional[str]:
        if self._processor is None:
            await self._init_processor()

        audio_float = _bytes_to_float32(audio.audio)
        result = await asyncio.to_thread(self._processor.process_chunk, audio_float)
        if not result or not result.get("text"):
            return None

        text = result["text"].strip()
        if not text:
            return None
        if result.get("is_final", False):
            return text

        await self.push_frame(
            InterimTranscriptionFrame(text=text, user_id="caller", timestamp=0)
        )
        return None

    async def process_audio(self, frame: AudioRawFrame):
        text = await self.run_stt(frame)
        if text:
            await self.push_frame(
                TranscriptionFrame(text=text, user_id="caller", timestamp=0)
            )

    async def stop(self, frame: EndFrame):
        self._processor = None
        await super().stop(frame)


# --- Telnyx hosted STT ---

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY", "")
TELNYX_STT_URL = "https://api.telnyx.com/v2/ai/audio/transcriptions"
# nova-3 (Deepgram, via Telnyx) is English-only and best quality; multilingual
# calls fall back to Whisper large-v3-turbo.
_TELNYX_STT_EN_MODEL = os.getenv("TELNYX_STT_MODEL", "deepgram/nova-3")
_TELNYX_STT_MULTILINGUAL_MODEL = "openai/whisper-large-v3-turbo"


class TelnyxSTTService(STTService):
    """Hosted STT via Telnyx (proxies Deepgram nova-3 for English, Whisper
    large-v3-turbo otherwise).

    Sample rate: the call delivers one VAD-released utterance per AudioRawFrame
    as int16 mono PCM at audio.sample_rate. We wrap it as a WAV in memory and
    POST one transcription per turn (no streaming needed). On any API error we
    return None so the call continues.
    """

    def __init__(self, language: str = "en", api_key: str = ""):
        super().__init__()
        self._language = (language or "en").lower()
        self._api_key = api_key or TELNYX_API_KEY
        self._english = self._language.startswith("en")

    def _wav_bytes(self, audio: AudioRawFrame) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(getattr(audio, "num_channels", 1) or 1)
            w.setsampwidth(2)
            w.setframerate(audio.sample_rate or 8000)
            w.writeframes(audio.audio)
        return buf.getvalue()

    async def run_stt(self, audio: AudioRawFrame) -> Optional[str]:
        if not self._api_key:
            logger.error("Telnyx STT: TELNYX_API_KEY not set")
            return None
        if not audio.audio:
            return None
        model = _TELNYX_STT_EN_MODEL if self._english else _TELNYX_STT_MULTILINGUAL_MODEL
        data = {"model": model, "response_format": "json"}
        if self._english:
            data["language"] = "en"
            # model_config is only accepted for the deepgram model.
            data["model_config"] = json.dumps({"smart_format": True, "punctuate": True})
        files = {"file": ("utterance.wav", self._wav_bytes(audio), "audio/wav")}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    TELNYX_STT_URL,
                    data=data,
                    files=files,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
            if res.status_code != 200:
                logger.error("Telnyx STT %d: %s", res.status_code, res.text[:300])
                return None
            text = (res.json().get("text") or "").strip()
            return text or None
        except Exception as e:
            logger.error("Telnyx STT request failed: %s", e)
            return None

    async def process_audio(self, frame: AudioRawFrame):
        text = await self.run_stt(frame)
        if text:
            await self.push_frame(
                TranscriptionFrame(text=text, user_id="caller", timestamp=0)
            )


def build_stt(language: str = "en") -> STTService:
    """Factory: Telnyx hosted STT when STT_PROVIDER=telnyx, otherwise local
    (Moonshine for English, WhisperLiveKit for anything else)."""
    if os.getenv("STT_PROVIDER", "local").lower() == "telnyx":
        return TelnyxSTTService(language=language)
    if language.lower().startswith("en"):
        return MoonshineSTT()
    return WhisperLiveKitSTT(language=language)
