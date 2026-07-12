"""
Career Applications — Shared endpoint for US and Canada applications.

  POST /api/careers/apply         → US application
  POST /api/canada/careers/apply  → Canada application (via canada.py)
"""
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from ...db import get_db

logger = logging.getLogger("meridian.api.careers")

router = APIRouter(prefix="/api/careers", tags=["careers"])

_NOTIFY_EMAIL_US = os.environ.get("CAREERS_NOTIFY_EMAIL", "careers@meridian.tips")
_NOTIFY_EMAIL_CA = os.environ.get("CANADA_CAREERS_NOTIFY_EMAIL", "careers-canada@meridian.tips")


class CareerApplication(BaseModel):
    name: str
    email: EmailStr
    phone: str = ""
    position: str
    city: str = ""
    province: str = ""
    state: str = ""
    experience: str = ""
    current_employer: str = ""
    linkedin_url: str = ""
    referral_source: str = ""
    availability: str = ""
    motivation: str = ""


async def submit_application(req: CareerApplication, country: str = "US") -> dict:
    app_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    state_province = req.province or req.state or ""
    country_label = "Canada" if country == "CA" else "US"
    notify_email = _NOTIFY_EMAIL_CA if country == "CA" else _NOTIFY_EMAIL_US

    db = get_db()

    try:
        await db.insert("career_applications", {
            "id": app_id,
            "country": country,
            "name": req.name,
            "email": req.email,
            "phone": req.phone,
            "position": req.position,
            "city": req.city,
            "state_province": state_province,
            "experience": req.experience,
            "current_employer": req.current_employer,
            "linkedin_url": req.linkedin_url,
            "referral_source": req.referral_source,
            "availability": req.availability,
            "motivation": req.motivation,
            "status": "pending",
            "created_at": now,
        })
    except Exception as e:
        logger.warning("career_applications insert failed (table may not exist): %s", e)

    position_label = "Sales Representative" if req.position == "sales_rep" else "Sales Team Lead"

    # (An earlier notifications insert lived here — it had never succeeded:
    # notifications.org_id is a uuid and this passed "meridian-{cc}-careers",
    # so every insert 400'd and nothing consumed the rows. The durable record
    # is career_applications above; humans are notified via the email below.)

    # For Canadian applications, upsert a sales_reps row so it appears
    # in the SR portal Team > Applications tab for admin approval.
    if country == "CA":
        try:
            await db.upsert("sales_reps", {
                "id": str(uuid4()),
                "org_id": "168b6df2-e9af-4b00-8fec-51e51149ff19",
                "name": req.name,
                "email": req.email,
                "phone": req.phone or None,
                "commission_rate": 0.70,
                "is_active": False,
                "portal_context": "canada",
                "created_at": now,
            }, on_conflict="email")
            logger.info("Upserted pending sales_reps row for CA applicant %s", req.email)
        except Exception as e:
            logger.warning("Could not upsert sales_reps row for CA applicant: %s", e)

    # Email the hiring inbox (Postal primary, Resend fallback) — best-effort,
    # never blocks the application: the DB rows above are the source of truth.
    try:
        from ...email.send import send_career_application
        await send_career_application(
            notify_email,
            country_label=country_label,
            position_label=position_label,
            applicant_name=req.name,
            applicant_email=req.email,
            applicant_phone=req.phone,
            location=f"{req.city}{', ' + state_province if state_province else ''}",
            experience=req.experience,
            availability=req.availability,
            linkedin_url=req.linkedin_url,
            referral_source=req.referral_source,
            motivation=req.motivation,
            application_id=app_id,
        )
    except Exception as e:
        logger.warning("Could not email career application %s: %s", app_id, e)

    logger.info(
        "%s career application saved: %s (%s) for %s in %s [id=%s]",
        country_label, req.name, req.email, req.position, req.city, app_id,
    )

    return {
        "status": "received",
        "application_id": app_id,
        "name": req.name,
        "position": req.position,
        "message": "Your application has been received. We'll be in touch soon!",
    }


@router.post("/apply")
async def submit_us_career_application(req: CareerApplication):
    return await submit_application(req, country="US")
