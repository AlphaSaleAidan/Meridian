"""Team Management — employee account admin (Workstream 1c/1e).

Owner-facing control center for the org's people:

  GET    /api/team-admin/members?org_id=…          → list roster w/ roles + perms
  POST   /api/team-admin/members                    → create account, set role,
                                                        set manager permissions,
                                                        send login invite email
  PATCH  /api/team-admin/members/{member_id}        → edit role / permissions
  DELETE /api/team-admin/members/{member_id}?org_id → deactivate member
  GET    /api/team-admin/permission-schema          → taxonomy for the UI checklist

SECURITY:
  - Every mutation requires the ``manage_team`` action (owners always hold it;
    managers only if the owner ticked it). Cross-org access is blocked by the
    tenancy gate inside rbac.resolve_access.
  - org_id is validated against the caller's membership on EVERY call — a body
    org_id can never be used to act on a foreign tenant (rbac + enforce).
  - Employee auth user is created via the Supabase admin API (email_confirm),
    with org_id + role in user_metadata, then a login invite is sent through the
    EXISTING invite email path (src/email/send.send_invite). No new mailer.
  - Every role/permission change writes an append-only business_user_audit row.
"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from ..auth import require_service_auth
from .. import rbac
from ...db import get_db

logger = logging.getLogger("meridian.api.team_admin")
router = APIRouter(prefix="/api/team-admin", tags=["team-management"])

_FRONTEND = os.environ.get("MERIDIAN_FRONTEND_URL", "https://meridian.tips")


# ── Models ─────────────────────────────────────────────────────────────────
class MemberCreate(BaseModel):
    org_id: str
    email: EmailStr
    full_name: str = ""
    role: str = "employee"          # owner | manager | employee
    permissions: dict = Field(default_factory=dict)
    portal: str = "us"              # for the invite email label
    send_invite: bool = True


class MemberUpdate(BaseModel):
    org_id: str
    role: Optional[str] = None
    permissions: Optional[dict] = None


def _supabase_conf() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    return url, key


async def _write_audit(
    org_id: str, actor: dict, action: str, *,
    target_member_id: Optional[str] = None, target_user_id: Optional[str] = None,
    old_value: Optional[dict] = None, new_value: Optional[dict] = None,
) -> None:
    """Best-effort append-only audit row. Never raises."""
    try:
        db = get_db()
        actor_user = actor.get("user") or {}
        await db.insert("business_user_audit", {
            "id": str(uuid4()),
            "business_id": org_id,
            "target_member_id": target_member_id,
            "target_user_id": target_user_id,
            "actor_user_id": actor_user.get("id"),
            "actor_email": actor_user.get("email"),
            "action": action,
            "old_value": old_value,
            "new_value": new_value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("team audit write failed (non-critical): %s", exc)


async def _create_or_find_auth_user(email: str, org_id: str, role: str, full_name: str) -> tuple[Optional[str], Optional[str]]:
    """Create a Supabase auth user for the employee (or find an existing one).

    Returns (auth_user_id, temp_password). Password is None when the user already
    existed (we don't reset an existing login). Mirrors the onboarding pattern.
    """
    url, key = _supabase_conf()
    if not url or not key:
        raise HTTPException(503, "Supabase not configured")
    temp_password = secrets.token_urlsafe(12)
    headers = {"Authorization": f"Bearer {key}", "apikey": key, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{url}/auth/v1/admin/users",
            headers=headers,
            json={
                "email": email,
                "password": temp_password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": full_name,
                    "org_id": org_id,
                    "role": rbac.normalize_role(role),
                    "must_reset_password": True,
                },
            },
        )
        if resp.status_code in (200, 201):
            return resp.json().get("id"), temp_password
        if resp.status_code == 422 and "already been registered" in resp.text.lower():
            # Find the existing user; do NOT reset their password.
            from ._supabase_admin import find_auth_user_by_email
            existing = await find_auth_user_by_email(client, url, key, email)
            if existing:
                return existing.get("id"), None
        logger.error("employee auth user create failed: %s %s", resp.status_code, resp.text[:200])
        raise HTTPException(502, "Could not create employee login")


# ── Routes ─────────────────────────────────────────────────────────────────
@router.get("/permission-schema")
async def permission_schema(_auth=Depends(require_service_auth)):
    """Taxonomy for the owner's visibility/permission checklist UI."""
    return {
        "roles": [rbac.ROLE_OWNER, rbac.ROLE_MANAGER, rbac.ROLE_EMPLOYEE],
        "visibility": list(rbac.VISIBILITY_KEYS),
        "actions": list(rbac.ACTION_KEYS),
    }


@router.get("/members")
async def list_members(org_id: str = Query(...), principal=Depends(require_service_auth)):
    # Only members who can manage the team may view the full roster w/ perms.
    await rbac.require_action(principal, org_id, "manage_team")
    db = get_db()
    rows = await db.select(
        "business_users",
        filters={"business_id": f"eq.{org_id}", "is_active": "eq.true"},
        order="created_at.asc",
    )
    members = [
        {
            "id": r.get("id"),
            "email": r.get("email"),
            "full_name": r.get("full_name"),
            "role": rbac.normalize_role(r.get("role")),
            "permissions": rbac.sanitize_permissions(r.get("permissions"))
            if rbac.normalize_role(r.get("role")) != rbac.ROLE_OWNER
            else rbac.default_permissions(rbac.ROLE_OWNER),
            "invite_status": r.get("invite_status", "active"),
            "user_id": r.get("user_id"),
        }
        for r in rows
    ]
    return {"members": members, "total": len(members)}


@router.post("/members")
async def create_member(body: MemberCreate, principal=Depends(require_service_auth)):
    access = await rbac.require_action(principal, body.org_id, "manage_team")

    role = rbac.normalize_role(body.role)
    if role == rbac.ROLE_OWNER:
        # Owner is the account holder; you don't create a second owner here.
        raise HTTPException(400, "Cannot create a second owner via team admin")

    # Managers get exactly the ticked checklist; employees get their defaults
    # merged with anything explicitly granted (e.g. schedule visibility).
    perms = rbac.sanitize_permissions(body.permissions)

    auth_user_id, temp_password = await _create_or_find_auth_user(
        str(body.email), body.org_id, role, body.full_name,
    )

    db = get_db()
    member_id = str(uuid4())
    actor_user = (principal.get("user") or {})
    row = {
        "id": member_id,
        "business_id": body.org_id,
        "user_id": auth_user_id,
        "email": str(body.email),
        "full_name": body.full_name or None,
        "role": role,
        "permissions": perms,
        "is_active": True,
        "invited_by": actor_user.get("id"),
        "invited_at": datetime.now(timezone.utc).isoformat(),
        "invite_status": "pending" if body.send_invite else "active",
    }
    # business_users has a unique (business_id, email) index — upsert on conflict.
    await db.upsert("business_users", row, on_conflict="business_id,email")

    await _write_audit(
        body.org_id, principal, "create",
        target_member_id=member_id, target_user_id=auth_user_id,
        new_value={"role": role, "permissions": perms},
    )

    invite_result = None
    if body.send_invite:
        try:
            from ...email import send as email_send
            inviter_name = actor_user.get("email") or "Your manager"
            invite_url = f"{_FRONTEND}/login"
            invite_result = await email_send.send_invite(
                to=str(body.email),
                inviter_name=inviter_name,
                role=role,
                portal=body.portal,
                invite_url=invite_url,
                org_id=body.org_id,
            )
            await _write_audit(
                body.org_id, principal, "invite_sent",
                target_member_id=member_id, target_user_id=auth_user_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("invite email send failed for %s: %s", body.email, exc)

    return {
        "member": {
            "id": member_id,
            "email": str(body.email),
            "full_name": body.full_name,
            "role": role,
            "permissions": perms,
            "invite_status": row["invite_status"],
        },
        "invite_sent": bool(invite_result and invite_result.get("status") == "sent"),
        # temp_password is returned ONLY to the owner UI for out-of-band delivery
        # when email is unavailable; never logged.
        "temp_password": temp_password,
    }


@router.patch("/members/{member_id}")
async def update_member(member_id: str, body: MemberUpdate, principal=Depends(require_service_auth)):
    await rbac.require_action(principal, body.org_id, "manage_team")
    db = get_db()

    existing = await db.select(
        "business_users",
        filters={"id": f"eq.{member_id}", "business_id": f"eq.{body.org_id}"},
        limit=1,
    )
    if not existing:
        raise HTTPException(404, "Member not found in this org")
    current = existing[0]
    if rbac.normalize_role(current.get("role")) == rbac.ROLE_OWNER:
        raise HTTPException(400, "Cannot modify the owner's role or permissions")

    old_value = {
        "role": rbac.normalize_role(current.get("role")),
        "permissions": rbac.sanitize_permissions(current.get("permissions")),
    }
    updates: dict = {}
    if body.role is not None:
        new_role = rbac.normalize_role(body.role)
        if new_role == rbac.ROLE_OWNER:
            raise HTTPException(400, "Cannot promote a member to owner via team admin")
        updates["role"] = new_role
    if body.permissions is not None:
        updates["permissions"] = rbac.sanitize_permissions(body.permissions)
    if not updates:
        raise HTTPException(400, "No changes provided")

    await db.update(
        "business_users", updates,
        filters={"id": f"eq.{member_id}", "business_id": f"eq.{body.org_id}"},
    )

    action = "role_change" if "role" in updates else "permissions_change"
    await _write_audit(
        body.org_id, principal, action,
        target_member_id=member_id, target_user_id=current.get("user_id"),
        old_value=old_value,
        new_value={
            "role": updates.get("role", old_value["role"]),
            "permissions": updates.get("permissions", old_value["permissions"]),
        },
    )
    return {"member_id": member_id, "updated": updates}


@router.delete("/members/{member_id}")
async def deactivate_member(
    member_id: str, org_id: str = Query(...), principal=Depends(require_service_auth),
):
    await rbac.require_action(principal, org_id, "manage_team")
    db = get_db()
    existing = await db.select(
        "business_users",
        filters={"id": f"eq.{member_id}", "business_id": f"eq.{org_id}"},
        limit=1,
    )
    if not existing:
        raise HTTPException(404, "Member not found in this org")
    if rbac.normalize_role(existing[0].get("role")) == rbac.ROLE_OWNER:
        raise HTTPException(400, "Cannot deactivate the owner")

    await db.update(
        "business_users",
        {"is_active": False, "invite_status": "revoked"},
        filters={"id": f"eq.{member_id}", "business_id": f"eq.{org_id}"},
    )
    await _write_audit(
        org_id, principal, "deactivate",
        target_member_id=member_id, target_user_id=existing[0].get("user_id"),
    )
    return {"member_id": member_id, "active": False}
