"""
Canada-specific Routes — Careers applications and Canada portal endpoints.

  POST /api/canada/careers/apply    → Submit a Canadian sales application
  POST /api/canada/create-customer  → Create Supabase Auth user for a Canada customer
"""
import asyncio
import logging
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator

from ..auth import require_admin, require_jwt, require_admin_jwt, rate_limit_signup
from .careers import submit_application, CareerApplication

logger = logging.getLogger("meridian.api.canada")

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _validate_rep_id(rep_id: str) -> None:
    """Validate rep_id is a proper UUID to prevent PostgREST filter injection."""
    if not _UUID_RE.match(rep_id):
        raise HTTPException(status_code=400, detail="Invalid rep_id format")

router = APIRouter(prefix="/api/canada", tags=["canada"])


CANADA_ORG_ID = "168b6df2-e9af-4b00-8fec-51e51149ff19"


def _get_anon_key() -> str:
    """Get the Supabase anon key from env (public key, safe to embed as fallback)."""
    return (
        os.environ.get("SUPABASE_ANON_KEY", "")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
        or os.environ.get("VITE_SUPABASE_ANON_KEY", "")
    )


def _user_token(request) -> str:
    """Extract the Bearer token from the incoming Authorization header.

    Used by admin endpoints to forward the caller's JWT to Supabase's REST API
    so that RLS is enforced as the calling user (defense-in-depth — the service
    role bypasses every policy and silently breaks future RLS tightening).
    For /auth/v1/admin/* calls, keep using the service role key directly.
    """
    auth_header = request.headers.get("authorization", "") or request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()
    return ""


def _sanitize_text(v: str) -> str:
    """Strip HTML tags and dangerous characters from user input."""
    import re
    v = re.sub(r'<[^>]+>', '', v)
    v = v.replace('&', '&amp;').replace('"', '&quot;').replace("'", '&#x27;')
    return v.strip()


class RepSignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = _sanitize_text(v)
        if len(v) < 2:
            raise ValueError("name must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("name too long")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class CreateCustomerRequest(BaseModel):
    email: EmailStr
    business_name: str
    contact_name: str
    phone: str | None = None
    vertical: str | None = None
    deal_id: str | None = None
    monthly_price: int = 0
    portal: str = "canada"

    @field_validator("business_name", "contact_name")
    @classmethod
    def sanitize_names(cls, v: str) -> str:
        return _sanitize_text(v)


@router.post("/rep-signup", dependencies=[Depends(rate_limit_signup)])
async def rep_signup(req: RepSignupRequest):
    """Create a new sales rep: auth user + sales_reps row.

    Rate limited to 5 signups per hour per IP to block account-spam bots.
    Account is still created with `is_active=False` and requires admin approval
    before the rep can interact with deals.
    """
    import httpx

    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    async with httpx.AsyncClient(timeout=15.0) as client:
        auth_resp = await client.post(
            f"{supabase_url}/auth/v1/admin/users",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": "application/json",
            },
            json={
                "email": req.email,
                "password": req.password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": req.name,
                    "role": "sales_rep",
                    "portal": "canada",
                },
            },
        )
        if auth_resp.status_code not in (200, 201):
            if auth_resp.status_code == 422 and "already been registered" in auth_resp.text.lower():
                logger.info(f"Auth user already exists for {req.email}")
            else:
                logger.error(f"Rep auth creation failed: {auth_resp.status_code} {auth_resp.text}")
                raise HTTPException(400, auth_resp.json().get("msg", "Could not create account"))

        rep_resp = await client.post(
            f"{supabase_url}/rest/v1/sales_reps",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": "application/json",
                "Prefer": "return=representation,resolution=merge-duplicates",
            },
            json={
                "org_id": CANADA_ORG_ID,
                "name": req.name,
                "email": req.email,
                "phone": req.phone or "",
                "commission_rate": 0.70,
                "is_active": False,
                "portal_context": "canada",
            },
        )
        if rep_resp.status_code not in (200, 201):
            logger.error(f"sales_reps insert failed: {rep_resp.status_code} {rep_resp.text}")
            raise HTTPException(400, "Account created but rep profile failed. Contact admin.")

        rep_data = rep_resp.json()
        rep_row = rep_data[0] if isinstance(rep_data, list) else rep_data

    logger.info(f"New Canada rep signed up: {req.name} ({req.email})")
    return {
        "ok": True,
        "rep_id": rep_row.get("id"),
        "name": req.name,
        "email": req.email,
    }


