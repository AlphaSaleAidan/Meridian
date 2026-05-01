"""
Vision Intelligence API Routes.

v1 Endpoints (camera management + basic ingest):
  GET    /api/vision/cameras/{org_id}       → List cameras
  POST   /api/vision/cameras                → Register camera
  PATCH  /api/vision/cameras/{camera_id}    → Update camera config
  DELETE /api/vision/cameras/{camera_id}    → Remove camera
  POST   /api/vision/cameras/{camera_id}/heartbeat → Edge heartbeat
  POST   /api/vision/ingest/traffic         → Ingest traffic metrics
  POST   /api/vision/ingest/visits          → Ingest visit records
  GET    /api/vision/traffic/{org_id}       → Traffic analytics
  GET    /api/vision/agents/{org_id}        → Run vision agents

v2 Endpoints (Palantir-grade analytics):
  POST   /api/vision/ingest                 → Batch ingest from edge pipeline
  GET    /api/vision/foot-traffic/{org_id}  → Passerby, walk-in, conversion
  GET    /api/vision/demographics/{org_id}  → Gender/age over time
  GET    /api/vision/heatmap/{org_id}       → Zone heatmap data
  GET    /api/vision/customers/{org_id}     → Customer profiles
  GET    /api/vision/customers/{org_id}/{profile_id} → Single profile
  GET    /api/vision/insights/{org_id}      → AI-generated insights
  GET    /api/vision/conversion-funnel/{org_id} → Full funnel analytics
  POST   /api/vision/zones/{org_id}         → Configure zone polygons
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


# ══════════════════════════════════════════════════════════════
#  V2 ENDPOINTS — Palantir-Grade Vision Analytics
# ══════════════════════════════════════════════════════════════

class BatchIngestRequest(BaseModel):
    org_id: str
    camera_id: str
    bucket: str
    passerby_count: int = 0
    window_shoppers: int = 0
    walk_ins: int = 0
    walk_outs: int = 0
    male_count: int = 0
    female_count: int = 0
    age_buckets: dict = {}
    returning_count: int = 0
    new_face_count: int = 0
    non_customer_count: int = 0
    sentiment_summary: dict = {}
    visits: list[dict] = []
    zone_metrics: dict = {}


class ZoneConfigRequest(BaseModel):
    zones: dict


@router.post("/ingest")
async def batch_ingest(req: BatchIngestRequest):
    """Receive full batch from edge pipeline — traffic + visits in one call."""
    from ...db import get_db

    db = get_db()
    if not hasattr(db, "client"):
        raise HTTPException(status_code=503, detail="Database not available")

    traffic_row = {
        "org_id": req.org_id,
        "camera_id": req.camera_id,
        "window_start": req.bucket,
        "window_end": req.bucket,
        "passerby_count": req.passerby_count,
        "window_shoppers": req.window_shoppers,
        "walk_ins": req.walk_ins,
        "walk_outs": req.walk_outs,
        "male_count": req.male_count,
        "female_count": req.female_count,
        "age_buckets": req.age_buckets,
        "returning_count": req.returning_count,
        "new_face_count": req.new_face_count,
        "non_customer_count": req.non_customer_count,
        "sentiment_summary": req.sentiment_summary,
    }
    db.client.table("foot_traffic").upsert(
        traffic_row, on_conflict="org_id,camera_id,window_start"
    ).execute()

    visit_count = 0
    for visit in req.visits:
        visitor_hash = visit.get("visitor_hash")
        profile_id = None
        if visitor_hash:
            existing = (
                db.client.table("customer_profiles")
                .select("id, visit_count")
                .eq("org_id", req.org_id)
                .eq("embedding_hash", visitor_hash)
                .limit(1)
                .execute()
            )
            if existing.data:
                profile_id = existing.data[0]["id"]
                db.client.table("customer_profiles").update({
                    "last_seen": datetime.now(timezone.utc).isoformat(),
                    "visit_count": existing.data[0].get("visit_count", 0) + 1,
                }).eq("id", profile_id).execute()
            else:
                new_profile = db.client.table("customer_profiles").insert({
                    "org_id": req.org_id,
                    "embedding_hash": visitor_hash,
                    "first_seen": visit.get("entered_at", datetime.now(timezone.utc).isoformat()),
                    "last_seen": visit.get("entered_at", datetime.now(timezone.utc).isoformat()),
                    "gender": visit.get("demographic", {}).get("gender_est", ""),
                    "age_range": visit.get("demographic", {}).get("age_range", ""),
                }).execute()
                if new_profile.data:
                    profile_id = new_profile.data[0]["id"]

        visit_row = {
            "org_id": req.org_id,
            "profile_id": profile_id,
            "entered_at": visit.get("entered_at"),
            "exited_at": visit.get("exited_at"),
            "dwell_seconds": visit.get("dwell_seconds"),
            "zones_visited": visit.get("zones_visited", []),
            "emotion_entry": visit.get("emotion_entry", ""),
            "emotion_exit": visit.get("emotion_exit", ""),
            "was_window_shopper": visit.get("was_window_shopper", False),
            "converted_later": visit.get("converted_later", False),
        }
        db.client.table("customer_visits").insert(visit_row).execute()
        visit_count += 1

    return {"status": "ok", "traffic_bucket": req.bucket, "visits_ingested": visit_count}


@router.get("/foot-traffic/{org_id}")
async def get_foot_traffic(
    org_id: str,
    days: int = Query(7, ge=1, le=90),
):
    """Passerby, walk-in, and conversion analytics."""
    from ...db import get_db
    from datetime import timedelta

    db = get_db()
    if not hasattr(db, "client"):
        return {"org_id": org_id, "traffic": [], "summary": {}}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    result = (
        db.client.table("foot_traffic")
        .select("*")
        .eq("org_id", org_id)
        .gte("window_start", cutoff)
        .order("window_start", desc=True)
        .limit(2000)
        .execute()
    )
    rows = result.data or []

    total_passersby = sum(r.get("passerby_count", 0) for r in rows)
    total_window = sum(r.get("window_shoppers", 0) for r in rows)
    total_walkins = sum(r.get("walk_ins", 0) for r in rows)
    total_walkouts = sum(r.get("walk_outs", 0) for r in rows)
    total_returning = sum(r.get("returning_count", 0) for r in rows)
    total_new = sum(r.get("new_face_count", 0) for r in rows)
    total_non_cust = sum(r.get("non_customer_count", 0) for r in rows)

    return {
        "org_id": org_id,
        "days": days,
        "traffic": rows[:500],
        "summary": {
            "total_passersby": total_passersby,
            "window_shoppers": total_window,
            "walk_ins": total_walkins,
            "walk_outs": total_walkouts,
            "walk_in_conversion": round(total_walkins / max(total_passersby, 1), 3),
            "returning_visitors": total_returning,
            "new_faces": total_new,
            "non_customers": total_non_cust,
            "buckets": len(rows),
        },
    }


@router.get("/demographics/{org_id}")
async def get_demographics(
    org_id: str,
    days: int = Query(7, ge=1, le=90),
):
    """Gender and age breakdown over time."""
    from ...db import get_db
    from datetime import timedelta
    from collections import defaultdict

    db = get_db()
    if not hasattr(db, "client"):
        return {"org_id": org_id, "demographics": {}}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = (
        db.client.table("foot_traffic")
        .select("window_start,male_count,female_count,age_buckets")
        .eq("org_id", org_id)
        .gte("window_start", cutoff)
        .order("window_start", desc=True)
        .limit(2000)
        .execute()
    )
    rows = result.data or []

    total_male = sum(r.get("male_count", 0) for r in rows)
    total_female = sum(r.get("female_count", 0) for r in rows)
    age_totals: dict[str, int] = defaultdict(int)
    for r in rows:
        for bucket, count in (r.get("age_buckets") or {}).items():
            age_totals[bucket] += count

    daily: dict[str, dict] = defaultdict(lambda: {"male": 0, "female": 0})
    for r in rows:
        ws = r.get("window_start", "")
        try:
            day = datetime.fromisoformat(ws.replace("Z", "+00:00")).strftime("%Y-%m-%d")
            daily[day]["male"] += r.get("male_count", 0)
            daily[day]["female"] += r.get("female_count", 0)
        except (ValueError, AttributeError):
            pass

    total = total_male + total_female
    return {
        "org_id": org_id,
        "days": days,
        "demographics": {
            "gender": {
                "male": total_male,
                "female": total_female,
                "male_pct": round(total_male / max(total, 1) * 100, 1),
                "female_pct": round(total_female / max(total, 1) * 100, 1),
            },
            "age_buckets": dict(age_totals),
            "daily_gender": dict(daily),
        },
    }


@router.get("/heatmap/{org_id}")
async def get_heatmap(
    org_id: str,
    days: int = Query(7, ge=1, le=90),
    camera_id: Optional[str] = Query(None),
):
    """Zone heatmap data — visit counts and dwell by zone."""
    from ...db import get_db
    from datetime import timedelta
    from collections import defaultdict

    db = get_db()
    if not hasattr(db, "client"):
        return {"org_id": org_id, "heatmap": {}}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = (
        db.client.table("customer_visits")
        .select("zones_visited,dwell_seconds")
        .eq("org_id", org_id)
        .gte("entered_at", cutoff)
        .limit(5000)
        .execute()
    )
    rows = result.data or []

    zone_visits: dict[str, int] = defaultdict(int)
    zone_dwell: dict[str, list] = defaultdict(list)
    for r in rows:
        dwell = r.get("dwell_seconds", 0)
        for z in (r.get("zones_visited") or []):
            zone_visits[z] += 1
            if dwell:
                zone_dwell[z].append(dwell)

    zones_result = (
        db.client.table("vision_cameras")
        .select("zone_config")
        .eq("org_id", org_id)
        .limit(10)
        .execute()
    )
    zone_polygons = {}
    for cam in (zones_result.data or []):
        zone_polygons.update(cam.get("zone_config") or {})

    return {
        "org_id": org_id,
        "days": days,
        "heatmap": {
            "zone_visits": dict(zone_visits),
            "zone_avg_dwell": {
                k: round(sum(v) / len(v), 1) for k, v in zone_dwell.items() if v
            },
            "zone_polygons": zone_polygons,
            "total_visits": len(rows),
        },
    }


@router.get("/customers/{org_id}")
async def list_customer_profiles(
    org_id: str,
    sort: str = Query("last_seen", regex="^(last_seen|visit_count|predicted_ltv)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List customer profiles with sorting and pagination."""
    from ...db import get_db

    db = get_db()
    if not hasattr(db, "client"):
        return {"org_id": org_id, "profiles": [], "total": 0}

    count_result = (
        db.client.table("customer_profiles")
        .select("id", count="exact")
        .eq("org_id", org_id)
        .execute()
    )
    total = count_result.count or 0

    result = (
        db.client.table("customer_profiles")
        .select("*")
        .eq("org_id", org_id)
        .order(sort, desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    profiles = []
    for p in (result.data or []):
        profiles.append({
            "id": p["id"],
            "embedding_hash": p.get("embedding_hash", "")[:8],
            "visit_count": p.get("visit_count", 0),
            "first_seen": p.get("first_seen"),
            "last_seen": p.get("last_seen"),
            "avg_dwell_sec": p.get("avg_dwell_sec", 0),
            "favorite_zone": p.get("favorite_zone", ""),
            "visit_pattern": p.get("visit_pattern", ""),
            "gender": p.get("gender", ""),
            "age_range": p.get("age_range", ""),
            "avg_sentiment": p.get("avg_sentiment", ""),
            "total_pos_spend_cents": p.get("total_pos_spend_cents", 0),
            "predicted_ltv": p.get("predicted_ltv", 0),
            "is_opted_in": p.get("is_opted_in", False),
            "tags": p.get("tags", []),
        })

    return {"org_id": org_id, "profiles": profiles, "total": total, "offset": offset}


@router.get("/customers/{org_id}/{profile_id}")
async def get_customer_profile(org_id: str, profile_id: str):
    """Single customer profile with visit history."""
    from ...db import get_db

    db = get_db()
    if not hasattr(db, "client"):
        raise HTTPException(status_code=503, detail="Database not available")

    profile = (
        db.client.table("customer_profiles")
        .select("*")
        .eq("org_id", org_id)
        .eq("id", profile_id)
        .limit(1)
        .execute()
    )
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    p = profile.data[0]

    visits = (
        db.client.table("customer_visits")
        .select("*")
        .eq("profile_id", profile_id)
        .order("entered_at", desc=True)
        .limit(100)
        .execute()
    )

    return {
        "profile": p,
        "visits": visits.data or [],
        "visit_count": p.get("visit_count", 0),
    }


@router.get("/insights/{org_id}")
async def get_vision_insights(
    org_id: str,
    period: str = Query("7d", regex="^(1d|7d|30d|snapshot)$"),
    limit: int = Query(20, ge=1, le=50),
):
    """AI-generated vision insights."""
    from ...db import get_db
    from ...vision.insight_generator import VisionInsightGenerator

    db = get_db()
    if not hasattr(db, "client"):
        return {"org_id": org_id, "insights": []}

    existing = (
        db.client.table("vision_insights")
        .select("*")
        .eq("org_id", org_id)
        .order("generated_at", desc=True)
        .limit(limit)
        .execute()
    )

    if existing.data and len(existing.data) >= 3:
        latest = existing.data[0].get("generated_at", "")
        try:
            latest_dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - latest_dt).total_seconds() / 3600
            if age_hours < 6:
                return {"org_id": org_id, "insights": existing.data, "cached": True}
        except (ValueError, AttributeError):
            pass

    generator = VisionInsightGenerator(org_id)
    insights = await generator.generate(db)

    return {"org_id": org_id, "insights": insights, "cached": False}


@router.get("/conversion-funnel/{org_id}")
async def get_conversion_funnel(
    org_id: str,
    days: int = Query(7, ge=1, le=90),
):
    """Full conversion funnel: passerby → window → walk-in → browse → buy."""
    from ...db import get_db
    from datetime import timedelta

    db = get_db()
    if not hasattr(db, "client"):
        return {"org_id": org_id, "funnel": {}}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    traffic = (
        db.client.table("foot_traffic")
        .select("passerby_count,window_shoppers,walk_ins,non_customer_count")
        .eq("org_id", org_id)
        .gte("window_start", cutoff)
        .execute()
    )
    rows = traffic.data or []

    passersby = sum(r.get("passerby_count", 0) for r in rows)
    window = sum(r.get("window_shoppers", 0) for r in rows)
    walk_ins = sum(r.get("walk_ins", 0) for r in rows)
    non_customers = sum(r.get("non_customer_count", 0) for r in rows)

    visits = (
        db.client.table("customer_visits")
        .select("converted_later,was_window_shopper,pos_transaction_id")
        .eq("org_id", org_id)
        .gte("entered_at", cutoff)
        .execute()
    )
    visit_rows = visits.data or []
    buyers = sum(1 for v in visit_rows if v.get("pos_transaction_id"))
    browsers = walk_ins - buyers

    funnel = [
        {"stage": "Passersby", "count": passersby, "pct": 100.0},
        {"stage": "Window Shoppers", "count": window,
         "pct": round(window / max(passersby, 1) * 100, 1)},
        {"stage": "Walk-ins", "count": walk_ins,
         "pct": round(walk_ins / max(passersby, 1) * 100, 1)},
        {"stage": "Browsers (no purchase)", "count": max(0, browsers),
         "pct": round(max(0, browsers) / max(passersby, 1) * 100, 1)},
        {"stage": "Buyers", "count": buyers,
         "pct": round(buyers / max(passersby, 1) * 100, 1)},
    ]

    drop_offs = []
    for i in range(1, len(funnel)):
        prev = funnel[i - 1]["count"]
        curr = funnel[i]["count"]
        if prev > 0:
            drop_offs.append({
                "from": funnel[i - 1]["stage"],
                "to": funnel[i]["stage"],
                "lost": max(0, prev - curr),
                "drop_pct": round(max(0, prev - curr) / prev * 100, 1),
            })

    return {
        "org_id": org_id,
        "days": days,
        "funnel": funnel,
        "drop_offs": drop_offs,
        "conversion_rate": round(buyers / max(passersby, 1) * 100, 2),
    }


@router.post("/zones/{org_id}")
async def configure_zones(org_id: str, req: ZoneConfigRequest):
    """Update zone polygons for all cameras belonging to an org."""
    from ...db import get_db

    db = get_db()
    if not hasattr(db, "client"):
        raise HTTPException(status_code=503, detail="Database not available")

    cameras = (
        db.client.table("vision_cameras")
        .select("id")
        .eq("org_id", org_id)
        .execute()
    )
    if not cameras.data:
        raise HTTPException(status_code=404, detail="No cameras found for this org")

    updated = 0
    for cam in cameras.data:
        db.client.table("vision_cameras").update({
            "zone_config": req.zones,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", cam["id"]).execute()
        updated += 1

    return {"status": "ok", "cameras_updated": updated, "zones": req.zones}
