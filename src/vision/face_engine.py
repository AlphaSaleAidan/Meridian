"""
FaceEngine — Dual-engine face recognition + demographics.

Primary: InsightFace ArcFace (buffalo_l) for 512-dim embeddings.
  - match_embedding() → known_customer | returning_anonymous | new_face
Secondary: DeepFace for demographics (age, gender, emotion).

All face data stays on-prem. Only hashed visitor IDs go to cloud.
"""
import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

logger = logging.getLogger("meridian.vision.face")


class MatchResult(Enum):
    KNOWN_CUSTOMER = "known_customer"
    RETURNING_ANONYMOUS = "returning_anonymous"
    NEW_FACE = "new_face"


@dataclass
class FaceRecord:
    embedding: np.ndarray
    embedding_hash: str
    match_type: MatchResult
    age_range: str = ""
    gender: str = ""
    emotion: str = ""
    confidence: float = 0.0
    track_id: int | None = None


@dataclass
class FaceIndex:
    """On-prem face embedding index — never leaves merchant hardware."""
    embeddings: list[np.ndarray] = field(default_factory=list)
    hashes: list[str] = field(default_factory=list)
    visit_counts: list[int] = field(default_factory=list)
    metadata: list[dict] = field(default_factory=list)

    def add(self, embedding: np.ndarray, meta: dict | None = None) -> str:
        h = _hash_embedding(embedding)
        self.embeddings.append(embedding)
        self.hashes.append(h)
        self.visit_counts.append(1)
        self.metadata.append(meta or {})
        return h

    def search(self, embedding: np.ndarray, threshold: float = 0.4) -> tuple[int, float] | None:
        if not self.embeddings:
            return None
        query = embedding / (np.linalg.norm(embedding) + 1e-8)
        best_idx = -1
        best_sim = -1.0
        for i, stored in enumerate(self.embeddings):
            normed = stored / (np.linalg.norm(stored) + 1e-8)
            sim = float(np.dot(query, normed))
            if sim > best_sim:
                best_sim = sim
                best_idx = i
        if best_sim >= threshold:
            return best_idx, best_sim
        return None

    def increment_visits(self, idx: int):
        if 0 <= idx < len(self.visit_counts):
            self.visit_counts[idx] += 1

    @property
    def size(self) -> int:
        return len(self.embeddings)


def _hash_embedding(embedding: np.ndarray) -> str:
    raw = embedding.astype(np.float32).tobytes()
    return hashlib.sha256(raw).hexdigest()[:32]


