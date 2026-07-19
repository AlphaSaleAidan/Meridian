"""Team Management RBAC — server-side role + permission enforcement.

Three roles (migration 051, stored on ``business_users``):

    owner     — full access to everything in the org. Bypasses the permission
                object entirely.
    manager   — visibility + permissions are configured BY THE OWNER at creation
                (nothing default-granted) and editable later. Gated by the
                structured ``permissions`` jsonb.
    employee  — their own shifts + (optionally) the team schedule + internal
                chat. No management actions.

This module is the ONE place that answers "may principal P perform action A in
org O?". It sits ON TOP of ``auth.enforce_service_member`` (which only proves
membership, not permission) and is called by every management route.

Security invariants:
  - org_id is ALWAYS the caller's authenticated org — the ROUTE derives it and
    passes it here; this module never trusts an org id from a request body.
  - Machine principals (X-Admin-Key / service token) and ADMIN_EMAILS users are
    treated as owners (support access), consistent with the rest of auth.py.
  - Unknown / missing member row => deny (fail closed).
  - The permission object is allow-list only: an absent key means NOT granted.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx
from fastapi import HTTPException

from .auth import ADMIN_EMAILS, enforce_service_member

logger = logging.getLogger("meridian.api.rbac")

# ── Permission taxonomy ────────────────────────────────────────────────────
# VISIBILITY: which tabs/features a member can SEE.
VISIBILITY_KEYS = (
    "financials",            # revenue, margins, taxes/expenses, staff pay
    "phone_agent_analytics",
    "staff_pay",
    "schedule",              # team schedule (employees may get this if owner allows)
    "camera",
    "chatbot",
)

# ACTIONS: what a member can DO.
ACTION_KEYS = (
    "edit_schedule",
    "publish_schedule",
    "edit_punches",
    "change_phone_agent",
    "manage_chatbot",
    "invite_employees",
    "manage_team",           # create/edit members, set roles/permissions
    "post_chat",             # post in internal chat (default true for all members)
)

ROLE_OWNER = "owner"
ROLE_MANAGER = "manager"
ROLE_EMPLOYEE = "employee"
_LEGACY_STAFF = "staff"  # historical value; treated as employee


def normalize_role(role: Optional[str]) -> str:
    r = (role or "").strip().lower()
    if r == _LEGACY_STAFF:
        return ROLE_EMPLOYEE
    if r in (ROLE_OWNER, ROLE_MANAGER, ROLE_EMPLOYEE):
        return r
    return ROLE_EMPLOYEE  # unknown => least privilege


def default_permissions(role: str) -> dict:
    """Baseline permissions for a role at creation.

    NOTHING is default-granted for a manager (the owner ticks the checklist).
    Employees get chat-post + their-own-schedule visibility only. Owners bypass
    the object, so their defaults are illustrative (all true).
    """
    role = normalize_role(role)
    if role == ROLE_OWNER:
        return {
            "visibility": {k: True for k in VISIBILITY_KEYS},
            "actions": {k: True for k in ACTION_KEYS},
        }
    if role == ROLE_EMPLOYEE:
        return {
            "visibility": {k: False for k in VISIBILITY_KEYS},
            "actions": {k: False for k in ACTION_KEYS} | {"post_chat": True},
        }
    # manager — nothing default-granted
    return {
        "visibility": {k: False for k in VISIBILITY_KEYS},
        "actions": {k: False for k in ACTION_KEYS} | {"post_chat": True},
    }


def sanitize_permissions(raw: Optional[dict]) -> dict:
    """Coerce an arbitrary permissions payload into the canonical shape,
    dropping unknown keys and forcing booleans. Absent keys => False."""
    raw = raw or {}
    vis_in = raw.get("visibility") or {}
    act_in = raw.get("actions") or {}
    return {
        "visibility": {k: bool(vis_in.get(k, False)) for k in VISIBILITY_KEYS},
        "actions": {k: bool(act_in.get(k, False)) for k in ACTION_KEYS},
    }


def _principal_is_machine_or_admin(principal: dict) -> bool:
    if not principal:
        return False
    if principal.get("kind") in ("admin", "service"):
        return True
    email = ((principal.get("user") or {}).get("email") or "").lower()
    return bool(email) and email in [e.lower() for e in ADMIN_EMAILS]


def _supabase_conf() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    return url, key


async def _fetch_member(user_id: str, org_id: str) -> Optional[dict]:
    """Return the business_users row for (user_id, org_id) or None.

    Uses the service-role REST API (same pattern as auth._check_org_membership).
    Only active members are considered.
    """
    url, key = _supabase_conf()
    if not url or not key or not user_id or not org_id:
        return None
    headers = {"Authorization": f"Bearer {key}", "apikey": key}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{url}/rest/v1/business_users",
                params={
                    "business_id": f"eq.{org_id}",
                    "user_id": f"eq.{user_id}",
                    "is_active": "eq.true",
                    "select": "id,role,permissions,email,full_name",
                    "limit": "1",
                },
                headers=headers,
            )
            if resp.status_code == 200 and resp.json():
                return resp.json()[0]
    except Exception as exc:  # noqa: BLE001
        logger.warning("rbac member lookup failed user=%s org=%s: %s", user_id, org_id, exc)
    return None


async def _is_org_owner(user_id: str, org_id: str) -> bool:
    url, key = _supabase_conf()
    if not url or not key or not user_id or not org_id:
        return False
    headers = {"Authorization": f"Bearer {key}", "apikey": key}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{url}/rest/v1/businesses",
                params={"id": f"eq.{org_id}", "owner_user_id": f"eq.{user_id}", "select": "id"},
                headers=headers,
            )
            return resp.status_code == 200 and bool(resp.json())
    except Exception as exc:  # noqa: BLE001
        logger.warning("rbac owner lookup failed user=%s org=%s: %s", user_id, org_id, exc)
    return False


async def resolve_access(principal: dict, org_id: str) -> dict:
    """Resolve the caller's effective access in ``org_id``.

    Returns ``{"role": str, "permissions": dict, "is_owner": bool, "member_id": str|None}``.

    First proves membership via ``enforce_service_member`` (raises 403 on a
    cross-tenant attempt), then determines the role + permission object.
    Machine/admin principals resolve to owner.
    """
    # Membership / tenancy gate first — raises 403 on cross-org access.
    await enforce_service_member(principal, org_id)

    if _principal_is_machine_or_admin(principal):
        return {
            "role": ROLE_OWNER,
            "permissions": default_permissions(ROLE_OWNER),
            "is_owner": True,
            "member_id": None,
        }

    user = principal.get("user") or {}
    user_id = user.get("id") or user.get("sub") or ""

    if await _is_org_owner(user_id, org_id):
        return {
            "role": ROLE_OWNER,
            "permissions": default_permissions(ROLE_OWNER),
            "is_owner": True,
            "member_id": None,
        }

    member = await _fetch_member(user_id, org_id)
    if not member:
        # Passed enforce_service_member (e.g. TENANCY_ENFORCEMENT_DISABLED) but
        # has no role row => least privilege.
        return {
            "role": ROLE_EMPLOYEE,
            "permissions": default_permissions(ROLE_EMPLOYEE),
            "is_owner": False,
            "member_id": None,
        }

    role = normalize_role(member.get("role"))
    if role == ROLE_OWNER:
        perms = default_permissions(ROLE_OWNER)
        is_owner = True
    else:
        perms = sanitize_permissions(member.get("permissions"))
        is_owner = False
    return {
        "role": role,
        "permissions": perms,
        "is_owner": is_owner,
        "member_id": member.get("id"),
    }


# Actions every active member holds regardless of the stored permission object
# (chat is a baseline capability of the internal team surface).
_BASELINE_ACTIONS = ("post_chat",)


def _has(access: dict, category: str, key: str) -> bool:
    if access.get("is_owner") or access.get("role") == ROLE_OWNER:
        return True
    if category == "actions" and key in _BASELINE_ACTIONS:
        return True
    return bool((access.get("permissions") or {}).get(category, {}).get(key, False))


async def require_action(principal: dict, org_id: str, action: str) -> dict:
    """Authorize ``principal`` to perform ``action`` in ``org_id``.

    Raises 403 if the action is not granted. Returns the resolved access dict on
    success so the caller can reuse role/member_id for audit rows.
    """
    if action not in ACTION_KEYS:
        raise HTTPException(500, f"Unknown RBAC action: {action}")
    access = await resolve_access(principal, org_id)
    if not _has(access, "actions", action):
        logger.warning(
            "RBAC_DENY action=%s role=%s org=%s member=%s",
            action, access.get("role"), org_id, access.get("member_id"),
        )
        raise HTTPException(403, f"You do not have permission to: {action}")
    return access


async def require_visibility(principal: dict, org_id: str, feature: str) -> dict:
    """Authorize ``principal`` to SEE ``feature`` in ``org_id``. Raises 403 if not."""
    if feature not in VISIBILITY_KEYS:
        raise HTTPException(500, f"Unknown RBAC visibility feature: {feature}")
    access = await resolve_access(principal, org_id)
    if not _has(access, "visibility", feature):
        logger.warning(
            "RBAC_DENY visibility=%s role=%s org=%s member=%s",
            feature, access.get("role"), org_id, access.get("member_id"),
        )
        raise HTTPException(403, f"You do not have access to: {feature}")
    return access


async def require_owner(principal: dict, org_id: str) -> dict:
    """Authorize ``principal`` as the org OWNER (or machine/admin). Raises 403."""
    access = await resolve_access(principal, org_id)
    if not access.get("is_owner"):
        logger.warning("RBAC_DENY owner-only role=%s org=%s", access.get("role"), org_id)
        raise HTTPException(403, "Owner access required")
    return access
