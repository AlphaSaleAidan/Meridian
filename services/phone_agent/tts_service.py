"""
Kokoro TTS adapter for Pipecat.
Replaces Cartesia — 100% local, no API calls, no cost per character.
MOS 4.2 quality, RTF 0.03 on GPU.
"""
import asyncio
import logging
from typing import AsyncGenerator

import numpy as np
from pipecat.services.ai_services import TTSService
from pipecat.frames.frames import AudioRawFrame, StartFrame, EndFrame

logger = logging.getLogger("meridian.phone_agent.tts")


def _resample_to_8khz(audio: np.ndarray, source_rate: int = 24000) -> np.ndarray:
    from scipy.signal import resample_poly
    ratio = source_rate // 8000
    return resample_poly(audio, 1, ratio)


class KokoroTTS(TTSService):

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
