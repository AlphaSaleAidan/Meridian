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

from ...credits import COSTS, InsufficientCredits, deduct

router = APIRouter(prefix="/api/content", tags=["content"])
logger = logging.getLogger("meridian.content")


async def _charge_credits(merchant_id: str, action: str, action_id: str | None = None) -> None:
    """Deduct credits for a content action. Raises HTTPException(402) on insufficient balance.

    Demo accounts bypass — they don't have real balances to draw from and
    showing 402 in the tour would be confusing.
    """
    demo_id = os.getenv("DEMO_MERCHANT_ID", "demo-merchant")
    if not merchant_id or merchant_id in ("demo", demo_id):
        return
    cost = COSTS.get(action)
    if not cost or cost.credits <= 0:
        return
    try:
        await deduct(
            merchant_id=merchant_id,
            amount=cost.credits,
            action_type=action,
            action_id=action_id,
        )
    except InsufficientCredits as exc:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credits",
                "balance": exc.available,
                "requested": exc.requested,
                "needed": exc.requested - exc.available,
                "action": action,
                "message": f"This action costs {cost.credits} credits. Top up to continue.",
            },
        )

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


class BrandProfile(BaseModel):
    business_name: str = ""
    business_type: str = "retail"
    voice_profile: Optional[dict] = None


class VideoGenRequest(BaseModel):
    merchantId: str
    prompt: str
    platform: str = "instagram_reel"
    model: str = "seedance-2-fast"
    style: Optional[str] = None
    durationSeconds: int = 5
    brand: Optional[BrandProfile] = None
    enhance: bool = True

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
    style: Optional[str] = None
    brand: Optional[BrandProfile] = None
    enhance: bool = True

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
                if status_resp.status_code not in (200, 202):
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

    final_prompt = req.prompt
    director_notes = None

    if req.enhance and req.brand:
        try:
            from ...ai.commercial_director import direct_video
            brand_dict = {
                "business_name": req.brand.business_name,
                "business_type": req.brand.business_type,
                "voice_profile": req.brand.voice_profile or {},
                "merchant_id": req.merchantId,
            }
            result = await direct_video(
                brand=brand_dict,
                prompt=req.prompt,
                platform=req.platform,
                style=req.style,
                model=req.model,
                duration_seconds=req.durationSeconds,
            )
            final_prompt = result.enhanced_prompt
            director_notes = {
                "style_notes": result.style_notes,
                "model_recommendation": result.model_recommendation,
                "original_prompt": result.original_prompt,
            }
            logger.info(f"Director enhanced prompt: {len(req.prompt)} → {len(final_prompt)} chars")
        except Exception as e:
            logger.warning(f"Commercial Director failed, using raw prompt: {e}")

    headers = _fal_headers()
    payload = {
        "prompt": final_prompt,
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
        resp = {
            "ok": True,
            "videoUrl": video_url,
            "model": req.model,
            "durationSeconds": req.durationSeconds,
        }
        if director_notes:
            resp["director"] = director_notes
        return resp

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
        "enhanced_prompt": final_prompt if final_prompt != req.prompt else None,
        "director_notes": director_notes,
    }

    import asyncio
    asyncio.create_task(_poll_fal_job(job_id, status_url, response_url))

    resp = {
        "ok": True,
        "jobId": job_id,
        "status": "processing",
        "model": req.model,
    }
    if director_notes:
        resp["director"] = director_notes
    return resp


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
    if job.get("director_notes"):
        result["director"] = job["director_notes"]
    if job.get("enhanced_prompt"):
        result["enhanced_prompt"] = job["enhanced_prompt"]

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

        status_url = data.get("status_url") or f"https://queue.fal.run/{endpoint}/requests/{request_id}/status"
        result_url = data.get("response_url") or f"https://queue.fal.run/{endpoint}/requests/{request_id}"

        import asyncio
        for _ in range(60):
            await asyncio.sleep(2)
            status_resp = await client.get(status_url, headers=headers)
            if status_resp.status_code not in (200, 202):
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
    await _charge_credits(req.merchantId, "content_image_regen")
    _check_daily_cap(req.merchantId, "image")
    logger.info(f"Image gen: merchant={req.merchantId} {req.width}x{req.height}")

    final_prompt = req.prompt
    director_notes = None

    if req.enhance and req.brand:
        try:
            from ...ai.commercial_director import direct_image
            brand_dict = {
                "business_name": req.brand.business_name,
                "business_type": req.brand.business_type,
                "voice_profile": req.brand.voice_profile or {},
                "merchant_id": req.merchantId,
            }
            result = await direct_image(
                brand=brand_dict,
                prompt=req.prompt,
                platform=req.platform,
                style=req.style,
            )
            final_prompt = result.enhanced_prompt
            director_notes = {
                "style_notes": result.style_notes,
                "model_recommendation": result.model_recommendation,
                "original_prompt": result.original_prompt,
            }
            logger.info(f"Director enhanced image prompt: {len(req.prompt)} → {len(final_prompt)} chars")
        except Exception as e:
            logger.warning(f"Commercial Director failed for image, using raw prompt: {e}")

    payload = {
        "prompt": final_prompt,
        "image_size": {"width": req.width, "height": req.height},
        "safety_tolerance": "2",
    }

    result = await _fal_submit_sync(IMAGE_MODEL, payload)

    images = result.get("images", [])
    if not images:
        raise HTTPException(status_code=500, detail="fal.ai returned no images")

    resp = {
        "ok": True,
        "imageUrl": images[0].get("url"),
        "seed": result.get("seed", 0),
    }
    if director_notes:
        resp["director"] = director_notes
    return resp