class FaceEngine:
    SIMILARITY_THRESHOLD = 0.4
    RECOGNITION_INTERVAL_SEC = 5

    def __init__(
        self,
        model_name: str = "buffalo_l",
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        enable_demographics: bool = True,
    ):
        self._model_name = model_name
        self._threshold = similarity_threshold
        self._enable_demographics = enable_demographics
        self._insight_app = None
        self._deepface_loaded = False
        self._index = FaceIndex()
        self._last_recognition: dict[int, float] = {}

    def _load_insightface(self):
        if self._insight_app is not None:
            return
        try:
            import insightface
            self._insight_app = insightface.app.FaceAnalysis(
                name=self._model_name,
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )
            self._insight_app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("InsightFace loaded: %s", self._model_name)
        except ImportError:
            logger.error("insightface not installed — run: pip install insightface onnxruntime-gpu")
            raise

    def _should_recognize(self, track_id: int) -> bool:
        now = time.time()
        last = self._last_recognition.get(track_id, 0)
        if now - last >= self.RECOGNITION_INTERVAL_SEC:
            self._last_recognition[track_id] = now
            return True
        return False

    def get_embeddings(self, frame: np.ndarray) -> list[tuple[np.ndarray, tuple]]:
        self._load_insightface()
        faces = self._insight_app.get(frame)
        results = []
        for face in faces:
            if face.embedding is not None:
                bbox = tuple(face.bbox.astype(int).tolist())
                results.append((face.embedding, bbox))
        return results

    def match_embedding(self, embedding: np.ndarray) -> tuple[MatchResult, str, float]:
        result = self._index.search(embedding, self._threshold)
        if result is not None:
            idx, sim = result
            self._index.increment_visits(idx)
            h = self._index.hashes[idx]
            visits = self._index.visit_counts[idx]
            if visits >= 2:
                return MatchResult.RETURNING_ANONYMOUS, h, sim
            return MatchResult.RETURNING_ANONYMOUS, h, sim
        h = self._index.add(embedding)
        return MatchResult.NEW_FACE, h, 0.0

    def analyze_demographics(self, frame: np.ndarray, bbox: tuple) -> dict:
        if not self._enable_demographics:
            return {}
        try:
            from deepface import DeepFace
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 - x1 < 20 or y2 - y1 < 20:
                return {}
            face_crop = frame[y1:y2, x1:x2]
            analysis = DeepFace.analyze(
                face_crop,
                actions=["age", "gender", "emotion"],
                enforce_detection=False,
                silent=True,
            )
            if isinstance(analysis, list):
                analysis = analysis[0]
            age = analysis.get("age", 0)
            gender = analysis.get("dominant_gender", "")
            emotion = analysis.get("dominant_emotion", "")
            if age < 18:
                age_range = "under_18"
            elif age < 25:
                age_range = "18-24"
            elif age < 35:
                age_range = "25-34"
            elif age < 45:
                age_range = "35-44"
            elif age < 55:
                age_range = "45-54"
            else:
                age_range = "55+"
            return {
                "age_range": age_range,
                "gender_est": gender[:1].upper() if gender else "",
                "dominant_emotion": emotion,
            }
        except ImportError:
            logger.debug("deepface not installed — demographics unavailable")
            return {}
        except Exception as e:
            logger.debug("Demographics analysis failed: %s", e)
            return {}

    def process_frame(
        self, frame: np.ndarray, tracks: list, compliance_mode: str = "anonymous"
    ) -> list[FaceRecord]:
        if compliance_mode == "disabled":
            return []
        if compliance_mode == "anonymous":
            return []

        results = []
        face_data = self.get_embeddings(frame)

        for embedding, face_bbox in face_data:
            matched_track = None
            for track in tracks:
                tx1, ty1, tx2, ty2 = track.bbox
                fx1, fy1 = face_bbox[0], face_bbox[1]
                if tx1 <= fx1 <= tx2 and ty1 <= fy1 <= ty2:
                    matched_track = track
                    break

            if matched_track and not self._should_recognize(matched_track.track_id):
                continue

            match_type, emb_hash, sim = self.match_embedding(embedding)

            demo = {}
            if self._enable_demographics:
                demo = self.analyze_demographics(frame, face_bbox)

            results.append(FaceRecord(
                embedding=embedding,
                embedding_hash=emb_hash,
                match_type=match_type,
                age_range=demo.get("age_range", ""),
                gender=demo.get("gender_est", ""),
                emotion=demo.get("dominant_emotion", ""),
                confidence=sim,
                track_id=matched_track.track_id if matched_track else None,
            ))

        return results

    @property
    def index_size(self) -> int:
        return self._index.size

    def delete_embedding(self, embedding_hash: str) -> bool:
        """Right-to-forget: delete all data for a specific embedding."""
        for i, h in enumerate(self._index.hashes):
            if h == embedding_hash:
                self._index.embeddings.pop(i)
                self._index.hashes.pop(i)
                self._index.visit_counts.pop(i)
                self._index.metadata.pop(i)
                return True
        return False

    def purge_expired(self, max_age_sec: float = 90 * 86400) -> int:
        """Auto-purge embeddings older than retention period (default 90 days)."""
        now = time.time()
        purged = 0
        i = 0
        while i < len(self._index.metadata):
            created = self._index.metadata[i].get("created_at", now)
            if now - created > max_age_sec:
                self._index.embeddings.pop(i)
                self._index.hashes.pop(i)
                self._index.visit_counts.pop(i)
                self._index.metadata.pop(i)
                purged += 1
            else:
                i += 1
        return purged
