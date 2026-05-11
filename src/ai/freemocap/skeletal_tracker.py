"""
FreeMoCap Skeletal Tracker — 3D pose estimation integration.

Uses skellytracker (from FreeMoCap project) when available for
markerless motion capture. Detects gestures like reaching, bending,
pointing, and browsing postures that correlate with purchase intent.

Falls back to a no-op tracker when skellytracker is not installed.
"""
import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

logger = logging.getLogger("meridian.ai.freemocap")

_skelly_available = False
try:
    from skellytracker import CameraConfig, SkellyCam
    _skelly_available = True
except ImportError:
    pass

GESTURE_LABELS = {
    "reaching": "Person reaching for product on shelf",
    "browsing": "Person leaning in to examine products",
    "pointing": "Person pointing at display or product",
    "carrying": "Person carrying items",
    "waiting": "Person standing still (likely in queue)",
    "walking": "Person in transit between zones",
}

SHOULDER_IDX = (11, 12)
WRIST_IDX = (15, 16)
HIP_IDX = (23, 24)
ANKLE_IDX = (27, 28)


class SkeletalTracker:

    def __init__(self):
        self._available = _skelly_available
        if self._available:
            logger.info("FreeMoCap skellytracker available — skeletal tracking enabled")
        else:
            logger.debug("skellytracker not installed — skeletal features disabled")

    @property
    def is_available(self) -> bool:
        return self._available

    def estimate_pose(self, frame: np.ndarray) -> dict[str, Any] | None:
        """Extract 2D/3D pose landmarks from a frame."""
        if not self._available:
            return None

        try:
            from skellytracker.trackers.mediapipe_tracker.mediapipe_holistic_tracker import (
                MediapipeHolisticTracker,
            )
            tracker = MediapipeHolisticTracker()
            result = tracker.process_image(frame)
            if result is None or result.body_landmarks is None:
                return None

            landmarks = {}
            for idx, lm in enumerate(result.body_landmarks):
                landmarks[str(idx)] = [float(lm.x), float(lm.y), float(lm.z)]

            return {
                "landmarks": landmarks,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "num_landmarks": len(landmarks),
            }
        except Exception as e:
            logger.debug(f"Pose estimation failed: {e}")
            return None

    def classify_gesture(self, landmarks: dict[str, list[float]]) -> tuple[str, float]:
        """Classify body gesture from pose landmarks."""
        if not landmarks or len(landmarks) < 25:
            return "unknown", 0.0

        try:
            l_shoulder = np.array(landmarks.get("11", [0, 0, 0]))
            r_shoulder = np.array(landmarks.get("12", [0, 0, 0]))
            l_wrist = np.array(landmarks.get("15", [0, 0, 0]))
            r_wrist = np.array(landmarks.get("16", [0, 0, 0]))
            l_hip = np.array(landmarks.get("23", [0, 0, 0]))
            r_hip = np.array(landmarks.get("24", [0, 0, 0]))
            l_ankle = np.array(landmarks.get("27", [0, 0, 0]))
            r_ankle = np.array(landmarks.get("28", [0, 0, 0]))

            shoulder_y = (l_shoulder[1] + r_shoulder[1]) / 2
            hip_y = (l_hip[1] + r_hip[1]) / 2
            wrist_y = min(l_wrist[1], r_wrist[1])
            ankle_y = (l_ankle[1] + r_ankle[1]) / 2

            wrist_above_shoulder = wrist_y < shoulder_y - 0.05
            torso_lean = abs(shoulder_y - hip_y)
            ankle_still = np.linalg.norm(l_ankle - r_ankle) < 0.15

            if wrist_above_shoulder:
                return "reaching", 0.75

            l_wrist_forward = l_wrist[2] < l_shoulder[2] - 0.1
            r_wrist_forward = r_wrist[2] < r_shoulder[2] - 0.1
            if l_wrist_forward or r_wrist_forward:
                if torso_lean > 0.1:
                    return "browsing", 0.65
                return "pointing", 0.60

            wrist_below_hip = min(l_wrist[1], r_wrist[1]) > hip_y + 0.1
            if wrist_below_hip:
                return "carrying", 0.55

            if ankle_still and torso_lean < 0.05:
                return "waiting", 0.70

            return "walking", 0.50
        except Exception:
            return "unknown", 0.0

    def process_frame_for_person(
        self, frame: np.ndarray, bbox: list[float]
    ) -> dict[str, Any] | None:
        """Extract pose and gesture for a single detected person crop."""
        if not self._available:
            return None

        try:
            x1, y1, x2, y2 = [int(c) for c in bbox]
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 - x1 < 30 or y2 - y1 < 60:
                return None

            crop = frame[y1:y2, x1:x2]
            pose = self.estimate_pose(crop)
            if not pose:
                return None

            gesture, gesture_conf = self.classify_gesture(pose["landmarks"])
            return {
                "landmarks": pose["landmarks"],
                "gesture": gesture,
                "gesture_confidence": gesture_conf,
                "gesture_label": GESTURE_LABELS.get(gesture, ""),
                "timestamp": pose["timestamp"],
            }
        except Exception as e:
            logger.debug(f"Person pose extraction failed: {e}")
            return None
