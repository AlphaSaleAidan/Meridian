"""
US Sales Portal Routes — rep management + customer onboarding for US market.

  POST /api/us/rep-signup       → Create a new US sales rep
  POST /api/us/create-customer  → Create Supabase Auth user for a US customer
  GET  /api/us/team             → List all US reps (active + applicants)
  POST /api/us/rep-approve      → Admin approves a pending rep
  POST /api/us/rep-reject       → Admin rejects a pending rep
  POST /api/us/rep-update       → Admin updates rep name/commission
  GET  /api/us/leads            → List US deals
  GET  /api/us/stats            → Aggregate US sales stats
"""
import logging
import os
import re
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator

from ..auth import (
    ADMIN_EMAILS as ALL_ADMIN_EMAILS,
    require_service_auth,
    require_jwt,
    require_admin_jwt,
)

logger = logging.getLogger("meridian.api.us")

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _validate_rep_id(rep_id: str) -> None:
    """Validate rep_id is a proper UUID to prevent PostgREST filter injection."""
    if not _UUID_RE.match(rep_id):
        raise HTTPException(status_code=400, detail="Invalid rep_id format")

router = APIRouter(prefix="/api/us", tags=["us"])

US_ORG_ID = "us-org-00000000-0000-0000-0000-000000000001"

# US portal admin scope is INTENTIONALLY NARROWER than the canada/compliance
# scope defined in src/api/auth.py:ADMIN_EMAILS. Per business policy, US
# portal admin = Aidan Pierce only (across all his email addresses). Enoch
# Cheung and Aidan Nguyen are Canada/compliance admins and must NOT be
# granted US write access. Do NOT collapse this back to ALL_ADMIN_EMAILS —
# if you need both lists to be the same, change US policy first.
#
# The intersection-with-centralized pattern means removing an admin from
# auth.py automatically removes them here too, while the explicit allowlist
# below controls who *can* be a US admin.
_US_ADMIN_ALLOWLIST = {
    "apierce@alphasale.co",
    "aidanpierce72@gmail.com",
    "aidanpierce@meridian.tips",
}
ADMIN_EMAILS = [e for e in ALL_ADMIN_EMAILS if e in _US_ADMIN_ALLOWLIST]
# NOTE: ADMIN_EMAILS is not yet referenced elsewhere in this module — it
# exists as the policy artifact for when US admin gating gets wired up.
# A per-scope role-tags refactor is filed as a follow-up issue.


def _sanitize_text(v: str) -> str:
    import re
    v = re.sub(r'<[^>]+>', '', v)
    v = v.replace('&', '&amp;').replace('"', '&quot;').replace("'", '&#x27;')
    return v.strip()


def _supabase_creds() -> tuple[str, str]:
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")
    return supabase_url, service_key


def _headers(service_key: str) -> dict:
    return {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Content-Type": "application/json",
    }


def _get_anon_key() -> str:
    """Get the Supabase anon key from env (public key, safe to embed as fallback)."""
    return (
        os.environ.get("SUPABASE_ANON_KEY", "")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
        or os.environ.get("VITE_SUPABASE_ANON_KEY", "")
    )


def _user_token(request) -> str:
    """Extract the Bearer token from the incoming Authorization header so we can
    forward the caller's JWT to Supabase REST (RLS enforced as the user)."""
    auth_header = request.headers.get("authorization", "") or request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()
    return ""


