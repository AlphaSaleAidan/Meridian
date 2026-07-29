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
# Hiring team: every inbound application is also confirmed to these inboxes —
# the careers-* addresses above are unmonitored aliases (owner call, 2026-07-29).
_ADMIN_NOTIFY_EMAILS = [
    e.strip()
    for e in os.environ.get(
        "CAREERS_ADMIN_NOTIFY_EMAILS",
        "aidanpierce72@gmail.com,cheungenochmgmt@gmail.com,aidanvietnguyen@gmail.com",
    ).split(",")
    if e.strip()
]

# The org UUID every production sales_reps row carries — org_id is NOT NULL in
# the live table (ad-hoc schema, absent from 20260512's DDL), so inserts
# without it fail. Same value as canada.py's CANADA_ORG_ID (import would be
# circular: canada.py imports from this module).
SALES_ORG_ID = os.environ.get("CANADA_ORG_ID", "168b6df2-e9af-4b00-8fec-51e51149ff19")


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

    # Applicants must be visible in their portal's Team > Applications tab the
    # moment they apply (owner call, 2026-07-29 — reverts the 2026-07-16
    # pipeline-only behavior; extended to US 2026-07-29 since the US tab reads
    # the same table and had the identical blind spot): insert an INACTIVE
    # sales_reps row so an admin can approve them there without the applicant
    # registering again. Insert only if absent — never an upsert — so a
    # re-application can never deactivate or rewrite an existing rep's row.
    # The recruiting pipeline (careers_pipeline.py) still owns staged hiring;
    # stage='hired' upserts on the same email and activates this row under the
    # recruiter. A failure here is surfaced as a WARNING banner in the alert
    # emails below (and caught by the daily careers-reconcile worker) — it must
    # never again die as an unread log line.
    rep_row_issue = ""
    try:
        email_lc = str(req.email).strip().lower()
        existing = await db.select(
            "sales_reps", columns="id",
            filters={"email": f"eq.{email_lc}"}, limit=1,
        )
        if not existing:
            await db.insert("sales_reps", {
                "org_id": SALES_ORG_ID,
                "name": req.name,
                "email": email_lc,
                "phone": req.phone or "",
                "commission_rate": 0.70,
                "is_active": False,
                "portal_context": "canada" if country == "CA" else "us",
                "created_at": now,
            }, return_data=False)
            logger.info("Created pending sales_reps applicant row for %s", email_lc)
    except Exception as e:
        rep_row_issue = str(e)
        logger.warning("Could not create applicant sales_reps row for %s: %s", req.email, e)

    alert_note = (
        "WARNING: this applicant could NOT be added to Team > Applications "
        f"(pending rep row failed: {rep_row_issue}). They are saved in the "
        "recruiting pipeline — run the careers backfill or check the API logs."
    ) if rep_row_issue else ""

    # Email the hiring inbox + hiring team (Postal primary, Resend fallback) —
    # best-effort per recipient, never blocks the application: the DB rows
    # above are the source of truth.
    for recipient in dict.fromkeys([notify_email, *_ADMIN_NOTIFY_EMAILS]):
        try:
            from ...email.send import send_career_application
            await send_career_application(
                recipient,
                alert_note=alert_note,
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
            logger.warning("Could not email career application %s to %s: %s", app_id, recipient, e)

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
