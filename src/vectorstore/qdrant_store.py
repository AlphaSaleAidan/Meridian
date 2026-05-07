"""
Qdrant vector store for Meridian AI training data and pattern search.

Uses qdrant-client to store/search embeddings for:
  - Camera detection patterns (person tracks, dwell zones)
  - Agent insight embeddings (for similarity search across merchants)
  - Training data for fine-tuning detection models
"""
import logging
import math
import os
from typing import Any

logger = logging.getLogger("meridian.vectorstore")

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
COLLECTION_PREFIX = os.environ.get("QDRANT_COLLECTION_PREFIX", "meridian")


class MeridianVectorStore:
    """Qdrant-backed vector store with graceful fallback to in-memory."""

    def __init__(self, collection_suffix: str = "default", vector_size: int = 384):
        self.collection_name = f"{COLLECTION_PREFIX}_{collection_suffix}"
        self.vector_size = vector_size
        self._client = None
        self._fallback_store: list[dict] = []
        self._init_client()

    def _init_client(self):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            self._client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            collections = [c.name for c in self._client.get_collections().collections]
            if self.collection_name not in collections:
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Using existing Qdrant collection: {self.collection_name}")
        except ImportError:
            logger.warning("qdrant-client not installed — using in-memory fallback")
            self._client = None
        except Exception as e:
            logger.warning(f"Qdrant connection failed ({e}) — using in-memory fallback")
            self._client = None

    def upsert(self, point_id: str, vector: list[float], payload: dict[str, Any] | None = None):
        if self._client:
            from qdrant_client.models import PointStruct

            self._client.upsert(
                collection_name=self.collection_name,
                points=[PointStruct(id=point_id, vector=vector, payload=payload or {})],
            )
        else:
            self._fallback_store.append({"id": point_id, "vector": vector, "payload": payload or {}})

    def upsert_batch(self, points: list[dict]):
        """Batch upsert. Each dict: {id, vector, payload}."""
        if self._client:
            from qdrant_client.models import PointStruct

            structs = [
                PointStruct(id=p["id"], vector=p["vector"], payload=p.get("payload", {}))
                for p in points
            ]
            self._client.upsert(collection_name=self.collection_name, points=structs)
        else:
            self._fallback_store.extend(points)

    def search(
        self, query_vector: list[float], limit: int = 10, score_threshold: float = 0.5
    ) -> list[dict]:
        if self._client:
            results = self._client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )
            return [{"id": r.id, "score": r.score, "payload": r.payload} for r in results]
        return self._fallback_search(query_vector, limit, score_threshold)

    def _fallback_search(
        self, query_vector: list[float], limit: int, threshold: float
    ) -> list[dict]:
        """Cosine similarity search over in-memory store."""
        scored = []
        for item in self._fallback_store:
            v = item["vector"]
            dot = sum(a * b for a, b in zip(query_vector, v))
            mag_a = math.sqrt(sum(x * x for x in query_vector))
            mag_b = math.sqrt(sum(x * x for x in v))
            score = dot / (mag_a * mag_b) if mag_a > 0 and mag_b > 0 else 0
            if score >= threshold:
                scored.append({"id": item["id"], "score": score, "payload": item.get("payload", {})})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def delete(self, point_ids: list[str]):
        if self._client:
            self._client.delete(
                collection_name=self.collection_name, points_selector=point_ids
            )
        else:
            self._fallback_store = [p for p in self._fallback_store if p["id"] not in point_ids]

    def count(self) -> int:
        if self._client:
            return self._client.count(collection_name=self.collection_name).count
        return len(self._fallback_store)

    @property
    def is_connected(self) -> bool:
        return self._client is not None
