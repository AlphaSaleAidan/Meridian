"""Smart inference router — DeepSeek API for reasoning, local Qwen for batch.

Routing:
  User-facing (dashboard, insights, reports)  → DeepSeek V3 API
  Batch/background (scraper, celery, training) → Local Qwen 7B (free)
  Fallback if DeepSeek unavailable             → Local Qwen 7B
"""

import logging
import os
from enum import Enum

logger = logging.getLogger("meridian.inference.router")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = os.getenv("DEEPSEEK_URL", "https://api.deepseek.com/v1/chat/completions")


class InferenceTarget(str, Enum):
    LOCAL = "local"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    AUTO = "auto"


BATCH_SOURCES = {"scraper", "batch", "training", "embedding", "celery", "nightly"}

REALTIME_SOURCES = {"dashboard", "api", "user", "widget", "report", "agent"}

BATCH_KEYWORDS = [
    "summarize", "classify", "extract", "tag", "categorize",
    "score", "rank", "analyze scraped", "process article",
    "generate embedding", "bulk", "batch",
]

REALTIME_KEYWORDS = [
    "insight", "recommendation", "predict", "forecast",
    "customer question", "dashboard", "report", "explain",
    "why", "what should", "action",
]


def classify_task(prompt: str, source: str = "unknown") -> InferenceTarget:
    if source in BATCH_SOURCES:
        return InferenceTarget.LOCAL

    if source in REALTIME_SOURCES:
        return InferenceTarget.DEEPSEEK if DEEPSEEK_API_KEY else InferenceTarget.LOCAL

    lower = prompt.lower()
    for kw in REALTIME_KEYWORDS:
        if kw in lower:
            return InferenceTarget.DEEPSEEK if DEEPSEEK_API_KEY else InferenceTarget.LOCAL

    for kw in BATCH_KEYWORDS:
        if kw in lower:
            return InferenceTarget.LOCAL

    return InferenceTarget.DEEPSEEK if DEEPSEEK_API_KEY else InferenceTarget.LOCAL


async def route_inference(
    prompt: str,
    system: str = "You are a helpful business analytics assistant.",
    max_tokens: int = 1024,
    temperature: float = 0.7,
    source: str = "unknown",
    target: InferenceTarget = InferenceTarget.AUTO,
) -> dict:
    if target == InferenceTarget.AUTO:
        target = classify_task(prompt, source)

    logger.info(f"Routing to {target.value} (source={source})")

    if target == InferenceTarget.DEEPSEEK:
        result = await _deepseek_inference(prompt, system, max_tokens, temperature)
        if result:
            return result
        logger.warning("DeepSeek failed — falling back to local")
        return await _local_inference(prompt, system, max_tokens, temperature)

    if target == InferenceTarget.OPENAI:
        return await _openai_inference(prompt, system, max_tokens, temperature)

    return await _local_inference(prompt, system, max_tokens, temperature)


async def _deepseek_inference(
    prompt: str, system: str, max_tokens: int, temperature: float
) -> dict | None:
    import httpx

    if not DEEPSEEK_API_KEY:
        return None

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                DEEPSEEK_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            if resp.status_code != 200:
                logger.warning("DeepSeek returned %d: %s", resp.status_code, resp.text[:200])
                return None

            data = resp.json()

        tokens = data.get("usage", {})
        input_cost = tokens.get("prompt_tokens", 0) * 0.00000027
        output_cost = tokens.get("completion_tokens", 0) * 0.0000011
        return {
            "content": data["choices"][0]["message"]["content"],
            "model": "deepseek-chat",
            "target": "deepseek",
            "cost_usd": round(input_cost + output_cost, 6),
            "tokens": tokens,
        }
    except Exception as e:
        logger.error("DeepSeek inference failed: %s", e)
        return None


async def _local_inference(
    prompt: str, system: str, max_tokens: int, temperature: float
) -> dict:
    from .local_llm import generate
    import asyncio

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: generate(prompt, system, max_tokens, temperature)
    )
    return {
        "content": result,
        "model": "qwen-2.5-7b-local",
        "target": "local",
        "cost_usd": 0.0,
    }


async def _openai_inference(
    prompt: str, system: str, max_tokens: int, temperature: float
) -> dict:
    import httpx

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("No OPENAI_API_KEY — falling back to local")
        return await _local_inference(prompt, system, max_tokens, temperature)

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    tokens_used = data.get("usage", {})
    input_cost = tokens_used.get("prompt_tokens", 0) * 0.00000015
    output_cost = tokens_used.get("completion_tokens", 0) * 0.0000006
    return {
        "content": data["choices"][0]["message"]["content"],
        "model": "gpt-4o-mini",
        "target": "openai",
        "cost_usd": round(input_cost + output_cost, 6),
    }
