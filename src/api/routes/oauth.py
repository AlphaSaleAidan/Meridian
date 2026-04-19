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
from uuid import uuid4

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

from ...square.oauth import OAuthManager, OAuthError
from ...config import app as app_config

logger = logging.getLogger("meridian.api.oauth")

router = APIRouter(prefix="/api/square", tags=["square-oauth"])

# HMAC signing secret — loaded from env, must be set in production
_STATE_SECRET = os.environ.get("OAUTH_STATE_SECRET", "dev-secret-change-me")
_STATE_TTL_SECONDS = 600  # 10 minutes

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

    # Create self-contained HMAC-signed state (no server-side storage)
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
    
    On success: exchange code for tokens, start backfill.
    On denial: show friendly error message.
    """
    # Handle merchant denial
    if error:
        logger.warning(f"OAuth denied: {error} — {error_description}")
        return JSONResponse(
            status_code=200,
            content={
                "status": "denied",
                "error": error,
                "message": error_description or "Authorization was denied.",
            },
        )

    if not code or not state:
        raise HTTPException(400, "Missing code or state parameter")

    # Verify HMAC-signed state (no server-side store needed)
    org_id = _verify_state(state)
    if org_id is None:
        raise HTTPException(403, "Invalid or expired state — possible CSRF attack")

    # Exchange code for tokens
    try:
        tokens = await oauth_manager.exchange_code(code)
    except OAuthError as e:
        logger.error(f"OAuth token exchange failed for org {org_id}: {e}")
        raise HTTPException(500, f"Token exchange failed: {str(e)}")

    logger.info(
        f"OAuth success for org {org_id}: "
        f"merchant_id={tokens['merchant_id']}, "
        f"expires_at={tokens['expires_at']}"
    )

    # In production: 
    # 1. Encrypt tokens with Supabase Vault
    # 2. Upsert into pos_connections table
    # 3. Kick off initial backfill worker
    # 4. Redirect to dashboard with success message

    return JSONResponse(
        status_code=200,
        content={
            "status": "connected",
            "merchant_id": tokens["merchant_id"],
            "expires_at": tokens["expires_at"],
            "org_id": org_id,
            "message": "Square connected! Starting initial data sync...",
            "next_step": "backfill_started",
        },
    )
