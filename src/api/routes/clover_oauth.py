"""
Clover OAuth Routes — 1-click Square-style authorization for Clover.

  GET  /api/clover/authorize  → Redirect merchant to Clover
  GET  /api/clover/callback   → Handle callback from Clover

Manual key/ID paste is handled by /api/pos/connect; this module covers the
1-click OAuth path only. Mirrors src/api/routes/oauth.py (Square) — same
HMAC-signed state, same return_to allowlist, same encrypted-token storage.
"""
import base64
import hashlib
import hmac
import logging
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from fastapi.responses import RedirectResponse

from ...clover.oauth import CloverOAuthManager, CloverOAuthError
from ...config import clover as clover_config
from ...db.supabase_rest import SupabaseRESTError, is_uuid_cast_error
from ...security.encryption import encrypt_token
# Shared post-OAuth return-path + origin allowlists (also used by oauth.py/Square).
from ._oauth_return import (
    origin_from_referer as _origin_from_referer,
    safe_origin as _safe_origin,
    safe_return_to as _safe_return_to,
)

logger = logging.getLogger("meridian.api.clover_oauth")

router = APIRouter(prefix="/api/clover", tags=["clover-oauth"])

# org_id is validated before it reaches the DB lookup. Real merchant/org ids are
# the businesses.id TEXT primary key shaped `biz_<hex>` (see frontend auth.tsx),
# but some tables still key off UUIDs — so accept BOTH shapes. Anything else is
# treated as "not connected" rather than crashing on an invalid cast. Keep a
# strict format guard so no arbitrary/injection string reaches the query layer.
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I
)
_ORG_ID_RE = re.compile(
    r'^(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    r'|biz_[0-9a-f]{16,40})$',
    re.I,
)

# HMAC signing secret — reuse the same OAuth state secret as Square so a single
# env var governs all OAuth CSRF protection.
_STATE_SECRET = os.environ.get("OAUTH_STATE_SECRET", "")
if not _STATE_SECRET:
    if os.environ.get("TESTING", "").lower() in ("1", "true"):
        _STATE_SECRET = "test-only-secret-not-for-production"
    elif os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RENDER"):
        raise RuntimeError("OAUTH_STATE_SECRET must be set in production — refusing to start")
    else:
        import warnings
        _STATE_SECRET = os.urandom(32).hex()
        warnings.warn("OAUTH_STATE_SECRET not set — using ephemeral random secret (dev only)")

_STATE_TTL_SECONDS = 600  # 10 minutes

_FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    os.environ.get("FRONTEND_ORIGIN", "https://meridian.tips")
)

_DEFAULT_RETURN_TO = "/app/settings"

oauth_manager = CloverOAuthManager()


def _redirect_to(return_to: str, params: dict, origin: str = "") -> RedirectResponse:
    path = return_to or _DEFAULT_RETURN_TO
    base = _safe_origin(origin) or _FRONTEND_URL
    return RedirectResponse(url=f"{base}{path}?{urlencode(params)}")


def _b64_encode_field(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=") if value else "_"


def _b64_decode_field(value: str) -> str:
    if value == "_":
        return ""
    try:
        pad = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + pad).decode()
    except Exception:
        return ""


def _sign_state(org_id: str, return_to: str = "", origin: str = "") -> str:
    """Self-contained HMAC-signed state token:
    org_id:nonce:expires:rt_b64[:origin_b64]:sig. origin_b64 is only appended
    when an origin was captured, so origin-less states stay in the older 5-part
    format and in-flight flows survive a deploy."""
    nonce = uuid4().hex[:16]
    expires = int(time.time()) + _STATE_TTL_SECONDS
    rt_b64 = _b64_encode_field(return_to)
    payload = f"{org_id}:{nonce}:{expires}:{rt_b64}"
    if origin:
        payload = f"{payload}:{_b64_encode_field(origin)}"
    sig = hmac.new(
        _STATE_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:32]
    return f"{payload}:{sig}"


def _verify_state(state: str) -> tuple[str, str, str] | None:
    """Verify HMAC-signed state token. Returns (org_id, return_to, origin) or
    None. Accepts old 5-part (no origin) and new 6-part formats."""
    parts = state.split(":")
    origin_b64 = "_"
    if len(parts) == 5:
        org_id, nonce, expires_str, rt_b64, sig = parts
        payload = f"{org_id}:{nonce}:{expires_str}:{rt_b64}"
    elif len(parts) == 6:
        org_id, nonce, expires_str, rt_b64, origin_b64, sig = parts
        payload = f"{org_id}:{nonce}:{expires_str}:{rt_b64}:{origin_b64}"
    else:
        return None
    try:
        expires = int(expires_str)
    except ValueError:
        return None
    if time.time() > expires:
        logger.warning("Clover OAuth state expired")
        return None
    expected_sig = hmac.new(
        _STATE_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected_sig):
        return None
    return_to = _b64_decode_field(rt_b64)
    origin = _b64_decode_field(origin_b64)
    return org_id, _safe_return_to(return_to), _safe_origin(origin)


