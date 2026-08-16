"""Vision metric ingest — DEVICE-authenticated (no user JWT).

Split out of routes/vision.py on purpose. The main vision router is gated at the
router level by require_org_access (a valid Supabase JWT), which is correct for
the browser/dashboard endpoints but WRONG for metric ingest: the caller is a
headless on-site device (edge_agent.py on a PC/POS, or the LAN connector), which
has no user login. Because the ingest body carries org_id, require_org_access
resolved it and demanded a JWT — so device ingest was returning 401 and NO
camera metrics could ever land. (Reproduced against main before this split.)

This router has NO router-level JWT dependency. It authenticates purely with a
per-org device token (``X-Device-Token``, see camera/device_tokens.py) and
enforces that the token's org matches the org in the body. Endpoints:

    POST /api/vision/ingest/traffic   5/15-min bucketed traffic + queue metrics
    POST /api/vision/ingest/visits    one row per completed visit (dwell + zones)

Compliance is unchanged: anonymous-only unless CAMERA_IDENTITY_ENABLED is set
(demographics + repeat-visitor biometrics are stripped otherwise).
"""
from __future__ import annotations

import json as json_mod
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from ...camera.device_tokens import enforce_org_match, resolve_device_token
from pydantic import BaseModel

from .vision import (
    TrafficIngestRequest,
    VisitIngestRequest,
    camera_identity_enabled,
)

logger = logging.getLogger("meridian.api.vision_ingest")

# No router-level require_org_access: device tokens are the credential here.
router = APIRouter(prefix="/api/vision", tags=["vision", "ingest"])


def _get_db():
    from ...db import _db_instance as db
    return db


async def require_device_principal(x_device_token: Optional[str] = Header(None)) -> dict:
    """Resolve the X-Device-Token to a principal ({org_id, site_id, ...}) or 401.

    Fails closed with 503 (not 401) when no token mechanism is configured at all,
    so a misconfigured server is distinguishable from a bad client token."""
    import os

    principal = await resolve_device_token(_get_db(), x_device_token)
    if principal is not None:
        return principal
    if not (os.environ.get("VISION_INGEST_TOKEN") or _get_db()):
        raise HTTPException(status_code=503, detail="Vision ingest not configured")
    raise HTTPException(status_code=401, detail="Invalid device token")


@router.get("/device/cameras")
async def device_list_cameras(principal: dict = Depends(require_device_principal)):
    """Device-authed camera list for an on-site agent to self-configure (no user JWT).

    The dashboard endpoint GET /api/vision/cameras/{org} requires a Supabase JWT,
    which a headless agent can't hold. A per-org device token resolves to its org
    here and returns that org's cameras (rtsp_url + zone_config). A legacy/global
    token (org_id=None) can't scope a list, so it must use a local config file."""
    org_id = principal.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=400,
            detail="This token is not org-scoped; provide cameras via a local config file.",
        )
    db = _get_db()
    if not db:
        return {"org_id": org_id, "cameras": [], "total": 0}
    try:
        cameras = await db.select(
            "vision_cameras", filters={"org_id": f"eq.{org_id}"}, order="created_at.asc"
        )
    except Exception as e:
        logger.warning("device camera list failed: %s", e)
        cameras = []
    return {"org_id": org_id, "cameras": cameras, "total": len(cameras)}


@router.post("/ingest/traffic")
async def ingest_traffic(
    req: TrafficIngestRequest,
    principal: dict = Depends(require_device_principal),
):
    enforce_org_match(principal, req.org_id)

    db = _get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    # Anonymous-only: drop demographic estimates unless the identity tier is live.
    if not camera_identity_enabled():
        req.demographic_breakdown = {}

    row = {
        "org_id": req.org_id,
        "camera_id": req.camera_id,
        "location_id": req.location_id,
        "bucket": req.bucket,
        "entries": req.entries,
        "exits": req.exits,
        "occupancy_avg": req.occupancy_avg,
        "occupancy_peak": req.occupancy_peak,
        "queue_length_avg": req.queue_length_avg,
        "queue_wait_avg_sec": req.queue_wait_avg_sec,
        "conversion_rate": req.conversion_rate,
        "demographic_breakdown": json_mod.dumps(req.demographic_breakdown),
    }
    if req.depth_zone_occupancy is not None:
        row["depth_zone_occupancy"] = json_mod.dumps(req.depth_zone_occupancy)
    if req.avg_person_distance is not None:
        row["avg_person_distance"] = req.avg_person_distance

    try:
        await db.upsert("vision_traffic", row, on_conflict="org_id,camera_id,bucket")
    except Exception as e:
        logger.warning("Traffic ingest failed: %s", e)
    return {"status": "ok", "bucket": req.bucket}


