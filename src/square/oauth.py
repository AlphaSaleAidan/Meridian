"""
Square OAuth 2.0 Manager — Handles merchant authorization flow.

Flow:
  1. Generate authorize URL → merchant approves on Square
  2. Handle callback → exchange code for tokens
  3. Token refresh → automatic via daily cron
  4. Token revocation → disconnect + notify on webhook
"""
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from ..config import square as sq_config, app as app_config, OAUTH_SCOPES

logger = logging.getLogger("meridian.square.oauth")


class OAuthError(Exception):
    """Raised when OAuth flow fails."""
    pass


class OAuthManager:
    """
    Manages Square OAuth 2.0 authorization.
    
    Usage:
        oauth = OAuthManager()
        
        # Step 1: Generate authorize URL
        url, state = oauth.get_authorize_url()
        # → redirect merchant to url
        
        # Step 2: Handle callback
        tokens = await oauth.exchange_code(code="AUTH_CODE")
        # → store tokens in pos_connections table
        
        # Step 3: Refresh token (cron)
        new_tokens = await oauth.refresh_token(refresh_token="...")
    """

    def __init__(self):
        self.app_id = sq_config.app_id
        self.app_secret = sq_config.app_secret
        self.base_url = sq_config.base_url
        self.redirect_uri = app_config.redirect_uri

    # ─── Step 1: Generate Authorization URL ───────────────────

    def get_authorize_url(self, org_id: str | None = None) -> tuple[str, str]:
        """
        Generate Square OAuth authorization URL.
        
        Returns (url, csrf_state_token) — store the state token
        in the session to verify on callback.
        """
        state = secrets.token_urlsafe(32)
        
        # Encode org_id into state if provided (to link callback to org)
        if org_id:
            state = f"{org_id}:{state}"

        params = {
            "client_id": self.app_id,
            "scope": " ".join(OAUTH_SCOPES),
            "session": "false",
            "state": state,
        }

        url = f"{sq_config.oauth_authorize_url}?{urlencode(params)}"
        return url, state

    # ─── Step 2: Exchange Authorization Code ──────────────────

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access + refresh tokens.
        
        Returns:
            {
                "access_token": "...",
                "refresh_token": "...",
                "expires_at": "2026-05-19T00:00:00Z",
                "merchant_id": "...",
                "token_type": "bearer"
            }
        """
        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.post(
                f"{self.base_url}/oauth2/token",
                json={
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )

        if response.status_code != 200:
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            errors = body.get("errors", [{"detail": response.text}])
            logger.error(f"OAuth token exchange failed: {errors}")
            raise OAuthError(f"Token exchange failed: {errors}")

        data = response.json()
        
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "expires_at": data.get("expires_at", ""),
            "merchant_id": data.get("merchant_id", ""),
            "token_type": data.get("token_type", "bearer"),
        }

    # ─── Step 3: Refresh Token ────────────────────────────────

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh an expiring access token.
        
        Call this when token_expires_at is within 5 days.
        
        Returns same structure as exchange_code().
        """
        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.post(
                f"{self.base_url}/oauth2/token",
                json={
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

        if response.status_code != 200:
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            errors = body.get("errors", [{"detail": response.text}])
            logger.error(f"OAuth token refresh failed: {errors}")
            raise OAuthError(f"Token refresh failed: {errors}")

        data = response.json()

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "expires_at": data.get("expires_at", ""),
            "merchant_id": data.get("merchant_id", ""),
            "token_type": data.get("token_type", "bearer"),
        }

    # ─── Token Revocation ─────────────────────────────────────

    async def revoke_token(self, access_token: str) -> bool:
        """
        Revoke an access token (e.g., when merchant disconnects from Meridian).
        
        Returns True if revocation succeeded.
        """
        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.post(
                f"{self.base_url}/oauth2/revoke",
                json={
                    "client_id": self.app_id,
                    "access_token": access_token,
                },
                headers={
                    "Authorization": f"Client {self.app_secret}",
                    "Content-Type": "application/json",
                },
            )

        if response.status_code == 200:
            data = response.json()
            return data.get("success", False)

        logger.error(f"Token revocation failed: {response.status_code} {response.text}")
        return False

    # ─── CSRF Verification ────────────────────────────────────

    @staticmethod
    def verify_state(received_state: str, stored_state: str) -> bool:
        """Constant-time comparison of OAuth state parameter."""
        return hmac.compare_digest(received_state, stored_state)

    @staticmethod
    def extract_org_id(state: str) -> str | None:
        """Extract org_id from state if it was embedded."""
        if ":" in state:
            return state.split(":", 1)[0]
        return None