# ── Request Models ──────────────────────────────────────────


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
    # Optional — the sales-portal create-customer flow deliberately omits
    # password and lets the customer set it via Supabase resetPasswordForEmail.
    # When omitted, the route generates a high-entropy throwaway server-side.
    password: str | None = None
    business_name: str
    contact_name: str
    phone: str | None = None
    vertical: str | None = None
    deal_id: str | None = None
    monthly_price: int = 0

    @field_validator("business_name", "contact_name")
    @classmethod
    def sanitize_names(cls, v: str) -> str:
        return _sanitize_text(v)

    @field_validator("password")
    @classmethod
    def validate_customer_password(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class SignSlaRequest(BaseModel):
    customer_email: EmailStr
    signature_name: str
    business_name: str | None = None
    state: str | None = None
    org_id: str | None = None
    monthly_price_usd_cents: int | None = None
    setup_fee_usd_cents: int | None = 0
    pos_system: str | None = None
    rep_id: str | None = None
    rep_name: str | None = None

    @field_validator("signature_name")
    @classmethod
    def validate_signature(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("signature must be at least 2 characters")
        return _sanitize_text(v)


class RepActionRequest(BaseModel):
    rep_id: str
    admin_email: EmailStr


class RepUpdateRequest(BaseModel):
    rep_id: str
    admin_email: EmailStr
    name: str | None = None
    commission_rate: float | None = None


# ── Endpoints ───────────────────────────────────────────────


@router.post("/rep-signup")
async def rep_signup(req: RepSignupRequest):
    import httpx

    supabase_url, service_key = _supabase_creds()

    async with httpx.AsyncClient(timeout=15.0) as client:
        auth_resp = await client.post(
            f"{supabase_url}/auth/v1/admin/users",
            headers=_headers(service_key),
            json={
                "email": req.email,
                "password": req.password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": req.name,
                    "role": "sales_rep",
                    "portal": "us",
                },
            },
        )
        if auth_resp.status_code not in (200, 201):
            if auth_resp.status_code == 422 and "already been registered" in auth_resp.text.lower():
                logger.info("Auth user already exists for %s", req.email)
            else:
                logger.error("Rep auth creation failed: %s %s", auth_resp.status_code, auth_resp.text)
                raise HTTPException(400, auth_resp.json().get("msg", "Could not create account"))

        rep_resp = await client.post(
            f"{supabase_url}/rest/v1/sales_reps",
            headers={**_headers(service_key), "Prefer": "return=representation,resolution=merge-duplicates"},
            json={
                "org_id": US_ORG_ID,
                "name": req.name,
                "email": req.email,
                "phone": req.phone or "",
                "commission_rate": 0.70,
                "is_active": False,
                "portal_context": "us",
            },
        )
        if rep_resp.status_code not in (200, 201):
            logger.error("sales_reps insert failed: %s %s", rep_resp.status_code, rep_resp.text)
            raise HTTPException(400, "Account created but rep profile failed. Contact admin.")

        rep_data = rep_resp.json()
        rep_row = rep_data[0] if isinstance(rep_data, list) else rep_data

    logger.info("New US rep signed up: %s (%s)", req.name, req.email)
    return {"ok": True, "rep_id": rep_row.get("id"), "name": req.name, "email": req.email}


@router.post("/create-customer")
async def create_customer(req: CreateCustomerRequest, _auth=Depends(require_service_auth)):
    import httpx

    supabase_url, service_key = _supabase_creds()
    org_id = str(uuid.uuid4())

    # When the caller omits a password, generate a high-entropy throwaway. The
    # customer never sees it — handleCreateCustomerAccount in the frontend
    # immediately triggers Supabase resetPasswordForEmail so the user sets
    # their own via the secure link. Supabase admin user creation still
    # requires *some* password, so we provide one rather than leaving it null.
    password = req.password or secrets.token_urlsafe(32)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{supabase_url}/auth/v1/admin/users",
            headers=_headers(service_key),
            json={
                "email": req.email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": req.contact_name,
                    "business_name": req.business_name,
                    "org_id": org_id,
                    "role": "owner",
                    "portal": "us",
                    "vertical": req.vertical,
                },
            },
        )
        if resp.status_code in (200, 201):
            auth_user_id = resp.json().get("id")
            logger.info("Created US customer auth user %s for %s", auth_user_id, req.email)
        elif resp.status_code == 422 and "already been registered" in resp.text.lower():
            logger.info("Auth user already exists for %s", req.email)
        else:
            logger.error("Auth user creation failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(400, "Could not create customer account")

    return {"ok": True, "org_id": org_id}


@router.post("/sign-sla")
async def sign_sla(req: SignSlaRequest, request: Request, claims: dict = Depends(require_jwt)):
    """Persist a US customer's SLA signature + trigger a confirmation email.

    Mirrors the Canada handler. Writes US data into the country='US' columns
    (state, monthly_price_usd_cents, setup_fee_usd_cents) added in migration
    20260531_sla_signatures_us_columns.sql.
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
        "country": "US",
        "customer_email": req.customer_email,
        "signature_name": req.signature_name.strip(),
        "business_name": req.business_name,
        "state": req.state,
        "org_id": req.org_id,
        "monthly_price_usd_cents": req.monthly_price_usd_cents,
        "setup_fee_usd_cents": req.setup_fee_usd_cents or 0,
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
            logger.error("US SLA signature insert failed: %s %s", ins_resp.status_code, ins_resp.text)
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
        logger.warning("US SLA confirmation email failed for %s: %s", req.customer_email, exc)

    return {"ok": True, "signed_at": signed_at}


@router.get("/team")
async def get_team(request: Request, user: dict = Depends(require_jwt)):
    """Return all US sales reps (enforces RLS via user JWT)."""
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
            f"{supabase_url}/rest/v1/sales_reps?portal_context=in.(us,all)&order=created_at.asc"
            "&select=id,name,email,phone,commission_rate,is_active,created_at,portal_context",
            headers={
                "Authorization": f"Bearer {user_token}",
                "apikey": anon_key,
            },
        )
        if resp.status_code != 200:
            logger.error("US team fetch failed: %s", resp.text)
            return {"reps": [], "applicants": []}

        rows = resp.json()

    reps = [r for r in rows if r.get("is_active")]
    applicants = [r for r in rows if not r.get("is_active")]
    return {"reps": reps, "applicants": applicants}


@router.post("/rep-approve")
async def approve_rep(req: RepActionRequest, admin: dict = Depends(require_admin_jwt)):
    _validate_rep_id(req.rep_id)

    import httpx
    import secrets
    import string

    supabase_url, service_key = _supabase_creds()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.patch(
            f"{supabase_url}/rest/v1/sales_reps?id=eq.{req.rep_id}",
            headers={**_headers(service_key), "Prefer": "return=representation"},
            json={"is_active": True},
        )
        if resp.status_code not in (200, 204):
            logger.error("US rep approve PATCH failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(500, "Could not approve rep")

        updated_rows = resp.json() if resp.status_code == 200 else []
        if not updated_rows:
            raise HTTPException(404, "Rep not found")

        rep_row = updated_rows[0]
        rep_email = rep_row.get("email", "")
        rep_name = rep_row.get("name", "")

        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        auth_created = False

        auth_resp = await client.post(
            f"{supabase_url}/auth/v1/admin/users",
            headers=_headers(service_key),
            json={
                "email": rep_email,
                "password": temp_password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": rep_name,
                    "role": "sales_rep",
                    "portal": "us",
                },
            },
        )
        if auth_resp.status_code in (200, 201):
            auth_created = True
        elif auth_resp.status_code == 422 and "already been registered" in auth_resp.text.lower():
            logger.info("Auth user already exists for %s", rep_email)
        else:
            logger.warning("Auth user creation failed for %s: %s", rep_email, auth_resp.status_code)

    email_sent = False
    if rep_email:
        try:
            from ...email.send import send_rep_credentials
            login_url = "https://meridian.tips/us/portal/login"
            result = await send_rep_credentials(
                to=rep_email,
                rep_name=rep_name,
                email=rep_email,
                password=temp_password if auth_created else None,
                login_url=login_url,
            )
            email_sent = result.get("status") == "sent" or result.get("id") is not None
        except Exception as e:
            logger.error("Failed to send US approval email to %s: %s", rep_email, e)

    logger.info("US rep approved: %s (%s) by %s", rep_name, rep_email, req.admin_email)
    return {"ok": True, "rep_id": req.rep_id, "email_sent": email_sent}


@router.post("/rep-reject")
async def reject_rep(req: RepActionRequest, admin: dict = Depends(require_admin_jwt)):
    _validate_rep_id(req.rep_id)

    import httpx

    supabase_url, service_key = _supabase_creds()

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{supabase_url}/rest/v1/sales_reps?id=eq.{req.rep_id}",
            headers=_headers(service_key),
        )
        if resp.status_code not in (200, 204):
            logger.error("US rep reject failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(500, "Could not reject rep")

    return {"ok": True, "rep_id": req.rep_id}


@router.post("/rep-update")
async def update_rep(req: RepUpdateRequest, admin: dict = Depends(require_admin_jwt)):
    _validate_rep_id(req.rep_id)

    import httpx

    supabase_url, service_key = _supabase_creds()

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
            headers={**_headers(service_key), "Prefer": "return=representation"},
            json=updates,
        )
        if resp.status_code not in (200, 204):
            logger.error("US rep update failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(500, "Could not update rep")

    return {"ok": True, "rep_id": req.rep_id}


@router.post("/rep-remove")
async def remove_rep(req: RepActionRequest, admin: dict = Depends(require_admin_jwt)):
    """Admin removes an active rep from the team — deletes the sales_reps row."""
    _validate_rep_id(req.rep_id)

    import httpx

    supabase_url, service_key = _supabase_creds()

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{supabase_url}/rest/v1/sales_reps?id=eq.{req.rep_id}",
            headers=_headers(service_key),
        )
        if resp.status_code not in (200, 204):
            logger.error("US rep remove failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(500, "Could not remove rep")

    logger.info("US rep removed: %s by %s", req.rep_id, req.admin_email)
    return {"ok": True, "rep_id": req.rep_id}


@router.get("/leads")
async def get_leads(request: Request, user: dict = Depends(require_jwt)):
    """Return all US leads (enforces RLS via user JWT)."""
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
            f"{supabase_url}/rest/v1/us_leads?order=created_at.desc&select=*",
            headers=headers,
        )
        if resp.status_code == 200:
            return {"leads": resp.json()}

    return {"leads": []}


@router.get("/stats")
async def get_stats(request: Request, user: dict = Depends(require_jwt)):
    """Aggregate US sales stats (enforces RLS via user JWT)."""
    import httpx

    supabase_url = os.environ.get("SUPABASE_URL", "")
    anon_key = _get_anon_key()

    # Extract the user's JWT from the Authorization header to enforce RLS
    auth_header = request.headers.get("authorization", "")
    user_token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""

    if not supabase_url or not user_token:
        return {"total_reps": 0, "active_reps": 0}

    headers = {"Authorization": f"Bearer {user_token}", "apikey": anon_key}

    async with httpx.AsyncClient(timeout=10.0) as client:
        reps_resp = await client.get(
            f"{supabase_url}/rest/v1/sales_reps?portal_context=in.(us,all)&select=id,is_active",
            headers=headers,
        )

    reps = reps_resp.json() if reps_resp.status_code == 200 else []
    active_reps = sum(1 for r in reps if r.get("is_active"))

    return {"total_reps": len(reps), "active_reps": active_reps}
