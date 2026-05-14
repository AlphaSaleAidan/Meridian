"""
Onboarding Routes — New customer account creation and welcome flow.

  POST /api/onboarding/create-account  → Create org + admin user
  POST /api/onboarding/send-welcome    → Send welcome email with Square connect link
"""
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
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

    # 3. Send setup fee invoice (card stored on payment → auto-billing starts)
    invoices_sent = False
    setup_result = None
    try:
        from src.billing.billing_service import BillingService
        billing = BillingService(db)

        plan_label = req.plan.replace("_", " ").title()

        # Single invoice for setup fee — store_card=True so card is saved
        # when customer pays. Monthly auto-billing via Square Subscription
        # is created by the webhook after this invoice is paid.
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

            # Get or create Square customer for subscription later
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

    # 4. Send credentials email via Postal/Resend
    welcome_sent = False
    login_url = f"{_FRONTEND_URL}/canada/login"
    try:
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

        await db.insert("notifications", {
            "id": str(uuid4()),
            "org_id": req.org_id,
            "title": f"Welcome to Meridian — {req.business_name}",
            "body": f"Credentials email sent to {req.email}",
            "priority": "high",
            "source_type": "event",
            "status": "active",
            "created_at": now,
        })
    except Exception as e:
        logger.warning(f"Credentials email failed: {e}")

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


class ConnectPosRequest(BaseModel):
    deal_id: str | None = None
    provider: str
    credentials: dict
    business_name: str | None = None


class VerifyPosRequest(BaseModel):
    deal_id: str | None = None
    provider: str


@router.post("/connect-pos")
async def connect_pos_onboarding(req: ConnectPosRequest):
    """Test POS credentials then save if valid. Called from lead detail page."""
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
                "deals",
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


@router.post("/verify-pos")
async def verify_pos_onboarding(req: VerifyPosRequest):
    """Quick verify that POS connection is still live."""
    from .pos_connections import test_connection, TestConnectionRequest

    if req.deal_id:
        db = get_db()
        try:
            rows = await db.select("deals", filters={"id": f"eq.{req.deal_id}"}, limit=1)
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
