"""
Token Refresh Worker — Daily cron job.

Refreshes Square OAuth tokens expiring within 7 days.
Square access tokens expire after 30 days.
"""
import logging
from datetime import datetime, timedelta, timezone

from ..db import get_db
from ..security.encryption import decrypt_token, encrypt_token
from ..square.oauth import OAuthManager, OAuthError

logger = logging.getLogger("meridian.workers.token_refresh")


async def refresh_expiring_tokens() -> dict:
    """
    Refresh tokens for all connections expiring within 7 days.

    Returns:
        {"refreshed": count, "failed": count, "errors": [...]}
    """
    oauth = OAuthManager()
    db = get_db()

    cutoff = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    connections = await db.select(
        "pos_connections",
        filters={
            "status": "eq.connected",
            "token_expires_at": f"lt.{cutoff}",
        },
    )

    stats = {"refreshed": 0, "failed": 0, "errors": []}

    for conn in connections:
        connection_id = conn.get("id", "unknown")
        org_id = conn.get("org_id", "unknown")

        try:
            refresh_token = decrypt_token(conn.get("refresh_token_encrypted", ""))

            if not refresh_token:
                logger.warning(f"No refresh token for connection {connection_id}")
                stats["errors"].append(f"{connection_id}: no refresh token")
                stats["failed"] += 1
                continue

            tokens = await oauth.refresh_token(refresh_token)

            await db.update(
                "pos_connections",
                {
                    "access_token_encrypted": encrypt_token(tokens["access_token"]),
                    "refresh_token_encrypted": encrypt_token(tokens.get("refresh_token", "")),
                    "token_expires_at": tokens.get("expires_at"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                filters={"id": f"eq.{connection_id}"},
            )

            logger.info(f"Refreshed token for org={org_id} connection={connection_id}, new expiry: {tokens['expires_at']}")
            stats["refreshed"] += 1

        except OAuthError as e:
            logger.error(f"Token refresh failed for connection {connection_id}: {e}")
            stats["errors"].append(f"{connection_id}: {str(e)}")
            stats["failed"] += 1

        except Exception as e:
            logger.error(f"Unexpected error refreshing {connection_id}: {e}", exc_info=True)
            stats["errors"].append(f"{connection_id}: {str(e)}")
            stats["failed"] += 1

    logger.info(f"Token refresh complete: {stats['refreshed']} refreshed, {stats['failed']} failed")
    return stats
