#!/usr/bin/env python3
"""meridian local agent — ONE-CLICK, LOCAL camera processing (no cloud media gateway).

Runs on a PC/POS the merchant already has. Pipeline, end to end, on their box:

    go2rtc (ONVIF discovery, camera creds stay local)
      → GET /api/frame.jpeg?src=<cam>           (a JPEG snapshot, on the LAN)
      → MeridianDetector + MeridianPeopleCounter (YOLO11 + ByteTrack, zones/lines/dwell)
      → 5-min buckets
      → POST /api/vision/ingest/{traffic,visits} with X-Device-Token (per-org)

This is the piece that makes the one-click path ACTUALLY produce metrics: the old
connector only registered + heartbeated and relied on a server-side stream
processor that isn't deployed, so no metrics ever landed. Here the merchant's own
machine does the vision and pushes only anonymous counts.

Why pull frames from go2rtc instead of the camera directly? go2rtc handles every
ONVIF/RTSP dialect, discovery, and credentials — we just grab a JPEG from its
local API. Camera passwords never touch our code or the cloud.

Auth: pairing code → per-org device token (see /api/connector/pair). Anonymous
counts only. Outbound HTTPS only — no inbound ports, no router changes.

Env:
  MERIDIAN_API           https://api.meridian.tips
  MERIDIAN_PAIRING_CODE  from the portal "Connect cameras" wizard
  GO2RTC_API             http://127.0.0.1:1984   (local discovery/frames)
  FRAME_INTERVAL_SEC     0.3   (~3 fps snapshot polling)
  BUCKET_SEC             300   (5-min metric buckets)
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s local-agent %(levelname)s %(message)s")
log = logging.getLogger("local-agent")

API = os.environ.get("MERIDIAN_API", "https://api.meridian.tips").rstrip("/")
PAIRING_CODE = os.environ.get("MERIDIAN_PAIRING_CODE", "")
GO2RTC = os.environ.get("GO2RTC_API", "http://127.0.0.1:1984").rstrip("/")
FRAME_INTERVAL_SEC = float(os.environ.get("FRAME_INTERVAL_SEC", "0.3"))
BUCKET_SEC = int(os.environ.get("BUCKET_SEC", "300"))
HEARTBEAT_SEC = int(os.environ.get("HEARTBEAT_SEC", "30"))


# ─────────────────────────── cloud ingest client ───────────────────────────
class IngestClient:
    """Thin HTTP client for the device-authed vision API (per-org X-Device-Token)."""

    def __init__(self, api: str, token: str, org_id: str):
        self.api = api.rstrip("/")
        self.org_id = org_id
        self._http = httpx.Client(
            base_url=self.api, headers={"X-Device-Token": token}, timeout=20
        )

    def post_traffic(self, metrics: dict) -> bool:
        try:
            r = self._http.post("/api/vision/ingest/traffic", json=metrics)
            if r.status_code != 200:
                log.warning("ingest/traffic -> %s %s", r.status_code, r.text[:160])
            return r.status_code == 200
        except Exception as e:  # noqa: BLE001 - never crash the capture loop
            log.warning("ingest/traffic failed: %s", e)
            return False

    def post_visit(self, visit: dict) -> bool:
        try:
            r = self._http.post("/api/vision/ingest/visits", json=visit)
            return r.status_code == 200
        except Exception as e:  # noqa: BLE001
            log.warning("ingest/visits failed: %s", e)
            return False

    def heartbeat(self, camera_id: str) -> None:
        try:
            self._http.post(f"/api/vision/cameras/{camera_id}/heartbeat", json={"status": "online"})
        except Exception as e:  # noqa: BLE001
            log.debug("heartbeat %s failed: %s", camera_id, e)

    def register(self, site_id: str, name: str) -> Optional[str]:
        try:
            r = self._http.post(
                f"/api/sites/{site_id}/cameras", json={"org_id": self.org_id, "name": name}
            )
            if r.status_code == 200:
                return (r.json().get("camera") or {}).get("id")
            log.warning("register %s -> %s %s", name, r.status_code, r.text[:160])
        except Exception as e:  # noqa: BLE001
            log.warning("register %s failed: %s", name, e)
        return None


def pair(api: str, code: str, http: Optional[httpx.Client] = None) -> dict:
    """Exchange the wizard pairing code for a per-org device token + site/org. Retries."""
    client = http or httpx.Client(timeout=15)
    while True:
        try:
            r = client.post(f"{api}/api/connector/pair", json={"code": code})
            if r.status_code == 200:
                data = r.json()
                log.info("paired: org=%s site=%s", data.get("org_id"), data.get("site_id"))
                return data
            log.warning("pair -> %s %s", r.status_code, r.text[:160])
        except Exception as e:  # noqa: BLE001
            log.warning("pairing failed (%s), retrying in 10s", e)
        time.sleep(10)


# ─────────────────────────── metric bucketing ───────────────────────────
@dataclass
class TrafficBucket:
    """Accumulates per-frame counts into one 5-min ingest row."""

    bucket_sec: int = 300
    _start: float = field(default_factory=lambda: 0.0)
    occ: list[int] = field(default_factory=list)
    queue: list[int] = field(default_factory=list)
    entries: int = 0
    exits: int = 0

    def add(self, occupancy: int, entries: int, exits: int, queue: int, now: float) -> None:
        if self._start == 0.0:
            self._start = now
        self.occ.append(occupancy)
        self.entries += entries
        self.exits += exits
        if queue:
            self.queue.append(queue)

    def due(self, now: float) -> bool:
        return self._start != 0.0 and (now - self._start) >= self.bucket_sec

    def flush(self, org_id: str, camera_id: str, now: float) -> Optional[dict]:
        if not self.occ and not self.entries and not self.exits:
            self._reset(now)
            return None
        dt = datetime.fromtimestamp(self._start or now, tz=timezone.utc)
        floored_min = (dt.minute // (self.bucket_sec // 60 or 1)) * (self.bucket_sec // 60 or 1)
        bucket_iso = dt.replace(minute=floored_min % 60, second=0, microsecond=0).isoformat()
        q = self.queue
        metrics = {
            "org_id": org_id,
            "camera_id": camera_id,
            "bucket": bucket_iso,
            "entries": self.entries,
            "exits": self.exits,
            "occupancy_avg": round(sum(self.occ) / len(self.occ), 1) if self.occ else 0,
            "occupancy_peak": max(self.occ) if self.occ else 0,
            "queue_length_avg": round(sum(q) / len(q), 1) if q else 0,
            "queue_wait_avg_sec": round((sum(q) / len(q)) * 30, 1) if q else 0,
            "conversion_rate": 0,
            "demographic_breakdown": {},
        }
        self._reset(now)
        return metrics

    def _reset(self, now: float) -> None:
        self._start = now
        self.occ, self.queue, self.entries, self.exits = [], [], 0, 0


# ─────────────────────────── per-camera worker ───────────────────────────
class CameraWorker:
    """Pulls frames for ONE camera and runs them through the real vision pipeline.

    frame_source(name) -> JPEG bytes | None  (defaults to go2rtc's snapshot API).
    The detector/counter are created lazily (heavy imports) but injectable for tests.
    """

    def __init__(
        self,
        camera_id: str,
        org_id: str,
        name: str,
        ingest: IngestClient,
        frame_source: Callable[[str], Optional[bytes]],
        zone_config: Optional[dict] = None,
        bucket_sec: int = 300,
        _detector=None,
        _counter=None,
    ):
        self.camera_id = camera_id
        self.org_id = org_id
        self.name = name
        self.ingest = ingest
        self.frame_source = frame_source
        self.bucket = TrafficBucket(bucket_sec=bucket_sec)
        self._detector = _detector
        self._counter = _counter
        self._zone_config = zone_config or {}
        self._checkout_zone_ids: list[str] = []

    def _ensure_pipeline(self):
        if self._detector is not None and self._counter is not None:
            return
        from src.camera.detector import MeridianDetector
        from src.camera.people_counter import MeridianPeopleCounter
        from src.camera.zone_loader import load_zones_for_camera, load_entry_lines

        cfg = {"zone_config": self._zone_config}
        zones = load_zones_for_camera(cfg, 1280, 720, "restaurant")
        lines = load_entry_lines(cfg, 1280, 720)
        self._checkout_zone_ids = [
            z["zone_id"] for z in zones if z.get("type") in ("checkout", "queue")
        ]
        self._detector = MeridianDetector()
        self._counter = MeridianPeopleCounter(zones=zones, entry_lines=lines)

    def tick(self, now: Optional[float] = None) -> Optional[dict]:
        """Grab one frame, update counts, and flush a bucket if it's due.
        Returns the posted metrics dict when a bucket flushed, else None."""
        now = now if now is not None else time.time()
        jpeg = self.frame_source(self.name)
        if jpeg:
            self._process_jpeg(jpeg, now)
        if self.bucket.due(now):
            metrics = self.bucket.flush(self.org_id, self.camera_id, now)
            if metrics:
                self.ingest.post_traffic(metrics)
                return metrics
        return None

    def _process_jpeg(self, jpeg: bytes, now: float) -> None:
        import cv2
        import numpy as np

        self._ensure_pipeline()
        arr = np.frombuffer(jpeg, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None or frame.size == 0:
            return
        det = self._detector.process_frame(
            frame=frame, merchant_id=self.org_id, camera_id=self.camera_id
        )
        detections = _to_sv(det)
        cr = self._counter.process_frame(frame, precomputed_detections=detections)

        queue = sum(cr.zone_counts.get(z, 0) for z in self._checkout_zone_ids)
        self.bucket.add(cr.total_count, cr.entries_this_frame, cr.exits_this_frame, queue, now)

        # Completed dwell records → anonymous visit rows.
        for comp in self._counter.flush_dwell(cr.tracked_ids):
            self.ingest.post_visit({
                "org_id": self.org_id,
                "camera_id": self.camera_id,
                "entered_at": datetime.now(timezone.utc).isoformat(),
                "dwell_seconds": int(comp["dwell_seconds"]),
                "zones_visited": [comp["zone_id"]],
                "converted": False,
            })


def _to_sv(result: dict):
    """Build sv.Detections from the detector's person list (skip a 2nd YOLO pass)."""
    import numpy as np
    import supervision as sv

    persons = result.get("persons", [])
    if not persons:
        return None
    xyxy = np.array([p["bbox"] for p in persons], dtype=np.float32)
    conf = np.array([p["confidence"] for p in persons], dtype=np.float32)
    ids = np.array([p["tracker_id"] for p in persons], dtype=int)
    return sv.Detections(xyxy=xyxy, confidence=conf, tracker_id=ids)


# ─────────────────────────── go2rtc frame source ───────────────────────────
def go2rtc_frame_source(go2rtc_api: str) -> Callable[[str], Optional[bytes]]:
    """Return a frame_source that pulls a JPEG snapshot for a stream from go2rtc."""
    client = httpx.Client(timeout=10)

    def _src(name: str) -> Optional[bytes]:
        try:
            r = client.get(f"{go2rtc_api}/api/frame.jpeg", params={"src": name})
            return r.content if r.status_code == 200 and r.content else None
        except Exception as e:  # noqa: BLE001
            log.debug("frame fetch %s failed: %s", name, e)
            return None

    return _src


def discover_streams(go2rtc_api: str) -> list[str]:
    """List stream names go2rtc discovered (ONVIF) or has configured."""
    try:
        r = httpx.get(f"{go2rtc_api}/api/streams", timeout=10)
        if r.status_code == 200:
            return list((r.json() or {}).keys())
    except Exception as e:  # noqa: BLE001
        log.warning("go2rtc discovery failed: %s", e)
    return []


# ─────────────────────────── main loop ───────────────────────────
def main() -> int:
    if not PAIRING_CODE:
        log.error("MERIDIAN_PAIRING_CODE not set")
        return 2
    paired = pair(API, PAIRING_CODE)
    token, org_id, site_id = paired["device_token"], paired["org_id"], paired["site_id"]
    ingest = IngestClient(API, token, org_id)
    frame_source = go2rtc_frame_source(GO2RTC)

    workers: dict[str, CameraWorker] = {}
    last_hb = 0.0
    log.info("local agent up — discovering cameras via go2rtc at %s", GO2RTC)
    while True:
        for name in discover_streams(GO2RTC):
            if name not in workers:
                cam_id = ingest.register(site_id, name)
                if cam_id:
                    workers[name] = CameraWorker(
                        cam_id, org_id, name, ingest, frame_source, bucket_sec=BUCKET_SEC
                    )
                    log.info("processing camera %s -> %s", name, cam_id)
        for w in workers.values():
            try:
                w.tick()
            except Exception as e:  # noqa: BLE001 - one camera must not kill the loop
                log.warning("tick %s failed: %s", w.name, e)
        now = time.time()
        if now - last_hb >= HEARTBEAT_SEC:
            for w in workers.values():
                ingest.heartbeat(w.camera_id)
            last_hb = now
        time.sleep(FRAME_INTERVAL_SEC)


if __name__ == "__main__":
    raise SystemExit(main())
