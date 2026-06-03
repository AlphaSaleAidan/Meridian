"""
Clover OAuth Routes — merchant authorization flow.

  GET  /api/clover/authorize  → Redirect merchant to Clover
  GET  /api/clover/callback   → Handle callback from Clover

Mirrors the Square OAuth shape (`src/api/routes/oauth.py`):
  * HMAC-signed state token with optional rep_id (P2 rep
    attribution);
  * Backward-compatible state format (5-part with rep_id, accepts
    4-part legacy);
  * Encrypted token storage on success;
  * Background backfill kickoff;
  * Frontend redirect with success / denied / error.

The audit's docstring in `src/api/routes/pos_connections.py` promised
this surface ("OAuth-based systems (Square, Clover) use their own
/api/square/ and /api/clover/ routes for the authorization flow")
but the routes themselves were never mounted. This file closes that
gap using the existing `CloverOAuthManager` helper class in
`src/clover/oauth.py`.
"""
import hashlib
import hmac
import logging
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from fastapi.responses import RedirectResponse

from ...clover.oauth import CloverOAuthManager, CloverOAuthError
from ...security.encryption import encrypt_token

logger = logging.getLogger("meridian.api.clover_oauth")

router = APIRouter(prefix="/api/clover", tags=["clover-oauth"])

# Shared OAUTH_STATE_SECRET with Square (single CSRF-signing key
# across providers — rotating it forces re-auth on both surfaces,
# which is the right correlated-blast-radius for a CSRF break).
_STATE_SECRET = os.environ.get("OAUTH_STATE_SECRET", "")
if not _STATE_SECRET:
    if os.environ.get("TESTING", "").lower() in ("1", "true"):
        _STATE_SECRET = "test-only-secret-not-for-production"
    elif os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RENDER"):
        raise RuntimeError(
            "OAUTH_STATE_SECRET must be set in production — refusing to start"
        )
    else:
        import warnings
        _STATE_SECRET = os.urandom(32).hex()
        warnings.warn(
            "OAUTH_STATE_SECRET not set — using ephemeral random secret (dev only)"
        )

_STATE_TTL_SECONDS = 600  # 10 minutes — matches Square

_FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    os.environ.get("FRONTEND_ORIGIN", "https://meridian.tips")
)

oauth_manager = CloverOAuthManager()


def _sign_state(org_id: str, rep_id: str | None = None) -> str:
    """Same format as Square: `org_id:rep_id:nonce:expires:sig`."""
    nonce = uuid4().hex[:16]
    expires = int(time.time()) + _STATE_TTL_SECONDS
    rep_field = rep_id or ""
    payload = f"{org_id}:{rep_field}:{nonce}:{expires}"
    sig = hmac.new(
        _STATE_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:32]
    return f"{payload}:{sig}"


def _verify_state(state: str) -> tuple[str, str | None] | None:
    """Returns (org_id, rep_id_or_None). Accepts 5-part rep-id format
    and 4-part legacy format for any callbacks in flight when this
    code rolls out."""
    parts = state.split(":")
    if len(parts) == 5:
        org_id, rep_field, nonce, expires_str, sig = parts
    elif len(parts) == 4:
        org_id, nonce, expires_str, sig = parts
        rep_field = ""
    else:
        return None

    try:
        expires = int(expires_str)
    except ValueError:
        return None
    if time.time() > expires:
        logger.warning("Clover OAuth state expired")
        return None

    if len(parts) == 5:
        payload = f"{org_id}:{rep_field}:{nonce}:{expires_str}"
    else:
        payload = f"{org_id}:{nonce}:{expires_str}"
    expected_sig = hmac.new(
        _STATE_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected_sig):
        return None
    return org_id, (rep_field or None)


@router.get("/authorize")
async def authorize(
    request: Request,
    org_id: str | None = None,
    rep_id: str | None = None,
):
    """Step 1: redirect merchant to Clover's authorization page."""
    if not org_id:
        raise HTTPException(400, "org_id is required")

    state = _sign_state(org_id, rep_id=rep_id)
    url, _ = oauth_manager.get_authorize_url(org_id=org_id, state=state)

    logger.info(
        f"Clover OAuth: redirecting org {org_id} to Clover authorize "
        f"(rep_id={'set' if rep_id else 'none'})"
    )
    return RedirectResponse(url=url)


