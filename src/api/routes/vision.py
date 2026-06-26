"""
Vision Intelligence API Routes.

Endpoints:
  GET    /api/vision/cameras/{org_id}       -> List cameras
  POST   /api/vision/cameras                -> Register camera
  PATCH  /api/vision/cameras/{camera_id}    -> Update camera config
  DELETE /api/vision/cameras/{camera_id}    -> Remove camera
  POST   /api/vision/cameras/{camera_id}/heartbeat -> Edge heartbeat
  POST   /api/vision/ingest/traffic         -> Ingest traffic metrics
  POST   /api/vision/ingest/visits          -> Ingest visit records
  GET    /api/vision/traffic/{org_id}       -> Traffic analytics
  GET    /api/vision/agents/{org_id}        -> Run vision agents
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from ..auth import require_org_access

logger = logging.getLogger("meridian.api.vision")

router = APIRouter(prefix="/api/vision", tags=["vision"], dependencies=[Depends(require_org_access)])


async def require_device_token(x_device_token: Optional[str] = Header(None)):
    """Auth for edge-device ingest endpoints (cameras, not browsers).

    Devices send X-Device-Token matching the VISION_INGEST_TOKEN env var.
    Fails closed with 503 if the token is not configured server-side.
    """
    expected = os.environ.get("VISION_INGEST_TOKEN", "")
    if not expected:
        logger.error("VISION_INGEST_TOKEN not configured — rejecting vision ingest")
        raise HTTPException(status_code=503, detail="Vision ingest not configured")
    if not x_device_token or x_device_token != expected:
        raise HTTPException(status_code=401, detail="Invalid device token")


# Per-camera tracking toggles the edge agent honors. Privacy-sensitive analyses
# (demographics, VIP face-matching, depth) and live-view default OFF.
DEFAULT_CAMERA_FEATURES = {
    "detection": True, "zones": True,
    "demographics": False, "vip": False, "depth": False, "live_view": False,
}


class CameraRegisterRequest(BaseModel):
    org_id: str
    location_id: Optional[str] = None
    name: str
    rtsp_url: str
    zone_config: dict = {}
    compliance_mode: str = "anonymous"
    active_hours: dict = {"start": "07:00", "end": "22:00"}
    edge_device_id: Optional[str] = None
    features: dict = {}


class CameraUpdateRequest(BaseModel):
    name: Optional[str] = None
    zone_config: Optional[dict] = None
    compliance_mode: Optional[str] = None
    active_hours: Optional[dict] = None
    status: Optional[str] = None
    features: Optional[dict] = None


class HeartbeatRequest(BaseModel):
    status: str = "online"
    edge_version: Optional[str] = None
    gpu_temp_c: Optional[float] = None
    fps: Optional[float] = None


class TrafficIngestRequest(BaseModel):
    org_id: str
    camera_id: str
    location_id: Optional[str] = None
    bucket: str
    entries: int = 0
    exits: int = 0
    occupancy_avg: float = 0
    occupancy_peak: int = 0
    queue_length_avg: float = 0
    queue_wait_avg_sec: float = 0
    conversion_rate: float = 0
    demographic_breakdown: dict = {}
    depth_zone_occupancy: Optional[dict] = None
    avg_person_distance: Optional[float] = None


class VisitIngestRequest(BaseModel):
    org_id: str
    camera_id: str
    visitor_hash: Optional[str] = None
    entered_at: str
    exited_at: Optional[str] = None
    dwell_seconds: Optional[int] = None
    zones_visited: list[str] = []
    converted: bool = False
    demographic: dict = {}


def _get_db():
    from ...db import _db_instance as db
    return db


@router.get("/cameras/{org_id}")
async def list_cameras(org_id: str):
    db = _get_db()
    if not db:
        return {"org_id": org_id, "cameras": [], "total": 0}

    try:
        cameras = await db.select("vision_cameras", filters={"org_id": f"eq.{org_id}"}, order="created_at.asc")
        return {"org_id": org_id, "cameras": cameras, "total": len(cameras)}
    except Exception as e:
        logger.warning("vision_cameras query failed: %s", e)
        return {"org_id": org_id, "cameras": [], "total": 0}


@router.post("/cameras")
async def register_camera(req: CameraRegisterRequest):
    if req.compliance_mode not in ("anonymous", "opt_in_identity", "disabled"):
        raise HTTPException(status_code=400, detail="Invalid compliance_mode")

    db = _get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    import json as json_mod
    row = {
        "org_id": req.org_id,
        "location_id": req.location_id,
        "name": req.name,
        "rtsp_url": req.rtsp_url,
        "zone_config": json_mod.dumps(req.zone_config),
        "compliance_mode": req.compliance_mode,
        "active_hours": json_mod.dumps(req.active_hours),
        "edge_device_id": req.edge_device_id,
        "status": "offline",
        "features": json_mod.dumps({**DEFAULT_CAMERA_FEATURES, **(req.features or {})}),
    }
    try:
        result = await db.insert("vision_cameras", row)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to register camera")
        return result[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to register camera: %s", e)
        raise HTTPException(status_code=500, detail="Failed to register camera")


@router.patch("/cameras/{camera_id}")
async def update_camera(camera_id: str, req: CameraUpdateRequest):
    db = _get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    if "compliance_mode" in updates and updates["compliance_mode"] not in (
        "anonymous", "opt_in_identity", "disabled"
    ):
        raise HTTPException(status_code=400, detail="Invalid compliance_mode")

    import json as json_mod
    if "zone_config" in updates:
        updates["zone_config"] = json_mod.dumps(updates["zone_config"])
    if "active_hours" in updates:
        updates["active_hours"] = json_mod.dumps(updates["active_hours"])
    if "features" in updates:
        # Merge over defaults so a partial toggle payload can't drop keys.
        updates["features"] = json_mod.dumps({**DEFAULT_CAMERA_FEATURES, **updates["features"]})

    try:
        result = await db.update("vision_cameras", updates, filters={"id": f"eq.{camera_id}"})
        if not result:
            raise HTTPException(status_code=404, detail="Camera not found")
        return result[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update camera: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update camera")


@router.delete("/cameras/{camera_id}")
async def delete_camera(camera_id: str):
    db = _get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        await db.delete("vision_cameras", filters={"id": f"eq.{camera_id}"})
    except Exception as e:
        logger.warning("Failed to delete camera: %s", e)
    return {"deleted": True, "camera_id": camera_id}


@router.post("/cameras/{camera_id}/heartbeat")
async def camera_heartbeat(camera_id: str, req: HeartbeatRequest):
    db = _get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    now = datetime.now(timezone.utc).isoformat()
    try:
        result = await db.update("vision_cameras", {
            "status": req.status,
            "last_heartbeat": now,
            "updated_at": now,
        }, filters={"id": f"eq.{camera_id}"})
        if not result:
            raise HTTPException(status_code=404, detail="Camera not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Heartbeat update failed: %s", e)
    return {"status": "ok", "camera_id": camera_id}


# ── Live view (Cloudflare Stream WHIP/WHEP, on-demand) ───────────────
# How many seconds a viewer "request" keeps the edge publishing. The browser
# re-pings POST /live while watching; when pings stop, the edge sees the request
# go stale and stops publishing → we pay Cloudflare only while someone watches.
LIVE_REQUEST_TTL_SEC = int(os.getenv("CAMERA_LIVE_TTL_SEC", "30") or 30)


@router.post("/cameras/{camera_id}/live", dependencies=[Depends(require_org_access)])
async def request_live_view(camera_id: str, org_id: str = Query(...)):
    """Viewer asks to watch a camera live. Ensures a Cloudflare Live Input exists,
    marks the stream requested (edge starts publishing on-demand), returns the WHEP
    URL for the browser to play. Re-call every ~15s while watching to keep it alive.

    org_id is required so the router's require_org_access enforces the caller is a
    member of that org; we then confirm the camera belongs to it (the path is
    camera_id, which org_access can't gate on its own)."""
    from ...services import cloudflare_stream as cf
    db = _get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    rows = await db.select("vision_cameras", filters={"id": f"eq.{camera_id}"}, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="Camera not found")
    cam = rows[0]
    if str(cam.get("org_id") or "") != org_id:
        raise HTTPException(status_code=403, detail="Camera does not belong to this org")
    feats = cam.get("features") or {}
    if isinstance(feats, str):
        import json as _j
        try: feats = _j.loads(feats)
        except Exception: feats = {}
    if not feats.get("live_view"):
        raise HTTPException(status_code=403, detail="Live view is turned off for this camera")

    whep = cam.get("live_whep_url")
    whip = cam.get("live_whip_url")
    uid = cam.get("live_input_uid")
    if not (uid and whep and whip):
        created = await cf.create_live_input(f"meridian:{cam.get('name','camera')}", creator=str(cam.get('org_id','')))
        if not created or not created.get("whep_url"):
            raise HTTPException(status_code=503, detail="Live streaming unavailable")
        uid, whip, whep = created["uid"], created["whip_url"], created["whep_url"]

    now = datetime.now(timezone.utc).isoformat()
    await db.update("vision_cameras", {
        "live_input_uid": uid, "live_whip_url": whip, "live_whep_url": whep,
        "live_requested_at": now, "updated_at": now,
    }, filters={"id": f"eq.{camera_id}"})
    return {"camera_id": camera_id, "whep_url": whep, "ttl_sec": LIVE_REQUEST_TTL_SEC}


@router.get("/cameras/{camera_id}/live-state", dependencies=[Depends(require_device_token)])
async def live_state(camera_id: str):
    """Edge polls this: should I be WHIP-publishing this camera right now? True only
    while live_view is on AND a viewer requested within the TTL (on-demand)."""
    db = _get_db()
    if not db:
        return {"publish": False}
    rows = await db.select("vision_cameras", filters={"id": f"eq.{camera_id}"}, limit=1)
    if not rows:
        return {"publish": False}
    cam = rows[0]
    feats = cam.get("features") or {}
    if isinstance(feats, str):
        import json as _j
        try: feats = _j.loads(feats)
        except Exception: feats = {}
    req_at = cam.get("live_requested_at")
    fresh = False
    if req_at:
        try:
            ts = datetime.fromisoformat(str(req_at).replace("Z", "+00:00"))
            fresh = (datetime.now(timezone.utc) - ts).total_seconds() <= LIVE_REQUEST_TTL_SEC
        except Exception:
            fresh = False
    publish = bool(feats.get("live_view") and fresh and cam.get("live_whip_url"))
    return {"publish": publish, "whip_url": cam.get("live_whip_url") if publish else None,
            "rtsp_url": cam.get("rtsp_url") if publish else None}


@router.post("/ingest/traffic", dependencies=[Depends(require_device_token)])
async def ingest_traffic(req: TrafficIngestRequest):
    db = _get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    import json as json_mod
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


@router.post("/ingest/visits", dependencies=[Depends(require_device_token)])
async def ingest_visits(req: VisitIngestRequest):
    db = _get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    import json as json_mod
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


@router.get("/traffic/{org_id}")
async def get_traffic(
    org_id: str,
    days: int = Query(7, ge=1, le=90),
    camera_id: Optional[str] = Query(None),
):
    db = _get_db()
    if not db:
        return {"org_id": org_id, "traffic": [], "summary": {}}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    filters = {"org_id": f"eq.{org_id}", "bucket": f"gte.{cutoff}"}
    if camera_id:
        filters["camera_id"] = f"eq.{camera_id}"

    try:
        rows = await db.select("vision_traffic", filters=filters, order="bucket.desc", limit=1000)
    except Exception as e:
        logger.warning("Traffic query failed: %s", e)
        rows = []

    total_entries = sum(r.get("entries", 0) for r in rows)
    total_exits = sum(r.get("exits", 0) for r in rows)
    avg_occupancy = sum(r.get("occupancy_avg", 0) for r in rows) / max(len(rows), 1)
    avg_queue_wait = sum(r.get("queue_wait_avg_sec", 0) for r in rows) / max(len(rows), 1)
    avg_conversion = sum(r.get("conversion_rate", 0) for r in rows) / max(len(rows), 1)

    return {
        "org_id": org_id,
        "days": days,
        "traffic": rows[:200],
        "summary": {
            "total_entries": total_entries,
            "total_exits": total_exits,
            "avg_occupancy": round(avg_occupancy, 1),
            "avg_queue_wait_sec": round(avg_queue_wait, 1),
            "avg_conversion_rate": round(avg_conversion, 3),
            "buckets_count": len(rows),
        },
    }


@router.get("/agents/{org_id}")
async def run_vision_agents(org_id: str, days: int = Query(7, ge=1, le=90)):
    import asyncio
    from ...ai.agents.foot_traffic import FootTrafficAgent
    from ...ai.agents.dwell_time import DwellTimeAgent
    from ...ai.agents.customer_recognizer import CustomerRecognizerAgent
    from ...ai.agents.demographic_profiler import DemographicProfilerAgent
    from ...ai.agents.queue_monitor import QueueMonitorAgent
    from ...ai.engine import AnalysisContext

    db = _get_db()
    if not db:
        return {"org_id": org_id, "agents": {}, "error": "Database not available"}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    try:
        traffic_data = await db.select("vision_traffic", filters={"org_id": f"eq.{org_id}", "bucket": f"gte.{cutoff}"}, order="bucket.desc", limit=2000)
    except Exception:
        traffic_data = []
    try:
        visits_data = await db.select("vision_visits", filters={"org_id": f"eq.{org_id}", "entered_at": f"gte.{cutoff}"}, order="entered_at.desc", limit=2000)
    except Exception:
        visits_data = []
    try:
        visitors_data = await db.select("vision_visitors", filters={"org_id": f"eq.{org_id}"}, limit=500)
    except Exception:
        visitors_data = []

    ctx = AnalysisContext(
        org_id=org_id,
        analysis_days=days,
        daily_revenue=[],
        hourly_revenue=[],
        product_performance=[],
        transactions=[],
        inventory=[],
    )
    ctx.vision_traffic = traffic_data
    ctx.vision_visits = visits_data
    ctx.vision_visitors = visitors_data

    agents = [
        FootTrafficAgent(ctx),
        DwellTimeAgent(ctx),
        CustomerRecognizerAgent(ctx),
        DemographicProfilerAgent(ctx),
        QueueMonitorAgent(ctx),
    ]

    results = {}
    tier_1 = [a for a in agents if a.tier <= 1]
    tier_2 = [a for a in agents if a.tier == 2]
    tier_3 = [a for a in agents if a.tier >= 3]

    for batch in [tier_1, tier_2, tier_3]:
        if batch:
            batch_results = await asyncio.gather(
                *[a.analyze() for a in batch], return_exceptions=True
            )
            for agent, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error("Vision agent %s failed: %s", agent.name, result)
                    results[agent.name] = {"error": str(result)}
                else:
                    results[agent.name] = result

    return {"org_id": org_id, "agents": results}
