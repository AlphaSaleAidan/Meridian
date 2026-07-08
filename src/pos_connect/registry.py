"""
POS provider registry for the generic 1-click connector.

Each ProviderConfig describes one OAuth2 authorization-code provider. Adding a
new 1-click POS = adding an entry here (plus registering a real developer app
and flipping `verified` once validated) — no new route code.

IMPORTANT — `verified` discipline:
  Endpoints/scopes below are transcribed from public developer docs. Several
  vendors ship *multiple* products with different OAuth hosts (e.g. Lightspeed
  R-Series `cloud.lightspeedapp.com` vs X-Series `retail.lightspeed.app` vs
  K-Series). Docs are NOT proof. A config stays `verified=False` until its full
  authorize→callback→token round-trip has been run against a real registered
  app. `verified=False` providers are never offered (see `enabled`).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderConfig:
    key: str                      # url-safe slug, e.g. "lightspeed_xseries"
    label: str                    # display name, e.g. "Lightspeed (X-Series)"
    authorize_url: str            # OAuth2 authorization endpoint
    token_url: str                # OAuth2 token endpoint ({domain_prefix} placeholder allowed)
    scopes: list[str]             # requested scopes
    client_id_env: str            # env var holding the app's client id
    client_secret_env: str        # env var holding the app's client secret
    # How to resolve the merchant's external id after token exchange:
    #   "token:<field>"  → read <field> straight from the token response
    #   "userinfo:<url>:<dotted.path>" → GET <url> with bearer token, read path
    merchant_id_strategy: str
    uses_pkce: bool = False
    verified: bool = False        # validated against a real app? (see module docstring)
    # Market context surfaced to the frontend / sales, not used at runtime.
    market_note: str = ""
    docs_url: str = ""
    extra_authorize_params: dict[str, str] = field(default_factory=dict)

    def client_id(self) -> str:
        return os.environ.get(self.client_id_env, "")

    def client_secret(self) -> str:
        return os.environ.get(self.client_secret_env, "")

    def credentials_present(self) -> bool:
        return bool(self.client_id() and self.client_secret())

    def enabled(self) -> bool:
        """Offered to merchants only when validated AND server-side creds exist."""
        return self.verified and self.credentials_present()


# ─── Registry ────────────────────────────────────────────────────────────────
# All new providers start verified=False. Square and Clover are intentionally
# ABSENT here — they keep their dedicated, fully-synced routes.
_REGISTRY: dict[str, ProviderConfig] = {
    p.key: p
    for p in [
        # Lightspeed X-Series (formerly Vend) — self-serve OAuth2, strong US
        # restaurant + retail share. Highest-value net-new 1-click target.
        # NOTE: endpoint host differs between Lightspeed products — confirm the
        # X-Series host on the real app before flipping verified.
        ProviderConfig(
            key="lightspeed_xseries",
            label="Lightspeed (X-Series)",
            # Validated 2026-07-08 against the real "Meridian POS Analytics" app:
            # secure.retail.lightspeed.app/connect accepted our client_id and
            # redirected to Lightspeed sign-in preserving the OAuth params. Token
            # host is per-account (the domain_prefix returned on the callback).
            authorize_url="https://secure.retail.lightspeed.app/connect",
            token_url="https://{domain_prefix}.retail.lightspeed.app/api/1.0/token",
            scopes=["sales:read", "products:read"],  # X-Series requires a scope from 2026-06-01
            client_id_env="LIGHTSPEED_CLIENT_ID",
            client_secret_env="LIGHTSPEED_CLIENT_SECRET",
            # X-Series identifies the account by the domain_prefix on the callback
            # query, not in the token response.
            merchant_id_strategy="callback:domain_prefix",
            verified=True,
            market_note="Self-serve OAuth2. Real US restaurant + retail footprint.",
            docs_url="https://x-series-api.lightspeedhq.com/docs/authorization",
        ),
        # SumUp — self-serve OAuth2. Small in US restaurants (mobile card reader),
        # but a clean, simple connector; good framework proof.
        ProviderConfig(
            key="sumup",
            label="SumUp",
            authorize_url="https://api.sumup.com/authorize",
            token_url="https://api.sumup.com/token",
            scopes=["transactions.history"],
            client_id_env="SUMUP_CLIENT_ID",
            client_secret_env="SUMUP_CLIENT_SECRET",
            merchant_id_strategy="userinfo:https://api.sumup.com/v0.1/me:merchant_profile.merchant_code",
            verified=False,
            market_note="Self-serve OAuth2. Low US restaurant share.",
            docs_url="https://developer.sumup.com/tools/authorization/oauth",
        ),
        # PayPal Zettle — self-serve OAuth2 (PKCE). EU-leaning; low US restaurant share.
        ProviderConfig(
            key="zettle",
            label="PayPal Zettle",
            authorize_url="https://oauth.zettle.com/authorize",
            token_url="https://oauth.zettle.com/token",
            scopes=["READ:PURCHASE"],
            client_id_env="ZETTLE_CLIENT_ID",
            client_secret_env="ZETTLE_CLIENT_SECRET",
            merchant_id_strategy="userinfo:https://oauth.zettle.com/users/self:uuid",
            uses_pkce=True,
            verified=False,
            market_note="Self-serve OAuth2 (PKCE). EU-leaning.",
            docs_url="https://developer.zettle.com/docs/api/oauth",
        ),
    ]
}


def get_provider(key: str) -> ProviderConfig | None:
    return _REGISTRY.get(key)


def enabled_providers() -> list[ProviderConfig]:
    return [p for p in _REGISTRY.values() if p.enabled()]


# Public read-only view.
PROVIDERS: dict[str, ProviderConfig] = dict(_REGISTRY)
