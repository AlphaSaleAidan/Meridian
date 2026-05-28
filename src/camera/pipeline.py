from __future__ import annotations

import logging
from typing import Any

import numpy as np
import supervision as sv

from .detector import MeridianDetector
from .line_counter import EntryExitCounter
from .people_counter import MeridianPeopleCounter
from .rtsp_handler import RTSPStreamHandler
from .supabase_writer import CameraDataWriter
from .zone_loader import load_zones_for_camera, load_entry_lines

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

        # People counter + writer per camera (zone counting, dwell, density)
        self._people_counters: dict[str, MeridianPeopleCounter] = {}
        self._writers: dict[str, CameraDataWriter] = {}
        for cfg in camera_configs:
            cam_id = cfg["camera_id"]
            org_id = cfg.get("org_id", merchant_id)
            biz = cfg.get("business_type", "restaurant")
            zones = load_zones_for_camera(cfg, 1280, 720, biz)
            entry_lines = load_entry_lines(cfg, 1280, 720)
            self._people_counters[cam_id] = MeridianPeopleCounter(
                model_path=model_size,
                zones=zones,
                entry_lines=entry_lines,
            )
            self._writers[cam_id] = CameraDataWriter(org_id=org_id, camera_id=cam_id)

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

            # People counter: zone counts, dwell, density
            # Reuse detections from _detector to avoid a second YOLO pass
            pc = self._people_counters.get(cam_id)
            writer = self._writers.get(cam_id)
            if pc and writer:
                cr = pc.process_frame(frame, precomputed_detections=detections)
                writer.accumulate(cr.zone_counts, cr.total_count)
                if cr.entries_this_frame or cr.exits_this_frame:
                    writer.write_entry_exit(cr.entries_this_frame, cr.exits_this_frame)
                completions = pc.flush_dwell(cr.tracked_ids)
                writer.write_dwell_records(completions, pc.zone_configs)
                if cr.density in ("high", "critical"):
                    checkout_zones = [
                        zid for zid, cfg in pc.zone_configs.items()
                        if cfg.get("type") in ("checkout", "queue")
                    ]
                    q_count = sum(cr.zone_counts.get(z, 0) for z in checkout_zones)
                    if q_count > 0:
                        writer.write_queue_metrics(float(q_count), q_count * 30.0)

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