@router.get("/callback")
async def callback(
    request: Request,
    background_tasks: BackgroundTasks,
    code: str | None = None,
    state: str | None = None,
    merchant_id: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    """Step 2: handle Clover's OAuth callback.

    Clover sends `merchant_id` as a query param alongside `code`
    (unlike Square, which embeds it in the token response). We
    forward both into `exchange_code` so the manager records the
    right merchant identity on the tokens dict.
    """
    if error:
        logger.warning(f"Clover OAuth denied: {error} — {error_description}")
        params = urlencode({
            "oauth": "denied",
            "provider": "clover",
            "error": error_description or "Authorization was denied.",
        })
        return RedirectResponse(url=f"{_FRONTEND_URL}/app/settings?{params}")

    if not code or not state:
        raise HTTPException(400, "Missing code or state parameter")

    verified = _verify_state(state)
    if verified is None:
        raise HTTPException(403, "Invalid or expired state — possible CSRF attack")
    org_id, rep_id = verified

    try:
        tokens = await oauth_manager.exchange_code(code, merchant_id=merchant_id)
    except CloverOAuthError as e:
        logger.error(f"Clover OAuth token exchange failed for org {org_id}: {e}")
        params = urlencode({
            "oauth": "error",
            "provider": "clover",
            "error": str(e),
        })
        return RedirectResponse(url=f"{_FRONTEND_URL}/app/settings?{params}")

    logger.info(
        f"Clover OAuth success for org {org_id}: "
        f"merchant_id={tokens['merchant_id']}"
    )

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
                    "plan": "free",
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                logger.info(f"Created organization: {org_id}")

            connection_data = {
                "id": str(uuid4()),
                "org_id": org_id,
                "provider": "clover",
                "status": "connected",
                "merchant_id": tokens["merchant_id"],
                "access_token_encrypted": encrypt_token(tokens["access_token"]),
                # Clover tokens don't auto-expire — leave refresh +
                # expires_at NULL so the token_refresh worker skips them.
                "location_ids": [],
                "historical_import_complete": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if rep_id:
                connection_data["connected_by_rep_id"] = rep_id

            existing = await _db_instance.select(
                "pos_connections",
                filters={
                    "org_id": f"eq.{org_id}",
                    "merchant_id": f"eq.{tokens['merchant_id']}",
                },
                limit=1,
            )

            if existing:
                update_fields = {
                    "status": "connected",
                    "access_token_encrypted": encrypt_token(tokens["access_token"]),
                    "last_error": None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                if rep_id:
                    update_fields["connected_by_rep_id"] = rep_id
                await _db_instance.update(
                    "pos_connections",
                    update_fields,
                    filters={"id": f"eq.{existing[0]['id']}"},
                )
                conn_id = existing[0]["id"]
                logger.info(f"Updated existing Clover connection for org {org_id}")
            else:
                await _db_instance.insert("pos_connections", connection_data)
                conn_id = connection_data["id"]
                logger.info(f"Created new Clover connection for org {org_id}")

            await _db_instance.insert("notifications", {
                "id": str(uuid4()),
                "org_id": org_id,
                "title": "Clover Connected!",
                "body": (
                    f"Successfully connected to Clover merchant "
                    f"{tokens['merchant_id']}. Starting initial data sync..."
                ),
                "priority": "normal",
                "source_type": "event",
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

            # Kick off backfill using the same path the credential-paste
            # surface uses (auto-backfill added in P1).
            from .pos_connections import _run_clover_backfill
            background_tasks.add_task(
                _run_clover_backfill,
                org_id=org_id,
                connection_id=conn_id,
                credentials={
                    "access_token": tokens["access_token"],
                    "merchant_id": tokens["merchant_id"],
                },
            )
            logger.info(f"Queued Clover backfill for org={org_id}, connection={conn_id}")
        else:
            logger.warning("DB not initialized — Clover tokens returned but not persisted")
    except Exception as e:
        logger.error(f"Failed to store Clover OAuth tokens: {e}", exc_info=True)
        params = urlencode({
            "oauth": "partial",
            "provider": "clover",
            "merchant_id": tokens["merchant_id"],
            "warning": "Connected but failed to save — please retry.",
        })
        return RedirectResponse(url=f"{_FRONTEND_URL}/app/settings?{params}")

    params = urlencode({
        "oauth": "success",
        "provider": "clover",
        "merchant_id": tokens["merchant_id"],
    })
    return RedirectResponse(url=f"{_FRONTEND_URL}/app/settings?{params}")


@router.get("/status")
async def connection_status(org_id: str):
    """Quick check if org has an active Clover connection."""
    from ...db import _db_instance
    if not _db_instance:
        return {"connected": False, "reason": "db_unavailable"}

    conns = await _db_instance.select(
        "pos_connections",
        filters={"org_id": f"eq.{org_id}", "provider": "eq.clover"},
        limit=1,
    )
    if conns:
        c = conns[0]
        return {
            "connected": True,
            "merchant_id": c.get("merchant_id"),
            "status": c.get("status"),
            "last_sync_at": c.get("last_sync_at"),
        }
    return {"connected": False}
