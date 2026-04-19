"""
Token Refresh Worker — Daily cron job.

Refreshes Square OAuth tokens expiring within 5 days.
Square access tokens expire after 30 days.
"""
import logging
from datetime import datetime, timezone

from ..square.oauth import OAuthManager, OAuthError

logger = logging.getLogger("meridian.workers.token_refresh")


async def refresh_expiring_tokens(
    connections: list[dict] | None = None,
) -> dict:
    """
    Refresh tokens for all connections expiring within 5 days.
    
    In production:
        connections = await db.query(GET_CONNECTIONS_NEEDING_REFRESH)
    
    Args:
        connections: List of pos_connection rows with refresh_token_enc
    
    Returns:
        {"refreshed": count, "failed": count, "errors": [...]}
    """
    oauth = OAuthManager()
    connections = connections or []
    
    stats = {"refreshed": 0, "failed": 0, "errors": []}

    for conn in connections:
        connection_id = conn.get("id", "unknown")
        org_id = conn.get("org_id", "unknown")
        
        try:
            # In production: decrypt(conn["refresh_token_enc"])
            refresh_token = conn.get("refresh_token_enc", "")
            
            if not refresh_token:
                logger.warning(f"No refresh token for connection {connection_id}")
                stats["errors"].append(f"{connection_id}: no refresh token")
                stats["failed"] += 1
                continue

            tokens = await oauth.refresh_token(refresh_token)
            
            # In production: update pos_connections table
            # await db.execute(UPDATE_CONNECTION_TOKENS, {
            #     "id": connection_id,
            #     "access_token_enc": encrypt(tokens["access_token"]),
            #     "refresh_token_enc": encrypt(tokens["refresh_token"]),
            #     "token_expires_at": tokens["expires_at"],
            # })
            
            logger.info(
                f"Refreshed token for org={org_id} connection={connection_id}, "
                f"new expiry: {tokens['expires_at']}"
            )
            stats["refreshed"] += 1

        except OAuthError as e:
            logger.error(f"Token refresh failed for connection {connection_id}: {e}")
            stats["errors"].append(f"{connection_id}: {str(e)}")
            stats["failed"] += 1

        except Exception as e:
            logger.error(f"Unexpected error refreshing {connection_id}: {e}", exc_info=True)
            stats["errors"].append(f"{connection_id}: {str(e)}")
            stats["failed"] += 1

    logger.info(
        f"Token refresh complete: {stats['refreshed']} refreshed, "
        f"{stats['failed']} failed"
    )
    return stats
