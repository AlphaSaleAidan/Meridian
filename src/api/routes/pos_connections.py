"""
POS Connection Management — test, connect, status, disconnect, sync.

Handles credential-based POS systems (Toast, TouchBistro, Revel, etc.)
where the merchant enters API keys directly rather than going through OAuth.

OAuth-based systems (Square, Clover) use their own /api/square/ and
/api/clover/ routes for the authorization flow, then share the same
connection status and sync infrastructure here.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ...security.encryption import encrypt_token, decrypt_token
from ...services.pos_connectors import (
    GenericRESTConnector,
    POSConnectionConfig,
    get_connector_config,
    normalize_transaction,
)

logger = logging.getLogger("meridian.api.pos_connections")

router = APIRouter(prefix="/api/pos", tags=["pos-connections"])


class TestConnectionRequest(BaseModel):
    pos_system: str
    credentials: dict


class ConnectRequest(BaseModel):
    org_id: str
    pos_system: str
    credentials: dict
    restaurant_guid: Optional[str] = None


class DisconnectRequest(BaseModel):
    org_id: str
    pos_system: str


# ─── Test Connection ─────────────────────────────────────────

@router.post("/test-connection")
async def test_connection(req: TestConnectionRequest):
    """Validate POS credentials without saving. Returns success + business info."""
    if req.pos_system == "toast":
        return await _test_toast(req.credentials)
    if req.pos_system == "square":
        return await _test_square(req.credentials)
    if req.pos_system == "clover":
        return await _test_clover(req.credentials)

    api_config = get_connector_config(req.pos_system)
    if api_config and api_config.get("auth_type") != "csv_only":
        conn_config = POSConnectionConfig(
            system_key=req.pos_system,
            system_name=req.pos_system.replace("-", " ").title(),
            tier=3,
            auth_method=api_config.get("auth_type", "bearer"),
            base_url=api_config.get("base_url", ""),
            credentials=req.credentials,
        )
        connector = GenericRESTConnector(conn_config, api_config)
        return await connector.test_connection()

    return {
        "success": False,
        "message": f"Connection testing not yet available for {req.pos_system}. "
                   "Your credentials will be securely stored for when it launches.",
    }


async def _test_toast(credentials: dict) -> dict:
    client_id = credentials.get("client_id", "")
    client_secret = credentials.get("client_secret", "")
    restaurant_guid = credentials.get("restaurant_guid", "")

    if not all([client_id, client_secret, restaurant_guid]):
        return {
            "success": False,
            "message": "All three fields are required: Client ID, Client Secret, and Restaurant GUID.",
        }

    try:
        from ...toast.client import ToastClient
        async with ToastClient(client_id, client_secret, restaurant_guid) as client:
            info = await client.get_restaurant_info()
            if not info:
                return {
                    "success": False,
                    "message": "Authentication succeeded but could not read restaurant data. "
                               "Check that your Restaurant GUID is correct.",
                }
            return {
                "success": True,
                "message": "Connected to Toast successfully.",
                "details": {
                    "restaurant_name": info.get("general", {}).get("name"),
                    "guid": info.get("guid"),
                },
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Toast connection failed: {e}",
            "help": "Double-check your Client ID, Client Secret, and Restaurant GUID.",
        }


async def _test_square(credentials: dict) -> dict:
    access_token = credentials.get("access_token", "")
    if not access_token:
        return {"success": False, "message": "Access token required."}

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.get(
                "https://connect.squareup.com/v2/merchants/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Square-Version": "2024-01-18",
                },
            )
        if resp.status_code != 200:
            return {"success": False, "message": "Square rejected the credentials."}
        data = resp.json()
        merchant = data.get("merchant", {})
        return {
            "success": True,
            "message": "Connected to Square.",
            "details": {"business_name": merchant.get("business_name")},
        }
    except Exception as e:
        return {"success": False, "message": f"Square test failed: {e}"}


async def _test_clover(credentials: dict) -> dict:
    access_token = credentials.get("access_token", "")
    merchant_id = credentials.get("merchant_id", "")
    if not all([access_token, merchant_id]):
        return {"success": False, "message": "Access token and Merchant ID required."}

    try:
        from ...clover.oauth import CloverOAuthManager
        oauth = CloverOAuthManager()
        is_valid = await oauth.verify_token(access_token, merchant_id)
        if is_valid:
            return {"success": True, "message": "Connected to Clover."}
        return {"success": False, "message": "Clover rejected the credentials."}
    except Exception as e:
        return {"success": False, "message": f"Clover test failed: {e}"}


# ─── Connect (save credentials + start sync) ────────────────

@router.post("/connect")
async def connect_pos(req: ConnectRequest, background_tasks: BackgroundTasks):
    """Encrypt and store POS credentials, then trigger initial backfill."""
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(503, "Database not available")

    encrypted_creds = {
        key: encrypt_token(value)
        for key, value in req.credentials.items()
        if value
    }

    connection_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    existing = await db.select(
        "pos_connections",
        filters={
            "org_id": f"eq.{req.org_id}",
            "provider": f"eq.{req.pos_system}",
        },
        limit=1,
    )

    if existing:
        connection_id = existing[0]["id"]
        await db.update(
            "pos_connections",
            {
                "status": "connected",
                "credentials_encrypted": encrypted_creds,
                "last_error": None,
                "updated_at": now,
            },
            filters={"id": f"eq.{connection_id}"},
        )
    else:
        await db.insert("pos_connections", {
            "id": connection_id,
            "org_id": req.org_id,
            "provider": req.pos_system,
            "status": "connected",
            "credentials_encrypted": encrypted_creds,
            "merchant_id": req.restaurant_guid or req.credentials.get("merchant_id", ""),
            "historical_import_complete": False,
            "created_at": now,
            "updated_at": now,
        })

    await db.table("organizations").update({
        "pos_system": req.pos_system,
        "pos_connection_status": "connected",
    }).eq("id", req.org_id).execute()

    if req.pos_system == "toast":
        background_tasks.add_task(
            _run_toast_backfill,
            org_id=req.org_id,
            connection_id=connection_id,
            credentials=req.credentials,
        )

    return {
        "success": True,
        "connection_id": connection_id,
        "message": f"{req.pos_system.title()} connected. Initial data sync started.",
        "syncing": True,
    }


async def _run_toast_backfill(org_id: str, connection_id: str, credentials: dict):
    """Background task: run Toast initial backfill."""
    from ...toast.client import ToastClient
    from ...toast.sync_engine import ToastSyncEngine
    from ...db import get_db

    db = get_db()

    try:
        async with ToastClient(
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
            restaurant_guid=credentials["restaurant_guid"],
        ) as client:
            engine = ToastSyncEngine(
                client=client,
                org_id=org_id,
                pos_connection_id=connection_id,
            )
            result = await engine.run_initial_backfill()

        if result.products:
            await db.batch_upsert("products", result.products, on_conflict="org_id,external_id")
        if result.transactions:
            await db.batch_upsert("transactions", result.transactions, on_conflict="org_id,external_id")
        if result.transaction_items:
            await db.batch_upsert("transaction_items", result.transaction_items, on_conflict="id,transaction_at")

        await db.update(
            "pos_connections",
            {
                "historical_import_complete": True,
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            filters={"id": f"eq.{connection_id}"},
        )
        logger.info(f"Toast backfill complete for org={org_id}: {result.summary}")

        try:
            from ...pipeline import MeridianPipeline
            import os
            pipeline = MeridianPipeline(
                org_id=org_id,
                square_token="",
                supabase_url=os.environ.get("SUPABASE_URL", ""),
                supabase_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
                    or os.environ.get("SUPABASE_SERVICE_KEY", ""),
                pos_connection_id=connection_id,
            )
            await pipeline.run_full_sync()
        except Exception as e:
            logger.warning(f"AI pipeline after Toast backfill failed: {e}")

    except Exception as e:
        logger.error(f"Toast backfill failed for org={org_id}: {e}", exc_info=True)
        await db.update(
            "pos_connections",
            {"status": "error", "last_error": str(e)[:500]},
            filters={"id": f"eq.{connection_id}"},
        )


# ─── Connection Status ──────────────────────────────────────

@router.get("/connections/{org_id}")
async def get_connections(org_id: str):
    """List all POS connections for an organization."""
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(503, "Database not available")

    connections = await db.select(
        "pos_connections",
        filters={"org_id": f"eq.{org_id}"},
    )

    result = []
    for conn in connections or []:
        result.append({
            "id": conn["id"],
            "provider": conn.get("provider"),
            "status": conn.get("status"),
            "merchant_id": conn.get("merchant_id"),
            "last_sync_at": conn.get("last_sync_at"),
            "historical_import_complete": conn.get("historical_import_complete", False),
            "last_error": conn.get("last_error"),
            "created_at": conn.get("created_at"),
        })

    return {"connections": result}


# ─── Disconnect ──────────────────────────────────────────────

@router.post("/disconnect")
async def disconnect_pos(req: DisconnectRequest):
    """Disconnect a POS system and revoke tokens if applicable."""
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(503, "Database not available")

    connections = await db.select(
        "pos_connections",
        filters={
            "org_id": f"eq.{req.org_id}",
            "provider": f"eq.{req.pos_system}",
        },
        limit=1,
    )

    if not connections:
        raise HTTPException(404, f"No {req.pos_system} connection found")

    conn = connections[0]

    if req.pos_system == "square" and conn.get("access_token_encrypted"):
        try:
            token = decrypt_token(conn["access_token_encrypted"])
            from ...square.oauth import OAuthManager
            await OAuthManager().revoke_token(token)
        except Exception as e:
            logger.warning(f"Square token revocation failed: {e}")

    await db.update(
        "pos_connections",
        {"status": "disconnected", "updated_at": datetime.now(timezone.utc).isoformat()},
        filters={"id": f"eq.{conn['id']}"},
    )

    await db.table("organizations").update({
        "pos_connection_status": None,
    }).eq("id", req.org_id).execute()

    return {"success": True, "message": f"{req.pos_system.title()} disconnected."}


# ─── Manual Sync Trigger ────────────────────────────────────

@router.post("/sync/{org_id}/{pos_system}")
async def trigger_sync(org_id: str, pos_system: str, background_tasks: BackgroundTasks):
    """Manually trigger an incremental sync for a connection."""
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(503, "Database not available")

    connections = await db.select(
        "pos_connections",
        filters={
            "org_id": f"eq.{org_id}",
            "provider": f"eq.{pos_system}",
            "status": "eq.connected",
        },
        limit=1,
    )

    if not connections:
        raise HTTPException(404, f"No active {pos_system} connection found")

    conn = connections[0]
    background_tasks.add_task(
        _run_incremental_sync,
        org_id=org_id,
        pos_system=pos_system,
        connection=conn,
    )

    return {"success": True, "message": "Sync started."}


async def _run_incremental_sync(org_id: str, pos_system: str, connection: dict):
    """Background task: run incremental sync for any POS."""
    from ...db import get_db
    db = get_db()

    try:
        since = connection.get("last_sync_at")

        if pos_system == "square":
            token = decrypt_token(connection.get("access_token_encrypted", ""))
            from ...square.client import SquareClient
            async with SquareClient(access_token=token) as client:
                from ...square.sync_engine import SyncEngine
                engine = SyncEngine(client=client, org_id=org_id, pos_connection_id=connection["id"])
                result = await engine.run_incremental_sync(since=since)

        elif pos_system == "clover":
            token = decrypt_token(connection.get("access_token_encrypted", ""))
            merchant_id = connection.get("merchant_id", "")
            from ...clover.client import CloverClient
            client = CloverClient(access_token=token, merchant_id=merchant_id)
            from ...clover.sync_engine import CloverSyncEngine
            engine = CloverSyncEngine(client=client, org_id=org_id, pos_connection_id=connection["id"])
            result = await engine.run_incremental_sync(since=since)

        elif pos_system == "toast":
            creds = connection.get("credentials_encrypted", {})
            decrypted = {k: decrypt_token(v) for k, v in creds.items()}
            from ...toast.client import ToastClient
            async with ToastClient(
                client_id=decrypted.get("client_id", ""),
                client_secret=decrypted.get("client_secret", ""),
                restaurant_guid=decrypted.get("restaurant_guid", ""),
            ) as client:
                from ...toast.sync_engine import ToastSyncEngine
                engine = ToastSyncEngine(client=client, org_id=org_id, pos_connection_id=connection["id"])
                result = await engine.run_incremental_sync(since=since)
        else:
            api_config = get_connector_config(pos_system)
            if not api_config or api_config.get("auth_type") == "csv_only":
                logger.info(f"No incremental sync for {pos_system} (CSV-only)")
                return

            creds = connection.get("credentials_encrypted", {})
            decrypted = {k: decrypt_token(v) for k, v in creds.items()}
            conn_config = POSConnectionConfig(
                system_key=pos_system,
                system_name=pos_system.replace("-", " ").title(),
                tier=3,
                auth_method=api_config.get("auth_type", "bearer"),
                base_url=api_config.get("base_url", ""),
                credentials=decrypted,
                merchant_id=connection.get("merchant_id", ""),
            )
            connector = GenericRESTConnector(conn_config, api_config)
            sync_result = await connector.run_sync(since=since)

            result_transactions = [
                normalize_transaction(t, pos_system, org_id=org_id)
                for t in sync_result.transactions
            ]
            if result_transactions:
                await db.batch_upsert("transactions", result_transactions, on_conflict="org_id,external_id")

            await db.update(
                "pos_connections",
                {
                    "last_sync_at": datetime.now(timezone.utc).isoformat(),
                    "last_error": None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                filters={"id": f"eq.{connection['id']}"},
            )
            logger.info(f"Generic sync complete for {org_id}/{pos_system}: {sync_result.records_fetched} records")
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
            filters={"id": f"eq.{connection['id']}"},
        )
        logger.info(f"Incremental sync complete for {org_id}/{pos_system}: {result.summary}")

    except Exception as e:
        logger.error(f"Incremental sync failed for {org_id}/{pos_system}: {e}", exc_info=True)
        await db.update(
            "pos_connections",
            {"last_error": str(e)[:500]},
            filters={"id": f"eq.{connection['id']}"},
        )
