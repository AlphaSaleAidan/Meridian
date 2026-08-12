"""Careers recruiting pipeline — applications flow through stages and the org
tree grows from recruiting.

  GET  /api/careers/pipeline                → admin: all; manager: apps whose
                                              recruiter_id is in their subtree
  POST /api/careers/{id}/stage              → advance/reject (appends
                                              stage_history {stage, by, at});
                                              stage='hired' creates/activates
                                              the sales_reps row with
                                              manager_id = recruiter_id
  POST /api/careers/{id}/assign-recruiter   → admin: anyone; manager: only
                                              recruiters inside their subtree

The sales_reps row is NO LONGER created at application time (see careers.py) —
it is created only on hire, landing the new rep in the recruiter's downline.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...db import get_db
from ..auth import require_jwt
from .. import hierarchy
from .careers import SALES_ORG_ID

logger = logging.getLogger("meridian.api.careers_pipeline")

router = APIRouter(prefix="/api/careers", tags=["careers"])

STAGES = ("applied", "screened", "interview", "offer", "hired", "rejected")
TERMINAL_STAGES = ("hired",)  # rejected can be reopened by re-staging

# Legacy status kept coherent for old consumers of career_applications.status.
_STAGE_TO_STATUS = {"hired": "approved", "rejected": "rejected"}


class StageRequest(BaseModel):
    stage: str


class AssignRecruiterRequest(BaseModel):
    recruiter_id: str


async def _load_application(db, application_id: str) -> dict:
    rows = await db.select("career_applications", filters={"id": f"eq.{application_id}"}, limit=1)
    if not rows:
        raise HTTPException(404, "Application not found")
    return rows[0]


async def _authorize_app_access(scope: hierarchy.RepScope, app_row: dict) -> None:
    """Admin passes; a region member passes on their own region's applications
    (the region lead recruits for the region, even before a recruiter is
    assigned); otherwise a manager/rep passes only when the application's
    recruiter is inside their subtree. Independent of RLS (backend plane)."""
    if scope.is_admin:
        return
    if scope.region and (app_row.get("region") or "") == scope.region:
        return
    allowed = await hierarchy.visible_rep_ids(scope)
    recruiter_id = app_row.get("recruiter_id")
    if not recruiter_id or allowed is None or recruiter_id not in allowed:
        raise HTTPException(403, "This application is outside your branch")


@router.get("/pipeline")
async def get_pipeline(user: dict = Depends(require_jwt)):
    db = get_db()
    scope = await hierarchy.resolve_scope(user)
    rows = await db.select("career_applications", order="created_at.desc")

    # Region routing (20260812 regions): an applicant who picked a region lands
    # in THAT region's pipeline. Region members see their region's applicants
    # (incl. still-unassigned ones — they recruit for the region) and never core
    # apps; core members never see region apps; admins see everything.
    if not scope.is_admin:
        if scope.region:
            rows = [r for r in rows if (r.get("region") or "") == scope.region]
        else:
            allowed = await hierarchy.visible_rep_ids(scope) or set()
            rows = [r for r in rows
                    if not (r.get("region") or "") and r.get("recruiter_id") in allowed]

    return {
        "applications": rows,
        "stages": list(STAGES),
        "viewer": {"role": scope.role, "rep_id": scope.rep_id,
                   "is_admin": scope.is_admin, "region": scope.region},
    }


@router.post("/{application_id}/stage")
async def set_stage(application_id: str, req: StageRequest, user: dict = Depends(require_jwt)):
    stage = (req.stage or "").strip().lower()
    if stage not in STAGES:
        raise HTTPException(400, f"Unknown stage '{req.stage}'")

    db = get_db()
    scope = await hierarchy.resolve_scope(user)
    app_row = await _load_application(db, application_id)
    await _authorize_app_access(scope, app_row)

    current = (app_row.get("stage") or "applied").lower()
    if current in TERMINAL_STAGES:
        raise HTTPException(409, f"Application is already '{current}' and cannot be re-staged")
    if stage == current:
        return {"ok": True, "application_id": application_id, "stage": stage, "unchanged": True}

    history = list(app_row.get("stage_history") or [])
    history.append({
        "stage": stage,
        "by": user.get("email") or "",
        "at": datetime.now(timezone.utc).isoformat(),
    })

    updates = {
        "stage": stage,
        "stage_history": history,
        "status": _STAGE_TO_STATUS.get(stage, "pending"),
    }

    rep_id = None
    if stage == "hired":
        rep_id = await _hire_applicant(db, app_row)

    await db.update("career_applications", updates, filters={"id": f"eq.{application_id}"})
    logger.info(
        "careers: application %s %s -> %s by %s%s",
        application_id, current, stage, user.get("email"),
        f" (rep {rep_id} created)" if rep_id else "",
    )
    return {"ok": True, "application_id": application_id, "stage": stage, "rep_id": rep_id}


async def _hire_applicant(db, app_row: dict) -> str | None:
    """stage='hired' → create (or activate) the sales_reps row. The new rep
    lands in the recruiter's downline: manager_id = recruiter_id, role =
    sales_rep. The path trigger materializes their position in the tree."""
    email = (app_row.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(422, "Application has no email — cannot hire")
    recruiter_id = app_row.get("recruiter_id")
    country = (app_row.get("country") or "US").upper()

    row = {
        "org_id": SALES_ORG_ID,  # NOT NULL in the live table — insert fails without it
        "name": app_row.get("name") or email,
        "email": email,
        "phone": app_row.get("phone") or "",
        "role": "sales_rep",
        "manager_id": recruiter_id,
        "is_active": True,
        "commission_rate": 0.70,
        "portal_context": "canada" if country == "CA" else "us",
    }
    try:
        created = await db.upsert("sales_reps", row, on_conflict="email")
    except Exception as exc:
        logger.error("careers: hire upsert failed for %s: %s", email, exc)
        raise HTTPException(502, "Could not create the sales rep record for this hire")
    rep_id = created[0].get("id") if created else None
    logger.info("careers: hired %s -> rep %s under manager %s", email, rep_id, recruiter_id)

    # Credentials go out ONLY on acceptance (owner call, 2026-07-29): provision
    # the Supabase login + email it, exactly like canada.py/us.py rep-approve —
    # a hire from the pipeline must never leave the rep unable to sign in.
    # Best-effort: the hire itself is durable either way.
    try:
        await _provision_rep_login(email, row["name"], row["portal_context"])
    except Exception as exc:
        logger.warning("careers: hired %s but login provisioning failed: %s", email, exc)
    return rep_id


async def _provision_rep_login(email: str, name: str, portal: str) -> None:
    """Create the Supabase auth user (if absent) and email login credentials.

    Mirrors the rep-approve flow in canada.py/us.py: temp password only when
    the auth user is newly created; an existing user keeps their password and
    the email just points at the login page.
    """
    import os
    import secrets
    import string

    import httpx

    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not service_key:
        raise RuntimeError("Supabase not configured — cannot provision rep login")

    temp_password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    auth_created = False
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{supabase_url}/auth/v1/admin/users",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": "application/json",
            },
            json={
                "email": email,
                "password": temp_password,
                "email_confirm": True,
                "user_metadata": {"full_name": name, "role": "sales_rep", "portal": portal},
            },
        )
        if resp.status_code in (200, 201):
            auth_created = True
            logger.info("careers: created auth user for hired rep %s", email)
        elif resp.status_code == 422 and "already been registered" in resp.text.lower():
            logger.info("careers: auth user already exists for %s — keeping their password", email)
        else:
            logger.warning("careers: auth user creation failed for %s: %s %s", email, resp.status_code, resp.text)

    from ...email.send import send_rep_credentials
    login_url = (
        "https://meridian.tips/canada/portal/login" if portal == "canada"
        else "https://meridian.tips/us/portal/login"
    )
    await send_rep_credentials(
        to=email,
        rep_name=name,
        email=email,
        password=temp_password if auth_created else None,
        login_url=login_url,
    )


@router.post("/{application_id}/assign-recruiter")
async def assign_recruiter(
    application_id: str,
    req: AssignRecruiterRequest,
    user: dict = Depends(require_jwt),
):
    hierarchy.validate_uuid(req.recruiter_id, "recruiter_id")

    db = get_db()
    scope = await hierarchy.resolve_scope(user)
    await _load_application(db, application_id)  # 404 before authz probing

    if not scope.is_admin:
        allowed = await hierarchy.visible_rep_ids(scope) or set()
        if req.recruiter_id not in allowed:
            raise HTTPException(403, "Recruiter is outside your branch")

    await db.update(
        "career_applications",
        {"recruiter_id": req.recruiter_id},
        filters={"id": f"eq.{application_id}"},
    )
    logger.info("careers: application %s recruiter -> %s by %s",
                application_id, req.recruiter_id, user.get("email"))
    return {"ok": True, "application_id": application_id, "recruiter_id": req.recruiter_id}
