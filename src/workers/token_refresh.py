"""
Token Refresh Worker — Daily cron job.

Refreshes OAuth tokens expiring within 7 days. Square access tokens last ~30
days; Clover v2 access tokens last only ~30 min (so Clover is refreshed primarily
inline at sync time — see clover.oauth.ensure_fresh_clover_token — and this daily
pass is a backstop that keeps the refresh-token chain alive for idle connections).
Provider dispatch picks the matching OAuth manager so a Clover row is never
refreshed against Square's endpoint (or vice versa).
"""
import logging
from datetime import datetime, timedelta, timezone

from ..clover.oauth import CloverOAuthError, CloverOAuthManager
from ..db import get_db
from ..security.encryption import decrypt_token, encrypt_token
from ..square.oauth import OAuthManager, OAuthError

logger = logging.getLogger("meridian.workers.token_refresh")


def _oauth_for(provider: str):
    """Return the OAuth manager for a connection's provider, or None if the
    provider has no refresh flow (e.g. Toast client-credentials, generic)."""
    if provider == "square":
        return OAuthManager()
    if provider == "clover":
        return CloverOAuthManager()
    return None


async def refresh_expiring_tokens() -> dict:
    """
    Refresh tokens for all connections expiring within 7 days.

    Returns:
        {"refreshed": count, "failed": count, "errors": [...]}
    """
    db = get_db()

    cutoff = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    all_conns = await db.select(
        "pos_connections",
        filters={"status": "eq.connected"},
    )
    # Refresh anything expiring within 7 days OR with a missing/blank expiry. The
    # manual /connect path never set token_expires_at, and a server-side `lt` filter
    # silently EXCLUDES those NULLs — so they expired unnoticed and sync died at
    # ~30 days with no signal (audit #8). Filter in Python to include them.
    connections = [
        c for c in (all_conns or [])
        if not c.get("token_expires_at") or c["token_expires_at"] < cutoff
    ]

    stats = {"refreshed": 0, "failed": 0, "errors": []}

    for conn in connections:
        connection_id = conn.get("id", "unknown")
        org_id = conn.get("org_id", "unknown")

        try:
            oauth = _oauth_for(conn.get("provider", ""))
            if oauth is None:
                # Provider has no refresh flow (Toast/generic) — skip silently.
                continue

            refresh_token = decrypt_token(conn.get("refresh_token_enc", ""))

            if not refresh_token:
                logger.warning(f"No refresh token for connection {connection_id}")
                stats["errors"].append(f"{connection_id}: no refresh token")
                stats["failed"] += 1
                continue

            tokens = await oauth.refresh_token(refresh_token)

            update_data = {
                "access_token_enc": encrypt_token(tokens["access_token"]),
                "token_expires_at": tokens.get("expires_at"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            # Square may omit refresh_token in the refresh response.
            # Only overwrite when a non-empty new value is returned —
            # encrypting an empty string would brick future refreshes.
            new_refresh_token = tokens.get("refresh_token")
            if new_refresh_token:
                update_data["refresh_token_enc"] = encrypt_token(new_refresh_token)

            await db.update(
                "pos_connections",
                update_data,
                filters={"id": f"eq.{connection_id}"},
            )

            logger.info(f"Refreshed token for org={org_id} connection={connection_id}, new expiry: {tokens['expires_at']}")
            stats["refreshed"] += 1

        except (OAuthError, CloverOAuthError) as e:
            logger.error(f"Token refresh failed for connection {connection_id}: {e}")
            stats["errors"].append(f"{connection_id}: {str(e)}")
            stats["failed"] += 1

        except Exception as e:
            logger.error(f"Unexpected error refreshing {connection_id}: {e}", exc_info=True)
            stats["errors"].append(f"{connection_id}: {str(e)}")
            stats["failed"] += 1

    logger.info(f"Token refresh complete: {stats['refreshed']} refreshed, {stats['failed']} failed")
    return stats
