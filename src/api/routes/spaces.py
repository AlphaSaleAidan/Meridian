"""
3D Space Management — scan ingestion, model storage, profile linking.

Routes:
  POST /api/spaces/upload       → Upload a LiDAR scan (presigned URL flow)
  GET  /api/spaces/:org_id      → List spaces for an organization
  GET  /api/spaces/:org_id/:id  → Get single space with model URL
  PATCH /api/spaces/:id/status  → Update processing status
  POST /api/spaces/:id/zones    → Store zone mapping data
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..auth import enforce_service_member, require_org_access, require_service_auth

logger = logging.getLogger("meridian.spaces")

router = APIRouter(prefix="/api/spaces", tags=["spaces"], dependencies=[Depends(require_org_access)])


async def _authorize_space_access(principal: dict, space_id: str) -> None:
    """BOLA guard for routes keyed only by space_id (status/zones/model).

    require_org_access is a no-op here — these routes carry no org_id in
    query/path/body (live-probed 2026-07-15: POST /{id}/zones returned 200
    UNAUTHENTICATED). So: authenticate via require_service_auth at the route,
    then load the space row and require the caller's org to match its org_id.
    The org comes from the AUTHENTICATED session (enforce_service_member),
    never from the request. Machine principals (admin key / service token)
    are org-agnostic, mirroring phone_dashboard.py.
    """
    if principal.get("kind") in ("admin", "service"):
        return
    from ...db import _db_instance as db
    if not db:
        return  # demo mode — no tenant rows exist to protect
    try:
        rows = await db.select("spaces", "*", filters={"id": f"eq.{space_id}"}, limit=1)
    except Exception as e:
        # Fail CLOSED for session users — an authz lookup error must not
        # grant cross-tenant access.
        logger.warning("Space authz lookup failed for %s: %s", space_id, e)
        raise HTTPException(status_code=503, detail="Space authorization unavailable")
    if not rows:
        raise HTTPException(status_code=404, detail="Space not found")
    await enforce_service_member(principal, rows[0].get("org_id") or "")


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

    try:
        await db.insert("spaces", {
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
        })
    except Exception as e:
        logger.warning("Spaces insert failed (table may not exist): %s", e)
        return {"id": space_id, "status": "demo", "message": "Scan registered (demo mode)"}

    return {
        "id": space_id,
        "status": "uploaded",
        "message": "Scan registered. Processing will begin shortly.",
    }


@router.post("/process")
async def process_video(
    video: UploadFile = File(...),
    merchant_id: str = Form(...),
    scan_name: str = Form(""),
):
    """Upload a walkthrough video for 3D reconstruction."""
    from ...db import _db_instance as db

    space_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    frames_dir = Path("data/spaces") / space_id
    frames_dir.mkdir(parents=True, exist_ok=True)

    video_path = frames_dir / f"source{Path(video.filename or '.mp4').suffix}"
    content = await video.read()
    video_path.write_bytes(content)

    record = {
        "id": space_id,
        "org_id": merchant_id,
        "name": scan_name or "Untitled Scan",
        "scan_type": "video",
        "device_model": None,
        "file_format": "mp4",
        "file_size_bytes": len(content),
        "status": "processing",
        "created_at": now,
        "updated_at": now,
    }

    if db:
        try:
            await db.insert("spaces", record)
        except Exception as e:
            logger.warning("Spaces insert failed: %s", e)

    return {"spaceId": space_id, "jobId": job_id, "status": "processing"}


@router.post("/process-frames")
async def process_frames(
    merchant_id: str = Form(...),
    scan_name: str = Form(""),
    metadata: str = Form("{}"),
    frames: list[UploadFile] = File(...),
):
    """Upload captured frames (from live camera or AR scan) for 3D reconstruction."""
    from ...db import _db_instance as db

    space_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    try:
        meta = json.loads(metadata)
    except json.JSONDecodeError:
        meta = {}

    frames_dir = Path("data/spaces") / space_id / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    for i, frame_file in enumerate(frames):
        frame_path = frames_dir / f"frame_{i:04d}.jpg"
        content = await frame_file.read()
        frame_path.write_bytes(content)
        saved_count += 1

    scan_type = "live-capture"
    if meta.get("tier") == "lidar":
        scan_type = "lidar-ar"
    if meta.get("xrSessionUsed"):
        scan_type = "lidar-xr"

    record = {
        "id": space_id,
        "org_id": merchant_id,
        "name": scan_name or "Untitled Scan",
        "scan_type": scan_type,
        "device_model": meta.get("deviceModel"),
        "frame_count": saved_count,
        "status": "processing",
        "created_at": now,
        "updated_at": now,
    }

    if db:
        try:
            await db.insert("spaces", record)
        except Exception as e:
            logger.warning("Spaces insert failed: %s", e)

    (Path("data/spaces") / space_id / "metadata.json").write_text(
        json.dumps(meta, indent=2)
    )

    logger.info(
        "Frames uploaded: space=%s frames=%d type=%s device=%s",
        space_id, saved_count, scan_type, meta.get("deviceModel"),
    )

    return {
        "spaceId": space_id,
        "jobId": job_id,
        "framesReceived": saved_count,
        "scanType": scan_type,
        "status": "processing",
    }


@router.post("/upload-splat")
async def upload_splat(
    splat: UploadFile = File(...),
    merchant_id: str = Form(...),
    scan_name: str = Form(""),
):
    """Upload a pre-processed .splat or .ply file for direct 3D viewing."""
    from ...db import _db_instance as db

    space_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    space_dir = Path("data/spaces") / space_id
    space_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(splat.filename or "model.splat").suffix or ".splat"
    model_path = space_dir / f"model{ext}"
    content = await splat.read()
    model_path.write_bytes(content)

    splat_count = len(content) // 32 if ext == ".splat" else None

    record = {
        "id": space_id,
        "org_id": merchant_id,
        "name": scan_name or "Untitled Scan",
        "scan_type": "gaussian-splat",
        "file_format": ext.lstrip("."),
        "file_size_bytes": len(content),
        "frame_count": splat_count,
        "splat_url": f"/api/spaces/{space_id}/model",
        "status": "ready",
        "model_used": "gaussian-splat",
        "created_at": now,
        "updated_at": now,
        "completed_at": now,
    }

    if db:
        try:
            await db.insert("spaces", record)
        except Exception as e:
            logger.warning("Spaces insert failed: %s", e)

    logger.info("Splat uploaded: space=%s size=%d ext=%s", space_id, len(content), ext)

    return {
        "spaceId": space_id,
        "splatUrl": f"/api/spaces/{space_id}/model",
        "splatCount": splat_count,
        "status": "ready",
    }


@router.get("/{space_id}/model")
async def get_space_model(space_id: str, principal=Depends(require_service_auth)):
    """Serve the .splat/.ply model file for a space (org-scoped)."""
    from fastapi.responses import FileResponse

    await _authorize_space_access(principal, space_id)

    space_dir = Path("data/spaces") / space_id
    for ext in [".splat", ".ply", ".spz"]:
        model_path = space_dir / f"model{ext}"
        if model_path.exists():
            media_type = {
                ".splat": "application/octet-stream",
                ".ply": "application/octet-stream",
                ".spz": "application/octet-stream",
            }.get(ext, "application/octet-stream")
            return FileResponse(
                model_path,
                media_type=media_type,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "public, max-age=3600",
                },
            )

    raise HTTPException(status_code=404, detail="Model file not found")


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get processing job status. Simulates progress for now."""
    return {
        "id": job_id,
        "status": "processing",
        "progress_pct": 50,
        "frame_count": None,
        "error_message": None,
    }


