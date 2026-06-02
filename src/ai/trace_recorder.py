"""
Trace recorder — minimal SQLite tee for swarm baseline instrumentation.

Records one row per agent invocation or LLM call into
``data/swarm_traces.sqlite`` (table ``swarm_traces``, schema in
``migrations/2026-06-02-swarm_traces.sql``).

Design goals:
  * stdlib only (sqlite3, time, uuid, contextlib, logging, threading, pathlib);
  * lazy import + lazy connect — first call applies the schema;
  * safe no-op if the DB is unreachable or the schema apply fails;
  * "few ms" overhead on the happy path (single INSERT, indexed table);
  * thread-safe enough for asyncio.gather fanout (uses one connection per
    thread, and ``check_same_thread=False``).

Public API:
  * ``record(...)`` — fire-and-forget single-row insert.
  * ``trace(...)`` — context manager that auto-times the block and records
    success/failure based on whether the block raised.
  * ``new_trace_id()`` — uuid helper so callers can correlate rows.
  * ``set_db_path(path)`` — override default for tests / scripts.

This module MUST stay under 300 lines.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger("meridian.ai.trace_recorder")

# ---------------------------------------------------------------------------
# Paths / configuration
# ---------------------------------------------------------------------------

_DEFAULT_DB_PATH = Path(
    os.environ.get(
        "MERIDIAN_SWARM_TRACE_DB",
        str(Path(__file__).resolve().parent.parent.parent / "data" / "swarm_traces.sqlite"),
    )
)
_MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "migrations"
    / "2026-06-02-swarm_traces.sql"
)

# Set to True after we have successfully applied the schema once.
_schema_ready = False
_schema_lock = threading.Lock()

# Per-thread connection cache. SQLite connections are not safe to share across
# threads with check_same_thread=True; we set it False but still keep one per
# thread to avoid serializing every write through a global lock.
_tls = threading.local()


def set_db_path(path: str | os.PathLike) -> None:
    """Override the trace DB path. Resets connection + schema state."""
    global _DEFAULT_DB_PATH, _schema_ready
    _DEFAULT_DB_PATH = Path(path)
    with _schema_lock:
        _schema_ready = False
    # Drop any cached connection on this thread.
    if hasattr(_tls, "conn"):
        try:
            _tls.conn.close()
        except Exception:
            pass
        del _tls.conn


def get_db_path() -> Path:
    return _DEFAULT_DB_PATH


def new_trace_id() -> str:
    """Generate a fresh trace id. Callers can pass this to correlate rows."""
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Connection / schema
# ---------------------------------------------------------------------------


def _apply_schema(conn: sqlite3.Connection) -> None:
    """Apply the swarm_traces DDL. Prefers the canonical migration file
    so the writer and the migration cannot drift."""
    if _MIGRATION_PATH.exists():
        try:
            sql = _MIGRATION_PATH.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.commit()
            return
        except Exception as exc:  # pragma: no cover — fall through to inline
            logger.debug("Could not apply migration file (%s); using inline DDL", exc)

    # Inline fallback — keep this identical to the .sql file.
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS swarm_traces (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id          TEXT NOT NULL,
            agent_name        TEXT NOT NULL,
            tier              TEXT,
            provider          TEXT,
            model             TEXT,
            prompt_tokens     INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            latency_ms        INTEGER DEFAULT 0,
            escalated_from    TEXT,
            success           INTEGER NOT NULL DEFAULT 1,
            task_kind         TEXT,
            error             TEXT,
            created_at        TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_swarm_traces_agent   ON swarm_traces(agent_name);
        CREATE INDEX IF NOT EXISTS idx_swarm_traces_trace   ON swarm_traces(trace_id);
        CREATE INDEX IF NOT EXISTS idx_swarm_traces_kind    ON swarm_traces(task_kind);
        CREATE INDEX IF NOT EXISTS idx_swarm_traces_created ON swarm_traces(created_at);
        """
    )
    conn.commit()


