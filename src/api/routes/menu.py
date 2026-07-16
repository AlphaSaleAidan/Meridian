"""
Menu Store API — review queue, item management, and the public hosted menu.

  GET    /api/menu/{merchant_id}/items          → full managed list (auth)
  GET    /api/menu/{merchant_id}/review         → pending review queue (auth)
  POST   /api/menu/{merchant_id}/confirm        → accept edited items → publish
  PATCH  /api/menu/{merchant_id}/items/{id}     → inline edit / sold-out toggle
  DELETE /api/menu/{merchant_id}/items/{id}     → remove item
  POST   /api/menu/{merchant_id}/publish        → publish public page (slug)
  GET    /api/menu/{merchant_id}/public-info    → slug/URL for the merchant UI
  GET    /api/menu/public/{slug}                → public menu payload (NO auth)

Org auth mirrors phone_dashboard.py (require_service_auth +
enforce_service_member). All mutations flow through src/services/menu_store —
which keeps the phone_agent_config.menu_items JSONB mirror in sync, so the
live agent and every legacy reader update instantly.
"""
from __future__ import annotations

import logging
import os
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import enforce_service_member, require_service_auth
from ...db import get_db
from ...services import menu_store
from .phone_dashboard import _validate_merchant_id

logger = logging.getLogger("meridian.api.menu")

router = APIRouter(prefix="/api/menu", tags=["menu"])

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,59}$")

PUBLIC_MENU_BASE = os.getenv("PUBLIC_SITE_BASE", "https://meridian.tips").rstrip("/")


class MenuItemEdit(BaseModel):
    """Inline edit payload — prices in dollars (converted to cents in the store)."""
    name: str | None = None
    price: float | None = Field(None, ge=0)
    category: str | None = None
    description: str | None = None
    sizes: list[str] | None = None
    size_prices: dict[str, float] | None = None
    topping_price: float | None = Field(None, ge=0)
    modifications: list[str] | None = None
    sold_out: bool | None = None
    position: int | None = None


class MenuItemConfirm(MenuItemEdit):
    id: str


class ConfirmRequest(BaseModel):
    items: list[MenuItemConfirm]


def _item_out(row: dict) -> dict:
    """Store row → UI dict (dollars + review metadata)."""
    return {
        "id": row.get("id"),
        **menu_store.to_agent_shape(row),
        "sold_out": bool(row.get("sold_out")),
        "source": row.get("source"),
        "confidence": row.get("confidence"),
        "needs_review": bool(row.get("needs_review")),
        "published": bool(row.get("published")),
        "position": row.get("position"),
        "updated_at": row.get("updated_at"),
    }


@router.get("/public/{slug}")
async def get_public_menu(slug: str):
    """Public hosted menu (meridian.tips/m/{slug}) — published items grouped
    client-side by category, sold-out flags included. No auth by design;
    404 for unknown or unpublished menus."""
    if not _SLUG_RE.match(slug or ""):
        raise HTTPException(status_code=404, detail="Menu not found")
    payload = await menu_store.get_public_menu(get_db(), slug)
    if payload is None:
        raise HTTPException(status_code=404, detail="Menu not found")
    return payload


@router.get("/{merchant_id}/items")
async def list_menu_items(merchant_id: str, principal=Depends(require_service_auth)):
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    db = get_db()
    # Migrate-on-read-of-the-new-UI: JSONB-only merchants get their blob
    # imported as published manual rows the first time they open the manager.
    try:
        await menu_store.import_jsonb_menu(db, merchant_id)
    except Exception as e:  # noqa: BLE001 — table may not exist yet
        logger.warning("menu import_jsonb failed for %s: %s", merchant_id, e)
    rows = await menu_store.list_items(db, merchant_id)
    return {
        "merchant_id": merchant_id,
        "items": [_item_out(r) for r in rows],
        "pending_review": sum(1 for r in rows if r.get("needs_review")),
    }


@router.get("/{merchant_id}/review")
async def list_review_items(merchant_id: str, principal=Depends(require_service_auth)):
    """The review queue: every ingested item waiting for a human decision."""
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    rows = await menu_store.list_items(get_db(), merchant_id, needs_review=True)
    return {"merchant_id": merchant_id, "items": [_item_out(r) for r in rows]}


@router.post("/{merchant_id}/confirm")
async def confirm_menu_items(merchant_id: str, req: ConfirmRequest,
                             principal=Depends(require_service_auth)):
    """Accept (optionally edited) reviewed items → published + mirrored."""
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    if not req.items:
        raise HTTPException(status_code=400, detail="no items to confirm")
    edits = [i.model_dump(exclude_none=True) for i in req.items]
    published = await menu_store.confirm_items(get_db(), merchant_id, edits)
    return {"ok": True, "published": published}


@router.patch("/{merchant_id}/items/{item_id}")
async def patch_menu_item(merchant_id: str, item_id: str, edit: MenuItemEdit,
                          principal=Depends(require_service_auth)):
    """Inline edit / instant sold-out toggle — propagates to the agent prompt
    and the public page via the store mirror."""
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    result = await menu_store.update_item(
        get_db(), merchant_id, item_id, edit.model_dump(exclude_none=True))
    if not result.get("updated"):
        raise HTTPException(status_code=400, detail="no editable fields provided")
    return {"ok": True}


@router.delete("/{merchant_id}/items/{item_id}")
async def delete_menu_item(merchant_id: str, item_id: str,
                           principal=Depends(require_service_auth)):
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    await menu_store.delete_item(get_db(), merchant_id, item_id)
    return {"ok": True}


@router.post("/{merchant_id}/publish")
async def publish_public_menu(merchant_id: str, principal=Depends(require_service_auth)):
    """Publish the hosted menu page; generates the slug on first publish."""
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    db = get_db()
    config = await db.select(
        "phone_agent_config", filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    display_name = (config[0].get("business_name") if config else "") or ""
    meta = await menu_store.ensure_public_menu(db, merchant_id, display_name)
    slug = meta.get("public_slug") or ""
    return {"ok": True, "slug": slug, "url": f"{PUBLIC_MENU_BASE}/m/{slug}",
            "published": bool(meta.get("published"))}


@router.get("/{merchant_id}/public-info")
async def get_public_menu_info(merchant_id: str, principal=Depends(require_service_auth)):
    """The merchant's own hosted-menu URL (or published:false when none)."""
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    rows = await get_db().select(
        "merchant_menus", filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    if not rows or not rows[0].get("public_slug"):
        return {"published": False, "slug": None, "url": None}
    row = rows[0]
    return {
        "published": bool(row.get("published")),
        "slug": row["public_slug"],
        "url": f"{PUBLIC_MENU_BASE}/m/{row['public_slug']}",
    }
