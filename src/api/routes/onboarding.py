"""
Onboarding Routes — New customer account creation and welcome flow.

  POST /api/onboarding/create-account  → Create org + admin user
  POST /api/onboarding/send-welcome    → Send welcome email with Square connect link
"""
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, field_validator

from ..auth import (
    enforce_service_member,
    require_admin_auth,
    require_jwt,
    require_org_member,
    require_service_auth,
)
from ...db import get_db

logger = logging.getLogger("meridian.api.onboarding")

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

_FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    os.environ.get("FRONTEND_ORIGIN", "https://meridian.tips"),
)


class CreateAccountRequest(BaseModel):
    email: EmailStr
    business_name: str
    plan: str = "free"
    square_payment_id: str | None = None

    @field_validator("business_name")
    @classmethod
    def validate_business_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("business_name must be at least 2 characters")
        if len(v) > 200:
            raise ValueError("business_name too long")
        return v


class CreateAccountResponse(BaseModel):
    org_id: str
    admin_user_id: str
    temporary_password: str
    login_url: str
    connect_square_url: str


class SendWelcomeRequest(BaseModel):
    org_id: str
    email: EmailStr


@router.get("/checklist")
async def get_checklist(
    org_id: str,
    principal=Depends(require_service_auth),
):
    """Onboarding checklist: which steps are complete for this org.

    Security (June require_service_auth BOLA batch): this endpoint was fully
    unauthenticated and org_id-keyed — anyone could probe any org's POS/
    onboarding state. Now requires auth + org scope (machine principals pass).
    """
    await enforce_service_member(principal, org_id)
    db = get_db()

    org_rows = await db.select("organizations", filters={"id": f"eq.{org_id}"}, limit=1)
    if not org_rows:
        raise HTTPException(404, "Organization not found")

    connections = await db.select(
        "pos_connections",
        filters={"org_id": f"eq.{org_id}"},
        limit=1,
    )
    pos_connected = bool(connections and connections[0].get("status") == "connected")
    has_sync = bool(connections and connections[0].get("last_sync_at"))

    notifications = await db.select(
        "notifications",
        filters={"org_id": f"eq.{org_id}"},
        limit=1,
    )
    welcome_sent = bool(notifications)

    steps = [
        {"key": "account_created", "label": "Account created", "complete": True},
        {"key": "welcome_sent", "label": "Welcome email sent", "complete": welcome_sent},
        {"key": "pos_connected", "label": "POS connected", "complete": pos_connected},
        {"key": "first_sync", "label": "First data sync", "complete": has_sync},
    ]

    return {
        "org_id": org_id,
        "steps": steps,
        "progress": sum(1 for s in steps if s["complete"]),
        "total": len(steps),
    }


# Raw org + admin-user creation. No rep/merchant frontend calls /create-account (verified:
# zero callers in frontend/src — reps onboard merchants via /provision-customer, which stays
# require_service_auth). Admin-locked; MERIDIAN_SERVICE_TOKEN + admin key still pass.
@router.post("/create-account", response_model=CreateAccountResponse, dependencies=[Depends(require_admin_auth)])
async def create_account(req: CreateAccountRequest):
    """
    Create a new organization and admin user.

    Called after Square QR code payment or manual signup.
    Returns credentials for first login.
    """
    db = get_db()
    org_id = str(uuid4())
    admin_user_id = str(uuid4())
    temp_password = secrets.token_urlsafe(12)
    now = datetime.now(timezone.utc).isoformat()
    slug = req.business_name.lower().replace(" ", "-")[:50]

    await db.insert("organizations", {
        "id": org_id,
        "name": req.business_name,
        "slug": slug,
        "plan": req.plan,
        "is_active": True,
        "created_at": now,
    })

    await db.insert("admin_users", {
        "id": admin_user_id,
        "org_id": org_id,
        "email": req.email,
        "password_hash": _hash_password(temp_password),
        "role": "owner",
        "is_active": True,
        "created_at": now,
    })

    if req.square_payment_id:
        await db.insert("notifications", {
            "id": str(uuid4()),
            "org_id": org_id,
            "title": "Welcome to Meridian!",
            "body": f"Account created for {req.business_name}. Connect your Square POS to get started.",
            "priority": "high",
            "source_type": "event",
            "status": "sent",
            "created_at": now,
        })

    connect_url = f"{_FRONTEND_URL}/api/square/authorize?org_id={org_id}"
    login_url = f"{_FRONTEND_URL}/login"

    logger.info(f"Created account: org={org_id}, email={req.email}, business={req.business_name}")

    return CreateAccountResponse(
        org_id=org_id,
        admin_user_id=admin_user_id,
        temporary_password=temp_password,
        login_url=login_url,
        connect_square_url=connect_url,
    )


