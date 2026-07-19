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
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

from ...db import get_db

logger = logging.getLogger("meridian.api.careers")

router = APIRouter(prefix="/api/careers", tags=["careers"])

_NOTIFY_EMAIL_US = os.environ.get("CAREERS_NOTIFY_EMAIL", "careers@meridian.tips")
_NOTIFY_EMAIL_CA = os.environ.get("CANADA_CAREERS_NOTIFY_EMAIL", "careers-canada@meridian.tips")


class CareerApplication(BaseModel):
    # The US careers form (CareersPage.tsx) posts the canonical backend keys
    # (experience / current_employer / linkedin_url / referral_source /
    # motivation). The Canada form (CanadaCareersPage.tsx) posts UI-shaped keys
    # (yearsExperience / employer / linkedin / heardFrom / message) plus two
    # answers that had NO backend home and were silently dropped by Pydantic:
    # commissionExperience and the referral *name*. AliasChoices accepts either
    # spelling so both forms round-trip; the two new fields below make the
    # commission + referral-name answers durable.
    model_config = ConfigDict(populate_by_name=True)

    name: str
    email: EmailStr
    phone: str = ""
    position: str
    city: str = ""
    province: str = ""
    state: str = ""
    experience: str = Field(
        "", validation_alias=AliasChoices("experience", "yearsExperience"),
    )
    current_employer: str = Field(
        "", validation_alias=AliasChoices("current_employer", "employer"),
    )
    linkedin_url: str = Field(
        "", validation_alias=AliasChoices("linkedin_url", "linkedin"),
    )
    referral_source: str = Field(
        "", validation_alias=AliasChoices("referral_source", "heardFrom"),
    )
    availability: str = ""
    motivation: str = Field(
        "", validation_alias=AliasChoices("motivation", "message"),
    )
    # Previously-dropped answers, now durable (see 038 migration).
    commission_experience: str = Field(
        "", validation_alias=AliasChoices("commission_experience", "commissionExperience"),
    )
    referral_name: str = Field(
        "", validation_alias=AliasChoices("referral_name", "referral"),
    )


async def submit_application(req: CareerApplication, country: str = "US") -> dict:
    app_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    state_province = req.province or req.state or ""
    country_label = "Canada" if country == "CA" else "US"
    notify_email = _NOTIFY_EMAIL_CA if country == "CA" else _NOTIFY_EMAIL_US

    db = get_db()

    # Spam dedup (2026-07-15 hunt): same email + position + country within 24h
    # → answer 200 (never tip off a bot / punish a double-click) but store no
    # duplicate row and send no duplicate email.
    from ...services.submission_guard import is_recent_duplicate
    if await is_recent_duplicate(
        db, "career_applications", str(req.email),
        extra_filters={"position": f"eq.{req.position}", "country": f"eq.{country}"},
    ):
        logger.info("Duplicate career application suppressed: %s (%s/%s)",
                    req.email, req.position, country)
        return {
            "status": "received",
            "application_id": app_id,
            "name": req.name,
            "position": req.position,
            "message": "Your application has been received. We'll be in touch soon!",
        }

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
            "referral_name": req.referral_name,
            "commission_experience": req.commission_experience,
            "availability": req.availability,
            "motivation": req.motivation,
            "status": "pending",
            # Recruiting pipeline entry point (careers_pipeline.py). The
            # SupabaseREST client drops unknown columns, so this stays
            # backward-compatible until the 20260716 migration is applied.
            "stage": "applied",
            "stage_history": [],
            "created_at": now,
        })
    except Exception as e:
        logger.warning("career_applications insert failed (table may not exist): %s", e)

    position_label = "Sales Representative" if req.position == "sales_rep" else "Sales Team Lead"

    # (An earlier notifications insert lived here — it had never succeeded:
    # notifications.org_id is a uuid and this passed "meridian-{cc}-careers",
    # so every insert 400'd and nothing consumed the rows. The durable record
    # is career_applications above; humans are notified via the email below.)

    # NOTE (2026-07-16, careers pipeline): applications NO LONGER auto-upsert an
    # inactive sales_reps row here. They live in the recruiting pipeline
    # (career_applications.stage, careers_pipeline.py) and the sales_reps row is
    # created only at stage='hired', with manager_id = recruiter_id — the org
    # tree grows from recruiting. Applicants who already got an inactive row
    # from the old flow keep it (Team > Applications approve/reject still works
    # for them); nothing is orphaned.

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
            commission_experience=req.commission_experience,
            availability=req.availability,
            linkedin_url=req.linkedin_url,
            referral_source=req.referral_source,
            referral_name=req.referral_name,
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
