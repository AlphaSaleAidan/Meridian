"""
Meridian People Counter — zone counting, line crossing, and density.

Extends the existing detector with patterns from the Labellerr
Hands-On CV repo (Crowd_analysis_using_YOLOv12, perimeter_sensing,
traffic_flow_counting notebooks).

Three counting modes on the same YOLO inference pass:
  1. Zone Counting (PolygonZone.trigger) — people per zone per frame
  2. Line Crossing (LineZone.trigger) — entry/exit counts
  3. Crowd Density — total count bucketed into severity levels

Writes to: vision_traffic (5-min buckets), vision_visits (dwell records)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import warnings

import numpy as np
import supervision as sv
from ultralytics import YOLO

warnings.filterwarnings("ignore", message=".*ByteTrack.*deprecated.*")

logger = logging.getLogger("meridian.camera.counter")

PERSON_CLASS = 0


@dataclass
class CountResult:
    zone_counts: dict[str, int] = field(default_factory=dict)
    zone_person_ids: dict[str, list[int]] = field(default_factory=dict)
    entries_this_frame: int = 0
    exits_this_frame: int = 0
    total_count: int = 0
    density: str = "empty"
    tracked_ids: list[int] = field(default_factory=list)
    detections: sv.Detections | None = None


class MeridianPeopleCounter:
    """Unified people counter wrapping YOLO + supervision tracking."""

    CONFIDENCE = 0.35

    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        zones: list[dict[str, Any]] | None = None,
        entry_lines: list[dict[str, Any]] | None = None,
        frame_width: int = 1280,
        frame_height: int = 720,
    ) -> None:
        self.frame_w = frame_width
        self.frame_h = frame_height
        self._model = YOLO(model_path)
        self._tracker = sv.ByteTrack()

        self._polygon_zones: dict[str, sv.PolygonZone] = {}
        self._zone_configs: dict[str, dict] = {}
        self._line_zones: list[tuple[str, sv.LineZone, str]] = []

        # Dwell tracking: {track_id: {zone_id, start_time}}
        self._dwell: dict[int, dict] = {}

        # Heatmap accumulator
        self._heatmap = sv.HeatMapAnnotator(
            position=sv.Position.BOTTOM_CENTER,
            opacity=0.6,
            radius=40,
            kernel_size=25,
        )

        # Cumulative line crossing counts
        self.cumulative_entries = 0
        self.cumulative_exits = 0

        if zones:
            self._init_zones(zones)
        if entry_lines:
            self._init_lines(entry_lines)

        logger.info(
            "PeopleCounter: %d zones, %d lines, model=%s",
            len(self._polygon_zones), len(self._line_zones), model_path,
        )

    @property
    def zone_configs(self) -> dict[str, dict]:
        return self._zone_configs

    def _init_zones(self, zones: list[dict[str, Any]]) -> None:
        for z in zones:
            zid = z["zone_id"]
            coords = z.get("polygon_coords", [])
            if len(coords) < 3:
                continue
            polygon = np.array(coords, dtype=np.int32)
            try:
                pz = sv.PolygonZone(polygon=polygon)
                self._polygon_zones[zid] = pz
                self._zone_configs[zid] = {
                    "name": z.get("name", zid),
                    "type": z.get("type", "floor"),
                }
            except Exception as exc:
                logger.warning("Zone %s init failed: %s", zid, exc)

    def _init_lines(self, lines: list[dict[str, Any]]) -> None:
        for cfg in lines:
            start = cfg["start"]
            end = cfg["end"]
            direction = cfg.get("entry_direction", "in")
            cam_id = cfg.get("camera_id", "default")
            try:
                lz = sv.LineZone(
                    start=sv.Point(int(start[0]), int(start[1])),
                    end=sv.Point(int(end[0]), int(end[1])),
                )
                self._line_zones.append((cam_id, lz, direction))
            except Exception as exc:
                logger.warning("LineZone init failed: %s", exc)

    def process_frame(
        self,
        frame: np.ndarray,
        precomputed_detections: sv.Detections | None = None,
    ) -> CountResult:
        result = CountResult()

        if precomputed_detections is not None:
            detections = precomputed_detections
            result.total_count = len(detections)
            if len(detections) == 0:
                result.density = "empty"
                return result
            # Already tracked — skip YOLO and tracker
            result.detections = detections
        else:
            yolo_out = self._model(
                frame, classes=[PERSON_CLASS], conf=self.CONFIDENCE, verbose=False
            )[0]

            detections = sv.Detections.from_ultralytics(yolo_out)
            result.total_count = len(detections)

            if len(detections) == 0:
                result.density = "empty"
                return result

            detections = self._tracker.update_with_detections(detections)
            result.detections = detections

        if detections.tracker_id is not None:
            result.tracked_ids = detections.tracker_id.tolist()

        # Zone counting
        now = time.time()
        for zid, pz in self._polygon_zones.items():
            try:
                mask = pz.trigger(detections=detections)
                result.zone_counts[zid] = int(mask.sum())
                if detections.tracker_id is not None:
                    ids_in = detections.tracker_id[mask].tolist()
                    result.zone_person_ids[zid] = ids_in
                    for tid in ids_in:
                        if tid not in self._dwell:
                            self._dwell[tid] = {"zone_id": zid, "start": now}
            except Exception:
                result.zone_counts[zid] = 0

        # Line crossing
        for _cam, lz, direction in self._line_zones:
            try:
                crossed_in, crossed_out = lz.trigger(detections)
                cin = int(crossed_in.sum())
                cout = int(crossed_out.sum())
                if direction == "out":
                    cin, cout = cout, cin
                result.entries_this_frame += cin
                result.exits_this_frame += cout
                self.cumulative_entries += cin
                self.cumulative_exits += cout
            except Exception:
                pass

        result.density = self._classify(result.total_count)
        return result

    def process_frame_with_pose(self, frame: np.ndarray) -> CountResult:
        """Process frame with pose estimation for activity classification."""
        result = self.process_frame(frame)

        if result.total_count == 0:
            return result

        try:
            pose_model = self._get_pose_model()
            pose_out = pose_model(frame, classes=[PERSON_CLASS], conf=self.CONFIDENCE, verbose=False)[0]

            if pose_out.keypoints is not None:
                keypoints = pose_out.keypoints.data.cpu().numpy()
                activities = []
                for kps in keypoints:
                    activity = self._classify_pose(kps)
                    activities.append(activity)
                result.zone_counts["_activities"] = len(activities)
        except Exception as e:
            logger.debug("Pose estimation failed: %s", e)

        return result

    def _get_pose_model(self):
        if not hasattr(self, '_pose_model'):
            self._pose_model = YOLO("yolo11n-pose.pt")
        return self._pose_model

    @staticmethod
    def _classify_pose(keypoints: np.ndarray) -> str:
        """Classify activity from COCO keypoints (17 points)."""
        if len(keypoints) < 17:
            return "unknown"
        nose_y = keypoints[0][1]
        hip_y = (keypoints[11][1] + keypoints[12][1]) / 2
        knee_y = (keypoints[13][1] + keypoints[14][1]) / 2
        if hip_y > 0 and knee_y > 0:
            if abs(hip_y - knee_y) < 30:
                return "sitting"
        if nose_y > 0 and hip_y > 0:
            torso_height = abs(hip_y - nose_y)
            if torso_height < 50:
                return "bending"
        return "standing"

    def generate_heatmap(self, frame: np.ndarray, detections: sv.Detections | None = None) -> np.ndarray:
        """Overlay density heatmap on frame using accumulated detection positions."""
        if detections is None or len(detections) == 0:
            return frame
        return self._heatmap.annotate(scene=frame.copy(), detections=detections)

    def flush_dwell(self, active_ids: list[int]) -> list[dict]:
        """Return completed dwell records for people who left their zone."""
        now = time.time()
        completions = []
        gone = [tid for tid in list(self._dwell) if tid not in active_ids]
        for tid in gone:
            rec = self._dwell.pop(tid)
            secs = round(now - rec["start"], 1)
            if secs >= 5:
                completions.append({
                    "zone_id": rec["zone_id"],
                    "dwell_seconds": secs,
                })

        # Evict stale entries older than 30 minutes
        cutoff = now - 1800
        stale = [tid for tid, rec in self._dwell.items() if rec["start"] < cutoff]
        for tid in stale:
            del self._dwell[tid]

        return completions

    def reset(self) -> None:
        self.cumulative_entries = 0
        self.cumulative_exits = 0
        self._dwell.clear()

    @staticmethod
    def _classify(count: int) -> str:
        if count == 0:
            return "empty"
        if count <= 3:
            return "low"
        if count <= 8:
            return "medium"
        if count <= 15:
            return "high"
        return "critical"
