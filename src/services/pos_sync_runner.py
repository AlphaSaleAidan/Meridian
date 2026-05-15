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


async def run_incremental(org_id: str, provider: str, connection: dict):
    """Run an incremental sync for a single POS connection."""
    from ..db import get_db
    db = get_db()

    conn_id = connection["id"]
    since = connection.get("last_sync_at")

    try:
        if provider == "square":
            result = await _sync_square(org_id, conn_id, connection, since)
        elif provider == "clover":
            result = await _sync_clover(org_id, conn_id, connection, since)
        elif provider == "toast":
            result = await _sync_toast(org_id, conn_id, connection, since)
        else:
            result = await _sync_generic(org_id, conn_id, connection, provider, since)
            if result is None:
                return

        if result.transactions:
            await db.batch_upsert("transactions", result.transactions, on_conflict="org_id,external_id")
        if result.transaction_items:
            await db.batch_upsert("transaction_items", result.transaction_items, on_conflict="id,transaction_at")

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
        await db.update(
            "pos_connections",
            {"last_error": str(e)[:500]},
            filters={"id": f"eq.{conn_id}"},
        )
        raise


async def _sync_square(org_id, conn_id, connection, since):
    token = decrypt_token(connection.get("access_token_encrypted", ""))
    from ..square.client import SquareClient
    from ..square.sync_engine import SyncEngine

    async with SquareClient(access_token=token) as client:
        engine = SyncEngine(client=client, org_id=org_id, pos_connection_id=conn_id)
        return await engine.run_incremental_sync(since=since)


async def _sync_clover(org_id, conn_id, connection, since):
    token = decrypt_token(connection.get("access_token_encrypted", ""))
    merchant_id = connection.get("merchant_id", "")
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
        merchant_id=connection.get("merchant_id", ""),
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
