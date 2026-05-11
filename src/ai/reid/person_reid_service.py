"""
Person Re-Identification Service — Cross-camera person matching.

Uses FastReID appearance embeddings when available, falls back to
tracker_id-only matching (single-camera) when it's not installed.

Gallery stores (person_id → embedding) pairs in memory. Matching uses
cosine similarity with a configurable threshold.
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

logger = logging.getLogger("meridian.ai.reid")

_fastreid_available = False
_fastreid_predictor = None

try:
    from fastreid.config import get_cfg
    from fastreid.engine import DefaultPredictor
    _fastreid_available = True
except ImportError:
    import sys
    from pathlib import Path
    _vendor = Path(__file__).resolve().parents[3] / "vendor" / "fast-reid"
    if _vendor.is_dir() and str(_vendor) not in sys.path:
        sys.path.insert(0, str(_vendor))
        try:
            from fastreid.config import get_cfg
            from fastreid.engine import DefaultPredictor
            _fastreid_available = True
        except ImportError:
            pass

MATCH_THRESHOLD = 0.65
GALLERY_MAX_SIZE = 2000
EMBEDDING_DIM = 2048


@dataclass
class PersonSighting:
    person_id: str
    camera_id: str
    tracker_id: int
    bbox: list[float]
    zone: str | None
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    embedding: np.ndarray | None = None


class PersonReIDService:

    def __init__(self, model_config: str | None = None, threshold: float = MATCH_THRESHOLD):
        self._threshold = threshold
        self._gallery: dict[str, np.ndarray] = {}
        self._tracker_to_person: dict[str, str] = {}
        self._person_sightings: dict[str, list[PersonSighting]] = {}
        self._predictor = None

        if _fastreid_available and model_config:
            try:
                cfg = get_cfg()
                cfg.merge_from_file(model_config)
                cfg.MODEL.WEIGHTS = model_config.replace(".yaml", ".pth")
                cfg.freeze()
                self._predictor = DefaultPredictor(cfg)
                logger.info("FastReID predictor loaded")
            except Exception as e:
                logger.warning(f"FastReID init failed, using tracker-only mode: {e}")

    @property
    def has_reid(self) -> bool:
        return self._predictor is not None

    def process_detections(
        self,
        detections: list[dict[str, Any]],
        camera_id: str,
        frame: np.ndarray | None = None,
    ) -> list[PersonSighting]:
        """Match detections to known persons or create new ones."""
        sightings = []

        for det in detections:
            tracker_id = det["tracker_id"]
            bbox = det["bbox"]
            zone = det.get("zone")
            conf = det.get("confidence", 0.5)

            embedding = None
            if self._predictor is not None and frame is not None:
                embedding = self._extract_embedding(frame, bbox)

            person_id = self._match_or_create(camera_id, tracker_id, embedding)

            sighting = PersonSighting(
                person_id=person_id,
                camera_id=camera_id,
                tracker_id=tracker_id,
                bbox=bbox,
                zone=zone,
                confidence=conf,
                embedding=embedding,
            )
            sightings.append(sighting)

            if person_id not in self._person_sightings:
                self._person_sightings[person_id] = []
            self._person_sightings[person_id].append(sighting)

        return sightings

    def get_person_history(self, person_id: str) -> list[PersonSighting]:
        return self._person_sightings.get(person_id, [])

    def get_active_persons(self) -> list[str]:
        return list(self._person_sightings.keys())

    def gallery_size(self) -> int:
        return len(self._gallery)

    def clear_stale(self, max_age_seconds: int = 3600):
        """Remove persons not seen within max_age_seconds."""
        now = datetime.now(timezone.utc)
        stale = []
        for pid, sightings in self._person_sightings.items():
            if not sightings:
                stale.append(pid)
                continue
            last_seen = max(s.timestamp for s in sightings)
            if (now - last_seen).total_seconds() > max_age_seconds:
                stale.append(pid)

        for pid in stale:
            self._person_sightings.pop(pid, None)
            self._gallery.pop(pid, None)

        keys_to_remove = [k for k, v in self._tracker_to_person.items() if v in stale]
        for k in keys_to_remove:
            del self._tracker_to_person[k]

        if stale:
            logger.debug(f"Cleared {len(stale)} stale persons from gallery")

    def _match_or_create(
        self, camera_id: str, tracker_id: int, embedding: np.ndarray | None
    ) -> str:
        tracker_key = f"{camera_id}:{tracker_id}"

        if tracker_key in self._tracker_to_person:
            person_id = self._tracker_to_person[tracker_key]
            if embedding is not None and person_id in self._gallery:
                self._gallery[person_id] = 0.9 * self._gallery[person_id] + 0.1 * embedding
            return person_id

        if embedding is not None and self._gallery:
            match_id, score = self._find_best_match(embedding)
            if match_id and score >= self._threshold:
                self._tracker_to_person[tracker_key] = match_id
                self._gallery[match_id] = 0.9 * self._gallery[match_id] + 0.1 * embedding
                logger.debug(f"ReID match: tracker {tracker_key} → {match_id} (score={score:.3f})")
                return match_id

        person_id = f"p-{uuid.uuid4().hex[:12]}"
        self._tracker_to_person[tracker_key] = person_id
        if embedding is not None:
            if len(self._gallery) >= GALLERY_MAX_SIZE:
                oldest = next(iter(self._gallery))
                del self._gallery[oldest]
            self._gallery[person_id] = embedding

        return person_id

    def _find_best_match(self, embedding: np.ndarray) -> tuple[str | None, float]:
        best_id = None
        best_score = -1.0

        query_norm = embedding / (np.linalg.norm(embedding) + 1e-8)

        for pid, gallery_emb in self._gallery.items():
            gallery_norm = gallery_emb / (np.linalg.norm(gallery_emb) + 1e-8)
            score = float(np.dot(query_norm, gallery_norm))
            if score > best_score:
                best_score = score
                best_id = pid

        return best_id, best_score

    def _extract_embedding(self, frame: np.ndarray, bbox: list[float]) -> np.ndarray | None:
        try:
            x1, y1, x2, y2 = [int(c) for c in bbox]
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            if x2 - x1 < 10 or y2 - y1 < 10:
                return None

            crop = frame[y1:y2, x1:x2]
            outputs = self._predictor(crop)
            return outputs.cpu().numpy().flatten()
        except Exception as e:
            logger.debug(f"Embedding extraction failed: {e}")
            return None
