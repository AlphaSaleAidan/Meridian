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

import os
import time
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/content", tags=["content"])

FAL_KEY = os.getenv("FAL_KEY", "")
FAL_BASE = "https://queue.fal.run"

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


class ImageGenRequest(BaseModel):
    merchantId: str
    prompt: str
    platform: str = "instagram_feed"
    width: int = 1080
    height: int = 1080


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
    endpoint = VIDEO_MODELS.get(req.model)
    if not endpoint:
        raise HTTPException(status_code=400, detail=f"Unknown model: {req.model}")

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
