"""
Browser camera frame ingest — Path A of zero-hardware camera connect.

This router is SEPARATE from the main vision router on purpose: the vision router
is gated by require_org_access (a valid Supabase JWT), but a phone running the /cam
PWA page has no JWT. Instead each browser camera holds a short-lived per-camera HMAC
frame token (minted by POST /api/vision/camera/register-browser). This endpoint
verifies that token and feeds the JPEG into the SAME detector/analytics pipeline the
RTSP path uses.

    POST /api/vision/camera/frame   (multipart form)
      camera_id: str
      org_id:    str
      token:     str   (per-camera HMAC frame token)
      frame:     file  (JPEG)

Compliance: anonymous only — the frame ingest produces aggregate counts, never
biometric/identity data. Plan gating is unchanged (browser cameras appear in the
same vision console as RTSP cameras, subject to the same plan).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ...camera.frame_ingest import (
    MAX_FRAME_BYTES,
    FrameIngestError,
    ingest_browser_frame,
    verify_frame_token,
)

logger = logging.getLogger("meridian.api.browser_camera")

# No router-level JWT dependency: browser cameras authenticate with a frame token.
router = APIRouter(prefix="/api/vision/camera", tags=["vision", "browser-camera"])


@router.post("/frame")
async def ingest_frame(
    camera_id: str = Form(...),
    org_id: str = Form(...),
    token: str = Form(...),
    frame: UploadFile = File(...),
):
    """Accept one JPEG from a browser camera, verify its per-camera token, and run
    it through the existing vision pipeline. Returns the live person count so the
    phone can show 'N people detected'."""
    if not verify_frame_token(token, camera_id, org_id):
        raise HTTPException(status_code=401, detail="Invalid or expired frame token")

    # Content-type guard (defense in depth; the real check is the decode below).
    ctype = (frame.content_type or "").lower()
    if ctype and not ctype.startswith("image/"):
        raise HTTPException(status_code=415, detail="frame must be an image")

    # Read with a hard cap so a huge upload can't exhaust memory before the size check.
    data = await frame.read(MAX_FRAME_BYTES + 1)
    if len(data) > MAX_FRAME_BYTES:
        raise HTTPException(status_code=413, detail="frame too large")

    try:
        summary = ingest_browser_frame(org_id=org_id, camera_id=camera_id, jpeg_bytes=data)
    except FrameIngestError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {"status": "ok", "camera_id": camera_id, **summary}
