"""
Meridian × Clover POS Integration

Mirrors the Square integration pattern:
  - OAuth 2.0 flow for merchant authorization
  - Async API client with rate limiting + retries
  - Sync engine (backfill + incremental + webhooks)
  - Data mappers (Clover → Meridian schema)
  - Webhook handlers (real-time updates)
"""
from .client import CloverClient, CloverAPIError
from .oauth import CloverOAuthManager, CloverOAuthError
from .sync_engine import CloverSyncEngine
from .mappers import CloverDataMapper

__all__ = [
    "CloverClient",
    "CloverAPIError",
    "CloverOAuthManager",
    "CloverOAuthError",
    "CloverSyncEngine",
    "CloverDataMapper",
]
