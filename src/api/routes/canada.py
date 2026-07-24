"""
Canada-specific Routes — Careers applications and Canada portal endpoints.

  POST /api/canada/careers/apply    → Submit a Canadian sales application
  POST /api/canada/create-customer  → Create Supabase Auth user for a Canada customer
"""
import logging
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator

from ..auth import ADMIN_EMAILS, require_jwt, require_admin_jwt, rate_limit_signup
from .. import hierarchy
from ...billing.fee_terms import ORDER_FEE_CAP_CENTS, ORDER_FEE_FLOOR_CENTS
from .careers import submit_application, CareerApplication
from ._supabase_admin import delete_auth_user_by_email

logger = logging.getLogger("meridian.api.canada")

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _validate_rep_id(rep_id: str) -> None:
    """Validate rep_id is a proper UUID to prevent PostgREST filter injection."""
    if not _UUID_RE.match(rep_id):
        raise HTTPException(status_code=400, detail="Invalid rep_id format")


def _generate_temp_password() -> str:
    """Generate a readable temporary password like 'Mer-7kX9pQ2m'."""
    import secrets
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    return "Mer-" + "".join(secrets.choice(chars) for _ in range(8))

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
    # Rep fee slider: chosen plan + per-order Meridian fee in cents (charge
    # currency). None = plan/tier default rate; the server re-clamps to the
    # tier redline so a crafted request can't undercut the floor.
    plan_id: str | None = None
    order_fee_cents: int | None = None

    @field_validator("business_name", "contact_name")
    @classmethod
    def sanitize_names(cls, v: str) -> str:
        return _sanitize_text(v)


# Per-order fee REDLINES (cents) — the floor the rep slider can reach, by plan.
# Aidan 2026-07-15: premium (middle tier) floor $0.65/order, command (top tier)
# floor $0.45/order in USD. Aidan 2026-07-19: CAD floors + cap = the standard
# ×1.4 CAD multiplier, rounded down to 5¢, applied to those USD constants
# (premium CA$0.90, command CA$0.60, cap CA$7.00) — supersedes CA$0.85/CA$0.65.
# SOURCE OF TRUTH: src/billing/fee_terms.py (ORDER_FEE_FLOOR_CENTS /
# ORDER_FEE_CAP_CENTS); the aliases below are kept for existing importers.
# Unknown plan → the lowest non-zero floor, so a crafted request can never
# zero out the fee.
_ORDER_FEE_FLOOR_CENTS_USD = ORDER_FEE_FLOOR_CENTS["us"]
_ORDER_FEE_FLOOR_CENTS_CAD = ORDER_FEE_FLOOR_CENTS["ca"]


def _clamp_order_fee_cents(fee: int, plan_id: str | None,
                           market: str = "ca") -> int:
    """Server-side redline: clamp a client-sent per-order fee to the market's
    [tier floor, hard cap]. Currency-aware — a crafted CA request can't ride
    the lower US floors."""
    m = market if market in ORDER_FEE_FLOOR_CENTS else "ca"
    floors = ORDER_FEE_FLOOR_CENTS[m]
    cap = ORDER_FEE_CAP_CENTS[m]
    default_floor = min(v for v in floors.values() if v > 0)
    floor = floors.get((plan_id or "").strip().lower(), default_floor)
    return max(min(int(fee), cap), floor)


async def _provision_fee_terms(
    *,
    market: str,
    org_id: str,
    deal_id: str | None,
    plan_id: str | None,
    monthly_price: int,
    order_fee_cents: int | None,
    locked_by: str,
) -> dict:
    """Fee parity at deal close (shared by canada + us create-customer).

    1. Locks the structured fee terms onto the lead row (canada_leads /
       us_leads) — the deal's contract of record. Fields the client omitted
       are REQUIRED server-side by defaulting them from the selected tier's
       canonical values (src/billing/fee_terms.py), so old clients keep working.
    2. Records the provisioned billing contract (merchant_billing_terms) for
       the new org — the source of truth live billing reads. No deal_id
       (manual creation) → override_reason='manual_provision'.

    Loud-but-non-fatal: a terms failure must never fail customer creation,
    but it is surfaced in the response so the rep KNOWS the contract did not
    stick (mirrors the order-fee seed contract)."""
    out = {"fee_terms_locked": False, "billing_terms_recorded": False}
    try:
        from ...billing.fee_terms import (
            lock_lead_fee_terms,
            resolve_fee_terms,
            set_merchant_billing_terms,
        )
        from ...db import get_db

        db = get_db()
        terms = resolve_fee_terms(
            market,
            plan_tier=plan_id,
            monthly_fee_cents=monthly_price * 100 if monthly_price else None,
            order_fee_cents=order_fee_cents,
        )
        lead_id = deal_id if (deal_id and _UUID_RE.match(deal_id)) else None
        if lead_id:
            out["fee_terms_locked"] = await lock_lead_fee_terms(
                db, market, lead_id, terms, locked_by)
        out["billing_terms_recorded"] = bool(await set_merchant_billing_terms(
            db, org_id, terms,
            source_lead_id=lead_id,
            source_market=market,
            created_by=locked_by,
            override_reason=None if lead_id else "manual_provision",
        ))
    except Exception as e:  # noqa: BLE001 — never fail customer creation
        logger.error("fee-terms provisioning failed for org %s: %s", org_id, e)
    return out


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
                # Store lowercased so every email-join (JWT claim is lowercased
                # by Supabase auth) matches — a mixed-case row silently breaks
                # rep entitlement + commission lookups. See fix/sales-rep-email-case.
                "email": (req.email or "").strip().lower(),
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


