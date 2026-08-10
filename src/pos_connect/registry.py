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
    # Token-endpoint auth style: False → client_id/client_secret in the form
    # body (the common OAuth2 pattern); True → HTTP basic with client_secret
    # as the username (Stripe Apps' /v1/oauth/token contract).
    token_basic_auth: bool = False
    # Seconds an access token lives when the token response omits expires_in
    # (Stripe Apps: fixed 1h, not echoed in the response). 0 = trust expires_in.
    default_token_ttl: int = 0
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
        # Stripe — merchant connects their EXISTING Stripe account via a
        # STRIPE APP (stripe-app/ in this repo), not classic Connect OAuth:
        # Stripe support confirmed 2026-08-08 that the Connect `read_only`
        # scope is deprecated and platforms must ship a Stripe App for
        # read-only access. The app declares `charge_read` in its manifest;
        # no `scope` param goes on the authorize URL.
        #   client_id     → the app's OAuth client id (from the app's
        #                   External test / Settings tab after upload — NOT
        #                   the legacy ca_… Connect id)
        #   client_secret → the app developer account's SECRET KEY, sent as
        #                   HTTP basic auth on /v1/oauth/token
        # Deliberately STRIPE_POS_* env names — the payments rails
        # (stripe_connect.py / stripe_checkout.py) own STRIPE_SECRET_KEY and
        # may be a different Stripe account. Access tokens live 1h with
        # rolling 1y refresh tokens (see src/stripe_pos/tokens.py).
        # Unlike a POS, Stripe has charges only (no items/menu/labor); the sync
        # engine lives in src/stripe_pos/.
        ProviderConfig(
            key="stripe",
            label="Stripe",
            authorize_url="https://marketplace.stripe.com/oauth/v2/authorize",
            token_url="https://api.stripe.com/v1/oauth/token",
            scopes=[],  # permissions are declared in stripe-app/stripe-app.json
            client_id_env="STRIPE_POS_CLIENT_ID",
            client_secret_env="STRIPE_POS_CLIENT_SECRET",
            # Token response carries stripe_user_id = acct_… directly.
            merchant_id_strategy="token:stripe_user_id",
            token_basic_auth=True,
            default_token_ttl=3600,
            verified=False,
            market_note="Payment processor, not full POS — revenue analytics only (no menu/labor).",
            docs_url="https://docs.stripe.com/stripe-apps/api-authentication/oauth",
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
