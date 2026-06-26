"""
Meridian Vision Edge Agent.

Runs on merchant hardware (Jetson Nano/Orin). Processes RTSP camera feeds
through YOLO → ByteTrack → optional DeepFace, then pushes anonymized
metrics to Meridian cloud API.

No images or video frames are ever stored or transmitted.
Face embeddings stay on-prem and auto-delete after 90 days.
"""
import asyncio
import hashlib
import json
import logging
import os
import signal
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import cv2
import httpx
import numpy as np
from ultralytics import YOLO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-5s | %(message)s",
)
logger = logging.getLogger("meridian.edge")

API_URL = os.environ.get("MERIDIAN_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("MERIDIAN_API_KEY", "")
ORG_ID = os.environ.get("MERIDIAN_ORG_ID", "")
COMPREFACE_URL = os.environ.get("COMPREFACE_URL", "http://localhost:8000")
COMPREFACE_API_KEY = os.environ.get("COMPREFACE_API_KEY", "")

ENABLE_DEPTH = os.environ.get("ENABLE_DEPTH", "0") == "1"
ENABLE_DEMOGRAPHICS = os.environ.get("ENABLE_DEMOGRAPHICS", "1") == "1"
DEMO_SAMPLE_RATE = int(os.environ.get("DEMO_SAMPLE_RATE", "5"))
HEARTBEAT_INTERVAL = 60
TRAFFIC_PUSH_INTERVAL = 900  # 15 minutes
PERSON_CLASS_ID = 0

_deepface = None
_deepface_available = False

if ENABLE_DEMOGRAPHICS:
    try:
        from deepface import DeepFace
        _deepface = DeepFace
        _deepface_available = True
        logger.info("DeepFace loaded — demographic analysis enabled")
    except ImportError:
        logger.warning("deepface not installed — demographic analysis disabled")


class CameraProcessor:
    """Process a single RTSP camera stream."""

    def __init__(self, camera_config: dict):
        self.camera_id = camera_config["id"]
        self.rtsp_url = camera_config["rtsp_url"]
        self.name = camera_config.get("name", "Camera")
        self.compliance_mode = camera_config.get("compliance_mode", "anonymous")
        self.zone_config = camera_config.get("zone_config", {})
        self.active_hours = camera_config.get("active_hours", {"start": "07:00", "end": "22:00"})
        # Per-camera feature toggles set by the merchant in the portal (vision_cameras.features).
        # The merchant's choice is authoritative: a disabled analysis is skipped even if
        # globally enabled. detection is core (always on); privacy-sensitive ones default off.
        _f = camera_config.get("features") or {}
        self.features = {
            "detection": _f.get("detection", True),
            "zones": _f.get("zones", True),
            "demographics": _f.get("demographics", False),
            "vip": _f.get("vip", False),
            "depth": _f.get("depth", False),
            "live_view": _f.get("live_view", False),
        }

        model_path = camera_config.get("model_path", os.environ.get("YOLO_MODEL", "yolo11n.pt"))
        self.model = YOLO(model_path)
        self.tracker = None
        self._init_tracker()

        self.depth_processor = None
        if ENABLE_DEPTH:
            self._init_depth()

        self._demo_frame_counter = 0
        self._reset_bucket()

    def _reset_bucket(self):
        self.current_bucket = defaultdict(int)
        self.current_bucket["occupancy_samples"] = []
        self.current_bucket["queue_samples"] = []
        self.current_bucket["wait_samples"] = []
        self.current_bucket["depth_distances"] = []
        self.current_bucket["depth_zone_counts"] = defaultdict(list)
        self.current_bucket["demographics"] = defaultdict(int)
        self.current_bucket["vip_sightings"] = []

    def _init_tracker(self):
        try:
            from boxmot import BYTETracker
            self.tracker = BYTETracker()
        except ImportError:
            logger.warning("boxmot not available — tracking disabled")

    def _init_depth(self):
        try:
            from depth_processor import DepthProcessor
            device = os.environ.get("DEPTH_DEVICE", "cuda")
            model_size = os.environ.get("DEPTH_MODEL_SIZE", "small")
            self.depth_processor = DepthProcessor(model_size=model_size, device=device)
            logger.info("Depth Anything V2 enabled")
        except Exception as e:
            logger.warning(f"Depth processor init failed (continuing without depth): {e}")

    def is_active(self) -> bool:
        now = datetime.now()
        start_h, start_m = map(int, self.active_hours.get("start", "07:00").split(":"))
        end_h, end_m = map(int, self.active_hours.get("end", "22:00").split(":"))
        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        return start_minutes <= current_minutes <= end_minutes

    def _analyze_demographics(self, frame: np.ndarray, detections: list):
        """Run DeepFace on person crops. Samples every DEMO_SAMPLE_RATE frames."""
        if not _deepface_available or not detections:
            return
        self._demo_frame_counter += 1
        if self._demo_frame_counter % DEMO_SAMPLE_RATE != 0:
            return
        h, w = frame.shape[:2]
        for det in detections[:4]:
            x1, y1, x2, y2 = int(det[0]), int(det[1]), int(det[2]), int(det[3])
            pad = int((x2 - x1) * 0.1)
            crop_y1 = max(0, y1 - pad)
            crop_y2 = min(h, y1 + int((y2 - y1) * 0.4))
            crop_x1 = max(0, x1 - pad)
            crop_x2 = min(w, x2 + pad)
            face_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]
            if face_crop.size == 0:
                continue
            try:
                results = _deepface.analyze(
                    face_crop,
                    actions=["age", "gender", "emotion"],
                    enforce_detection=False,
                    silent=True,
                    detector_backend="skip",
                )
                if not results:
                    continue
                r = results[0] if isinstance(results, list) else results
                age = r.get("age", 0)
                if age < 18:
                    bucket = "age_0-17"
                elif age < 25:
                    bucket = "age_18-24"
                elif age < 35:
                    bucket = "age_25-34"
                elif age < 50:
                    bucket = "age_35-49"
                else:
                    bucket = "age_50+"
                self.current_bucket["demographics"][bucket] += 1
                gender = r.get("dominant_gender", "")
                if gender:
                    self.current_bucket["demographics"][f"gender_{gender[0]}"] += 1
                emotion = r.get("dominant_emotion", "")
                if emotion:
                    self.current_bucket["demographics"][f"emotion_{emotion}"] += 1
            except Exception as e:
                logger.debug(f"DeepFace analysis failed: {e}")

    # TODO: VIP checking requires an async camera pipeline refactor.
    # Once process_camera / process_frame is fully async, wire _check_vip
    # into the per-frame loop and append results to current_bucket["vip_sightings"].
    async def _check_vip(
        self,
        frame: np.ndarray,
        detections: list,
        http_client: httpx.AsyncClient | None = None,
    ) -> list[dict]:
        """Check detected faces against VIP collection via CompreFace."""
        if not COMPREFACE_API_KEY or not detections:
            return []

        client = http_client or httpx.AsyncClient(timeout=5.0)
        close_client = http_client is None
        vips = []
        h, w = frame.shape[:2]
        try:
            for det in detections[:2]:  # Max 2 checks per frame
                x1, y1, x2, y2 = int(det[0]), int(det[1]), int(det[2]), int(det[3])
                pad = int((x2 - x1) * 0.1)
                crop = frame[max(0, y1 - pad):min(h, y2 + pad), max(0, x1 - pad):min(w, x2 + pad)]
                if crop.size == 0:
                    continue
                try:
                    _, buf = cv2.imencode('.jpg', crop)
                    resp = await client.post(
                        f"{COMPREFACE_URL}/api/v1/recognition/recognize",
                        headers={"x-api-key": COMPREFACE_API_KEY},
                        files={"file": ("face.jpg", buf.tobytes(), "image/jpeg")},
                    )
                    if resp.status_code == 200:
                        results = resp.json().get("result", [])
                        for r in results:
                            subjects = r.get("subjects", [])
                            for s in subjects:
                                if s.get("similarity", 0) > 0.9:
                                    vips.append({
                                        "subject": s["subject"],
                                        "similarity": round(s["similarity"], 3),
                                    })
                except Exception as e:
                    logger.debug(f"VIP check failed: {e}")
        finally:
            if close_client:
                await client.aclose()
        return vips

    def process_frame(self, frame: np.ndarray) -> dict:
        """Run YOLO detection + tracking on a single frame. Returns metrics."""
        results = self.model(frame, classes=[PERSON_CLASS_ID], verbose=False)

        detections = []
        if results and results[0].boxes:
            boxes = results[0].boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                detections.append([x1, y1, x2, y2, conf])

        person_count = len(detections)

        tracked_ids = set()
        if self.tracker and detections:
            try:
                dets = np.array(detections)
                tracks = self.tracker.update(dets, frame)
                tracked_ids = {int(t[4]) for t in tracks if len(t) > 4}
            except Exception as e:
                logger.debug(f"Tracking failed: {e}")

        if self.features["demographics"]:
            self._analyze_demographics(frame, detections)
        self.current_bucket["occupancy_samples"].append(person_count)

        queue_zone = self.zone_config.get("checkout", {}) if self.features["zones"] else {}
        if queue_zone and detections:
            qx1 = queue_zone.get("x1", 0)
            qy1 = queue_zone.get("y1", 0)
            qx2 = queue_zone.get("x2", frame.shape[1])
            qy2 = queue_zone.get("y2", frame.shape[0])
            in_queue = sum(
                1 for d in detections
                if d[0] >= qx1 and d[1] >= qy1 and d[2] <= qx2 and d[3] <= qy2
            )
            self.current_bucket["queue_samples"].append(in_queue)

        # Depth estimation (additive — never blocks existing pipeline)
        if self.features["depth"] and self.depth_processor and detections:
            try:
                depth_map = self.depth_processor.estimate_depth(frame)

                bboxes = [[d[0], d[1], d[2], d[3]] for d in detections]
                distances = self.depth_processor.estimate_distances(depth_map, bboxes)
                self.current_bucket["depth_distances"].extend(distances)

                if self.zone_config:
                    zone_depths = self.depth_processor.get_zone_depths(
                        depth_map, self.zone_config
                    )
                    zone_counts = defaultdict(int)
                    for dist in distances:
                        zone_name = self.depth_processor.classify_zone_by_depth(dist)
                        zone_counts[zone_name] += 1
                    for zone_name, count in zone_counts.items():
                        self.current_bucket["depth_zone_counts"][zone_name].append(count)
            except Exception as e:
                logger.debug(f"Depth estimation failed: {e}")

        return {
            "person_count": person_count,
            "tracked_ids": tracked_ids,
        }

    def flush_bucket(self) -> dict:
        """Flush current 15-minute bucket and return traffic metrics."""
        occ = self.current_bucket["occupancy_samples"]
        queue = self.current_bucket["queue_samples"]

        now_utc = datetime.now(timezone.utc)
        bucket_time = now_utc.replace(
            minute=(now_utc.minute // 15) * 15, second=0, microsecond=0
        ).isoformat()

        metrics = {
            "org_id": ORG_ID,
            "camera_id": self.camera_id,
            "bucket": bucket_time,
            "entries": self.current_bucket.get("entries", 0),
            "exits": self.current_bucket.get("exits", 0),
            "occupancy_avg": round(sum(occ) / max(len(occ), 1), 1),
            "occupancy_peak": max(occ) if occ else 0,
            "queue_length_avg": round(sum(queue) / max(len(queue), 1), 1),
            "queue_wait_avg_sec": 0,
            "conversion_rate": 0,
            "demographic_breakdown": dict(self.current_bucket.get("demographics", {})),
        }

        # VIP sightings (populated when async VIP pipeline is active)
        metrics["vip_sightings"] = self.current_bucket.get("vip_sightings", [])

        # Depth metrics (only present when ENABLE_DEPTH=1)
        depth_dists = self.current_bucket.get("depth_distances", [])
        depth_zones = self.current_bucket.get("depth_zone_counts", {})
        if depth_dists:
            metrics["avg_person_distance"] = round(
                sum(depth_dists) / len(depth_dists), 4
            )
            zone_occ = {}
            for zone_name, counts in depth_zones.items():
                zone_occ[zone_name] = round(sum(counts) / max(len(counts), 1), 1)
            metrics["depth_zone_occupancy"] = zone_occ

        self._reset_bucket()

        return metrics


class EdgeAgent:
    """Main edge agent — manages cameras and pushes data to cloud."""

    def __init__(self):
        self.cameras: list[CameraProcessor] = []
        self.running = True
        self.http = httpx.AsyncClient(
            base_url=API_URL,
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=30,
        )

    async def load_config(self):
        config_path = Path("config/cameras.json")
        if config_path.exists():
            with open(config_path) as f:
                camera_configs = json.load(f)
            for cfg in camera_configs:
                self.cameras.append(CameraProcessor(cfg))
            logger.info(f"Loaded {len(self.cameras)} cameras from config")
        else:
            try:
                resp = await self.http.get(f"/api/vision/cameras/{ORG_ID}")
                data = resp.json()
                for cam in data.get("cameras", []):
                    if cam.get("status") != "disabled":
                        self.cameras.append(CameraProcessor(cam))
                logger.info(f"Loaded {len(self.cameras)} cameras from API")
            except Exception as e:
                logger.error(f"Failed to load cameras: {e}")

    async def heartbeat_loop(self):
        while self.running:
            for cam in self.cameras:
                try:
                    await self.http.post(
                        f"/api/vision/cameras/{cam.camera_id}/heartbeat",
                        json={"status": "online"},
                    )
                except Exception as e:
                    logger.warning(f"Heartbeat failed for {cam.name}: {e}")
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def push_traffic(self, metrics: dict):
        try:
            await self.http.post("/api/vision/ingest/traffic", json=metrics)
        except Exception as e:
            logger.error(f"Traffic push failed: {e}")

    async def process_camera(self, cam: CameraProcessor):
        logger.info(f"Starting camera: {cam.name} ({cam.rtsp_url})")
        cap = cv2.VideoCapture(cam.rtsp_url)

        if not cap.isOpened():
            logger.error(f"Cannot open camera: {cam.name}")
            return

        last_flush = time.time()
        frame_skip = 3
        frame_count = 0

        try:
            while self.running:
                ret, frame = await asyncio.to_thread(cap.read)
                if not ret:
                    logger.warning(f"Frame read failed: {cam.name}, reconnecting...")
                    cap.release()
                    await asyncio.sleep(5)
                    cap = cv2.VideoCapture(cam.rtsp_url)
                    continue

                frame_count += 1
                if frame_count % frame_skip != 0:
                    continue

                if not cam.is_active():
                    await asyncio.sleep(10)
                    continue

                cam.process_frame(frame)

                if time.time() - last_flush >= TRAFFIC_PUSH_INTERVAL:
                    metrics = cam.flush_bucket()
                    await self.push_traffic(metrics)
                    last_flush = time.time()

                await asyncio.sleep(0.033)  # ~30fps cap
        finally:
            cap.release()

    async def run(self):
        logger.info("Meridian Edge Agent starting...")
        await self.load_config()

        if not self.cameras:
            logger.error("No cameras configured. Exiting.")
            return

        tasks = [
            asyncio.create_task(self.heartbeat_loop()),
        ]
        for cam in self.cameras:
            tasks.append(asyncio.create_task(self.process_camera(cam)))

        def shutdown(sig, frame):
            logger.info("Shutting down...")
            self.running = False

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        await asyncio.gather(*tasks, return_exceptions=True)
        await self.http.aclose()
        logger.info("Edge agent stopped.")


if __name__ == "__main__":
    agent = EdgeAgent()
    asyncio.run(agent.run())
