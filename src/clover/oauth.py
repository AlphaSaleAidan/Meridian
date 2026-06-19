"""
Clover OAuth 2.0 Manager — Handles merchant authorization flow.

Flow:
  1. Generate authorize URL → merchant approves on Clover
  2. Handle callback → exchange code for access token (+ refresh token)
  3. Token refresh → v2/OAuth access tokens expire in 30 min; refresh inline
  4. Token revocation → disconnect + cleanup

Clover OAuth notes:
  - v2/OAuth (current default) issues an EXPIRING access_token (~30 min) plus a
    refresh_token. Legacy apps issue a non-expiring token with no refresh_token.
    exchange_code tries v2 first and falls back to legacy, so it works for both.
    https://docs.clover.com/dev/docs/use-oauth
  - Auth URL includes merchant_id in some flows
  - Scopes are implicit based on app permissions (set in Clover dashboard)
  - Sandbox uses sandbox.dev.clover.com, production uses www.clover.com
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from ..config import clover as cl_config

logger = logging.getLogger("meridian.clover.oauth")


def _unix_to_iso(value: Any) -> str:
    """Convert a Clover token expiration (Unix SECONDS, 10 digits) to ISO-8601.

    Clover OAuth expirations are in seconds; other Clover APIs use milliseconds.
    Returns "" when the value is missing/unparseable so callers store a blank
    (treated as "refresh now") rather than a bogus far-future date.
    """
    if not value:
        return ""
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (ValueError, OSError, TypeError):
        return ""


class CloverOAuthError(Exception):
    """Raised when OAuth flow fails."""
    pass


class CloverOAuthManager:
    """
    Manages Clover OAuth 2.0 authorization.

    Usage:
        oauth = CloverOAuthManager()

        # Step 1: Generate authorize URL
        url, state = oauth.get_authorize_url(org_id="...")
        # → redirect merchant to url

        # Step 2: Handle callback
        tokens = await oauth.exchange_code(code="AUTH_CODE", merchant_id="MERCH_ID")
        # → store tokens in pos_connections table

        # Step 3: No refresh needed — Clover tokens don't expire
    """

    def __init__(self):
        self.app_id = cl_config.app_id
        self.app_secret = cl_config.app_secret
        self.base_url = cl_config.base_url

    # ─── Step 1: Generate Authorization URL ───────────────────

    def get_authorize_url(
        self,
        org_id: str | None = None,
        state: str | None = None,
    ) -> tuple[str, str]:
        """
        Generate Clover OAuth authorization URL.

        Args:
            org_id: Merchant org ID (embedded in state for callback linking)
            state: Pre-built CSRF state token. If None, generates one.

        Returns (url, csrf_state_token) — store the state token
        in the session to verify on callback.
        """
        if state is None:
            state = secrets.token_urlsafe(32)
            if org_id:
                state = f"{org_id}:{state}"

        params = {
            "client_id": self.app_id,
            "response_type": "code",
            "state": state,
            "redirect_uri": cl_config.redirect_uri,
        }

        url = f"{cl_config.oauth_authorize_url}?{urlencode(params)}"
        return url, state

    # ─── Step 2: Exchange Authorization Code ──────────────────

    async def exchange_code(
        self,
        code: str,
        merchant_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Exchange authorization code for access token.

        Clover sends merchant_id in the callback URL params.

        Tries the v2/OAuth expiring-token flow first (POST /oauth/v2/token,
        returns access_token + refresh_token + expirations). If the app is on the
        legacy non-expiring flow, the v2 endpoint rejects the code, so we fall
        back to the legacy GET /oauth/token (no refresh_token/expiry).

        Returns:
            {
                "access_token": "...",
                "refresh_token": "...",     # "" on legacy apps
                "expires_at": "...",        # ISO; "" on legacy apps
                "refresh_token_expires_at": "...",
                "merchant_id": "...",
                "employee_id": "...",
                "token_type": "bearer",
                "connected_at": "2026-04-21T00:00:00Z",
            }
        """
        data: dict[str, Any] = {}
        access_token = ""

        # ── v2/OAuth (expiring) — POST body, NOT query params ──
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                v2 = await http.post(
                    cl_config.oauth_v2_token_url,
                    json={
                        "client_id": self.app_id,
                        "client_secret": self.app_secret,
                        "code": code,
                    },
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
            if v2.status_code == 200:
                data = v2.json()
                access_token = data.get("access_token", "")
            else:
                logger.info(
                    f"Clover v2 token exchange returned {v2.status_code}; "
                    f"falling back to legacy flow"
                )
        except httpx.HTTPError as e:
            logger.info(f"Clover v2 token exchange errored ({e}); falling back to legacy flow")

        # ── Legacy (non-expiring) — GET with query params ──
        if not access_token:
            async with httpx.AsyncClient(timeout=30.0) as http:
                legacy = await http.get(
                    f"{self.base_url}/oauth/token",
                    params={
                        "client_id": self.app_id,
                        "client_secret": self.app_secret,
                        "code": code,
                    },
                )
            if legacy.status_code != 200:
                body = legacy.json() if legacy.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = body.get("message", legacy.text[:200])
                logger.error(f"Clover OAuth exchange failed: {legacy.status_code} — {error_msg}")
                raise CloverOAuthError(f"Token exchange failed: {error_msg}")
            data = legacy.json()
            access_token = data.get("access_token", "")

        if not access_token:
            raise CloverOAuthError("No access_token in Clover response")

        refresh_token = data.get("refresh_token", "")
        expires_at = _unix_to_iso(data.get("access_token_expiration") or data.get("expires_at"))
        logger.info(
            f"Clover OAuth success — merchant_id={merchant_id} "
            f"flow={'v2' if refresh_token else 'legacy'}"
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "refresh_token_expires_at": _unix_to_iso(data.get("refresh_token_expiration")),
            "merchant_id": merchant_id or data.get("merchant_id", ""),
            "employee_id": data.get("employee_id", ""),
            "token_type": "bearer",
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

    # ─── Refresh expiring (v2) token ──────────────────────────

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Exchange a refresh_token for a fresh access_token (v2/OAuth).

        POST /oauth/v2/refresh with {client_id, refresh_token}. Returns the new
        access_token + refresh_token + ISO expiries. Mirrors Square's
        OAuthManager.refresh_token shape so the refresh worker can treat both
        providers uniformly.
        """
        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.post(
                cl_config.oauth_v2_refresh_url,
                json={"client_id": self.app_id, "refresh_token": refresh_token},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )

        if response.status_code != 200:
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            error_msg = body.get("message", response.text[:200])
            logger.error(f"Clover token refresh failed: {response.status_code} — {error_msg}")
            raise CloverOAuthError(f"Token refresh failed: {error_msg}")

        data = response.json()
        new_access = data.get("access_token", "")
        if not new_access:
            raise CloverOAuthError("No access_token in Clover refresh response")

        return {
            "access_token": new_access,
            "refresh_token": data.get("refresh_token", ""),
            "expires_at": _unix_to_iso(data.get("access_token_expiration") or data.get("expires_at")),
            "refresh_token_expires_at": _unix_to_iso(data.get("refresh_token_expiration")),
        }

    # ─── Verify Token ─────────────────────────────────────────

    async def verify_token(self, access_token: str, merchant_id: str) -> bool:
        """
        Verify a Clover access token is still valid by making a lightweight API call.
        """
        try:
            async with httpx.AsyncClient(timeout=15.0) as http:
                response = await http.get(
                    f"{cl_config.api_base_url}/v3/merchants/{merchant_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            return False

    # ─── Revoke / Disconnect ──────────────────────────────────

    async def revoke_token(self, access_token: str, merchant_id: str) -> bool:
        """
        Revoke a Clover access token.

        Note: Clover doesn't have a formal revoke endpoint.
        The merchant disconnects from the Clover app marketplace.
        We mark the connection as disconnected in our DB.
        """
        logger.info(f"Clover token revocation requested for merchant {merchant_id}")
        # Verify the token is actually dead
        is_valid = await self.verify_token(access_token, merchant_id)
        if not is_valid:
            logger.info(f"Token for merchant {merchant_id} is already invalid")
        return True

# ─── Inline token resolution (v2 expiring tokens) ─────────────

# Clover v2 access tokens live only ~30 minutes — too short for a daily refresh
# cron. Sync paths resolve the token through this helper, which refreshes inline
# (and persists the rotation) when the stored token is expired or near expiry.
_REFRESH_BUFFER = timedelta(minutes=5)


async def ensure_fresh_clover_token(connection: dict) -> str:
    """Return a valid Clover access token for a pos_connections row.

    - Legacy (non-expiring) connections have no refresh_token_enc → the stored
      access token is returned unchanged.
    - v2 connections are refreshed inline when token_expires_at is missing or
      within the 5-minute buffer; the rotated access/refresh token + new expiry
      are persisted back to pos_connections before the token is returned.
    On any refresh failure the stored token is returned (best-effort) so a
    transient refresh hiccup doesn't hard-fail the sync — the API call will
    surface a 401 if the token is truly dead.
    """
    from ..db import get_db
    from ..security.encryption import decrypt_token, encrypt_token

    access_token = decrypt_token(connection.get("access_token_enc", ""))
    refresh_tok = decrypt_token(connection.get("refresh_token_enc", ""))

    # No refresh token → legacy non-expiring flow; nothing to refresh.
    if not refresh_tok:
        return access_token

    expires_at = connection.get("token_expires_at")
    needs_refresh = True
    if expires_at:
        try:
            exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            needs_refresh = exp <= datetime.now(timezone.utc) + _REFRESH_BUFFER
        except ValueError:
            needs_refresh = True
    if not needs_refresh:
        return access_token

    try:
        oauth = CloverOAuthManager()
        new = await oauth.refresh_token(refresh_tok)
    except CloverOAuthError as e:
        logger.warning(
            f"Clover inline refresh failed for connection "
            f"{connection.get('id')}: {e} — using stored token"
        )
        return access_token

    new_access = new.get("access_token") or access_token
    update: dict[str, Any] = {
        "access_token_enc": encrypt_token(new_access),
        "token_expires_at": new.get("expires_at") or None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    # Only overwrite the refresh token when a new one is returned — encrypting an
    # empty string would brick future refreshes (same guard as Square's worker).
    new_refresh = new.get("refresh_token")
    if new_refresh:
        update["refresh_token_enc"] = encrypt_token(new_refresh)

    db = get_db()
    if db and connection.get("id"):
        await db.update("pos_connections", update, filters={"id": f"eq.{connection['id']}"})

    return new_access