class DirectorPreviewRequest(BaseModel):
    merchantId: str
    prompt: str
    platform: str = "instagram_reel"
    style: Optional[str] = None
    media_type: str = "video"
    durationSeconds: int = 5
    brand: Optional[BrandProfile] = None

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Prompt cannot be empty")
        if len(v) > MAX_PROMPT_LENGTH:
            raise ValueError(f"Prompt exceeds {MAX_PROMPT_LENGTH} characters")
        return v


@router.post("/director/preview")
async def director_preview(req: DirectorPreviewRequest):
    """Preview Director-enhanced prompt without generating media."""
    if not req.brand:
        raise HTTPException(status_code=400, detail="Brand profile required for Director preview")

    try:
        from ...ai.commercial_director import direct_video, direct_image
        brand_dict = {
            "business_name": req.brand.business_name,
            "business_type": req.brand.business_type,
            "voice_profile": req.brand.voice_profile or {},
            "merchant_id": req.merchantId,
        }
        if req.media_type == "image":
            result = await direct_image(
                brand=brand_dict,
                prompt=req.prompt,
                platform=req.platform,
                style=req.style,
            )
        else:
            result = await direct_video(
                brand=brand_dict,
                prompt=req.prompt,
                platform=req.platform,
                style=req.style,
                duration_seconds=req.durationSeconds,
            )
        return {
            "ok": True,
            "enhanced_prompt": result.enhanced_prompt,
            "original_prompt": result.original_prompt,
            "generation_config": result.generation_config,
            "style_notes": result.style_notes,
            "model_recommendation": result.model_recommendation,
        }
    except Exception as e:
        logger.error(f"Director preview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Director preview failed: {str(e)}")


@router.get("/director/styles")
async def director_styles():
    """List available Director styles and platform configs."""
    from ...ai.commercial_director import STYLE_PROFILES, PLATFORM_CONFIG, BUSINESS_VISUAL_LANGUAGE
    return {
        "styles": {k: v for k, v in STYLE_PROFILES.items()},
        "platforms": PLATFORM_CONFIG,
        "business_types": {k: v for k, v in BUSINESS_VISUAL_LANGUAGE.items()},
    }


# ── Website scraper — extract brand info, logos, content ───────────────────

class ScrapeRequest(BaseModel):
    url: str
    merchantId: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        if len(v) > 2000:
            raise ValueError("URL too long")
        return v