def _generate_temp_password() -> str:
    """Generate a readable temporary password like 'Mer-7kX9pQ2m'."""
    import secrets
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    return "Mer-" + "".join(secrets.choice(chars) for _ in range(8))


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
    # Readable temporary password returned to the rep so they can share it with
    # the customer. The customer is forced to reset it on first login via the
    # must_reset_password flag below — no reliance on Supabase recovery email.
    temp_password = _generate_temp_password()
    auth_user_id = None
    fee_parity = {"fee_terms_locked": False, "billing_terms_recorded": False}

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
                "password": temp_password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": req.contact_name,
                    "business_name": req.business_name,
                    "org_id": org_id,
                    "role": "owner",
                    "portal": "canada",
                    "vertical": req.vertical,
                    "must_reset_password": True,
                },
            },
        )
        if resp.status_code in (200, 201):
            auth_user_id = resp.json().get("id")
            logger.info(f"Created Canada customer auth user {auth_user_id} for {req.email}")
            org_id = resp.json().get("user_metadata", {}).get("org_id", org_id)
        elif resp.status_code == 422 and "already been registered" in resp.text.lower():
            logger.info(f"Auth user already exists for {req.email} — resetting temp password")
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
                    logger.error(f"Admin user list failed p{page}: {list_resp.status_code} {list_resp.text[:200]}")
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
                logger.error(f"Existing auth user for {req.email} not found in admin list — cannot reset password")
                raise HTTPException(500, "Customer account exists but could not be updated")
            # Takeover guard: a rep JWT must never be able to rotate the
            # password of an admin, a rep, or any non-Canada-customer account.
            # Only accounts that look like Canada customer owners are eligible;
            # ADMIN_EMAILS is excluded explicitly as an independent check even
            # though admins shouldn't carry the owner/canada metadata shape.
            existing_role = (existing_meta.get("role") or "").lower()
            existing_portal = (existing_meta.get("portal") or "").lower()
            if req.email.lower() in [e.lower() for e in ADMIN_EMAILS]:
                logger.warning(
                    "create-customer reset BLOCKED: %s targeted admin account %s",
                    user_id, req.email,
                )
                raise HTTPException(403, "This account cannot be managed from the rep portal")
            if existing_role not in ("owner", "") or (existing_portal and existing_portal != "canada"):
                logger.warning(
                    "create-customer reset BLOCKED: %s targeted role=%r portal=%r account %s",
                    user_id, existing_role, existing_portal, req.email,
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
                logger.error(f"Password/flag reset PUT failed for {req.email}: {put_resp.status_code} {put_resp.text[:200]}")
                raise HTTPException(502, "Could not update customer account password")
            confirmed = (put_resp.json().get("user_metadata") or {}).get("must_reset_password")
            logger.info(f"Reset OK for {req.email} (id={existing_id}); must_reset_password={confirmed}")
            auth_user_id = existing_id
        else:
            logger.error(f"Auth user creation failed: {resp.status_code} {resp.text}")
            raise HTTPException(400, "Could not create customer account")

        # Link the customer to a business record so the portal can load their org
        # on login. Without this row fetchBusinessForUser returns null, org stays
        # null, and ProtectedRoute bounces the customer back to /canada/login even
        # after a successful password reset. Mirrors onboarding.provision_customer.
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

            # Fee parity: lock the deal terms on the lead + record the billing
            # contract for the new org (see _provision_fee_terms).
            fee_parity = await _provision_fee_terms(
                market="ca",
                org_id=org_id,
                deal_id=req.deal_id,
                plan_id=req.plan_id,
                monthly_price=req.monthly_price,
                order_fee_cents=req.order_fee_cents,
                locked_by=claims.get("email") or user_id,
            )

            # Commission accrual (Canada, LIVE + flag-gated). Writes the rep's
            # M0-M3 milestone schedule the moment a deal closes. Best-effort +
            # idempotent (UNIQUE(account_id,milestone)) — a hiccup here must
            # NEVER fail customer creation. Rep is resolved from the closing
            # rep's verified JWT email; package = nearest price-point (Enoch's
            # plan). Milestones are 'pending'/'earned', never auto-PAID —
            # settlement stays quarterly + gated. See commission_engine.py.
            try:
                from ...services.commission_engine import (
                    CommissionEngineService,
                    canada_commission_live,
                )
                from datetime import datetime, timezone

                if canada_commission_live() and req.monthly_price:
                    from ...db import get_db as _get_commission_db

                    _csvc = CommissionEngineService(db=_get_commission_db())
                    await _csvc.accrue_for_canada_close(
                        account_id=org_id,
                        rep_email=claims.get("email") or "",
                        negotiated_monthly_cents=req.monthly_price * 100,
                        close_date=datetime.now(timezone.utc).date(),
                    )
            except Exception as e:  # noqa: BLE001 — never fail customer creation
                logger.error("commission accrual failed for org %s: %s", org_id, e)

            # Rep fee slider: pre-seed phone_agent_config with the negotiated
            # per-order fee so every payment rail picks it up the moment the
            # phone agent goes live. Best-effort — a fee-seed hiccup must never
            # fail customer creation (the fee falls back to the tier default).
            if req.order_fee_cents is not None:
                fee = _clamp_order_fee_cents(req.order_fee_cents, req.plan_id)
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
                # Creation still succeeds on a seed failure, but the rep must
                # KNOW the negotiated fee didn't stick (it falls back to the
                # tier default until set manually) — surface it in the response.
                return {"ok": True, "org_id": org_id,
                        # Alias both keys (US portal reads temp_password) to kill
                        # the cross-market response-key drift.
                        "temporary_password": temp_password,
                        "temp_password": temp_password,
                        "fee_seeded": fee_seeded, "order_fee_cents": fee,
                        **fee_parity}

    return {"ok": True, "org_id": org_id,
            "temporary_password": temp_password,
            "temp_password": temp_password,
            **fee_parity}


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
    _user_token_unused = _user_token(request)  # noqa: F841 — kept for audit logging hooks if added later
    _anon_key_unused = _get_anon_key()  # noqa: F841

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

    async with httpx.AsyncClient(timeout=20.0) as client:
        # return=representation gives us the deleted row (incl. email) so we can
        # also tear down the Supabase auth login — without it a rejected
        # applicant could sign in again and re-create their rep row.
        resp = await client.delete(
            f"{supabase_url}/rest/v1/sales_reps?id=eq.{req.rep_id}",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Prefer": "return=representation",
            },
        )
        if resp.status_code not in (200, 204):
            logger.error("Rep reject failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(500, "Could not reject rep")

        deleted = resp.json() if (resp.status_code == 200 and resp.text) else []
        rep_email = deleted[0].get("email", "") if deleted else ""
        login_removed, login_detail = False, "no_email"
        if rep_email:
            login_removed, login_detail = await delete_auth_user_by_email(
                client, supabase_url, service_key, rep_email, protected_emails=ADMIN_EMAILS,
            )

    return {"ok": True, "rep_id": req.rep_id, "login_removed": login_removed, "login_detail": login_detail}


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
    """Admin removes a rep from the team.

    Deletes the sales_reps row AND the underlying Supabase auth login (best
    effort) so the account cannot reappear on next sign-in. Real merchant-owner
    accounts are protected automatically: their auth user can't be deleted while
    a `businesses.owner_user_id` FK still references it, so the auth delete fails
    gracefully and only the rep row is removed.
    """
    _validate_rep_id(req.rep_id)

    import httpx
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.delete(
            f"{supabase_url}/rest/v1/sales_reps?id=eq.{req.rep_id}",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Prefer": "return=representation",
            },
        )
        if resp.status_code not in (200, 204):
            logger.error("Rep remove failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(500, "Could not remove rep")

        deleted = resp.json() if (resp.status_code == 200 and resp.text) else []
        rep_email = deleted[0].get("email", "") if deleted else ""
        login_removed, login_detail = False, "no_email"
        if rep_email:
            login_removed, login_detail = await delete_auth_user_by_email(
                client, supabase_url, service_key, rep_email, protected_emails=ADMIN_EMAILS,
            )

    logger.info("Rep removed: %s by %s (login_removed=%s, %s)", req.rep_id, req.admin_email, login_removed, login_detail)
    return {"ok": True, "rep_id": req.rep_id, "login_removed": login_removed, "login_detail": login_detail}


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

    rows: list = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/deals?order=created_at.desc&select=*",
            headers=headers,
        )
        if resp.status_code == 200:
            rows = resp.json()
        else:
            resp = await client.get(
                f"{supabase_url}/rest/v1/data_sales?order=created_at.desc&select=*",
                headers=headers,
            )
            if resp.status_code == 200:
                rows = resp.json()

    # Backend scoping plane (independent of RLS): filter rep-keyed rows to the
    # caller's subtree; unassigned rows stay visible (matches the RLS plane).
    scope = await hierarchy.resolve_scope(user)
    allowed = await hierarchy.visible_rep_ids(scope)
    return {"leads": hierarchy.scope_lead_rows(rows, allowed)}


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
    """Return the caller's visible Canada roster.

    Two INDEPENDENT scoping planes (do not collapse them):
      1. RLS — the fetch forwards the caller's JWT, so the sales_reps roster
         policy (20260716_sales_hierarchy.sql) already scopes at the DB.
      2. Backend — hierarchy.scope_roster_rows re-filters to subtree + upline
         regardless of what the fetch returned, so a policy regression cannot
         leak lateral branches through this endpoint.
    """
    import httpx
    supabase_url = os.environ.get("SUPABASE_URL", "")
    anon_key = _get_anon_key()

    # Extract the user's JWT from the Authorization header to enforce RLS
    auth_header = request.headers.get("authorization", "")
    user_token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""

    if not supabase_url or not user_token:
        return {"reps": [], "applicants": []}

    base_cols = "id,name,email,phone,commission_rate,is_active,created_at,portal_context"
    hier_cols = base_cols + ",role,manager_id,path,level"
    headers = {"Authorization": f"Bearer {user_token}", "apikey": anon_key}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/sales_reps?portal_context=in.(canada,all)&order=created_at.asc&select={hier_cols}",
            headers=headers,
        )
        if resp.status_code != 200:
            # Pre-migration prod: hierarchy columns unknown → legacy column set.
            resp = await client.get(
                f"{supabase_url}/rest/v1/sales_reps?portal_context=in.(canada,all)&order=created_at.asc&select={base_cols}",
                headers=headers,
            )
        if resp.status_code != 200:
            logger.error("Team fetch failed: %s", resp.text)
            return {"reps": [], "applicants": []}

        rows = resp.json()

    scope = await hierarchy.resolve_scope(user)
    allowed = await hierarchy.visible_rep_ids(scope)
    rows = hierarchy.scope_roster_rows(rows, scope, allowed)

    reps = [r for r in rows if r.get("is_active")]
    applicants = [r for r in rows if not r.get("is_active")]
    return {
        "reps": reps,
        "applicants": applicants,
        "viewer": {"role": scope.role, "rep_id": scope.rep_id, "is_admin": scope.is_admin},
    }


