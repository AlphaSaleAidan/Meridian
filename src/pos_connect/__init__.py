"""
Generic POS 1-click connect framework.

Square and Clover each have a hand-written OAuth route + engine
(src/api/routes/oauth.py, clover_oauth.py). Those stay as-is — they are the
proven, fully-synced integrations. This package adds a *generic* OAuth2
authorization-code connector so additional POS providers become a config entry
(pos_connect/registry.py) rather than a new 400-line route file.

Safety model — a provider is only ever offered to a merchant when BOTH:
  1. `verified=True` in the registry (its OAuth config has been validated
     against a real registered developer app — not just transcribed from docs), and
  2. its client-id / client-secret env vars are actually set on the server.
`ProviderConfig.enabled()` enforces both. Until then the provider is invisible
to the frontend (GET /api/pos/providers returns only enabled ones) and its
authorize route 404s. Nothing half-built is ever shown to a merchant.

Scope note: this framework handles CONNECT + token storage + refresh. Per-provider
historical data sync (mapping a provider's orders/catalog into Meridian's schema)
is a separate build per provider, gated on a live test merchant — see
docs/POS_1CLICK_ONBOARDING.md.
"""
from .registry import PROVIDERS, ProviderConfig, get_provider, enabled_providers

__all__ = ["PROVIDERS", "ProviderConfig", "get_provider", "enabled_providers"]