@router.post("/scrape/website")
async def scrape_website(req: ScrapeRequest):
    """Scrape a merchant's website for brand info, logos, meta, and page content."""
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlparse

    logger.info(f"Scraping website: {req.url} for merchant={req.merchantId}")

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        try:
            resp = await client.get(req.url, headers={
                "User-Agent": "MeridianBot/1.0 (content optimization)",
                "Accept": "text/html,application/xhtml+xml",
            })
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Website returned {resp.status_code}")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Website timed out")
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Could not connect to website")

    html = resp.text
    soup = BeautifulSoup(html, "lxml")

    base_url = req.url.rstrip("/")
    parsed = urlparse(base_url)
    domain = parsed.netloc

    # Extract title and meta
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_desc = ""
    meta_kw = ""
    for meta in soup.find_all("meta"):
        name = (meta.get("name") or meta.get("property") or "").lower()
        content = meta.get("content", "")
        if name in ("description", "og:description"):
            meta_desc = content
        if name == "keywords":
            meta_kw = content

    # Extract logos
    logos: list[str] = []
    for tag in soup.find_all("img"):
        src = tag.get("src", "")
        alt = (tag.get("alt") or "").lower()
        cls = " ".join(tag.get("class") or []).lower()
        if any(kw in alt + cls + src.lower() for kw in ["logo", "brand", "header-img"]):
            full_url = urljoin(base_url, src)
            if full_url not in logos:
                logos.append(full_url)
    # Also check link[rel=icon]
    for link in soup.find_all("link", rel=lambda r: r and any(x in r for x in ["icon", "apple-touch-icon"])):
        href = link.get("href", "")
        if href:
            logos.append(urljoin(base_url, href))

    # Extract main text content
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    body_text = soup.get_text(separator="\n", strip=True)
    # Deduplicate empty lines and truncate
    lines = [line.strip() for line in body_text.split("\n") if line.strip()]
    body_text = "\n".join(lines[:200])  # First ~200 lines

    # Extract headings for structure
    headings = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        text = h.get_text(strip=True)
        if text:
            headings.append({"level": h.name, "text": text[:200]})

    # Extract social links
    social_links: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        for platform in ["instagram.com", "facebook.com", "tiktok.com", "twitter.com", "x.com", "linkedin.com", "youtube.com", "yelp.com"]:
            if platform in href:
                name = platform.split(".")[0]
                if name == "x":
                    name = "twitter"
                social_links[name] = href

    # Extract colors from inline styles and CSS (basic)
    colors: list[str] = []
    import re
    for style in soup.find_all("style"):
        found = re.findall(r"#[0-9a-fA-F]{3,8}", style.string or "")
        colors.extend(found[:10])
    colors = list(dict.fromkeys(colors))[:8]

    return {
        "ok": True,
        "domain": domain,
        "title": title,
        "meta_description": meta_desc,
        "meta_keywords": meta_kw,
        "logos": logos[:5],
        "headings": headings[:20],
        "social_links": social_links,
        "brand_colors": colors,
        "content_preview": body_text[:3000],
        "word_count": len(body_text.split()),
    }


# ── SEO content generation ────────────────────────────────────────────────

