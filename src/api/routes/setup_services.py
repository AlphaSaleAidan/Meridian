"""
Setup Services API — the work-order record behind every adder product.

    the merchant PAYS → a work order is created → it is posted to the Foundry
    dev marketplace → devs bid with actual work → the OWNER picks.

The rep portals call POST /api/setup-services/order once per toggled service
at close. Nothing is posted to the marketplace here: posting happens when the
Stripe payment lands (see src/services/setup_services.dispatch_paid_orders,
called from the checkout webhook). Recording and posting are separate on
purpose — a rep closing a deal is not a merchant paying for one.

Routes:
  POST /api/setup-services/order        → record a sold adder as a work order
  GET  /api/setup-services              → work orders for a rep (or recent)
  GET  /api/setup-services/{order_id}   → one work order
  POST /api/setup-services/{id}/post    → post it now (ops override)
"""

import logging
import os
import re
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from ..auth import require_admin_jwt, require_jwt
from ...services.setup_services import (
    CATALOG,
    post_to_marketplace,
    record_work_order,
    service_for,
)

router = APIRouter(prefix="/api/setup-services", tags=["setup-services"])
logger = logging.getLogger("meridian.api.setup_services")

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _supabase() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    if not url or not key:
        raise HTTPException(503, "Supabase not configured — cannot record a sold service")
    return url, key


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}", "apikey": key, "Content-Type": "application/json"}


class WorkOrderRequest(BaseModel):
    serviceKind: str
    market: str
    businessName: str
    priceCents: int
    brief: dict[str, Any] = {}
    orgId: Optional[str] = None
    leadId: Optional[str] = None
    repId: Optional[str] = None
    repName: Optional[str] = None
    businessType: Optional[str] = None
    contactName: Optional[str] = None
    contactEmail: Optional[str] = None
    serviceLabel: Optional[str] = None

    @field_validator("market")
    @classmethod
    def validate_market(cls, v: str) -> str:
        if v not in ("us", "ca"):
            raise ValueError("market must be 'us' or 'ca'")
        return v

    @field_validator("serviceKind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("serviceKind is required")
        return v[:60]

    @field_validator("businessName")
    @classmethod
    def validate_business(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("businessName is required")
        return v[:200]

    @field_validator("priceCents")
    @classmethod
    def validate_price(cls, v: int) -> int:
        if v < 0:
            raise ValueError("priceCents cannot be negative")
        return v


@router.get("/catalog")
async def catalog(user: dict = Depends(require_jwt)):
    """The adders that have a registered marketplace posting.

    A kind that is NOT here still records and still posts, through the generic
    work-order route — the catalog is where a service gets a *bespoke* posting,
    not where it gets permission to exist.
    """
    return {
        "ok": True,
        "services": [
            {"kind": s.kind, "label": s.label, "fixedPrice": s.fixed_price}
            for s in CATALOG.values()
        ],
    }


@router.post("/order")
async def create_work_order(req: WorkOrderRequest, user: dict = Depends(require_jwt)):
    """Record a sold adder. Called once per toggled service at close.

    Returns 409 when the same service is already live for this org — that is a
    double-submit from the portal, not a second purchase, and the portal should
    treat it as success.
    """
    row = await record_work_order(
        service_kind=req.serviceKind,
        market=req.market,
        business_name=req.businessName,
        price_cents=req.priceCents,
        brief=req.brief,
        org_id=req.orgId,
        lead_id=req.leadId,
        rep_id=req.repId,
        rep_name=req.repName,
        business_type=req.businessType,
        contact_name=req.contactName,
        contact_email=req.contactEmail,
        service_label=req.serviceLabel,
    )
    if not row:
        # record_work_order returns None for both "already live" and a real
        # write failure; the log distinguishes them. A sold service that was
        # not recorded must be visible, so this is a 409 the portal surfaces
        # rather than a silent 200.
        raise HTTPException(
            409,
            "Could not record this service — it may already be live for this "
            "customer. Check the Setup Services console before re-closing.",
        )

    return {
        "ok": True,
        "orderId": row["id"],
        "serviceKind": row["service_kind"],
        "status": row["status"],
        "postsOn": "payment",
    }


@router.get("")
async def list_work_orders(
    repId: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(require_jwt),
):
    """Work orders for a rep, or the 100 most recent."""
    url, key = _supabase()
    query = "select=*&order=created_at.desc&limit=100"
    if repId:
        if not re.match(r"^[A-Za-z0-9_.@-]{1,100}$", repId):
            raise HTTPException(400, "Invalid rep id")
        query += f"&rep_id=eq.{repId}"
    if status:
        if not re.match(r"^[a-z_]{1,30}$", status):
            raise HTTPException(400, "Invalid status")
        query += f"&status=eq.{status}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{url}/rest/v1/setup_service_orders?{query}", headers=_headers(key))

    return {"ok": True, "orders": resp.json() if resp.status_code == 200 else []}


@router.get("/{order_id}")
async def get_work_order(order_id: str, user: dict = Depends(require_jwt)):
    if not _UUID_RE.match(order_id):
        raise HTTPException(400, "Invalid order id")
    url, key = _supabase()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{url}/rest/v1/setup_service_orders?id=eq.{order_id}&select=*", headers=_headers(key)
        )
    rows = resp.json() if resp.status_code == 200 else []
    if not rows:
        raise HTTPException(404, "Work order not found")

    order = rows[0]
    return {
        "ok": True,
        "order": order,
        "posting": service_for(order.get("service_kind", "")).endpoint,
    }


@router.post("/{order_id}/post")
async def post_now(order_id: str, _admin: dict = Depends(require_admin_jwt)):
    """Post a work order to the marketplace right now — the ops override.

    For comped work, an off-Stripe payment, or a posting that failed and needs
    another go. Admin-only because it puts real work in front of developers
    against a deal the payment webhook has not confirmed.
    """
    if not _UUID_RE.match(order_id):
        raise HTTPException(400, "Invalid order id")
    url, key = _supabase()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{url}/rest/v1/setup_service_orders?id=eq.{order_id}&select=*", headers=_headers(key)
        )
    rows = resp.json() if resp.status_code == 200 else []
    if not rows:
        raise HTTPException(404, "Work order not found")

    job_id = await post_to_marketplace(rows[0])
    if not job_id:
        raise HTTPException(502, "Could not post to the marketplace — see the order's status detail")
    return {"ok": True, "orderId": order_id, "foundryJobId": job_id, "status": "posted"}
