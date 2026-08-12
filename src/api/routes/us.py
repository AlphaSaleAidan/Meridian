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
    require_jwt,
    rate_limit_signup,
)
from .. import hierarchy
from ._supabase_admin import delete_auth_user_by_email

logger = logging.getLogger("meridian.api.us")

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _validate_rep_id(rep_id: str) -> None:
    """Validate rep_id is a proper UUID to prevent PostgREST filter injection."""
    if not _UUID_RE.match(rep_id):
        raise HTTPException(status_code=400, detail="Invalid rep_id format")

router = APIRouter(prefix="/api/us", tags=["us"])

# sales_reps.org_id is a uuid column, so this MUST be a valid UUID. The old
# "us-org-0000…" placeholder failed the uuid cast, so every US rep-signup
# created the auth user but then 400'd on the sales_reps insert ("Account
# created but rep profile failed"). Use the real Meridian org UUID — the same
# org_id every existing US rep already carries — so new US reps match them.
US_ORG_ID = "168b6df2-e9af-4b00-8fec-51e51149ff19"

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


async def require_us_admin(user: dict = Depends(require_jwt)) -> dict:
    """US-admin gate — INTENTIONALLY narrower than auth.require_admin_jwt.

    require_admin_jwt checks the global ADMIN_EMAILS (which includes the
    Canada/compliance admins), so using it on US rep-management endpoints let
    Enoch Cheung / Aidan Nguyen approve/reject/remove US reps — contrary to the
    stated US policy (US admin = Aidan Pierce only). Gate on the US-scoped
    ADMIN_EMAILS list above instead. This wires in what was previously a
    documented-but-unreferenced policy artifact.
    """
    email = (user.get("email") or "").lower()
    if email not in [e.lower() for e in ADMIN_EMAILS]:
        logger.warning("US admin access denied for %s", email)
        raise HTTPException(403, "US admin access required")
    return user


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
    # Rep fee slider (mirrors canada.create_customer): chosen plan + per-order
    # Meridian fee in cents (USD). None = tier default; server re-clamps to the
    # tier redline (premium ≥ 65¢, command ≥ 45¢).
    plan_id: str | None = None
    order_fee_cents: int | None = None
    # Pricing model chosen by the rep at close (mirrors canada.py, migration
    # 077): None/'per_order' = per-order fee model; 'zero_per_order' = minutes
    # licensing — order fee forced to 0, monthly minute bucket + overage.
    pricing_model: str | None = None

    @field_validator("pricing_model")
    @classmethod
    def validate_pricing_model(cls, v: str | None) -> str | None:
        if v is not None and v not in ("per_order", "zero_per_order"):
            raise ValueError("pricing_model must be per_order or zero_per_order")
        return v

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


