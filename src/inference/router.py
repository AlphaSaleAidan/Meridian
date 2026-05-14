"""Smart inference router — sends batch/background tasks to local LLM,
real-time user-facing requests to OpenAI API."""

import logging
import os
from enum import Enum
from typing import Optional

logger = logging.getLogger("meridian.inference.router")


class InferenceTarget(str, Enum):
    LOCAL = "local"
    OPENAI = "openai"
    AUTO = "auto"


BATCH_KEYWORDS = [
    "summarize", "classify", "extract", "tag", "categorize",
    "score", "rank", "analyze scraped", "process article",
    "generate embedding", "bulk", "batch",
]

REALTIME_KEYWORDS = [
    "insight", "recommendation", "predict", "forecast",
    "customer question", "dashboard", "report",
]


def classify_task(prompt: str, source: str = "unknown") -> InferenceTarget:
    lower = prompt.lower()

    if source in ("scraper", "batch", "training", "embedding", "celery"):
        return InferenceTarget.LOCAL

    if source in ("dashboard", "api", "user", "widget"):
        return InferenceTarget.LOCAL

    for kw in BATCH_KEYWORDS:
        if kw in lower:
            return InferenceTarget.LOCAL

    for kw in REALTIME_KEYWORDS:
        if kw in lower:
            return InferenceTarget.LOCAL

    return InferenceTarget.LOCAL


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

    if target == InferenceTarget.LOCAL:
        return await _local_inference(prompt, system, max_tokens, temperature)
    else:
        return await _openai_inference(prompt, system, max_tokens, temperature)


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
        "model": "llama-3.1-8b-local",
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
