#!/usr/bin/env python3
"""
Baseline aggregator — read ``swarm_traces`` and write
``tests/ml_eval/baseline_2026-06.json`` (one record per row).

This artifact is what the ML wave acceptance tests compare against.

Usage::

    python3 scripts/dump_baseline.py
    # or, to point at a non-default DB:
    MERIDIAN_SWARM_TRACE_DB=/path/to/swarm_traces.sqlite python3 scripts/dump_baseline.py

Rollback: rm scripts/dump_baseline.py.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "data" / "swarm_traces.sqlite"
OUTPUT_PATH = REPO_ROOT / "tests" / "ml_eval" / "baseline_2026-06.json"

COLUMNS = [
    "id", "trace_id", "agent_name", "tier", "provider", "model",
    "prompt_tokens", "completion_tokens", "latency_ms", "escalated_from",
    "success", "task_kind", "error", "created_at",
]


def _db_path() -> Path:
    return Path(os.environ.get("MERIDIAN_SWARM_TRACE_DB", str(DEFAULT_DB)))


def load_rows(db_path: Path) -> list[dict]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    try:
        # If the table doesn't exist yet, return empty rather than raise.
        tbl = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='swarm_traces'"
        ).fetchone()
        if not tbl:
            return []
        cur = conn.execute(
            f"SELECT {', '.join(COLUMNS)} FROM swarm_traces ORDER BY id ASC"
        )
        out: list[dict] = []
        for row in cur.fetchall():
            rec = dict(zip(COLUMNS, row))
            rec["success"] = bool(rec.get("success"))
            out.append(rec)
        return out
    finally:
        conn.close()


def main() -> int:
    db = _db_path()
    rows = load_rows(db)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "source_db": str(db),
        "row_count": len(rows),
        "columns": COLUMNS,
        "rows": rows,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
