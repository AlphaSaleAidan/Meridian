"""
Multi-Location Hub routes — Command-tier only.

One authenticated identity (same email) operating MANY orgs/locations from one
command surface. Every endpoint here:

  - derives the acting identity from the SESSION JWT (require_jwt), never a body;
  - is gated SERVER-SIDE to the Command tier (require_command_hub) — hiding the
    UI is not the control; a non-Command org gets 403 even hitting the endpoint
    directly;
  - re-scopes to orgs the identity actually belongs to (no cross-org leakage).

Spec: docs/multi-location-hub-journey.md
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import require_jwt
from ..hub_service import (
    aggregate_overview,
    assert_org_switchable,
    list_identity_orgs,
    push_down,
    verify_and_link_org,
)
from ...billing.tiers import resolve_org_command_tier
from ...db import get_db

logger = logging.getLogger("meridian.api.hub")

router = APIRouter(prefix="/api/hub", tags=["hub"])


def _uid(user: dict) -> str:
    return user.get("id") or user.get("sub") or ""


async def require_command_hub(
    org_id: str = Query(..., description="The hub org (must be Command tier)"),
    user: dict = Depends(require_jwt),
) -> dict:
    """Command-tier server-side gate for the whole hub.

    `org_id` here is the HUB org the owner operates from (the switcher's active
    org). We (1) verify the identity belongs to it — no reading tier for an org
    you don't control — and (2) verify that org is on the Command tier. Either
    failure → 403. Tier is resolved from the org record / billing contract, never
    the request body.

    Returns {"user": ..., "user_id": ..., "hub_org_id": ...} for handlers.
    """
    uid = _uid(user)
    if not uid:
        raise HTTPException(401, "Invalid session")
    db = get_db()

    # (1) identity must belong to the hub org.
    from ..hub_service import _identity_controls_org
    controls, _ = await _identity_controls_org(db, uid, org_id)
    if not controls:
        # Membership rows are also an acceptable proof (already-connected org).
        rows = await db.select(
            "identity_org_memberships",
            columns="org_id",
            filters={"user_id": f"eq.{uid}", "org_id": f"eq.{org_id}", "is_active": "eq.true"},
            limit=1,
        )
        if not rows:
            raise HTTPException(403, "Not a member of this org")

    # (2) the hub org must be Command tier (fail-closed resolver).
    if not await resolve_org_command_tier(db, org_id):
        logger.info("HUB_GATE_DENY user=%s org=%s (not Command tier)", uid, org_id)
        raise HTTPException(403, "Multi-Location Hub requires the Command plan")

    return {"user": user, "user_id": uid, "hub_org_id": org_id}


# ── Switcher / membership ────────────────────────────────────────────────────


@router.get("/orgs")
async def hub_orgs(ctx: dict = Depends(require_command_hub)):
    """List the orgs the session identity belongs to (the location switcher)."""
    db = get_db()
    orgs = await list_identity_orgs(db, ctx["user_id"])
    return {"orgs": orgs}


class ConnectRequest(BaseModel):
    # NOTE: this is the org being LINKED, distinct from the ?org_id= hub org used
    # by the gate. Membership is proven server-side; the body cannot self-grant.
    target_org_id: str = Field(..., min_length=3)


@router.post("/connect")
async def hub_connect(body: ConnectRequest, ctx: dict = Depends(require_command_hub)):
    """Link another Meridian portal the identity provably controls into the hub."""
    db = get_db()
    try:
        result = await verify_and_link_org(db, ctx["user_id"], body.target_org_id)
    except PermissionError:
        raise HTTPException(403, "You do not control that org")
    return result


class SwitchRequest(BaseModel):
    target_org_id: str = Field(..., min_length=3)


@router.post("/switch")
async def hub_switch(body: SwitchRequest, ctx: dict = Depends(require_command_hub)):
    """JUMP: validate the identity may switch to target_org_id, return it as the
    new active context. The frontend then re-scopes every call to it. Switching
    to an org the identity is not a member of → 403 (no A->B leakage)."""
    db = get_db()
    try:
        result = await assert_org_switchable(db, ctx["user_id"], body.target_org_id)
    except PermissionError:
        raise HTTPException(403, "Not a member of the target org")
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"active_org_id": result["org_id"], **result}


# ── Unified overview ─────────────────────────────────────────────────────────


@router.get("/overview")
async def hub_overview(
    ctx: dict = Depends(require_command_hub),
    days: int = Query(30, ge=1, le=400),
):
    """Aggregated stats across all connected locations the identity belongs to."""
    db = get_db()
    return await aggregate_overview(db, ctx["user_id"], days=days)


# ── Franchise push-down ──────────────────────────────────────────────────────


class PushDownRequest(BaseModel):
    config_type: str = Field(..., min_length=1)
    payload: dict = Field(default_factory=dict)
    target_org_ids: list[str] = Field(default_factory=list)


@router.post("/push-down")
async def hub_push_down(body: PushDownRequest, ctx: dict = Depends(require_command_hub)):
    """Deploy a config change to SELECTED branches the identity owns/administers.

    Targets are filtered server-side to owned/administered branches (unowned →
    skipped_not_owned). Returns a per-branch result for the UI's per-branch
    confirmation."""
    db = get_db()
    try:
        return await push_down(
            db,
            ctx["user_id"],
            body.config_type,
            body.payload,
            body.target_org_ids,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))
