"""
Onboarding Routes — New customer account creation and welcome flow.

  POST /api/onboarding/create-account  → Create org + admin user
  POST /api/onboarding/send-welcome    → Send welcome email with Square connect link
"""
import logging
import os
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

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


class CreateAccountResponse(BaseModel):
    org_id: str
    admin_user_id: str
    temporary_password: str
    login_url: str
    connect_square_url: str


class SendWelcomeRequest(BaseModel):
    org_id: str
    email: EmailStr


@router.post("/create-account", response_model=CreateAccountResponse)
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
            "status": "active",
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
async def send_welcome(req: SendWelcomeRequest):
    """
    Send welcome email with login link and Square connect button.

    In production, integrate with SendGrid/Resend/SES.
    For now, logs the email content and creates a notification.
    """
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
        "status": "active",
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

    db = get_db()

    try:
        req = CreateAccountRequest(
            email=customer_email,
            business_name=business_name,
            plan="starter",
            square_payment_id=payment_id,
        )
        result = await create_account(req)

        await send_welcome(SendWelcomeRequest(
            org_id=result.org_id,
            email=customer_email,
        ))

        logger.info(f"Auto-onboarding complete for {customer_email}, org={result.org_id}")
    except Exception as e:
        logger.error(f"Auto-onboarding failed for {customer_email}: {e}", exc_info=True)


# ── SR-Driven Customer Provisioning ─────────────────────────

class ProvisionCustomerRequest(BaseModel):
    org_id: str
    email: EmailStr
    owner_name: str
    business_name: str
    phone: str | None = None
    plan: str = "starter"
    monthly_price: int = 500
    rep_id: str | None = None
    rep_name: str | None = None


class ProvisionCustomerResponse(BaseModel):
    org_id: str
    email: str
    temporary_password: str
    login_url: str
    invoices_sent: bool
    welcome_email_sent: bool
    invoice_sms_sent: bool = False


@router.post("/provision-customer", response_model=ProvisionCustomerResponse)
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
                },
            },
        )
        if resp.status_code in (200, 201):
            auth_user_id = resp.json().get("id")
            logger.info(f"Created auth user {auth_user_id} for {req.email}")
        elif resp.status_code == 422 and "already been registered" in resp.text.lower():
            logger.info(f"Auth user already exists for {req.email} — proceeding")
        else:
            logger.error(f"Auth user creation failed: {resp.status_code} {resp.text}")
            raise HTTPException(400, f"Could not create user account: {resp.json().get('msg', 'Unknown error')}")

    # 2. Create business record linking auth user to org
    if auth_user_id:
        try:
            await db.upsert("businesses", {
                "id": req.org_id,
                "owner_user_id": auth_user_id,
                "name": req.business_name,
                "owner_name": req.owner_name,
                "email": req.email,
                "plan_tier": req.plan,
                "pos_connected": False,
                "onboarded": True,
                "created_at": now,
            }, on_conflict="id")
        except Exception as e:
            logger.warning(f"Business upsert warning: {e}")

    # 3. Send Square invoices (setup fee + monthly recurring)
    invoices_sent = False
    try:
        from src.billing.billing_service import BillingService
        billing = BillingService(db)

        plan_label = req.plan.replace("_", " ").title()

        setup_result = await billing.create_invoice(
            org_id=req.org_id,
            amount_cents=req.monthly_price * 100,
            customer_email=req.email,
            description=f"Meridian Analytics - {plan_label} Plan (Setup Fee)",
            due_days=3,
        )
        recurring_result = await billing.create_invoice(
            org_id=req.org_id,
            amount_cents=req.monthly_price * 100,
            customer_email=req.email,
            description=f"Meridian Analytics - {plan_label} Plan (Monthly Recurring)",
            due_days=30,
        )

        invoices_sent = setup_result.success and recurring_result.success
        if invoices_sent:
            logger.info(f"Sent invoices for {req.email}: setup={setup_result.invoice_id}, recurring={recurring_result.invoice_id}")

            await db.upsert("subscriptions", {
                "org_id": req.org_id,
                "tier": req.plan,
                "status": "pending_payment",
                "monthly_price_cents": req.monthly_price * 100,
                "current_period_start": now,
                "metadata": {
                    "payment_method": "square_invoice",
                    "setup_invoice_id": setup_result.invoice_id,
                    "recurring_invoice_id": recurring_result.invoice_id,
                    "created_via": "sr_provision",
                    "rep_id": req.rep_id,
                },
            }, on_conflict="org_id")
    except ImportError:
        logger.warning("Billing service not available — skipping invoices")
    except Exception as e:
        logger.warning(f"Invoice creation failed: {e}")

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

    # 4. Send welcome email with credentials via Postal
    welcome_sent = False
    login_url = f"{_FRONTEND_URL}/customer/login"
    try:
        from ...email.send import send_welcome_email
        email_result = await send_welcome_email(
            to=req.email,
            first_name=req.owner_name.split()[0],
            org_id=req.org_id,
        )
        welcome_sent = email_result.get("status") == "sent"

        await db.insert("notifications", {
            "id": str(uuid4()),
            "org_id": req.org_id,
            "title": f"Welcome to Meridian — {req.business_name}",
            "body": f"Welcome email sent to {req.email}",
            "priority": "high",
            "source_type": "event",
            "status": "active",
            "created_at": now,
        })
    except Exception as e:
        logger.warning(f"Welcome email failed: {e}")

    return ProvisionCustomerResponse(
        org_id=req.org_id,
        email=req.email,
        temporary_password=temp_password,
        login_url=login_url,
        invoices_sent=invoices_sent,
        welcome_email_sent=welcome_sent,
        invoice_sms_sent=sms_sent,
    )


class SendInvoiceSmsRequest(BaseModel):
    phone: str
    owner_name: str
    business_name: str
    invoice_url: str
    plan_label: str = "Starter"
    amount_display: str = "$250/mo"


@router.post("/send-invoice-sms")
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