@router.get("/authorize")
async def authorize(request: Request, org_id: str | None = None, return_to: str | None = None):
    """
    Step 1: Redirect merchant to Clover's authorization page.

    Requires CLOVER_APP_ID / CLOVER_APP_SECRET to be configured server-side. If
    they are not, the merchant should use the manual key/ID paste flow instead.
    """
    if not org_id:
        raise HTTPException(400, "org_id is required")
    if not clover_config.has_oauth_credentials:
        raise HTTPException(
            503,
            "Clover 1-click connect isn't configured on this server yet — "
            "use the manual API token + Merchant ID option instead.",
        )

    # Capture the origin the merchant started from (sessions are per-origin) so
    # the callback lands them back on the same frontend.
    origin = _origin_from_referer(request.headers.get("referer"))
    state = _sign_state(org_id, _safe_return_to(return_to), origin)
    url, _ = oauth_manager.get_authorize_url(org_id=org_id, state=state)

    logger.info(f"Clover OAuth: redirecting org {org_id} to Clover authorize")
    return RedirectResponse(url=url)


@router.get("/callback")
async def callback(
    request: Request,
    background_tasks: BackgroundTasks,
    code: str | None = None,
    state: str | None = None,
    merchant_id: str | None = None,
    employee_id: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    """
    Step 2: Handle Clover's OAuth callback.

    Clover sends code + merchant_id (and employee_id) plus our signed state.
    On success: exchange code for a token, store it encrypted, kick backfill.
    """
    if error:
        logger.warning(f"Clover OAuth denied: {error} — {error_description}")
        verified = _verify_state(state) if state else None
        denied_return_to = verified[1] if verified else ""
        denied_origin = verified[2] if verified else ""
        return _redirect_to(denied_return_to, {
            "oauth": "denied",
            "error": error_description or "Authorization was denied.",
        }, denied_origin)

    if not code or not state:
        raise HTTPException(400, "Missing code or state parameter")

    verified = _verify_state(state)
    if verified is None:
        raise HTTPException(403, "Invalid or expired state — possible CSRF attack")
    org_id, return_to, origin = verified

    try:
        tokens = await oauth_manager.exchange_code(code, merchant_id=merchant_id)
    except CloverOAuthError as e:
        logger.error(f"Clover token exchange failed for org {org_id}: {e}")
        return _redirect_to(return_to, {"oauth": "error", "error": str(e)}, origin)

    resolved_merchant_id = tokens.get("merchant_id") or merchant_id or ""
    logger.info(f"Clover OAuth success for org {org_id}: merchant_id={resolved_merchant_id}")

    # ── Store tokens in Supabase (mirror Square's storage shape) ──
    try:
        from ...db import _db_instance
        if _db_instance:
            existing_orgs = await _db_instance.select(
                "organizations",
                filters={"id": f"eq.{org_id}"},
                limit=1,
            )
            if not existing_orgs:
                await _db_instance.insert("organizations", {
                    "id": org_id,
                    "name": f"Org {org_id}",
                    "slug": org_id.lower().replace(" ", "-"),
                    # `vertical` is NOT NULL with no default on organizations — omitting
                    # it failed the insert, so the org row was never created and the
                    # pos_connections FK (org_id -> organizations.id) rejected the
                    # connection ("Connected but failed to save").
                    "vertical": "other",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })

            token_enc = encrypt_token(tokens["access_token"])
            # v2/OAuth tokens expire (~30 min) and carry a refresh_token; store
            # both + expiry so the sync path can refresh inline. Legacy apps
            # return blank refresh/expiry → columns stay null (non-expiring).
            refresh_enc = (
                encrypt_token(tokens["refresh_token"]) if tokens.get("refresh_token") else None
            )
            connection_data = {
                "id": str(uuid4()),
                "org_id": org_id,
                "provider": "clover",
                "status": "connected",
                "external_merchant_id": resolved_merchant_id,
                "access_token_enc": token_enc,
                "refresh_token_enc": refresh_enc,
                "token_expires_at": tokens.get("expires_at") or None,
                "credentials_encrypted": {
                    "access_token": token_enc,
                    "merchant_id": resolved_merchant_id,
                },
                "historical_import_complete": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            existing = await _db_instance.select(
                "pos_connections",
                filters={
                    "org_id": f"eq.{org_id}",
                    "provider": "eq.clover",
                },
                limit=1,
            )

            if existing:
                conn_id = existing[0]["id"]
                await _db_instance.update(
                    "pos_connections",
                    {
                        "status": "connected",
                        "external_merchant_id": resolved_merchant_id,
                        "access_token_enc": token_enc,
                        "refresh_token_enc": refresh_enc,
                        "token_expires_at": tokens.get("expires_at") or None,
                        "credentials_encrypted": connection_data["credentials_encrypted"],
                        "last_error": None,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    filters={"id": f"eq.{conn_id}"},
                )
            else:
                conn_id = connection_data["id"]
                await _db_instance.insert("pos_connections", connection_data)

            await _db_instance.update(
                "businesses",
                {"pos_connected": True},
                filters={"id": f"eq.{org_id}"},
            )
            await _db_instance.update(
                "organizations",
                {"pos_system": "clover", "pos_connection_status": "connected"},
                filters={"id": f"eq.{org_id}"},
            )

            # Queue backfill FIRST — the best-effort notification below must never
            # block data sync or roll back a successful connection.
            from .pos_connections import _run_clover_backfill
            background_tasks.add_task(
                _run_clover_backfill,
                org_id=org_id,
                connection_id=conn_id,
                access_token=tokens["access_token"],
                merchant_id=resolved_merchant_id,
            )
            logger.info(f"Queued Clover backfill for org={org_id}, connection={conn_id}")

            # Best-effort welcome notification — NON-FATAL (notifications has
            # NOT-NULL user_id/channel/scheduled_for).
            try:
                _biz = await _db_instance.select("businesses", filters={"id": f"eq.{org_id}"}, limit=1)
                owner_user_id = _biz[0].get("owner_user_id") if _biz else None
                if owner_user_id:
                    await _db_instance.insert("notifications", {
                        "id": str(uuid4()),
                        "org_id": org_id,
                        "user_id": owner_user_id,
                        "channel": "in_app",
                        "scheduled_for": datetime.now(timezone.utc).isoformat(),
                        "title": "Clover Connected!",
                        "body": f"Successfully connected to Clover merchant {resolved_merchant_id}. Starting initial data sync...",
                        "priority": "normal",
                        "source_type": "event",
                        "status": "active",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
            except Exception as notify_err:
                logger.warning(f"Welcome notification skipped for org {org_id}: {notify_err}")
        else:
            logger.warning("DB not initialized — Clover tokens returned but not persisted")

    except Exception as e:
        logger.error(f"Failed to store Clover OAuth tokens: {e}", exc_info=True)
        return _redirect_to(return_to, {
            "oauth": "partial",
            "merchant_id": resolved_merchant_id,
            "warning": "Connected but failed to save — please retry.",
        }, origin)

    return _redirect_to(return_to, {
        "oauth": "success",
        "merchant_id": resolved_merchant_id,
    }, origin)


@router.get("/status")
async def connection_status(org_id: str):
    """Quick check if org has an active Clover connection + whether 1-click is available."""
    from ...db import _db_instance
    oauth_available = clover_config.has_oauth_credentials
    clover_available = clover_config.is_enabled
    # Guard malformed org_id (demo edge) before it reaches the query layer.
    # Accepts both UUIDs and `biz_` merchant ids (the real businesses.id shape);
    # anything else is reported as "not connected" rather than crashing.
    if not _ORG_ID_RE.match(org_id or ""):
        return {
            "connected": False,
            "reason": "invalid_org_id",
            "oauth_available": oauth_available,
            "clover_available": clover_available,
        }
    if not _db_instance:
        return {
            "connected": False,
            "reason": "db_unavailable",
            "oauth_available": oauth_available,
            "clover_available": clover_available,
        }

    # pos_connections.org_id is a UUID column in prod; `biz_` merchant ids are
    # the TEXT businesses.id with NO businesses→organizations mapping, so a
    # biz_ id can never match a row — querying with it raises a 22P02 uuid cast
    # → 500 → the onboarding wizard read oauth_available as false and hid the
    # Clover 1-click button. Report not-connected but keep the REAL capability
    # flags (computed from env above, exactly as the happy path does).
    if not _UUID_RE.match(org_id):
        return {
            "connected": False,
            "reason": "org_not_uuid_keyed",
            "oauth_available": oauth_available,
            "clover_available": clover_available,
        }

    try:
        conns = await _db_instance.select(
            "pos_connections",
            filters={"org_id": f"eq.{org_id}", "provider": "eq.clover"},
            limit=1,
        )
    except SupabaseRESTError as exc:
        # Backstop: no validated id shape may 500 this read-only status
        # endpoint — a uuid-cast 400 (22P02) simply means "no such row".
        if exc.status_code == 400 and is_uuid_cast_error(exc):
            logger.info(
                "clover status: org_id=%s not UUID-shaped for pos_connections "
                "(message=%r) — reporting not connected", org_id, exc.message,
            )
            conns = []
        else:
            raise
    if conns:
        conn = conns[0]
        return {
            "connected": conn.get("status") == "connected",
            "merchant_id": conn.get("external_merchant_id"),
            "status": conn.get("status"),
            "last_sync_at": conn.get("last_sync_at"),
            "historical_import_complete": conn.get("historical_import_complete", False),
            "oauth_available": oauth_available,
            "clover_available": clover_available,
        }
    return {
        "connected": False,
        "oauth_available": oauth_available,
        "clover_available": clover_available,
    }
