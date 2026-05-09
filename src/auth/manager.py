"""
User Manager — Bridges fastapi-users with Supabase Auth.

Handles user creation, verification, and password reset
using Supabase as the backend instead of SQLAlchemy.
"""
import logging
import os
from typing import Optional

import httpx
from fastapi import Request
from fastapi_users import BaseUserManager, UUIDIDMixin

from .models import UserDB, UserRole

logger = logging.getLogger("meridian.auth")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    or os.environ.get("SUPABASE_SERVICE_KEY", "")
)
SECRET = os.environ.get("AUTH_SECRET", "meridian-auth-secret-change-in-production")


class UserManager(UUIDIDMixin, BaseUserManager):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user, request: Optional[Request] = None):
        logger.info(f"User registered: {user.id} ({user.email})")

    async def on_after_forgot_password(self, user, token: str, request: Optional[Request] = None):
        logger.info(f"Password reset requested for {user.email}, token={token[:8]}...")

    async def on_after_request_verify(self, user, token: str, request: Optional[Request] = None):
        logger.info(f"Verification requested for {user.email}, token={token[:8]}...")


async def get_user_from_supabase(token: str) -> Optional[UserDB]:
    """Validate a Supabase JWT and return the user."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": SUPABASE_SERVICE_KEY,
            },
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        metadata = data.get("user_metadata", {})
        return UserDB(
            id=data["id"],
            email=data.get("email", ""),
            org_id=metadata.get("org_id"),
            location_id=metadata.get("location_id"),
            role=UserRole(metadata.get("role", "staff")),
            display_name=metadata.get("display_name"),
            is_active=True,
            is_verified=data.get("email_confirmed_at") is not None,
        )
