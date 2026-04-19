"""
Meridian × Square integration layer.

Modules:
  client.py           — Async Square REST client with retries + rate limiting
  oauth.py            — OAuth 2.0 flow (authorize, exchange, refresh, revoke)
  mappers.py          — Square → Meridian data transformers (6 modules)
  sync_engine.py      — Backfill + incremental sync orchestration
  webhook_handlers.py — HMAC verification + 7 event handlers
  rate_limiter.py     — Token-bucket rate limiter
"""

from .client import SquareClient, SquareAPIError, SquareRetryExhaustedError
from .oauth import generate_auth_url, exchange_code, refresh_token
from .rate_limiter import SquareRateLimiter
from .sync_engine import run_initial_backfill, run_incremental_sync, SyncResult

__all__ = [
    "SquareClient",
    "SquareAPIError",
    "SquareRetryExhaustedError",
    "SquareRateLimiter",
    "SyncResult",
    "generate_auth_url",
    "exchange_code",
    "refresh_token",
    "run_initial_backfill",
    "run_incremental_sync",
]
