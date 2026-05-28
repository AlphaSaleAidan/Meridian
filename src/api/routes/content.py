"""
Content API — video and image generation via fal.ai.

Routes:
  GET  /api/content/dashboard/{org_id}     → Content dashboard data
  POST /api/content/video/generate          → Queue video generation
  POST /api/content/calendar/generate/{org} → Queue weekly calendar
  PATCH /api/content/posts/{id}/approve     → Approve a post
  PATCH /api/content/posts/{id}/reject      → Reject a post
  POST /api/content/posts/{id}/regenerate   → Regenerate a post field
"""

import logging
import os
import time
import httpx
from collections import defaultdict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional

router = APIRouter(prefix="/api/content", tags=["content"])
logger = logging.getLogger("meridian.content")

FAL_KEY = os.getenv("FAL_KEY", "")
FAL_BASE = "https://queue.fal.run"

# ── Usage caps (per merchant, per day) ──
DAILY_VIDEO_CAP = int(os.getenv("DAILY_VIDEO_CAP", "10"))
DAILY_IMAGE_CAP = int(os.getenv("DAILY_IMAGE_CAP", "25"))
MAX_PROMPT_LENGTH = 500

_daily_usage: dict[str, dict[str, int]] = defaultdict(lambda: {"video": 0, "image": 0, "day": 0})


def _check_daily_cap(merchant_id: str, media_type: str):
    today = int(time.time()) // 86400
    bucket = _daily_usage[merchant_id]
    if bucket["day"] != today:
        bucket["video"] = 0
        bucket["image"] = 0
        bucket["day"] = today
    cap = DAILY_VIDEO_CAP if media_type == "video" else DAILY_IMAGE_CAP
    if bucket[media_type] >= cap:
        raise HTTPException(
            status_code=429,
            detail=f"Daily {media_type} generation limit reached ({cap}/day). Resets at midnight UTC.",
        )
    bucket[media_type] += 1

VIDEO_MODELS = {
    "kling-v3":         "fal-ai/kling-video/v3/pro/text-to-video",
    "kling-v2.5-turbo": "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",
    "seedance-2":       "fal-ai/bytedance/seedance-2.0/text-to-video",
    "seedance-2-fast":  "fal-ai/bytedance/seedance-2.0/fast/text-to-video",
    "minimax-video":    "fal-ai/minimax/video-01-live",
    "ltx-video":        "fal-ai/ltx-video-13b-distilled/image-to-video",
    "wan-2.5":          "fal-ai/wan-25-preview/text-to-video",
    "hunyuan":          "fal-ai/hunyuan-video",
    "veo-3.1":          "fal-ai/veo3.1",
    "mochi":            "fal-ai/mochi-v1",
}

IMAGE_MODEL = "fal-ai/flux-2-pro"


class VideoGenRequest(BaseModel):
    merchantId: str
    prompt: str
    platform: str = "instagram_reel"
    model: str = "seedance-2-fast"
    style: Optional[str] = None
    durationSeconds: int = 5

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Prompt cannot be empty")
        if len(v) > MAX_PROMPT_LENGTH:
            raise ValueError(f"Prompt exceeds {MAX_PROMPT_LENGTH} characters")
        return v

    @field_validator("durationSeconds")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v < 2 or v > 10:
            raise ValueError("Duration must be 2-10 seconds")
        return v


class ImageGenRequest(BaseModel):
    merchantId: str
    prompt: str
    platform: str = "instagram_feed"
    width: int = 1080
    height: int = 1080

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Prompt cannot be empty")
        if len(v) > MAX_PROMPT_LENGTH:
            raise ValueError(f"Prompt exceeds {MAX_PROMPT_LENGTH} characters")
        return v

    @field_validator("width", "height")
    @classmethod
    def validate_dimensions(cls, v: int) -> int:
        if v < 256 or v > 2048:
            raise ValueError("Dimensions must be 256-2048px")
        return v