@router.post("/create-customer")
async def create_customer(req: CreateCustomerRequest, claims: dict = Depends(require_jwt)):
    """Create a Supabase Auth user for a Canada customer.

    Auth: requires a valid user JWT (rep must be logged in).
    Note: the internal Supabase call still uses the service role key because
    /auth/v1/admin/users is an admin-only API that cannot be called with a
    user JWT.  The security improvement is that callers must now present a
    verified Supabase session instead of a static service token.
    """
    import httpx
    import secrets

    user_id = claims.get("id", "")
    logger.info("create-customer called by user %s (%s)", user_id, claims.get("email", ""))

    supabase_url = os.environ.get("SUPABASE_URL", "")
    # Service role key is still required here: the Supabase admin user-creation
    # API (/auth/v1/admin/users) rejects non-service-role tokens.
    service_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )

    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    org_id = str(uuid.uuid4())
    # Server-generated random password — never returned to the caller.
    # The customer sets their own password via the Supabase recovery email
    # that the frontend triggers after this endpoint returns.
    server_password = secrets.token_urlsafe(24)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{supabase_url}/auth/v1/admin/users",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": "application/json",
            },
            json={
                "email": req.email,
                "password": server_password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": req.contact_name,
                    "business_name": req.business_name,
                    "org_id": org_id,
                    "role": "owner",
                    "portal": "canada",
                    "vertical": req.vertical,
                },
            },
        )
        if resp.status_code in (200, 201):
            auth_user_id = resp.json().get("id")
            logger.info(f"Created Canada customer auth user {auth_user_id} for {req.email}")
        elif resp.status_code == 422 and "already been registered" in resp.text.lower():
            logger.info(f"Auth user already exists for {req.email}")
        else:
            logger.error(f"Auth user creation failed: {resp.status_code} {resp.text}")
            raise HTTPException(400, "Could not create customer account")

    return {"ok": True, "org_id": org_id}


@router.post("/careers/apply")
async def submit_career_application(req: CareerApplication):
    return await submit_application(req, country="CA")


