"""
Zero-hardware camera ingest — Path A (phone/tablet as camera).

The merchant opens the /cam PWA page on a phone they already own; the browser
captures a JPEG every ~0.7s and POSTs it here. This module is the ONLY new step:
it decodes that JPEG into a numpy frame and feeds it into the EXISTING vision
pipeline — the same MeridianDetector + MeridianPeopleCounter + CameraDataWriter
that the RTSP path uses. No forking of the detector or analytics.

    JPEG bytes ──▶ decode (cv2.imdecode) ──▶ numpy BGR frame
               ──▶ MeridianDetector.process_frame        (YOLO11 + ByteTrack)
               ──▶ MeridianPeopleCounter.process_frame   (zones, lines, dwell, density)
               ──▶ CameraDataWriter                      (vision_traffic / vision_visits)

Per-camera state (detector, counter, writer) is cached in-process keyed by
camera_id so ByteTrack IDs and dwell timers persist across frames from the same
phone. This mirrors how the RTSP CameraPipeline holds one counter per camera.

Auth: a browser can't hold a Supabase service JWT, so each browser camera gets a
short-lived per-camera HMAC token minted at register time. The token binds
camera_id + org_id and is verified here (constant-time). The token hash is stored
on the vision_cameras row; the raw token lives only on the phone.

Compliance: anonymous only. This path never touches the biometric/identity tier —
it produces aggregate counts exactly like the anonymous RTSP path.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger("meridian.camera.frame_ingest")

# A single browser frame at 1080p JPEG is well under 1 MB. Cap generously but
# firmly to reject garbage / abuse before we spend CPU decoding.
MAX_FRAME_BYTES = 3 * 1024 * 1024  # 3 MB

# Token TTL: browser cameras are long-lived (propped in a corner for days), so the
# token is a session credential, not a 60s view token. Rotatable by re-registering.
FRAME_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days


# ─────────────────────────── token mint / verify ───────────────────────────
def _secret() -> str:
    """HMAC signing secret. Reuses VISION_INGEST_TOKEN as the keying material so no
    new secret has to be provisioned; falls back to nothing (fails closed)."""
    return os.environ.get("VISION_FRAME_TOKEN_SECRET") or os.environ.get(
        "VISION_INGEST_TOKEN", ""
    )


def mint_frame_token(camera_id: str, org_id: str, issued_at: int | None = None) -> str:
    """Return a signed opaque token binding camera_id + org_id.

    Format: "<issued_at>.<hexsig>" where hexsig = HMAC-SHA256(secret, camera_id|org_id|issued_at).
    Raises RuntimeError if no secret is configured (fail closed, never mint an
    unsigned credential).
    """
    secret = _secret()
    if not secret:
        raise RuntimeError("VISION_INGEST_TOKEN not configured — cannot mint frame token")
    ts = int(issued_at if issued_at is not None else time.time())
    msg = f"{camera_id}|{org_id}|{ts}".encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def verify_frame_token(token: str, camera_id: str, org_id: str) -> bool:
    """Constant-time verify a frame token for (camera_id, org_id). Returns False on
    any malformed / expired / mismatched token."""
    secret = _secret()
    if not secret or not token or "." not in token:
        return False
    ts_str, _, sig = token.partition(".")
    try:
        ts = int(ts_str)
    except ValueError:
        return False
    if ts <= 0 or (time.time() - ts) > FRAME_TOKEN_TTL_SECONDS:
        return False
    expected = hmac.new(
        secret.encode(), f"{camera_id}|{org_id}|{ts}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(sig, expected)


def token_hash(token: str) -> str:
    """sha256 of the raw token — what we persist on the vision_cameras row."""
    return hashlib.sha256(token.encode()).hexdigest()


# ─────────────────────────── per-camera pipeline cache ───────────────────────────
class _BrowserCameraWorker:
    """Holds the detector + people counter + writer for one browser camera so
    tracker IDs and dwell timers persist across frames. Reuses the exact same
    classes the RTSP pipeline uses — no forked logic."""

    def __init__(self, org_id: str, camera_id: str, model_size: str = "yolo11n.pt") -> None:
        # Imported lazily: ultralytics / supervision are heavy and only needed when
        # a frame actually arrives (keeps API import time + test import time cheap).
        from .detector import MeridianDetector
        from .people_counter import MeridianPeopleCounter
        from .supabase_writer import CameraDataWriter

        self.org_id = org_id
        self.camera_id = camera_id
        self._detector = MeridianDetector(model_size=model_size)
        self._counter = MeridianPeopleCounter(model_path=model_size)
        self._writer = CameraDataWriter(org_id=org_id, camera_id=camera_id)
        self.last_frame_at = time.time()

    def process(self, frame) -> dict[str, Any]:
        """Run one frame through detector + counter + writer. Returns a small
        summary the phone can render (person count, density)."""
        self.last_frame_at = time.time()
        detection_result = self._detector.process_frame(
            frame=frame, merchant_id=self.org_id, camera_id=self.camera_id,
        )
        detections = _to_sv_detections(detection_result)
        count_result = self._counter.process_frame(frame, precomputed_detections=detections)

        # Persist to the same tables the RTSP path writes to.
        self._writer.accumulate(count_result.zone_counts, count_result.total_count)
        if count_result.entries_this_frame or count_result.exits_this_frame:
            self._writer.write_entry_exit(
                count_result.entries_this_frame, count_result.exits_this_frame
            )
        completions = self._counter.flush_dwell(count_result.tracked_ids)
        if completions:
            self._writer.write_dwell_records(completions, self._counter.zone_configs)

        return {
            "persons": detection_result.get("total_detected", 0),
            "density": count_result.density,
        }


def _to_sv_detections(result: dict[str, Any]):
    """Build sv.Detections from the detector's person list (mirrors
    CameraPipeline._build_sv_detections so the people counter can skip a 2nd YOLO pass)."""
    import numpy as np
    import supervision as sv

    persons = result.get("persons", [])
    if not persons:
        return None
    xyxy = np.array([p["bbox"] for p in persons], dtype=np.float32)
    confidence = np.array([p["confidence"] for p in persons], dtype=np.float32)
    tracker_ids = np.array([p["tracker_id"] for p in persons], dtype=int)
    return sv.Detections(xyxy=xyxy, confidence=confidence, tracker_id=tracker_ids)


_workers: dict[str, _BrowserCameraWorker] = {}
_workers_lock = threading.Lock()
# Evict a browser camera worker after this idle gap (phone closed / walked away).
_WORKER_IDLE_TTL = 60 * 10  # 10 minutes


def _get_worker(org_id: str, camera_id: str) -> _BrowserCameraWorker:
    with _workers_lock:
        # opportunistic eviction of stale workers
        now = time.time()
        stale = [k for k, w in _workers.items() if now - w.last_frame_at > _WORKER_IDLE_TTL]
        for k in stale:
            _workers.pop(k, None)

        worker = _workers.get(camera_id)
        if worker is None:
            worker = _BrowserCameraWorker(org_id=org_id, camera_id=camera_id)
            _workers[camera_id] = worker
        return worker


class FrameIngestError(ValueError):
    """Raised for oversize / undecodable / garbage frame payloads."""


def ingest_browser_frame(org_id: str, camera_id: str, jpeg_bytes: bytes) -> dict[str, Any]:
    """Decode a JPEG posted by a browser camera and run it through the existing
    vision pipeline. Returns a small summary for the phone UI.

    Raises FrameIngestError on oversize or undecodable input.
    """
    if not jpeg_bytes:
        raise FrameIngestError("empty frame")
    if len(jpeg_bytes) > MAX_FRAME_BYTES:
        raise FrameIngestError(
            f"frame too large: {len(jpeg_bytes)} bytes (max {MAX_FRAME_BYTES})"
        )

    import cv2
    import numpy as np

    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None or frame.size == 0:
        raise FrameIngestError("could not decode frame as an image")

    worker = _get_worker(org_id, camera_id)
    try:
        return worker.process(frame)
    except Exception as exc:  # detector/counter failure must not 500 the phone loop
        logger.warning("browser frame processing failed for %s: %s", camera_id, exc)
        return {"persons": 0, "density": "unknown", "error": "processing_failed"}
