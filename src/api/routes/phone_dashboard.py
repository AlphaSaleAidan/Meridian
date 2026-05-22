"""
Phone Agent Dashboard API routes.

Endpoints for the frontend phone orders page:
  GET    /api/phone/config/{merchant_id}   → Get phone agent config
  POST   /api/phone/config                 → Save/update phone agent config
  GET    /api/phone/calls/{merchant_id}    → List call logs
  GET    /api/phone/orders/{merchant_id}   → List phone orders
  GET    /api/phone/stats/{merchant_id}    → Aggregated stats
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth import require_service_auth
from ...db import get_db

logger = logging.getLogger("meridian.api.phone_dashboard")

router = APIRouter(prefix="/api/phone", tags=["phone-dashboard"])

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I
)


class PhoneConfigRequest(BaseModel):
    merchant_id: str
    business_name: str | None = None
    business_type: str | None = None
    phone_number: str | None = None
    greeting: str | None = None
    voice: str | None = None
    language: str | None = None
    active: bool | None = None
    menu_items: list | None = None
    pos_system: str | None = None
    pos_access_token: str | None = None
    pos_location_id: str | None = None
    business_hours: dict | None = None
    after_hours_message: str | None = None
    max_concurrent_calls: int | None = None
    order_types: list | None = None
    special_instructions_enabled: bool | None = None
    transfer_number: str | None = None


def _validate_merchant_id(merchant_id: str):
    if not _UUID_RE.match(merchant_id):
        raise HTTPException(400, "Invalid merchant_id format")


@router.get("/config/{merchant_id}")
async def get_phone_config(merchant_id: str, _auth=Depends(require_service_auth)):
    """Return phone agent config for a merchant. Returns {exists: false} if none."""
    _validate_merchant_id(merchant_id)
    db = get_db()

    rows = await db.select(
        "phone_agent_config",
        filters={"merchant_id": f"eq.{merchant_id}"},
        limit=1,
    )

    if not rows:
        return {"exists": False, "merchant_id": merchant_id}

    row = rows[0]
    row.pop("pos_access_token", None)
    return {"exists": True, **row}


@router.post("/config")
async def save_phone_config(req: PhoneConfigRequest, _auth=Depends(require_service_auth)):
    """Create or update phone agent configuration."""
    _validate_merchant_id(req.merchant_id)
    db = get_db()

    rows = await db.select(
        "phone_agent_config",
        filters={"merchant_id": f"eq.{req.merchant_id}"},
        limit=1,
    )

    payload = {
        k: v for k, v in req.model_dump().items()
        if v is not None and k != "merchant_id"
    }
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    if rows:
        await db.update(
            "phone_agent_config",
            payload,
            filters={"merchant_id": f"eq.{req.merchant_id}"},
        )
        logger.info("Updated phone config for %s", req.merchant_id)
    else:
        payload["merchant_id"] = req.merchant_id
        await db.insert("phone_agent_config", payload)
        logger.info("Created phone config for %s", req.merchant_id)

    return {"ok": True, "merchant_id": req.merchant_id}


@router.get("/calls/{merchant_id}")
async def get_phone_calls(
    merchant_id: str,
    _auth=Depends(require_service_auth),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return call logs for a merchant, newest first."""
    _validate_merchant_id(merchant_id)
    db = get_db()

    calls = await db.select(
        "phone_call_logs",
        filters={"merchant_id": f"eq.{merchant_id}"},
        order="created_at.desc",
        limit=limit,
        offset=offset,
    )

    return {"merchant_id": merchant_id, "calls": calls, "count": len(calls)}


@router.get("/orders/{merchant_id}")
async def get_phone_orders(
    merchant_id: str,
    _auth=Depends(require_service_auth),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return phone orders for a merchant, newest first."""
    _validate_merchant_id(merchant_id)
    db = get_db()

    orders = await db.select(
        "phone_orders",
        filters={"merchant_id": f"eq.{merchant_id}"},
        order="created_at.desc",
        limit=limit,
        offset=offset,
    )

    return {"merchant_id": merchant_id, "orders": orders, "count": len(orders)}


@router.get("/stats/{merchant_id}")
async def get_phone_stats(
    merchant_id: str,
    _auth=Depends(require_service_auth),
    days: int = Query(7, ge=1, le=90),
):
    """Return aggregated phone stats for a merchant over N days."""
    _validate_merchant_id(merchant_id)
    db = get_db()

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    calls = await db.select(
        "phone_call_logs",
        filters={
            "merchant_id": f"eq.{merchant_id}",
            "created_at": f"gte.{since}",
        },
        order="created_at.desc",
        limit=5000,
    )

    orders = await db.select(
        "phone_orders",
        filters={
            "merchant_id": f"eq.{merchant_id}",
            "created_at": f"gte.{since}",
        },
        order="created_at.desc",
        limit=5000,
    )

    total_calls = len(calls)
    order_calls = sum(1 for c in calls if c.get("status") == "order_placed")
    total_orders = len(orders)
    total_revenue = sum(float(o.get("total", 0)) for o in orders)
    avg_duration = 0
    durations = [c.get("duration_seconds", 0) for c in calls if c.get("duration_seconds")]
    if durations:
        avg_duration = round(sum(durations) / len(durations))

    return {
        "merchant_id": merchant_id,
        "days": days,
        "total_calls": total_calls,
        "order_calls": order_calls,
        "conversion_rate": round(order_calls / total_calls * 100, 1) if total_calls else 0,
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "avg_duration_seconds": avg_duration,
    }
