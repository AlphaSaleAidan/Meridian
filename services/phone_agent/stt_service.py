"""
WhisperLiveKit streaming STT adapter for Pipecat.
Replaces Deepgram — 100% local, no API calls, no cost per transcription.
Each call gets its own AudioProcessor instance, fully isolated.
"""
import asyncio
import logging
import numpy as np
from typing import Optional

from pipecat.services.ai_services import STTService
from pipecat.frames.frames import (
    AudioRawFrame,
    TranscriptionFrame,
    InterimTranscriptionFrame,
    StartFrame,
    EndFrame,
)

logger = logging.getLogger("meridian.phone_agent.stt")


class WhisperLiveKitSTT(STTService):

    def __init__(
        self,
        model: str = "medium",
        language: str = "en",
        device: str = "auto",
        compute_type: str = "int8",
        sample_rate: int = 8000,
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
        logger.info(
            "WhisperLiveKit STT initialized: model=%s device=%s",
            self._model_name,
            self._device,
        )

    async def run_stt(self, audio: AudioRawFrame) -> Optional[str]:
        if self._processor is None:
            await self._init_processor()

        audio_array = np.frombuffer(audio.audio, dtype=np.int16)
        audio_float = audio_array.astype(np.float32) / 32768.0

        result = await asyncio.to_thread(
            self._processor.process_chunk, audio_float
        )

        if result and result.get("text"):
            text = result["text"].strip()
            if not text:
                return None
            if result.get("is_final", False):
                logger.debug("Final transcription: %s", text)
                return text
            else:
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
