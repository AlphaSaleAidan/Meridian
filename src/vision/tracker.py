"""
PersonTracker — BoxMOT multi-object tracking.

Assigns a persistent track_id to each person across frames so
downstream analytics (dwell time, zone crossing, re-identification)
operate on stable identities rather than per-frame detections.
"""
import logging
import time
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger("meridian.vision.tracker")


@dataclass
class Track:
    track_id: int
    bbox: tuple[float, float, float, float]
    confidence: float
    age_frames: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    @property
    def center(self) -> tuple[float, float]:
        return (
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2,
        )

    @property
    def duration_sec(self) -> float:
        return self.last_seen - self.first_seen


class PersonTracker:
    DEFAULT_TRACKER = "deepocsort"

    def __init__(self, tracker_type: str = DEFAULT_TRACKER, device: str = "auto"):
        self._tracker_type = tracker_type
        self._device = device
        self._tracker = None
        self._track_registry: dict[int, Track] = {}

    def _load_tracker(self):
        if self._tracker is not None:
            return
        try:
            from boxmot import DeepOCSORT
            self._tracker = DeepOCSORT(
                device="cuda:0" if self._device == "auto" else self._device,
                fp16=True,
            )
            logger.info("BoxMOT tracker loaded: %s", self._tracker_type)
        except ImportError:
            logger.warning("boxmot not installed — using naive ID tracker fallback")
            self._tracker = _NaiveTracker()

    def update(self, detections: list, frame: np.ndarray) -> list[Track]:
        self._load_tracker()
        now = time.time()

        if not detections:
            return []

        dets_array = np.array([
            [d.bbox[0], d.bbox[1], d.bbox[2], d.bbox[3], d.confidence, 0]
            for d in detections
        ], dtype=np.float32)

        if isinstance(self._tracker, _NaiveTracker):
            tracked = self._tracker.update(dets_array)
        else:
            tracked = self._tracker.update(dets_array, frame)

        active_tracks = []
        for row in tracked:
            x1, y1, x2, y2 = float(row[0]), float(row[1]), float(row[2]), float(row[3])
            track_id = int(row[4])
            conf = float(row[5]) if len(row) > 5 else 0.5

            if track_id in self._track_registry:
                t = self._track_registry[track_id]
                t.bbox = (x1, y1, x2, y2)
                t.confidence = conf
                t.age_frames += 1
                t.last_seen = now
            else:
                t = Track(
                    track_id=track_id,
                    bbox=(x1, y1, x2, y2),
                    confidence=conf,
                    first_seen=now,
                    last_seen=now,
                )
                self._track_registry[track_id] = t
            active_tracks.append(t)

        return active_tracks

    def get_track(self, track_id: int) -> Track | None:
        return self._track_registry.get(track_id)

    def get_active_tracks(self, max_age_sec: float = 30.0) -> list[Track]:
        now = time.time()
        return [
            t for t in self._track_registry.values()
            if now - t.last_seen < max_age_sec
        ]

    def get_completed_tracks(self, min_duration_sec: float = 2.0) -> list[Track]:
        now = time.time()
        return [
            t for t in self._track_registry.values()
            if now - t.last_seen >= 30.0 and t.duration_sec >= min_duration_sec
        ]

    def reset(self):
        self._track_registry.clear()
        self._tracker = None

    @property
    def total_tracked(self) -> int:
        return len(self._track_registry)


class _NaiveTracker:
    """Fallback when boxmot is not installed — simple centroid matching."""

    def __init__(self, max_dist: float = 80.0):
        self._max_dist = max_dist
        self._next_id = 1
        self._prev: list[tuple[int, float, float]] = []

    def update(self, dets: np.ndarray) -> np.ndarray:
        results = []
        new_prev = []
        used = set()

        for det in dets:
            cx = (det[0] + det[2]) / 2
            cy = (det[1] + det[3]) / 2
            best_id = None
            best_dist = self._max_dist

            for i, (tid, px, py) in enumerate(self._prev):
                if i in used:
                    continue
                d = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
                if d < best_dist:
                    best_dist = d
                    best_id = (i, tid)

            if best_id is not None:
                used.add(best_id[0])
                tid = best_id[1]
            else:
                tid = self._next_id
                self._next_id += 1

            results.append([det[0], det[1], det[2], det[3], tid, det[4]])
            new_prev.append((tid, cx, cy))

        self._prev = new_prev
        return np.array(results) if results else np.empty((0, 6))