class SignSlaRequest(BaseModel):
    customer_email: EmailStr
    signature_name: str
    business_name: str | None = None
    province: str | None = None
    org_id: str | None = None
    monthly_price_cad_cents: int | None = None
    setup_fee_cad_cents: int | None = 0
    pos_system: str | None = None
    rep_id: str | None = None
    rep_name: str | None = None

    @field_validator("signature_name")
    @classmethod
    def validate_signature(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("signature must be at least 2 characters")
        return _sanitize_text(v)


@router.post("/sign-sla")
async def sign_sla(req: SignSlaRequest, request: Request, claims: dict = Depends(require_jwt)):
    """Persist a customer's SLA signature + trigger a confirmation email.

    Called by the Canada customer onboarding wizard's SLA step after the
    customer types their name and ticks the agreement checkbox. Requires a
    valid Supabase session (the customer just created their account in the
    previous step). RLS on sla_signatures restricts inserts to authenticated
    users only.
    """
    import httpx

    supabase_url = os.environ.get("SUPABASE_URL", "")
    if not supabase_url:
        raise HTTPException(503, "Supabase not configured")

    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    user_token = _user_token(request) or service_key
    anon_key = _get_anon_key() or service_key

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:500]

    row = {
        "customer_email": req.customer_email,
        "signature_name": req.signature_name.strip(),
        "business_name": req.business_name,
        "province": req.province,
        "org_id": req.org_id,
        "monthly_price_cad_cents": req.monthly_price_cad_cents,
        "setup_fee_cad_cents": req.setup_fee_cad_cents or 0,
        "pos_system": req.pos_system,
        "rep_id": req.rep_id,
        "rep_name": req.rep_name,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }

    signed_at = None
    async with httpx.AsyncClient(timeout=10.0) as client:
        ins_resp = await client.post(
            f"{supabase_url}/rest/v1/sla_signatures",
            headers={
                "Authorization": f"Bearer {user_token}",
                "apikey": anon_key,
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json=row,
        )
        if ins_resp.status_code not in (200, 201):
            logger.error("SLA signature insert failed: %s %s", ins_resp.status_code, ins_resp.text)
            raise HTTPException(500, "Could not save SLA signature — please try again")
        rows = ins_resp.json()
        signed_at = (rows[0].get("signed_at") if rows else None)

    # Send confirmation email (best-effort — signature persistence already succeeded)
    try:
        from ...email.send import send_sla_signed
        await send_sla_signed(
            to=req.customer_email,
            business_name=req.business_name or "",
            rep_name=req.rep_name or "",
            signed_by=req.signature_name.strip(),
            signed_date=(signed_at or "").split("T")[0] if signed_at else "",
            provider_signatory="Aidan Pierce, Founder & CEO",
            org_id=req.org_id,
        )
    except Exception as exc:
        logger.warning("SLA confirmation email failed for %s: %s", req.customer_email, exc)

    return {"ok": True, "signed_at": signed_at}


class RepActionRequest(BaseModel):
    rep_id: str
    admin_email: EmailStr


@router.post("/rep-approve")
async def approve_rep(req: RepActionRequest, request: Request, admin: dict = Depends(require_admin_jwt)):
    """Admin approves a pending rep — sets is_active=true, creates auth user if needed, sends credentials email."""
    _validate_rep_id(req.rep_id)

    import httpx
    import secrets
    import string

    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")
    # The caller has already been verified as an admin via require_admin_jwt
    # above. Use the service key for the write so all approved admins can
    # action approvals regardless of whether their user_id is listed in the
    # sales_reps UPDATE RLS policy. Defense-in-depth lives in
    # require_admin_jwt (ADMIN_EMAILS allowlist), not in PostgREST policies.
    # The Supabase /auth/v1/admin/users call further down also requires the
    # service key.

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. PATCH is_active = true and verify row was updated
        resp = await client.patch(
            f"{supabase_url}/rest/v1/sales_reps?id=eq.{req.rep_id}",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json={"is_active": True},
        )
        if resp.status_code not in (200, 204):
            logger.error("Rep approve PATCH failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(500, "Could not approve rep")

        updated_rows = resp.json() if resp.status_code == 200 else []
        if not updated_rows:
            logger.error("Rep approve: no rows matched id=%s", req.rep_id)
            raise HTTPException(404, "Rep not found — could not approve")

        rep_row = updated_rows[0]
        rep_email = rep_row.get("email", "")
        rep_name = rep_row.get("name", "")

        # 2. Create Supabase auth user if one doesn't exist yet
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        auth_created = False

        auth_resp = await client.post(
            f"{supabase_url}/auth/v1/admin/users",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": "application/json",
            },
            json={
                "email": rep_email,
                "password": temp_password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": rep_name,
                    "role": "sales_rep",
                    "portal": "canada",
                },
            },
        )
        if auth_resp.status_code in (200, 201):
            auth_created = True
            logger.info("Created auth user for approved rep %s", rep_email)
        elif auth_resp.status_code == 422 and "already been registered" in auth_resp.text.lower():
            logger.info("Auth user already exists for %s — skipping creation", rep_email)
        else:
            logger.warning("Auth user creation failed for %s: %s %s", rep_email, auth_resp.status_code, auth_resp.text)

    # 3. Send approval email (always — include temp password only for newly created auth users)
    email_sent = False
    if rep_email:
        try:
            from ...email.send import send_rep_credentials
            login_url = "https://meridian.tips/canada/portal/login"
            result = await send_rep_credentials(
                to=rep_email,
                rep_name=rep_name,
                email=rep_email,
                password=temp_password if auth_created else None,
                login_url=login_url,
            )
            email_sent = result.get("status") == "sent" or result.get("id") is not None
            logger.info("Sent approval email to %s: %s", rep_email, result.get("status"))
        except Exception as e:
            logger.error("Failed to send approval email to %s: %s", rep_email, e)

    logger.info("Rep approved: %s (%s) by %s", rep_name, rep_email, req.admin_email)
    return {"ok": True, "rep_id": req.rep_id, "email_sent": email_sent}