@router.post("/rep-signup", dependencies=[Depends(rate_limit_signup)])
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
                # Store lowercased so every email-join (the JWT claim is
                # lowercased by Supabase auth) matches — a mixed-case row
                # silently breaks rep entitlement + commission lookups. Mirrors
                # the Canada path (canada.py). See fix/sales-rep-email-case.
                "email": (req.email or "").strip().lower(),
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
async def create_customer(req: CreateCustomerRequest, caller: dict = Depends(require_jwt)):
    """Create (or reset) a US customer login with a rep-shareable temp password.

    Mirrors /api/canada/create-customer: the temp password + must_reset_password
    metadata flag replace the old client-side resetPasswordForEmail flow, which
    silently never delivered (Supabase project has no custom SMTP; built-in
    mailer is dev-only and rate-limited to 2/hour). Gated on require_jwt (the rep's
    own token) to match Canada and drop the broader X-Admin-Key/service-token path.
    """
    import httpx

    from .canada import _generate_temp_password

    supabase_url, service_key = _supabase_creds()
    org_id = str(uuid.uuid4())
    auth_user_id = None
    fee_parity = {"fee_terms_locked": False, "billing_terms_recorded": False}

    logger.info("US create-customer requested by %s for %s", caller.get("email"), req.email)

    temp_password = req.password or _generate_temp_password()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{supabase_url}/auth/v1/admin/users",
            headers=_headers(service_key),
            json={
                "email": req.email,
                "password": temp_password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": req.contact_name,
                    "business_name": req.business_name,
                    "org_id": org_id,
                    "role": "owner",
                    "portal": "us",
                    "vertical": req.vertical,
                    "must_reset_password": True,
                },
            },
        )
        if resp.status_code in (200, 201):
            auth_user_id = resp.json().get("id")
            logger.info("Created US customer auth user %s for %s", auth_user_id, req.email)
        elif resp.status_code == 422 and "already been registered" in resp.text.lower():
            logger.info("Auth user already exists for %s — resetting temp password", req.email)
            # Page through the admin user list to find the existing account.
            existing_id = None
            existing_meta: dict = {}
            for page in range(1, 21):  # up to 20 pages * 200 = 4000 users
                list_resp = await client.get(
                    f"{supabase_url}/auth/v1/admin/users",
                    headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
                    params={"page": page, "per_page": 200},
                )
                if list_resp.status_code != 200:
                    logger.error("Admin user list failed p%s: %s %s", page, list_resp.status_code, list_resp.text[:200])
                    break
                users = list_resp.json().get("users", [])
                for u in users:
                    if u.get("email", "").lower() == req.email.lower():
                        existing_id = u["id"]
                        existing_meta = u.get("user_metadata") or {}
                        break
                if existing_id or len(users) < 200:
                    break
            if not existing_id:
                logger.error("Existing auth user for %s not found in admin list — cannot reset password", req.email)
                raise HTTPException(500, "Customer account exists but could not be updated")
            # Takeover guard (same as Canada): a rep must never be able to rotate
            # the password of an admin, a rep, or any non-US-customer account.
            existing_role = (existing_meta.get("role") or "").lower()
            existing_portal = (existing_meta.get("portal") or "").lower()
            if req.email.lower() in [e.lower() for e in ALL_ADMIN_EMAILS]:
                logger.warning("us create-customer reset BLOCKED: targeted admin account %s", req.email)
                raise HTTPException(403, "This account cannot be managed from the rep portal")
            if existing_role not in ("owner", "") or (existing_portal and existing_portal != "us"):
                logger.warning(
                    "us create-customer reset BLOCKED: targeted role=%r portal=%r account %s",
                    existing_role, existing_portal, req.email,
                )
                raise HTTPException(403, "This account cannot be managed from the rep portal")
            # Merge so we don't wipe org_id/role/portal on an existing user.
            merged_meta = {**existing_meta, "must_reset_password": True}
            org_id = existing_meta.get("org_id", org_id)
            put_resp = await client.put(
                f"{supabase_url}/auth/v1/admin/users/{existing_id}",
                headers={"Authorization": f"Bearer {service_key}", "apikey": service_key, "Content-Type": "application/json"},
                json={"password": temp_password, "user_metadata": merged_meta},
            )
            if put_resp.status_code not in (200, 201):
                logger.error("Password/flag reset PUT failed for %s: %s %s", req.email, put_resp.status_code, put_resp.text[:200])
                raise HTTPException(502, "Could not update customer account password")
            logger.info("Reset OK for %s (id=%s)", req.email, existing_id)
            auth_user_id = existing_id
        else:
            logger.error("Auth user creation failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(400, "Could not create customer account")

        # Link the customer to a business record so the portal can load their org
        # on login. Without this row fetchBusinessForUser returns null, org stays
        # null, and ProtectedRoute bounces the customer back to /us/login even
        # after a successful login. Mirrors canada.create_customer + provision_customer.
        if auth_user_id:
            biz_resp = await client.post(
                f"{supabase_url}/rest/v1/businesses",
                headers={
                    "Authorization": f"Bearer {service_key}",
                    "apikey": service_key,
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal,resolution=merge-duplicates",
                },
                json={
                    "id": org_id,
                    "owner_user_id": auth_user_id,
                    "name": req.business_name,
                    "owner_name": req.contact_name,
                    "email": req.email,
                    "phone": req.phone or "",
                    "plan_tier": "trial",
                    "business_type": req.vertical or "restaurant",
                    "pos_connected": False,
                    "onboarded": False,
                    "status": "active",
                },
            )
            if biz_resp.status_code not in (200, 201, 204):
                logger.error(
                    "businesses upsert failed for %s: %s %s",
                    req.email, biz_resp.status_code, biz_resp.text[:200],
                )
                raise HTTPException(500, "Customer account created but business profile failed to save")
            logger.info("Linked business %s -> user %s for %s", org_id, auth_user_id, req.email)

            # Fee parity: lock the deal terms on the us_leads row + record the
            # billing contract for the new org (shared helper in canada.py).
            from .canada import _provision_fee_terms
            fee_parity = await _provision_fee_terms(
                market="us",
                org_id=org_id,
                deal_id=req.deal_id,
                plan_id=req.plan_id,
                monthly_price=req.monthly_price,
                order_fee_cents=req.order_fee_cents,
                locked_by=caller.get("email") or caller.get("id", ""),
                pricing_model=req.pricing_model,
            )

            # Commission accrual (US) — path wired in lockstep with Canada
            # (canada.py). Gated on us_commission_live() which DEFAULTS OFF: the
            # rep's M0-M3 milestone schedule is written the moment a deal closes
            # only once US comp terms are ratified and COMMISSION_ENGINE_US_LIVE=1
            # is set. Rep resolved from the closing rep's verified JWT email;
            # package = nearest price-point. Best-effort + idempotent
            # (UNIQUE(account_id,milestone)) — a hiccup here must NEVER fail
            # customer creation. Milestones are 'pending'/'earned', never
            # auto-PAID; settlement stays quarterly + gated.
            try:
                from ...services.commission_engine import (
                    CommissionEngineService,
                    us_commission_live,
                )
                from datetime import datetime, timezone

                if us_commission_live() and req.monthly_price:
                    from ...db import get_db as _get_commission_db

                    _csvc = CommissionEngineService(db=_get_commission_db())
                    await _csvc.accrue_for_us_close(
                        account_id=org_id,
                        rep_email=caller.get("email") or "",
                        negotiated_monthly_cents=req.monthly_price * 100,
                        close_date=datetime.now(timezone.utc).date(),
                    )
            except Exception as e:  # noqa: BLE001 — never fail customer creation
                logger.error("US commission accrual failed for org %s: %s", org_id, e)

            # Rep fee slider — pre-seed phone_agent_config with the negotiated
            # per-order fee (mirrors canada.create_customer). Best-effort: a
            # seed failure never fails customer creation.
            # Zero-per-order (minutes plan): seed fee=0, skip the redline
            # clamp — mirrors canada.create_customer.
            from ...billing.fee_terms import normalize_pricing_model
            _zero_per_order = normalize_pricing_model(req.pricing_model) == "zero_per_order"
            if _zero_per_order:
                _seed_fee: int | None = 0
            elif req.order_fee_cents is not None:
                from .canada import _clamp_order_fee_cents
                _seed_fee = _clamp_order_fee_cents(req.order_fee_cents, req.plan_id,
                                                   market="us")
            else:
                _seed_fee = None
            if _seed_fee is not None:
                fee = _seed_fee
                fee_seeded = False
                try:
                    pac_headers = {
                        "Authorization": f"Bearer {service_key}",
                        "apikey": service_key,
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal",
                    }
                    existing = await client.get(
                        f"{supabase_url}/rest/v1/phone_agent_config",
                        headers=pac_headers,
                        params={"merchant_id": f"eq.{org_id}", "select": "id"},
                    )
                    seed = {"order_fee_cents": fee}
                    if req.plan_id:
                        seed["plan_tier"] = (req.plan_id or "").strip().lower()
                    if existing.status_code == 200 and existing.json():
                        pac_resp = await client.patch(
                            f"{supabase_url}/rest/v1/phone_agent_config?merchant_id=eq.{org_id}",
                            headers=pac_headers, json=seed,
                        )
                    else:
                        pac_resp = await client.post(
                            f"{supabase_url}/rest/v1/phone_agent_config",
                            headers=pac_headers,
                            json={
                                "merchant_id": org_id,
                                "business_name": req.business_name,
                                "business_type": req.vertical or "restaurant",
                                "active": False,
                                **seed,
                            },
                        )
                    if pac_resp.status_code in (200, 201, 204):
                        fee_seeded = True
                        logger.info("Seeded order fee %d¢ (plan=%s) for %s",
                                    fee, req.plan_id or "-", org_id)
                    else:
                        logger.error("order-fee seed failed for %s: %s %s",
                                     org_id, pac_resp.status_code, pac_resp.text[:200])
                except Exception as e:  # noqa: BLE001
                    logger.error("order-fee seed failed for %s: %s", org_id, e)
                # Surface a seed failure so the rep knows the negotiated fee
                # fell back to the tier default (mirrors canada.create_customer).
                return {"ok": True, "org_id": org_id,
                        # Return BOTH keys: US portal pages read a mix of
                        # temp_password / temporary_password (Canada uses the
                        # latter). Aliasing both removes the drift without a
                        # coordinated frontend deploy.
                        "temp_password": temp_password,
                        "temporary_password": temp_password,
                        "fee_seeded": fee_seeded, "order_fee_cents": fee,
                        **fee_parity}

    return {"ok": True, "org_id": org_id,
            "temp_password": temp_password,
            "temporary_password": temp_password,
            **fee_parity}


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

    base_cols = "id,name,email,phone,commission_rate,is_active,created_at,portal_context"
    hier_cols = base_cols + ",role,manager_id,path,level,region"
    headers = {"Authorization": f"Bearer {user_token}", "apikey": anon_key}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/sales_reps?portal_context=in.(us,all)&order=created_at.asc"
            f"&select={hier_cols}",
            headers=headers,
        )
        if resp.status_code != 200:
            # Pre-migration prod: hierarchy columns unknown → legacy column set.
            resp = await client.get(
                f"{supabase_url}/rest/v1/sales_reps?portal_context=in.(us,all)&order=created_at.asc"
                f"&select={base_cols}",
                headers=headers,
            )
        if resp.status_code != 200:
            logger.error("US team fetch failed: %s", resp.text)
            return {"reps": [], "applicants": []}

        rows = resp.json()

    # Backend scoping plane (independent of RLS): subtree + upline only,
    # then the region fence (region members ↔ core never see each other).
    scope = await hierarchy.resolve_scope(user)
    allowed = await hierarchy.visible_rep_ids(scope)
    rows = hierarchy.scope_roster_rows(rows, scope, allowed)
    rows = hierarchy.partition_by_region(rows, scope)

    reps = [r for r in rows if r.get("is_active")]
    applicants = [r for r in rows if not r.get("is_active")]
    return {
        "reps": reps,
        "applicants": applicants,
        "viewer": {"role": scope.role, "rep_id": scope.rep_id, "is_admin": scope.is_admin,
                   "region": scope.region},
    }


