"""
Auth Routes — Registration, login, password reset, verification.

Integrates with Supabase Auth directly (not fastapi-users transport)
since Supabase handles JWT issuance and password hashing.
"""
import logging
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from .manager import get_user_from_supabase
from .models import UserDB, UserRole
from .rbac import require_role

logger = logging.getLogger("meridian.auth.router")

router = APIRouter(prefix="/api/auth", tags=["auth"])

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    or os.environ.get("SUPABASE_SERVICE_KEY", "")
)


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
    """Send password reset email via Supabase."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/recover",
            json={"email": body.email},
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        )

    # Always return success to prevent email enumeration
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
    """Request email verification resend."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/resend",
            json={"type": "signup", "email": user.email},
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        )

    return {"status": "ok", "message": "Verification email sent"}
