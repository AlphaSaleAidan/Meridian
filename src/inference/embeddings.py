"""Vector embeddings for scraped content using sentence-transformers.
Creates searchable vector store so the swarm retrieves relevant context
instead of sending everything to the LLM."""

import json
import logging
import sqlite3
import struct
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("meridian.inference.embeddings")

DB_PATH = Path(__file__).parent.parent.parent / "data" / "vectors.db"
MODEL_NAME = "all-MiniLM-L6-v2"

_model = None


def get_model():
    global _model
    if _model is not None:
        return _model
    from sentence_transformers import SentenceTransformer
    logger.info(f"Loading embedding model: {MODEL_NAME}")
    _model = SentenceTransformer(MODEL_NAME)
    logger.info("Embedding model loaded")
    return _model


def _init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            source_key TEXT,
            title TEXT,
            content TEXT,
            domain_tags TEXT,
            word_count INTEGER,
            embedding BLOB,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_source ON documents(source_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_tags ON documents(domain_tags)")
    conn.commit()


def _encode_vector(vec: np.ndarray) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec.tolist())


def _decode_vector(blob: bytes) -> np.ndarray:
    n = len(blob) // 4
    return np.array(struct.unpack(f"{n}f", blob), dtype=np.float32)


def embed_text(text: str) -> np.ndarray:
    model = get_model()
    return model.encode(text, normalize_embeddings=True)


def embed_and_store(doc_id: str, source_key: str, title: str, content: str,
                    domain_tags: list[str], word_count: int):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    _init_db(conn)

    preview = content[:2000]
    vec = embed_text(preview)

    conn.execute(
        """INSERT OR REPLACE INTO documents
           (id, source_key, title, content, domain_tags, word_count, embedding)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (doc_id, source_key, title, content[:10000], json.dumps(domain_tags),
         word_count, _encode_vector(vec)),
    )
    conn.commit()
    conn.close()


def search(query: str, limit: int = 5, source_filter: Optional[str] = None,
           tag_filter: Optional[str] = None) -> list[dict]:
    if not DB_PATH.exists():
        return []

    query_vec = embed_text(query)
    conn = sqlite3.connect(str(DB_PATH))
    _init_db(conn)

    where_clauses = []
    params = []
    if source_filter:
        where_clauses.append("source_key = ?")
        params.append(source_filter)
    if tag_filter:
        where_clauses.append("domain_tags LIKE ?")
        params.append(f"%{tag_filter}%")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    rows = conn.execute(
        f"SELECT id, source_key, title, content, domain_tags, word_count, embedding FROM documents {where_sql}",
        params,
    ).fetchall()

    results = []
    for row in rows:
        doc_vec = _decode_vector(row[6])
        score = float(np.dot(query_vec, doc_vec))
        results.append({
            "id": row[0],
            "source_key": row[1],
            "title": row[2],
            "content": row[3][:500],
            "domain_tags": json.loads(row[4]),
            "word_count": row[5],
            "score": round(score, 4),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    conn.close()
    return results[:limit]


_RAG_PRINCIPLE_PREAMBLE = (
    "The following context contains business principles extracted from "
    "published sources. Use ONLY the actionable financial and operational "
    "principles — do NOT adopt the author's voice, personality, investment "
    "philosophy, or writing style. Restate principles as direct, practical "
    "advice for the specific merchant being analyzed."
)


def get_context_for_prompt(query: str, max_tokens: int = 2000, limit: int = 3) -> str:
    """Retrieve relevant context from vector store for RAG.

    Book/author content is prefixed with a depersonalization instruction
    so the swarm extracts principles without absorbing author voice.
    """
    from .principle_filter import needs_filtering

    docs = search(query, limit=limit)
    if not docs:
        return ""

    has_author_content = any(
        needs_filtering(doc["source_key"]) for doc in docs
    )

    context_parts = []
    token_est = 0

    if has_author_content:
        context_parts.append(_RAG_PRINCIPLE_PREAMBLE)
        token_est += len(_RAG_PRINCIPLE_PREAMBLE.split()) * 1.3

    for doc in docs:
        chunk = f"[{doc['source_key']}] {doc['title']}\n{doc['content']}"
        chunk_tokens = len(chunk.split()) * 1.3
        if token_est + chunk_tokens > max_tokens:
            break
        context_parts.append(chunk)
        token_est += chunk_tokens

    return "\n\n---\n\n".join(context_parts)


def ingest_scraper_output(data_dir: Path):
    """Bulk ingest all scraped JSON files into vector store.

    Book/author/financial-expert content is run through the principle
    extraction filter before embedding — we want actionable business
    principles, not the author's voice or investment philosophy.
    """
    from .principle_filter import filter_for_embedding

    count = 0
    filtered_count = 0
    for json_file in data_dir.glob("*.json"):
        if json_file.name == "manifest.json":
            continue
        try:
            doc = json.loads(json_file.read_text())
            meta = doc.get("metadata", {})
            source_key = doc.get("source_key", meta.get("source_key", "unknown"))
            source_type = doc.get("source_type", meta.get("source_type", ""))
            raw_content = doc.get("content", "")
            title = doc.get("title", "Untitled")

            content = filter_for_embedding(
                raw_content, source_key, source_type, title,
            )
            if content != raw_content:
                filtered_count += 1

            embed_and_store(
                doc_id=doc.get("id", json_file.stem),
                source_key=source_key,
                title=title,
                content=content,
                domain_tags=meta.get("domain_tags", doc.get("topics", [])),
                word_count=meta.get("word_count", doc.get("word_count", 0)),
            )
            count += 1
        except Exception as e:
            logger.warning(f"Failed to ingest {json_file.name}: {e}")

    logger.info(
        f"Ingested {count} documents into vector store "
        f"({filtered_count} principle-filtered)"
    )
    return count


def stats() -> dict:
    if not DB_PATH.exists():
        return {"documents": 0, "sources": [], "db_size_mb": 0}
    conn = sqlite3.connect(str(DB_PATH))
    _init_db(conn)
    total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    sources = [r[0] for r in conn.execute("SELECT DISTINCT source_key FROM documents").fetchall()]
    conn.close()
    size_mb = round(DB_PATH.stat().st_size / 1024 / 1024, 2)
    return {"documents": total, "sources": sources, "db_size_mb": size_mb}
