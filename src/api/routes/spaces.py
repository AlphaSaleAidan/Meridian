"""
3D Space Management — scan ingestion, model storage, profile linking.

Routes:
  POST /api/spaces/upload       → Upload a LiDAR scan (presigned URL flow)
  GET  /api/spaces/:org_id      → List spaces for an organization
  GET  /api/spaces/:org_id/:id  → Get single space with model URL
  PATCH /api/spaces/:id/status  → Update processing status
  POST /api/spaces/:id/zones    → Store zone mapping data
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("meridian.spaces")

router = APIRouter(prefix="/api/spaces", tags=["spaces"])


class ScanUploadRequest(BaseModel):
    org_id: str
    scan_type: str = "lidar"  # lidar | photogrammetry | polycam
    device_model: Optional[str] = None
    file_format: str = "usdz"  # usdz | glb | obj | ply
    file_size_bytes: Optional[int] = None
    source_url: Optional[str] = None  # for Polycam embed URLs


class ZoneMapping(BaseModel):
    zone_id: str
    label: str
    position: list[float]  # [x, y, z]
    radius: float
    category: str = "general"  # general | counter | entrance | display | shelf


class ZonesRequest(BaseModel):
    zones: list[ZoneMapping]


@router.post("/upload")
async def upload_scan(req: ScanUploadRequest):
    from ...db import _db_instance as db
    if not db:
        return {
            "id": str(uuid.uuid4()),
            "status": "demo",
            "message": "Scan registered (demo mode — no database)",
        }

    space_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    result = db.table("spaces").insert({
        "id": space_id,
        "org_id": req.org_id,
        "scan_type": req.scan_type,
        "device_model": req.device_model,
        "file_format": req.file_format,
        "file_size_bytes": req.file_size_bytes,
        "source_url": req.source_url,
        "status": "uploaded",
        "created_at": now,
        "updated_at": now,
    }).execute()

    return {
        "id": space_id,
        "status": "uploaded",
        "message": "Scan registered. Processing will begin shortly.",
    }


@router.get("/{org_id}")
async def list_spaces(org_id: str):
    from ...db import _db_instance as db
    if not db:
        return {"spaces": _demo_spaces(), "total": 1}

    result = db.table("spaces").select("*").eq("org_id", org_id).order("created_at", desc=True).execute()
    return {"spaces": result.data or [], "total": len(result.data or [])}


@router.get("/{org_id}/{space_id}")
async def get_space(org_id: str, space_id: str):
    from ...db import _db_instance as db
    if not db:
        demos = _demo_spaces()
        return demos[0] if demos else {}

    result = db.table("spaces").select("*, space_zones(*)").eq("id", space_id).eq("org_id", org_id).maybe_single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Space not found")
    return result.data


@router.patch("/{space_id}/status")
async def update_status(space_id: str, status: str):
    from ...db import _db_instance as db
    if not db:
        return {"id": space_id, "status": status}

    valid = {"uploaded", "processing", "ready", "failed"}
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid}")

    now = datetime.now(timezone.utc).isoformat()
    db.table("spaces").update({"status": status, "updated_at": now}).eq("id", space_id).execute()
    return {"id": space_id, "status": status}


@router.post("/{space_id}/zones")
async def store_zones(space_id: str, req: ZonesRequest):
    from ...db import _db_instance as db
    if not db:
        return {"space_id": space_id, "zones_stored": len(req.zones)}

    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "id": str(uuid.uuid4()),
            "space_id": space_id,
            "zone_id": z.zone_id,
            "label": z.label,
            "position_x": z.position[0] if len(z.position) > 0 else 0,
            "position_y": z.position[1] if len(z.position) > 1 else 0,
            "position_z": z.position[2] if len(z.position) > 2 else 0,
            "radius": z.radius,
            "category": z.category,
            "created_at": now,
        }
        for z in req.zones
    ]
    db.table("space_zones").insert(rows).execute()
    return {"space_id": space_id, "zones_stored": len(rows)}


def _demo_spaces():
    return [{
        "id": "demo-space-1",
        "org_id": "demo",
        "scan_type": "polycam",
        "device_model": "iPhone 15 Pro",
        "file_format": "usdz",
        "source_url": "https://poly.cam/capture/D3C8EE9B-7EF3-44F2-A656-7E869018204F",
        "status": "ready",
        "created_at": "2026-05-04T00:00:00Z",
        "zones": [
            {"zone_id": "counter", "label": "POS Counter", "category": "counter"},
            {"zone_id": "entrance", "label": "Entrance Zone", "category": "entrance"},
            {"zone_id": "display", "label": "Feature Display", "category": "display"},
            {"zone_id": "shelf-a", "label": "High-Value Shelf", "category": "shelf"},
        ],
    }]