@router.post("/send-welcome")
async def send_welcome(req: SendWelcomeRequest, principal=Depends(require_service_auth)):
    """
    Send welcome email with login link and Square connect button (org-scoped).

    Security (June require_service_auth BOLA batch): previously unauthenticated
    — anyone could send a Square-connect welcome email for ANY org to ANY
    address. The trusted internal webhook path calls _send_welcome_impl.
    """
    await enforce_service_member(principal, req.org_id)
    return await _send_welcome_impl(req)


async def _send_welcome_impl(req: SendWelcomeRequest):
    """Implementation shared by the authed route and the internal
    subscription-payment webhook path (handle_subscription_payment)."""
    db = get_db()

    orgs = await db.select("organizations", filters={"id": f"eq.{req.org_id}"}, limit=1)
    if not orgs:
        raise HTTPException(404, "Organization not found")

    org = orgs[0]
    connect_url = f"{_FRONTEND_URL}/api/square/authorize?org_id={req.org_id}"

    from ...email.send import send_welcome_email
    result = await send_welcome_email(
        to=req.email,
        first_name=org["name"].split()[0],
        org_id=req.org_id,
        connect_url=connect_url,
    )

    await db.insert("notifications", {
        "id": str(uuid4()),
        "org_id": req.org_id,
        "title": "Welcome email sent",
        "body": f"Welcome email sent to {req.email}",
        "priority": "normal",
        "source_type": "event",
        "status": "sent",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"status": result.get("status", "sent"), "email": req.email, "org_id": req.org_id}


async def handle_subscription_payment(payment_data: dict):
    """
    Auto-trigger onboarding when a subscription payment completes.

    Called from the Square payment.completed webhook handler.
    Looks up customer email from the payment, creates account, sends welcome.
    """
    customer_email = (
        payment_data.get("buyer_email_address")
        or payment_data.get("receipt_email")
    )

    if not customer_email:
        logger.warning("Subscription payment received but no customer email found")
        return

    business_name = payment_data.get("note", "New Business")
    payment_id = payment_data.get("id", "")

    try:
        req = CreateAccountRequest(
            email=customer_email,
            business_name=business_name,
            plan="starter",
            square_payment_id=payment_id,
        )
        result = await create_account(req)

        await _send_welcome_impl(SendWelcomeRequest(
            org_id=result.org_id,
            email=customer_email,
        ))

        logger.info(f"Auto-onboarding complete for {customer_email}, org={result.org_id}")
    except Exception as e:
        logger.error(f"Auto-onboarding failed for {customer_email}: {e}", exc_info=True)


# ── SR-Driven Customer Provisioning ─────────────────────────

class ProvisionCustomerRequest(BaseModel):
    org_id: str

    @field_validator("org_id")
    @classmethod
    def _org_id_must_be_uuid(cls, v: str) -> str:
        # businesses.id is text, but pos_connections/products/organizations/
        # subscriptions/notifications all type org_id as uuid — a slug here
        # 22P02s every downstream query (hit live with 'biz_aidan_view').
        try:
            UUID(v)
        except ValueError:
            raise ValueError("org_id must be a UUID")
        return v
    email: EmailStr
    owner_name: str
    business_name: str
    phone: str | None = None
    plan: str = "starter"
    monthly_price: int = 500
    rep_id: str | None = None
    rep_name: str | None = None
    business_type: str | None = None
    pos_provider: str | None = None
    setup_fee: int = 0
    first_month_free: bool = False
    country: str = "CA"
    # Fee parity: the closed lead this provision fulfils. When set, the lead's
    # LOCKED fee terms are copied verbatim into merchant_billing_terms — no
    # manual re-entry. When absent (legacy/manual provision), terms are built
    # from the explicit params below and recorded with
    # override_reason='manual_provision'.
    lead_id: str | None = None
    lead_market: str | None = None  # 'ca' | 'us'; defaults from `country`
    order_fee_cents: int | None = None
    # Fee allocation mode chosen by the rep at close, FIXED thereafter
    # (business_pays | split_5050 | customer_pays). None → legacy fee behavior.
    fee_allocation_mode: str | None = None

    @field_validator("fee_allocation_mode")
    @classmethod
    def _validate_fee_mode(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if v not in ("business_pays", "split_5050", "customer_pays"):
            raise ValueError(
                "fee_allocation_mode must be business_pays, split_5050, or customer_pays")
        return v
    # When true (self-serve onboarding wizard), the customer already created
    # their account with a self-chosen password — do NOT overwrite it with a
    # temp password or force a reset, and skip the credentials email. Default
    # false preserves the rep-provisioned behaviour (temp password + email).
    preserve_password: bool = False


class ProvisionCustomerResponse(BaseModel):
    org_id: str
    email: str
    temporary_password: str
    login_url: str
    portal_url: str = ""
    invoices_sent: bool
    welcome_email_sent: bool
    invoice_sms_sent: bool = False
    invoice_error: str | None = None
    email_error: str | None = None
    # Fee parity: whether the billing contract (merchant_billing_terms) was
    # recorded. False = loud follow-up needed (terms table missing / write
    # failed) — the merchant would otherwise drift from the deal.
    billing_terms_recorded: bool = False


# `businesses.plan_tier` is constrained to ('trial','starter','growth','enterprise')
# (migration 20260429_001). The sales portal sends pricing-plan ids
# (weekly/standard/premium/command), so writing req.plan straight in violates
# businesses_plan_tier_check and 500s provisioning. Map to a valid tier.
_VALID_PLAN_TIERS = {"trial", "starter", "growth", "enterprise"}
_PLAN_TIER_MAP = {"weekly": "starter", "standard": "growth", "premium": "growth", "command": "enterprise"}


def _plan_tier(plan: str | None) -> str:
    p = (plan or "").strip().lower()
    if p in _VALID_PLAN_TIERS:
        return p
    return _PLAN_TIER_MAP.get(p, "starter")


async def _record_provision_fee_terms(db, req: ProvisionCustomerRequest) -> tuple[bool, dict]:
    """Fee parity for provision-customer: resolve the deal's fee terms, lock
    them onto the source lead, and record the billing contract.

    Order of operations (the invariant the New Customer flow relies on):
      1. lead_id + already-locked lead → the locked columns are the contract
         of record; copy them verbatim (no re-entry, no drift).
      2. lead_id + unlocked lead (New Customer inserts the lead immediately
         before provisioning) → resolve terms from the explicit request params
         and lock them onto the lead server-side (first-lock-wins), so the CRM
         row carries fee_terms_locked_at and matches what billing records.
      3. no lead_id (self-serve wizards, legacy callers) → resolve from params
         and flag override_reason='manual_provision'. Unchanged behavior.

    Returns (billing_terms_recorded, terms). Raises on unexpected errors —
    the caller owns the loud-but-non-fatal handling.
    """
    from ...billing.fee_terms import (
        LEAD_TABLE_BY_MARKET,
        lock_lead_fee_terms,
        normalize_market,
        resolve_fee_terms,
        set_merchant_billing_terms,
        terms_from_lead_row,
    )

    market = normalize_market(req.lead_market or req.country)
    locked_by = req.rep_name or req.rep_id or "provision_customer"
    terms: dict | None = None
    override_reason: str | None = "manual_provision"
    lead_row: dict | None = None
    if req.lead_id:
        lead_rows = await db.select(
            LEAD_TABLE_BY_MARKET[market],
            filters={"id": f"eq.{req.lead_id}"}, limit=1,
        )
        if lead_rows:
            lead_row = lead_rows[0]
            if lead_row.get("fee_terms_locked_at"):
                terms = terms_from_lead_row(market, lead_row)
                override_reason = None
        else:
            logger.warning("provision-customer: lead %s not found in %s — falling back to explicit params",
                           req.lead_id, LEAD_TABLE_BY_MARKET[market])
    if terms is None:
        terms = resolve_fee_terms(
            market,
            plan_tier=req.plan,
            monthly_fee_cents=req.monthly_price * 100 if req.monthly_price else None,
            order_fee_cents=req.order_fee_cents,
        )
        if lead_row is not None:
            locked = await lock_lead_fee_terms(db, market, req.lead_id, terms, locked_by)
            override_reason = None if locked else "lead_terms_not_locked"
    recorded = bool(await set_merchant_billing_terms(
        db, req.org_id, terms,
        source_lead_id=req.lead_id if lead_row is not None else None,
        source_market=market,
        created_by=locked_by,
        override_reason=override_reason,
    ))
    return recorded, terms


@router.post("/provision-customer", response_model=ProvisionCustomerResponse, dependencies=[Depends(require_service_auth)])
async def provision_customer(req: ProvisionCustomerRequest):
    """
    Full customer provisioning — called by the sales rep after confirming a deal.

    1. Creates Supabase Auth user with generated password
    2. Links user to existing organization (created by SR frontend)
    3. Sends Square invoices (setup fee + monthly recurring)
    4. Sends welcome email with login credentials

    Returns the generated password so the SR can see/share it.
    """
    import httpx

    db = get_db()
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    temp_password = _generate_password()
    now = datetime.now(timezone.utc).isoformat()

    # 1. Create Supabase Auth user (admin API — skips email confirmation)
    auth_user_id = None
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
                    "full_name": req.owner_name,
                    "business_name": req.business_name,
                    "org_id": req.org_id,
                    "role": "owner",
                    "must_reset_password": True,
                },
            },
        )
        if resp.status_code in (200, 201):
            auth_user_id = resp.json().get("id")
            logger.info(f"Created auth user {auth_user_id} for {req.email}")
        elif resp.status_code == 422 and "already been registered" in resp.text.lower():
            logger.info(f"Auth user already exists for {req.email} — updating password and fetching ID")
            list_resp = await client.get(
                f"{supabase_url}/auth/v1/admin/users",
                headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
                params={"page": 1, "per_page": 50},
            )
            if list_resp.status_code == 200:
                for u in list_resp.json().get("users", []):
                    if u.get("email", "").lower() == req.email.lower():
                        auth_user_id = u["id"]
                        break
            if auth_user_id:
                # preserve_password (self-serve): sync org/role metadata only —
                # don't reset the password the customer just chose or force a reset.
                _meta = {"full_name": req.owner_name, "business_name": req.business_name, "org_id": req.org_id, "role": "owner", "must_reset_password": not req.preserve_password}
                _put_json: dict = {"user_metadata": _meta}
                if not req.preserve_password:
                    _put_json["password"] = temp_password
                pw_resp = await client.put(
                    f"{supabase_url}/auth/v1/admin/users/{auth_user_id}",
                    headers={"Authorization": f"Bearer {service_key}", "apikey": service_key, "Content-Type": "application/json"},
                    json=_put_json,
                )
                if pw_resp.status_code == 200:
                    logger.info(f"Updated {'metadata' if req.preserve_password else 'password and metadata'} for existing user {auth_user_id}")
                else:
                    logger.warning(f"User update failed: {pw_resp.status_code}")
        else:
            logger.error(f"Auth user creation failed: {resp.status_code} {resp.text}")
            raise HTTPException(400, f"Could not create user account: {resp.json().get('msg', 'Unknown error')}")

    # 2. Create business record linking auth user to org
    portal_token = secrets.token_urlsafe(16)
    if auth_user_id:
        try:
            biz_data = {
                "id": req.org_id,
                "owner_user_id": auth_user_id,
                "name": req.business_name,
                "owner_name": req.owner_name,
                "email": req.email,
                "phone": req.phone,
                "plan_tier": _plan_tier(req.plan),
                "business_type": req.business_type or "restaurant",
                "pos_provider": req.pos_provider,
                "pos_connected": False,
                "onboarded": False,
                "status": "active",
                "created_at": now,
                "access_token": portal_token,
                # constrained to pending/redeemed/expired (20260429_001); the portal
                # redemption flow flips it to 'redeemed' — "active" 23514s the upsert
                "token_status": "pending",
            }
            await db.upsert("businesses", biz_data, on_conflict="id")
        except Exception as e:
            logger.error(f"Business record creation failed for {req.email}: {e}", exc_info=True)
            raise HTTPException(500, "Account created but business profile failed to save. Please retry or contact support.")

    # 2b. Fee parity: record the billing contract WITH activation, before any
    # invoicing — merchant_billing_terms is the source of truth billing reads.
    # lead_id present → lock/copy the lead's fee terms so the CRM row and the
    # contract can't drift; absent → build from the explicit params and flag
    # 'manual_provision'. (Order of operations lives in
    # _record_provision_fee_terms — unit-tested in tests/test_fee_parity_terms.py.)
    # Loud-but-non-fatal until migration 20260716_merchant_billing_terms is
    # applied everywhere: a terms failure must not strand a paying customer,
    # but it is surfaced in the response and the logs.
    billing_terms_recorded = False
    try:
        billing_terms_recorded, terms = await _record_provision_fee_terms(db, req)
        # Seed the live phone/website order-fee rail (phone_agent_config) from
        # the same terms so the negotiated per-order fee applies the moment the
        # phone agent goes live (mirrors canada/us create-customer seeding). The
        # rep-set fee_allocation_mode is seeded here too — even for tiers with no
        # per-order fee (standard) — so the mode is FIXED from the moment of
        # provisioning.
        _seed_order_fee = billing_terms_recorded and terms.get("order_fee_cents") is not None
        if _seed_order_fee or req.fee_allocation_mode:
            try:
                pac_seed: dict = {}
                if _seed_order_fee:
                    pac_seed["order_fee_cents"] = int(terms["order_fee_cents"])
                    pac_seed["plan_tier"] = terms.get("plan_tier")
                if req.fee_allocation_mode:
                    pac_seed["fee_allocation_mode"] = req.fee_allocation_mode
                existing_pac = await db.select(
                    "phone_agent_config", "id",
                    filters={"merchant_id": f"eq.{req.org_id}"}, limit=1)
                if existing_pac:
                    await db.update("phone_agent_config", pac_seed,
                                    filters={"merchant_id": f"eq.{req.org_id}"})
                else:
                    await db.insert("phone_agent_config", {
                        "merchant_id": req.org_id,
                        "business_name": req.business_name,
                        "business_type": req.business_type or "restaurant",
                        "active": False,
                        **pac_seed,
                    })
            except Exception as pac_err:  # noqa: BLE001
                logger.error("provision-customer: order-fee/mode seed failed for %s: %s",
                             req.org_id, pac_err)
    except Exception as terms_err:  # noqa: BLE001
        logger.error("provision-customer: billing terms provisioning FAILED for %s: %s",
                     req.org_id, terms_err, exc_info=True)

    # 3. Send setup fee invoice (card stored on payment → auto-billing starts)
    invoices_sent = False
    invoice_error = None
    setup_result = None
    try:
        from src.billing.billing_service import BillingService
        billing = BillingService(db)

        plan_label = req.plan.replace("_", " ").title()

        setup_result = await billing.create_invoice(
            org_id=req.org_id,
            amount_cents=req.monthly_price * 100,
            customer_email=req.email,
            description=f"Meridian Analytics - {plan_label} Plan (Setup + First Month)",
            due_days=3,
            store_card=True,
        )

        invoices_sent = setup_result.success
        if invoices_sent:
            logger.info(f"Sent setup invoice for {req.email}: {setup_result.invoice_id}")

            customer_id = await billing._get_or_create_customer(
                req.email, req.owner_name, req.business_name,
            )

            period_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
            await db.upsert("subscriptions", {
                "org_id": req.org_id,
                "tier": req.plan,
                "status": "pending_payment",
                "monthly_price_cents": req.monthly_price * 100,
                "current_period_start": now,
                "current_period_end": period_end,
                "metadata": {
                    "payment_method": "square_invoice",
                    "setup_invoice_id": setup_result.invoice_id,
                    "setup_invoice_url": setup_result.invoice_url,
                    "square_customer_id": customer_id,
                    "awaiting_auto_subscription": True,
                    "target_monthly_cents": req.monthly_price * 100,
                    "created_via": "sr_provision",
                    "rep_id": req.rep_id,
                    "auto_renew": True,
                },
            }, on_conflict="org_id")
        else:
            invoice_error = "Invoice creation returned unsuccessful"
            logger.warning(f"Invoice not successful for {req.email}: {setup_result}")
    except ImportError:
        invoice_error = "billing_service_unavailable"
        logger.warning("Billing service not available — skipping invoices")
    except Exception as e:
        invoice_error = str(e)
        logger.error(f"Invoice creation failed for {req.email}: {e}", exc_info=True)

    # 3b. Send invoice SMS to customer phone
    sms_sent = False
    if invoices_sent and req.phone:
        try:
            from src.sms.client import send_invoice_sms
            plan_label = req.plan.replace("_", " ").title()
            invoice_url = setup_result.invoice_url if setup_result else None
            sms_result = await send_invoice_sms(
                phone=req.phone,
                owner_name=req.owner_name,
                business_name=req.business_name,
                invoice_url=invoice_url,
                plan_label=plan_label,
                amount_display=f"${req.monthly_price}/mo",
            )
            sms_sent = sms_result.get("sent", False)
            if sms_sent:
                logger.info(f"Invoice SMS sent to {req.phone} for {req.email}")
        except Exception as e:
            logger.warning(f"Invoice SMS failed for {req.phone}: {e}")

    # 4. Send credentials email via Postal/Resend
    welcome_sent = False
    email_error = None
    login_url = f"{_FRONTEND_URL}/us/login" if (req.country or "CA").upper() == "US" else f"{_FRONTEND_URL}/canada/login"
    try:
        if req.preserve_password:
            # Self-serve customer already has working credentials they chose — no
            # temp-password email to send. Treat as success (nothing to deliver).
            welcome_sent = True
        else:
            from ...email.send import send_customer_credentials
            email_result = await send_customer_credentials(
                to=req.email,
                business_name=req.business_name,
                email=req.email,
                password=temp_password,
                login_url=login_url,
                rep_name=req.rep_name or "",
                org_id=req.org_id,
            )
            welcome_sent = email_result.get("status") == "sent"
            if not welcome_sent:
                email_error = email_result.get("error", "Email delivery unsuccessful")

            await db.insert("notifications", {
                "id": str(uuid4()),
                "org_id": req.org_id,
                "title": f"Welcome to Meridian — {req.business_name}",
                "body": f"Credentials email {'sent to' if welcome_sent else 'FAILED for'} {req.email}",
                "priority": "high",
                "source_type": "event",
                "status": "sent",
                "created_at": now,
            })
    except Exception as e:
        email_error = str(e)
        logger.error(f"Credentials email failed for {req.email}: {e}", exc_info=True)

    # 5. Dispatch autonomous swarm: POS sync → analysis → insight generation
    try:
        from src.workers.celery_app import celery_app
        celery_app.send_task(
            "src.workers.tasks.run_analysis",
            args=[req.org_id],
            countdown=120,  # 2-min delay to let POS data arrive
            queue="analysis",
        )
        logger.info(f"Queued autonomous analysis for org={req.org_id} (2min delay)")
    except Exception as e:
        logger.warning(f"Could not queue analysis task: {e}")

    return ProvisionCustomerResponse(
        org_id=req.org_id,
        email=req.email,
        temporary_password=temp_password,
        login_url=login_url,
        portal_url=f"{_FRONTEND_URL}/c/{portal_token}",
        invoices_sent=invoices_sent,
        welcome_email_sent=welcome_sent,
        invoice_sms_sent=sms_sent,
        invoice_error=invoice_error,
        email_error=email_error,
        billing_terms_recorded=billing_terms_recorded,
    )


