from __future__ import annotations

import logging
from typing import Any

import numpy as np
import supervision as sv

from .detector import MeridianDetector
from .line_counter import EntryExitCounter
from .rtsp_handler import RTSPStreamHandler

logger = logging.getLogger("meridian.camera.pipeline")


class CameraPipeline:

    def __init__(
        self,
        merchant_id: str,
        camera_configs: list[dict[str, Any]],
        model_size: str = "yolo11n",
    ) -> None:
        self._merchant_id = merchant_id
        self._camera_configs = camera_configs
        self._detector = MeridianDetector(model_size=model_size)
        self._streams: dict[str, RTSPStreamHandler] = {}
        self._zone_maps: dict[str, dict[str, list[list[float]]]] = {}

        line_configs: list[dict[str, Any]] = []
        for cfg in camera_configs:
            cam_id = cfg["camera_id"]
            rtsp_url = cfg["rtsp_url"]
            self._streams[cam_id] = RTSPStreamHandler(rtsp_url=rtsp_url, camera_id=cam_id)

            zone_map = self._load_zone_map(cam_id, cfg)
            if zone_map:
                self._zone_maps[cam_id] = zone_map

            for line in cfg.get("entry_lines", []):
                line_configs.append({
                    "camera_id": cam_id,
                    "start": line["start"],
                    "end": line["end"],
                    "entry_direction": line.get("entry_direction", "in"),
                })

        self._counter = EntryExitCounter(line_configs)

    def start(self) -> None:
        for cam_id, stream in self._streams.items():
            try:
                stream.start()
            except ConnectionError:
                logger.error("Could not start stream for camera %s", cam_id)

    def stop(self) -> None:
        for stream in self._streams.values():
            stream.stop()

    def process_cycle(self) -> dict[str, Any]:
        all_tracking: list[dict[str, Any]] = []
        all_counts: list[dict[str, Any]] = []

        for cam_id, stream in self._streams.items():
            if not stream.is_running:
                continue

            frame = stream.get_latest_frame(timeout=1.0)
            if frame is None:
                logger.debug("No frame available for camera %s", cam_id)
                continue

            zone_map = self._zone_maps.get(cam_id)
            detection_result = self._detector.process_frame(
                frame=frame,
                merchant_id=self._merchant_id,
                camera_id=cam_id,
                zone_map=zone_map,
            )
            all_tracking.append(detection_result)

            frame_h, frame_w = frame.shape[:2]
            detections = self._build_sv_detections(detection_result)
            if detections is not None:
                counts = self._counter.process_detections(
                    detections=detections,
                    camera_id=cam_id,
                    frame_w=frame_w,
                    frame_h=frame_h,
                )
                all_counts.append(counts)

        return {
            "merchant_id": self._merchant_id,
            "tracking": all_tracking,
            "entry_exit": all_counts,
            "cameras_active": sum(1 for s in self._streams.values() if s.is_running),
            "cameras_total": len(self._streams),
        }

    def _build_sv_detections(self, result: dict[str, Any]) -> sv.Detections | None:
        persons = result.get("persons", [])
        if not persons:
            return None

        xyxy = np.array([p["bbox"] for p in persons], dtype=np.float32)
        confidence = np.array([p["confidence"] for p in persons], dtype=np.float32)
        tracker_ids = np.array([p["tracker_id"] for p in persons], dtype=int)

        return sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            tracker_id=tracker_ids,
        )

    def _load_zone_map(
        self,
        camera_id: str,
        config: dict[str, Any],
    ) -> dict[str, list[list[float]]] | None:
        # Prefer inline zone_config from the camera config dict
        if config.get("zone_config"):
            return config["zone_config"]

        # Fall back to Supabase lookup
        try:
            from ..db import get_db
            db = get_db()
            if db is None or not hasattr(db, "client"):
                return None

            result = (
                db.client.table("vision_cameras")
                .select("zone_config")
                .eq("id", camera_id)
                .limit(1)
                .execute()
            )
            if result.data and result.data[0].get("zone_config"):
                return result.data[0]["zone_config"]
        except Exception:
            logger.debug("Could not load zone_config from DB for camera %s", camera_id)

        return None
