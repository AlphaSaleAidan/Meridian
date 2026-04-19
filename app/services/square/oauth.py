"""
Square OAuth 2.0 — authorization URL, code exchange, token refresh.

Flow:
  1. generate_auth_url()  → redirect merchant to Square consent page
  2. handle_callback()    → exchange auth code for access + refresh tokens
  3. refresh_token()      → rotate access token before expiry (30-day TTL)

All 7 scopes are read-only (Meridian never writes to merchant POS).
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger("meridian.square.oauth")

# ---------------------------------------------------------------------------
# Config loaded from environment
# ---------------------------------------------------------------------------
SQUARE_APP_ID = os.getenv("SQUARE_APP_ID", "")
SQUARE_APP_SECRET = os.getenv("SQUARE_APP_SECRET", "")
SQUARE_ENVIRONMENT = os.getenv("SQUARE_ENVIRONMENT", "sandbox")
SQUARE_REDIRECT_URI = os.getenv(
    "SQUARE_REDIRECT_URI", "https://app.meridianpos.ai/api/square/callback"
)

BASE_URL = (
    "https://connect.squareupsandbox.com"
    if SQUARE_ENVIRONMENT == "sandbox"
    else "https://connect.squareup.com"
)

SCOPES = [
    "MERCHANT_PROFILE_READ",
    "ITEMS_READ",
    "ORDERS_READ",
    "PAYMENTS_READ",
    "INVENTORY_READ",
    "EMPLOYEES_READ",
    "CUSTOMERS_READ",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime        # UTC
    merchant_id: str
    token_type: str = "bearer"

    @classmethod
    def from_square_response(cls, data: dict[str, Any]) -> "OAuthTokens":
        # Square returns expires_at as ISO-8601 string
        raw_exp = data.get("expires_at", "")
        if raw_exp:
            expires_at = datetime.fromisoformat(raw_exp.replace("Z", "+00:00"))
        else:
            # Fallback: 30 days from now
            from datetime import timedelta
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            expires_at=expires_at,
            merchant_id=data.get("merchant_id", ""),
            token_type=data.get("token_type", "bearer"),
        )


class OAuthError(Exception):
    def __init__(self, error: str, description: str = ""):
        self.error = error
        self.description = description
        super().__init__(f"{error}: {description}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_state_token() -> str:
    """Generate a cryptographically-random CSRF state token."""
    return secrets.token_urlsafe(32)


def generate_auth_url(state: str | None = None) -> tuple[str, str]:
    """
    Build the Square OAuth consent URL.

    Returns (url, state_token).
    """
    state = state or generate_state_token()
    scope_str = "+".join(SCOPES)
    url = (
        f"{BASE_URL}/oauth2/authorize"
        f"?client_id={SQUARE_APP_ID}"
        f"&scope={scope_str}"
        f"&session=false"
        f"&state={state}"
        f"&redirect_uri={SQUARE_REDIRECT_URI}"
    )
    return url, state


async def exchange_code(authorization_code: str) -> OAuthTokens:
    """
    Exchange the authorization code for access + refresh tokens.

    Called from the OAuth callback endpoint.
    """
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(
            f"{BASE_URL}/oauth2/token",
            json={
                "client_id": SQUARE_APP_ID,
                "client_secret": SQUARE_APP_SECRET,
                "code": authorization_code,
                "grant_type": "authorization_code",
                "redirect_uri": SQUARE_REDIRECT_URI,
            },
        )

    body = resp.json()

    if resp.status_code != 200 or "access_token" not in body:
        error = body.get("type", body.get("error", "unknown"))
        desc = body.get("message", body.get("error_description", str(body)))
        logger.error("OAuth code exchange failed: %s — %s", error, desc)
        raise OAuthError(error, desc)

    tokens = OAuthTokens.from_square_response(body)
    logger.info("OAuth code exchange succeeded for merchant %s", tokens.merchant_id)
    return tokens


async def refresh_token(current_refresh_token: str) -> OAuthTokens:
    """
    Refresh an access token before it expires (30-day TTL).
    Square also rotates the refresh token, so store both new values.
    """
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(
            f"{BASE_URL}/oauth2/token",
            json={
                "client_id": SQUARE_APP_ID,
                "client_secret": SQUARE_APP_SECRET,
                "refresh_token": current_refresh_token,
                "grant_type": "refresh_token",
            },
        )

    body = resp.json()

    if resp.status_code != 200 or "access_token" not in body:
        error = body.get("type", body.get("error", "unknown"))
        desc = body.get("message", body.get("error_description", str(body)))
        logger.error("Token refresh failed: %s — %s", error, desc)
        raise OAuthError(error, desc)

    tokens = OAuthTokens.from_square_response(body)
    logger.info("Token refreshed for merchant %s (expires %s)", tokens.merchant_id, tokens.expires_at)
    return tokens


async def revoke_token(access_token: str) -> bool:
    """Revoke a token (used when merchant disconnects from Meridian side)."""
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(
            f"{BASE_URL}/oauth2/revoke",
            json={
                "client_id": SQUARE_APP_ID,
                "access_token": access_token,
            },
            headers={"Authorization": f"Client {SQUARE_APP_SECRET}"},
        )
    if resp.status_code == 200:
        body = resp.json()
        return body.get("success", False)
    return False
