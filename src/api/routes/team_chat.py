"""Internal team chat — org-scoped channels + messages (Workstream 1d).

  GET  /api/team-chat/channels?org_id            → list org channels
  POST /api/team-chat/channels                    → create a channel (manage_team)
  GET  /api/team-chat/messages?org_id&channel_id  → recent messages in a channel
  POST /api/team-chat/messages                    → post a message (post_chat)

SECURITY:
  - org_id validated against caller membership on every call (rbac gate).
  - Reads require membership (any active member). Posting requires the baseline
    ``post_chat`` action (all active members hold it unless explicitly revoked).
  - A channel_id is verified to belong to org_id before read/post (BOLA guard),
    so a member cannot read/post into another tenant's channel.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth import require_service_auth
from .. import rbac
from ...db import get_db

logger = logging.getLogger("meridian.api.team_chat")
router = APIRouter(prefix="/api/team-chat", tags=["team-management"])

_MAX_BODY = 4000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChannelCreate(BaseModel):
    org_id: str
    name: str
    description: str = ""


class MessageCreate(BaseModel):
    org_id: str
    channel_id: str
    body: str


async def _channel_in_org(channel_id: str, org_id: str) -> Optional[dict]:
    db = get_db()
    rows = await db.select(
        "team_channels",
        filters={"id": f"eq.{channel_id}", "org_id": f"eq.{org_id}"},
        limit=1,
    )
    return rows[0] if rows else None


@router.get("/channels")
async def list_channels(org_id: str = Query(...), principal=Depends(require_service_auth)):
    # Membership is sufficient to see channels.
    await rbac.resolve_access(principal, org_id)
    db = get_db()
    rows = await db.select(
        "team_channels",
        filters={"org_id": f"eq.{org_id}", "archived": "eq.false"},
        order="created_at.asc",
    )
    if not rows:
        # Lazily provision a default #general channel so the UI is never empty.
        default = {
            "id": str(uuid4()),
            "org_id": org_id,
            "name": "general",
            "description": "Team-wide channel",
            "is_default": True,
            "archived": False,
            "created_at": _now_iso(),
        }
        try:
            await db.insert("team_channels", default)
            rows = [default]
        except Exception as exc:  # noqa: BLE001
            logger.warning("default channel provision failed: %s", exc)
    return {"channels": rows, "total": len(rows)}


@router.post("/channels")
async def create_channel(body: ChannelCreate, principal=Depends(require_service_auth)):
    # Creating channels is a management action.
    access = await rbac.require_action(principal, body.org_id, "manage_team")
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "Channel name required")
    db = get_db()
    channel = {
        "id": str(uuid4()),
        "org_id": body.org_id,
        "name": name,
        "description": (body.description or "").strip(),
        "is_default": False,
        "archived": False,
        "created_by": (principal.get("user") or {}).get("id"),
        "created_at": _now_iso(),
    }
    try:
        rows = await db.insert("team_channels", channel)
    except Exception:
        # unique (org, lower(name)) collision
        raise HTTPException(409, "A channel with that name already exists")
    _ = access
    return {"channel": rows[0] if rows else channel}


@router.get("/messages")
async def list_messages(
    org_id: str = Query(...),
    channel_id: str = Query(...),
    principal=Depends(require_service_auth),
    limit: int = Query(50, ge=1, le=200),
):
    await rbac.resolve_access(principal, org_id)
    if not await _channel_in_org(channel_id, org_id):
        raise HTTPException(404, "Channel not found in this org")
    db = get_db()
    rows = await db.select(
        "team_messages",
        filters={"channel_id": f"eq.{channel_id}", "org_id": f"eq.{org_id}", "deleted": "eq.false"},
        order="created_at.desc",
        limit=limit,
    )
    rows = list(reversed(rows))  # oldest-first for display
    return {"messages": rows, "total": len(rows)}


@router.post("/messages")
async def post_message(body: MessageCreate, principal=Depends(require_service_auth)):
    text = (body.body or "").strip()
    if not text:
        raise HTTPException(400, "Message body required")
    if len(text) > _MAX_BODY:
        raise HTTPException(400, f"Message too long (max {_MAX_BODY} chars)")
    # Posting requires the baseline post_chat action.
    access = await rbac.require_action(principal, body.org_id, "post_chat")
    if not await _channel_in_org(body.channel_id, body.org_id):
        raise HTTPException(404, "Channel not found in this org")

    db = get_db()
    user = principal.get("user") or {}
    msg = {
        "id": str(uuid4()),
        "org_id": body.org_id,
        "channel_id": body.channel_id,
        "author_user_id": user.get("id"),
        "author_member_id": access.get("member_id"),
        "author_name": user.get("email") or "Member",
        "body": text,
        "deleted": False,
        "created_at": _now_iso(),
    }
    rows = await db.insert("team_messages", msg)
    return {"message": rows[0] if rows else msg}
