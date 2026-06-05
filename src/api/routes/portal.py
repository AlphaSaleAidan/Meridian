"""
Portal token routes — secure per-customer portal URLs.

Each customer gets a unique portal token (e.g. /c/8f2a9b3c4d) stored in
businesses.access_token. This gives them an exclusive URL for their dashboard.

Endpoints:
  GET  /api/portal/resolve/:token  → Resolve token to org details (no auth — token IS the auth)
  POST /api/portal/generate        → Generate/get portal token for an org
"""
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_service_auth
from ...db import get_db

logger = logging.getLogger("meridian.api.portal")

router = APIRouter(prefix="/api/portal", tags=["portal"])


def _generate_token() -> str:
    return secrets.token_urlsafe(16)


class GenerateTokenRequest(BaseModel):
    org_id: str


class PortalTokenResponse(BaseModel):
    token: str
    org_id: str
    portal_url: str


@router.get("/resolve/{token}")
async def resolve_portal_token(token: str):
    """Resolve a portal token to the org details. No auth required (token IS the auth)."""
    if not token or len(token) < 8:
        raise HTTPException(400, "Invalid token")

    db = get_db()

    rows = await db.select(
        "businesses",
        filters={"access_token": f"eq.{token}", "status": "eq.active"},
        limit=1,
    )

    if not rows:
        raise HTTPException(404, "Portal link expired or invalid")

    biz = rows[0]

    return {
        "org_id": biz["id"],
        "business_name": biz.get("name", ""),
        "plan_tier": biz.get("plan_tier", "starter"),
        "portal_token": token,
        "pos_provider": biz.get("pos_provider"),
        "onboarded": biz.get("onboarded", False),
    }


@router.post("/generate", response_model=PortalTokenResponse, dependencies=[Depends(require_service_auth)])
async def generate_token(req: GenerateTokenRequest):
    """Generate a unique portal token for a customer org, or return existing one."""
    db = get_db()

    rows = await db.select("businesses", filters={"id": f"eq.{req.org_id}"}, limit=1)
    if not rows:
        raise HTTPException(404, "Business not found")

    biz = rows[0]
    token = biz.get("access_token")

    if not token:
        token = _generate_token()
        await db.update("businesses", {"access_token": token, "token_status": "pending"}, filters={"id": f"eq.{req.org_id}"})

    portal_url = f"https://canada.meridian.tips/c/{token}"

    return PortalTokenResponse(
        token=token,
        org_id=req.org_id,
        portal_url=portal_url,
    )
