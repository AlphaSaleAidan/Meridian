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
HEARTBEAT_INTERVAL = 60
TRAFFIC_PUSH_INTERVAL = 900  # 15 minutes
PERSON_CLASS_ID = 0


class CameraProcessor:
    """Process a single RTSP camera stream."""

    def __init__(self, camera_config: dict):
        self.camera_id = camera_config["id"]
        self.rtsp_url = camera_config["rtsp_url"]
        self.name = camera_config.get("name", "Camera")
        self.compliance_mode = camera_config.get("compliance_mode", "anonymous")
        self.zone_config = camera_config.get("zone_config", {})
        self.active_hours = camera_config.get("active_hours", {"start": "07:00", "end": "22:00"})

        self.model = YOLO("yolo11n.pt")
        self.tracker = None
        self._init_tracker()

        self.depth_processor = None
        if ENABLE_DEPTH:
            self._init_depth()

        self.current_bucket = defaultdict(int)
        self.current_bucket["occupancy_samples"] = []
        self.current_bucket["queue_samples"] = []
        self.current_bucket["wait_samples"] = []
        self.current_bucket["depth_distances"] = []
        self.current_bucket["depth_zone_counts"] = defaultdict(list)

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

        self.current_bucket["occupancy_samples"].append(person_count)

        queue_zone = self.zone_config.get("checkout", {})
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
        if self.depth_processor and detections:
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

        bucket_time = datetime.now(timezone.utc).replace(
            minute=(datetime.now().minute // 15) * 15, second=0, microsecond=0
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
            "demographic_breakdown": {},
        }

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

        self.current_bucket = defaultdict(int)
        self.current_bucket["occupancy_samples"] = []
        self.current_bucket["queue_samples"] = []
        self.current_bucket["wait_samples"] = []
        self.current_bucket["depth_distances"] = []
        self.current_bucket["depth_zone_counts"] = defaultdict(list)

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
                ret, frame = cap.read()
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
