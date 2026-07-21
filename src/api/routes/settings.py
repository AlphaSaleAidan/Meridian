"""
Merchant settings routes.

The Settings page's Notifications tab has called GET/PUT
/api/settings/notifications since it shipped, but no backend route existed —
every load 404'd silently and preferences only lived in localStorage (so they
were lost across devices/browsers). Preferences persist in
organizations.metadata.notification_prefs (existing jsonb column — no
migration), merged so other metadata keys are never clobbered.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_jwt, require_org_member
from ...db import get_db

logger = logging.getLogger("meridian.settings.routes")

router = APIRouter(prefix="/api/settings", tags=["settings"])

_METADATA_KEY = "notification_prefs"

# Keep in lockstep with NOTIF_DEFAULTS in frontend/src/pages/SettingsPage.tsx.
_PREF_KEYS = ("deal_stage", "daily_revenue", "ai_anomaly", "low_stock", "new_customer")


class NotificationPrefs(BaseModel):
    org_id: str
    deal_stage: bool | None = None
    daily_revenue: bool | None = None
    ai_anomaly: bool | None = None
    low_stock: bool | None = None
    new_customer: bool | None = None


def _known_prefs(raw) -> dict:
    """Only the boolean pref keys — the frontend spreads the response into its
    state, so stray keys (or the org_id) must never come back."""
    if not isinstance(raw, dict):
        return {}
    return {k: bool(raw[k]) for k in _PREF_KEYS if isinstance(raw.get(k), bool)}


async def _load_metadata(db, org_id: str) -> dict:
    rows = await db.select(
        "organizations", "metadata", filters={"id": f"eq.{org_id}"}, limit=1,
    )
    if not rows:
        raise HTTPException(404, "Organization not found")
    return rows[0].get("metadata") or {}


@router.get("/notifications")
async def get_notification_prefs(org_id: str, user: dict = Depends(require_jwt)):
    await require_org_member(user, org_id)
    db = get_db()
    metadata = await _load_metadata(db, org_id)
    return _known_prefs(metadata.get(_METADATA_KEY))


@router.put("/notifications")
async def put_notification_prefs(
    req: NotificationPrefs, user: dict = Depends(require_jwt)
):
    await require_org_member(user, req.org_id)
    db = get_db()
    metadata = await _load_metadata(db, req.org_id)

    current = _known_prefs(metadata.get(_METADATA_KEY))
    updates = {
        k: v for k, v in req.model_dump(exclude={"org_id"}).items() if v is not None
    }
    merged = {**current, **updates}

    # Merge under our one key — never clobber sibling metadata (stripe
    # checkout et al. store their own keys here).
    await db.update(
        "organizations",
        {"metadata": {**metadata, _METADATA_KEY: merged}},
        filters={"id": f"eq.{req.org_id}"},
    )
    return merged
