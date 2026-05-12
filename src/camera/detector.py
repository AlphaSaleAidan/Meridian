from __future__ import annotations

import logging
from typing import Any

import numpy as np

try:
    import supervision as sv
    from ultralytics import YOLO
except ImportError:
    sv = None
    YOLO = None

logger = logging.getLogger("meridian.camera.detector")

PERSON_CLASS = 0


class MeridianDetector:

    def __init__(self, model_size: str = "yolo11n", confidence: float = 0.35) -> None:
        self._model = YOLO(model_size)
        self._tracker = sv.ByteTrack()
        self._confidence = confidence

    def process_frame(
        self,
        frame: np.ndarray,
        merchant_id: str,
        camera_id: str,
        zone_map: dict[str, list[list[float]]] | None = None,
    ) -> dict[str, Any]:
        results = self._model(frame, verbose=False)[0]

        boxes = results.boxes
        mask = boxes.cls.cpu().numpy().astype(int) == PERSON_CLASS
        person_boxes = boxes[mask]

        detections = sv.Detections(
            xyxy=person_boxes.xyxy.cpu().numpy(),
            confidence=person_boxes.conf.cpu().numpy(),
            class_id=person_boxes.cls.cpu().numpy().astype(int),
        )

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
            poly_zone = sv.PolygonZone(polygon=polygon_px)

            # Build a single-point detection to test containment
            point_det = sv.Detections(
                xyxy=np.array([[px - 1, py - 1, px + 1, py + 1]], dtype=np.float32),
            )
            mask = poly_zone.trigger(point_det)
            if mask.any():
                return zone_name

        return None
