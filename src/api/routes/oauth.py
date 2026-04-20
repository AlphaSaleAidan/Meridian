"""
OAuth Routes — Square authorization endpoints.

  GET  /api/square/authorize  → Redirect merchant to Square
  GET  /api/square/callback   → Handle callback from Square
"""
import hashlib
import hmac
import logging
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

from ...square.oauth import OAuthManager, OAuthError
from ...config import app as app_config

logger = logging.getLogger("meridian.api.oauth")

router = APIRouter(prefix="/api/square", tags=["square-oauth"])

# HMAC signing secret — REQUIRED in all environments.
_STATE_SECRET = os.environ.get("OAUTH_STATE_SECRET", "")
if not _STATE_SECRET:
    import warnings
    if os.environ.get("TESTING", "").lower() in ("1", "true"):
        _STATE_SECRET = "test-only-secret-not-for-production"
        warnings.warn("Using test-only OAUTH_STATE_SECRET — do NOT use in production")
    else:
        _STATE_SECRET = "dev-fallback-not-for-production"
        warnings.warn("OAUTH_STATE_SECRET not set — using insecure fallback")

_STATE_TTL_SECONDS = 600  # 10 minutes

# Frontend URL for redirects after OAuth
_FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    os.environ.get("FRONTEND_ORIGIN", "https://meridian-dun-nu.vercel.app")
)

oauth_manager = OAuthManager()


def _sign_state(org_id: str) -> str:
    """Create a self-contained HMAC-signed state token: org_id:nonce:expires:sig."""
    nonce = uuid4().hex[:16]
    expires = int(time.time()) + _STATE_TTL_SECONDS
    payload = f"{org_id}:{nonce}:{expires}"
    sig = hmac.new(
        _STATE_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:32]
    return f"{payload}:{sig}"


def _verify_state(state: str) -> str | None:
    """Verify HMAC-signed state token. Returns org_id or None."""
    parts = state.split(":")
    if len(parts) != 4:
        return None
    org_id, nonce, expires_str, sig = parts
    try:
        expires = int(expires_str)
    except ValueError:
        return None
    if time.time() > expires:
        logger.warning("OAuth state expired")
        return None
    payload = f"{org_id}:{nonce}:{expires_str}"
    expected_sig = hmac.new(
        _STATE_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected_sig):
        return None
    return org_id


@router.get("/authorize")
async def authorize(request: Request, org_id: str | None = None):
    """
    Step 1: Redirect merchant to Square's authorization page.
    
    Query params:
      org_id — the merchant's org ID (to link after callback)
    """
    if not org_id:
        raise HTTPException(400, "org_id is required")

    state = _sign_state(org_id)
    url, _ = oauth_manager.get_authorize_url(org_id=org_id, state=state)
    
    logger.info(f"OAuth: redirecting org {org_id} to Square authorize")
    return RedirectResponse(url=url)


@router.get("/callback")
async def callback(
    request: Request,
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
    # Handle merchant denial
    if error:
        logger.warning(f"OAuth denied: {error} — {error_description}")
        params = urlencode({
            "oauth": "denied",
            "error": error_description or "Authorization was denied.",
        })
        return RedirectResponse(url=f"{_FRONTEND_URL}/app/settings?{params}")

    if not code or not state:
        raise HTTPException(400, "Missing code or state parameter")

    # Verify HMAC-signed state
    org_id = _verify_state(state)
    if org_id is None:
        raise HTTPException(403, "Invalid or expired state — possible CSRF attack")

    # Exchange code for tokens
    try:
        tokens = await oauth_manager.exchange_code(code)
    except OAuthError as e:
        logger.error(f"OAuth token exchange failed for org {org_id}: {e}")
        params = urlencode({
            "oauth": "error",
            "error": str(e),
        })
        return RedirectResponse(url=f"{_FRONTEND_URL}/app/settings?{params}")

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
                    "plan": "free",
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                logger.info(f"Created organization: {org_id}")

            # Upsert POS connection
            connection_data = {
                "id": str(uuid4()),
                "org_id": org_id,
                "provider": "square",
                "status": "connected",
                "merchant_id": tokens["merchant_id"],
                "access_token_encrypted": tokens["access_token"],
                "refresh_token_encrypted": tokens.get("refresh_token", ""),
                "token_expires_at": tokens.get("expires_at"),
                "location_ids": [],
                "historical_import_complete": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Check if connection already exists for this org + merchant
            existing = await _db_instance.select(
                "pos_connections",
                filters={
                    "org_id": f"eq.{org_id}",
                    "merchant_id": f"eq.{tokens['merchant_id']}",
                },
                limit=1,
            )

            if existing:
                # Update existing connection
                await _db_instance.update(
                    "pos_connections",
                    {
                        "status": "connected",
                        "access_token_encrypted": tokens["access_token"],
                        "refresh_token_encrypted": tokens.get("refresh_token", ""),
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

            # Create a notification
            await _db_instance.insert("notifications", {
                "id": str(uuid4()),
                "org_id": org_id,
                "title": "Square Connected!",
                "body": f"Successfully connected to Square merchant {tokens['merchant_id']}. Starting initial data sync...",
                "priority": "normal",
                "source_type": "event",
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        else:
            logger.warning("DB not initialized — tokens returned but not persisted")

    except Exception as e:
        logger.error(f"Failed to store OAuth tokens: {e}", exc_info=True)
        # Don't fail the callback — redirect with warning
        params = urlencode({
            "oauth": "partial",
            "merchant_id": tokens["merchant_id"],
            "warning": "Connected but failed to save — please retry.",
        })
        return RedirectResponse(url=f"{_FRONTEND_URL}/app/settings?{params}")

    # ── Redirect to dashboard ────────────────────────────
    params = urlencode({
        "oauth": "success",
        "merchant_id": tokens["merchant_id"],
    })
    return RedirectResponse(url=f"{_FRONTEND_URL}/app/settings?{params}")


@router.get("/status")
async def connection_status(org_id: str):
    """Quick check if org has an active Square connection."""
    from ...db import _db_instance
    if not _db_instance:
        return {"connected": False, "reason": "db_unavailable"}

    conn = await _db_instance.get_pos_connection(org_id)
    if conn:
        return {
            "connected": True,
            "merchant_id": conn.get("merchant_id"),
            "status": conn.get("status"),
            "last_sync_at": conn.get("last_sync_at"),
        }
    return {"connected": False}
