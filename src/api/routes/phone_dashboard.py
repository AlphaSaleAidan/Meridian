"""
Phone Agent Dashboard API routes.

Endpoints for the frontend phone orders page:
  GET    /api/phone/config/{merchant_id}   → Get phone agent config
  POST   /api/phone/config                 → Save/update phone agent config
  GET    /api/phone/calls/{merchant_id}    → List call logs
  GET    /api/phone/orders/{merchant_id}   → List phone orders
  GET    /api/phone/stats/{merchant_id}    → Aggregated stats
"""

import asyncio
import logging
import os
import re
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, field_validator

from ..auth import enforce_service_member, require_admin_auth, require_service_auth
from ...db import get_db
from ...services.vapi_provisioning import (
    delete_vapi_number,
    import_telnyx_number,
    vapi_telnyx_enabled,
)

logger = logging.getLogger("meridian.api.phone_dashboard")

router = APIRouter(prefix="/api/phone", tags=["phone-dashboard"])

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I
)
# Real merchant ids are the businesses.id TEXT primary key, shaped
# `biz_<hex>` (see frontend auth.tsx / businesses table: `biz_` + 32 hex).
# Accept both a UUID and a `biz_` id, but keep a strict format guard so no
# arbitrary/injection-shaped string gets through to the DB layer.
_MERCHANT_ID_RE = re.compile(
    r'^(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    r'|biz_[0-9a-f]{16,40})$',
    re.I,
)


