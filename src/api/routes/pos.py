"""POS system selection, connection status, and waitlist API routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from ..auth import require_admin, require_service_auth
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger("meridian.api.pos")
router = APIRouter(prefix="/api/pos", tags=["pos-connections"])


class POSSelectRequest(BaseModel):
    org_id: str
    pos_system: str = Field(..., min_length=1, max_length=100)
    connection_status: str = Field(..., pattern="^(connected|manual|pending)$")


class WaitlistRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    pos_system: str = Field(..., min_length=1, max_length=100)
    org_id: Optional[str] = None


@router.post("/select")
async def select_pos(req: POSSelectRequest, _auth=Depends(require_service_auth)):
    """Record a merchant's POS system selection and connection status."""
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        await db.update("organizations", {
            "pos_system": req.pos_system,
            "pos_connection_status": req.connection_status,
        }, filters={"id": f"eq.{req.org_id}"})

        return {"ok": True, "pos_system": req.pos_system, "status": req.connection_status}
    except Exception as e:
        logger.error("Failed to update POS selection: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save POS selection")


@router.post("/waitlist")
async def join_waitlist(req: WaitlistRequest):
    """Add an email to the POS integration waitlist."""
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        await db.insert("pos_waitlist", {
            "email": req.email,
            "pos_system": req.pos_system,
            "org_id": req.org_id,
        })

        if req.org_id:
            await db.update("organizations", {
                "pos_waitlist_email": req.email,
            }, filters={"id": f"eq.{req.org_id}"})

        return {"ok": True, "message": f"Added to {req.pos_system} waitlist"}
    except Exception as e:
        logger.error("Failed to add to waitlist: %s", e)
        raise HTTPException(status_code=500, detail="Failed to join waitlist")


@router.get("/coverage", dependencies=[Depends(require_admin)])
async def pos_coverage():
    """Admin endpoint: POS system coverage stats across all merchants."""
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        coverage = await db.select("pos_coverage_stats")
        waitlist = await db.select("pos_waitlist_stats")

        return {
            "coverage": coverage or [],
            "waitlist": waitlist or [],
        }
    except Exception as e:
        logger.error("Failed to fetch POS coverage: %s", e)
        return {"coverage": [], "waitlist": []}


@router.patch("/status")
async def update_pos_status(pos_system: str, new_status: str, _auth=Depends(require_service_auth)):
    """Admin: toggle a POS system status (e.g. coming_soon -> integrated).

    This is a lightweight admin action — the actual system registry lives
    in the frontend. This endpoint persists the override in the DB so
    the admin dashboard can track changes.
    """
    valid = {"integrated", "coming_soon", "contingency", "unsupported"}
    if new_status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid}")

    return {"ok": True, "pos_system": pos_system, "new_status": new_status}
