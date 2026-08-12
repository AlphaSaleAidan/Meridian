"""
Meridian v1.5 — integrations hub catalog.

  GET /api/integrations/catalog?org_id=  → full catalog with per-org state

One endpoint drives the whole hub page: every integration Meridian offers
(dedicated Square/Clover/Toast flows, generic 1-click OAuth registry providers,
and partner-gated entries), each with tier, configured/connected flags and the
authorize path to hit for 1-click connect.

Exposes the same information surface as the existing per-provider /status
endpoints (connected flag keyed on a caller-supplied org_id) — no tokens or
credentials ever leave this endpoint. Request-access demand goes through the
existing public POST /api/pos/waitlist.
"""
import logging
import re

from fastapi import APIRouter

from ...pos_connect.catalog import CATEGORY_LABELS, build_catalog

logger = logging.getLogger("meridian.api.integrations")

router = APIRouter(prefix="/api/integrations", tags=["integrations-hub"])

_ORG_ID_RE = re.compile(
    r'^(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    r'|biz_[0-9a-f]{16,40})$', re.I,
)


async def _connected_map(org_id: str | None) -> dict[str, str]:
    """provider → connection status for this org, from pos_connections.
    Any lookup problem degrades to 'nothing connected' — the catalog itself
    must always render."""
    if not org_id or not _ORG_ID_RE.match(org_id):
        return {}
    from ...db import _db_instance
    from ...db.org_ids import connection_org_id
    if not _db_instance:
        return {}
    org_uuid = connection_org_id(org_id) or org_id
    try:
        rows = await _db_instance.select(
            "pos_connections",
            filters={"org_id": f"eq.{org_uuid}"},
        )
    except Exception as e:
        logger.warning("integrations catalog: connection lookup failed for %s: %s",
                       org_id, e)
        return {}
    return {r["provider"]: r.get("status", "") for r in rows or [] if r.get("provider")}


@router.get("/catalog")
async def catalog(org_id: str | None = None):
    """The full integrations catalog, org-aware when org_id is supplied."""
    connected = await _connected_map(org_id)
    items = build_catalog(connected)
    return {
        "categories": [
            {"key": k, "label": v} for k, v in CATEGORY_LABELS.items()
        ],
        "integrations": items,
        "connected_count": sum(1 for i in items if i["connected"]),
    }
