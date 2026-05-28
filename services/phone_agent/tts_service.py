"""
OmniVoice TTS adapter for Pipecat.
Replaces Kokoro — supports voice cloning, 600+ languages, branded voices.
STT (WhisperLiveKit) stays unchanged. Only TTS output is swapped.
"""
import asyncio
import logging
from typing import AsyncGenerator

import numpy as np
from pipecat.services.ai_services import TTSService
from pipecat.frames.frames import AudioRawFrame, StartFrame, EndFrame

from voice_profiles import VOICE_PROFILES, get_voice_profile

logger = logging.getLogger("meridian.phone_agent.tts")


def _resample_to_8khz(audio: np.ndarray, source_rate: int = 24000) -> np.ndarray:
    from scipy.signal import resample_poly
    ratio = source_rate // 8000
    return resample_poly(audio, 1, ratio)


class OmniVoiceTTS(TTSService):

    def __init__(
        self,
        portal: str = "us",
        ref_audio: str | None = None,
        output_sample_rate: int = 8000,
    ):
        super().__init__()
        self._portal = portal
        self._ref_audio = ref_audio
        self._output_sample_rate = output_sample_rate
        self._model = None
        self._voice_config = get_voice_profile(portal)

    async def start(self, frame: StartFrame):
        await super().start(frame)
        await self._init_model()

    async def _init_model(self):
        import torch
        from omnivoice import OmniVoice

        device = (
            "mps" if torch.backends.mps.is_available()
            else "cuda:0" if torch.cuda.is_available()
            else "cpu"
        )
        self._model = OmniVoice.from_pretrained(
            "k2-fsa/OmniVoice",
            device_map=device,
            dtype=torch.float16 if device != "cpu" else torch.float32,
        )
        logger.info(
            "OmniVoice TTS initialized: portal=%s mode=%s device=%s",
            self._portal, self._voice_config["mode"], device,
        )

    async def run_tts(self, text: str) -> AsyncGenerator[AudioRawFrame, None]:
        if self._model is None:
            await self._init_model()

        voice_cfg = self._voice_config
        ref_audio = self._ref_audio or voice_cfg.get("ref_audio")

        def _generate():
            if ref_audio and voice_cfg["mode"] == "clone":
                audio = self._model.generate(text=text, ref_audio=ref_audio)
            else:
                audio = self._model.generate(
                    text=text, instruct=voice_cfg["instruct"]
                )

            raw = audio[0] if isinstance(audio, (list, tuple)) else audio
            if hasattr(raw, "numpy"):
                raw = raw.numpy()
            audio_8khz = _resample_to_8khz(raw)
            return (audio_8khz * 32767).astype(np.int16).tobytes()

        audio_bytes = await asyncio.to_thread(_generate)
        yield AudioRawFrame(
            audio=audio_bytes,
            sample_rate=self._output_sample_rate,
            num_channels=1,
        )

    def set_merchant_voice(self, merchant_config):
        """Update voice profile for a specific merchant (e.g. custom clone)."""
        self._voice_config = get_voice_profile(self._portal, merchant_config)
        if merchant_config and getattr(merchant_config, "voice_clone_audio", None):
            self._ref_audio = merchant_config.voice_clone_audio

    async def stop(self, frame: EndFrame):
        self._model = None
        await super().stop(frame)


# Legacy fallback — rename old Kokoro implementation for rollback
class KokoroTTSLegacy(TTSService):

    def __init__(
        self,
        voice: str = "af_bella",
        speed: float = 1.0,
        lang_code: str = "a",
        output_sample_rate: int = 8000,
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
        logger.info("Kokoro TTS (legacy) initialized: voice=%s speed=%.1f", self._voice, self._speed)

    async def run_tts(self, text: str) -> AsyncGenerator[AudioRawFrame, None]:
        if self._pipeline is None:
            await self._init_pipeline()

        def _generate():
            chunks = []
            for _graphemes, _phonemes, audio_chunk in self._pipeline(
                text=text, voice=self._voice, speed=self._speed,
                split_pattern=r"[.!?,;]+",
            ):
                if audio_chunk is not None and len(audio_chunk) > 0:
                    audio_8khz = _resample_to_8khz(audio_chunk)
                    audio_bytes = (audio_8khz * 32767).astype(np.int16).tobytes()
                    chunks.append(audio_bytes)
            return chunks

        chunks = await asyncio.to_thread(_generate)
        for audio_bytes in chunks:
            yield AudioRawFrame(
                audio=audio_bytes,
                sample_rate=self._output_sample_rate,
                num_channels=1,
            )

    async def stop(self, frame: EndFrame):
        self._pipeline = None
        await super().stop(frame)
