"""
Garry AI — Meridian's marketing strategist powered by local Qwen 2.5 7B.

Streams responses via OpenAI-compatible local llama-cpp server on :8002.
No external API keys needed.

Endpoints:
  POST /api/garry/chat     → Stream a Garry response
  GET  /api/garry/history  → Get conversation history for a thread
"""
import json
import logging
import os
import time
from collections import defaultdict

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger("meridian.api.garry")

router = APIRouter(prefix="/api/garry", tags=["garry"])

QWEN_URL = os.getenv("GARRY_LLM_URL", "http://localhost:8002")

GARRY_SYSTEM = (
    "You are Garry, Meridian's dedicated AI marketing strategist. You have deep knowledge "
    "of the Meridian brand: a dark-green/teal aesthetic (#00d4aa accent), focused on AI-powered "
    "POS analytics for independent Canadian and US businesses (restaurants, smoke shops, cafes, "
    "salons, retail).\n\n"
    "Your job: help the Meridian team create compelling marketing content. You produce:\n"
    "- Social media posts (LinkedIn, Instagram, X) — punchy, conversion-focused\n"
    "- Email campaigns — subject lines, body copy, CTAs\n"
    "- Ad copy — Google, Meta, short-form video scripts\n"
    "- Blog/content outlines — thought leadership, SEO-driven\n"
    "- Pitch decks and one-pagers — structured, benefit-led\n"
    "- Sales enablement — objection handlers, talk tracks, case study templates\n\n"
    "Tone: confident, direct, data-driven. Meridian's voice is 'the smart operator's unfair "
    "advantage.' Never fluffy. Always anchor to dollar amounts and ROI. Use CA$ for Canadian content.\n\n"
    "When generating content, always provide ready-to-use copy — not just suggestions. "
    "Structure outputs clearly with headers."
)

MAX_HISTORY = 20

# In-memory conversation store (keyed by thread_id)
_conversations: dict[str, list[dict]] = defaultdict(list)


class GarryChatRequest(BaseModel):
    message: str
    thread_id: str


@router.post("/chat")
async def garry_chat(req: GarryChatRequest):
    history = _conversations[req.thread_id]
    history.append({"role": "user", "content": req.message})

    # Keep history bounded
    if len(history) > MAX_HISTORY:
        history[:] = history[-MAX_HISTORY:]

    messages = [{"role": "system", "content": GARRY_SYSTEM}] + list(history)

    async def stream():
        accumulated = ""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{QWEN_URL}/v1/chat/completions",
                    json={
                        "messages": messages,
                        "max_tokens": 2048,
                        "temperature": 0.7,
                        "stream": True,
                    },
                ) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        logger.error(f"Qwen error: {resp.status_code} {body[:300]}")
                        yield f"data: {json.dumps({'error': f'LLM returned {resp.status_code}'})}\n\n"
                        return

                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if raw == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            chunk = json.loads(raw)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                accumulated += content
                                yield f"data: {json.dumps({'content': content})}\n\n"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

            # Save assistant response to history
            if accumulated:
                history.append({"role": "assistant", "content": accumulated})

        except httpx.ConnectError:
            yield f"data: {json.dumps({'error': 'Garry is starting up — try again in 30 seconds'})}\n\n"
        except Exception as e:
            logger.exception("Garry stream error")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/history")
async def garry_history(thread_id: str = Query(...)):
    return {"thread_id": thread_id, "messages": _conversations.get(thread_id, [])}
