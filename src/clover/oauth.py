"""
Clover OAuth 2.0 Manager — Handles merchant authorization flow.

Flow:
  1. Generate authorize URL → merchant approves on Clover
  2. Handle callback → exchange code for access token
  3. Token refresh → Clover tokens don't expire but can be revoked
  4. Token revocation → disconnect + cleanup

Clover OAuth differences from Square:
  - Tokens don't auto-expire (no refresh flow needed)
  - Auth URL includes merchant_id in some flows
  - Scopes are implicit based on app permissions (set in Clover dashboard)
  - Sandbox uses sandbox.dev.clover.com, production uses www.clover.com
"""
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from ..config import clover as cl_config, app as app_config

logger = logging.getLogger("meridian.clover.oauth")


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

        Returns:
            {
                "access_token": "...",
                "merchant_id": "...",
                "employee_id": "...",  # employee who authorized
                "token_type": "bearer",
                "connected_at": "2026-04-21T00:00:00Z"
            }
        """
        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.get(
                f"{self.base_url}/oauth/token",
                params={
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "code": code,
                },
            )

        if response.status_code != 200:
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            error_msg = body.get("message", response.text[:200])
            logger.error(f"Clover OAuth exchange failed: {response.status_code} — {error_msg}")
            raise CloverOAuthError(f"Token exchange failed: {error_msg}")

        data = response.json()
        access_token = data.get("access_token")

        if not access_token:
            raise CloverOAuthError("No access_token in Clover response")

        logger.info(f"Clover OAuth success — merchant_id={merchant_id}")

        return {
            "access_token": access_token,
            "merchant_id": merchant_id or data.get("merchant_id", ""),
            "employee_id": data.get("employee_id", ""),
            "token_type": "bearer",
            "connected_at": datetime.now(timezone.utc).isoformat(),
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

    # ─── Webhook Signature Verification ───────────────────────

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verify Clover webhook HMAC signature.

        Clover signs webhooks with HMAC-SHA256 using the app secret.
        """
        expected = hmac.new(
            self.app_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)
