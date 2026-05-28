"""
Content API — video and image generation via fal.ai.

Routes:
  POST /api/content/video/generate          → Submit video job (returns jobId)
  GET  /api/content/video/status/{job_id}   → Poll job status
  POST /api/content/image/generate          → Generate image (sync, fast)
  GET  /api/content/models                  → Available models
"""

import logging
import os
import time
import uuid
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

# In-memory job tracker (video jobs)
_video_jobs: dict[str, dict] = {}


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


# ── Async background poller ─────────────────────────────────────────────────

async def _poll_fal_job(job_id: str, status_url: str, result_url: str):
    """Background task: poll fal.ai until done, update _video_jobs."""
    import asyncio
    headers = _fal_headers()
    logger.info(f"Job {job_id}: polling status_url={status_url} result_url={result_url}")

    async with httpx.AsyncClient(timeout=30) as client:
        for i in range(180):
            await asyncio.sleep(3)
            _video_jobs[job_id]["poll_count"] = i + 1
            try:
                status_resp = await client.get(status_url, headers=headers)
                if status_resp.status_code != 200:
                    _video_jobs[job_id]["last_error"] = f"HTTP {status_resp.status_code}: {status_resp.text[:200]}"
                    if i < 3:
                        logger.warning(f"Job {job_id}: poll {i} returned {status_resp.status_code}: {status_resp.text[:200]}")
                    continue

                status_data = status_resp.json()
                status = status_data.get("status", "")
                _video_jobs[job_id]["fal_status"] = status

                if status in ("COMPLETED", "completed", "succeeded"):
                    result_resp = await client.get(result_url, headers=headers)
                    if result_resp.status_code == 200:
                        result = result_resp.json()
                        video_url = (
                            result.get("video", {}).get("url")
                            or result.get("video_url")
                            or (result.get("videos", [{}])[0].get("url") if result.get("videos") else None)
                        )
                        _video_jobs[job_id].update({
                            "status": "completed",
                            "videoUrl": video_url,
                            "completed_at": time.time(),
                        })
                        logger.info(f"Job {job_id}: completed, video_url={video_url is not None}")
                    else:
                        _video_jobs[job_id].update({
                            "status": "failed",
                            "error": f"Failed to fetch result (HTTP {result_resp.status_code})",
                        })
                    return

                if status in ("FAILED", "failed"):
                    err = status_data.get("error", "unknown error")
                    _video_jobs[job_id].update({"status": "failed", "error": str(err)})
                    logger.error(f"Job {job_id}: fal.ai failed: {err}")
                    return

            except Exception as e:
                logger.warning(f"Job {job_id}: poll error: {e}")
                continue

    _video_jobs[job_id].update({"status": "failed", "error": "Generation timed out (9 min)"})
    logger.error(f"Job {job_id}: timed out after 9 min")


# ── Video endpoints (async submit + poll) ────────────────────────────────────

@router.post("/video/generate")
async def generate_video(req: VideoGenRequest):
    _check_daily_cap(req.merchantId, "video")
    endpoint = VIDEO_MODELS.get(req.model)
    if not endpoint:
        raise HTTPException(status_code=400, detail=f"Unknown model: {req.model}")

    logger.info(f"Video gen: merchant={req.merchantId} model={req.model} dur={req.durationSeconds}s")

    headers = _fal_headers()
    payload = {
        "prompt": req.prompt,
        "duration": req.durationSeconds,
        "aspect_ratio": _aspect_ratio(req.platform),
    }

    async with httpx.AsyncClient(timeout=30) as client:
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
    fal_request_id = data.get("request_id")
    fal_status_url = data.get("status_url")
    fal_response_url = data.get("response_url")
    logger.info(f"fal.ai submit: request_id={fal_request_id} status_url={fal_status_url} response_url={fal_response_url} keys={list(data.keys())}")

    # If fal returned the result directly (no queue)
    if not fal_request_id:
        video_url = (
            data.get("video", {}).get("url")
            or data.get("video_url")
            or (data.get("videos", [{}])[0].get("url") if data.get("videos") else None)
        )
        return {
            "ok": True,
            "videoUrl": video_url,
            "model": req.model,
            "durationSeconds": req.durationSeconds,
        }

    # Build URLs from fal response or fall back to constructed ones
    status_url = fal_status_url or f"https://queue.fal.run/{endpoint}/requests/{fal_request_id}/status"
    response_url = fal_response_url or f"https://queue.fal.run/{endpoint}/requests/{fal_request_id}"

    job_id = str(uuid.uuid4())[:8]
    _video_jobs[job_id] = {
        "status": "processing",
        "model": req.model,
        "platform": req.platform,
        "fal_request_id": fal_request_id,
        "fal_endpoint": endpoint,
        "fal_status_url": status_url,
        "fal_response_url": response_url,
        "fal_status": "IN_QUEUE",
        "submitted_at": time.time(),
        "poll_count": 0,
    }

    import asyncio
    asyncio.create_task(_poll_fal_job(job_id, status_url, response_url))

    return {
        "ok": True,
        "jobId": job_id,
        "status": "processing",
        "model": req.model,
    }


@router.get("/video/status/{job_id}")
async def video_status(job_id: str):
    job = _video_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result: dict = {
        "jobId": job_id,
        "status": job["status"],
        "model": job.get("model"),
        "fal_status": job.get("fal_status"),
        "poll_count": job.get("poll_count", 0),
        "elapsed": round(time.time() - job.get("submitted_at", time.time()), 1),
    }

    if job["status"] == "completed":
        result["videoUrl"] = job.get("videoUrl")
        result["ok"] = True
    elif job["status"] == "failed":
        result["error"] = job.get("error", "Unknown error")

    if job.get("last_error"):
        result["last_poll_error"] = job["last_error"]

    return result


@router.get("/video/debug/{job_id}")
async def video_debug(job_id: str):
    """Direct fal.ai status check for debugging."""
    job = _video_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    status_url = job.get("fal_status_url", "")
    headers = _fal_headers()

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(status_url, headers=headers)
        return {
            "job_id": job_id,
            "fal_request_id": job.get("fal_request_id"),
            "status_url": status_url,
            "response_url": job.get("fal_response_url"),
            "http_status": resp.status_code,
            "response": resp.text[:500],
            "poll_count": job.get("poll_count", 0),
            "last_error": job.get("last_error"),
        }


# ── Image endpoint (sync — FLUX is fast) ─────────────────────────────────────

async def _fal_submit_sync(endpoint: str, payload: dict) -> dict:
    """Submit and poll for fast models (images)."""
    headers = _fal_headers()

    async with httpx.AsyncClient(timeout=120) as client:
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

        import asyncio
        for _ in range(60):
            await asyncio.sleep(2)
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

        raise HTTPException(status_code=504, detail="Image generation timed out")


@router.post("/image/generate")
async def generate_image(req: ImageGenRequest):
    _check_daily_cap(req.merchantId, "image")
    logger.info(f"Image gen: merchant={req.merchantId} {req.width}x{req.height}")
    payload = {
        "prompt": req.prompt,
        "image_size": {"width": req.width, "height": req.height},
        "safety_tolerance": "2",
    }

    result = await _fal_submit_sync(IMAGE_MODEL, payload)

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
