"""
TTS adapters for the Pipecat phone agent pipeline.

Primary: Kokoro-82M (Apache-2.0, ~300 MB, realtime on CPU, top of TTS-Arena Jan 2026).
Fallback: CosyVoice2 wrapper for voice cloning if a merchant uploads a reference sample.

Both classes implement Pipecat's TTSService interface and emit 8 kHz mono PCM,
which is what Twilio Media Streams expects (mu-law decoded to linear).
"""
import asyncio
import logging
import os
import re
from typing import AsyncGenerator, Optional

import httpx
import numpy as np
from pipecat.services.ai_services import TTSService
from pipecat.frames.frames import AudioRawFrame, StartFrame, EndFrame

from voice_profiles import resolve_kokoro_voice

logger = logging.getLogger("meridian.phone_agent.tts")

# Kokoro generates at 24 kHz; Twilio wants 8 kHz mu-law (we hand it linear PCM, transport encodes).
_KOKORO_NATIVE_RATE = 24000
_TWILIO_RATE = 8000


def _resample_to_8khz(audio: np.ndarray, source_rate: int = _KOKORO_NATIVE_RATE) -> np.ndarray:
    from scipy.signal import resample_poly
    if source_rate == _TWILIO_RATE:
        return audio
    ratio = source_rate // _TWILIO_RATE
    return resample_poly(audio, 1, ratio)


def _to_int16_bytes(audio: np.ndarray) -> bytes:
    clipped = np.clip(audio, -1.0, 1.0)
    return (clipped * 32767).astype(np.int16).tobytes()


def _pcm16_to_float(audio_bytes: bytes) -> np.ndarray:
    # binary_output can return an odd byte count if a chunk is truncated; drop the
    # trailing half-sample so np.frombuffer doesn't raise.
    if len(audio_bytes) % 2:
        audio_bytes = audio_bytes[:-1]
    return np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0


class KokoroTTS(TTSService):
    """Kokoro-82M streaming TTS.

    Splits text on sentence boundaries and yields one AudioRawFrame per chunk,
    so the caller hears the first words within ~200ms instead of waiting for the
    whole response to render.
    """

    def __init__(
        self,
        voice: str = "af_bella",
        speed: float = 1.0,
        lang_code: str = "a",
        output_sample_rate: int = _TWILIO_RATE,
    ):
        super().__init__()
        self._voice = voice
        self._speed = speed
        self._lang_code = lang_code
        self._output_sample_rate = output_sample_rate
        self._pipeline = None

    async def start(self, frame: StartFrame):
        await super().start(frame)
        await self._init_pipeline()

    async def _init_pipeline(self):
        from kokoro import KPipeline
        self._pipeline = KPipeline(lang_code=self._lang_code)
        logger.info("Kokoro TTS initialized: voice=%s speed=%.1f", self._voice, self._speed)

    async def run_tts(self, text: str) -> AsyncGenerator[AudioRawFrame, None]:
        if self._pipeline is None:
            await self._init_pipeline()

        def _generate():
            chunks = []
            for _graphemes, _phonemes, audio_chunk in self._pipeline(
                text=text,
                voice=self._voice,
                speed=self._speed,
                split_pattern=r"[.!?,;]+",
            ):
                if audio_chunk is None or len(audio_chunk) == 0:
                    continue
                raw = audio_chunk.numpy() if hasattr(audio_chunk, "numpy") else audio_chunk
                resampled = _resample_to_8khz(raw)
                chunks.append(_to_int16_bytes(resampled))
            return chunks

        chunks = await asyncio.to_thread(_generate)
        for audio_bytes in chunks:
            yield AudioRawFrame(
                audio=audio_bytes,
                sample_rate=self._output_sample_rate,
                num_channels=1,
            )

    def set_merchant_voice(self, merchant_config):
        """Resolve merchant.voice (e.g. 'af_bella') against the Kokoro voice catalog."""
        self._voice = resolve_kokoro_voice(merchant_config)

    async def stop(self, frame: EndFrame):
        self._pipeline = None
        await super().stop(frame)


class CosyVoiceTTS(TTSService):
    """CosyVoice 2 streaming TTS with optional zero-shot voice cloning.

    Use this when a merchant uploads a 5-30s reference sample for branded voice;
    Kokoro is the default because it's smaller, faster, and licensed permissively.
    """

    def __init__(
        self,
        ref_audio: Optional[str] = None,
        ref_text: Optional[str] = None,
        output_sample_rate: int = _TWILIO_RATE,
    ):
        super().__init__()
        self._ref_audio = ref_audio
        self._ref_text = ref_text
        self._output_sample_rate = output_sample_rate
        self._model = None

    async def start(self, frame: StartFrame):
        await super().start(frame)
        await self._init_model()

    async def _init_model(self):
        from cosyvoice.cli.cosyvoice import CosyVoice2
        self._model = CosyVoice2("FunAudioLLM/CosyVoice2-0.5B")
        logger.info("CosyVoice2 TTS initialized: voice_clone=%s", bool(self._ref_audio))

    async def run_tts(self, text: str) -> AsyncGenerator[AudioRawFrame, None]:
        if self._model is None:
            await self._init_model()

        def _generate():
            chunks = []
            stream = self._model.inference_zero_shot(text, self._ref_text, self._ref_audio, stream=True)
            for piece in stream:
                wav = piece["tts_speech"].numpy().squeeze()
                # CosyVoice native rate is 22.05k; resample to 8k for Twilio
                from scipy.signal import resample_poly
                resampled = resample_poly(wav, 8000, 22050)
                chunks.append(_to_int16_bytes(resampled))
            return chunks

        chunks = await asyncio.to_thread(_generate)
        for audio_bytes in chunks:
            yield AudioRawFrame(
                audio=audio_bytes,
                sample_rate=self._output_sample_rate,
                num_channels=1,
            )

    def set_merchant_voice(self, merchant_config):
        clone = getattr(merchant_config, "voice_clone_audio", None)
        clone_text = getattr(merchant_config, "voice_clone_text", None)
        if clone:
            self._ref_audio = clone
        if clone_text:
            self._ref_text = clone_text

    async def stop(self, frame: EndFrame):
        self._model = None
        await super().stop(frame)


