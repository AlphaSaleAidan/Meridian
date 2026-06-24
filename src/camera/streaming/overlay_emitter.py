"""Overlay emitter (Phase 6) — bridges the EXISTING swarm outputs to the live overlay
feed. No new analytics: it reshapes detector output + cross_reference_insights + anomalies
into the OverlayFrame the portal renders, and broadcasts it on the Supabase realtime
channel `overlays:<camera_id>`. ponytail: pure transforms + one thin httpx broadcast,
flagged off by default so it never changes pipeline behavior.
"""
from __future__ import annotations

import logging
import os
import time

import httpx

logger = logging.getLogger("meridian.camera.overlay")

OVERLAY_FEED_ENABLED = os.environ.get("OVERLAY_FEED_ENABLED", "0") == "1"


def _now_ms() -> int:
    return int(time.time() * 1000)


def boxes_from_detection(detection_result: dict) -> list[dict]:
    """persons[].bbox (px) -> normalized boxes (resolution-independent) for the overlay."""
    h, w = (detection_result.get("frame_shape") or [1, 1])[:2]
    w = w or 1
    h = h or 1
    out = []
    for p in detection_result.get("persons", []):
        x1, y1, x2, y2 = p.get("bbox", [0, 0, 0, 0])
        out.append({
            "id": p.get("tracker_id"),
            "x": round(x1 / w, 4), "y": round(y1 / h, 4),
            "w": round((x2 - x1) / w, 4), "h": round((y2 - y1) / h, 4),
            "conf": p.get("confidence"),
        })
    return out


def insight_to_xref(insight: dict) -> dict | None:
    """A cross_reference_insights row -> a POS x-ref overlay tag (basket/items/checked-out).
    Only emits when the insight carries person+basket linkage in its `data` payload."""
    data = insight.get("data") or {}
    if "tracker_id" not in data and "person_id" not in data:
        return None
    return {
        "id": data.get("tracker_id"),
        "x": float(data.get("x", 0.5)), "y": float(data.get("y", 0.5)),
        "basketCents": data.get("basket_cents"),
        "items": data.get("item_count"),
        "checkedOut": bool(data.get("checked_out", False)),
    }


def build_overlay_frame(
    detection_result: dict,
    *,
    xref: list[dict] | None = None,
    exceptions: list[dict] | None = None,
) -> dict:
    """Assemble one OverlayFrame from existing outputs (frontend OverlayFrame shape)."""
    return {
        "frame_ts": _now_ms(),
        "boxes": boxes_from_detection(detection_result),
        "xref": xref or [],
        "exceptions": exceptions or [],
    }


def broadcast_overlay(camera_id: str, frame: dict) -> None:
    """Push the frame to the Supabase realtime channel the portal subscribes to.
    No-op when disabled or unconfigured (fails safe — never breaks the pipeline)."""
    if not OVERLAY_FEED_ENABLED:
        return
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return
    try:
        httpx.post(
            f"{url}/realtime/v1/api/broadcast",
            headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"messages": [{"topic": f"overlays:{camera_id}", "event": "frame", "payload": frame}]},
            timeout=2.0,
        )
    except Exception as e:  # noqa: BLE001 - overlay feed must never break capture
        logger.debug("overlay broadcast failed (cam=%s): %s", camera_id, e)


def clip_evidence_url(api_base: str, camera_id: str, ts_from: str, ts_to: str, org_id: str) -> str:
    """'View evidence' link: a flagged transaction's time window -> the /clip endpoint."""
    return (f"{api_base.rstrip('/')}/api/cameras/{camera_id}/clip"
            f"?from={ts_from}&to={ts_to}&org_id={org_id}")