@router.get("/{org_id}")
async def list_spaces(org_id: str):
    from ...db import _db_instance as db
    if not db:
        # No DB configured — honestly report no spaces, never fabricate one.
        return {"spaces": [], "total": 0}

    try:
        rows = await db.select("spaces", "*", filters={"org_id": f"eq.{org_id}"}, order="created_at.desc")
        return {"spaces": rows, "total": len(rows)}
    except Exception as e:
        # Surface the failure instead of handing a real merchant fabricated data.
        logger.warning("Spaces query failed for %s: %s", org_id, e)
        raise HTTPException(status_code=503, detail="Spaces are temporarily unavailable")


@router.get("/{org_id}/{space_id}")
async def get_space(org_id: str, space_id: str):
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(status_code=404, detail="Space not found")

    try:
        rows = await db.select("spaces", "*", filters={"id": f"eq.{space_id}", "org_id": f"eq.{org_id}"}, limit=1)
        if not rows:
            raise HTTPException(status_code=404, detail="Space not found")
        return rows[0]
    except HTTPException:
        raise
    except Exception as e:
        # Surface the failure instead of returning a fabricated space.
        logger.warning("Space query failed for %s/%s: %s", org_id, space_id, e)
        raise HTTPException(status_code=503, detail="Spaces are temporarily unavailable")


@router.patch("/{space_id}/status")
async def update_status(space_id: str, status: str, principal=Depends(require_service_auth)):
    await _authorize_space_access(principal, space_id)
    from ...db import _db_instance as db
    if not db:
        return {"id": space_id, "status": status}

    valid = {"uploaded", "processing", "ready", "failed"}
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid}")

    now = datetime.now(timezone.utc).isoformat()
    try:
        await db.update("spaces", {"status": status, "updated_at": now}, filters={"id": f"eq.{space_id}"})
    except Exception as e:
        logger.warning("Spaces update failed: %s", e)
    return {"id": space_id, "status": status}


@router.post("/{space_id}/zones")
async def store_zones(space_id: str, req: ZonesRequest, principal=Depends(require_service_auth)):
    await _authorize_space_access(principal, space_id)
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
    try:
        for row in rows:
            await db.insert("space_zones", row)
    except Exception as e:
        logger.warning("Zone insert failed: %s", e)
    return {"space_id": space_id, "zones_stored": len(rows)}