class MarkOnboardedRequest(BaseModel):
    org_id: str


@router.post("/mark-onboarded")
async def mark_onboarded(req: MarkOnboardedRequest, user: dict = Depends(require_jwt)):
    """Mark a business as onboarded. Called after setup wizard completion.

    Auth: a customer marks THEIR OWN org onboarded with their own session JWT.
    Previously this required service auth (admin/service token), so the customer's
    "Skip — I'll connect later" step 403'd and never persisted server-side — on
    every reload the customer was bounced back to /canada/setup (BUG-1). We now
    accept the owner JWT and enforce org membership so a customer can only mark
    their own org (no cross-tenant); admins in ADMIN_EMAILS retain support access
    via _check_org_membership.
    """
    await require_org_member(user, req.org_id)
    import httpx

    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(
            f"{supabase_url}/rest/v1/businesses?id=eq.{req.org_id}",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json={"onboarded": True},
        )
        if resp.status_code not in (200, 204):
            logger.warning(f"mark-onboarded failed for {req.org_id}: {resp.status_code} {resp.text}")
            raise HTTPException(500, "Could not update onboarded status")

    logger.info(f"Marked business {req.org_id} as onboarded")
    return {"status": "ok", "org_id": req.org_id}


class SendInvoiceSmsRequest(BaseModel):
    phone: str
    owner_name: str
    business_name: str
    invoice_url: str
    plan_label: str = "Starter"
    amount_display: str = "$250/mo"