# --- Telnyx hosted TTS ---

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY", "")
# The synthesis endpoint is /v2/text-to-speech/speech (the bare /v2/text-to-speech
# path 404s — the public website docs are wrong; the telnyx-python SDK is right).
TELNYX_TTS_URL = "https://api.telnyx.com/v2/text-to-speech/speech"
# Telnyx hosts Kokoro with the SAME voice ids as our local Kokoro, so the mapping
# is just "Telnyx.KokoroTTS.{kokoro_voice}". There is no "NaturalHD" model.
_DEFAULT_TELNYX_VOICE = os.getenv("TELNYX_TTS_VOICE", "Telnyx.KokoroTTS.af_bella")


async def _ffmpeg_mp3_to_pcm8k(mp3_bytes: bytes) -> bytes:
    """Decode Telnyx's MP3 response to 8 kHz signed-16-bit LE mono PCM.

    binary_output returns audio/mpeg (not raw PCM), so we shell out to ffmpeg to
    decode + downmix + resample in one pass. ffmpeg is installed in the container
    image (see Dockerfile). Returns b"" on any failure so the call continues.
    """
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", str(_TWILIO_RATE), "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate(mp3_bytes)
    if proc.returncode != 0:
        logger.error("ffmpeg MP3 decode failed (rc=%s): %s", proc.returncode, err[:300])
        return b""
    return out


class TelnyxTTSService(TTSService):
    """Hosted TTS via Telnyx (POST /v2/text-to-speech/speech, binary_output).

    Splits text on sentence boundaries and POSTs one request per sentence so the
    caller hears the first words while later sentences are still rendering. Telnyx
    returns MP3 (audio/mpeg); we decode + downmix + resample to 8 kHz mono PCM via
    ffmpeg for the call transport. On any error we yield nothing so the call continues.
    """

    def __init__(
        self,
        voice: str = _DEFAULT_TELNYX_VOICE,
        api_key: str = "",
        output_sample_rate: int = _TWILIO_RATE,
    ):
        super().__init__()
        self._voice = voice
        self._api_key = api_key or TELNYX_API_KEY
        self._output_sample_rate = output_sample_rate

    async def run_tts(self, text: str) -> AsyncGenerator[AudioRawFrame, None]:
        if not self._api_key:
            logger.error("Telnyx TTS: TELNYX_API_KEY not set")
            return
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
        if not sentences:
            return
        async with httpx.AsyncClient(timeout=15.0) as client:
            for sentence in sentences:
                try:
                    res = await client.post(
                        TELNYX_TTS_URL,
                        json={
                            "text": sentence,
                            "voice": self._voice,
                            "output_type": "binary_output",
                        },
                        headers={"Authorization": f"Bearer {self._api_key}"},
                    )
                    if res.status_code != 200:
                        logger.error("Telnyx TTS %d: %s", res.status_code, res.text[:300])
                        continue
                    pcm8k = await _ffmpeg_mp3_to_pcm8k(res.content)
                    if not pcm8k:
                        continue
                    yield AudioRawFrame(
                        audio=pcm8k,
                        sample_rate=self._output_sample_rate,
                        num_channels=1,
                    )
                except Exception as e:
                    logger.error("Telnyx TTS request failed: %s", e)
                    continue

    def set_merchant_voice(self, merchant_config):
        kokoro_voice = resolve_kokoro_voice(merchant_config)
        self._voice = f"Telnyx.KokoroTTS.{kokoro_voice}"


def build_tts(merchant_config) -> TTSService:
    """Factory: Telnyx hosted TTS when TTS_PROVIDER=telnyx; otherwise local
    (CosyVoice if the merchant has a clone, else Kokoro)."""
    if os.getenv("TTS_PROVIDER", "local").lower() == "telnyx":
        tts = TelnyxTTSService()
        tts.set_merchant_voice(merchant_config)
        return tts
    clone = getattr(merchant_config, "voice_clone_audio", None)
    if clone:
        tts = CosyVoiceTTS()
        tts.set_merchant_voice(merchant_config)
        return tts
    tts = KokoroTTS()
    tts.set_merchant_voice(merchant_config)
    return tts
