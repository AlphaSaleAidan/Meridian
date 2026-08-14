"""
Ad Spot API — the 30-Second AI Advertisement sold as a Setup Service in both
sales-rep portals (US$1,000 / CA$1,400, billed into the one-time setup fee).

Closing the deal posts the rep's intake here. From that brief the route:

  1. BOARDS the spot — one LLM pass turns the brief into SHOT_COUNT beats
     (hook → product → proof → offer → CTA), because no model generates 30
     usable seconds in one shot. Six 5-second shots ARE the 30 seconds.
  2. DIRECTS each beat through the Commercial Director (src/ai/commercial_director)
     so every shot carries the merchant's brand voice and the placement's
     aspect ratio.
  3. SUBMITS each shot to the same fal.ai queue the content studio already
     runs on, then polls each to completion.

  4. ASSEMBLES the shots into a master on request (src/media/spot_assembly.py:
     concat to exact runtime, Telnyx voiceover of the boarded script, ducked
     music bed, optional burned captions) and uploads it to Supabase Storage.

`shots_ready` means footage in hand. `assembled` means a master exists and a
human should watch it. Only POST /{id}/deliver marks a spot delivered — nothing
in this pipeline decides on its own that a merchant's ad is finished.

Routes:
  POST /api/content/ad-spot/order              → record the sold brief + start generation
  GET  /api/content/ad-spot/{order_id}         → order + per-shot status
  GET  /api/content/ad-spot                    → orders for the calling rep
  POST /api/content/ad-spot/{id}/shots/{n}/retry → re-generate one weak or failed shot
  POST /api/content/ad-spot/{id}/assemble      → cut the shots into a master
  POST /api/content/ad-spot/{id}/deliver       → hand the master over (admin)
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from ..auth import require_admin_jwt, require_jwt
from .content import FAL_BASE, VIDEO_MODELS, _fal_headers

router = APIRouter(prefix="/api/content/ad-spot", tags=["content", "ad-spot"])
logger = logging.getLogger("meridian.content.ad_spot")

# ── Spot shape ───────────────────────────────────────────────────────────────
# 6 shots × 5s = the 30 seconds the merchant bought. Keep these in step with
# AD_SPOT_SERVICE.shotCount / durationSeconds in frontend/src/lib/proposal-plans.ts
# — that object is what the rep quotes off, this is what actually generates.
SHOT_COUNT = 6
SHOT_SECONDS = 5

# Models the spot may generate on. Bounded on purpose: the Director is free to
# recommend anything, but a $1,000 deliverable should not be able to route
# itself onto an unpredictably-priced endpoint. Order = preference.
ALLOWED_MODELS = ["kling-v2.5-turbo", "seedance-2", "seedance-2-fast", "kling-v3", "veo-3.1"]
DEFAULT_MODEL = os.getenv("AD_SPOT_MODEL", "kling-v2.5-turbo")

# Placement → aspect ratio. Ids match AD_SPOT_PLACEMENTS in the frontend.
PLACEMENT_ASPECT = {
    "instagram_reel": "9:16",
    "instagram_feed": "1:1",
    "youtube_video": "16:9",
}

MAX_POLLS = 200          # × POLL_INTERVAL ≈ 10 min per shot
POLL_INTERVAL = 3

# Supabase Storage bucket the cut masters land in (migration 078 creates it;
# the upload path also creates it on demand so a fresh env self-heals).
STORAGE_BUCKET = os.getenv("AD_SPOT_BUCKET", "ad-spots")

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _get_supabase() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    return url, key


def _sb_headers(service_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Content-Type": "application/json",
    }


def _require_supabase() -> tuple[str, str]:
    url, key = _get_supabase()
    if not url or not key:
        raise HTTPException(503, "Supabase not configured — cannot record a paid ad-spot order")
    return url, key


async def _sb_patch(table: str, row_id: str, patch: dict) -> None:
    """Best-effort row update. A failed status write must never abandon a paid
    order mid-generation, so this logs and returns rather than raising."""
    url, key = _get_supabase()
    if not url or not key:
        return
    patch = {**patch, "updated_at": datetime.now(timezone.utc).isoformat()}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.patch(
                f"{url}/rest/v1/{table}?id=eq.{row_id}",
                headers=_sb_headers(key),
                json=patch,
            )
        if resp.status_code not in (200, 204):
            logger.error("%s patch %s failed: %s %s", table, row_id, resp.status_code, resp.text[:200])
    except Exception as exc:  # noqa: BLE001 — never break the pipeline on a write
        logger.error("%s patch %s errored: %s", table, row_id, exc)


# ── Request models ───────────────────────────────────────────────────────────

class AdSpotOrderRequest(BaseModel):
    market: str                       # 'us' | 'ca'
    businessName: str
    businessType: str = "retail"
    goal: str                         # the brief — what the ad must sell/do
    placement: str = "instagram_reel"
    audio: str = "voiceover_music"
    highlights: Optional[str] = None  # products/dishes/services to feature
    brandNotes: Optional[str] = None
    priceCents: int
    orgId: Optional[str] = None
    leadId: Optional[str] = None
    repId: Optional[str] = None
    repName: Optional[str] = None
    contactEmail: Optional[str] = None

    @field_validator("market")
    @classmethod
    def validate_market(cls, v: str) -> str:
        if v not in ("us", "ca"):
            raise ValueError("market must be 'us' or 'ca'")
        return v

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) < 10:
            raise ValueError("goal is the creative brief — give the director something to work from")
        return v[:2000]

    @field_validator("businessName")
    @classmethod
    def validate_business(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("businessName is required")
        return v[:200]

    @field_validator("placement")
    @classmethod
    def validate_placement(cls, v: str) -> str:
        if v not in PLACEMENT_ASPECT:
            raise ValueError(f"placement must be one of {sorted(PLACEMENT_ASPECT)}")
        return v

    @field_validator("priceCents")
    @classmethod
    def validate_price(cls, v: int) -> int:
        if v < 0:
            raise ValueError("priceCents cannot be negative")
        return v


class AdSpotDeliverRequest(BaseModel):
    #: Omit to hand over the assembled master. Supply a URL to deliver a cut
    #: that was finished outside the pipeline (an editor's pass, say).
    deliveredUrl: Optional[str] = None

    @field_validator("deliveredUrl")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not v.startswith("https://"):
            raise ValueError("deliveredUrl must be an https URL")
        return v


# ── Storyboard ───────────────────────────────────────────────────────────────

_VO_RULES_MARKERS = ("<!-- VO-RULES:START -->", "<!-- VO-RULES:END -->")

_vo_rules_cache: str | None = None


def _load_vo_rules() -> str:
    """The house rules for writing the read, pulled from the standards doc.

    docs/ad-creative-standards.md is the recreation template for a spot, and
    its voiceover rules block is the method that actually produced usable
    reads. Loading it here rather than restating it means the doc and the
    prompt cannot drift apart — edit the doc, the scripts change.

    The Commercial Director only ever sees the first 3,000 characters of that
    file (see commercial_director._enhance_with_llm), and the voiceover section
    sits well past that cut, so this loader is the only path by which these
    rules reach an LLM at all.
    """
    global _vo_rules_cache
    if _vo_rules_cache is not None:
        return _vo_rules_cache

    start, end = _VO_RULES_MARKERS
    path = Path(__file__).resolve().parents[3] / "docs" / "ad-creative-standards.md"
    try:
        text = path.read_text()
        block = text.split(start, 1)[1].split(end, 1)[0].strip()
        _vo_rules_cache = block
        logger.info("Loaded voiceover rules from ad-creative-standards.md (%d chars)", len(block))
    except (OSError, IndexError):
        # Never fail an order over a missing doc — fall back to the short form.
        logger.warning("Could not load the voiceover rules block — using the inline fallback")
        _vo_rules_cache = (
            "- One line per shot, under 14 words — it is spoken over a single shot.\n"
            "- Write for performance: ellipsis for a breath, em-dash for the pivot, "
            "ONE stressed word in caps.\n"
            "- Say numbers the way a person says them (\"forty-three hundred\").\n"
            "- The lines must read as one continuous script.\n"
            "- Let the picture carry the detail; the read carries the idea.\n"
            "- Never write a claim the business cannot stand behind."
        )
    return _vo_rules_cache


def _storyboard_system() -> str:
    return f"""You are Meridian's Commercial Director boarding a {SHOT_COUNT * SHOT_SECONDS}-second
