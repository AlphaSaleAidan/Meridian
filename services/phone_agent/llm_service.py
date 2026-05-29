"""
LLM adapters for the Pipecat phone agent pipeline.

Primary: SambaNova (OpenAI-compatible, ~150 ms TTFT, Llama-3.3-70B). Aligns with
the LLM the production TwiML path already uses, so behaviour stays consistent
when we flip the feature flag.

Fallback: Ollama (local Llama-3 / Qwen-2.5) for self-hosted deploys with GPU.
"""
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import aiohttp

from pipecat.services.ai_services import LLMService
from pipecat.frames.frames import (
    TextFrame,
    TranscriptionFrame,
    FunctionCallFrame,
    StartFrame,
    EndFrame,
)

logger = logging.getLogger("meridian.phone_agent.llm")

SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "")
SAMBANOVA_BASE_URL = os.getenv("SAMBANOVA_BASE_URL", "https://api.sambanova.ai/v1")
SAMBANOVA_MODEL = os.getenv("SAMBANOVA_MODEL", "Meta-Llama-3.3-70B-Instruct")

OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.3:70b")

ORDER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "submit_order",
            "description": (
                "Call this ONLY after confirming the complete order with the customer "
                "and they have agreed it is correct."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "order_type": {
                        "type": "string",
                        "enum": ["pickup", "delivery", "dine_in", "appointment", "hold"],
                    },
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
                "required": ["customer_name", "order_type", "items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_human",
            "description": "Call when customer asks to speak to a person",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "end_call_no_order",
            "description": "Call when the call ends without an order",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "enum": [
                            "order_completed",
                            "customer_declined",
                            "wrong_number",
                            "question_only",
                            "customer_hung_up",
                        ],
                    }
                },
                "required": ["reason"],
            },
        },
    },
]


@dataclass
class LLMContext:
    messages: list[dict[str, Any]] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=lambda: ORDER_TOOLS)

    def get_messages(self) -> list[dict[str, Any]]:
        return self.messages

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})


# Back-compat alias for bot.py imports that still say OllamaContext.
OllamaContext = LLMContext


class _ContextAggregator:
    def __init__(self, context: LLMContext):
        self.context = context

    def user(self):
        return _ContextAppender(self.context, "user")

    def assistant(self):
        return _ContextAppender(self.context, "assistant")


class _ContextAppender:
    def __init__(self, context: LLMContext, role: str):
        self._context = context
        self._role = role

    async def process_frame(self, frame, direction=None):
        if isinstance(frame, (TranscriptionFrame, TextFrame)):
            self._context.add_message(self._role, frame.text)


