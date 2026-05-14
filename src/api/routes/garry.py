"""
Garry AI proxy — forwards chat requests to DeerFlow (LangGraph) and streams responses.

Avoids CORS issues by proxying DeerFlow through the Meridian API.

Endpoints:
  POST /api/garry/chat  → Stream a Garry AI response
"""
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger("meridian.api.garry")

router = APIRouter(prefix="/api/garry", tags=["garry"])

DEERFLOW_URL = os.getenv("DEERFLOW_URL", "http://localhost:8001")
DEERFLOW_EMAIL = os.getenv("DEERFLOW_EMAIL", "aidanpierce@meridian.tips")
DEERFLOW_PASSWORD = os.getenv("DEERFLOW_PASSWORD", "Meridian1!")

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

_cached_access_token: str | None = None
_cached_csrf_token: str | None = None


async def _get_deerflow_tokens(client: httpx.AsyncClient) -> tuple[str, str]:
    global _cached_access_token, _cached_csrf_token
    if _cached_access_token and _cached_csrf_token:
        return _cached_access_token, _cached_csrf_token
    resp = await client.post(
        f"{DEERFLOW_URL}/api/v1/auth/login/local",
        data={"username": DEERFLOW_EMAIL, "password": DEERFLOW_PASSWORD},
    )
    if resp.status_code != 200:
        raise HTTPException(502, "DeerFlow auth failed")
    _cached_access_token = resp.cookies.get("access_token")
    _cached_csrf_token = resp.cookies.get("csrf_token")
    if not _cached_access_token:
        body = resp.json()
        _cached_access_token = body.get("access_token")
    if not _cached_access_token:
        raise HTTPException(502, "No DeerFlow token received")
    return _cached_access_token, _cached_csrf_token or ""


class GarryChatRequest(BaseModel):
    message: str
    thread_id: str


@router.post("/chat")
async def garry_chat(req: GarryChatRequest):
    # Get tokens with a short-lived client
    async with httpx.AsyncClient(timeout=10.0) as auth_client:
        access_token, csrf_token = await _get_deerflow_tokens(auth_client)

    async def stream():
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{DEERFLOW_URL}/api/runs/stream",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "Cookie": f"access_token={access_token}; csrf_token={csrf_token}",
                    "X-CSRF-Token": csrf_token,
                },
                json={
                    "assistant_id": "lead_agent",
                    "thread_id": req.thread_id,
                    "input": {
                        "messages": [
                            {"role": "system", "content": GARRY_SYSTEM},
                            {"role": "user", "content": req.message},
                        ],
                    },
                    "stream_mode": ["messages"],
                    "config": {"configurable": {"thread_id": req.thread_id}},
                },
            ) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    logger.error(f"DeerFlow stream failed: {resp.status_code} {body[:200]}")
                    yield f"data: {{\"error\": \"DeerFlow returned {resp.status_code}\"}}\n\n"
                    return
                async for chunk in resp.aiter_bytes():
                    yield chunk

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
