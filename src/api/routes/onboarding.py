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
    os.environ.get("FRONTEND_ORIGIN", "https://meridian-dun-nu.vercel.app"),
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
    login_url = f"{_FRONTEND_URL}/login"

    email_body = (
        f"Welcome to Meridian, {org['name']}!\n\n"
        f"Your POS intelligence platform is ready. Here's how to get started:\n\n"
        f"1. Log in: {login_url}\n"
        f"2. Connect Your Square POS: {connect_url}\n"
        f"3. Your data will sync in 10-30 minutes after connecting.\n\n"
        f"Once connected, Meridian will analyze your transaction history "
        f"and start generating actionable insights for your business."
    )

    # TODO: Replace with actual email service (SendGrid/Resend/SES)
    logger.info(f"Welcome email for {req.email}:\n{email_body}")

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

    return {"status": "sent", "email": req.email, "org_id": req.org_id}


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
