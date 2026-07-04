"""
Phone Agent Dashboard API routes.

Endpoints for the frontend phone orders page:
  GET    /api/phone/config/{merchant_id}   → Get phone agent config
  POST   /api/phone/config                 → Save/update phone agent config
  GET    /api/phone/calls/{merchant_id}    → List call logs
  GET    /api/phone/orders/{merchant_id}   → List phone orders
  GET    /api/phone/stats/{merchant_id}    → Aggregated stats
"""

import logging
import os
import re
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from ..auth import enforce_service_member, require_service_auth
from ...db import get_db

logger = logging.getLogger("meridian.api.phone_dashboard")

router = APIRouter(prefix="/api/phone", tags=["phone-dashboard"])

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I
)


class PhoneConfigRequest(BaseModel):
    merchant_id: str
    business_name: str | None = None
    business_type: str | None = None
    phone_number: str | None = None
    greeting: str | None = None
    voice: str | None = None
    language: str | None = None
    active: bool | None = None
    menu_items: list | None = None
    pos_system: str | None = None
    pos_access_token: str | None = None
    pos_location_id: str | None = None
    business_hours: dict | None = None
    after_hours_message: str | None = None
    max_concurrent_calls: int | None = None
    order_types: list | None = None
    special_instructions_enabled: bool | None = None
    transfer_number: str | None = None
    # How the wizard routes confirmed orders: 'pos' | 'webhook' | 'sms' | 'email'.
    # Persisted to phone_agent_config.order_routing (migration 032). Optional and
    # back-compat: omitting it leaves the stored value untouched (save_phone_config
    # only writes non-None fields).
    order_routing: str | None = None
    # Reservations: hand-off to the restaurant's EXISTING rez system.
    website_url: str | None = None
    reservation_url: str | None = None
    reservation_platform: str | None = None
    reservations_enabled: bool | None = None


def _validate_merchant_id(merchant_id: str):
    if not _UUID_RE.match(merchant_id):
        raise HTTPException(400, "Invalid merchant_id format")


class ReservationScrapeRequest(BaseModel):
    website_url: str