television-quality advertisement for a small business.

The finished spot is cut from exactly {SHOT_COUNT} shots of {SHOT_SECONDS} seconds each.
Write the shot list. Structure the {SHOT_COUNT * SHOT_SECONDS} seconds as a real ad:
open on a hook that stops the scroll, establish the business, show the product or
service doing its job, land one proof or benefit, state the offer, close on the
call to action.

SHOT RULES:
1. Every shot must be filmable as a single continuous {SHOT_SECONDS}-second take — one
   subject, one camera move. Never describe a cut inside a shot.
2. Describe only what the camera SEES. No text overlays, no logos, no captions
   (those are added in the finishing cut).
3. Shots must be visually distinct from one another — vary subject, scale and angle.
4. Respond with valid JSON only.

VOICEOVER RULES — `voiceover` is the line read aloud over that shot. These are the
house rules and they are what make the read usable:
{_load_vo_rules()}"""


def _storyboard_user_content(req: AdSpotOrderRequest) -> str:
    return json.dumps({
        "business_name": req.businessName,
        "business_type": req.businessType,
        "what_the_ad_must_do": req.goal,
        "feature_these": req.highlights or "",
        "brand_notes": req.brandNotes or "",
        "placement": req.placement,
        "aspect_ratio": PLACEMENT_ASPECT[req.placement],
        "audio_treatment": req.audio,
        "shot_count": SHOT_COUNT,
        "seconds_per_shot": SHOT_SECONDS,
    })


def _fallback_storyboard(req: AdSpotOrderRequest) -> list[dict]:
    """Used when the LLM is unreachable. Deliberately generic but structurally
    correct — a human can rewrite beats, but the order still generates."""
    name = req.businessName
    feature = req.highlights or "their signature offering"
    beats = [
        f"Opening hook: an arresting close-up inside {name} that stops the scroll",
        f"Establishing shot of {name} — the space, alive and inviting",
        f"Hero shot of {feature}, shown in loving detail",
        f"A customer at {name} enjoying {feature}, genuine reaction",
        "The team at work — craft, care and speed on display",
        f"Closing shot: {name} at its most inviting, ready for the viewer to walk in",
    ]
    return [
        {"shot": i + 1, "beat": b, "voiceover": ""}
        for i, b in enumerate(beats[:SHOT_COUNT])
    ]


async def _board_spot(req: AdSpotOrderRequest) -> list[dict]:
    """One LLM pass → SHOT_COUNT beats. Falls back to a structural board."""
    try:
        from ...ai.llm_layer import _call_llm
    except ImportError:
        logger.warning("llm_layer unavailable — using fallback storyboard")
        return _fallback_storyboard(req)

    messages = [
        {
            "role": "system",
            "content": _storyboard_system() + (
                '\n\nRespond with ONLY: {"shots": [{"shot": 1, "beat": "...", "voiceover": "..."}, ...]}'
                f"\nExactly {SHOT_COUNT} shots, numbered 1..{SHOT_COUNT}."
            ),
        },
        {"role": "user", "content": _storyboard_user_content(req)},
    ]

    try:
        result = await _call_llm(messages, org_id=req.orgId, agent_name="ad_spot_director")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Storyboard LLM call failed (%s) — using fallback", exc)
        return _fallback_storyboard(req)

    shots = (result or {}).get("shots") or []
    shots = [s for s in shots if isinstance(s, dict) and s.get("beat")]
    if len(shots) < SHOT_COUNT:
        logger.warning("Storyboard returned %d/%d shots — padding from fallback", len(shots), SHOT_COUNT)
        shots += _fallback_storyboard(req)[len(shots):]
    for i, s in enumerate(shots[:SHOT_COUNT]):
        s["shot"] = i + 1
    return shots[:SHOT_COUNT]


# ── Generation ───────────────────────────────────────────────────────────────

def _pick_model(recommended: str | None) -> str:
    if recommended in ALLOWED_MODELS:
        return recommended
    return DEFAULT_MODEL if DEFAULT_MODEL in VIDEO_MODELS else ALLOWED_MODELS[0]


async def _submit_shot(client: httpx.AsyncClient, order_id: str, shot_row_id: str,
                       prompt: str, model: str, aspect: str) -> dict | None:
    """Submit one shot to the fal queue. Returns the queue handles, or None."""
    endpoint = VIDEO_MODELS.get(model)
    if not endpoint:
        await _sb_patch("ad_spot_shots", shot_row_id, {"status": "failed", "error": f"unknown model {model}"})
        return None

    payload = {"prompt": prompt, "duration": SHOT_SECONDS, "aspect_ratio": aspect}
    try:
        resp = await client.post(f"{FAL_BASE}/{endpoint}", headers=_fal_headers(), json=payload)
    except Exception as exc:  # noqa: BLE001
        await _sb_patch("ad_spot_shots", shot_row_id, {"status": "failed", "error": f"submit error: {exc}"[:400]})
        return None

    if resp.status_code not in (200, 201):
        await _sb_patch("ad_spot_shots", shot_row_id, {
            "status": "failed",
            "error": f"fal submit {resp.status_code}: {resp.text[:300]}",
        })
        return None

    data = resp.json()
    request_id = data.get("request_id")

    # Some endpoints answer synchronously with the finished video.
    if not request_id:
        video_url = (
            data.get("video", {}).get("url")
            or data.get("video_url")
            or (data.get("videos", [{}])[0].get("url") if data.get("videos") else None)
        )
        await _sb_patch("ad_spot_shots", shot_row_id, {
            "status": "completed" if video_url else "failed",
            "video_url": video_url,
            "error": None if video_url else "fal returned no request_id and no video",
        })
        return None

    handles = {
        "fal_request_id": request_id,
        "fal_status_url": data.get("status_url") or f"{FAL_BASE}/{endpoint}/requests/{request_id}/status",
        "fal_response_url": data.get("response_url") or f"{FAL_BASE}/{endpoint}/requests/{request_id}",
    }
    await _sb_patch("ad_spot_shots", shot_row_id, {"status": "generating", **handles})
    logger.info("order=%s shot=%s submitted request_id=%s", order_id, shot_row_id, request_id)
    return handles


async def _poll_shot(client: httpx.AsyncClient, shot_row_id: str, handles: dict) -> bool:
    """Poll one shot to completion. Returns True if a video landed."""
    headers = _fal_headers()
    for _ in range(MAX_POLLS):
        await asyncio.sleep(POLL_INTERVAL)
        try:
            status_resp = await client.get(handles["fal_status_url"], headers=headers)
            if status_resp.status_code not in (200, 202):
                continue
            status = status_resp.json().get("status", "")

            if status in ("COMPLETED", "completed", "succeeded"):
                result_resp = await client.get(handles["fal_response_url"], headers=headers)
                if result_resp.status_code != 200:
                    await _sb_patch("ad_spot_shots", shot_row_id, {
                        "status": "failed",
                        "error": f"result fetch HTTP {result_resp.status_code}",
                    })
                    return False
                result = result_resp.json()
                video_url = (
                    result.get("video", {}).get("url")
                    or result.get("video_url")
                    or (result.get("videos", [{}])[0].get("url") if result.get("videos") else None)
                )
                await _sb_patch("ad_spot_shots", shot_row_id, {
                    "status": "completed" if video_url else "failed",
                    "video_url": video_url,
                    "error": None if video_url else "completed with no video url",
                })
                return bool(video_url)

            if status in ("FAILED", "failed"):
                await _sb_patch("ad_spot_shots", shot_row_id, {"status": "failed", "error": "fal reported FAILED"})
                return False
        except Exception as exc:  # noqa: BLE001
            logger.warning("shot %s poll error: %s", shot_row_id, exc)
            continue

    await _sb_patch("ad_spot_shots", shot_row_id, {"status": "failed", "error": "generation timed out"})
    return False


async def _run_order(order_id: str, req: AdSpotOrderRequest) -> None:
    """Board → direct → submit → poll. Owns the order's status transitions."""
    url, key = _get_supabase()
    aspect = PLACEMENT_ASPECT[req.placement]
    brand = {
        "business_name": req.businessName,
        "business_type": req.businessType,
        "voice_profile": {"top_products": [h.strip() for h in (req.highlights or "").split(",") if h.strip()][:5]},
        "merchant_id": req.orgId,
    }

    try:
        storyboard = await _board_spot(req)
    except Exception as exc:  # noqa: BLE001
        logger.exception("order=%s boarding failed", order_id)
        await _sb_patch("ad_spot_orders", order_id, {"status": "failed", "status_detail": f"boarding failed: {exc}"[:400]})
        return

    # Direct each beat into a generation prompt.
    try:
        from ...ai.commercial_director import direct_video
    except ImportError:
        direct_video = None  # type: ignore[assignment]

    shots: list[dict] = []
    for beat in storyboard:
        prompt, model = beat["beat"], DEFAULT_MODEL
        if direct_video is not None:
            try:
                directed = await direct_video(
                    brand=brand,
                    prompt=beat["beat"],
                    platform=req.placement,
                    duration_seconds=SHOT_SECONDS,
                )
                prompt = directed.enhanced_prompt
                model = _pick_model(directed.model_recommendation)
            except Exception as exc:  # noqa: BLE001
                logger.warning("order=%s shot=%s director failed: %s", order_id, beat["shot"], exc)
        shots.append({**beat, "prompt": prompt, "model": model})

    await _sb_patch("ad_spot_orders", order_id, {
        "status": "generating",
        "storyboard": {"aspect_ratio": aspect, "shots": shots},
    })

    # Persist the shot rows, then submit + poll them concurrently.
    shot_rows: list[dict] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for s in shots:
            payload = {
                "order_id": order_id,
                "shot_number": s["shot"],
                "beat": s["beat"],
                "prompt": s["prompt"],
                "model": s["model"],
                "duration_seconds": SHOT_SECONDS,
                "status": "queued",
            }
            try:
                resp = await client.post(
                    f"{url}/rest/v1/ad_spot_shots",
                    headers={**_sb_headers(key), "Prefer": "return=representation"},
                    json=payload,
                )
                if resp.status_code in (200, 201) and resp.json():
                    shot_rows.append({**s, "row_id": resp.json()[0]["id"]})
                else:
                    logger.error("order=%s shot=%s insert failed: %s", order_id, s["shot"], resp.text[:200])
            except Exception as exc:  # noqa: BLE001
                logger.error("order=%s shot=%s insert errored: %s", order_id, s["shot"], exc)

        if not shot_rows:
            await _sb_patch("ad_spot_orders", order_id, {
                "status": "failed",
                "status_detail": "could not record any shot — nothing was submitted for generation",
            })
            return

        async def one(row: dict) -> bool:
            handles = await _submit_shot(client, order_id, row["row_id"], row["prompt"], row["model"], aspect)
            if handles is None:
                return False
            return await _poll_shot(client, row["row_id"], handles)

        results = await asyncio.gather(*(one(r) for r in shot_rows), return_exceptions=True)

    landed = sum(1 for r in results if r is True)
    if landed == 0:
        await _sb_patch("ad_spot_orders", order_id, {
            "status": "failed",
            "status_detail": f"0/{len(shot_rows)} shots generated",
        })
    else:
        await _sb_patch("ad_spot_orders", order_id, {
            "status": "shots_ready",
            "status_detail": f"{landed}/{len(shot_rows)} shots generated — awaiting the finishing cut",
        })
    logger.info("order=%s finished: %d/%d shots", order_id, landed, len(shot_rows))


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/order")
async def create_ad_spot_order(req: AdSpotOrderRequest, user: dict = Depends(require_jwt)):
    """Record a sold 30-second spot and start generating its shots.

    Called by both create-customer flows the moment the rep closes. The order
    row is written synchronously (so a paid deal is never lost to a hiccup in
    the generation pipeline); boarding and generation run in the background.
    """
    url, key = _require_supabase()

    payload = {
        "org_id": req.orgId or None,
        "market": req.market,
        "lead_id": req.leadId or None,
        "rep_id": req.repId or None,
        "rep_name": req.repName or None,
        "business_name": req.businessName,
        "business_type": req.businessType,
        "contact_email": req.contactEmail or None,
        "price_cents": req.priceCents,
        "currency": "CAD" if req.market == "ca" else "USD",
        "goal": req.goal,
        "highlights": req.highlights or None,
        "brand_notes": req.brandNotes or None,
        "placement": req.placement,
        "aspect_ratio": PLACEMENT_ASPECT[req.placement],
        "audio": req.audio,
        "status": "boarding",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{url}/rest/v1/ad_spot_orders",
            headers={**_sb_headers(key), "Prefer": "return=representation"},
            json=payload,
        )
    if resp.status_code not in (200, 201) or not resp.json():
        logger.error("ad-spot order insert failed: %s %s", resp.status_code, resp.text[:300])
        raise HTTPException(500, "Could not record the ad-spot order")

    order_id = resp.json()[0]["id"]
    logger.info("ad-spot order %s created for %s (%s)", order_id, req.businessName, req.market)

    asyncio.create_task(_run_order(order_id, req))
    asyncio.create_task(_open_foundry_contest(order_id, req))

    return {
        "ok": True,
        "orderId": order_id,
        "status": "boarding",
        "shotCount": SHOT_COUNT,
        "durationSeconds": SHOT_COUNT * SHOT_SECONDS,
    }


