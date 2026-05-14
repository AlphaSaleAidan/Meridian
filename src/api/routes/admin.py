"""
Admin Routes — One-time setup helpers.
"""
import logging
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from ...db import get_db

logger = logging.getLogger("meridian.api.admin")
router = APIRouter(prefix="/api/admin", tags=["admin"])


class CreateRepRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    commission_rate: float = 35.0


@router.post("/create-rep")
async def create_rep(req: CreateRepRequest):
    """Create a sales rep record."""
    try:
        db = get_db()
        rep_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Check if exists
        existing = await db.select(
            "sales_reps",
            filters={"email": f"eq.{req.email}"},
            limit=1,
        )
        if existing:
            return {"status": "exists", "rep_id": existing[0].get("id")}

        await db.insert("sales_reps", {
            "id": rep_id,
            "name": req.name,
            "email": req.email,
            "phone": req.phone,
            "commission_rate": req.commission_rate,
            "is_active": True,
            "total_earned": 0,
            "total_paid": 0,
            "created_at": now,
            "updated_at": now,
        })

        logger.info(f"Created sales rep: {req.name} ({req.email})")
        return {"status": "created", "rep_id": rep_id}
    except Exception as e:
        logger.error(f"create-rep failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