def _aspect_ratio(platform: str) -> str:
    vertical = {"instagram_reel", "instagram_story", "tiktok"}
    square = {"instagram_feed"}
    if platform in vertical:
        return "9:16"
    if platform in square:
        return "1:1"
    return "16:9"


def _fal_headers() -> dict:
    if not FAL_KEY:
        raise HTTPException(status_code=500, detail="FAL_KEY not configured")
    return {
        "Authorization": f"Key {FAL_KEY}",
        "Content-Type": "application/json",
    }


async def _fal_submit(endpoint: str, payload: dict) -> dict:
    """Submit a job to fal.ai queue and poll until done."""
    headers = _fal_headers()

    async with httpx.AsyncClient(timeout=600) as client:
        submit_resp = await client.post(
            f"{FAL_BASE}/{endpoint}",
            headers=headers,
            json=payload,
        )
        if submit_resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=submit_resp.status_code,
                detail=f"fal.ai submit failed: {submit_resp.text[:300]}",
            )

        data = submit_resp.json()
        request_id = data.get("request_id")
        if not request_id:
            return data

        status_url = f"https://queue.fal.run/{endpoint}/requests/{request_id}/status"
        result_url = f"https://queue.fal.run/{endpoint}/requests/{request_id}"

        for _ in range(180):
            await _async_sleep(3)
            status_resp = await client.get(status_url, headers=headers)
            if status_resp.status_code != 200:
                continue
            status_data = status_resp.json()
            status = status_data.get("status", "")
            if status in ("COMPLETED", "completed", "succeeded"):
                result_resp = await client.get(result_url, headers=headers)
                if result_resp.status_code == 200:
                    return result_resp.json()
                raise HTTPException(status_code=500, detail="Failed to fetch fal.ai result")
            if status in ("FAILED", "failed"):
                err = status_data.get("error", "unknown error")
                raise HTTPException(status_code=500, detail=f"fal.ai generation failed: {err}")

        raise HTTPException(status_code=504, detail="fal.ai generation timed out (9 min limit)")


async def _async_sleep(seconds: float):
    import asyncio
    await asyncio.sleep(seconds)


@router.post("/video/generate")
async def generate_video(req: VideoGenRequest):
    _check_daily_cap(req.merchantId, "video")
    endpoint = VIDEO_MODELS.get(req.model)
    if not endpoint:
        raise HTTPException(status_code=400, detail=f"Unknown model: {req.model}")
    logger.info(f"Video gen: merchant={req.merchantId} model={req.model} dur={req.durationSeconds}s")

    payload = {
        "prompt": req.prompt,
        "duration": req.durationSeconds,
        "aspect_ratio": _aspect_ratio(req.platform),
    }

    result = await _fal_submit(endpoint, payload)

    video_url = (
        result.get("video", {}).get("url")
        or result.get("video_url")
        or (result.get("videos", [{}])[0].get("url") if result.get("videos") else None)
    )

    if not video_url:
        raise HTTPException(status_code=500, detail="fal.ai returned no video URL")

    return {
        "ok": True,
        "videoUrl": video_url,
        "model": req.model,
        "durationSeconds": req.durationSeconds,
    }


@router.post("/image/generate")
async def generate_image(req: ImageGenRequest):
    _check_daily_cap(req.merchantId, "image")
    logger.info(f"Image gen: merchant={req.merchantId} {req.width}x{req.height}")
    payload = {
        "prompt": req.prompt,
        "image_size": {"width": req.width, "height": req.height},
        "safety_tolerance": "2",
    }

    result = await _fal_submit(IMAGE_MODEL, payload)

    images = result.get("images", [])
    if not images:
        raise HTTPException(status_code=500, detail="fal.ai returned no images")

    return {
        "ok": True,
        "imageUrl": images[0].get("url"),
        "seed": result.get("seed", 0),
    }


@router.get("/models")
async def list_models():
    return {
        "video": [
            {"id": k, "endpoint": v}
            for k, v in VIDEO_MODELS.items()
        ],
        "image": IMAGE_MODEL,
    }
