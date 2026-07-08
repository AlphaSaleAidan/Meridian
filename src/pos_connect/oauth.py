"""
Generic OAuth2 authorization-code manager for the POS connect framework.

Deliberately standalone from src/square/oauth.py and clover_oauth.py so adding
providers can never regress the two live integrations. State signing here uses
the same OAUTH_STATE_SECRET but a self-describing, provider-scoped payload.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import time
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import httpx

from .registry import ProviderConfig

logger = logging.getLogger("meridian.pos_connect.oauth")

_STATE_TTL_SECONDS = 600  # 10 minutes


class OAuthError(Exception):
    pass


def _state_secret() -> str:
    secret = os.environ.get("OAUTH_STATE_SECRET", "")
    if secret:
        return secret
    if os.environ.get("TESTING", "").lower() in ("1", "true"):
        return "test-only-secret-not-for-production"
    if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RENDER"):
        raise RuntimeError("OAUTH_STATE_SECRET must be set in production — refusing to start")
    import warnings
    warnings.warn("OAUTH_STATE_SECRET not set — using ephemeral random secret (dev only)")
    return os.urandom(32).hex()


def _b64(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=") if value else "_"


def _unb64(value: str) -> str:
    if value == "_":
        return ""
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
    except Exception:
        return ""


def sign_state(provider: str, org_id: str, return_to: str = "") -> str:
    """provider:org_id:nonce:expires:rt_b64:sig (HMAC-SHA256, 32-hex truncated)."""
    nonce = uuid4().hex[:16]
    expires = int(time.time()) + _STATE_TTL_SECONDS
    payload = f"{provider}:{org_id}:{nonce}:{expires}:{_b64(return_to)}"
    sig = hmac.new(_state_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}:{sig}"


def verify_state(state: str) -> tuple[str, str, str] | None:
    """Return (provider, org_id, return_to) or None on tamper/expiry."""
    parts = state.split(":")
    if len(parts) != 6:
        return None
    provider, org_id, nonce, expires_str, rt_b64, sig = parts
    payload = f"{provider}:{org_id}:{nonce}:{expires_str}:{rt_b64}"
    try:
        if time.time() > int(expires_str):
            return None
    except ValueError:
        return None
    expected = hmac.new(_state_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected):
        return None
    return provider, org_id, _unb64(rt_b64)


class GenericOAuthManager:
    def __init__(self, config: ProviderConfig, redirect_uri: str):
        self.cfg = config
        self.redirect_uri = redirect_uri

    def authorize_url(self, state: str, code_challenge: str = "") -> str:
        params: dict[str, str] = {
            "response_type": "code",
            "client_id": self.cfg.client_id(),
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        if self.cfg.scopes:
            params["scope"] = " ".join(self.cfg.scopes)
        if self.cfg.uses_pkce and code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        params.update(self.cfg.extra_authorize_params)
        return f"{self.cfg.authorize_url}?{urlencode(params)}"

    def _token_url(self, domain_prefix: str = "") -> str:
        return self.cfg.token_url.replace("{domain_prefix}", domain_prefix or "")

    async def exchange_code(self, code: str, code_verifier: str = "",
                            domain_prefix: str = "") -> dict[str, Any]:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.cfg.client_id(),
            "client_secret": self.cfg.client_secret(),
        }
        if self.cfg.uses_pkce and code_verifier:
            data["code_verifier"] = code_verifier
        return await self._post_token(data, domain_prefix)

    async def refresh(self, refresh_token: str, domain_prefix: str = "") -> dict[str, Any]:
        return await self._post_token({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.cfg.client_id(),
            "client_secret": self.cfg.client_secret(),
        }, domain_prefix)

    async def _post_token(self, data: dict[str, str], domain_prefix: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.post(
                self._token_url(domain_prefix),
                data=data,  # OAuth2 token endpoints take form-encoded bodies
                headers={"Accept": "application/json"},
            )
        if resp.status_code != 200:
            logger.error("token exchange failed for %s: %s %s",
                         self.cfg.key, resp.status_code, resp.text[:300])
            raise OAuthError(f"Token exchange failed ({resp.status_code})")
        body = resp.json()
        expires_in = body.get("expires_in")
        expires_at = (
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + int(expires_in)))
            if expires_in else ""
        )
        return {
            "access_token": body["access_token"],
            "refresh_token": body.get("refresh_token", ""),
            "expires_at": expires_at,
            "token_type": body.get("token_type", "bearer"),
            "raw": body,
        }

    async def resolve_merchant_id(self, tokens: dict[str, Any]) -> str:
        """Resolve external_merchant_id per the provider's strategy. Best-effort:
        falls back to '' so the caller can substitute a generated id."""
        strat = self.cfg.merchant_id_strategy
        try:
            if strat.startswith("token:"):
                field = strat.split(":", 1)[1]
                return str(tokens.get("raw", {}).get(field, "") or "")
            if strat.startswith("userinfo:"):
                _, url, path = strat.split(":", 2)
                async with httpx.AsyncClient(timeout=20.0) as http:
                    resp = await http.get(url, headers={
                        "Authorization": f"Bearer {tokens['access_token']}",
                        "Accept": "application/json",
                    })
                if resp.status_code != 200:
                    return ""
                node: Any = resp.json()
                for part in path.split("."):
                    node = node.get(part, {}) if isinstance(node, dict) else {}
                return str(node) if node and not isinstance(node, dict) else ""
        except Exception as e:
            logger.warning("merchant id resolution failed for %s: %s", self.cfg.key, e)
        return ""
