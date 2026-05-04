"""
Vision Intelligence API Routes.

Endpoints:
  GET    /api/vision/cameras/{org_id}       → List cameras
  POST   /api/vision/cameras                → Register camera
  PATCH  /api/vision/cameras/{camera_id}    → Update camera config
  DELETE /api/vision/cameras/{camera_id}    → Remove camera
  POST   /api/vision/cameras/{camera_id}/heartbeat → Edge heartbeat
  POST   /api/vision/ingest/traffic         → Ingest traffic metrics
  POST   /api/vision/ingest/visits          → Ingest visit records
  GET    /api/vision/traffic/{org_id}       → Traffic analytics
  GET    /api/vision/agents/{org_id}        → Run vision agents
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("meridian.api.vision")

router = APIRouter(prefix="/api/vision", tags=["vision"])


# ── Request Models ───────────────────────────────────────────

class CameraRegisterRequest(BaseModel):
    org_id: str
    location_id: Optional[str] = None
    name: str
    rtsp_url: str
    zone_config: dict = {}
    compliance_mode: str = "anonymous"
    active_hours: dict = {"start": "07:00", "end": "22:00"}
    edge_device_id: Optional[str] = None


class CameraUpdateRequest(BaseModel):
    name: Optional[str] = None
    zone_config: Optional[dict] = None
    compliance_mode: Optional[str] = None
    active_hours: Optional[dict] = None
    status: Optional[str] = None


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
    # Depth metrics (optional — populated when edge runs with ENABLE_DEPTH=1)
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


# ── Camera Management ────────────────────────────────────────

@router.get("/cameras/{org_id}")
async def list_cameras(org_id: str):
    """List all cameras for an org."""
    from ...db import get_db

    db = get_db()
    if not hasattr(db, "client"):
        return {"org_id": org_id, "cameras": [], "total": 0}

    result = (
        db.client.table("vision_cameras")
        .select("*")
        .eq("org_id", org_id)
        .order("created_at", desc=False)
        .execute()
    )
    cameras = result.data or []
    return {"org_id": org_id, "cameras": cameras, "total": len(cameras)}


@router.post("/cameras")
async def register_camera(req: CameraRegisterRequest):
    """Register a new camera."""
    from ...db import get_db

    if req.compliance_mode not in ("anonymous", "opt_in_identity", "disabled"):
        raise HTTPException(status_code=400, detail="Invalid compliance_mode")

    db = get_db()
    if not hasattr(db, "client"):
        raise HTTPException(status_code=503, detail="Database not available")

    row = {
        "org_id": req.org_id,
        "location_id": req.location_id,
        "name": req.name,
        "rtsp_url": req.rtsp_url,
        "zone_config": req.zone_config,
        "compliance_mode": req.compliance_mode,
        "active_hours": req.active_hours,
        "edge_device_id": req.edge_device_id,
        "status": "offline",
    }
    result = db.client.table("vision_cameras").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to register camera")
    return result.data[0]


@router.patch("/cameras/{camera_id}")
async def update_camera(camera_id: str, req: CameraUpdateRequest):
    """Update camera configuration."""
    from ...db import get_db

    db = get_db()
    if not hasattr(db, "client"):
        raise HTTPException(status_code=503, detail="Database not available")

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    if "compliance_mode" in updates and updates["compliance_mode"] not in (
        "anonymous", "opt_in_identity", "disabled"
    ):
        raise HTTPException(status_code=400, detail="Invalid compliance_mode")

    result = (
        db.client.table("vision_cameras")
        .update(updates)
        .eq("id", camera_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Camera not found")
    return result.data[0]


@router.delete("/cameras/{camera_id}")
async def delete_camera(camera_id: str):
    """Remove a camera."""
    from ...db import get_db

    db = get_db()
    if not hasattr(db, "client"):
        raise HTTPException(status_code=503, detail="Database not available")

    result = (
        db.client.table("vision_cameras")
        .delete()
        .eq("id", camera_id)
        .execute()
    )
    return {"deleted": True, "camera_id": camera_id}


@router.post("/cameras/{camera_id}/heartbeat")
async def camera_heartbeat(camera_id: str, req: HeartbeatRequest):
    """Edge device heartbeat — updates camera status and last_heartbeat."""
    from ...db import get_db

    db = get_db()
    if not hasattr(db, "client"):
        raise HTTPException(status_code=503, detail="Database not available")

    result = (
        db.client.table("vision_cameras")
        .update({
            "status": req.status,
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", camera_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Camera not found")
    return {"status": "ok", "camera_id": camera_id}


# ── Data Ingestion (from edge devices) ───────────────────────

@router.post("/ingest/traffic")
async def ingest_traffic(req: TrafficIngestRequest):
    """Ingest aggregated traffic metrics from edge device."""
    from ...db import get_db

    db = get_db()
    if not hasattr(db, "client"):
        raise HTTPException(status_code=503, detail="Database not available")

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
        "demographic_breakdown": req.demographic_breakdown,
    }
    if req.depth_zone_occupancy is not None:
        row["depth_zone_occupancy"] = req.depth_zone_occupancy
    if req.avg_person_distance is not None:
        row["avg_person_distance"] = req.avg_person_distance
    result = (
        db.client.table("vision_traffic")
        .upsert(row, on_conflict="org_id,camera_id,bucket")
        .execute()
    )
    return {"status": "ok", "bucket": req.bucket}


@router.post("/ingest/visits")
async def ingest_visits(req: VisitIngestRequest):
    """Ingest individual visit records from edge device."""
    from ...db import get_db

    db = get_db()
    if not hasattr(db, "client"):
        raise HTTPException(status_code=503, detail="Database not available")

    visitor_id = None
    if req.visitor_hash:
        existing = (
            db.client.table("vision_visitors")
            .select("id")
            .eq("org_id", req.org_id)
            .eq("embedding_hash", req.visitor_hash)
            .limit(1)
            .execute()
        )
        if existing.data:
            visitor_id = existing.data[0]["id"]
            db.client.table("vision_visitors").update({
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "visit_count": existing.data[0].get("visit_count", 0) + 1,
            }).eq("id", visitor_id).execute()
        else:
            new_visitor = db.client.table("vision_visitors").insert({
                "org_id": req.org_id,
                "embedding_hash": req.visitor_hash,
                "first_seen": req.entered_at,
                "last_seen": req.entered_at,
                "demographic": req.demographic,
            }).execute()
            if new_visitor.data:
                visitor_id = new_visitor.data[0]["id"]

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
    result = db.client.table("vision_visits").insert(visit_row).execute()
    return {"status": "ok", "visit_id": result.data[0]["id"] if result.data else None}


# ── Traffic Analytics ────────────────────────────────────────

@router.get("/traffic/{org_id}")
async def get_traffic(
    org_id: str,
    days: int = Query(7, ge=1, le=90),
    camera_id: Optional[str] = Query(None),
):
    """Get traffic analytics for an org."""
    from ...db import get_db
    from datetime import timedelta

    db = get_db()
    if not hasattr(db, "client"):
        return {"org_id": org_id, "traffic": [], "summary": {}}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    query = (
        db.client.table("vision_traffic")
        .select("*")
        .eq("org_id", org_id)
        .gte("bucket", cutoff)
        .order("bucket", desc=True)
    )
    if camera_id:
        query = query.eq("camera_id", camera_id)

    result = query.limit(1000).execute()
    rows = result.data or []

    total_entries = sum(r.get("entries", 0) for r in rows)
    total_exits = sum(r.get("exits", 0) for r in rows)
    avg_occupancy = (
        sum(r.get("occupancy_avg", 0) for r in rows) / max(len(rows), 1)
    )
    avg_queue_wait = (
        sum(r.get("queue_wait_avg_sec", 0) for r in rows) / max(len(rows), 1)
    )
    avg_conversion = (
        sum(r.get("conversion_rate", 0) for r in rows) / max(len(rows), 1)
    )

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


# ── Vision Agent Execution ───────────────────────────────────

@router.get("/agents/{org_id}")
async def run_vision_agents(org_id: str, days: int = Query(7, ge=1, le=90)):
    """Run all 5 vision agents and return results."""
    import asyncio
    from ...db import get_db
    from ...ai.agents.foot_traffic import FootTrafficAgent
    from ...ai.agents.dwell_time import DwellTimeAgent
    from ...ai.agents.customer_recognizer import CustomerRecognizerAgent
    from ...ai.agents.demographic_profiler import DemographicProfilerAgent
    from ...ai.agents.queue_monitor import QueueMonitorAgent
    from ...ai.engine import AnalysisContext

    db = get_db()
    if not hasattr(db, "client"):
        return {"org_id": org_id, "agents": {}, "error": "Database not available"}

    cutoff = (
        datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)
    ).isoformat()

    traffic_result = (
        db.client.table("vision_traffic")
        .select("*")
        .eq("org_id", org_id)
        .gte("bucket", cutoff)
        .order("bucket", desc=True)
        .limit(2000)
        .execute()
    )
    visits_result = (
        db.client.table("vision_visits")
        .select("*")
        .eq("org_id", org_id)
        .gte("entered_at", cutoff)
        .order("entered_at", desc=True)
        .limit(2000)
        .execute()
    )
    visitors_result = (
        db.client.table("vision_visitors")
        .select("*")
        .eq("org_id", org_id)
        .limit(500)
        .execute()
    )

    ctx = AnalysisContext(
        org_id=org_id,
        analysis_days=days,
        daily_revenue=[],
        hourly_revenue=[],
        product_performance=[],
        transactions=[],
        inventory=[],
    )
    ctx.vision_traffic = traffic_result.data or []
    ctx.vision_visits = visits_result.data or []
    ctx.vision_visitors = visitors_result.data or []

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
                    logger.error(f"Vision agent {agent.name} failed: {result}")
                    results[agent.name] = {"error": str(result)}
                else:
                    results[agent.name] = result

    return {"org_id": org_id, "agents": results}
