"""
Worker: Square token refresh (runs daily via cron).

Proactively refreshes access tokens that expire within 5 days.
Square access tokens have a 30-day TTL and Square also rotates
the refresh token on each use, so both must be persisted.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from ..services.square.oauth import OAuthError, refresh_token

logger = logging.getLogger("meridian.workers.token_refresh")


async def refresh_expiring_tokens() -> dict[str, int]:
    """
    Find all Square connections expiring within 5 days and refresh them.

    In production:
        connections = await db.query('''
            SELECT id, refresh_token_enc, token_expires_at
            FROM pos_connections
            WHERE provider = 'square'
              AND status IN ('connected', 'syncing')
              AND token_expires_at < NOW() + INTERVAL '5 days'
        ''')

    Returns dict with counts: refreshed, failed, skipped.
    """
    stats = {"refreshed": 0, "failed": 0, "skipped": 0}

    # Placeholder: in production, iterate DB rows
    # For each connection:
    #   1. Decrypt refresh_token_enc
    #   2. Call refresh_token()
    #   3. Encrypt + store new access_token and refresh_token
    #   4. Update token_expires_at

    logger.info("Token refresh cron — scanning for tokens expiring within 5 days")

    # Example for a single sandbox connection:
    # (In sandbox, tokens don't really expire, but this proves the flow)
    sample_refresh_token = os.getenv("SQUARE_REFRESH_TOKEN", "")
    if sample_refresh_token:
        try:
            tokens = await refresh_token(sample_refresh_token)
            logger.info(
                "Refreshed token for merchant %s — new expiry: %s",
                tokens.merchant_id, tokens.expires_at,
            )
            stats["refreshed"] += 1

            # await db.update("pos_connections", conn.id,
            #     access_token_enc=encrypt(tokens.access_token),
            #     refresh_token_enc=encrypt(tokens.refresh_token),
            #     token_expires_at=tokens.expires_at,
            # )
        except OAuthError as exc:
            logger.error("Token refresh failed: %s", exc)
            stats["failed"] += 1
            # In production: if refresh fails, mark connection status='error'
            # and notify merchant to reconnect
    else:
        stats["skipped"] += 1
        logger.info("No refresh token configured — skipping")

    logger.info("Token refresh complete: %s", stats)
    return stats


# ---------------------------------------------------------------------------
# Standalone
# ---------------------------------------------------------------------------
async def _main() -> None:
    from dotenv import load_dotenv
    load_dotenv("/work/meridian/.env")

    stats = await refresh_expiring_tokens()
    print(f"Token refresh stats: {stats}")


if __name__ == "__main__":
    asyncio.run(_main())