@router.post("/reservations/scrape/{merchant_id}")
async def scrape_reservation_link(
    merchant_id: str, req: ReservationScrapeRequest,
    principal=Depends(require_service_auth),
):
    """Scrape the merchant's website for their existing reservation link
    (OpenTable/Resy/Tock/… or a generic "book a table" anchor) and store it on
    phone_agent_config. Triggered by the wizard's reservation toggle."""
    # BOLA guard: this endpoint WRITES to phone_agent_config, so the principal
    # must own this merchant — same gate as save_phone_config.
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    url = (req.website_url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        url = f"https://{url}"

    from ...services.website_scraper import scrape_website
    scraped = await scrape_website(url)
    if scraped.get("error"):
        raise HTTPException(422, f"Could not scrape {url}: {scraped['error']}")

    rez = scraped.get("reservation") or {}
    db = get_db()
    payload = {
        "website_url": url,
        "reservation_url": rez.get("url", ""),
        "reservation_platform": rez.get("platform", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    rows = await db.select("phone_agent_config",
                           filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    if rows:
        await db.update("phone_agent_config", payload,
                        filters={"merchant_id": f"eq.{merchant_id}"})
    else:
        await db.insert("phone_agent_config", {**payload, "merchant_id": merchant_id})

    logger.info("Reservation scrape for %s: %s (%s)", merchant_id,
                rez.get("url") or "not found", rez.get("platform") or "-")
    return {"ok": True, "found": bool(rez.get("url")),
            "reservation_url": rez.get("url", ""),
            "reservation_platform": rez.get("platform", "")}


@router.get("/config/{merchant_id}")
async def get_phone_config(merchant_id: str, principal=Depends(require_service_auth)):
    """Return phone agent config for a merchant. Returns {exists: false} if none."""
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    db = get_db()

    rows = await db.select(
        "phone_agent_config",
        filters={"merchant_id": f"eq.{merchant_id}"},
        limit=1,
    )

    if not rows:
        return {"exists": False, "merchant_id": merchant_id}

    row = rows[0]
    row.pop("pos_access_token", None)
    return {"exists": True, **row}


@router.post("/config")
async def save_phone_config(req: PhoneConfigRequest, principal=Depends(require_service_auth)):
    """Create or update phone agent configuration."""
    await enforce_service_member(principal, req.merchant_id)
    _validate_merchant_id(req.merchant_id)
    db = get_db()

    rows = await db.select(
        "phone_agent_config",
        filters={"merchant_id": f"eq.{req.merchant_id}"},
        limit=1,
    )

    payload = {
        k: v for k, v in req.model_dump().items()
        if v is not None and k != "merchant_id"
    }
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    if rows:
        await db.update(
            "phone_agent_config",
            payload,
            filters={"merchant_id": f"eq.{req.merchant_id}"},
        )
        logger.info("Updated phone config for %s", req.merchant_id)
    else:
        payload["merchant_id"] = req.merchant_id
        await db.insert("phone_agent_config", payload)
        logger.info("Created phone config for %s", req.merchant_id)

    return {"ok": True, "merchant_id": req.merchant_id}


def _decrypt_connection_token(conn: dict) -> str:
    """Pull a usable access token out of a pos_connections row.

    Two storage shapes exist in the wild: the OAuth callbacks
    (clover_oauth.py, oauth.py) write a single `access_token_enc`; the generic
    connect endpoint (pos_connections.py) writes a `credentials_encrypted` JSONB
    dict of encrypted values. Both are AES-GCM via security.encryption. Returns
    "" if nothing decryptable is present.
    """
    from ...security.encryption import decrypt_token

    enc = conn.get("access_token_enc")
    if enc:
        try:
            return decrypt_token(enc)
        except Exception:  # noqa: BLE001 — tampered/legacy ciphertext, treat as absent
            logger.warning("Could not decrypt access_token_enc for connection")

    creds = conn.get("credentials_encrypted")
    if isinstance(creds, dict):
        for key in ("access_token", "api_key", "token"):
            val = creds.get(key)
            if val:
                try:
                    return decrypt_token(val)
                except Exception:  # noqa: BLE001
                    logger.warning("Could not decrypt credentials_encrypted[%s]", key)
    return ""


# ---------------------------------------------------------------------------
# Auto menu-builder — when a merchant connects their POS, build the phone
# agent's menu from the POS catalog (read-only) and expose VISIBLE progress.
#
# State model (PONYTAIL ceiling): the "building" set is a process-local set of
# merchant_ids whose sync is in flight. It's intentionally NOT persisted — it
# only needs to survive the few seconds an extraction takes, and a single API
# worker handles both the trigger and the status poll for a given merchant.
# Ceiling: with multiple API workers behind a load balancer, a poll could hit a
# worker that doesn't know a build is running; it would then report 'ready'
# (menu_items present) or 'idle' (none) instead of 'building'. That's a cosmetic
# regression in the progress animation only — the menu still builds correctly
# via the background trigger. A `menu_sync_status` column on phone_agent_config
# would make it cross-worker durable; out of scope for the smallest diff.
# ---------------------------------------------------------------------------

_MENU_BUILDING: set[str] = set()


async def _sync_menu_from_pos_impl(merchant_id: str, db) -> dict:
    """Pull the merchant's menu from their connected POS (read-only) and store it.

    The single extraction path — shared by the manual POST /menu/sync endpoint
    and the auto-trigger fired on POS connect (pos_connections). Marks the
    merchant 'building' for the duration so GET /menu/status can show progress.

    Credential resolution, in order:
      1. Manual creds on the phone_agent_config row (pos_system + pos_access_token)
         — honoured first so a hand-entered token wins.
      2. The OAuth-connected POS in pos_connections. In this system merchant_id
         IS the org_id (see spaces.py / camera/pipeline.py), so we read
         pos_connections by org_id, take `provider` as the system and decrypt the
         stored token. `external_merchant_id` fills the catalog URL's {merchant_id}
         slot (Clover needs it).

    The catalog is fetched read-only, coerced into the agent's menu_items shape,
    and persisted onto phone_agent_config so the phone prompt picks it up with no
    data entry and no per-call latency. The POS token is never returned.
    """
    from ...services.pos_connectors.menu_extractor import extract_menu_items

    _MENU_BUILDING.add(merchant_id)
    try:
        config_rows = await db.select(
            "phone_agent_config",
            filters={"merchant_id": f"eq.{merchant_id}"},
            limit=1,
        )
        config_row = config_rows[0] if config_rows else {}

        system = (config_row.get("pos_system") or "").strip()
        token = (config_row.get("pos_access_token") or "").strip()
        location_id = (config_row.get("pos_location_id") or "").strip()
        external_merchant_id = ""
        source = "phone_config"

        if not (system and token):
            conns = await db.select(
                "pos_connections",
                filters={"org_id": f"eq.{merchant_id}", "status": "eq.connected"},
                order="updated_at.desc",
                limit=1,
            )
            if conns:
                conn = conns[0]
                system = system or (conn.get("provider") or "").strip()
                external_merchant_id = (conn.get("external_merchant_id") or "").strip()
                token = token or _decrypt_connection_token(conn)
                source = "pos_connections"

        if not system or not token:
            return {
                "synced": False,
                "reason": "no POS credentials on file (neither manual config nor an OAuth connection)",
                "item_count": 0,
            }

        items = await extract_menu_items(
            system,
            token,
            merchant_id=external_merchant_id,
            location_id=location_id,
        )
        if not items:
            return {
                "synced": False,
                "reason": "POS returned no catalog items (empty menu or auth failed)",
                "item_count": 0,
                "source": source,
            }

        payload = {"menu_items": items, "updated_at": datetime.now(timezone.utc).isoformat()}
        if config_rows:
            await db.update(
                "phone_agent_config",
                payload,
                filters={"merchant_id": f"eq.{merchant_id}"},
            )
        else:
            await db.insert("phone_agent_config", {"merchant_id": merchant_id, **payload})

        logger.info("Synced %d menu items from %s (%s) for %s", len(items), system, source, merchant_id)
        return {"synced": True, "item_count": len(items), "source": source, "sample": items[:5]}
    finally:
        _MENU_BUILDING.discard(merchant_id)


async def auto_build_menu_on_connect(merchant_id: str) -> None:
    """Best-effort auto-trigger fired after a POS connection becomes active.

    Reuses the exact extraction path the manual endpoint uses. Never raises — a
    menu-build failure must not break the POS connect response. Skips merchants
    whose id isn't a UUID (the menu_items shape keys off the org/merchant id).
    """
    if not _UUID_RE.match(merchant_id or ""):
        return
    try:
        db = get_db()
        result = await _sync_menu_from_pos_impl(merchant_id, db)
        logger.info("auto menu-build for %s: %s", merchant_id, result.get("reason") or f"{result.get('item_count', 0)} items")
    except Exception as e:  # noqa: BLE001 — auto-build is best-effort, never break connect
        logger.warning("auto menu-build failed for %s: %s", merchant_id, e)


@router.post("/menu/sync/{merchant_id}")
async def sync_menu_from_pos(merchant_id: str, principal=Depends(require_service_auth)):
    """Manual trigger: pull the merchant's menu from their connected POS."""
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    return await _sync_menu_from_pos_impl(merchant_id, get_db())


@router.get("/menu/status/{merchant_id}")
async def get_menu_status(merchant_id: str, principal=Depends(require_service_auth)):
    """Menu-build progress for the customer account UI.

    state:
      building → a sync is in flight in this worker
      ready    → menu_items already stored
      error    → config row carries a menu_sync_error (best-effort; reserved)
      idle     → nothing stored and nothing in flight
    """
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    db = get_db()

    rows = await db.select(
        "phone_agent_config",
        filters={"merchant_id": f"eq.{merchant_id}"},
        limit=1,
    )
    row = rows[0] if rows else {}
    items = row.get("menu_items") or []
    item_count = len(items) if isinstance(items, list) else 0
    sample = [
        (it.get("name") or "").strip()
        for it in (items if isinstance(items, list) else [])[:5]
        if isinstance(it, dict) and (it.get("name") or "").strip()
    ]

    building = merchant_id in _MENU_BUILDING
    if building:
        state = "building"
    elif row.get("menu_sync_error"):
        state = "error"
    elif item_count > 0:
        state = "ready"
    else:
        state = "idle"

    return {
        "state": state,
        "item_count": item_count,
        "updated_at": row.get("updated_at"),
        "sample": sample,
    }


# Max upload accepted for a menu photo (vision models cap input size anyway).
_MAX_MENU_PHOTO_BYTES = 12 * 1024 * 1024  # 12 MB


@router.post("/menu/scan-photo/{merchant_id}")
async def scan_menu_photo(
    merchant_id: str,
    photo: UploadFile = File(...),
    replace: bool = Query(False),
    principal=Depends(require_service_auth),
):
    """Supplementary menu builder: digitize a photo of a paper/printed menu.

    The image is sent to a vision model, parsed into the agent's
    ``{name, price?, category?}`` shape, and **merged onto** the merchant's
    existing ``menu_items`` (POS-synced or hand-entered) so the phone agent
    picks the new items up. Pass ``?replace=true`` to overwrite instead of
    merge (e.g. a full reprint). The image itself is never stored.
    """
    from ...services.menu_vision import (
        MenuVisionError,
        extract_menu_from_image,
        merge_menu_items,
    )

    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)

    image_bytes = await photo.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(image_bytes) > _MAX_MENU_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="image too large (max 12 MB)")

    try:
        scanned = await extract_menu_from_image(image_bytes, photo.content_type or "")
    except MenuVisionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not scanned:
        return {
            "scanned": True,
            "added": 0,
            "item_count": 0,
            "reason": "no menu items detected in the image",
        }

    db = get_db()
    config_rows = await db.select(
        "phone_agent_config",
        filters={"merchant_id": f"eq.{merchant_id}"},
        limit=1,
    )
    existing = (config_rows[0].get("menu_items") if config_rows else None) or []
    if replace:
        menu, added = scanned, len(scanned)
    else:
        before = len(existing) if isinstance(existing, list) else 0
        menu = merge_menu_items(existing, scanned)
        added = len(menu) - before

    payload = {"menu_items": menu, "updated_at": datetime.now(timezone.utc).isoformat()}
    if config_rows:
        await db.update(
            "phone_agent_config",
            payload,
            filters={"merchant_id": f"eq.{merchant_id}"},
        )
    else:
        await db.insert("phone_agent_config", {"merchant_id": merchant_id, **payload})

    logger.info(
        "Scanned %d menu items from photo for %s (%s, +%d, total %d)",
        len(scanned), merchant_id, "replace" if replace else "merge", added, len(menu),
    )
    return {
        "scanned": True,
        "added": added,
        "scanned_count": len(scanned),
        "item_count": len(menu),
        "mode": "replace" if replace else "merge",
        "sample": scanned[:5],
    }


@router.get("/calls/{merchant_id}")
async def get_phone_calls(
    merchant_id: str,
    principal=Depends(require_service_auth),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return call logs for a merchant, newest first."""
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    db = get_db()

    calls = await db.select(
        "phone_call_logs",
        filters={"merchant_id": f"eq.{merchant_id}"},
        order="created_at.desc",
        limit=limit,
        offset=offset,
    )

    return {"merchant_id": merchant_id, "calls": calls, "count": len(calls)}


@router.get("/orders/{merchant_id}")
async def get_phone_orders(
    merchant_id: str,
    principal=Depends(require_service_auth),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return phone orders for a merchant, newest first."""
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    db = get_db()

    orders = await db.select(
        "phone_orders",
        filters={"merchant_id": f"eq.{merchant_id}"},
        order="created_at.desc",
        limit=limit,
        offset=offset,
    )

    return {"merchant_id": merchant_id, "orders": orders, "count": len(orders)}


@router.get("/stats/{merchant_id}")
async def get_phone_stats(
    merchant_id: str,
    principal=Depends(require_service_auth),
    days: int = Query(7, ge=1, le=90),
):
    """Return aggregated phone stats for a merchant over N days."""
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    db = get_db()

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    calls = await db.select(
        "phone_call_logs",
        filters={
            "merchant_id": f"eq.{merchant_id}",
            "created_at": f"gte.{since}",
        },
        order="created_at.desc",
        limit=5000,
    )

    orders = await db.select(
        "phone_orders",
        filters={
            "merchant_id": f"eq.{merchant_id}",
            "created_at": f"gte.{since}",
        },
        order="created_at.desc",
        limit=5000,
    )

    total_calls = len(calls)
    order_calls = sum(1 for c in calls if c.get("status") == "order_placed")
    total_orders = len(orders)
    total_revenue = sum(float(o.get("total", 0)) for o in orders)
    avg_duration = 0
    durations = [c.get("duration_seconds", 0) for c in calls if c.get("duration_seconds")]
    if durations:
        avg_duration = round(sum(durations) / len(durations))

    return {
        "merchant_id": merchant_id,
        "days": days,
        "total_calls": total_calls,
        "order_calls": order_calls,
        "conversion_rate": round(order_calls / total_calls * 100, 1) if total_calls else 0,
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "avg_duration_seconds": avg_duration,
    }


class TestChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class TestChatRequest(BaseModel):
    merchant_id: str
    messages: list[TestChatMessage]
    business_name: str | None = None
    greeting: str | None = None
    menu_items: list | None = None
    order_types: list | None = None


def _build_test_prompt(req: TestChatRequest) -> str:
    """System prompt scoped to the merchant's own menu/greeting so the in-app
    test call behaves like the live agent for this specific business."""
    name = (req.business_name or "this restaurant").strip()
    lines = []
    for item in req.menu_items or []:
        try:
            price = float(item.get("price", 0))
        except (TypeError, ValueError):
            price = 0.0
        nm = (item.get("name") or "").strip()
        if not nm:
            continue
        cat = item.get("category")
        line = f" - {nm}: ${price:.2f}"
        if cat:
            line += f" ({cat})"
        lines.append(line)
    menu_text = "\n".join(lines) if lines else " (menu not configured yet — take the order generally)"
    order_types = ", ".join(req.order_types or ["pickup", "delivery"])
    greeting = (req.greeting or "").strip()
    greeting_line = f'\nOpen with a greeting like: "{greeting}"' if greeting else ""
    return (
        f"You are a friendly AI phone ordering assistant for {name}. "
        "Keep responses SHORT — 1-2 sentences. Sound warm and natural, not robotic. "
        f"This is a phone call.{greeting_line}\n\n"
        f"MENU:\n{menu_text}\n\n"
        f"Available order types: {order_types}.\n\n"
        "RULES:\n"
        "- Help the customer build their order item by item.\n"
        "- When done, read back the order with total price and ask for their name.\n"
        "- For items not on the menu, let them know politely.\n"
        "- Keep it brief — phone conversations should be quick."
    )


@router.post("/test-chat")
async def phone_test_chat(req: TestChatRequest, principal=Depends(require_service_auth)):
    """Interactive in-app test call. Runs the real agent brain (SambaNova →
    Qwen fallback) against the merchant's own menu so the wizard's test call
    responds to live speech instead of replaying a canned script."""
    await enforce_service_member(principal, req.merchant_id)
    _validate_merchant_id(req.merchant_id)

    # Reuse the production agent brain + parser from the Twilio route module.
    from .phone import _ask_ai, _parse

    convo = [{"role": m.role, "content": m.content} for m in req.messages if m.content.strip()]
    if not convo:
        raise HTTPException(400, "messages cannot be empty")

    result = await _ask_ai(convo, _build_test_prompt(req))
    reply, tool = _parse(result)
    ended = bool(tool and tool.get("name") in ("end_call", "submit_order"))
    order = tool.get("input") if (tool and tool.get("name") == "submit_order") else None

    if not reply:
        reply = "Sorry, could you say that again?"

    return {"reply": reply, "ended": ended, "order": order}


# ---------------------------------------------------------------------------
# Per-restaurant personalization brief
#
# Generates (or regenerates) a ≤120-word plain-prose brief for the merchant's
# phone agent by fetching their website + menu and summarising with the LLM
# gateway. The result is stored in phone_agent_config.restaurant_brief and read
# at call time by both the Pipecat streaming path (bot.py) and the turn-based
# Twilio/Telnyx path (phone.py).
#
# This is OPT-IN / manual: nothing runs automatically; the brief is generated
# once on demand and then just sits in the row. No new hard dependency — calls
# work fine when restaurant_brief is empty (prompt is unchanged).
# ---------------------------------------------------------------------------

class BuildBriefRequest(BaseModel):
    """Optional body for POST /api/phone/build-brief/{merchant_id}.

    website_url: if provided, sets / updates phone_agent_config.website_url
                 before generating. If omitted, the stored website_url is used.
    """
    website_url: str | None = None


@router.post("/build-brief/{merchant_id}")
async def build_restaurant_brief(
    merchant_id: str,
    req: BuildBriefRequest | None = None,
    principal=Depends(require_service_auth),
):
    """Generate and persist a personalization brief for the phone agent.

    Fetches the merchant's website + menu via the LLM gateway and stores the
    result in phone_agent_config.restaurant_brief / brief_updated_at.

    An optional JSON body ``{"website_url": "https://..."}`` sets or updates the
    stored website URL in the same request.

    Returns:
        ok, merchant_id, brief (the text), brief_length_words, website_url,
        generated_at (ISO timestamp).
    """
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    db = get_db()

    rows = await db.select(
        "phone_agent_config",
        filters={"merchant_id": f"eq.{merchant_id}"},
        limit=1,
    )
    if not rows:
        raise HTTPException(404, "No phone config found for this merchant — save a config first")

    row = rows[0]

    # Lazy import: the brief builder lives in services/phone_agent so we add
    # that directory to sys.path the same way phone.py does.
    import sys
    from pathlib import Path
    _phone_agent_dir = str(Path(__file__).resolve().parents[3] / "services" / "phone_agent")
    if _phone_agent_dir not in sys.path:
        sys.path.insert(0, _phone_agent_dir)
    from restaurant_brief import build_brief  # type: ignore[import]

    body = req or BuildBriefRequest()
    new_website_url = (body.website_url or "").strip()
    stored_website_url = (row.get("website_url") or "").strip()
    website_url = new_website_url or stored_website_url

    # Persist a new website_url if the caller supplied one that differs.
    if new_website_url and new_website_url != stored_website_url:
        await db.update(
            "phone_agent_config",
            {
                "website_url": new_website_url,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            filters={"merchant_id": f"eq.{merchant_id}"},
        )

    business_name = (row.get("business_name") or "this restaurant").strip()
    menu_items = row.get("menu_items") or []

    brief = await build_brief(business_name, website_url, menu_items)

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.update(
        "phone_agent_config",
        {
            "restaurant_brief": brief,
            "brief_updated_at": now_iso,
            "updated_at": now_iso,
        },
        filters={"merchant_id": f"eq.{merchant_id}"},
    )

    word_count = len(brief.split()) if brief else 0
    logger.info(
        "build_restaurant_brief: stored %d-word brief for merchant %s (website=%s)",
        word_count, merchant_id, bool(website_url),
    )
    return {
        "ok": True,
        "merchant_id": merchant_id,
        "brief": brief,
        "brief_length_words": word_count,
        "website_url": website_url,
        "generated_at": now_iso,
    }


# ---------------------------------------------------------------------------
# Number provisioning — buys a dedicated number per merchant and wires its
# voice webhook so inbound calls resolve to this business.
#
# Provider is selected by PHONE_PROVIDER (default "twilio"). Telnyx is the
# preferred provider (cheaper, and SMS already runs on it); a Telnyx number is
# attached to the TELNYX_VOICE_CONNECTION_ID app, whose voice webhook points at
# our backend, so inbound calls route through the same agent.
# ---------------------------------------------------------------------------

PHONE_PROVIDER = os.getenv("PHONE_PROVIDER", "twilio").lower()

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_API = "https://api.twilio.com/2010-04-01"

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY", "")
TELNYX_API = "https://api.telnyx.com/v2"
TELNYX_VOICE_CONNECTION_ID = os.getenv("TELNYX_VOICE_CONNECTION_ID", "")
TELNYX_MESSAGING_PROFILE_ID = os.getenv("TELNYX_MESSAGING_PROFILE_ID", "")


def _webhook_base() -> str:
    host = os.getenv("MEDIA_STREAM_HOST", "api.meridian.tips")
    return f"https://{host}"


class ProvisionNumberRequest(BaseModel):
    merchant_id: str
    country: str = "CA"
    area_code: str | None = None
    business_name: str | None = None


# --- Twilio provider ---

async def _twilio_search(country: str, area_code: str | None) -> str | None:
    """Return one available voice+SMS local number for the country, or None."""
    params: dict[str, str] = {"VoiceEnabled": "true", "SmsEnabled": "true", "Limit": "5"}
    if area_code:
        params["AreaCode"] = area_code
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.get(
            f"{TWILIO_API}/Accounts/{TWILIO_SID}/AvailablePhoneNumbers/{country}/Local.json",
            params=params,
            auth=(TWILIO_SID, TWILIO_TOKEN),
        )
        if res.status_code != 200:
            logger.error("Twilio number search %d: %s", res.status_code, res.text[:300])
            return None
        nums = res.json().get("available_phone_numbers", [])
        return nums[0]["phone_number"] if nums else None


async def _twilio_purchase(phone_number: str, friendly_name: str) -> dict:
    """Buy the number and point its voice/status webhooks at our backend."""
    base = _webhook_base()
    data = {
        "PhoneNumber": phone_number,
        "FriendlyName": friendly_name,
        "VoiceUrl": f"{base}/twilio/voice",
        "VoiceMethod": "POST",
        "StatusCallback": f"{base}/twilio/status",
        "StatusCallbackMethod": "POST",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(
            f"{TWILIO_API}/Accounts/{TWILIO_SID}/IncomingPhoneNumbers.json",
            data=data,
            auth=(TWILIO_SID, TWILIO_TOKEN),
        )
        if res.status_code not in (200, 201):
            logger.error("Twilio purchase %d: %s", res.status_code, res.text[:400])
            # Surface Twilio's own message (e.g. regulatory bundle / no funds).
            try:
                msg = res.json().get("message", res.text[:200])
            except Exception:
                msg = res.text[:200]
            raise HTTPException(502, f"Twilio could not provision a number: {msg}")
        body = res.json()
        return {"phone_number": body.get("phone_number"), "sid": body.get("sid")}


# --- Telnyx provider ---

async def _telnyx_search(country: str, area_code: str | None) -> str | None:
    """Return one available voice+SMS number for the country, or None."""
    params: list[tuple[str, str]] = [
        ("filter[country_code]", country),
        ("filter[features][]", "voice"),
        ("filter[features][]", "sms"),
        ("filter[limit]", "5"),
        ("filter[best_effort]", "true"),
    ]
    if area_code:
        params.append(("filter[national_destination_code]", area_code))
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.get(
            f"{TELNYX_API}/available_phone_numbers",
            params=params,
            headers={"Authorization": f"Bearer {TELNYX_API_KEY}"},
        )
        if res.status_code != 200:
            logger.error("Telnyx number search %d: %s", res.status_code, res.text[:300])
            return None
        nums = res.json().get("data", [])
        return nums[0]["phone_number"] if nums else None


async def _telnyx_purchase(phone_number: str) -> dict:
    """Order the number and attach it to our voice connection + messaging
    profile. The connection's voice webhook (set once on the TeXML/Call-Control
    app) routes inbound calls to our backend."""
    body: dict = {"phone_numbers": [{"phone_number": phone_number}]}
    if TELNYX_VOICE_CONNECTION_ID:
        body["connection_id"] = TELNYX_VOICE_CONNECTION_ID
    if TELNYX_MESSAGING_PROFILE_ID:
        body["messaging_profile_id"] = TELNYX_MESSAGING_PROFILE_ID
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(
            f"{TELNYX_API}/number_orders",
            json=body,
            headers={"Authorization": f"Bearer {TELNYX_API_KEY}", "Content-Type": "application/json"},
        )
        if res.status_code not in (200, 201):
            logger.error("Telnyx order %d: %s", res.status_code, res.text[:400])
            # Surface Telnyx's own error (e.g. no funds / regulatory requirement).
            try:
                errs = res.json().get("errors", [])
                msg = errs[0].get("detail") if errs else res.text[:200]
            except Exception:
                msg = res.text[:200]
            raise HTTPException(502, f"Telnyx could not provision a number: {msg}")
        data = res.json().get("data", {})
        order_id = data.get("id")
        nums = data.get("phone_numbers", [])
        bought = nums[0].get("phone_number") if nums else phone_number
        return {"phone_number": bought, "sid": order_id}


@router.post("/provision-number")
async def provision_number(req: ProvisionNumberRequest, principal=Depends(require_service_auth)):
    """Provision a dedicated phone number for a merchant. Idempotent: if the
    merchant already has a number it is returned unchanged (never double-buys).
    Provider is chosen by PHONE_PROVIDER (telnyx | twilio)."""
    await enforce_service_member(principal, req.merchant_id)
    _validate_merchant_id(req.merchant_id)

    if PHONE_PROVIDER == "telnyx":
        if not TELNYX_API_KEY:
            raise HTTPException(503, "Telnyx is not configured")
        if not TELNYX_VOICE_CONNECTION_ID:
            raise HTTPException(503, "Telnyx voice connection is not configured (TELNYX_VOICE_CONNECTION_ID)")
    elif not TWILIO_SID or not TWILIO_TOKEN:
        raise HTTPException(503, "Twilio is not configured")

    db = get_db()
    rows = await db.select(
        "phone_agent_config",
        filters={"merchant_id": f"eq.{req.merchant_id}"},
        limit=1,
    )
    existing = rows[0].get("phone_number") if rows else None
    if existing:
        return {"phone_number": existing, "provisioned": False, "already_existed": True}

    country = (req.country or "CA").upper()
    available = await _telnyx_search(country, req.area_code) if PHONE_PROVIDER == "telnyx" \
        else await _twilio_search(country, req.area_code)
    if not available:
        raise HTTPException(404, f"No available {country} numbers found")

    if PHONE_PROVIDER == "telnyx":
        purchased = await _telnyx_purchase(available)
    else:
        purchased = await _twilio_purchase(available, req.business_name or f"Meridian {req.merchant_id[:8]}")
    number = purchased["phone_number"]

    payload = {"phone_number": number, "updated_at": datetime.now(timezone.utc).isoformat()}
    if rows:
        await db.update("phone_agent_config", payload, filters={"merchant_id": f"eq.{req.merchant_id}"})
    else:
        payload["merchant_id"] = req.merchant_id
        await db.insert("phone_agent_config", payload)
    logger.info("Provisioned %s for merchant %s via %s", number, req.merchant_id, PHONE_PROVIDER)

    return {"phone_number": number, "provisioned": True, "already_existed": False, "provider": PHONE_PROVIDER}
