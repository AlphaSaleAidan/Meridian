"""
VisionPipeline — Orchestrates the full edge processing loop.

detect → track → recognize (every 5s) → demographics → zone analytics
→ aggregate metrics → batch upload to POST /api/vision/ingest every 60s.

Runs on merchant edge hardware. Only anonymized metrics are transmitted.
"""
import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

from .detector import PersonDetector
from .tracker import PersonTracker
from .face_engine import FaceEngine, MatchResult
from .zone_analytics import ZoneAnalytics

logger = logging.getLogger("meridian.vision.pipeline")


@dataclass
class PipelineConfig:
    camera_id: str = ""
    org_id: str = ""
    rtsp_url: str = ""
    zone_config: dict = field(default_factory=dict)
    compliance_mode: str = "anonymous"
    active_hours: dict = field(default_factory=lambda: {"start": "07:00", "end": "22:00"})
    detection_confidence: float = 0.4
    recognition_interval_sec: int = 5
    batch_interval_sec: int = 60
    api_url: str = "http://localhost:8000"
    heartbeat_interval_sec: int = 30


@dataclass
class BatchMetrics:
    bucket: str = ""
    entries: int = 0
    exits: int = 0
    occupancy_samples: list[int] = field(default_factory=list)
    queue_lengths: list[int] = field(default_factory=list)
    queue_waits: list[float] = field(default_factory=list)
    demographics: dict = field(default_factory=lambda: defaultdict(int))
    visits: list[dict] = field(default_factory=list)
    face_records: list[dict] = field(default_factory=list)

    @property
    def occupancy_avg(self) -> float:
        if not self.occupancy_samples:
            return 0.0
        return sum(self.occupancy_samples) / len(self.occupancy_samples)

    @property
    def occupancy_peak(self) -> int:
        return max(self.occupancy_samples) if self.occupancy_samples else 0

    @property
    def queue_length_avg(self) -> float:
        if not self.queue_lengths:
            return 0.0
        return sum(self.queue_lengths) / len(self.queue_lengths)

    @property
    def queue_wait_avg_sec(self) -> float:
        if not self.queue_waits:
            return 0.0
        return sum(self.queue_waits) / len(self.queue_waits)


