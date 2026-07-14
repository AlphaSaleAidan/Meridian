"""ONNX Runtime person-detection backend for MeridianDetector.

The Railway API image can't carry ultralytics (torch is ~2GB and OOMs the
build), which left the browser-camera frame path with no model at all. This
backend runs the same yolo11n network from a ~10MB ONNX export on
onnxruntime's CPU provider — same weights, same detections, no torch.

Output contract matches what detector.py needs: person boxes as xyxy in
original-frame pixels plus confidences. Tracking/zones stay in supervision
(ByteTrack/PolygonZone), which installs fine without ultralytics.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger("meridian.camera.onnx_yolo")

try:
    import onnxruntime as ort
except ImportError:  # keep module importable so detector.py can report cleanly
    ort = None

PERSON_CLASS = 0
_INPUT_SIZE = 640
# Pre-NMS floor only — the caller applies the real confidence threshold
# (MERIDIAN_VISION_CONFIDENCE) after tracking, same as the torch path.
_PRE_NMS_CONF = 0.10
_NMS_IOU = 0.45

DEFAULT_MODEL_PATH = str(Path(__file__).parent / "models" / "yolo11n.onnx")


def model_available() -> bool:
    path = os.environ.get("MERIDIAN_VISION_ONNX_MODEL", DEFAULT_MODEL_PATH)
    return ort is not None and Path(path).is_file()


class OnnxPersonModel:
    """yolo11n person detector on onnxruntime CPU."""

    def __init__(self, model_path: str | None = None) -> None:
        if ort is None:
            raise RuntimeError("onnxruntime is not installed")
        path = model_path or os.environ.get("MERIDIAN_VISION_ONNX_MODEL", DEFAULT_MODEL_PATH)
        if not Path(path).is_file():
            raise RuntimeError(f"ONNX vision model not found at {path}")
        so = ort.SessionOptions()
        # One frame at a time per camera worker; don't let ORT grab every core
        # of the shared API container.
        so.intra_op_num_threads = int(os.environ.get("MERIDIAN_VISION_ORT_THREADS", "2"))
        self._session = ort.InferenceSession(path, sess_options=so, providers=["CPUExecutionProvider"])
        self._input_name = self._session.get_inputs()[0].name
        logger.info("ONNX vision model loaded from %s", path)

    def infer(self, frame_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return (xyxy [N,4] float32 in original pixels, confidence [N]) for persons."""
        blob, ratio, pad = self._letterbox(frame_bgr)
        out = self._session.run(None, {self._input_name: blob})[0]
        # yolo11 ONNX head: (1, 84, 8400) → rows = [cx, cy, w, h, 80 class scores]
        pred = out[0].T  # (8400, 84)
        person_conf = pred[:, 4 + PERSON_CLASS]
        keep = person_conf >= _PRE_NMS_CONF
        if not keep.any():
            return np.zeros((0, 4), dtype=np.float32), np.zeros((0,), dtype=np.float32)
        boxes_cxcywh = pred[keep, :4]
        conf = person_conf[keep]

        # cxcywh → xyxy in letterboxed coords, then undo letterbox.
        xy = boxes_cxcywh[:, :2]
        wh = boxes_cxcywh[:, 2:4]
        xyxy = np.concatenate([xy - wh / 2, xy + wh / 2], axis=1)
        xyxy[:, [0, 2]] = (xyxy[:, [0, 2]] - pad[0]) / ratio
        xyxy[:, [1, 3]] = (xyxy[:, [1, 3]] - pad[1]) / ratio
        h, w = frame_bgr.shape[:2]
        xyxy[:, [0, 2]] = xyxy[:, [0, 2]].clip(0, w)
        xyxy[:, [1, 3]] = xyxy[:, [1, 3]].clip(0, h)

        # NMS expects xywh boxes.
        xywh = np.concatenate([xyxy[:, :2], xyxy[:, 2:4] - xyxy[:, :2]], axis=1)
        idx = cv2.dnn.NMSBoxes(xywh.tolist(), conf.tolist(), _PRE_NMS_CONF, _NMS_IOU)
        if len(idx) == 0:
            return np.zeros((0, 4), dtype=np.float32), np.zeros((0,), dtype=np.float32)
        idx = np.asarray(idx).reshape(-1)
        return xyxy[idx].astype(np.float32), conf[idx].astype(np.float32)

    @staticmethod
    def _letterbox(frame_bgr: np.ndarray) -> tuple[np.ndarray, float, tuple[float, float]]:
        h, w = frame_bgr.shape[:2]
        ratio = min(_INPUT_SIZE / w, _INPUT_SIZE / h)
        nw, nh = round(w * ratio), round(h * ratio)
        pad_x, pad_y = (_INPUT_SIZE - nw) / 2, (_INPUT_SIZE - nh) / 2
        resized = cv2.resize(frame_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((_INPUT_SIZE, _INPUT_SIZE, 3), 114, dtype=np.uint8)
        top, left = round(pad_y - 0.1), round(pad_x - 0.1)
        canvas[top:top + nh, left:left + nw] = resized
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        blob = (rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[None]
        return blob, ratio, (left, top)