def _get_conn() -> sqlite3.Connection | None:
    """Return a sqlite3 connection for this thread, applying schema once.
    Returns None if the DB cannot be opened — callers should treat that as
    a no-op (the recorder is safe to fail)."""
    global _schema_ready

    conn = getattr(_tls, "conn", None)
    if conn is not None:
        return conn

    try:
        _DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            _DEFAULT_DB_PATH,
            timeout=5.0,
            check_same_thread=False,
            isolation_level=None,  # autocommit; each INSERT is its own txn
        )
    except Exception as exc:
        logger.debug("trace_recorder: could not open %s (%s) — disabling", _DEFAULT_DB_PATH, exc)
        return None

    with _schema_lock:
        if not _schema_ready:
            try:
                _apply_schema(conn)
                _schema_ready = True
            except Exception as exc:
                logger.debug("trace_recorder: schema apply failed (%s) — disabling", exc)
                try:
                    conn.close()
                except Exception:
                    pass
                return None

    _tls.conn = conn
    return conn


# ---------------------------------------------------------------------------
# Public write API
# ---------------------------------------------------------------------------


def record(
    *,
    trace_id: str | None = None,
    agent_name: str,
    task_kind: str = "agent_run",
    latency_ms: int = 0,
    success: bool = True,
    tier: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    escalated_from: str | None = None,
    error: str | None = None,
) -> None:
    """Insert one row into ``swarm_traces``. Never raises."""
    conn = _get_conn()
    if conn is None:
        return
    try:
        conn.execute(
            """
            INSERT INTO swarm_traces (
                trace_id, agent_name, tier, provider, model,
                prompt_tokens, completion_tokens, latency_ms,
                escalated_from, success, task_kind, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace_id or new_trace_id(),
                agent_name,
                tier,
                provider,
                model,
                int(prompt_tokens or 0),
                int(completion_tokens or 0),
                int(latency_ms or 0),
                escalated_from,
                1 if success else 0,
                task_kind,
                (error or None) if not success else None,
            ),
        )
    except Exception as exc:  # never escalate to the caller
        logger.debug("trace_recorder.record failed: %s", exc)


@contextmanager
def trace(
    *,
    agent_name: str,
    task_kind: str = "agent_run",
    trace_id: str | None = None,
    tier: str | None = None,
) -> Iterator["TraceHandle"]:
    """Context manager that records a single row on exit, timing the block.

    Usage::

        with trace(agent_name="ForecasterAgent") as t:
            result = await agent.analyze()
            t.set(prompt_tokens=..., completion_tokens=...)

    On exception, ``success=False`` and ``error=str(exc)`` are recorded and
    the exception is re-raised.
    """
    handle = TraceHandle(
        trace_id=trace_id or new_trace_id(),
        agent_name=agent_name,
        task_kind=task_kind,
        tier=tier,
    )
    start = time.perf_counter()
    try:
        yield handle
    except Exception as exc:
        handle.success = False
        handle.error = repr(exc)[:500]
        raise
    finally:
        handle.latency_ms = int((time.perf_counter() - start) * 1000)
        record(
            trace_id=handle.trace_id,
            agent_name=handle.agent_name,
            task_kind=handle.task_kind,
            latency_ms=handle.latency_ms,
            success=handle.success,
            tier=handle.tier,
            provider=handle.provider,
            model=handle.model,
            prompt_tokens=handle.prompt_tokens,
            completion_tokens=handle.completion_tokens,
            escalated_from=handle.escalated_from,
            error=handle.error,
        )


class TraceHandle:
    """Mutable fields populated inside a ``trace()`` block."""

    __slots__ = (
        "trace_id", "agent_name", "task_kind", "tier",
        "provider", "model", "prompt_tokens", "completion_tokens",
        "escalated_from", "success", "error", "latency_ms",
    )

    def __init__(self, *, trace_id: str, agent_name: str, task_kind: str, tier: str | None) -> None:
        self.trace_id = trace_id
        self.agent_name = agent_name
        self.task_kind = task_kind
        self.tier = tier
        self.provider: str | None = None
        self.model: str | None = None
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.escalated_from: str | None = None
        self.success: bool = True
        self.error: str | None = None
        self.latency_ms: int = 0

    def set(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
