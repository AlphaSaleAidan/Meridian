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
from ..pos_connect.oauth import OAuthError as GenericOAuthError
from ..security.encryption import decrypt_token, encrypt_token
from ..square.oauth import OAuthManager, OAuthError

logger = logging.getLogger("meridian.workers.token_refresh")


def _oauth_for(provider: str, conn: dict | None = None):
    """Return an object with an async refresh_token(token) method for this
    connection's provider, or None if the provider has no refresh flow here.

    Registry (pos_connect) providers refresh through the generic manager —
    EXCEPT stripe, whose rolling refresh token is owned by stripe_pos.tokens at
    sync time (a concurrent refresh here would invalidate the rolled token and
    kill the connection)."""
    if provider == "square":
        return OAuthManager()
    if provider == "clover":
        return CloverOAuthManager()
    if provider == "stripe":
        return None
    from ..pos_connect.registry import get_provider
    cfg = get_provider(provider)
    if cfg is None or not cfg.credentials_present():
        return None

    class _GenericRefresher:
        """Adapts GenericOAuthManager.refresh to the refresh_token(token)
        contract this worker calls. Lightspeed X-Series tokens live on a
        per-account host — its {domain_prefix} is the stored merchant id."""

        async def refresh_token(self, refresh_token: str) -> dict:
            from ..pos_connect.oauth import GenericOAuthManager
            domain_prefix = ""
            if "{domain_prefix}" in cfg.token_url:
                domain_prefix = (conn or {}).get("external_merchant_id", "") or ""
            mgr = GenericOAuthManager(cfg, redirect_uri="")  # unused for refresh
            return await mgr.refresh(refresh_token, domain_prefix=domain_prefix)

    return _GenericRefresher()


async def refresh_expiring_tokens() -> dict:
    """
    Refresh tokens for all connections expiring within 7 days.

    Returns:
        {"refreshed": count, "failed": count, "errors": [...]}
    """
    db = get_db()

    cutoff = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    # Include `error` rows, not just `connected`. A failed sync sets status=error
    # and nothing ever sets it back except a fresh OAuth authorization, so
    # filtering on connected-only permanently excluded those rows from refresh —
    # their tokens then lapsed and the merchant had to reconnect by hand. A
    # refresh is precisely how such a connection recovers, so attempt it.
    all_conns = await db.select(
        "pos_connections",
        filters={"status": "in.(connected,error)"},
    )
    # Refresh anything expiring within 7 days OR with a missing/blank expiry. The
    # manual /connect path never set token_expires_at, and a server-side `lt` filter
    # silently EXCLUDES those NULLs — so they expired unnoticed and sync died at
    # ~30 days with no signal (audit #8). Filter in Python to include them.
    connections = [
        c for c in (all_conns or [])
        if not c.get("token_expires_at") or c["token_expires_at"] < cutoff
    ]

    stats = {"refreshed": 0, "failed": 0, "recovered": 0, "expiring_unfixed": [], "errors": []}

    for conn in connections:
        connection_id = conn.get("id", "unknown")
        org_id = conn.get("org_id", "unknown")

        try:
            oauth = _oauth_for(conn.get("provider", ""), conn)
            if oauth is None:
                # Provider has no refresh flow here (Toast client-credentials,
                # Stripe's sync-time rolling refresh, unconfigured registry
                # providers) — skip silently.
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
                # A working token means the connection is healthy again. Without
                # this the row stays `error` forever and is re-stranded next run.
                "status": "connected",
                "last_error": None,
            }
            was_errored = conn.get("status") == "error"
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
            if was_errored:
                stats["recovered"] += 1
                logger.info(f"Recovered errored connection {connection_id} (org={org_id})")

        except (OAuthError, CloverOAuthError, GenericOAuthError) as e:
            logger.error(f"Token refresh failed for connection {connection_id}: {e}")
            stats["errors"].append(f"{connection_id}: {str(e)}")
            stats["failed"] += 1
            _note_if_lapsing(stats, conn, connection_id, org_id, str(e))

        except Exception as e:
            logger.error(f"Unexpected error refreshing {connection_id}: {e}", exc_info=True)
            stats["errors"].append(f"{connection_id}: {str(e)}")
            stats["failed"] += 1
            _note_if_lapsing(stats, conn, connection_id, org_id, str(e))

    logger.info(
        f"Token refresh complete: {stats['refreshed']} refreshed "
        f"({stats['recovered']} recovered), {stats['failed']} failed"
    )
    if stats["expiring_unfixed"]:
        # Loud, greppable line: these merchants lose POS sync when the clock runs
        # out and only a manual reconnect brings them back.
        logger.error(
            "POS TOKEN LAPSE IMMINENT — refresh failed for %d connection(s) expiring within 7 days: %s",
            len(stats["expiring_unfixed"]),
            stats["expiring_unfixed"],
        )
    return stats


def _note_if_lapsing(stats: dict, conn: dict, connection_id: str, org_id: str, error: str) -> None:
    """Flag a failed refresh whose token actually runs out soon.

    A failure on a token with months left is noise; a failure on one expiring
    this week means the merchant is about to go dark.
    """
    expires_at = conn.get("token_expires_at")
    if not expires_at:
        return
    stats["expiring_unfixed"].append(
        {
            "connection_id": connection_id,
            "org_id": org_id,
            "provider": conn.get("provider"),
            "expires_at": expires_at,
            "error": error[:200],
        }
    )
