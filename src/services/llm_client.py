"""
LLMClient — single OpenAI-compatible client with per-channel provider chains.

All three providers (SambaNova, DeepSeek, local Qwen via /v1/chat/completions)
speak the OpenAI chat-completions format, so the adapter is one implementation
parameterised by base_url + key + model — not three bespoke clients.

Voice and SMS pick a channel at construction time; switching providers later
is a PROVIDER_CHAINS edit, never a call-site edit. That is the whole point of
the refactor: don't reintroduce a fork.

complete()-only for now. The current production voice path runs through
Twilio <Gather>, which is a REST round-trip — there is no per-token streaming
consumer today. stream() will be added when the Pipecat Media Streams path
(currently gated behind MEDIA_STREAMS_ENABLED, off in prod) migrates onto
this client.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger("meridian.llm_client")


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: Optional[str]   # None = no key required (e.g. local Qwen)
    model_env: str
    default_model: str
    timeout_s: float = 20.0
    send_model: bool = True       # local OpenAI-compat servers sometimes reject unknown model ids

    @property
    def api_key(self) -> str:
        return os.getenv(self.api_key_env, "") if self.api_key_env else ""

    @property
    def model(self) -> str:
        return os.getenv(self.model_env, self.default_model)


# Provider details lifted from the working call sites:
#   - SambaNova URL/model: src/api/routes/phone.py (production voice, primary)
#   - DeepSeek URL/model:  services/phone_agent/sms_order.py (production SMS, primary)
#   - Qwen-local URL:      src/api/routes/phone.py (production voice, fallback)
PROVIDERS: dict[str, ProviderConfig] = {
    "sambanova": ProviderConfig(
        name="sambanova",
        base_url=os.getenv("SAMBANOVA_BASE_URL", "https://api.sambanova.ai/v1").rstrip("/"),
        api_key_env="SAMBANOVA_API_KEY",
        model_env="SAMBANOVA_MODEL",
        default_model="Meta-Llama-3.3-70B-Instruct",
        timeout_s=20.0,
    ),
    "deepseek": ProviderConfig(
        name="deepseek",
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/"),
        api_key_env="DEEPSEEK_API_KEY",
        model_env="DEEPSEEK_MODEL",
        default_model="deepseek-chat",
        timeout_s=30.0,
    ),
    "qwen_local": ProviderConfig(
        name="qwen_local",
        base_url=os.getenv("GARRY_LLM_URL", "http://localhost:8002").rstrip("/") + "/v1",
        api_key_env=None,
        model_env="QWEN_LOCAL_MODEL",
        default_model="qwen2.5-7b-instruct",
        timeout_s=60.0,
        send_model=False,
    ),
}


# Per-channel fallback chains. Order = try-order on failure.
#   voice: SambaNova primary (~150ms TTFT), DeepSeek mid, Qwen-local backstop.
#   sms:   DeepSeek primary, SambaNova fallback (latency-invisible channel).
PROVIDER_CHAINS: dict[str, list[str]] = {
    "voice": ["sambanova", "deepseek", "qwen_local"],
    "sms":   ["deepseek", "sambanova"],
}


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResult:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    provider_used: str = ""
    model_used: str = ""

    @property
    def tool_call(self) -> Optional[ToolCall]:
        """First tool call, mirroring prior single-tool call-site behaviour."""
        return self.tool_calls[0] if self.tool_calls else None


class LLMClient:
    """Single client; provider/model selected by channel chain.

        client = LLMClient(channel="voice")
        result = await client.complete(
            messages=[{"role": "user", "content": "..."}],
            system="You are an assistant.",
            tools=[{"type": "function", "function": {...}}],
        )
    """

    def __init__(self, channel: str, *, max_tokens: int = 300):
        if channel not in PROVIDER_CHAINS:
            raise ValueError(
                f"Unknown channel '{channel}'. Known: {list(PROVIDER_CHAINS)}"
            )
        self._channel = channel
        self._chain = PROVIDER_CHAINS[channel]
        self._default_max_tokens = max_tokens

    @property
    def channel(self) -> str:
        return self._channel

    @property
    def primary_provider(self) -> str:
        """First entry in the channel chain, for health/status reporting."""
        for key in self._chain:
            p = PROVIDERS.get(key)
            if p and (p.api_key_env is None or p.api_key):
                return p.name
        return "none"

    @property
    def primary_model(self) -> str:
        for key in self._chain:
            p = PROVIDERS.get(key)
            if p and (p.api_key_env is None or p.api_key):
                return p.model
        return ""

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        system: str = "",
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
    ) -> ChatResult:
        """Walk the channel's provider chain; return on first success."""
        payload_messages: list[dict[str, Any]] = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)

        max_t = max_tokens or self._default_max_tokens
        last_err: Optional[str] = None

        for provider_key in self._chain:
            provider = PROVIDERS.get(provider_key)
            if provider is None:
                logger.warning(
                    "[%s] provider '%s' not registered, skipping",
                    self._channel, provider_key,
                )
                continue

            # Skip providers whose key isn't configured (keyless local providers pass).
            if provider.api_key_env and not provider.api_key:
                logger.info(
                    "[%s] provider '%s' has no key set, skipping",
                    self._channel, provider_key,
                )
                continue

            try:
                result = await self._call_provider(provider, payload_messages, tools, max_t)
            except Exception as e:
                last_err = f"{provider.name}: {e}"
                logger.warning(
                    "[%s] provider %s failed: %s", self._channel, provider.name, e,
                )
                continue

            result.provider_used = provider.name
            result.model_used = provider.model
            logger.info(
                "[%s] served by %s/%s", self._channel, provider.name, provider.model,
            )
            return result

        logger.error(
            "[%s] all providers in chain failed; last error: %s",
            self._channel, last_err,
        )
        return ChatResult(text="", tool_calls=[], provider_used="none", model_used="")

    @staticmethod
    async def _call_provider(
        provider: ProviderConfig,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]],
        max_tokens: int,
    ) -> ChatResult:
        payload: dict[str, Any] = {
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if provider.send_model:
            payload["model"] = provider.model
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {"Content-Type": "application/json"}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        async with httpx.AsyncClient(timeout=provider.timeout_s) as client:
            resp = await client.post(
                f"{provider.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

        if resp.status_code != 200:
            raise RuntimeError(
                f"{provider.name} HTTP {resp.status_code}: {resp.text[:200]}"
            )

        return _parse_openai_completion(resp.json())


def _parse_openai_completion(data: dict[str, Any]) -> ChatResult:
    """Parse an OpenAI-compatible chat-completions response into a ChatResult."""
    choices = data.get("choices") or []
    if not choices:
        return ChatResult(text="", tool_calls=[])

    message = choices[0].get("message", {}) or {}
    text = (message.get("content") or "").strip()

    tool_calls: list[ToolCall] = []
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function") or {}
        raw_args = fn.get("arguments", "{}")
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                logger.warning("LLM tool args not valid JSON: %s", raw_args[:200])
                args = {}
        else:
            args = raw_args or {}
        tool_calls.append(ToolCall(
            id=tc.get("id", ""),
            name=fn.get("name", ""),
            arguments=args,
        ))

    return ChatResult(text=text, tool_calls=tool_calls)