class SeoGenRequest(BaseModel):
    merchantId: str
    targetKeyword: str
    websiteUrl: Optional[str] = None
    contentType: str = "blog_post"  # blog_post, landing_page, product_page, faq
    wordCount: int = 800
    websiteContext: Optional[str] = None

    @field_validator("targetKeyword")
    @classmethod
    def validate_keyword(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Target keyword cannot be empty")
        if len(v) > 200:
            raise ValueError("Keyword too long")
        return v

    @field_validator("wordCount")
    @classmethod
    def validate_word_count(cls, v: int) -> int:
        if v < 300 or v > 3000:
            raise ValueError("Word count must be 300-3000")
        return v


SEO_CONTENT_TYPES = {
    "blog_post": "SEO-optimized blog post with headers, internal link suggestions, and meta description",
    "landing_page": "Conversion-focused landing page copy with hero, features, social proof, and CTA sections",
    "product_page": "Product/service page with benefits, specs, FAQ, and structured data suggestions",
    "faq": "FAQ page with schema markup suggestions targeting featured snippets and People Also Ask",
}


@router.post("/seo/generate")
async def generate_seo(req: SeoGenRequest):
    """Generate SEO content using LLM with optional website context."""
    await _charge_credits(req.merchantId, "content_seo_article")
    _check_daily_cap(req.merchantId, "image")  # reuse image cap for text gen

    content_desc = SEO_CONTENT_TYPES.get(req.contentType, SEO_CONTENT_TYPES["blog_post"])

    system_prompt = f"""You are Meridian's SEO content writer. Generate a {content_desc}.

RULES:
1. Target keyword: "{req.targetKeyword}" — use it in H1, first paragraph, and 2-3 subheadings
2. Write naturally — keyword density should be 1-2%, not stuffed
3. Include a meta title (under 60 chars) and meta description (under 155 chars)
4. Use H2 and H3 headers to structure the content
5. Include 2-3 internal link placeholders marked as [INTERNAL LINK: topic]
6. Add 1-2 external authority link suggestions
7. Write at least {req.wordCount} words
8. Include a clear CTA at the end
9. Respond with valid JSON only

If website context is provided, reference the business's actual products, services, and brand voice."""

    user_msg = f"Generate a {req.contentType} targeting '{req.targetKeyword}'"
    if req.websiteContext:
        user_msg += f"\n\nWebsite context:\n{req.websiteContext[:2000]}"

    try:
        from ...ai.llm_layer import _call_llm

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": user_msg
                + '\n\nRespond with JSON: {"meta_title": "...", "meta_description": "...", '
                '"content_html": "...", "word_count": 0, "keyword_density": 0.0, '
                '"headers": ["H2: ...", "H3: ..."], "internal_links": ["topic1"], '
                '"schema_suggestion": "Article or FAQPage"}'
            },
        ]

        result = await _call_llm(messages, org_id=req.merchantId)
        if not result:
            raise HTTPException(status_code=503, detail="LLM unavailable — try again")

        return {
            "ok": True,
            "seo_content": result,
            "target_keyword": req.targetKeyword,
            "content_type": req.contentType,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SEO generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SEO generation failed: {str(e)}")


# ── Social post generation ────────────────────────────────────────────────

class PostGenRequest(BaseModel):
    merchantId: str
    prompt: str
    platform: str = "instagram"
    postType: str = "social"  # social, gmb_post, ad_creative
    referenceImageUrl: Optional[str] = None
    brand: Optional[BrandProfile] = None
    websiteContext: Optional[str] = None

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Prompt cannot be empty")
        if len(v) > 500:
            raise ValueError("Prompt exceeds 500 characters")
        return v


@router.post("/post/generate")
async def generate_post(req: PostGenRequest):
    """Generate a social media post with AI."""
    await _charge_credits(req.merchantId, "content_social_post")
    platform_specs = {
        "instagram": "Instagram (2200 char cap, 30 hashtags max, visual-first)",
        "facebook": "Facebook (longer form OK, link previews, engagement questions)",
        "tiktok": "TikTok (short punchy caption, trending hashtags, CTA)",
        "google_business": "Google Business Profile (250 chars, local SEO, include hours/location)",
        "linkedin": "LinkedIn (professional tone, industry insights, thought leadership)",
    }
    platform_desc = platform_specs.get(req.platform, platform_specs["instagram"])

    brand_context = ""
    if req.brand:
        brand_context = f"\nBusiness: {req.brand.business_name} ({req.brand.business_type})"
        vp = req.brand.voice_profile or {}
        if vp.get("tone"):
            brand_context += f"\nTone: {vp['tone']}"
        if vp.get("top_products"):
            brand_context += f"\nTop products: {', '.join(vp['top_products'][:5])}"

    website_context = ""
    if req.websiteContext:
        website_context = f"\n\nWebsite info:\n{req.websiteContext[:1500]}"

    system_prompt = f"""You are Meridian's social media copywriter. Generate a {platform_desc} post.
{brand_context}{website_context}

RULES:
1. Hook in the first line — stop the scroll
2. Use the brand's tone and reference their actual products
3. Include 3-5 relevant hashtags (niche > generic)
4. End with a specific CTA
5. Match the platform's best practices
6. If a reference image is mentioned, describe how the post relates to it
7. Respond with valid JSON only"""

    try:
        from ...ai.llm_layer import _call_llm

        user_msg = f"Create a {req.platform} post about: {req.prompt}"
        if req.referenceImageUrl:
            user_msg += "\n\nReference image provided — the post should complement this visual."

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": user_msg
                + '\n\nRespond with JSON: {"hook": "...", "body": "...", "hashtags": ["..."], '
                '"call_to_action": "...", "suggested_image_prompt": "..."}'
            },
        ]

        result = await _call_llm(messages, org_id=req.merchantId)
        if not result:
            raise HTTPException(status_code=503, detail="LLM unavailable — try again")

        return {"ok": True, "post": result, "platform": req.platform}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Post generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Post generation failed: {str(e)}")


@router.get("/models")
async def list_models():
    return {
        "video": [
            {"id": k, "endpoint": v}
            for k, v in VIDEO_MODELS.items()
        ],
        "image": IMAGE_MODEL,
    }
