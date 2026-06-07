"""
Auth Routes — Registration, login, password reset, verification.

Integrates with Supabase Auth directly (not fastapi-users transport)
since Supabase handles JWT issuance and password hashing.
"""
import logging
import os
from typing import Optional
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from .manager import get_user_from_supabase
from .models import UserDB, UserRole

logger = logging.getLogger("meridian.auth.router")

router = APIRouter(prefix="/api/auth", tags=["auth"])

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    or os.environ.get("SUPABASE_SERVICE_KEY", "")
)
# Where the password-reset email link should land. Supabase otherwise uses its
# configured site_url (currently a stale Vercel URL), which produces broken
# reset links for meridian.tips customers. Must also be in Supabase's redirect
# allow-list. Empty = fall back to Supabase's site_url (current behaviour).
PASSWORD_RESET_REDIRECT_URL = os.environ.get("PASSWORD_RESET_REDIRECT_URL", "")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None
    org_id: Optional[str] = None
    role: UserRole = UserRole.STAFF


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    access_token: str
    new_password: str


async def get_current_user(request: Request) -> UserDB:
    """Extract and validate user from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth.removeprefix("Bearer ")
    user = await get_user_from_supabase(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


@router.post("/register")
async def register(body: RegisterRequest):
    """Register a new user via Supabase Auth."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/signup",
            json={
                "email": body.email,
                "password": body.password,
                "data": {
                    "display_name": body.display_name,
                    "org_id": body.org_id,
                    "role": body.role.value,
                },
            },
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        )

    if resp.status_code not in (200, 201):
        detail = resp.json().get("msg", resp.text)
        raise HTTPException(status_code=resp.status_code, detail=detail)

    data = resp.json()
    logger.info(f"User registered: {body.email}")

    # Grant free starter credits to this merchant. Idempotent — calling it
    # again from another signup path (sales rep portal, etc) is safe.
    if body.org_id:
        try:
            from ..credits import ensure_starter_grant
            new_balance = await ensure_starter_grant(body.org_id)
            logger.info("Starter grant for %s: balance now %d", body.org_id, new_balance)
        except Exception as e:
            # Never fail signup just because the credit grant flopped — the
            # admin can issue the grant manually via /api/credits/grant.
            logger.warning("Starter grant for %s failed: %s", body.org_id, e)

    return {"id": data.get("id"), "email": body.email, "status": "registered"}


@router.post("/login")
async def login(body: LoginRequest):
    """Login via Supabase Auth — returns JWT tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            json={"email": body.email, "password": body.password},
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    data = resp.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "expires_in": data.get("expires_in"),
        "user": {
            "id": data["user"]["id"],
            "email": data["user"]["email"],
            "role": data["user"].get("user_metadata", {}).get("role", "staff"),
        },
    }


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """Send password reset email via Supabase.

    Always returns a generic success to prevent email enumeration. But we no
    longer swallow *infrastructure* failures: a 429 (Supabase's built-in SMTP
    is capped at 2 emails/hour) or a 5xx means recovery email is actually
    broken, and that must be visible to ops rather than masked behind the
    generic response. Unknown-email 4xx stays quiet (debug only) so logs don't
    become an enumeration oracle.
    """
    url = f"{SUPABASE_URL}/auth/v1/recover"
    if PASSWORD_RESET_REDIRECT_URL:
        url += f"?redirect_to={quote(PASSWORD_RESET_REDIRECT_URL, safe='')}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json={"email": body.email},
                headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            )
    except httpx.HTTPError as e:
        logger.error("forgot-password: transport error reaching Supabase recover: %s", e)
        return {"status": "ok", "message": "If the email exists, a reset link has been sent"}

    if resp.status_code == 429:
        logger.error(
            "forgot-password: Supabase recover rate-limited (429) — built-in SMTP "
            "2/hr cap likely hit; configure custom SMTP. resp=%s",
            resp.text[:200],
        )
    elif resp.status_code >= 500:
        logger.error(
            "forgot-password: Supabase recover %s: %s", resp.status_code, resp.text[:200]
        )
    elif resp.status_code not in (200, 201):
        # Typically an unknown/invalid email — expected; keep it out of warn-level
        # logs to avoid an enumeration signal.
        logger.debug(
            "forgot-password: Supabase recover %s: %s", resp.status_code, resp.text[:200]
        )

    return {"status": "ok", "message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    """Reset password with token from email link."""
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{SUPABASE_URL}/auth/v1/user",
            json={"password": body.new_password},
            headers={
                "Authorization": f"Bearer {body.access_token}",
                "apikey": SUPABASE_SERVICE_KEY,
                "Content-Type": "application/json",
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Password reset failed")

    return {"status": "ok", "message": "Password updated"}


@router.get("/me")
async def get_me(user: UserDB = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return {
        "id": user.id,
        "email": user.email,
        "org_id": user.org_id,
        "location_id": user.location_id,
        "role": user.role.value,
        "display_name": user.display_name,
        "is_verified": user.is_verified,
    }


@router.post("/verify")
async def request_verification(user: UserDB = Depends(get_current_user)):
    """Request email verification resend.

    Like forgot-password, this goes through Supabase's email sender, so a 429
    (built-in SMTP 2/hr cap) or 5xx means the verification email silently never
    arrives. Surface those to ops instead of always reporting success.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{SUPABASE_URL}/auth/v1/resend",
                json={"type": "signup", "email": user.email},
                headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            )
    except httpx.HTTPError as e:
        logger.error("verify: transport error reaching Supabase resend: %s", e)
        return {"status": "ok", "message": "Verification email sent"}

    if resp.status_code == 429:
        logger.error(
            "verify: Supabase resend rate-limited (429) — built-in SMTP 2/hr cap "
            "likely hit; configure custom SMTP. resp=%s",
            resp.text[:200],
        )
    elif resp.status_code >= 500:
        logger.error("verify: Supabase resend %s: %s", resp.status_code, resp.text[:200])

    return {"status": "ok", "message": "Verification email sent"}