@router.post("/rep-reject")
async def reject_rep(req: RepActionRequest, request: Request, admin: dict = Depends(require_admin_jwt)):
    """Admin rejects a pending rep — deletes the sales_reps row."""
    _validate_rep_id(req.rep_id)

    import httpx
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{supabase_url}/rest/v1/sales_reps?id=eq.{req.rep_id}",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
            },
        )
        if resp.status_code not in (200, 204):
            logger.error("Rep reject failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(500, "Could not reject rep")

    return {"ok": True, "rep_id": req.rep_id}


class RepUpdateRequest(BaseModel):
    rep_id: str
    admin_email: EmailStr
    name: str | None = None
    commission_rate: float | None = None


@router.post("/rep-update")
async def update_rep(req: RepUpdateRequest, request: Request, admin: dict = Depends(require_admin_jwt)):
    """Admin updates a rep's name or commission rate."""
    _validate_rep_id(req.rep_id)

    import httpx
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    updates: dict = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.commission_rate is not None:
        updates["commission_rate"] = req.commission_rate
    if not updates:
        return {"ok": True, "rep_id": req.rep_id}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(
            f"{supabase_url}/rest/v1/sales_reps?id=eq.{req.rep_id}",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json=updates,
        )
        if resp.status_code not in (200, 204):
            logger.error("Rep update failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(500, "Could not update rep")

    return {"ok": True, "rep_id": req.rep_id}


@router.post("/rep-remove")
async def remove_rep(req: RepActionRequest, request: Request, admin: dict = Depends(require_admin_jwt)):
    """Admin removes an active rep from the team — deletes the sales_reps row."""
    _validate_rep_id(req.rep_id)

    import httpx
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{supabase_url}/rest/v1/sales_reps?id=eq.{req.rep_id}",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
            },
        )
        if resp.status_code not in (200, 204):
            logger.error("Rep remove failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(500, "Could not remove rep")

    logger.info("Rep removed: %s by %s", req.rep_id, req.admin_email)
    return {"ok": True, "rep_id": req.rep_id}


@router.get("/leads")
async def get_leads(request: Request, user: dict = Depends(require_jwt)):
    """Return all Canada deals/leads. Tries 'deals' table, falls back to 'data_sales'."""
    import httpx
    supabase_url = os.environ.get("SUPABASE_URL", "")
    anon_key = _get_anon_key()

    # Extract the user's JWT from the Authorization header to enforce RLS
    auth_header = request.headers.get("authorization", "")
    user_token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""

    if not supabase_url or not user_token:
        return {"leads": []}

    headers = {"Authorization": f"Bearer {user_token}", "apikey": anon_key}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/deals?order=created_at.desc&select=*",
            headers=headers,
        )
        if resp.status_code == 200:
            return {"leads": resp.json()}

        resp = await client.get(
            f"{supabase_url}/rest/v1/data_sales?order=created_at.desc&select=*",
            headers=headers,
        )
        if resp.status_code == 200:
            return {"leads": resp.json()}

        return {"leads": []}


@router.get("/stats")
async def get_stats(request: Request, user: dict = Depends(require_jwt)):
    """Aggregate Canada sales stats: rep count, deal count, revenue pipeline."""
    import httpx
    supabase_url = os.environ.get("SUPABASE_URL", "")
    anon_key = _get_anon_key()

    # Extract the user's JWT from the Authorization header to enforce RLS
    auth_header = request.headers.get("authorization", "")
    user_token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""

    if not supabase_url or not user_token:
        return {"total_reps": 0, "active_reps": 0, "total_leads": 0, "pipeline_cents": 0}

    headers = {"Authorization": f"Bearer {user_token}", "apikey": anon_key}

    async with httpx.AsyncClient(timeout=10.0) as client:
        reps_resp = await client.get(
            f"{supabase_url}/rest/v1/sales_reps?portal_context=in.(canada,all)&select=id,is_active,commission_rate",
            headers=headers,
        )

    reps = reps_resp.json() if reps_resp.status_code == 200 else []
    active_reps = sum(1 for r in reps if r.get("is_active"))

    return {
        "total_reps": len(reps),
        "active_reps": active_reps,
    }


@router.get("/team")
async def get_team(request: Request, user: dict = Depends(require_jwt)):
    """Return all Canada sales reps (enforces RLS via user JWT)."""
    import httpx
    supabase_url = os.environ.get("SUPABASE_URL", "")
    anon_key = _get_anon_key()

    # Extract the user's JWT from the Authorization header to enforce RLS
    auth_header = request.headers.get("authorization", "")
    user_token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""

    if not supabase_url or not user_token:
        return {"reps": [], "applicants": []}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/sales_reps?portal_context=in.(canada,all)&order=created_at.asc&select=id,name,email,phone,commission_rate,is_active,created_at,portal_context",
            headers={
                "Authorization": f"Bearer {user_token}",
                "apikey": anon_key,
            },
        )
        if resp.status_code != 200:
            logger.error("Team fetch failed: %s", resp.text)
            return {"reps": [], "applicants": []}

        rows = resp.json()

    reps = [r for r in rows if r.get("is_active")]
    applicants = [r for r in rows if not r.get("is_active")]
    return {"reps": reps, "applicants": applicants}