@router.get("/{order_id}")
async def get_ad_spot_order(order_id: str, user: dict = Depends(require_jwt)):
    """Order + per-shot status. `shots_ready` means the footage landed, not
    that the finished ad has been delivered."""
    if not _UUID_RE.match(order_id):
        raise HTTPException(400, "Invalid order id")
    url, key = _require_supabase()

    async with httpx.AsyncClient(timeout=15.0) as client:
        order_resp = await client.get(
            f"{url}/rest/v1/ad_spot_orders?id=eq.{order_id}&select=*",
            headers=_sb_headers(key),
        )
        shots_resp = await client.get(
            f"{url}/rest/v1/ad_spot_shots?order_id=eq.{order_id}&select=*&order=shot_number.asc",
            headers=_sb_headers(key),
        )

    rows = order_resp.json() if order_resp.status_code == 200 else []
    if not rows:
        raise HTTPException(404, "Ad-spot order not found")
    shots = shots_resp.json() if shots_resp.status_code == 200 else []

    return {
        "ok": True,
        "order": rows[0],
        "shots": shots,
        "shotsCompleted": sum(1 for s in shots if s.get("status") == "completed"),
        "shotsTotal": len(shots) or SHOT_COUNT,
    }


@router.get("")
async def list_ad_spot_orders(repId: Optional[str] = None, user: dict = Depends(require_jwt)):
    """Orders for a rep (or the 50 most recent when no rep is given)."""
    url, key = _require_supabase()
    query = "select=*&order=created_at.desc&limit=50"
    if repId:
        if not re.match(r"^[A-Za-z0-9_.@-]{1,100}$", repId):
            raise HTTPException(400, "Invalid rep id")
        query += f"&rep_id=eq.{repId}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{url}/rest/v1/ad_spot_orders?{query}", headers=_sb_headers(key))

    return {"ok": True, "orders": resp.json() if resp.status_code == 200 else []}


