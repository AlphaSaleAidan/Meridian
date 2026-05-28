"""
Admin Routes — One-time setup helpers.
"""
import logging
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, field_validator
from ..auth import require_admin
from ...db import get_db

logger = logging.getLogger("meridian.api.admin")
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class CreateRepRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    commission_rate: float = 35.0

    @field_validator("commission_rate")
    @classmethod
    def validate_commission_rate(cls, v: float) -> float:
        if v < 0 or v > 100:
            raise ValueError("commission_rate must be between 0 and 100")
        return v


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
        return {"status": "error", "error": "Failed to create rep. Check server logs."}


class UpdateBriefRequest(BaseModel):
    subject: str
    greeting: str = "Team"
    intro: str = ""
    sections: list[dict]
    closing: str = ""
    cta_text: str = ""
    cta_url: str = ""
    extra_recipients: list[str] = []
    portal: str = "canada"
    include_admin: bool = True
    admin_email: str = "aidanpierce@meridian.tips"


@router.post("/send-update-brief")
async def send_update_brief(req: UpdateBriefRequest):
    """Send an update brief to all active reps (+ admin) via Resend."""
    from ...email.send import send_update_brief as _send, fetch_canada_rep_emails

    recipients: list[str] = []
    if req.portal == "canada":
        rep_emails = await fetch_canada_rep_emails()
        recipients.extend(rep_emails)
    recipients.extend(req.extra_recipients)
    if req.include_admin and req.admin_email not in recipients:
        recipients.append(req.admin_email)

    if not recipients:
        return {"status": "error", "detail": "No recipients found"}

    unique = list(dict.fromkeys(recipients))
    results = await _send(
        unique,
        req.subject,
        greeting=req.greeting,
        intro=req.intro,
        sections=req.sections,
        closing=req.closing,
        cta_text=req.cta_text,
        cta_url=req.cta_url,
        reply_to=req.admin_email,
    )

    sent = sum(1 for r in results if r.get("status") == "sent")
    failed = len(results) - sent
    logger.info("Update brief sent: %d ok, %d failed, recipients: %s", sent, failed, unique)
    return {"status": "sent", "sent": sent, "failed": failed, "results": results}