class PhoneConfigRequest(BaseModel):
    merchant_id: str
    business_name: str | None = None
    business_type: str | None = None
    phone_number: str | None = None
    greeting: str | None = None
    voice: str | None = None
    # 'en' (default) or 'multi' — multi turns on Deepgram multilingual
    # transcription (Hindi/Punjabi + English code-switching on one call).
    language: str | None = None
    # Accent group chosen in the wizard (north_american | indian | east_asian).
    # Presentation-level; `voice` carries the actual Vapi voice name.
    accent: str | None = None

    @field_validator("accent")
    @classmethod
    def _valid_accent(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return v
        allowed = {"north_american", "indian", "east_asian"}
        s = v.strip().lower()
        if s not in allowed:
            raise ValueError(f"accent must be one of {sorted(allowed)}")
        return s
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
    # Human warm-transfer target. Validated on save against the transfer-loop
    # scenario (transfer → store line → carrier full-forward → agent DID →
    # infinite loop): rejected with a 422 when it equals this merchant's own
    # agent DID or ANY agent DID in phone_agent_config. Stored normalized E.164.
    transfer_number: str | None = None
    # Per-merchant hard call cap (minutes). None leaves the stored value
    # untouched; 0 = uncapped; otherwise overrides the env default (8).
    max_call_minutes: int | None = None
    # The merchant's real store line (the number they forward FROM), used by
    # the forwarding verification flow. Stored normalized E.164.
    business_line_number: str | None = None

    @field_validator("max_call_minutes")
    @classmethod
    def _valid_cap(cls, v: int | None) -> int | None:
        if v is None:
            return v
        if v < 0 or v > 60:
            raise ValueError("max_call_minutes must be between 0 (uncapped) and 60")
        return v
    # How the wizard routes confirmed orders: 'pos' | 'webhook' | 'sms' | 'email'.
    # Persisted to phone_agent_config.order_routing (migration 032). Optional and
    # back-compat: omitting it leaves the stored value untouched (save_phone_config
    # only writes non-None fields).
    order_routing: str | None = None
    # Merchant-customized Text-to-Pay SMS body. Supports {name} {business}
    # {total} {link} placeholders, rendered with safe replace (never .format)
    # by sms_checkout._format_checkout_sms. Empty/unset → default copy.
    # Persisted to phone_agent_config.sms_pay_template
    # (migration 20260706_sms_pay_template).
    sms_pay_template: str | None = None
    # {on_website: bool, website_url: str} — the "Connect your reservation
    # system" questionnaire (migration 20260706_reservation_config).
    reservation_config: dict | None = None
    # Agent personality: {formality: float, upsell: 'none'|'gentle'|'active',
    # humor: bool, customGreeting, customHold, customClosing, brandKeywords[]}.
    # Persisted to phone_agent_config.personality (migration
    # 20260706_personality) and rendered into the live Vapi system prompt by
    # vapi_webhook._system_prompt.
    personality: dict | None = None
    # Call-script pack (migration 20260717_phone_script_pack). 'legacy' or
    # unset keeps the current generic prompt byte-for-byte; other values must
    # be a known pack id (services/phone_agent/script_packs.py). None leaves
    # the stored value untouched; "" / "legacy" explicitly selects legacy.
    script_pack: str | None = None
    # "Pay with Cash" opt-in (migration 047). When true, the phone agent may
    # offer cash as a payment option and cash orders reach the kitchen flagged
    # UNPAID / CASH ON PICKUP with NO payment link. None leaves the stored value
    # untouched; the setup wizard / Settings tab gate turning it ON behind an
    # explicit warning modal. NULL/false = never offer cash (current behavior).
    accept_cash: bool | None = None

    @field_validator("script_pack")
    @classmethod
    def _valid_script_pack(cls, v: str | None) -> str | None:
        if v is None:
            return v
        s = v.strip().lower()
        if s in ("", "legacy"):
            return s
        try:
            from .vapi_webhook import _PHONE_AGENT_DIR  # ensures sys.path  # noqa: F401
            from script_packs import PACK_DEFS  # type: ignore[import]
        except Exception:  # noqa: BLE001 — call-time resolution is fail-legacy anyway
            return s
        if s not in PACK_DEFS:
            raise ValueError(
                f"script_pack must be 'legacy' or one of {sorted(PACK_DEFS)}")
        return s


def _validate_merchant_id(merchant_id: str):
    if not _MERCHANT_ID_RE.match(merchant_id or ""):
        raise HTTPException(400, "Invalid merchant_id format")


@router.get("/fees")
async def get_fee_settings():
    """Live pricing dials (env-tunable, no auth — it's public pricing).

    The UI reads these instead of hardcoding amounts, so changing
    MERIDIAN_SERVICE_FEE_CENTS / MERIDIAN_VOICE_OVERAGE_CENTS_PER_MIN in
    Railway updates every displayed price with no redeploy.
    """
    import os
    return {
        "service_fee_cents": int(os.getenv("MERIDIAN_SERVICE_FEE_CENTS", "0") or 0),
        "overage_cents_per_min": int(os.getenv("MERIDIAN_VOICE_OVERAGE_CENTS_PER_MIN", "45") or 45),
        "included_minutes": int(os.getenv("MERIDIAN_VOICE_INCLUDED_MIN", "3") or 3),
        # Hard cap DEFAULT: Vapi force-ends calls at this length (0 = no cap).
        # Merchants can override per-account via phone_agent_config.max_call_minutes.
        "max_call_minutes": int(os.getenv("MERIDIAN_VOICE_MAX_CALL_MIN", "8") or 0),
    }


@router.get("/script-packs")
async def get_script_packs(principal=Depends(require_service_auth)):
    """Available call-script packs (registry metadata, no merchant data).

    Drives the wizard/settings dropdown. 'legacy' (Standard) is always first
    and is the default for every merchant — selecting anything else is
    opt-in per merchant and only recommended for packs whose status is
    'beat_baseline' (see docs/playbook 30-features/phone-orders/script-packs.md).
    """
    import sys as _sys
    from pathlib import Path as _Path
    _dir = str(_Path(__file__).resolve().parents[3] / "services" / "phone_agent")
    if _dir not in _sys.path:
        _sys.path.insert(0, _dir)
    from script_packs import list_packs  # type: ignore[import]
    return {"packs": list_packs()}


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
    # Strip every credential/secret before returning the config to a client.
    # popping only pos_access_token left clover_hco_webhook_secret (the
    # per-merchant Clover HCO signing secret) in the response — a member could
    # read it and forge PAYMENT-APPROVED events (CONFIRMED leak, 2026-07-22).
    for _k in list(row.keys()):
        if _k.endswith("_secret") or _k.endswith("_token") or _k in (
                "pos_access_token", "credentials_encrypted", "access_token_enc",
                "refresh_token_enc"):
            row.pop(_k, None)
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

    # Go-live gate: an agent cannot be "active" (answering calls) without a
    # provisioned phone number — activating without one left the merchant
    # believing they were live while no call could ever land. phone_number is
    # system-managed (only /provision-number sets it), so check the STORED
    # value. Block only this unambiguous case; an empty menu is warned, not
    # blocked (POS-synced menus can populate asynchronously).
    if req.active is True:
        stored_number = (rows[0].get("phone_number") if rows else "") or ""
        if not stored_number.strip():
            raise HTTPException(
                400,
                "Provision a phone number before activating your agent — "
                "an active agent with no number can't receive calls.",
            )
        # When Vapi is the calling platform, the DID must also be imported into
        # Vapi (vapi_phone_number_id) or an inbound call fires no assistant-
        # request and the merchant is "live" while every call fails silently.
        # Only gate when Vapi is active — a Twilio-only deployment legitimately
        # has no Vapi binding, so requiring it there would block real go-lives.
        if vapi_telnyx_enabled():
            stored_vapi = (rows[0].get("vapi_phone_number_id") if rows else "") or ""
            if not str(stored_vapi).strip():
                raise HTTPException(
                    400,
                    "Your number isn't linked to the calling platform yet — "
                    "reprovision it before activating, or inbound calls won't "
                    "reach your agent.",
                )
        stored_menu = (rows[0].get("menu_items") if rows else None) or []
        if not (req.menu_items or stored_menu):
            logger.warning("phone go-live: merchant %s activating with an empty menu",
                           req.merchant_id)

    payload = {
        k: v for k, v in req.model_dump().items()
        if v is not None and k != "merchant_id"
    }
    # phone_number is SYSTEM-MANAGED — only /provision-number assigns it (with
    # a real provider purchase + Vapi binding). Accepting it here let a merchant
    # write ANY number, including another merchant's DID, which then routes that
    # merchant's inbound calls nondeterministically (get_merchant_by_phone
    # returns the first match). Drop it from the writable payload; the value is
    # still read below for the transfer-loop own-DID check only.
    payload.pop("phone_number", None)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Transfer-loop guard (onboarding layer): reject a transfer number that is
    # this merchant's own agent DID or any agent DID in the fleet — either
    # would bounce "transfer to a human" straight back to an AI agent.
    if (req.transfer_number or "").strip():
        from ...services.phone_safety import normalize_e164, transfer_number_conflict
        own_did = (
            req.phone_number
            or (rows[0].get("phone_number") if rows else "")
            or ""
        )
        conflict = await transfer_number_conflict(db, req.transfer_number, own_did)
        if conflict:
            raise HTTPException(status_code=422, detail=conflict)
        payload["transfer_number"] = normalize_e164(req.transfer_number)
    if (req.business_line_number or "").strip():
        from ...services.phone_safety import normalize_e164
        payload["business_line_number"] = normalize_e164(req.business_line_number)

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

    # WRITE-THROUGH (menu store): once a merchant's menu lives in menu_items,
    # a wizard/settings save that carries the full menu list must update the
    # store too — otherwise the next store mutation's JSONB mirror would
    # clobber this save. No store rows → no-op (legacy JSONB-only world).
    # Best-effort: a missing table (migration not applied) never breaks saves.
    if req.menu_items is not None:
        try:
            from ...services.menu_store import replace_menu_from_agent_items
            if await replace_menu_from_agent_items(db, req.merchant_id, req.menu_items):
                logger.info("menu store write-through on config save for %s", req.merchant_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("menu store write-through failed for %s: %s", req.merchant_id, e)

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


async def _fresh_connection_token(conn: dict) -> str:
    """Access token for a pos_connections row, refreshed inline when it expires.

    Clover v2/OAuth (the 1-click connect path) issues ~30-minute access tokens
    plus a refresh token; a row carrying refresh_token_enc is routed through
    ensure_fresh_clover_token, which refreshes at/near expiry and persists
    the rotation. Every other shape — Square, manual tokens, legacy Clover —
    falls through to the stored token unchanged, so this is a strict superset
    of _decrypt_connection_token for order/menu-time resolution.
    """
    provider = (conn.get("provider") or "").strip().lower()
    if provider == "clover" and conn.get("refresh_token_enc"):
        try:
            from ...clover.oauth import ensure_fresh_clover_token

            token = (await ensure_fresh_clover_token(conn) or "").strip()
            if token:
                return token
        except Exception:  # noqa: BLE001 — refresh must never take down order dispatch
            logger.warning(
                "clover inline token refresh failed for connection %s — using stored token",
                conn.get("id"),
            )
    return _decrypt_connection_token(conn)


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
            from ...db.org_ids import connection_org_id
            conns = await db.select(
                "pos_connections",
                # biz_ ids map to the companion UUID the callback stores under
                filters={"org_id": f"eq.{connection_org_id(merchant_id) or merchant_id}",
                         "status": "eq.connected"},
                order="updated_at.desc",
                limit=1,
            )
            if conns:
                conn = conns[0]
                system = system or (conn.get("provider") or "").strip()
                external_merchant_id = (conn.get("external_merchant_id") or "").strip()
                token = token or await _fresh_connection_token(conn)
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
            max_items=300,
        )
        if not items:
            return {
                "synced": False,
                "reason": "POS returned no catalog items (empty menu or auth failed)",
                "item_count": 0,
                "source": source,
            }

        # MENU STORE write-through: POS imports are trusted (source='pos',
        # published immediately) but items with no price land in the review
        # queue. ingest_items keeps the phone_agent_config.menu_items JSONB
        # mirror in sync, so the legacy write below only runs when the store
        # is unavailable (migration not applied yet).
        needs_review = 0
        stored = False
        try:
            from ...services.menu_store import ingest_items
            summary = await ingest_items(db, merchant_id, items, source="pos")
            needs_review = summary["needs_review"]
            stored = True
        except Exception as e:  # noqa: BLE001 — store unavailable → legacy path
            logger.warning("menu store unavailable for %s — JSONB-only sync: %s",
                           merchant_id, e)
        if not stored:
            legacy_items = [
                {k: v for k, v in it.items() if k != "source_external_id"}
                for it in items
            ]
            payload = {"menu_items": legacy_items,
                       "updated_at": datetime.now(timezone.utc).isoformat()}
            if config_rows:
                await db.update(
                    "phone_agent_config",
                    payload,
                    filters={"merchant_id": f"eq.{merchant_id}"},
                )
            else:
                await db.insert("phone_agent_config", {"merchant_id": merchant_id, **payload})

        logger.info("Synced %d menu items from %s (%s) for %s (store=%s, review=%d)",
                    len(items), system, source, merchant_id, stored, needs_review)
        return {"synced": True, "item_count": len(items), "needs_review": needs_review,
                "source": source, "sample": items[:5]}
    finally:
        _MENU_BUILDING.discard(merchant_id)


async def auto_build_menu_on_connect(merchant_id: str) -> None:
    """Best-effort auto-trigger fired after a POS connection becomes active.

    Reuses the exact extraction path the manual endpoint uses. Never raises — a
    menu-build failure must not break the POS connect response. Skips merchants
    whose id isn't a valid merchant id (the menu_items shape keys off the
    org/merchant id — accepts both UUIDs and `biz_` ids).
    """
    if not _MERCHANT_ID_RE.match(merchant_id or ""):
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


async def _persist_scanned_items(db, merchant_id: str, scanned: list[dict],
                                 source: str, replace: bool) -> dict:
    """Shared persistence for the legacy photo/CSV menu builders.

    Store-first: items land in menu_items behind the review gate (source=
    photo|csv, published=false + needs_review=true — never silently live;
    `replace` is moot there). Pre-migration fallback: the original JSONB
    merge (or replace) so nothing breaks before the table exists.
    """
    try:
        from ...services.menu_store import ingest_items
        summary = await ingest_items(db, merchant_id, scanned, source=source)
        return {
            "scanned": True,
            "added": summary["inserted"] + summary["updated"],
            "scanned_count": len(scanned),
            "pending_review": summary["needs_review"],
            "skipped_existing": summary["skipped_existing"],
            "item_count": len(scanned),
            "mode": "review",
            "sample": scanned[:5],
        }
    except Exception as e:  # noqa: BLE001 — store unavailable → legacy path
        logger.warning("menu store unavailable for %s — legacy JSONB merge: %s",
                       merchant_id, e)

    from ...services.menu_vision import merge_menu_items

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

    return {
        "scanned": True,
        "added": added,
        "scanned_count": len(scanned),
        "item_count": len(menu),
        "mode": "replace" if replace else "merge",
        "sample": scanned[:5],
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
    from ...services.menu_vision import MenuVisionError, extract_menu_from_image

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
    # MENU STORE: scanned items land behind the review gate (source='photo',
    # never silently live) — `replace` is ignored on this path since nothing
    # goes live until the merchant confirms. Legacy JSONB merge only when the
    # store is unavailable (migration not applied yet).
    result = await _persist_scanned_items(db, merchant_id, scanned, "photo", replace)
    logger.info(
        "Scanned %d menu items from photo for %s (%s)",
        len(scanned), merchant_id, result.get("mode"),
    )
    return result


# Max upload accepted for a menu CSV (spreadsheet exports are tiny).
_MAX_MENU_CSV_BYTES = 1 * 1024 * 1024  # 1 MB
_MAX_MENU_CSV_ROWS = 1000

# Header aliases recognized in a menu CSV (case-insensitive).
_CSV_NAME_KEYS = {"name", "item", "item name", "title", "product"}
_CSV_PRICE_KEYS = {"price", "cost", "amount", "unit price"}
_CSV_CATEGORY_KEYS = {"category", "section", "group", "type"}


def _parse_menu_csv(text: str) -> list[dict]:
    """Parse CSV text into the menu_items shape: [{name, price?, category?}].

    Header-flexible: a first row containing a recognizable name column (and
    optionally price/category, in any order) is used as the header; otherwise
    rows are read positionally as ``name,price[,category]``. Currency symbols
    in prices are tolerated ("$9.99", "CA$ 12"). Rows without a name are
    skipped.
    """
    import csv
    import io

    rows = [r for r in csv.reader(io.StringIO(text)) if any((c or "").strip() for c in r)]
    if not rows:
        return []
    if len(rows) > _MAX_MENU_CSV_ROWS:
        raise HTTPException(status_code=413, detail=f"too many rows (max {_MAX_MENU_CSV_ROWS})")

    def _norm(cell: str) -> str:
        return (cell or "").strip().lower()

    header = [_norm(c) for c in rows[0]]
    name_col = next((i for i, c in enumerate(header) if c in _CSV_NAME_KEYS), None)
    if name_col is not None:
        price_col = next((i for i, c in enumerate(header) if c in _CSV_PRICE_KEYS), None)
        category_col = next((i for i, c in enumerate(header) if c in _CSV_CATEGORY_KEYS), None)
        data_rows = rows[1:]
    else:
        # No recognizable header → positional name,price[,category].
        name_col, price_col, category_col = 0, 1, 2
        data_rows = rows

    def _cell(row: list, idx: int | None) -> str:
        if idx is None or idx >= len(row):
            return ""
        return (row[idx] or "").strip()

    items: list[dict] = []
    for row in data_rows:
        name = _cell(row, name_col)
        if not name:
            continue
        item: dict = {"name": name}
        raw_price = _cell(row, price_col)
        if raw_price:
            cleaned = re.sub(r"[^\d.\-]", "", raw_price)
            try:
                item["price"] = round(float(cleaned), 2)
            except ValueError:
                pass  # unparseable price — keep the item, priceless
        category = _cell(row, category_col)
        if category:
            item["category"] = category
        items.append(item)
    return items


@router.post("/menu/import-csv/{merchant_id}")
async def import_menu_csv(
    merchant_id: str,
    request: Request,
    replace: bool = Query(False),
    principal=Depends(require_service_auth),
):
    """Supplementary menu builder: import a ``name,price,category`` CSV.

    Accepts either a raw ``text/csv`` body or a multipart upload (field name
    ``file``). Rows are parsed into the agent's ``{name, price?, category?}``
    shape and **merged onto** the merchant's existing ``menu_items`` — same
    persistence as the photo scanner. Pass ``?replace=true`` to overwrite.
    """
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)

    content_type = (request.headers.get("content-type") or "").lower()
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file") or form.get("csv") or form.get("photo")
        if upload is None or isinstance(upload, str):
            raise HTTPException(status_code=400, detail="missing CSV file (multipart field 'file')")
        raw = await upload.read()
    else:
        raw = await request.body()

    if not raw:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(raw) > _MAX_MENU_CSV_BYTES:
        raise HTTPException(status_code=413, detail="CSV too large (max 1 MB)")

    try:
        text = raw.decode("utf-8-sig")  # tolerate Excel's BOM
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=422, detail="could not decode CSV text") from exc

    parsed = _parse_menu_csv(text)
    if not parsed:
        return {
            "scanned": True,
            "added": 0,
            "item_count": 0,
            "reason": "no menu items found in the CSV",
        }

    db = get_db()
    result = await _persist_scanned_items(db, merchant_id, parsed, "csv", replace)
    logger.info(
        "Imported %d menu items from CSV for %s (%s)",
        len(parsed), merchant_id, result.get("mode"),
    )
    return result


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

    total_calls = len(calls)
    # Orders + revenue derive from phone_call_logs — the superset both the
    # turn-based AND streaming paths write (one row per call). phone_orders is a
    # streaming-only subset, so reading it undercounted turn-based merchants to
    # 0 orders / $0 revenue. order_data.total is populated by both paths
    # (turn-based via the #378 menu pricer, streaming via normalize_order).
    order_statuses = {"order_placed", "order_placed_awaiting_card", "order_paid_card"}
    order_logs = [c for c in calls if c.get("status") in order_statuses]
    order_calls = len(order_logs)
    total_orders = order_calls
    total_revenue = sum(
        float((c.get("order_data") or {}).get("total", 0) or 0) for c in order_logs
    )
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
    # Same shape as phone_agent_config.personality — passed through so the
    # in-app test call behaves like the live Vapi agent (which renders it via
    # vapi_webhook._personality_style_lines / _upsell_step).
    personality: dict | None = None


