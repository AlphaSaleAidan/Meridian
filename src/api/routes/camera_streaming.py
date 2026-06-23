"""Camera streaming endpoints (Phase 3).

  POST /api/sites/{site_id}/cameras        connector registers a discovered camera
  POST /api/cameras/{camera_id}/live-token short-lived (<=60s) single-camera view token
  GET  /api/cameras/{camera_id}/clip       resolve recorded window -> signed playback URL
  GET  /api/overlays/{camera_id}/feed      tenant-scoped overlay subscription descriptor

All tenant-scoped: a camera/site not owned by the caller's org resolves to 404 (never
leak existence). Writes go through the service-role DB client; the gateway/token logic
is reused from Phase 2.
"""
from __future__ import annotations

import logging
import os
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from ..auth import require_org_access, require_service_auth
from ...db import get_db
from ...camera.streaming import get_gateway
from ...camera.streaming.tokens import mint_stream_token

logger = logging.getLogger("meridian.api.camera_streaming")
router = APIRouter(prefix="/api", tags=["camera-streaming"])

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)

# Overlay layers that require the analytics entitlement (gated server-side, not just client).
_GATED_LAYERS = {"identity", "pos_xref", "exceptions"}
_BASE_LAYERS = {"detections", "pose", "journey", "zones", "heatmap"}
_PREMIUM_PLANS = {"premium", "command"}


def _uuid(v: str, label: str):
    if not _UUID_RE.match(v or ""):
        raise HTTPException(400, f"Invalid {label}")


async def require_device_token(x_device_token: str | None = Header(None)):
    """Connector auth (mirrors vision ingest). Fails closed if unset."""
    expected = os.environ.get("VISION_INGEST_TOKEN", "")
    if not expected or x_device_token != expected:
        raise HTTPException(401, "Invalid device token")


async def _camera_in_org(db, camera_id: str, org_id: str) -> dict:
    """Return the camera row iff it belongs to org_id, else 404 (no existence leak)."""
    rows = await db.select(
        "vision_cameras",
        filters={"id": f"eq.{camera_id}", "org_id": f"eq.{org_id}"},
    )
    if not rows:
        raise HTTPException(404, "Camera not found")
    return rows[0]


# ─────────────────────────── models ───────────────────────────
class CameraRegister(BaseModel):
    org_id: str
    name: str
    rtsp_url: str | None = None        # advanced fallback only; happy path is ONVIF
    edge_device_id: str | None = None
    compliance_mode: str = "anonymous"


# ─────────────────────────── endpoints ────────────────────────
@router.post("/sites/{site_id}/cameras", dependencies=[Depends(require_device_token)])
async def register_camera(site_id: str, body: CameraRegister):
    """Connector registers a discovered camera under a site (device-token auth)."""
    _uuid(site_id, "site_id")
    db = get_db()
    # site must belong to the claimed org
    sites = await db.select("camera_sites", filters={"id": f"eq.{site_id}", "org_id": f"eq.{body.org_id}"})
    if not sites:
        raise HTTPException(404, "Site not found")
    cam = {
        "id": str(uuid4()),
        "org_id": body.org_id,
        "site_id": site_id,
        "name": body.name,
        "rtsp_url": body.rtsp_url or "",      # blank on the ONVIF happy path
        "compliance_mode": body.compliance_mode,
        "status": "offline",
    }
    rows = await db.insert("vision_cameras", cam)
    saved = rows[0] if rows else cam
    gw = get_gateway()
    return {
        "camera": saved,
        "publish_url": gw.publish_url(saved["id"]),   # where the connector pushes video
    }


@router.post("/cameras/{camera_id}/live-token", dependencies=[Depends(require_org_access)])
async def live_token(camera_id: str, org_id: str = Query(...)):
    """Mint a <=60s single-camera view token + return the player URLs."""
    _uuid(camera_id, "camera_id")
    db = get_db()
    await _camera_in_org(db, camera_id, org_id)
    try:
        token = mint_stream_token(camera_id, ttl_seconds=60)
    except RuntimeError:
        raise HTTPException(503, "Streaming not configured")
    gw = get_gateway()
    # audit record (store a hash, never the raw token)
    import hashlib
    await db.insert("stream_tokens", {
        "id": str(uuid4()), "org_id": org_id, "camera_id": camera_id,
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "expires_at": "now() + interval '60 seconds'",
    })
    return {
        "token": token, "expires_in": 60,
        "whep_url": gw.viewer_whep_url(camera_id),
        "hls_url": gw.viewer_hls_url(camera_id),
    }


@router.get("/cameras/{camera_id}/clip")
async def clip(
    camera_id: str,
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    org_id: str = Query(...),
    _auth=Depends(require_service_auth),
):
    """Resolve a recorded time window to a signed playback URL. Called by the POS
    cross-reference flow with a transaction's timestamp window. Service-auth +
    explicit org scoping (cross-tenant -> 404)."""
    _uuid(camera_id, "camera_id")
    db = get_db()
    await _camera_in_org(db, camera_id, org_id)
    gw = get_gateway()
    # MediaMTX playback addon serves recorded segments by time window.
    base = gw.viewer_hls_url(camera_id).rsplit("/", 1)[0]
    return {
        "camera_id": camera_id,
        "from": from_, "to": to,
        "playback_url": f"{base}/get?start={from_}&end={to}",
        "note": "requires gateway recording enabled (Phase 2 deploy)",
    }


@router.get("/overlays/{camera_id}/feed", dependencies=[Depends(require_org_access)])
async def overlay_feed(camera_id: str, org_id: str = Query(...)):
    """Return the Supabase-realtime subscription descriptor for this camera's overlay
    payloads + the layers this org is entitled to (gated server-side)."""
    _uuid(camera_id, "camera_id")
    db = get_db()
    await _camera_in_org(db, camera_id, org_id)
    # entitlement: advanced layers only for premium/command plans
    biz = await db.select("businesses", filters={"id": f"eq.{org_id}"})
    plan = (biz[0].get("plan") if biz else "") or ""
    allowed = set(_BASE_LAYERS)
    if plan.lower() in _PREMIUM_PLANS:
        allowed |= _GATED_LAYERS
    return {
        "camera_id": camera_id,
        # client subscribes to this Supabase realtime channel (RLS-scoped by its JWT)
        "channel": f"overlays:{camera_id}",
        "table": "cross_reference_insights",
        "filter": f"org_id=eq.{org_id}",
        "allowed_layers": sorted(allowed),
        "gated_layers": sorted(_GATED_LAYERS - allowed),
    }
