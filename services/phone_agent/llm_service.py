"""
Ollama LLM adapter for Pipecat with function calling.
Replaces Claude/Anthropic API — 100% free, no API key, no cost per token.
Supports function calling with Llama 3.3, Llama 3.1, and Qwen 2.5.
"""
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import aiohttp
from pipecat.services.ai_services import LLMService
from pipecat.frames.frames import (
    TextFrame,
    FunctionCallFrame,
    StartFrame,
    EndFrame,
)

logger = logging.getLogger("meridian.phone_agent.llm")

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
                    "customer_name": {
                        "type": "string",
                        "description": "Customer name for the order",
                    },
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
                                "modifications": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
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
                "properties": {
                    "reason": {"type": "string"},
                },
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
                    },
                },
                "required": ["reason"],
            },
        },
    },
]


@dataclass
class OllamaContext:
    messages: list[dict[str, Any]] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=lambda: ORDER_TOOLS)

    def get_messages_for_ollama(self) -> list[dict[str, str]]:
        return self.messages

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})


class OllamaLLM(LLMService):

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

    def create_context_aggregator(self, context: OllamaContext):
        return _OllamaContextAggregator(context)

    async def _process_context(self, context: OllamaContext):
        if self._session is None:
            self._session = aiohttp.ClientSession()

        payload = {
            "model": self._model,
            "messages": context.get_messages_for_ollama(),
            "tools": context.tools,
            "stream": True,
            "options": {
                "temperature": self._temperature,
                "num_predict": self._max_tokens,
            },
        }

        try:
            async with self._session.post(
                f"{self._base_url}/api/chat", json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error("Ollama error %d: %s", response.status, error_text)
                    await self.push_frame(
                        TextFrame(text="I'm sorry, I'm having trouble processing that. Could you repeat?")
                    )
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

                    if message.get("tool_calls"):
                        for tool_call in message["tool_calls"]:
                            func = tool_call.get("function", {})
                            logger.info(
                                "Function call: %s(%s)",
                                func.get("name"),
                                json.dumps(func.get("arguments", {}))[:200],
                            )
                            await self.push_frame(
                                FunctionCallFrame(
                                    function_name=func.get("name"),
                                    arguments=func.get("arguments", {}),
                                )
                            )

                if full_response:
                    context.add_message("assistant", full_response)

        except aiohttp.ClientError as e:
            logger.error("Ollama connection error: %s", e)
            await self.push_frame(
                TextFrame(text="I'm experiencing a connection issue. One moment please.")
            )


class _OllamaContextAggregator:
    def __init__(self, context: OllamaContext):
        self.context = context

    def user(self):
        return _ContextAppender(self.context, "user")

    def assistant(self):
        return _ContextAppender(self.context, "assistant")


class _ContextAppender:
    def __init__(self, context: OllamaContext, role: str):
        self._context = context
        self._role = role

    async def process_frame(self, frame, direction=None):
        if isinstance(frame, TranscriptionFrame):
            self._context.add_message(self._role, frame.text)
        elif isinstance(frame, TextFrame):
            self._context.add_message(self._role, frame.text)
