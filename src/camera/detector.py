from __future__ import annotations

import logging
import os
from typing import Any

import warnings

import numpy as np

try:
    import supervision as sv
    warnings.filterwarnings("ignore", message=".*ByteTrack.*deprecated.*")
except ImportError:
    sv = None

logger = logging.getLogger("meridian.camera.detector")

# Backend chosen at runtime: 'yolo' (ultralytics, AGPL — default) or 'rfdetr'
# (Apache-2.0). Flip DETECTOR_BACKEND=rfdetr to drop the AGPL dep once verified on the
# GPU box; tracking/zones/output below are backend-agnostic. ponytail: one extraction
# method branches, nothing else changes.
DETECTOR_BACKEND = os.environ.get("DETECTOR_BACKEND", "yolo").lower()
# COCO person id differs by backend (YOLO person=0; RF-DETR's 91-class COCO person=1).
PERSON_CLASS = int(os.environ.get("PERSON_CLASS_ID", 1 if DETECTOR_BACKEND == "rfdetr" else 0))


class MeridianDetector:

    def __init__(self, model_size: str = "yolo11n", confidence: float = 0.35) -> None:
        self._backend = DETECTOR_BACKEND
        if self._backend == "rfdetr":
            from rfdetr import RFDETRBase  # Apache-2.0; lazy
            self._model = RFDETRBase()
            logger.info("detector backend=rfdetr (Apache-2.0)")
        else:
            from ultralytics import YOLO  # AGPL; lazy
            self._model = YOLO(model_size)
            logger.info("detector backend=yolo")
        self._tracker = sv.ByteTrack()
        self._confidence = confidence
        self._polygon_zone_cache: dict[str, Any] = {}

    def _persons(self, frame: np.ndarray) -> "sv.Detections":
        """Backend-specific person detection → supervision Detections (xyxy/conf)."""
        if self._backend == "rfdetr":
            det = self._model.predict(frame, threshold=self._confidence)  # returns sv.Detections
            return det[det.class_id == PERSON_CLASS]
        results = self._model(frame, verbose=False)[0]
        boxes = results.boxes
        mask = boxes.cls.cpu().numpy().astype(int) == PERSON_CLASS
        person_boxes = boxes[mask]
        return sv.Detections(
            xyxy=person_boxes.xyxy.cpu().numpy(),
            confidence=person_boxes.conf.cpu().numpy(),
            class_id=person_boxes.cls.cpu().numpy().astype(int),
        )

    def process_frame(
        self,
        frame: np.ndarray,
        merchant_id: str,
        camera_id: str,
        zone_map: dict[str, list[list[float]]] | None = None,
    ) -> dict[str, Any]:
        detections = self._persons(frame)
        detections = detections[detections.confidence >= self._confidence]
        detections = self._tracker.update_with_detections(detections)

        frame_h, frame_w = frame.shape[:2]
        persons: list[dict[str, Any]] = []

        for i in range(len(detections)):
            x1, y1, x2, y2 = detections.xyxy[i]
            cx = float((x1 + x2) / 2)
            cy = float((y1 + y2) / 2)

            x_norm = cx / frame_w
            y_norm = cy / frame_h

            tracker_id = int(detections.tracker_id[i]) if detections.tracker_id is not None else i

            zone = self._detect_zone(x_norm, y_norm, zone_map, frame_w, frame_h) if zone_map else None

            persons.append({
                "tracker_id": tracker_id,
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                "center_norm": [round(x_norm, 4), round(y_norm, 4)],
                "confidence": round(float(detections.confidence[i]), 3),
                "zone": zone,
            })

        return {
            "merchant_id": merchant_id,
            "camera_id": camera_id,
            "persons": persons,
            "total_detected": len(persons),
            "frame_shape": [frame_h, frame_w],
        }

    def _detect_zone(
        self,
        x_norm: float,
        y_norm: float,
        zone_map: dict[str, list[list[float]]] | None,
        frame_w: int,
        frame_h: int,
    ) -> str | None:
        if not zone_map:
            return None

        # Pixel coordinates for PolygonZone containment check
        px = int(x_norm * frame_w)
        py = int(y_norm * frame_h)

        for zone_name, polygon_norm in zone_map.items():
            polygon_px = np.array(
                [[pt[0] * frame_w, pt[1] * frame_h] for pt in polygon_norm],
                dtype=np.int32,
            )
            zone_key = f"{zone_name}:{frame_w}x{frame_h}"
            if zone_key not in self._polygon_zone_cache:
                self._polygon_zone_cache[zone_key] = sv.PolygonZone(polygon=polygon_px)
            poly_zone = self._polygon_zone_cache[zone_key]

            # Build a single-point detection to test containment
            point_det = sv.Detections(
                xyxy=np.array([[px - 1, py - 1, px + 1, py + 1]], dtype=np.float32),
            )
            mask = poly_zone.trigger(point_det)
            if mask.any():
                return zone_name

        return None
