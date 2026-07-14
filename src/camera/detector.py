from __future__ import annotations

import logging
import os
from typing import Any

import warnings

import numpy as np

# supervision (ByteTrack/PolygonZone) installs without torch and is required
# for tracking either way; ultralytics (torch, ~2GB) is optional — when it's
# absent we fall back to the ONNX backend, which runs the same yolo11n weights
# on onnxruntime CPU. That's the production posture on Railway, where torch
# OOMs the image build.
try:
    import supervision as sv
    warnings.filterwarnings("ignore", message=".*ByteTrack.*deprecated.*")
except ImportError:
    sv = None

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from .onnx_yolo import OnnxPersonModel, model_available as _onnx_available

logger = logging.getLogger("meridian.camera.detector")

PERSON_CLASS = 0

# Person-detection confidence floor. Tuned on MOT17-09 (eval/camera): sweeping
# 0.25→0.45 raised F1 0.712→0.750, MOTA 0.40→0.535 and IDF1 0.688→0.744 (higher
# precision + steadier tracks at a small recall cost), so the default moved from
# 0.35 to 0.45. Override per-deployment with MERIDIAN_VISION_CONFIDENCE.
DEFAULT_CONFIDENCE = float(os.environ.get("MERIDIAN_VISION_CONFIDENCE", "0.45"))


class MeridianDetector:

    def __init__(self, model_size: str = "yolo11n", confidence: float | None = None) -> None:
        if sv is None:
            raise RuntimeError(
                "supervision is not installed — vision tracking unavailable"
            )
        if YOLO is not None:
            self._model = YOLO(model_size)
            self._onnx = None
        elif _onnx_available():
            self._model = None
            self._onnx = OnnxPersonModel()
            logger.info("ultralytics unavailable — using ONNX vision backend")
        else:
            raise RuntimeError(
                "No vision backend: install ultralytics, or onnxruntime plus the "
                "bundled yolo11n.onnx (src/camera/models/)"
            )
        self._tracker = sv.ByteTrack()
        self._confidence = DEFAULT_CONFIDENCE if confidence is None else confidence
        self._polygon_zone_cache: dict[str, Any] = {}

    def _infer_persons(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Run the active backend → (xyxy [N,4] px, confidence [N]) for persons."""
        if self._model is not None:
            results = self._model(frame, verbose=False)[0]
            boxes = results.boxes
            mask = boxes.cls.cpu().numpy().astype(int) == PERSON_CLASS
            person_boxes = boxes[mask]
            return person_boxes.xyxy.cpu().numpy(), person_boxes.conf.cpu().numpy()
        return self._onnx.infer(frame)

    def process_frame(
        self,
        frame: np.ndarray,
        merchant_id: str,
        camera_id: str,
        zone_map: dict[str, list[list[float]]] | None = None,
    ) -> dict[str, Any]:
        xyxy, conf = self._infer_persons(frame)

        detections = sv.Detections(
            xyxy=xyxy,
            confidence=conf,
            class_id=np.zeros(len(conf), dtype=int),
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
