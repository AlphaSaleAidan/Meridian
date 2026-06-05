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
import os
import re
from datetime import datetime, timedelta, timezone

import httpx
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


class TestChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class TestChatRequest(BaseModel):
    merchant_id: str
    messages: list[TestChatMessage]
    business_name: str | None = None
    greeting: str | None = None
    menu_items: list | None = None
    order_types: list | None = None


def _build_test_prompt(req: TestChatRequest) -> str:
    """System prompt scoped to the merchant's own menu/greeting so the in-app
    test call behaves like the live agent for this specific business."""
    name = (req.business_name or "this restaurant").strip()
    lines = []
    for item in req.menu_items or []:
        try:
            price = float(item.get("price", 0))
        except (TypeError, ValueError):
            price = 0.0
        nm = (item.get("name") or "").strip()
        if not nm:
            continue
        cat = item.get("category")
        line = f" - {nm}: ${price:.2f}"
        if cat:
            line += f" ({cat})"
        lines.append(line)
    menu_text = "\n".join(lines) if lines else " (menu not configured yet — take the order generally)"
    order_types = ", ".join(req.order_types or ["pickup", "delivery"])
    greeting = (req.greeting or "").strip()
    greeting_line = f'\nOpen with a greeting like: "{greeting}"' if greeting else ""
    return (
        f"You are a friendly AI phone ordering assistant for {name}. "
        "Keep responses SHORT — 1-2 sentences. Sound warm and natural, not robotic. "
        f"This is a phone call.{greeting_line}\n\n"
        f"MENU:\n{menu_text}\n\n"
        f"Available order types: {order_types}.\n\n"
        "RULES:\n"
        "- Help the customer build their order item by item.\n"
        "- When done, read back the order with total price and ask for their name.\n"
        "- For items not on the menu, let them know politely.\n"
        "- Keep it brief — phone conversations should be quick."
    )


@router.post("/test-chat")
async def phone_test_chat(req: TestChatRequest, _auth=Depends(require_service_auth)):
    """Interactive in-app test call. Runs the real agent brain (SambaNova →
    Qwen fallback) against the merchant's own menu so the wizard's test call
    responds to live speech instead of replaying a canned script."""
    _validate_merchant_id(req.merchant_id)

    # Reuse the production agent brain + parser from the Twilio route module.
    from .phone import _ask_ai, _parse

    convo = [{"role": m.role, "content": m.content} for m in req.messages if m.content.strip()]
    if not convo:
        raise HTTPException(400, "messages cannot be empty")

    result = await _ask_ai(convo, _build_test_prompt(req))
    reply, tool = _parse(result)
    ended = bool(tool and tool.get("name") in ("end_call", "submit_order"))
    order = tool.get("input") if (tool and tool.get("name") == "submit_order") else None

    if not reply:
        reply = "Sorry, could you say that again?"

    return {"reply": reply, "ended": ended, "order": order}


# ---------------------------------------------------------------------------
# Number provisioning — buys a dedicated Twilio number per merchant and wires
# its voice webhook so inbound calls resolve to this business.
# ---------------------------------------------------------------------------

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_API = "https://api.twilio.com/2010-04-01"


def _webhook_base() -> str:
    host = os.getenv("MEDIA_STREAM_HOST", "api.meridian.tips")
    return f"https://{host}"


class ProvisionNumberRequest(BaseModel):
    merchant_id: str
    country: str = "CA"
    area_code: str | None = None
    business_name: str | None = None


async def _twilio_search(country: str, area_code: str | None) -> str | None:
    """Return one available voice+SMS local number for the country, or None."""
    params: dict[str, str] = {"VoiceEnabled": "true", "SmsEnabled": "true", "Limit": "5"}
    if area_code:
        params["AreaCode"] = area_code
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.get(
            f"{TWILIO_API}/Accounts/{TWILIO_SID}/AvailablePhoneNumbers/{country}/Local.json",
            params=params,
            auth=(TWILIO_SID, TWILIO_TOKEN),
        )
        if res.status_code != 200:
            logger.error("Twilio number search %d: %s", res.status_code, res.text[:300])
            return None
        nums = res.json().get("available_phone_numbers", [])
        return nums[0]["phone_number"] if nums else None


async def _twilio_purchase(phone_number: str, friendly_name: str) -> dict:
    """Buy the number and point its voice/status webhooks at our backend."""
    base = _webhook_base()
    data = {
        "PhoneNumber": phone_number,
        "FriendlyName": friendly_name,
        "VoiceUrl": f"{base}/twilio/voice",
        "VoiceMethod": "POST",
        "StatusCallback": f"{base}/twilio/status",
        "StatusCallbackMethod": "POST",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(
            f"{TWILIO_API}/Accounts/{TWILIO_SID}/IncomingPhoneNumbers.json",
            data=data,
            auth=(TWILIO_SID, TWILIO_TOKEN),
        )
        if res.status_code not in (200, 201):
            logger.error("Twilio purchase %d: %s", res.status_code, res.text[:400])
            # Surface Twilio's own message (e.g. regulatory bundle / no funds).
            try:
                msg = res.json().get("message", res.text[:200])
            except Exception:
                msg = res.text[:200]
            raise HTTPException(502, f"Twilio could not provision a number: {msg}")
        body = res.json()
        return {"phone_number": body.get("phone_number"), "sid": body.get("sid")}


@router.post("/provision-number")
async def provision_number(req: ProvisionNumberRequest, _auth=Depends(require_service_auth)):
    """Provision a dedicated phone number for a merchant. Idempotent: if the
    merchant already has a number it is returned unchanged (never double-buys)."""
    _validate_merchant_id(req.merchant_id)

    if not TWILIO_SID or not TWILIO_TOKEN:
        raise HTTPException(503, "Twilio is not configured")

    db = get_db()
    rows = await db.select(
        "phone_agent_config",
        filters={"merchant_id": f"eq.{req.merchant_id}"},
        limit=1,
    )
    existing = rows[0].get("phone_number") if rows else None
    if existing:
        return {"phone_number": existing, "provisioned": False, "already_existed": True}

    country = (req.country or "CA").upper()
    available = await _twilio_search(country, req.area_code)
    if not available:
        raise HTTPException(404, f"No available {country} numbers found")

    purchased = await _twilio_purchase(available, req.business_name or f"Meridian {req.merchant_id[:8]}")
    number = purchased["phone_number"]

    payload = {"phone_number": number, "updated_at": datetime.now(timezone.utc).isoformat()}
    if rows:
        await db.update("phone_agent_config", payload, filters={"merchant_id": f"eq.{req.merchant_id}"})
    else:
        payload["merchant_id"] = req.merchant_id
        await db.insert("phone_agent_config", payload)
    logger.info("Provisioned %s for merchant %s", number, req.merchant_id)

    return {"phone_number": number, "provisioned": True, "already_existed": False}
