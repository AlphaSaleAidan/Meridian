"""
OAuth Routes — Square authorization endpoints.

  GET  /api/square/authorize  → Redirect merchant to Square
  GET  /api/square/callback   → Handle callback from Square
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

from ...square.oauth import OAuthManager, OAuthError
from ...security.encryption import encrypt_token
# Shared post-OAuth return-path allowlist (also used by clover_oauth.py) so the
# two callbacks can't drift — US /onboard was missing here before centralization.
from ._oauth_return import safe_return_to as _safe_return_to

logger = logging.getLogger("meridian.api.oauth")

router = APIRouter(prefix="/api/square", tags=["square-oauth"])

# org_id is a Postgres uuid column; a non-uuid value (demo/edge callers) makes
# the DB lookup raise an invalid-uuid cast error → 500. Validate the shape first
# and treat anything else as "not connected" (same regex as phone_dashboard).
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I
)
# Real merchant/org ids are the businesses.id TEXT primary key shaped `biz_<hex>`
# (see frontend auth.tsx). Accept both UUIDs and `biz_` ids, keeping a strict
# format guard so nothing arbitrary reaches the query layer.
_ORG_ID_RE = re.compile(
    r'^(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    r'|biz_[0-9a-f]{16,40})$',
    re.I,
)

# HMAC signing secret — REQUIRED in all environments.
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

# Frontend URL for redirects after OAuth
_FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    os.environ.get("FRONTEND_ORIGIN", "https://meridian.tips")
)

oauth_manager = OAuthManager()

# Post-callback redirect must stay on-site and on an allowlisted path. Empty/
# unknown return_to falls back to the legacy /app/settings target so existing
# (US) flows are byte-identical.
_DEFAULT_RETURN_TO = "/app/settings"


def _redirect_to(return_to: str, params: dict) -> RedirectResponse:
    """Build a same-origin redirect to the wizard (or legacy settings)."""
    path = return_to or _DEFAULT_RETURN_TO
    return RedirectResponse(url=f"{_FRONTEND_URL}{path}?{urlencode(params)}")


def _sign_state(org_id: str, return_to: str = "") -> str:
    """Create a self-contained HMAC-signed state token.

    Format: org_id:nonce:expires:rt_b64:sig (rt_b64 is '_' when no return_to,
    keeping legacy 4-part tokens verifiable for in-flight flows)."""
    nonce = uuid4().hex[:16]
    expires = int(time.time()) + _STATE_TTL_SECONDS
    rt_b64 = base64.urlsafe_b64encode(return_to.encode()).decode().rstrip("=") if return_to else "_"
    payload = f"{org_id}:{nonce}:{expires}:{rt_b64}"
    sig = hmac.new(
        _STATE_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:32]
    return f"{payload}:{sig}"


def _verify_state(state: str) -> tuple[str, str] | None:
    """Verify HMAC-signed state token. Returns (org_id, return_to) or None."""
    parts = state.split(":")
    if len(parts) == 4:
        org_id, nonce, expires_str, sig = parts
        rt_b64 = "_"
        payload = f"{org_id}:{nonce}:{expires_str}"
    elif len(parts) == 5:
        org_id, nonce, expires_str, rt_b64, sig = parts
        payload = f"{org_id}:{nonce}:{expires_str}:{rt_b64}"
    else:
        return None
    try:
        expires = int(expires_str)
    except ValueError:
        return None
    if time.time() > expires:
        logger.warning("OAuth state expired")
        return None
    expected_sig = hmac.new(
        _STATE_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected_sig):
        return None
    if rt_b64 == "_":
        return_to = ""
    else:
        try:
            pad = "=" * (-len(rt_b64) % 4)
            return_to = base64.urlsafe_b64decode(rt_b64 + pad).decode()
        except Exception:
            return_to = ""
    return org_id, _safe_return_to(return_to)


@router.get("/authorize")
async def authorize(request: Request, org_id: str | None = None, return_to: str | None = None):
    """
    Step 1: Redirect merchant to Square's authorization page.

    Query params:
      org_id — the merchant's org ID (to link after callback)
      return_to — optional on-site path to land on after callback (allowlisted
        to /canada/merchant*; anything else is ignored and the legacy
        /app/settings target is used).
    """
    if not org_id:
        raise HTTPException(400, "org_id is required")

    state = _sign_state(org_id, _safe_return_to(return_to))
    url, _ = oauth_manager.get_authorize_url(org_id=org_id, state=state)

    logger.info(f"OAuth: redirecting org {org_id} to Square authorize")
    return RedirectResponse(url=url)


@router.get("/callback")
async def callback(
    request: Request,
    background_tasks: BackgroundTasks,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    """
    Step 2: Handle Square's OAuth callback.
    
    On success: exchange code for tokens, store in DB, redirect to dashboard.
    On denial: redirect to settings with error.
    """
    # Handle merchant denial — recover return_to from state when present so the
    # Canada wizard can surface the denial in-place.
    if error:
        logger.warning(f"OAuth denied: {error} — {error_description}")
        verified = _verify_state(state) if state else None
        denied_return_to = verified[1] if verified else ""
        return _redirect_to(denied_return_to, {
            "oauth": "denied",
            "error": error_description or "Authorization was denied.",
        })

    if not code or not state:
        raise HTTPException(400, "Missing code or state parameter")

    # Verify HMAC-signed state
    verified = _verify_state(state)
    if verified is None:
        raise HTTPException(403, "Invalid or expired state — possible CSRF attack")
    org_id, return_to = verified

    # Exchange code for tokens
    try:
        tokens = await oauth_manager.exchange_code(code)
    except OAuthError as e:
        logger.error(f"OAuth token exchange failed for org {org_id}: {e}")
        return _redirect_to(return_to, {
            "oauth": "error",
            "error": str(e),
        })

    logger.info(
        f"OAuth success for org {org_id}: "
        f"merchant_id={tokens['merchant_id']}, "
        f"expires_at={tokens['expires_at']}"
    )

    # ── Store tokens in Supabase ──────────────────────────
    try:
        from ...db import _db_instance
        if _db_instance:
            # Ensure organization exists
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
                logger.info(f"Created organization: {org_id}")

            # Upsert POS connection
            connection_data = {
                "id": str(uuid4()),
                "org_id": org_id,
                "provider": "square",
                "status": "connected",
                "external_merchant_id": tokens["merchant_id"],
                "access_token_enc": encrypt_token(tokens["access_token"]),
                "refresh_token_enc": encrypt_token(tokens.get("refresh_token", "")),
                "token_expires_at": tokens.get("expires_at"),
                "historical_import_complete": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Check if connection already exists for this org + merchant
            existing = await _db_instance.select(
                "pos_connections",
                filters={
                    "org_id": f"eq.{org_id}",
                    "external_merchant_id": f"eq.{tokens['merchant_id']}",
                },
                limit=1,
            )

            if existing:
                # Update existing connection
                await _db_instance.update(
                    "pos_connections",
                    {
                        "status": "connected",
                        "access_token_enc": encrypt_token(tokens["access_token"]),
                        "refresh_token_enc": encrypt_token(tokens.get("refresh_token", "")),
                        "token_expires_at": tokens.get("expires_at"),
                        "last_error": None,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    filters={"id": f"eq.{existing[0]['id']}"},
                )
                logger.info(f"Updated existing connection for org {org_id}")
            else:
                # Insert new connection
                await _db_instance.insert("pos_connections", connection_data)
                logger.info(f"Created new connection for org {org_id}")

            # Reflect connected state where the merchant dashboard reads it:
            # the dashboard gates on businesses.pos_connected (fetchBusinessForUser),
            # and org-path falls back to organizations.pos_connection_status.
            await _db_instance.update(
                "businesses",
                {"pos_connected": True},
                filters={"id": f"eq.{org_id}"},
            )
            await _db_instance.update(
                "organizations",
                {"pos_system": "square", "pos_connection_status": "connected"},
                filters={"id": f"eq.{org_id}"},
            )

            # Kick off historical backfill in background FIRST — a failure of the
            # (best-effort) welcome notification below must never prevent data sync.
            conn_id = existing[0]["id"] if existing else connection_data["id"]
            from ...workers.backfill import run_backfill
            background_tasks.add_task(
                run_backfill,
                access_token=tokens["access_token"],
                org_id=org_id,
                connection_id=conn_id,
            )
            logger.info(f"Queued backfill task for org={org_id}, connection={conn_id}")

            # Best-effort welcome notification — NON-FATAL. notifications has
            # NOT-NULL user_id/channel/scheduled_for; if user_id can't be resolved
            # (or the insert otherwise fails) we must not roll back a successful
            # connection. Previously this threw and pushed the whole callback into
            # the "Connected but failed to save" partial path.
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
                        "title": "Square Connected!",
                        "body": f"Successfully connected to Square merchant {tokens['merchant_id']}. Starting initial data sync...",
                        "priority": "normal",
                        "source_type": "event",
                        "status": "active",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
            except Exception as notify_err:
                logger.warning(f"Welcome notification skipped for org {org_id}: {notify_err}")

        else:
            logger.warning("DB not initialized — tokens returned but not persisted")

    except Exception as e:
        logger.error(f"Failed to store OAuth tokens: {e}", exc_info=True)
        # Don't fail the callback — redirect with warning
        return _redirect_to(return_to, {
            "oauth": "partial",
            "merchant_id": tokens["merchant_id"],
            "warning": "Connected but failed to save — please retry.",
        })

    # ── Redirect back to the originating surface ──────────
    return _redirect_to(return_to, {
        "oauth": "success",
        "merchant_id": tokens["merchant_id"],
    })


@router.get("/status")
async def connection_status(org_id: str):
    """Quick check if org has an active Square connection."""
    from ...db import _db_instance
    # Guard malformed org_id (demo edge) before it reaches the query layer.
    # Accepts both UUIDs and `biz_` merchant ids (the real businesses.id shape).
    if not _ORG_ID_RE.match(org_id or ""):
        return {"connected": False, "reason": "invalid_org_id"}
    if not _db_instance:
        return {"connected": False, "reason": "db_unavailable"}

    conn = await _db_instance.get_pos_connection(org_id)
    if conn:
        return {
            "connected": True,
            "merchant_id": conn.get("external_merchant_id"),
            "status": conn.get("status"),
            "last_sync_at": conn.get("last_sync_at"),
            "historical_import_complete": conn.get("historical_import_complete", False),
        }
    return {"connected": False}