@router.post("/ingest/visits")
async def ingest_visits(
    req: VisitIngestRequest,
    principal: dict = Depends(require_device_principal),
):
    enforce_org_match(principal, req.org_id)

    db = _get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    # Anonymous-only: no repeat-visitor face matching or demographics unless the
    # identity tier is live. Strip the biometric identifier + demographics.
    if not camera_identity_enabled():
        req.visitor_hash = None
        req.demographic = {}

    visitor_id = None
    if req.visitor_hash:
        try:
            existing = await db.select("vision_visitors", "id,visit_count", filters={
                "org_id": f"eq.{req.org_id}",
                "embedding_hash": f"eq.{req.visitor_hash}",
            }, limit=1)
            if existing:
                visitor_id = existing[0]["id"]
                await db.update("vision_visitors", {
                    "last_seen": datetime.now(timezone.utc).isoformat(),
                    "visit_count": existing[0].get("visit_count", 0) + 1,
                }, filters={"id": f"eq.{visitor_id}"})
            else:
                new_rows = await db.insert("vision_visitors", {
                    "org_id": req.org_id,
                    "embedding_hash": req.visitor_hash,
                    "first_seen": req.entered_at,
                    "last_seen": req.entered_at,
                    "demographic": json_mod.dumps(req.demographic),
                })
                if new_rows:
                    visitor_id = new_rows[0]["id"]
        except Exception as e:
            logger.warning("Visitor lookup/insert failed: %s", e)

    visit_row = {
        "org_id": req.org_id,
        "camera_id": req.camera_id,
        "visitor_id": visitor_id,
        "entered_at": req.entered_at,
        "exited_at": req.exited_at,
        "dwell_seconds": req.dwell_seconds,
        "zones_visited": req.zones_visited,
        "converted": req.converted,
    }
    try:
        result = await db.insert("vision_visits", visit_row)
        return {"status": "ok", "visit_id": result[0]["id"] if result else None}
    except Exception as e:
        logger.warning("Visit insert failed: %s", e)
        return {"status": "ok", "visit_id": None}


class EventIngestRequest(BaseModel):
    """A batch of detections from one camera.

    Batched because the edge agent runs its detectors on a loop and a spill,
    a blocked aisle and a phone at the till can all fall out of the same pass.
    One request per event would triple the round trips for no benefit.
    """
    org_id: str
    camera_id: str
    location_id: Optional[str] = None
    events: list[dict] = []


@router.post("/ingest/events")
async def ingest_events(
    req: EventIngestRequest,
    principal: dict = Depends(require_device_principal),
):
    """Record what the cameras SAW, as opposed to how many people walked past.

    Nothing here identifies a person and nothing here can: the row has no
    column for it. That holds even when the identity tier is enabled, unlike
    the traffic and visit paths above — "someone at the till" is enough to go
    and look, and it is the version of this a merchant can run without first
    taking advice about monitoring staff.

    Malformed events are DROPPED, not rejected. The device is on a loop with
    no operator; failing the batch because one detector emitted a bad
    confidence would lose the spill that came with it.
    """
    from ...services.vision_events import normalise

    enforce_org_match(principal, req.org_id)

    db = _get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    accepted, dropped = 0, 0
    for payload in (req.events or [])[:100]:
        row = normalise(payload if isinstance(payload, dict) else {})
        if row is None:
            dropped += 1
            continue
        row.update({
            "org_id": req.org_id,
            "camera_id": req.camera_id,
            "location_id": req.location_id,
        })
        try:
            # Upsert on the dedupe key: a detector re-firing across frames in
            # the same window updates one row instead of flooding the feed.
            await db.upsert("vision_events", row, on_conflict="org_id,dedupe_key")
            accepted += 1
        except Exception as e:
            logger.warning("Vision event insert failed for %s: %s", req.org_id, e)
            dropped += 1

    if accepted:
        logger.info("Recorded %d vision events for %s", accepted, req.org_id)
    return {"status": "ok", "accepted": accepted, "dropped": dropped}
