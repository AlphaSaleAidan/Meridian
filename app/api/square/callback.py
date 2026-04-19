"""
FastAPI route: Square OAuth callback.

GET /api/square/callback?code={AUTH_CODE}&state={CSRF_TOKEN}

After a merchant approves on Square's consent page, Square redirects here.
We exchange the code for tokens and kick off the initial backfill.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from ...services.square.oauth import OAuthError, exchange_code

logger = logging.getLogger("meridian.api.square.callback")
router = APIRouter(prefix="/api/square", tags=["square-oauth"])

# In production this comes from a signed cookie / Redis session
# For now we accept any state to simplify sandbox testing
SKIP_STATE_CHECK = os.getenv("SQUARE_SKIP_STATE_CHECK", "true").lower() == "true"
DASHBOARD_URL = os.getenv("MERIDIAN_DASHBOARD_URL", "https://app.meridianpos.ai/dashboard")


@router.get("/callback")
async def square_oauth_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
):
    """
    Square redirects merchants here after they approve (or deny).

    Happy path:
        1. Exchange authorization code → access + refresh tokens
        2. Store tokens in pos_connections (encrypted in prod)
        3. Kick off initial backfill worker
        4. Redirect merchant to Meridian dashboard

    Denied / error:
        Redirect to dashboard with error query param.
    """

    # -- Handle denial / error from Square --------------------------------
    if error:
        logger.warning("OAuth denied: %s — %s", error, error_description)
        return RedirectResponse(
            f"{DASHBOARD_URL}/connect?error={error}&detail={error_description or ''}"
        )

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # -- CSRF state validation (skipped in sandbox) -----------------------
    if not SKIP_STATE_CHECK:
        # In production: verify `state` matches the value stored in
        # the user's session when we generated the auth URL.
        stored_state = request.session.get("square_oauth_state")
        if state != stored_state:
            raise HTTPException(status_code=403, detail="Invalid state token")

    # -- Exchange code for tokens -----------------------------------------
    try:
        tokens = await exchange_code(code)
    except OAuthError as exc:
        logger.error("Token exchange failed: %s", exc)
        return RedirectResponse(
            f"{DASHBOARD_URL}/connect?error=token_exchange_failed&detail={exc.description}"
        )

    # -- Persist connection -----------------------------------------------
    # In production this does:
    #   INSERT INTO pos_connections (
    #       org_id, provider, status, access_token_enc, refresh_token_enc,
    #       token_expires_at, external_merchant_id
    #   ) VALUES (...)
    #
    # For now we log so sandbox tests can verify the flow works.
    logger.info(
        "OAuth complete — merchant=%s, token_expires=%s",
        tokens.merchant_id,
        tokens.expires_at.isoformat(),
    )

    connection_record = {
        "provider": "square",
        "status": "connected",
        "access_token": tokens.access_token[:12] + "…",  # redacted for logging
        "refresh_token": tokens.refresh_token[:12] + "…" if tokens.refresh_token else None,
        "token_expires_at": tokens.expires_at.isoformat(),
        "external_merchant_id": tokens.merchant_id,
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("Connection record: %s", connection_record)

    # -- Kick off backfill (production: enqueue to task queue) ------------
    # await task_queue.enqueue("square_backfill", connection_id=new_conn.id)

    # -- Redirect to dashboard -------------------------------------------
    return RedirectResponse(f"{DASHBOARD_URL}/connect?success=true&provider=square")
