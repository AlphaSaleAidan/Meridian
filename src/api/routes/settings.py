"""
Merchant settings routes.

The Settings page's Notifications tab has called GET/PUT
/api/settings/notifications since it shipped, but no backend route existed —
every load 404'd silently and preferences only lived in localStorage (so they
were lost across devices/browsers). Preferences persist in the
notification_prefs table (migration 024) — keyed by org id with NO parent-table
FK, because Canada merchants live in `businesses` while US-era orgs live in
`organizations` (entity-model split): a route bound to either table misses the
other, which is exactly how the first cut of this route 404'd for every Canada
merchant.
"""
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..auth import require_jwt, require_org_member
from ...db import get_db

logger = logging.getLogger("meridian.settings.routes")

router = APIRouter(prefix="/api/settings", tags=["settings"])

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


async def _load_prefs(db, org_id: str) -> dict:
    rows = await db.select(
        "notification_prefs", "prefs", filters={"org_id": f"eq.{org_id}"}, limit=1,
    )
    return _known_prefs(rows[0].get("prefs")) if rows else {}


@router.get("/notifications")
async def get_notification_prefs(org_id: str, user: dict = Depends(require_jwt)):
    await require_org_member(user, org_id)
    return await _load_prefs(get_db(), org_id)


@router.put("/notifications")
async def put_notification_prefs(
    req: NotificationPrefs, user: dict = Depends(require_jwt)
):
    await require_org_member(user, req.org_id)
    db = get_db()
    current = await _load_prefs(db, req.org_id)
    updates = {
        k: v for k, v in req.model_dump(exclude={"org_id"}).items() if v is not None
    }
    merged = {**current, **updates}
    await db.upsert(
        "notification_prefs",
        {"org_id": req.org_id, "prefs": merged},
        on_conflict="org_id",
    )
    return merged
