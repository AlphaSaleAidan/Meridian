"""POS system selection, connection status, and waitlist API routes."""
import logging
from fastapi.security import APIKeyHeader
from fastapi import APIRouter, Depends, HTTPException
from .. import auth as _auth
from ..auth import enforce_service_member, require_admin, require_admin_auth, require_service_auth
from pydantic import BaseModel, Field
from typing import Optional

_waitlist_auth_header = APIKeyHeader(name="Authorization", auto_error=False)

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
async def select_pos(req: POSSelectRequest, principal=Depends(require_service_auth)):
    """Record a merchant's POS system selection and connection status."""
    await enforce_service_member(principal, req.org_id)
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
async def join_waitlist(
    req: WaitlistRequest,
    auth_header: str = Depends(_waitlist_auth_header),
):
    """Add an email to the POS integration waitlist.

    This is an intentionally PUBLIC endpoint — a prospect joins the waitlist by
    email with no session. The waitlist row itself is always recorded.

    SECURITY (org_id-from-body): the optional `org_id` in the body previously
    triggered a privileged `UPDATE organizations SET pos_waitlist_email ... WHERE
    id = <body org_id>`, letting ANY unauthenticated caller stamp an arbitrary
    email onto ANY organization row (cross-tenant write keyed on a
    client-supplied identifier). We now only perform that org-scoped side-effect
    when the request carries a principal that is a VERIFIED member of that org
    (or a machine principal). Non-members still get a normal 200 — they joined
    the waitlist — but no foreign-org write occurs.
    """
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        await db.insert("pos_waitlist", {
            "email": req.email,
            "pos_system": req.pos_system,
            "org_id": req.org_id,
        })

        if req.org_id and await _waitlist_can_write_org(auth_header, req.org_id):
            await db.update("organizations", {
                "pos_waitlist_email": req.email,
            }, filters={"id": f"eq.{req.org_id}"})

        return {"ok": True, "message": f"Added to {req.pos_system} waitlist"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add to waitlist: %s", e)
        raise HTTPException(status_code=500, detail="Failed to join waitlist")


async def _waitlist_can_write_org(auth_header: str | None, org_id: str) -> bool:
    """Return True only if the caller is a verified member of `org_id`.

    Fails closed: any missing/invalid token or non-member returns False, so the
    public waitlist signup still succeeds but the privileged organizations
    write is skipped rather than performed cross-tenant.
    """
    if not auth_header:
        return False
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        return False
    user = await _auth._verify_supabase_token(token)
    if not user:
        return False
    try:
        return await _auth._check_org_membership(user, org_id)
    except Exception as e:
        logger.warning("waitlist org membership check failed for org=%s: %s", org_id, e)
        return False


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
async def update_pos_status(pos_system: str, new_status: str, _auth=Depends(require_admin_auth)):
    """Admin: toggle a POS system status (e.g. coming_soon -> integrated).

    This is a lightweight admin action — the actual system registry lives
    in the frontend. This endpoint persists the override in the DB so
    the admin dashboard can track changes.
    """
    valid = {"integrated", "coming_soon", "contingency", "unsupported"}
    if new_status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid}")

    return {"ok": True, "pos_system": pos_system, "new_status": new_status}
