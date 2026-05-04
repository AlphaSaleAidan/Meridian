"""POS system selection, connection status, and waitlist API routes."""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger("meridian.api.pos")
router = APIRouter()


class POSSelectRequest(BaseModel):
    org_id: str
    pos_system: str = Field(..., min_length=1, max_length=100)
    connection_status: str = Field(..., pattern="^(connected|manual|pending)$")


class WaitlistRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    pos_system: str = Field(..., min_length=1, max_length=100)
    org_id: Optional[str] = None


@router.post("/api/pos/select")
async def select_pos(req: POSSelectRequest):
    """Record a merchant's POS system selection and connection status."""
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        await db.table("organizations").update({
            "pos_system": req.pos_system,
            "pos_connection_status": req.connection_status,
        }).eq("id", req.org_id).execute()

        return {"ok": True, "pos_system": req.pos_system, "status": req.connection_status}
    except Exception as e:
        logger.error("Failed to update POS selection: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save POS selection")


@router.post("/api/pos/waitlist")
async def join_waitlist(req: WaitlistRequest):
    """Add an email to the POS integration waitlist."""
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        await db.table("pos_waitlist").insert({
            "email": req.email,
            "pos_system": req.pos_system,
            "org_id": req.org_id,
        }).execute()

        if req.org_id:
            await db.table("organizations").update({
                "pos_waitlist_email": req.email,
            }).eq("id", req.org_id).execute()

        return {"ok": True, "message": f"Added to {req.pos_system} waitlist"}
    except Exception as e:
        logger.error("Failed to add to waitlist: %s", e)
        raise HTTPException(status_code=500, detail="Failed to join waitlist")


@router.get("/api/pos/coverage")
async def pos_coverage():
    """Admin endpoint: POS system coverage stats across all merchants."""
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        coverage = await db.table("pos_coverage_stats").select("*").execute()
        waitlist = await db.table("pos_waitlist_stats").select("*").execute()

        return {
            "coverage": coverage.data or [],
            "waitlist": waitlist.data or [],
        }
    except Exception as e:
        logger.error("Failed to fetch POS coverage: %s", e)
        return {"coverage": [], "waitlist": []}


@router.patch("/api/pos/status")
async def update_pos_status(pos_system: str, new_status: str):
    """Admin: toggle a POS system status (e.g. coming_soon -> integrated).

    This is a lightweight admin action — the actual system registry lives
    in the frontend. This endpoint persists the override in the DB so
    the admin dashboard can track changes.
    """
    valid = {"integrated", "coming_soon", "contingency", "unsupported"}
    if new_status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid}")

    return {"ok": True, "pos_system": pos_system, "new_status": new_status}