async def _open_foundry_contest(order_id: str, req: AdSpotOrderRequest) -> None:
    """Record the sold spot as a work order on the shared Setup Services path.

    Every adder follows one rule (Aidan 2026-08-14): the merchant pays, a work
    order is created, it goes on the Foundry board, developers submit real work
    and the owner picks. The spot used to post its own contest straight from
    here at close; that is now recorded as a work order and posted when the
    payment lands (src/services/setup_services.py).

    The house cut still generates immediately — the merchant paid for a
    finished spot, not for a contest — so what changes is only WHEN creators
    get to compete for it.

    Best-effort: a recording failure is logged onto the order rather than
    raised, because the spot itself is already generating.
    """
    try:
        from ...services.setup_services import record_work_order
        row = await record_work_order(
            service_kind="ad_spot",
            market=req.market,
            business_name=req.businessName,
            business_type=req.businessType,
            price_cents=req.priceCents,
            org_id=req.orgId,
            lead_id=req.leadId,
            rep_id=req.repId,
            rep_name=req.repName,
            contact_email=req.contactEmail,
            brief={
                "goal": req.goal,
                "highlights": req.highlights or "",
                "brandNotes": req.brandNotes or "",
                "placement": req.placement,
                "audio": req.audio,
                "durationSeconds": SHOT_COUNT * SHOT_SECONDS,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("order=%s work order not recorded: %s", order_id, exc)
        await _sb_patch("ad_spot_orders", order_id, {
            "foundry_detail": f"work order not recorded: {exc}"[:300],
        })
        return

    if row:
        await _sb_patch("ad_spot_orders", order_id, {
            "foundry_detail": "work order recorded — posts to the board when payment lands",
        })
        logger.info("order=%s work order %s recorded", order_id, row["id"])
    else:
        await _sb_patch("ad_spot_orders", order_id, {
            "foundry_detail": "work order not recorded (one may already be live)",
        })


async def _fetch_order(client: httpx.AsyncClient, url: str, key: str, order_id: str) -> dict:
    resp = await client.get(
        f"{url}/rest/v1/ad_spot_orders?id=eq.{order_id}&select=*", headers=_sb_headers(key)
    )
    rows = resp.json() if resp.status_code == 200 else []
    if not rows:
        raise HTTPException(404, "Ad-spot order not found")
    return rows[0]


async def _fetch_shots(client: httpx.AsyncClient, url: str, key: str, order_id: str) -> list[dict]:
    resp = await client.get(
        f"{url}/rest/v1/ad_spot_shots?order_id=eq.{order_id}&select=*&order=shot_number.asc",
        headers=_sb_headers(key),
    )
    return resp.json() if resp.status_code == 200 else []


@router.post("/{order_id}/shots/{shot_number}/retry")
async def retry_shot(order_id: str, shot_number: int, user: dict = Depends(require_jwt)):
    """Re-generate a single shot — the one that came back wrong, without
    re-rolling (or re-paying for) the other five."""
    if not _UUID_RE.match(order_id):
        raise HTTPException(400, "Invalid order id")
    if not 1 <= shot_number <= SHOT_COUNT:
        raise HTTPException(400, f"shot_number must be 1..{SHOT_COUNT}")
    url, key = _require_supabase()

    async with httpx.AsyncClient(timeout=30.0) as client:
        order = await _fetch_order(client, url, key, order_id)
        shots = await _fetch_shots(client, url, key, order_id)
        shot = next((s for s in shots if s.get("shot_number") == shot_number), None)
        if not shot:
            raise HTTPException(404, f"Shot {shot_number} not found on this order")
        if not shot.get("prompt"):
            raise HTTPException(409, "That shot has no prompt to re-run — re-board the order instead")

        aspect = order.get("aspect_ratio") or PLACEMENT_ASPECT["instagram_reel"]
        await _sb_patch("ad_spot_shots", shot["id"], {
            "status": "queued", "video_url": None, "error": None,
            "fal_request_id": None, "fal_status_url": None, "fal_response_url": None,
        })
        handles = await _submit_shot(
            client, order_id, shot["id"], shot["prompt"],
            _pick_model(shot.get("model")), aspect,
        )
        if handles is None:
            raise HTTPException(502, "Could not resubmit that shot to the generation queue")

    async def finish() -> None:
        async with httpx.AsyncClient(timeout=30.0) as poll_client:
            await _poll_shot(poll_client, shot["id"], handles)

    asyncio.create_task(finish())
    return {"ok": True, "orderId": order_id, "shotNumber": shot_number, "status": "generating"}


async def _upload_master(client: httpx.AsyncClient, url: str, key: str,
                         order_id: str, data: bytes) -> str:
    """Put the cut MP4 in the ad-spots bucket and return its public URL."""
    # Idempotent bucket create — a fresh environment should not need a manual
    # dashboard step before the first spot can be delivered.
    await client.post(
        f"{url}/storage/v1/bucket",
        headers=_sb_headers(key),
        json={"id": STORAGE_BUCKET, "name": STORAGE_BUCKET, "public": True},
    )
    object_path = f"{order_id}/master.mp4"
    resp = await client.post(
        f"{url}/storage/v1/object/{STORAGE_BUCKET}/{object_path}",
        headers={
            "Authorization": f"Bearer {key}",
            "apikey": key,
            "Content-Type": "video/mp4",
            "x-upsert": "true",
        },
        content=data,
    )
    if resp.status_code not in (200, 201):
        raise HTTPException(502, f"Master upload failed ({resp.status_code}): {resp.text[:200]}")
    return f"{url}/storage/v1/object/public/{STORAGE_BUCKET}/{object_path}"


async def _assemble_and_store(order_id: str, order: dict, completed: list[dict]) -> None:
    """Cut, upload, record. Runs detached — see assemble_order for why.

    Every exit path writes a status. An order that silently stayed on
    `assembling` forever would look identical to one still working, and the
    operator would never know to step in.
    """
    try:
        from ...media.spot_assembly import assemble_spot
        result = await assemble_spot(
            shots=completed,
            aspect_ratio=order.get("aspect_ratio") or "9:16",
            shot_seconds=SHOT_SECONDS,
            audio_treatment=order.get("audio") or "voiceover_music",
        )
    except Exception as exc:  # noqa: BLE001 — includes AssemblyError and ImportError
        logger.exception("order=%s assembly failed", order_id)
        await _sb_patch("ad_spot_orders", order_id, {
            "status": "shots_ready",
            "status_detail": f"assembly failed: {exc}"[:400],
        })
        return

    try:
        url, key = _get_supabase()
        async with httpx.AsyncClient(timeout=180.0) as client:
            master_url = await _upload_master(client, url, key, order_id, result.master)
    except Exception as exc:  # noqa: BLE001
        logger.exception("order=%s master upload failed", order_id)
        await _sb_patch("ad_spot_orders", order_id, {
            "status": "shots_ready",
            "status_detail": f"cut fine but the upload failed: {exc}"[:400],
        })
        return

    await _sb_patch("ad_spot_orders", order_id, {
        "status": "assembled",
        "status_detail": f"{result.duration_seconds}s master cut from {len(completed)} shots"
                         + (f" — {'; '.join(result.notes)}" if result.notes else ""),
        "master_url": master_url,
        "assembled_at": datetime.now(timezone.utc).isoformat(),
        "assembly_notes": {
            "notes": result.notes,
            "hasVoiceover": result.has_voiceover,
            "hasMusic": result.has_music,
            "hasCaptions": result.has_captions,
            "width": result.width,
            "height": result.height,
            "shotsUsed": len(completed),
        },
    })
    logger.info("order=%s assembled: %ss, %d shots", order_id, result.duration_seconds, len(completed))


@router.post("/{order_id}/assemble")
async def assemble_order(order_id: str, user: dict = Depends(require_jwt)):
    """Start cutting the completed shots into one master.

    Detached rather than synchronous: encoding six 1080p shots takes minutes,
    and holding the request open that long means a proxy timeout can kill a
    paid deliverable's cut halfway through. The order goes to `assembling` and
    the console polls it — the same way it already watches generation.

    Whatever the cut had to leave out lands in assembly_notes and is shown to
    the operator; it is never quietly dropped.
    """
    if not _UUID_RE.match(order_id):
        raise HTTPException(400, "Invalid order id")
    url, key = _require_supabase()

    async with httpx.AsyncClient(timeout=30.0) as client:
        order = await _fetch_order(client, url, key, order_id)
        shots = await _fetch_shots(client, url, key, order_id)

    completed = [s for s in shots if s.get("status") == "completed" and s.get("video_url")]
    if not completed:
        raise HTTPException(409, "No completed shots yet — nothing to cut")
    if order.get("status") == "assembling":
        raise HTTPException(409, "That spot is already being cut")

    # Carry each shot's boarded voiceover line into assembly: the storyboard
    # holds the script, the shot rows hold the footage.
    board = {
        int(s.get("shot", 0)): s
        for s in ((order.get("storyboard") or {}).get("shots") or [])
        if isinstance(s, dict)
    }
    for s in completed:
        s["voiceover"] = (board.get(s.get("shot_number"), {}) or {}).get("voiceover", "")

    await _sb_patch("ad_spot_orders", order_id, {
        "status": "assembling",
        "status_detail": f"cutting {len(completed)} shots",
    })
    asyncio.create_task(_assemble_and_store(order_id, order, completed))

    return {
        "ok": True,
        "orderId": order_id,
        "status": "assembling",
        "shotsUsed": len(completed),
        "durationSeconds": len(completed) * SHOT_SECONDS,
    }


@router.post("/{order_id}/deliver")
async def deliver_ad_spot(order_id: str, req: AdSpotDeliverRequest, _admin: dict = Depends(require_admin_jwt)):
    """Attach the finished master to the order — the only thing that marks a
    spot delivered. Admin-only: it is the record that the merchant got what
    they paid for."""
    if not _UUID_RE.match(order_id):
        raise HTTPException(400, "Invalid order id")
    url, key = _require_supabase()

    delivered_url = req.deliveredUrl
    if not delivered_url:
        async with httpx.AsyncClient(timeout=15.0) as client:
            order = await _fetch_order(client, url, key, order_id)
        delivered_url = order.get("master_url")
        if not delivered_url:
            raise HTTPException(
                409,
                "Nothing to deliver — assemble the spot first, or pass deliveredUrl "
                "for a cut finished outside the pipeline",
            )

    await _sb_patch("ad_spot_orders", order_id, {
        "status": "delivered",
        "delivered_url": delivered_url,
        "delivered_at": datetime.now(timezone.utc).isoformat(),
        "status_detail": "final master delivered",
    })
    return {"ok": True, "orderId": order_id, "status": "delivered", "deliveredUrl": delivered_url}
