"""
POS Sync Runner — Shared incremental sync logic.

Used by both the scheduler (automated) and the manual sync endpoint.
Decrypts credentials, creates the right client, runs the sync engine,
and persists results.
"""
import logging
from datetime import datetime, timezone

from ..security.encryption import decrypt_token

logger = logging.getLogger("meridian.services.pos_sync_runner")


def _parse_since(raw) -> datetime | None:
    """last_sync_at comes back from PostgREST as an ISO STRING, but the sync
    engines type ``since`` as datetime (Clover calls ``since.isoformat()`` and
    crashed with AttributeError on every incremental run). None on any parse
    failure — engines fall back to their own default window."""
    if raw is None or isinstance(raw, datetime):
        return raw
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        logger.warning("unparseable last_sync_at %r — using engine default window", raw)
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


async def run_incremental(org_id: str, provider: str, connection: dict):
    """Run an incremental sync for a single POS connection."""
    from ..db import get_db
    db = get_db()

    conn_id = connection["id"]
    since = _parse_since(connection.get("last_sync_at"))
    # Captured before any update so the auth-failure path can tell a fresh
    # disconnection from one it has already emailed about.
    was_connected = connection.get("status") == "connected"

    try:
        if provider == "square":
            result = await _sync_square(org_id, conn_id, connection, since)
        elif provider == "clover":
            result = await _sync_clover(org_id, conn_id, connection, since)
        elif provider == "toast":
            result = await _sync_toast(org_id, conn_id, connection, since)
        elif provider == "stripe":
            result = await _sync_stripe(org_id, conn_id, connection, since)
        else:
            result = await _sync_generic(org_id, conn_id, connection, provider, since)
            if result is None:
                return

        wrote_rows = bool(result.transactions or result.transaction_items)
        if result.transactions:
            await db.batch_upsert("transactions", result.transactions, on_conflict="org_id,external_id")
        if result.transaction_items:
            await db.batch_upsert("transaction_items", result.transaction_items, on_conflict="id,transaction_at")

        # Refresh the analytics matviews so the new rows actually surface on the
        # dashboard. The backfill path refreshes via run_analysis_only(), but the
        # 15-min incremental sweep writes straight to `transactions` and would
        # otherwise leave daily_revenue/hourly_revenue stale until the next
        # backfill — new revenue lands in the table but never on the dashboard.
        # Best-effort: a refresh hiccup must not fail (or unwind) a good sync.
        if wrote_rows:
            try:
                await db.refresh_views()
            except Exception as e:
                logger.warning(f"Matview refresh after incremental sync failed (non-fatal): {e}")

        # A sync engine that reports errors has NOT succeeded, even if it
        # returned normally instead of raising. Stamping last_sync_at and
        # clearing last_error here would erase the only evidence the sync is
        # broken and leave the connection looking healthy.
        if getattr(result, "errors", None):
            raise RuntimeError(f"sync reported errors: {'; '.join(str(x) for x in result.errors)[:400]}")

        await db.update(
            "pos_connections",
            {
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
                "last_error": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            filters={"id": f"eq.{conn_id}"},
        )

        logger.info(f"Incremental sync {org_id}/{provider}: {len(result.transactions)} transactions")

    except Exception as e:
        logger.error(f"Sync failed {org_id}/{provider}: {e}", exc_info=True)
        now = datetime.now(timezone.utc).isoformat()
        # An auth failure (revoked/expired token) is terminal — flip the connection
        # out of 'connected' so the dashboard prompts a reconnect, instead of the
        # 15-min sweep hammering a dead token forever (audit #8). A transient error
        # keeps 'connected' so a blip doesn't falsely sign the merchant out.
        is_auth = getattr(e, "status_code", None) in (401, 403)
        await db.update(
            "pos_connections",
            {"status": "error", "last_error": str(e)[:500], "updated_at": now}
            if is_auth else {"last_error": str(e)[:500], "updated_at": now},
            filters={"id": f"eq.{conn_id}"},
        )
        if is_auth:
            await db.update("businesses", {"pos_connected": False}, filters={"id": f"eq.{org_id}"})
            await db.update(
                "organizations",
                {"pos_connection_status": "error"},
                filters={"id": f"eq.{org_id}"},
            )
            # A revoked grant cannot be recovered by retrying — only the merchant
            # re-authorising fixes it. Tell them, once, rather than letting their
            # data quietly go stale. Guarded on the previous status so the
            # 15-minute sweep can't mail them every quarter hour.
            if was_connected:
                await _notify_reconnect_required(db, org_id, provider, conn_id)
        raise


async def _notify_reconnect_required(db, org_id: str, provider: str, conn_id: str) -> None:
    """Email the merchant that their POS grant died and needs re-authorising.

    Never raises: this runs inside the sync failure path, and a missing address
    or a bounced send must not mask the underlying sync error being re-raised.
    """
    try:
        orgs = await db.select(
            "organizations",
            columns="id,name,email",
            filters={"id": f"eq.{org_id}"},
            limit=1,
        )
        org = (orgs or [{}])[0]
        to = (org.get("email") or "").strip()
        if not to:
            logger.warning(
                "POS reconnect needed for org=%s (%s) but the org has no email on file — "
                "connection %s will stay dark until someone reconnects it by hand",
                org_id, provider, conn_id,
            )
            return

        from ..email.send import send_pos_reconnect_required

        await send_pos_reconnect_required(
            to,
            first_name=(org.get("name") or "there").split()[0],
            pos_name=provider.capitalize(),
            location_name=org.get("name") or "your location",
            org_id=org_id,
        )
        logger.info("Sent POS reconnect email for org=%s provider=%s", org_id, provider)
    except Exception as e:
        logger.error("Could not send POS reconnect email for org=%s: %s", org_id, e, exc_info=True)


async def _sync_square(org_id, conn_id, connection, since):
    token = decrypt_token(connection.get("access_token_enc", ""))
    from ..square.client import SquareClient
    from ..square.sync_engine import SyncEngine

    async with SquareClient(access_token=token) as client:
        engine = SyncEngine(client=client, org_id=org_id, pos_connection_id=conn_id)
        return await engine.run_incremental_sync(since=since)


async def _sync_clover(org_id, conn_id, connection, since):
    from ..clover.oauth import ensure_fresh_clover_token
    # Clover v2 access tokens expire in ~30 min — refresh inline before syncing.
    token = await ensure_fresh_clover_token(connection)
    merchant_id = connection.get("external_merchant_id", "")
    from ..clover.client import CloverClient
    from ..clover.sync_engine import CloverSyncEngine

    client = CloverClient(access_token=token, merchant_id=merchant_id)
    engine = CloverSyncEngine(client=client, org_id=org_id, pos_connection_id=conn_id)
    return await engine.run_incremental_sync(since=since)


async def _sync_toast(org_id, conn_id, connection, since):
    creds = connection.get("credentials_encrypted", {})
    decrypted = {k: decrypt_token(v) for k, v in creds.items()}
    from ..toast.client import ToastClient
    from ..toast.sync_engine import ToastSyncEngine

    async with ToastClient(
        client_id=decrypted.get("client_id", ""),
        client_secret=decrypted.get("client_secret", ""),
        restaurant_guid=decrypted.get("restaurant_guid", ""),
    ) as client:
        engine = ToastSyncEngine(client=client, org_id=org_id, pos_connection_id=conn_id)
        return await engine.run_incremental_sync(since=since)


async def stripe_pos_credentials(connection: dict) -> tuple[str, str]:
    """(api_key, account_id) for a Stripe POS connection.

    App-OAuth connections (refresh_token_enc present — every connection made
    since the Stripe App replaced Connect `read_only`, see registry.py) use
    the short-lived app access token bare, refreshed inline via
    stripe_pos.tokens (1h expiry, rolling refresh token — the Clover
    ensure-fresh pattern). Raises StripePOSAPIError(401) on a dead grant so
    the runner flips the connection to reconnect.

    Legacy Connect-OAuth rows (no refresh token stored): platform secret key +
    Stripe-Account header; fallback when the env is unset: the stored
    per-account access_token used bare.
    """
    import os
    if connection.get("refresh_token_enc"):
        from ..stripe_pos.tokens import ensure_fresh_access_token
        return await ensure_fresh_access_token(connection), ""
    account_id = connection.get("external_merchant_id", "") or ""
    platform_key = os.environ.get("STRIPE_POS_CLIENT_SECRET", "")
    if platform_key and account_id.startswith("acct_"):
        return platform_key, account_id
    return decrypt_token(connection.get("access_token_enc", "") or ""), ""


async def _sync_stripe(org_id, conn_id, connection, since):
    from ..stripe_pos.client import StripePOSClient
    from ..stripe_pos.sync_engine import StripePOSSyncEngine

    api_key, account_id = await stripe_pos_credentials(connection)
    async with StripePOSClient(api_key=api_key, account_id=account_id) as client:
        engine = StripePOSSyncEngine(client=client, org_id=org_id, pos_connection_id=conn_id)
        return await engine.run_incremental_sync(since=since)


async def _sync_generic(org_id, conn_id, connection, provider, since):
    from ..services.pos_connectors import (
        GenericRESTConnector, POSConnectionConfig, get_connector_config, normalize_transaction,
    )
    from ..db import get_db

    api_config = get_connector_config(provider)
    if not api_config or api_config.get("auth_type") == "csv_only":
        logger.debug(f"No sync engine for provider: {provider} (CSV-only or unknown)")
        return None

    db = get_db()
    creds = connection.get("credentials_encrypted", {})
    decrypted = {k: decrypt_token(v) for k, v in creds.items()}

    conn_config = POSConnectionConfig(
        system_key=provider,
        system_name=provider.replace("-", " ").title(),
        tier=api_config.get("tier", 3),
        auth_method=api_config.get("auth_type", "bearer"),
        base_url=api_config.get("base_url", ""),
        credentials=decrypted,
        merchant_id=connection.get("external_merchant_id", ""),
        org_id=org_id,
    )
    connector = GenericRESTConnector(conn_config, api_config)
    sync_result = await connector.run_sync(since=since)

    normalized = [
        normalize_transaction(t, provider, org_id=org_id)
        for t in sync_result.transactions
    ]
    if normalized:
        await db.batch_upsert("transactions", normalized, on_conflict="org_id,external_id")

    if sync_result.catalog_items:
        await db.batch_upsert("products", [
            {"org_id": org_id, "source_system": provider, **item}
            for item in sync_result.catalog_items
        ], on_conflict="org_id,external_id")

    await db.update(
        "pos_connections",
        {
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
            "last_error": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        filters={"id": f"eq.{conn_id}"},
    )

    logger.info(f"Generic sync {org_id}/{provider}: {sync_result.records_fetched} records, {len(sync_result.errors)} errors")

    class _Result:
        transactions = normalized
        transaction_items = []
        summary = f"{sync_result.records_fetched} records via GenericREST"

    return _Result()