def _build_test_prompt(req: TestChatRequest) -> str:
    """System prompt scoped to the merchant's own menu/greeting so the in-app
    test call behaves like the live agent for this specific business."""
    # Reuse the live-call personality renderers so test calls and real Vapi
    # calls express the panel settings identically. Unset personality → the
    # prompt stays byte-for-byte what it was before this field existed.
    from .vapi_webhook import _personality_style_lines, _upsell_step

    p = req.personality if isinstance(req.personality, dict) else {}
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
    # customGreeting (personality) overrides the standard greeting when set —
    # mirrors vapi_webhook._effective_greeting.
    greeting = (str(p.get("customGreeting") or "").strip() or (req.greeting or "")).strip()
    greeting_line = f'\nOpen with a greeting like: "{greeting}"' if greeting else ""
    style_lines = _personality_style_lines(p)
    style_block = ("\n".join(style_lines) + "\n") if style_lines else ""
    upsell = str(p.get("upsell") or "").strip().lower()
    upsell_line = ""
    if upsell in ("none", "gentle", "active"):
        # _upsell_step returns the numbered live-call step; reduce to a rule line.
        upsell_line = "- " + _upsell_step(p).split(". ", 1)[1].strip() + "\n"
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
        f"{upsell_line}{style_block}"
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