class SambaNovaLLM(LLMService):
    """SambaNova via OpenAI-compatible streaming SSE.

    Emits TextFrame chunks as content arrives and FunctionCallFrame when the
    model invokes a tool. Matches the schema of `OllamaLLM` so bot.py can swap
    them via env var.
    """

    def __init__(
        self,
        model: str = SAMBANOVA_MODEL,
        temperature: float = 0.3,
        max_tokens: int = 512,
        api_key: str = SAMBANOVA_API_KEY,
        base_url: str = SAMBANOVA_BASE_URL,
    ):
        super().__init__()
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def start(self, frame: StartFrame):
        await super().start(frame)
        if not self._api_key:
            logger.error("SAMBANOVA_API_KEY not set — LLM will fail open with a polite error")
        self._session = aiohttp.ClientSession()
        logger.info("SambaNova LLM initialized: model=%s", self._model)

    async def stop(self, frame: EndFrame):
        if self._session:
            await self._session.close()
            self._session = None
        await super().stop(frame)

    def create_context_aggregator(self, context: LLMContext) -> _ContextAggregator:
        return _ContextAggregator(context)

    async def _process_context(self, context: LLMContext):
        if not self._api_key:
            await self.push_frame(TextFrame(text="I'm sorry, our system is briefly offline. Please try again in a moment."))
            return
        if self._session is None:
            self._session = aiohttp.ClientSession()

        payload = {
            "model": self._model,
            "messages": context.get_messages(),
            "tools": context.tools,
            "tool_choice": "auto",
            "stream": True,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with self._session.post(
                f"{self._base_url}/chat/completions", json=payload, headers=headers
            ) as response:
                if response.status != 200:
                    err = (await response.text())[:200]
                    logger.error("SambaNova %d: %s", response.status, err)
                    await self.push_frame(TextFrame(text="Sorry, I had trouble there — could you repeat that?"))
                    return

                full_response = ""
                pending_tools: dict[int, dict[str, Any]] = {}

                async for raw_line in response.content:
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    payload_str = line[len("data:"):].strip()
                    if payload_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload_str)
                    except json.JSONDecodeError:
                        continue

                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        text = delta["content"]
                        full_response += text
                        await self.push_frame(TextFrame(text=text))

                    for tc in delta.get("tool_calls") or []:
                        idx = tc.get("index", 0)
                        slot = pending_tools.setdefault(idx, {"name": "", "args": ""})
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            slot["name"] = fn["name"]
                        if fn.get("arguments"):
                            slot["args"] += fn["arguments"]

                for slot in pending_tools.values():
                    if not slot["name"]:
                        continue
                    try:
                        args = json.loads(slot["args"] or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    logger.info("Function call: %s(%s)", slot["name"], json.dumps(args)[:200])
                    await self.push_frame(
                        FunctionCallFrame(function_name=slot["name"], arguments=args)
                    )

                if full_response:
                    context.add_message("assistant", full_response)

        except aiohttp.ClientError as e:
            logger.error("SambaNova connection error: %s", e)
            await self.push_frame(TextFrame(text="One moment please — I'm reconnecting."))


class OllamaLLM(LLMService):
    """Local Ollama LLM (Llama-3.3 or Qwen-2.5) for self-hosted deploys."""

    def __init__(
        self,
        model: str = OLLAMA_MODEL,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        base_url: str = OLLAMA_URL,
    ):
        super().__init__()
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def start(self, frame: StartFrame):
        await super().start(frame)
        self._session = aiohttp.ClientSession()
        logger.info("Ollama LLM initialized: model=%s url=%s", self._model, self._base_url)

    async def stop(self, frame: EndFrame):
        if self._session:
            await self._session.close()
            self._session = None
        await super().stop(frame)

    def create_context_aggregator(self, context: LLMContext) -> _ContextAggregator:
        return _ContextAggregator(context)

    async def _process_context(self, context: LLMContext):
        if self._session is None:
            self._session = aiohttp.ClientSession()

        payload = {
            "model": self._model,
            "messages": context.get_messages(),
            "tools": context.tools,
            "stream": True,
            "options": {
                "temperature": self._temperature,
                "num_predict": self._max_tokens,
            },
        }
        try:
            async with self._session.post(f"{self._base_url}/api/chat", json=payload) as response:
                if response.status != 200:
                    logger.error("Ollama %d: %s", response.status, (await response.text())[:200])
                    await self.push_frame(TextFrame(text="Sorry, could you repeat that?"))
                    return

                full_response = ""
                async for line in response.content:
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    if chunk.get("done"):
                        break
                    message = chunk.get("message", {})
                    if message.get("content"):
                        text = message["content"]
                        full_response += text
                        await self.push_frame(TextFrame(text=text))
                    for tool_call in message.get("tool_calls") or []:
                        fn = tool_call.get("function") or {}
                        args = fn.get("arguments") or {}
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {}
                        logger.info("Function call: %s(%s)", fn.get("name"), json.dumps(args)[:200])
                        await self.push_frame(
                            FunctionCallFrame(function_name=fn.get("name"), arguments=args)
                        )

                if full_response:
                    context.add_message("assistant", full_response)

        except aiohttp.ClientError as e:
            logger.error("Ollama connection error: %s", e)
            await self.push_frame(TextFrame(text="One moment please."))


def build_llm() -> LLMService:
    """Factory: SambaNova when key present, Ollama otherwise."""
    if SAMBANOVA_API_KEY:
        return SambaNovaLLM()
    return OllamaLLM()