@router.post("/send-invoice-sms", dependencies=[Depends(require_service_auth)])
async def send_invoice_sms_endpoint(req: SendInvoiceSmsRequest):
    """Manual resend: sales rep triggers invoice SMS to customer."""
    from src.sms.client import send_invoice_sms

    result = await send_invoice_sms(
        phone=req.phone,
        owner_name=req.owner_name,
        business_name=req.business_name,
        invoice_url=req.invoice_url,
        plan_label=req.plan_label,
        amount_display=req.amount_display,
    )

    if not result.get("sent"):
        raise HTTPException(502, f"SMS delivery failed: {result.get('reason', 'unknown')}")

    return {
        "status": "sent",
        "phone": req.phone,
        "method": result.get("method"),
        "message_sid": result.get("message_sid"),
    }


# Lead row lives in different tables per market: Canada deals in `deals`,
# US leads in `us_leads`. Allowlist guards against arbitrary table injection.
_POS_LEAD_TABLES = {"deals", "us_leads"}


def _pos_lead_table(table: str | None) -> str:
    t = (table or "deals").strip()
    if t not in _POS_LEAD_TABLES:
        raise HTTPException(400, "Invalid lead table")
    return t


class ConnectPosRequest(BaseModel):
    deal_id: str | None = None
    provider: str
    credentials: dict
    business_name: str | None = None
    # Which lead table deal_id belongs to. Default 'deals' keeps existing
    # callers unchanged; the US lead-detail page passes 'us_leads'.
    table: str | None = None


