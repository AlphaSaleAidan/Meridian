"""
POS Connection Management — test, connect, status, disconnect, sync.

Handles credential-based POS systems (Toast, TouchBistro, Revel, etc.)
where the merchant enters API keys directly rather than going through OAuth.

OAuth-based systems (Square, Clover) use their own /api/square/ and
/api/clover/ routes for the authorization flow, then share the same
connection status and sync infrastructure here.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel

from ..auth import require_org_access, require_jwt, require_org_member
from ...config import clover as cl_config
from ...security.encryption import encrypt_token, decrypt_token
from ...services.pos_connectors import (
    GenericRESTConnector,
    POSConnectionConfig,
    get_connector_config,
    normalize_transaction,
    import_csv_for_system,
)

logger = logging.getLogger("meridian.api.pos_connections")

# Router-level tenancy guard: every endpoint that accepts org_id in query OR path
# is automatically protected. POST endpoints that pass org_id in body (e.g.
# /connect, /test-connection, /upload-csv) must enforce internally (P1 follow-up).
router = APIRouter(
    prefix="/api/pos",
    tags=["pos-connections"],
    dependencies=[Depends(require_org_access)],
)


def _atomic_write_enabled() -> bool:
    return os.environ.get("POS_ATOMIC_WRITE", "").lower() in ("1", "true", "yes")


async def _write_sync_result(db, result) -> None:
    """Persist a SyncResult's products + transactions + transaction_items.

    The single write path for every backfill/incremental caller (replaces three
    copy-pasted blocks). Idempotent via deterministic ids, so it's safe to retry.

    - POS_ATOMIC_WRITE=1 and the DB exposes the `pos_sync_upsert` RPC → the three
      tables are written in ONE transaction (all-or-nothing). Falls back to the
      sequential path if the RPC errors.
    - Otherwise → sequential upserts in FK-safe order (products → transactions →
      transaction_items). A partial failure self-heals on the next (idempotent) sync.
    """
    products = list(getattr(result, "products", None) or [])
    transactions = list(getattr(result, "transactions", None) or [])
    items = list(getattr(result, "transaction_items", None) or [])
    if not (products or transactions or items):
        return

    if _atomic_write_enabled() and hasattr(db, "rpc"):
        try:
            await db.rpc("pos_sync_upsert", {
                "_products": products,
                "_transactions": transactions,
                "_transaction_items": items,
            })
            return
        except Exception as e:
            logger.warning(f"atomic pos_sync_upsert failed; falling back to sequential: {e}")

    if products:
        await db.batch_upsert("products", products, on_conflict="org_id,external_id")
    if transactions:
        await db.batch_upsert("transactions", transactions, on_conflict="org_id,external_id")
    if items:
        await db.batch_upsert("transaction_items", items, on_conflict="id,transaction_at")


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


async def _square_merchant_and_vertical(access_token: str) -> tuple[dict, str]:
    """Fetch the Square merchant profile + detect a business vertical, via
    SquareClient so it honors the configured Square environment (sandbox vs
    prod) and the current Square-Version. Shared by test-connection and connect
    so both always speak to the same Square. Returns (merchant, vertical)."""
    from ...square.client import SquareClient
    async with SquareClient(access_token=access_token) as client:
        merchant = await client.get_merchant("me")
        vertical = _detect_business_type_from_square(merchant)
        locations = await client.list_locations()
        if locations:
            mcc = locations[0].get("mcc", "")
            if mcc:
                vertical = _mcc_to_business_type(mcc) or vertical
    return merchant, vertical


async def _test_square(credentials: dict) -> dict:
    access_token = credentials.get("access_token", "")
    if not access_token:
        return {"success": False, "message": "Access token required."}

    try:
        merchant, detected_type = await _square_merchant_and_vertical(access_token)
        return {
            "success": True,
            "message": "Connected to Square.",
            "details": {
                "business_name": merchant.get("business_name"),
                "detected_business_type": detected_type,
            },
        }
    except Exception as e:
        return {"success": False, "message": f"Square test failed: {e}"}


def _mcc_to_business_type(mcc: str) -> str | None:
    """Map Square MCC (Merchant Category Code) to a Meridian business type."""
    mcc_map = {
        "5812": "restaurant", "5813": "restaurant", "5814": "fast_food",
        "5811": "restaurant",
        "5462": "coffee_shop", "5441": "coffee_shop",
        "7531": "auto_shop", "7534": "auto_shop", "7538": "auto_shop", "7542": "auto_shop",
        "5993": "smoke_shop", "5194": "smoke_shop",
    }
    return mcc_map.get(mcc)


def _detect_business_type_from_square(merchant: dict) -> str:
    """Heuristic: detect business type from Square merchant name/data."""
    name = (merchant.get("business_name") or "").lower()
    if any(w in name for w in ("coffee", "cafe", "café", "tea", "bakery", "espresso")):
        return "coffee_shop"
    if any(w in name for w in ("pizza", "burger", "taco", "sub", "wing", "chicken", "fries")):
        return "fast_food"
    if any(w in name for w in ("auto", "tire", "mechanic", "lube", "garage", "oil change")):
        return "auto_shop"
    if any(w in name for w in ("smoke", "vape", "tobacco", "cigar")):
        return "smoke_shop"
    if any(w in name for w in ("restaurant", "grill", "bistro", "diner", "bar", "kitchen", "eatery")):
        return "restaurant"
    return "restaurant"


def _canonical_clover_creds(credentials: dict) -> dict:
    """Map UI field IDs (clover_api_token, clover_merchant_id) to the canonical
    access_token / merchant_id keys the Clover client + sync engine expect.

    The OAuth path already supplies canonical keys; this only fills the gaps for
    the manual key/ID paste form, whose fields are namespaced (clover_*)."""
    creds = dict(credentials)
    if not creds.get("access_token"):
        token = creds.get("clover_api_token") or creds.get("clover_access_token")
        if token:
            creds["access_token"] = token
    if not creds.get("merchant_id"):
        mid = creds.get("clover_merchant_id")
        if mid:
            creds["merchant_id"] = mid
    return creds


async def _test_clover(credentials: dict) -> dict:
    # Coherent gate: mirror the OAuth/connect behavior. If Clover isn't enabled
    # on this server, fail gracefully instead of attempting a live call.
    if not cl_config.is_enabled:
        return {
            "success": False,
            "message": "Clover isn't enabled on this server yet.",
        }
    credentials = _canonical_clover_creds(credentials)
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
async def connect_pos(
    req: ConnectRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_jwt),
):
    """Encrypt and store POS credentials, then trigger initial backfill."""
    # Tenancy: the router guard only sees query/path org_id; this endpoint takes
    # org_id in the body, so enforce membership explicitly (closes CA-1/CA-2).
    await require_org_member(user, req.org_id)

    from ...db import _db_instance as db
    if not db:
        raise HTTPException(503, "Database not available")

    if req.pos_system == "clover":
        # Coherent gate: manual /connect must honor the same enablement check as
        # the OAuth /authorize path (which 503s when unconfigured). Without this
        # the manual paste path was wide open while OAuth was gated.
        if not cl_config.is_enabled:
            raise HTTPException(
                503,
                "Clover isn't enabled on this server yet. Set POS_CLOVER_ENABLED=true "
                "or configure Clover credentials.",
            )
        req.credentials = _canonical_clover_creds(req.credentials)

    encrypted_creds = {}
    for key, value in req.credentials.items():
        if not value:
            continue
        encrypted = encrypt_token(value)
        if not encrypted:
            raise HTTPException(500, f"Failed to encrypt credential '{key}' — check encryption config")
        encrypted_creds[key] = encrypted

    connection_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Clover and Square are read by the incremental scheduler from the dedicated
    # access_token_enc column (pos_sync_runner decrypts access_token_enc), while
    # manual connect stores creds in credentials_encrypted — mirror the token
    # into both so the scheduler resolves it identically to the OAuth path.
    # Without this, a manually-keyed Square/Clover connection would sync the
    # initial backfill but then silently stop (incremental decrypts "").
    token_column: dict = {}
    if req.pos_system in ("clover", "square") and encrypted_creds.get("access_token"):
        token_column["access_token_enc"] = encrypted_creds["access_token"]

    # Ensure the organizations row exists BEFORE any pos_connections write —
    # pos_connections.org_id FKs to organizations.id. Customers live in the
    # `businesses` table, so the parallel organizations row is often missing and
    # the insert below would hit pos_connections_org_id_fkey (409 23503), failing
    # the whole connect. Create it with the NOT-NULL `vertical` (refined to the
    # detected business type by the organizations update further down).
    existing_org = await db.select(
        "organizations", filters={"id": f"eq.{req.org_id}"}, limit=1,
    )
    if not existing_org:
        await db.insert("organizations", {
            "id": req.org_id,
            "name": f"Org {req.org_id}",
            "slug": req.org_id.lower().replace(" ", "-"),
            "vertical": "other",
            "created_at": now,
            "updated_at": now,
        })
        logger.info(f"Created organizations row for {req.org_id} (pos/connect)")

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
                # Reconnect kicks off a fresh backfill below, so the logical
                # state is PENDING (connected + import-incomplete) until it
                # finishes — not the prior connection's COMPLETE.
                "historical_import_complete": False,
                "updated_at": now,
                **token_column,
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
            "external_merchant_id": req.restaurant_guid or req.credentials.get("merchant_id", ""),
            "historical_import_complete": False,
            "created_at": now,
            "updated_at": now,
            **token_column,
        })

    org_update = {
        "pos_system": req.pos_system,
        "pos_connection_status": "connected",
    }

    if req.pos_system == "square":
        token = req.credentials.get("access_token", "")
        if token:
            try:
                _, org_update["vertical"] = await _square_merchant_and_vertical(token)
            except Exception as e:
                logger.warning(f"Square business type detection failed: {e}")

    await db.update("organizations", org_update, filters={"id": f"eq.{req.org_id}"})
    # Open BOTH halves of the dashboard gate. businesses.pos_connected is the
    # primary gate; businesses-based customers have no pos_connection_status
    # column to fall back on. Mirrors the OAuth callback path and is symmetric
    # with disconnect.
    await db.update("businesses", {"pos_connected": True}, filters={"id": f"eq.{req.org_id}"})

    if req.pos_system == "toast":
        background_tasks.add_task(
            _run_toast_backfill,
            org_id=req.org_id,
            connection_id=connection_id,
            credentials=req.credentials,
        )
    elif req.pos_system == "clover":
        background_tasks.add_task(
            _run_clover_backfill,
            org_id=req.org_id,
            connection_id=connection_id,
            access_token=req.credentials.get("access_token", ""),
            merchant_id=(req.credentials.get("merchant_id", "") or req.restaurant_guid or ""),
        )
    elif req.pos_system == "square":
        # Square normally connects via OAuth (the callback dispatches this same
        # run_backfill). A user-pasted access token lands here instead, so run
        # the identical initial backfill so the lifecycle advances PENDING →
        # COMPLETE (or → FAILED on a bad token) and the connection becomes
        # eligible for incremental sync — rather than sitting PENDING forever.
        # Guard on a present token so an empty manual paste doesn't kick a
        # backfill that would only fail.
        token = req.credentials.get("access_token", "")
        if token:
            from ...workers.backfill import run_backfill
            background_tasks.add_task(
                run_backfill,
                access_token=token,
                org_id=req.org_id,
                connection_id=connection_id,
            )
    else:
        api_config = get_connector_config(req.pos_system)
        if api_config and api_config.get("auth_type") != "csv_only":
            background_tasks.add_task(
                _run_generic_backfill,
                org_id=req.org_id,
                connection_id=connection_id,
                pos_system=req.pos_system,
                credentials=req.credentials,
            )

    # Auto-build the phone agent's menu from the freshly-connected POS catalog
    # (read-only). Best-effort + non-blocking: it shares the manual sync's
    # extraction path and never affects this connect response. The customer
    # account polls GET /api/phone/menu/status to watch it populate.
    background_tasks.add_task(_auto_build_phone_menu, req.org_id)

    return {
        "success": True,
        "connection_id": connection_id,
        "message": f"{req.pos_system.title()} connected. Initial data sync started.",
        "syncing": True,
    }


async def _auto_build_phone_menu(org_id: str) -> None:
    """Background task: kick the phone-agent menu build for a connected merchant.

    merchant_id IS the org_id in this system. Delegates to the phone dashboard's
    shared extraction helper so manual sync and auto-build run identical code.
    Never raises — a menu-build failure must not affect POS connect/sync.
    """
    try:
        from .phone_dashboard import auto_build_menu_on_connect
        await auto_build_menu_on_connect(org_id)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Auto menu-build dispatch failed for org={org_id}: {e}")


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

        await _write_sync_result(db, result)

        await _import_pos_staff(db, org_id, result.employee_cache)

        await db.update(
            "pos_connections",
            {
                "historical_import_complete": True,
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                # Clear any prior failure so a successful retry leaves COMPLETE,
                # not a stale FAILED (status=error) state.
                "status": "connected",
                "last_error": None,
            },
            filters={"id": f"eq.{connection_id}"},
        )
        logger.info(f"Toast backfill complete for org={org_id}: {result.summary}")

        try:
            from ...live_pipeline import MeridianPipeline
            import os
            pipeline = MeridianPipeline(
                org_id=org_id,
                square_token="",
                supabase_url=os.environ.get("SUPABASE_URL", ""),
                supabase_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
                    or os.environ.get("SUPABASE_SERVICE_KEY", ""),
                pos_connection_id=connection_id,
            )
            # Toast data is already in the DB via the sync engine above.
            # run_full_sync() would re-fetch from Square (no token here), so
            # run only the POS-agnostic analytics + portal phases.
            await pipeline.run_analysis_only()
        except Exception as e:
            logger.warning(f"AI pipeline after Toast backfill failed: {e}")

    except Exception as e:
        logger.error(f"Toast backfill failed for org={org_id}: {e}", exc_info=True)
        await db.update(
            "pos_connections",
            {"status": "error", "last_error": str(e)[:500]},
            filters={"id": f"eq.{connection_id}"},
        )


async def _import_pos_staff(db, org_id: str, employee_cache: dict[str, str]) -> int:
    """Best-effort: seed the schedule roster from the POS employee list.

    Idempotent by name — a re-sync skips employees already on the roster, so the
    merchant never gets duplicates. Never raises: the manual add-staff path in the
    Schedule tab is always available even if the POS has no employees or this fails.
    """
    if not employee_cache:
        return 0
    try:
        existing = await db.select("schedule_staff", filters={"merchant_id": f"eq.{org_id}"})
        have = {(r.get("name") or "").strip().lower() for r in existing}
        rows = []
        for name in employee_cache.values():
            clean = (name or "").strip()
            if not clean or clean.lower() in have:
                continue
            have.add(clean.lower())
            rows.append({
                "id": str(uuid4()),
                "merchant_id": org_id,
                "name": clean,
                "role": "any",
                "color": "#17C5B0",
                "hourly_rate": 0,
                "availability": {},
                "active": True,
            })
        if rows:
            await db.insert("schedule_staff", rows, return_data=False)
        logger.info(f"POS staff import for org={org_id}: {len(rows)} new of {len(employee_cache)} POS employees")
        return len(rows)
    except Exception as e:
        logger.warning(f"POS staff import failed for org={org_id}: {e}")
        return 0


async def _run_clover_backfill(org_id: str, connection_id: str, access_token: str, merchant_id: str):
    """Background task: run Clover initial backfill (manual-paste and OAuth share this)."""
    from ...clover.client import CloverClient
    from ...clover.sync_engine import CloverSyncEngine
    from ...db import get_db

    db = get_db()

    try:
        client = CloverClient(access_token=access_token, merchant_id=merchant_id)
        try:
            engine = CloverSyncEngine(
                client=client,
                org_id=org_id,
                pos_connection_id=connection_id,
            )
            result = await engine.run_initial_backfill()
        finally:
            await client.close()

        # run_initial_backfill never raises — it folds fatal exceptions into
        # result.errors ("fatal: ..."). Without this gate a dead backfill was
        # still marked historical_import_complete / status=connected (the
        # "connected, no data" bug fixed for Square in f0609688).
        fatal_errors = [err for err in (getattr(result, "errors", None) or []) if str(err).startswith("fatal:")]
        if fatal_errors:
            raise RuntimeError(fatal_errors[0])

        await _write_sync_result(db, result)

        await _import_pos_staff(db, org_id, result.employee_cache)

        await db.update(
            "pos_connections",
            {
                "historical_import_complete": True,
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                # Clear any prior failure so a successful retry leaves COMPLETE,
                # not a stale FAILED (status=error) state.
                "status": "connected",
                "last_error": None,
            },
            filters={"id": f"eq.{connection_id}"},
        )
        logger.info(f"Clover backfill complete for org={org_id}: {result.summary}")

        try:
            from ...live_pipeline import MeridianPipeline
            import os
            pipeline = MeridianPipeline(
                org_id=org_id,
                square_token="",
                supabase_url=os.environ.get("SUPABASE_URL", ""),
                supabase_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
                    or os.environ.get("SUPABASE_SERVICE_KEY", ""),
                pos_connection_id=connection_id,
            )
            # Clover data is already in the DB via the sync engine above.
            # run_full_sync() would re-fetch from Square (no token here), so
            # run only the POS-agnostic analytics + portal phases.
            await pipeline.run_analysis_only()
        except Exception as e:
            logger.warning(f"AI pipeline after Clover backfill failed: {e}")

    except Exception as e:
        logger.error(f"Clover backfill failed for org={org_id}: {e}", exc_info=True)
        try:
            await db.update(
                "pos_connections",
                {
                    "status": "error",
                    "last_error": str(e)[:500],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                filters={"id": f"eq.{connection_id}"},
            )
            # Revert the connected flags the dashboard gates on so the portal
            # prompts a reconnect (mirrors the Square fix in f0609688).
            await db.update("businesses", {"pos_connected": False}, filters={"id": f"eq.{org_id}"})
            await db.update("organizations", {"pos_connection_status": "error"}, filters={"id": f"eq.{org_id}"})
        except Exception as record_err:
            logger.error(f"Could not record Clover backfill failure for org={org_id}: {record_err}")


async def _run_generic_backfill(org_id: str, connection_id: str, pos_system: str, credentials: dict):
    """Background task: run initial backfill for any GenericREST POS system."""
    from ...db import get_db
    db = get_db()

    try:
        api_config = get_connector_config(pos_system)
        conn_config = POSConnectionConfig(
            system_key=pos_system,
            system_name=pos_system.replace("-", " ").title(),
            tier=api_config.get("tier", 3),
            auth_method=api_config.get("auth_type", "bearer"),
            base_url=api_config.get("base_url", ""),
            credentials=credentials,
            org_id=org_id,
        )
        connector = GenericRESTConnector(conn_config, api_config)
        sync_result = await connector.run_sync()

        normalized = [
            normalize_transaction(t, pos_system, org_id=org_id)
            for t in sync_result.transactions
        ]
        if normalized:
            await db.batch_upsert("transactions", normalized, on_conflict="org_id,external_id")

        if sync_result.catalog_items:
            await db.batch_upsert("products", [
                {"org_id": org_id, "source_system": pos_system, **item}
                for item in sync_result.catalog_items
            ], on_conflict="org_id,external_id")

        await db.update(
            "pos_connections",
            {
                "historical_import_complete": True,
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                # Clear any prior failure so a successful retry leaves COMPLETE,
                # not a stale FAILED (status=error) state.
                "status": "connected",
                "last_error": None,
            },
            filters={"id": f"eq.{connection_id}"},
        )
        logger.info(
            f"Generic backfill complete for {org_id}/{pos_system}: "
            f"{sync_result.records_fetched} records, {len(sync_result.errors)} errors"
        )

    except Exception as e:
        logger.error(f"Generic backfill failed for {org_id}/{pos_system}: {e}", exc_info=True)
        await db.update(
            "pos_connections",
            {"status": "error", "last_error": str(e)[:500]},
            filters={"id": f"eq.{connection_id}"},
        )


# ─── CSV Upload ──────────────────────────────────────────────

@router.post("/upload-csv")
async def upload_csv(
    background_tasks: BackgroundTasks,
    org_id: str = "",
    pos_system: str = "",
    file: bytes = b"",
    filename: str = "",
):
    """Upload a CSV/Excel export from a non-API POS system."""
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(503, "Database not available")

    api_config = get_connector_config(pos_system)
    if not api_config:
        raise HTTPException(400, f"Unknown POS system: {pos_system}")

    csv_columns = api_config.get("csv_columns", {})
    if not csv_columns:
        raise HTTPException(
            400,
            f"{pos_system} does not have CSV column mappings configured. "
            "Contact support to add this system.",
        )

    records, errors = import_csv_for_system(pos_system, csv_columns, file, filename)

    if not records:
        return {
            "success": False,
            "records_imported": 0,
            "errors": errors[:10],
            "message": "No valid records found. Check that the file matches the expected format.",
        }

    normalized = [
        normalize_transaction(r, pos_system, org_id=org_id)
        for r in records
    ]

    await db.batch_upsert("transactions", normalized, on_conflict="org_id,external_id")

    existing = await db.select(
        "pos_connections",
        filters={"org_id": f"eq.{org_id}", "provider": f"eq.{pos_system}"},
        limit=1,
    )
    now = datetime.now(timezone.utc).isoformat()
    if existing:
        await db.update("pos_connections", {
            "last_sync_at": now,
            "historical_import_complete": True,
            "updated_at": now,
        }, filters={"id": f"eq.{existing[0]['id']}"})
    else:
        await db.insert("pos_connections", {
            "id": str(uuid4()),
            "org_id": org_id,
            "provider": pos_system,
            "status": "connected",
            "external_merchant_id": "",
            "historical_import_complete": True,
            "last_sync_at": now,
            "created_at": now,
            "updated_at": now,
        })

    return {
        "success": True,
        "records_imported": len(normalized),
        "errors": errors[:10],
        "message": f"Imported {len(normalized)} transactions from {pos_system}.",
    }


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
        status = conn.get("status")
        import_complete = conn.get("historical_import_complete", False)
        result.append({
            "id": conn["id"],
            "provider": conn.get("provider"),
            "status": status,
            # Derived lifecycle state for the frontend (additive — the raw
            # status + historical_import_complete + last_error are unchanged):
            #   failed   = status=='error'
            #   complete = connected + import done
            #   pending  = connected + import in progress
            "state": _derive_connection_state(status, import_complete),
            "merchant_id": conn.get("external_merchant_id"),
            "last_sync_at": conn.get("last_sync_at"),
            "historical_import_complete": import_complete,
            "last_error": conn.get("last_error"),
            "created_at": conn.get("created_at"),
        })

    return {"connections": result}


def _derive_connection_state(status: str | None, historical_import_complete: bool) -> str:
    """Collapse (status, historical_import_complete) into a single lifecycle
    state for the frontend. Additive helper — does not change stored data.

      status=='error'                                  → 'failed'
      status=='connected' and import complete          → 'complete'
      status=='connected' and import incomplete        → 'pending'
      status=='disconnected' (or anything else)        → returns the raw status
    """
    if status == "error":
        return "failed"
    if status == "connected":
        return "complete" if historical_import_complete else "pending"
    return status or "unknown"


# ─── Disconnect ──────────────────────────────────────────────

async def teardown_connection(db, connection_id: str, org_id: str | None = None) -> None:
    """Fully tear down a POS connection so the dashboard gate can't stay half-open.

    The gate is `businesses.pos_connected OR organizations.pos_connection_status
    == 'connected'`, so a disconnect MUST close both. Also clears the stored token
    (don't leave a revoked merchant's token at rest) and resets the import flag so
    a future reconnect starts clean. Shared by the manual disconnect endpoint and
    the webhook auth-revoked path.
    """
    now = datetime.now(timezone.utc).isoformat()
    await db.update(
        "pos_connections",
        {
            "status": "disconnected",
            "access_token_enc": None,
            "credentials_encrypted": None,
            "historical_import_complete": False,
            "last_error": None,
            "updated_at": now,
        },
        filters={"id": f"eq.{connection_id}"},
    )

    if org_id is None:
        rows = await db.select("pos_connections", filters={"id": f"eq.{connection_id}"}, limit=1)
        org_id = rows[0].get("org_id") if rows else None
    if org_id:
        await db.update("businesses", {"pos_connected": False}, filters={"id": f"eq.{org_id}"})
        await db.update(
            "organizations",
            {"pos_connection_status": None, "pos_system": None},
            filters={"id": f"eq.{org_id}"},
        )


@router.post("/disconnect")
async def disconnect_pos(req: DisconnectRequest, user: dict = Depends(require_jwt)):
    """Disconnect a POS system and revoke tokens if applicable."""
    # Tenancy: org_id is in the body, so enforce membership explicitly.
    await require_org_member(user, req.org_id)

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

    if req.pos_system == "square" and conn.get("access_token_enc"):
        try:
            token = decrypt_token(conn["access_token_enc"])
            from ...square.oauth import OAuthManager
            await OAuthManager().revoke_token(token)
        except Exception as e:
            logger.warning(f"Square token revocation failed: {e}")

    # Fully tear down via the shared helper: drops the stored token, resets the
    # import flag, and closes BOTH halves of the dashboard gate (the gate is
    #   businesses.pos_connected OR organizations.pos_connection_status == 'connected'
    # — clearing only the org status left businesses.pos_connected true, so the
    # dashboard stayed unlocked with stale data after disconnect).
    await teardown_connection(db, conn["id"], req.org_id)

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
    # Refresh the phone-agent menu too (read-only, best-effort, non-blocking).
    background_tasks.add_task(_auto_build_phone_menu, org_id)

    return {"success": True, "message": "Sync started."}


async def _run_incremental_sync(org_id: str, pos_system: str, connection: dict):
    """Background task: run incremental sync for any POS."""
    from ...db import get_db
    db = get_db()

    try:
        since = connection.get("last_sync_at")

        if pos_system == "square":
            creds = connection.get("credentials_encrypted") or {}
            token = decrypt_token(creds.get("access_token", "") or connection.get("access_token_enc", ""))
            from ...square.client import SquareClient
            async with SquareClient(access_token=token) as client:
                from ...square.sync_engine import SyncEngine
                engine = SyncEngine(client=client, org_id=org_id, pos_connection_id=connection["id"])
                engine.db = db  # activate DB-backed product/location lookup load
                result = await engine.run_incremental_sync(since=since)

        elif pos_system == "clover":
            creds = connection.get("credentials_encrypted") or {}
            token = decrypt_token(creds.get("access_token", "") or connection.get("access_token_enc", ""))
            merchant_id = connection.get("external_merchant_id", "") or connection.get("merchant_id", "")
            from ...clover.client import CloverClient
            client = CloverClient(access_token=token, merchant_id=merchant_id)
            from ...clover.sync_engine import CloverSyncEngine
            engine = CloverSyncEngine(client=client, org_id=org_id, pos_connection_id=connection["id"])
            engine.db = db  # so incremental line items resolve product_id (not NULL)
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
                merchant_id=connection.get("external_merchant_id", ""),
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

        await _write_sync_result(db, result)

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

        # ── Reconcile against Square (read-only, best-effort) ──
        # Surface a sync gap in logs without failing the sync.
        if pos_system == "square":
            try:
                from ...services.reconcile import reconcile_square
                creds = connection.get("credentials_encrypted") or {}
                token = decrypt_token(
                    creds.get("access_token", "") or connection.get("access_token_enc", "")
                )
                from ...square.client import SquareClient
                async with SquareClient(access_token=token) as rc_client:
                    report = await reconcile_square(db, org_id, rc_client)
                logger.info(f"Reconcile after sync for org={org_id}: {report}")
            except Exception as e:
                logger.warning(f"Reconcile after sync failed for org={org_id}: {e}")

    except Exception as e:
        logger.error(f"Incremental sync failed for {org_id}/{pos_system}: {e}", exc_info=True)
        await db.update(
            "pos_connections",
            {"last_error": str(e)[:500]},
            filters={"id": f"eq.{connection['id']}"},
        )
