"""Pre-Wave-1B check: the swarm_traces recorder must not block the caller.

The recorder is invoked synchronously from inside async coroutines (the
``BaseAgent.__init_subclass__`` wrap, the LiteLLM tee in ``llm_layer.py``).
If the underlying ``sqlite3.execute()`` were called on the calling thread,
each agent run would stall the asyncio event loop for the duration of a
disk write — perceptible jitter on the Pipecat phone-order loop, and
accumulating overhead on every ``asyncio.gather`` of the tier-1..4 fanout.

These tests pin two contracts:

1. ``record()`` returns within a tiny budget (sub-millisecond on this VPS,
   well under the realtime jitter ceiling) regardless of how many rows
   are queued.
2. After a synchronous ``flush()``, every queued row is persisted to
   SQLite — so the non-blocking design loses no data on the happy path.
"""

from __future__ import annotations

import importlib
import sqlite3
import time
from pathlib import Path

import pytest


@pytest.fixture()
def fresh_recorder(tmp_path: Path, monkeypatch):
    """Re-import the recorder with a fresh DB path so each test owns its
    queue + worker, and tests don't see each other's rows."""
    db = tmp_path / "traces.sqlite"
    monkeypatch.setenv("MERIDIAN_SWARM_TRACE_DB", str(db))
    import src.ai.trace_recorder as tr
    importlib.reload(tr)
    yield tr, db
    # Best-effort teardown: drain remaining rows before the test owns its
    # tmp_path goes away. The worker thread is a daemon, so even if it
    # outlives the test it can't break the next one (next test reloads).
    try:
        tr.flush(timeout=2.0)
    except Exception:
        pass


def test_record_returns_quickly_under_load(fresh_recorder):
    """A burst of 200 record() calls must average well under 1 ms each."""
    tr, _ = fresh_recorder
    n = 200
    t0 = time.perf_counter()
    for i in range(n):
        tr.record(
            trace_id=tr.new_trace_id(),
            agent_name="stress_test",
            task_kind="unit",
            latency_ms=1,
            success=True,
        )
    elapsed = time.perf_counter() - t0
    per_call_us = (elapsed / n) * 1_000_000

    # Realtime budget: 1 ms / call upper bound; informational target ≪ that.
    print(f"\n  record() avg = {per_call_us:.1f} µs over {n} calls")
    assert per_call_us < 1000.0, (
        f"record() avg {per_call_us:.1f} µs exceeds 1 ms realtime budget"
    )


def test_flushed_rows_persisted(fresh_recorder):
    """Every record() must appear in the DB after a synchronous flush()."""
    tr, db = fresh_recorder
    n = 50
    for i in range(n):
        tr.record(
            trace_id="t-persist",
            agent_name=f"agent_{i % 5}",
            task_kind="persist_test",
            latency_ms=i,
            success=(i % 7 != 0),
        )
    assert tr.flush(timeout=5.0), "flush() reported failure"

    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT COUNT(*) FROM swarm_traces WHERE task_kind=?",
            ("persist_test",),
        ).fetchone()
    assert rows[0] == n, f"expected {n} persisted rows, got {rows[0]}"


def test_overflow_drops_instead_of_blocking(fresh_recorder, monkeypatch):
    """When the queue is artificially saturated, record() must not block.

    We can't easily wedge the worker, so we shrink the queue to 0 capacity
    and assert that excess record() calls return immediately and the
    drop counter advances.
    """
    tr, _ = fresh_recorder
    # Replace the queue with a zero-capacity stand-in to force overflow.
    import queue as _q

    tr._QUEUE = _q.Queue(maxsize=1)
    # Block worker so no slots open during the test.
    tr._QUEUE.put_nowait(("blocker",) * 12)

    start_dropped = tr.dropped_count()
    t0 = time.perf_counter()
    for _ in range(20):
        tr.record(agent_name="overflow", task_kind="overflow_test")
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.05, f"record() blocked under overflow ({elapsed:.3f}s)"
    assert tr.dropped_count() > start_dropped, "overflow drops not counted"
