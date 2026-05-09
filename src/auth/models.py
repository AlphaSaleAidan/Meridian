"""
User models for fastapi-users with Supabase backend.

Roles:
  - owner: Full access to organization data
  - manager: Location-scoped access
  - staff: Self-scoped access only
"""
from enum import Enum
from typing import Optional
from uuid import UUID

from fastapi_users import schemas
from pydantic import BaseModel


class UserRole(str, Enum):
    OWNER = "owner"
    MANAGER = "manager"
    STAFF = "staff"


class UserRead(schemas.BaseUser[UUID]):
    org_id: Optional[str] = None
    location_id: Optional[str] = None
    role: UserRole = UserRole.STAFF
    display_name: Optional[str] = None


class UserCreate(schemas.BaseUserCreate):
    org_id: Optional[str] = None
    location_id: Optional[str] = None
    role: UserRole = UserRole.STAFF
    display_name: Optional[str] = None


class UserUpdate(schemas.BaseUserUpdate):
    org_id: Optional[str] = None
    location_id: Optional[str] = None
    role: Optional[UserRole] = None
    display_name: Optional[str] = None


class UserDB(BaseModel):
    """Internal user representation from Supabase auth.users."""
    id: str
    email: str
    org_id: Optional[str] = None
    location_id: Optional[str] = None
    role: UserRole = UserRole.STAFF
    display_name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    is_superuser: bool = False