class VisionPipeline:

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.detector = PersonDetector(confidence=config.detection_confidence)
        self.tracker = PersonTracker()
        self.face_engine = FaceEngine(
            enable_demographics=(config.compliance_mode == "opt_in_identity"),
        )
        self.zones = ZoneAnalytics(config.zone_config if config.zone_config else None)

        self._running = False
        self._frame_count = 0
        self._batch = BatchMetrics()
        self._last_batch_time = time.time()
        self._last_heartbeat = time.time()
        self._entry_zone_ids: set[int] = set()
        self._exit_zone_ids: set[int] = set()

    def _is_active_hours(self) -> bool:
        now = datetime.now()
        start = self.config.active_hours.get("start", "07:00")
        end = self.config.active_hours.get("end", "22:00")
        try:
            sh, sm = map(int, start.split(":"))
            eh, em = map(int, end.split(":"))
            current = now.hour * 60 + now.minute
            start_min = sh * 60 + sm
            end_min = eh * 60 + em
            return start_min <= current <= end_min
        except (ValueError, AttributeError):
            return True

    def process_frame(self, frame: np.ndarray) -> dict:
        self._frame_count += 1

        if not self._is_active_hours():
            return {"skipped": True, "reason": "outside_active_hours"}

        detections = self.detector.detect(frame)
        tracks = self.tracker.update(detections, frame)
        crossings = self.zones.update(tracks)
        active_count = len(tracks)

        self._batch.occupancy_samples.append(active_count)

        for crossing in crossings:
            entrance_zones = {"entrance", "entry", "door"}
            if crossing.to_zone.lower() in entrance_zones:
                if crossing.track_id not in self._entry_zone_ids:
                    self._entry_zone_ids.add(crossing.track_id)
                    self._batch.entries += 1
            if crossing.from_zone.lower() in entrance_zones:
                if crossing.track_id not in self._exit_zone_ids:
                    self._exit_zone_ids.add(crossing.track_id)
                    self._batch.exits += 1

        face_records = []
        if self.config.compliance_mode == "opt_in_identity":
            face_records = self.face_engine.process_frame(
                frame, tracks, self.config.compliance_mode
            )
            for fr in face_records:
                demo = {}
                if fr.age_range:
                    demo["age_range"] = fr.age_range
                    self._batch.demographics[fr.age_range] = (
                        self._batch.demographics.get(fr.age_range, 0) + 1
                    )
                if fr.gender:
                    demo["gender_est"] = fr.gender
                self._batch.face_records.append({
                    "embedding_hash": fr.embedding_hash,
                    "match_type": fr.match_type.value,
                    "demographic": demo,
                    "track_id": fr.track_id,
                })

        completed = self.tracker.get_completed_tracks(min_duration_sec=5.0)
        for track in completed:
            journey = self.zones.get_zone_journey(track.track_id)
            dwell_data = {}
            if track.track_id in self.zones._dwells:
                for zname, zdwell in self.zones._dwells[track.track_id].items():
                    dwell_data[zname] = round(zdwell.duration_sec, 1)
            self._batch.visits.append({
                "track_id": track.track_id,
                "entered_at": datetime.fromtimestamp(track.first_seen, tz=timezone.utc).isoformat(),
                "exited_at": datetime.fromtimestamp(track.last_seen, tz=timezone.utc).isoformat(),
                "dwell_seconds": int(track.duration_sec),
                "zones_visited": journey,
                "zone_dwell": dwell_data,
            })

        now = time.time()
        should_flush = now - self._last_batch_time >= self.config.batch_interval_sec

        return {
            "frame": self._frame_count,
            "detections": len(detections),
            "active_tracks": active_count,
            "crossings": len(crossings),
            "face_records": len(face_records),
            "should_flush": should_flush,
        }

    def flush_batch(self) -> dict:
        now = datetime.now(timezone.utc)
        bucket = now.replace(second=0, microsecond=0)
        minute = bucket.minute
        bucket = bucket.replace(minute=minute - (minute % 15))

        zone_metrics = self.zones.to_metrics()

        traffic_payload = {
            "org_id": self.config.org_id,
            "camera_id": self.config.camera_id,
            "bucket": bucket.isoformat(),
            "entries": self._batch.entries,
            "exits": self._batch.exits,
            "occupancy_avg": round(self._batch.occupancy_avg, 1),
            "occupancy_peak": self._batch.occupancy_peak,
            "queue_length_avg": round(self._batch.queue_length_avg, 1),
            "queue_wait_avg_sec": round(self._batch.queue_wait_avg_sec, 1),
            "conversion_rate": 0.0,
            "demographic_breakdown": dict(self._batch.demographics),
        }

        visit_payloads = []
        for visit in self._batch.visits:
            face = next(
                (f for f in self._batch.face_records if f.get("track_id") == visit["track_id"]),
                None,
            )
            visit_payloads.append({
                "org_id": self.config.org_id,
                "camera_id": self.config.camera_id,
                "visitor_hash": face["embedding_hash"] if face else None,
                "entered_at": visit["entered_at"],
                "exited_at": visit["exited_at"],
                "dwell_seconds": visit["dwell_seconds"],
                "zones_visited": visit["zones_visited"],
                "converted": False,
                "demographic": face.get("demographic", {}) if face else {},
            })

        payload = {
            "traffic": traffic_payload,
            "visits": visit_payloads,
            "zone_metrics": zone_metrics,
        }

        self._batch = BatchMetrics()
        self._last_batch_time = time.time()
        self._entry_zone_ids.clear()
        self._exit_zone_ids.clear()

        return payload

    async def upload_batch(self, payload: dict) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                traffic = payload["traffic"]
                resp = await client.post(
                    f"{self.config.api_url}/api/vision/ingest/traffic",
                    json=traffic,
                )
                if resp.status_code != 200:
                    logger.warning("Traffic upload failed: %s", resp.status_code)

                for visit in payload.get("visits", []):
                    resp = await client.post(
                        f"{self.config.api_url}/api/vision/ingest/visits",
                        json=visit,
                    )
                    if resp.status_code != 200:
                        logger.warning("Visit upload failed: %s", resp.status_code)

            return True
        except ImportError:
            logger.error("httpx not installed — run: pip install httpx")
            return False
        except Exception as e:
            logger.error("Batch upload failed: %s", e)
            return False

    async def send_heartbeat(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self.config.api_url}/api/vision/cameras/{self.config.camera_id}/heartbeat",
                    json={"status": "online", "fps": self._frame_count / max(time.time() - self._last_heartbeat, 1)},
                )
                self._last_heartbeat = time.time()
                self._frame_count = 0
                return resp.status_code == 200
        except Exception as e:
            logger.debug("Heartbeat failed: %s", e)
            return False

    async def run_camera(self):
        """Main loop: read RTSP → process → batch upload."""
        try:
            import cv2
        except ImportError:
            logger.error("opencv-python not installed — run: pip install opencv-python-headless")
            return

        cap = cv2.VideoCapture(self.config.rtsp_url)
        if not cap.isOpened():
            logger.error("Cannot open camera: %s", self.config.rtsp_url)
            return

        self._running = True
        logger.info("Pipeline started for camera %s", self.config.camera_id)

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Frame read failed — reconnecting in 5s")
                    await asyncio.sleep(5)
                    cap.release()
                    cap = cv2.VideoCapture(self.config.rtsp_url)
                    continue

                result = self.process_frame(frame)

                if result.get("should_flush"):
                    payload = self.flush_batch()
                    await self.upload_batch(payload)

                now = time.time()
                if now - self._last_heartbeat >= self.config.heartbeat_interval_sec:
                    await self.send_heartbeat()

                await asyncio.sleep(0.033)
        finally:
            cap.release()
            self._running = False
            logger.info("Pipeline stopped for camera %s", self.config.camera_id)

    def stop(self):
        self._running = False

    @property
    def stats(self) -> dict:
        return {
            "camera_id": self.config.camera_id,
            "running": self._running,
            "frames_processed": self._frame_count,
            "total_tracked": self.tracker.total_tracked,
            "face_index_size": self.face_engine.index_size,
            "zone_metrics": self.zones.to_metrics(),
        }
