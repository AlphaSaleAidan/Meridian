"""
PersonDetector — YOLOv8-nano person detection.

Lazy-loads ultralytics to keep import cost near zero when
the vision pipeline is not actively running. Returns bounding
boxes with confidence scores for each detected person.
"""
import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger("meridian.vision.detector")

_model = None


@dataclass
class Detection:
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    confidence: float
    class_id: int = 0  # 0 = person in COCO

    @property
    def center(self) -> tuple[float, float]:
        return (
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2,
        )

    @property
    def area(self) -> float:
        return max(0, self.bbox[2] - self.bbox[0]) * max(0, self.bbox[3] - self.bbox[1])

    def to_xyxy(self) -> np.ndarray:
        return np.array(self.bbox, dtype=np.float32)


class PersonDetector:
    PERSON_CLASS = 0
    DEFAULT_CONFIDENCE = 0.4
    DEFAULT_MODEL = "yolov8n.pt"

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL,
        confidence: float = DEFAULT_CONFIDENCE,
        device: str = "auto",
    ):
        self._model_path = model_path
        self._confidence = confidence
        self._device = device
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from ultralytics import YOLO
            self._model = YOLO(self._model_path)
            if self._device != "auto":
                self._model.to(self._device)
            logger.info("YOLO model loaded: %s", self._model_path)
        except ImportError:
            logger.error("ultralytics not installed — run: pip install ultralytics")
            raise

    def detect(self, frame: np.ndarray) -> list[Detection]:
        self._load_model()
        results = self._model(
            frame,
            conf=self._confidence,
            classes=[self.PERSON_CLASS],
            verbose=False,
        )
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for i in range(len(boxes)):
                xyxy = boxes.xyxy[i].cpu().numpy()
                conf = float(boxes.conf[i].cpu())
                detections.append(Detection(
                    bbox=(float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])),
                    confidence=conf,
                    class_id=self.PERSON_CLASS,
                ))
        return detections

    def detect_batch(self, frames: list[np.ndarray]) -> list[list[Detection]]:
        return [self.detect(f) for f in frames]

    @property
    def is_loaded(self) -> bool:
        return self._model is not None
