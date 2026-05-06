"""
Career Applications — Shared endpoint for US and Canada applications.

  POST /api/careers/apply         → US application
  POST /api/canada/careers/apply  → Canada application (via canada.py)
"""
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
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
        logger.error("Failed to save %s career application to DB: %s", country_label, e)
        raise HTTPException(500, "Could not save application. Please try again.")

    position_label = "Sales Representative" if req.position == "sales_rep" else "Sales Team Lead"

    try:
        await db.insert("notifications", {
            "id": str(uuid4()),
            "org_id": f"meridian-{country.lower()}-careers",
            "title": f"New {country_label} Sales Application: {req.name}",
            "body": (
                f"New application for {position_label}\n\n"
                f"Name: {req.name}\n"
                f"Email: {req.email}\n"
                f"Phone: {req.phone or 'Not provided'}\n"
                f"Location: {req.city}{', ' + state_province if state_province else ''}\n"
                f"Experience: {req.experience or 'Not specified'}\n"
                f"Availability: {req.availability or 'Not specified'}\n"
                f"LinkedIn: {req.linkedin_url or 'Not provided'}\n"
                f"Heard from: {req.referral_source or 'Not specified'}\n\n"
                f"Motivation:\n{req.motivation or 'Not provided'}"
            ),
            "priority": "high",
            "source_type": "event",
            "status": "active",
            "created_at": now,
            "metadata": {
                "type": "career_application",
                "application_id": app_id,
                "country": country,
                "notify_email": notify_email,
                "applicant_email": req.email,
                "position": req.position,
                "state_province": state_province,
            },
        })
    except Exception as e:
        logger.warning("Could not create notification for career application: %s", e)

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
