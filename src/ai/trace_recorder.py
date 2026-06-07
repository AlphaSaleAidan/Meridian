"""
Trace recorder — minimal SQLite tee for swarm baseline instrumentation.

One row per agent invocation or LLM call, written to ``data/swarm_traces.sqlite``
(table ``swarm_traces``, schema in ``migrations/2026-06-02-swarm_traces.sql``).

Design: stdlib only, lazy connect, safe no-op on failure. ``record()`` is
non-blocking — it enqueues into a bounded queue and returns immediately, so
the SQLite write never blocks the event loop. A daemon worker thread drains
the queue. On overflow the row is dropped (with a debug log), because the
recorder must never delay a realtime caller (e.g. the Pipecat phone agent).
An ``atexit`` hook flushes the queue before process death.

Public API: ``record(...)``, ``trace(...)`` (ctx mgr), ``new_trace_id()``,
``set_db_path(path)``, ``flush(timeout=None)``.
"""

from __future__ import annotations

import atexit
import logging
import os
import queue
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

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


# ---------------------------------------------------------------------------
# Background queue + worker — keeps record() non-blocking on the hot path.
# ---------------------------------------------------------------------------

# Bounded so a stuck disk can't grow memory unboundedly. The realtime contract
# is "never block"; if the queue is full we drop. 10k rows is generous for the
# Meridian workload (a full analyze_merchant fanout is ~80 rows).
_QUEUE_MAX = int(os.environ.get("MERIDIAN_TRACE_QUEUE_MAX", "10000"))
_QUEUE: queue.Queue = queue.Queue(maxsize=_QUEUE_MAX)
_WORKER: threading.Thread | None = None
_WORKER_LOCK = threading.Lock()
_DROPPED = 0  # observability for the dashboard later
_SENTINEL: tuple = ()


def _worker_loop() -> None:
    """Drain ``_QUEUE`` into SQLite. One worker, one connection per worker
    thread (via the existing ``_get_conn`` thread-local)."""
    while True:
        row = _QUEUE.get()
        if row is _SENTINEL:
            _QUEUE.task_done()
            return
        try:
            conn = _get_conn()
            if conn is not None:
                conn.execute(
                    """
                    INSERT INTO swarm_traces (
                        trace_id, agent_name, tier, provider, model,
                        prompt_tokens, completion_tokens, latency_ms,
                        escalated_from, success, task_kind, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
        except Exception as exc:  # never escalate to producers
            logger.debug("trace_recorder worker insert failed: %s", exc)
        finally:
            _QUEUE.task_done()


def _ensure_worker() -> None:
    global _WORKER
    if _WORKER is not None and _WORKER.is_alive():
        return
    with _WORKER_LOCK:
        if _WORKER is not None and _WORKER.is_alive():
            return
        t = threading.Thread(
            target=_worker_loop,
            name="meridian-trace-writer",
            daemon=True,
        )
        t.start()
        _WORKER = t


def flush(timeout: float | None = 5.0) -> bool:
    """Block until all queued rows are written. Returns True on success.

    Used by tests, the baseline aggregator, and the atexit hook. Never called
    by realtime producers.
    """
    if _WORKER is None or not _WORKER.is_alive():
        return True
    try:
        _QUEUE.join() if timeout is None else _wait_join(timeout)
        return True
    except Exception:
        return False


def _wait_join(timeout: float) -> None:
    """Bounded variant of queue.Queue.join — stdlib Queue.join doesn't accept
    a timeout, so we poll unfinished_tasks. Acceptable; this is called from
    test paths and shutdown, never from the hot path."""
    deadline = time.monotonic() + timeout
    while True:
        with _QUEUE.all_tasks_done:
            if _QUEUE.unfinished_tasks == 0:
                return
        if time.monotonic() >= deadline:
            return
        time.sleep(0.01)


def _atexit_drain() -> None:
    """Flush remaining rows on interpreter shutdown so a crash doesn't lose
    the tail of a run."""
    if _WORKER is None or not _WORKER.is_alive():
        return
    _wait_join(timeout=2.0)
    try:
        _QUEUE.put_nowait(_SENTINEL)
    except queue.Full:
        pass  # interpreter exiting; drop the sentinel


atexit.register(_atexit_drain)


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
    """Enqueue one ``swarm_traces`` row. Non-blocking. Never raises.

    The actual SQLite ``INSERT`` happens on a background daemon thread, so the
    caller's coroutine / phone-order loop is never blocked by disk IO. If the
    queue is full (disk wedged, worker hung) the row is dropped and a counter
    is incremented — better to lose a trace than to add jitter on a live call.
    """
    global _DROPPED
    _ensure_worker()
    row: tuple[Any, ...] = (
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
    )
    try:
        _QUEUE.put_nowait(row)
    except queue.Full:
        _DROPPED += 1
        if _DROPPED == 1 or _DROPPED % 1000 == 0:
            logger.warning(
                "trace_recorder: queue full (max=%d), dropping row "
                "(total dropped=%d)",
                _QUEUE_MAX, _DROPPED,
            )


def dropped_count() -> int:
    """Observability hook for tests / dashboards."""
    return _DROPPED


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