class VerifyPosRequest(BaseModel):
    deal_id: str | None = None
    provider: str
    table: str | None = None


@router.post("/connect-pos", dependencies=[Depends(require_jwt)])
async def connect_pos_onboarding(req: ConnectPosRequest):
    """Test POS credentials then save if valid. Called from the US lead detail
    page (Canada reps have no POS UI — customers self-connect via /api/pos)."""
    from .pos_connections import test_connection, TestConnectionRequest

    test_result = await test_connection(TestConnectionRequest(
        pos_system=req.provider,
        credentials=req.credentials,
    ))

    if not test_result.get("success"):
        raise HTTPException(
            400,
            test_result.get("message", f"Could not connect to {req.provider}. Check your credentials."),
        )

    if req.deal_id:
        db = get_db()
        try:
            await db.update(
                _pos_lead_table(req.table),
                {"pos_system": req.provider, "pos_status": "connected"},
                filters={"id": f"eq.{req.deal_id}"},
            )
        except Exception as e:
            logger.warning("Could not update deal POS status: %s", e)

    return {
        "success": True,
        "message": test_result.get("message", f"{req.provider.title()} connected successfully."),
        "business_name": test_result.get("business_name"),
    }


@router.post("/verify-pos", dependencies=[Depends(require_jwt)])
async def verify_pos_onboarding(req: VerifyPosRequest):
    """Quick verify that POS connection is still live."""

    if req.deal_id:
        db = get_db()
        try:
            rows = await db.select(_pos_lead_table(req.table), filters={"id": f"eq.{req.deal_id}"}, limit=1)
            if rows and rows[0].get("pos_status") == "connected":
                return {"verified": True, "provider": req.provider}
        except Exception:
            pass

    return {"verified": False, "provider": req.provider, "message": "Connection not verified yet."}


def _generate_password() -> str:
    """Generate a readable temporary password like 'Mer-7kX9pQ2m'."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    suffix = "".join(secrets.choice(chars) for _ in range(8))
    return f"Mer-{suffix}"


def _hash_password(password: str) -> str:
    """Hash password for storage. Uses bcrypt if available, falls back to PBKDF2."""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        import hashlib
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return f"pbkdf2:{salt}:{hashed.hex()}"