@router.post("/rep-approve")
async def approve_rep(req: RepActionRequest, admin: dict = Depends(require_us_admin)):
    _validate_rep_id(req.rep_id)

    import httpx
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
async def reject_rep(req: RepActionRequest, admin: dict = Depends(require_us_admin)):
    _validate_rep_id(req.rep_id)

    import httpx

    supabase_url, service_key = _supabase_creds()

    async with httpx.AsyncClient(timeout=20.0) as client:
        # return=representation gives us the deleted row (incl. email) so we can
        # also tear down the Supabase auth login below — without it a rejected
        # applicant could just sign in again and re-create their rep row.
        resp = await client.delete(
            f"{supabase_url}/rest/v1/sales_reps?id=eq.{req.rep_id}",
            headers={**_headers(service_key), "Prefer": "return=representation"},
        )
        if resp.status_code not in (200, 204):
            logger.error("US rep reject failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(500, "Could not reject rep")

        deleted = resp.json() if (resp.status_code == 200 and resp.text) else []
        rep_email = deleted[0].get("email", "") if deleted else ""
        login_removed, login_detail = False, "no_email"
        if rep_email:
            login_removed, login_detail = await delete_auth_user_by_email(
                client, supabase_url, service_key, rep_email, protected_emails=ALL_ADMIN_EMAILS,
            )

    return {"ok": True, "rep_id": req.rep_id, "login_removed": login_removed, "login_detail": login_detail}


@router.post("/rep-update")
async def update_rep(req: RepUpdateRequest, admin: dict = Depends(require_us_admin)):
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
async def remove_rep(req: RepActionRequest, admin: dict = Depends(require_us_admin)):
    """Admin removes a rep from the team.

    Deletes the sales_reps row AND the underlying Supabase auth login (best
    effort) so the account cannot reappear on next sign-in. Real merchant-owner
    accounts are protected automatically: their auth user can't be deleted while
    a `businesses.owner_user_id` FK still references it, so the auth delete
    fails gracefully and only the rep row is removed.
    """
    _validate_rep_id(req.rep_id)

    import httpx

    supabase_url, service_key = _supabase_creds()

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.delete(
            f"{supabase_url}/rest/v1/sales_reps?id=eq.{req.rep_id}",
            headers={**_headers(service_key), "Prefer": "return=representation"},
        )
        if resp.status_code not in (200, 204):
            logger.error("US rep remove failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(500, "Could not remove rep")

        deleted = resp.json() if (resp.status_code == 200 and resp.text) else []
        rep_email = deleted[0].get("email", "") if deleted else ""
        login_removed, login_detail = False, "no_email"
        if rep_email:
            login_removed, login_detail = await delete_auth_user_by_email(
                client, supabase_url, service_key, rep_email, protected_emails=ALL_ADMIN_EMAILS,
            )

    logger.info("US rep removed: %s by %s (login_removed=%s, %s)", req.rep_id, req.admin_email, login_removed, login_detail)
    return {"ok": True, "rep_id": req.rep_id, "login_removed": login_removed, "login_detail": login_detail}


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

    rows: list = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/us_leads?order=created_at.desc&select=*",
            headers=headers,
        )
        if resp.status_code == 200:
            rows = resp.json()

    # Backend scoping plane. For us_leads this is the PRIMARY hierarchy guard
    # today: the 20260716 migration left us_leads policies alone, but the US
    # portal ALSO reads us_leads directly via Supabase (us-leads-service.ts),
    # which this plane cannot cover — the mirror RLS policy is authored in
    # 20260717_us_leads_downline_read.sql (NOT applied yet).
    scope = await hierarchy.resolve_scope(user)
    allowed = await hierarchy.visible_rep_ids(scope)
    return {"leads": hierarchy.scope_lead_rows(rows, allowed)}


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
