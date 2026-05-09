"""
Role-Based Access Control (RBAC) for Meridian.

Roles:
  - owner: Full access to all org data
  - manager: Access scoped to their location(s)
  - staff: Access scoped to their own data only

Usage in routes:
    @router.get("/admin/settings")
    async def admin_settings(user = Depends(require_role(UserRole.OWNER))):
        ...

    @router.get("/location/data")
    async def location_data(user = Depends(require_role(UserRole.MANAGER))):
        ...
"""
from typing import Callable

from fastapi import Depends, HTTPException

from .models import UserDB, UserRole

ROLE_HIERARCHY = {
    UserRole.OWNER: 3,
    UserRole.MANAGER: 2,
    UserRole.STAFF: 1,
}


def require_role(minimum_role: UserRole) -> Callable:
    """FastAPI dependency that enforces a minimum role level."""

    async def _check_role(user: UserDB = Depends()):
        user_level = ROLE_HIERARCHY.get(user.role, 0)
        required_level = ROLE_HIERARCHY.get(minimum_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Requires {minimum_role.value} role or higher",
            )
        return user

    return _check_role


def scope_query_to_user(user: UserDB, filters: dict) -> dict:
    """Add RBAC-based filtering to a database query.

    - owner: org_id filter only
    - manager: org_id + location_id
    - staff: org_id + user_id (own data only)
    """
    if not user.org_id:
        raise HTTPException(status_code=403, detail="User not associated with an organization")

    filters["org_id"] = f"eq.{user.org_id}"

    if user.role == UserRole.MANAGER and user.location_id:
        filters["location_id"] = f"eq.{user.location_id}"
    elif user.role == UserRole.STAFF:
        filters["user_id"] = f"eq.{user.id}"

    return filters