def _rollup_team_commissions(milestones: list[dict]) -> dict:
    """Pure per-rep commission rollup. earned='earned' (unpaid) / pending /
    paid; 'halted' and unknown statuses are excluded. Rows sorted by total desc.
    """
    by_rep: dict[str, dict] = {}
    tot = {"earned_cents": 0, "pending_cents": 0, "paid_cents": 0}
    bucket_of = {"earned": "earned_cents", "pending": "pending_cents", "paid": "paid_cents"}
    for m in milestones or []:
        rid = m.get("rep_id")
        bucket = bucket_of.get(m.get("status"))
        if not rid or bucket is None:
            continue
        cents = int(m.get("amount_cents") or 0)
        r = by_rep.setdefault(rid, {"rep_id": rid, "earned_cents": 0, "pending_cents": 0, "paid_cents": 0})
        r[bucket] += cents
        tot[bucket] += cents
    rows = sorted(by_rep.values(),
                  key=lambda r: -(r["earned_cents"] + r["pending_cents"] + r["paid_cents"]))
    return {"rows": rows, "totals": tot}


@router.get("/team/commissions")
async def get_team_commissions(user: dict = Depends(require_jwt)):
    """Per-rep commission rollup for the caller's VISIBLE subtree (view-only).

    Powers the Manager team view's commission column. Scoped by the same
    hierarchy plane as /team: a manager sees their downline, a rep sees only
    themselves, an admin sees everyone. Amounts are earned / pending / paid in
    integer cents — this NEVER pays or mutates anything.
    """
    scope = await hierarchy.resolve_scope(user)
    allowed = await hierarchy.visible_rep_ids(scope)  # None ⇒ admin (all reps)

    from ...db import get_db
    db = get_db()
    filters = {}
    if allowed is not None:
        if not allowed:
            return {"rows": [], "totals": {"earned_cents": 0, "pending_cents": 0, "paid_cents": 0}}
        filters["rep_id"] = "in.(" + ",".join(sorted(allowed)) + ")"
    milestones = await db.select(
        "commission_milestones",
        columns="rep_id,amount_cents,status",
        filters=filters or None,
        limit=5000,
    )

    return _rollup_team_commissions(milestones)