# Number provisioning is Telnyx-only. (Twilio is still used elsewhere for SMS
# and the forwarding-verification call — see sms/client.py, phone_activation.py
# — but numbers are never bought at Twilio.)
PHONE_PROVIDER = "telnyx"

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY", "")
TELNYX_API = "https://api.telnyx.com/v2"
TELNYX_VOICE_CONNECTION_ID = os.getenv("TELNYX_VOICE_CONNECTION_ID", "")
TELNYX_MESSAGING_PROFILE_ID = os.getenv("TELNYX_MESSAGING_PROFILE_ID", "")


class ProvisionNumberRequest(BaseModel):
    merchant_id: str
    country: str = "CA"
    area_code: str | None = None
    business_name: str | None = None
    # Swap: release the merchant's current number at the provider (best-effort)
    # and purchase a fresh one. Without force, provisioning stays idempotent.
    force: bool = False


# --- Telnyx provider (the only number-buying provider — no Twilio) ---

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


# --- Number release (swap support) ---

async def _telnyx_release(phone_number: str, sid: str | None) -> bool:
    """Release a purchased Telnyx number. The sid we store at purchase time is
    the number ORDER id, so resolve the phone-number resource id by number
    first, falling back to DELETE with the stored sid. Best-effort: failures
    are logged, never raised."""
    try:
        headers = {"Authorization": f"Bearer {TELNYX_API_KEY}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            number_id: str | None = None
            res = await client.get(
                f"{TELNYX_API}/phone_numbers",
                params={"filter[phone_number]": phone_number},
                headers=headers,
            )
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data:
                    number_id = data[0].get("id")
            target = number_id or sid
            if not target:
                logger.error("Telnyx release: no id resolvable for %s", phone_number)
                return False
            res = await client.delete(f"{TELNYX_API}/phone_numbers/{target}", headers=headers)
        if res.status_code in (200, 204):
            return True
        logger.error(
            "Telnyx number release %s (%s) failed %d: %s",
            phone_number, target, res.status_code, res.text[:300],
        )
    except Exception as exc:  # noqa: BLE001 — best-effort release
        logger.error("Telnyx number release %s failed: %s", phone_number, exc)
    return False


# Same-worker double-provision guard (double-click / double-submit / wizard
# retry): serialize provisioning per merchant so the read-then-buy section
# can't interleave. Cross-worker/instance races are caught by the atomic
# store in _store_provisioned_number_atomic. The dict is bounded by the
# number of merchants that ever provision in this process's lifetime.
_provision_locks: dict[str, asyncio.Lock] = {}


def _provision_lock(merchant_id: str) -> asyncio.Lock:
    return _provision_locks.setdefault(merchant_id, asyncio.Lock())


@router.post("/provision-number")
async def provision_number(req: ProvisionNumberRequest, principal=Depends(require_service_auth)):
    """Provision a dedicated phone number for a merchant. Idempotent: if the
    merchant already has a number it is returned unchanged (never double-buys).
    Concurrent calls for the same merchant are serialized in-process and any
    cross-instance race loses at the DB write (the loser's number is returned
    to the pool / released, never leaked). With ``force=true`` the current
    number is released at the provider (best-effort) and a fresh one is
    purchased — the swap path."""
    await enforce_service_member(principal, req.merchant_id)
    _validate_merchant_id(req.merchant_id)

    # All-Telnyx: numbers are bought at Telnyx and bound to Vapi (no Twilio).
    if not TELNYX_API_KEY:
        raise HTTPException(503, "Telnyx is not configured")

    async with _provision_lock(req.merchant_id):
        return await _provision_number_locked(req)


async def _provision_number_locked(req: ProvisionNumberRequest):
    db = get_db()
    rows = await db.select(
        "phone_agent_config",
        filters={"merchant_id": f"eq.{req.merchant_id}"},
        limit=1,
    )
    existing = rows[0].get("phone_number") if rows else None
    existing_sid = rows[0].get("phone_number_sid") if rows else None
    existing_vapi_id = rows[0].get("vapi_phone_number_id") if rows else None
    if existing and not req.force:
        return {"phone_number": existing, "provisioned": False, "already_existed": True}

    if existing and req.force:
        # Swap: release the old number at Telnyx + Vapi first. Best-effort — a
        # failed release (already released, legacy row without a sid, provider
        # hiccup) is logged but never blocks buying the replacement.
        if existing_vapi_id:
            await delete_vapi_number(existing_vapi_id)
        released = await _telnyx_release(existing, existing_sid)
        if not released:
            logger.warning(
                "Swap for %s: could not release %s at Telnyx (continuing with purchase)",
                req.merchant_id, existing,
            )

    # ── Pool-first: hand out a pre-bought, Vapi-bound number instantly ──
    # buy_into_pool already did the Telnyx purchase + Vapi import ahead of time,
    # so a claim is one DB update with zero external latency and no
    # purchase-failure surface at signup. Falls through to a live buy only when
    # the pool is dry.
    from ...services.number_pool import claim_from_pool
    claimed = await claim_from_pool(db, req.merchant_id)
    # Fresh provisions (everything except an explicit swap of an existing
    # number) must only land on a row that is still unassigned — a concurrent
    # provision that got there first wins, and ours unwinds instead of
    # overwriting (which would leak the winner's DID as a paid orphan).
    require_unassigned = not (req.force and existing)
    if claimed:
        number = claimed["phone_number"]
        vapi_id = claimed.get("vapi_phone_number_id")
        stored = await _store_provisioned_number_atomic(db, req.merchant_id, bool(rows), {
            "phone_number": number,
            "phone_number_sid": claimed.get("provider_sid"),
            "vapi_phone_number_id": vapi_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, require_unassigned=require_unassigned)
        if not stored:
            return await _lost_race_response(
                db, req.merchant_id, number, claimed.get("provider_sid"),
                vapi_id, from_pool=True,
            )
        logger.info("Provisioned %s for merchant %s from POOL", number, req.merchant_id)
        return {"phone_number": number, "provisioned": True, "already_existed": False,
                "provider": "telnyx", "vapi_bound": bool(vapi_id), "from_pool": True}

    # ── Pool empty → live buy at Telnyx + bind to Vapi ──
    country = (req.country or "CA").upper()
    available = await _telnyx_search(country, req.area_code)
    if not available:
        raise HTTPException(404, f"No available {country} numbers found")
    purchased = await _telnyx_purchase(available)
    number = purchased["phone_number"]

    # A bought DID is inert until Vapi owns it: only then does an inbound call
    # fire assistant-request → vapi_webhook resolves the merchant and answers,
    # and only then can forwarding verification pass. On import failure, release
    # the Telnyx number and fail loud — never hand a merchant a dead line.
    vapi_id = None
    if vapi_telnyx_enabled():
        vapi_id = await import_telnyx_number(
            number, name=req.business_name or f"Meridian {req.merchant_id[:8]}",
        )
        if not vapi_id:
            await _telnyx_release(number, purchased.get("sid"))
            raise HTTPException(
                502,
                "Provisioned the number but could not bind it to the calling "
                "platform — released it and did not charge you a dead line. "
                "Please retry.",
            )

    stored = await _store_provisioned_number_atomic(db, req.merchant_id, bool(rows), {
        "phone_number": number,
        "phone_number_sid": purchased.get("sid"),
        "vapi_phone_number_id": vapi_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, require_unassigned=require_unassigned)
    if not stored:
        return await _lost_race_response(
            db, req.merchant_id, number, purchased.get("sid"), vapi_id,
            from_pool=False,
        )
    logger.info("Provisioned %s for merchant %s via Telnyx%s%s",
                number, req.merchant_id, " (swap)" if req.force and existing else "",
                f" +vapi:{vapi_id}" if vapi_id else "")
    return {"phone_number": number, "provisioned": True, "already_existed": False,
            "provider": "telnyx", "vapi_bound": bool(vapi_id), "from_pool": False}


class PoolPreloadRequest(BaseModel):
    count: int = 10
    country: str = "CA"
    area_code: str | None = None

    @field_validator("count")
    @classmethod
    def _cap_count(cls, v: int) -> int:
        # Guard a fat-fingered bulk buy — each number is real money.
        if v < 1 or v > 50:
            raise ValueError("count must be between 1 and 50")
        return v


@router.post("/pool/preload")
async def pool_preload(req: PoolPreloadRequest, principal=Depends(require_admin_auth)):
    """Admin: buy `count` Telnyx numbers, bind each to Vapi, and stock the pool.
    Onboarding then claims a ready number instantly. Admin-only (bulk spend)."""
    if not vapi_telnyx_enabled():
        raise HTTPException(503, "Telnyx→Vapi binding not configured "
                                 "(VAPI_PRIVATE_KEY + VAPI_TELNYX_CREDENTIAL_ID)")
    from ...services.number_pool import buy_into_pool
    return await buy_into_pool(req.count, country=req.country, area_code=req.area_code)


@router.get("/pool")
async def pool_status_endpoint(principal=Depends(require_admin_auth)):
    """Admin: pool inventory counts (available / assigned / released)."""
    from ...services.number_pool import pool_status
    return await pool_status(get_db())


async def _store_provisioned_number(db, merchant_id: str, has_row: bool, payload: dict) -> None:
    """Write a provisioned number onto phone_agent_config. vapi_phone_number_id
    ships in migration 20260721; tolerate its absence so a deploy that predates
    the migration still provisions (retry without the column)."""
    try:
        if has_row:
            await db.update("phone_agent_config", payload, filters={"merchant_id": f"eq.{merchant_id}"})
        else:
            await db.insert("phone_agent_config", {**payload, "merchant_id": merchant_id})
    except Exception as e:  # noqa: BLE001 — pre-migration column absence must not lose the number
        logger.warning("provision store failed (%s); retrying without vapi column", e)
        payload = {k: v for k, v in payload.items() if k != "vapi_phone_number_id"}
        if has_row:
            await db.update("phone_agent_config", payload, filters={"merchant_id": f"eq.{merchant_id}"})
        else:
            await db.insert("phone_agent_config", {**payload, "merchant_id": merchant_id})


async def _store_provisioned_number_atomic(
    db, merchant_id: str, has_row: bool, payload: dict, *, require_unassigned: bool,
) -> bool:
    """Race-safe store for a freshly provisioned number. True = our number landed.

    require_unassigned=True (every fresh provision) makes the write conditional:
    the update only matches a row whose phone_number is still NULL, and an
    insert that hits the merchant_id UNIQUE constraint counts as a loss — so
    when two provision calls race across workers/instances, exactly one writes
    and the loser returns False WITHOUT overwriting the winner's number.
    require_unassigned=False (the force/swap path, which intentionally replaces
    an existing number) is the legacy unconditional store. The
    vapi_phone_number_id retry mirrors _store_provisioned_number (pre-migration
    deploys must still provision)."""
    if not require_unassigned:
        await _store_provisioned_number(db, merchant_id, has_row, payload)
        return True
    if has_row:
        filters = {"merchant_id": f"eq.{merchant_id}", "phone_number": "is.null"}
        try:
            updated = await db.update("phone_agent_config", payload, filters=filters)
        except Exception as e:  # noqa: BLE001 — pre-migration vapi column
            logger.warning("provision store failed (%s); retrying without vapi column", e)
            slim = {k: v for k, v in payload.items() if k != "vapi_phone_number_id"}
            updated = await db.update("phone_agent_config", slim, filters=filters)
        return bool(updated)
    try:
        await db.insert("phone_agent_config", {**payload, "merchant_id": merchant_id})
        return True
    except Exception as e:  # noqa: BLE001
        # Either the pre-migration vapi column or a concurrent insert (UNIQUE
        # merchant_id). Retry slim once; a second failure = lost the race.
        logger.warning("provision insert failed (%s); retrying without vapi column", e)
        slim = {k: v for k, v in payload.items() if k != "vapi_phone_number_id"}
        try:
            await db.insert("phone_agent_config", {**slim, "merchant_id": merchant_id})
            return True
        except Exception as e2:  # noqa: BLE001
            logger.warning("provision insert lost the race for %s: %s", merchant_id, e2)
            return False


async def _lost_race_response(
    db, merchant_id: str, number: str, sid, vapi_id, *, from_pool: bool,
) -> dict:
    """Unwind the loser of a provision race and answer with the winner's number.

    Pool claim → flip our claimed pool row back to available (the DID stays
    Telnyx-owned + Vapi-bound; only the assignment is undone). Live buy →
    delete the Vapi binding and release the Telnyx number, so a lost race never
    leaks a monthly-billed orphan DID. Unwind is best-effort: an unwind failure
    is logged loudly but the caller still gets the winner's (correct) number."""
    try:
        if from_pool:
            await db.update(
                "phone_number_pool",
                {"status": "available", "assigned_merchant_id": None, "assigned_at": None},
                filters={"phone_number": f"eq.{number}", "status": "eq.assigned"},
            )
        else:
            if vapi_id:
                await delete_vapi_number(vapi_id)
            await _telnyx_release(number, sid)
    except Exception as e:  # noqa: BLE001 — never mask the winner's number
        logger.error("provision race unwind FAILED for %s (from_pool=%s) — "
                     "possible orphan DID, check provider: %s", number, from_pool, e)
    rows = await db.select(
        "phone_agent_config", filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    winner = rows[0].get("phone_number") if rows else None
    logger.warning("provision race for merchant %s: lost to concurrent request "
                   "(winner=%s, our %s unwound)", merchant_id, winner, number)
    return {"phone_number": winner, "provisioned": False, "already_existed": True}
