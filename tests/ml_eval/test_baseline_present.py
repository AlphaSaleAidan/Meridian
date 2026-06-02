"""Step-2 baseline presence check.

Asserts that ``tests/ml_eval/baseline_2026-06.json`` exists and contains at
least one row when it is present. When the artifact is missing (e.g. the
seed runner has not yet been executed in a fully-configured env), the test
xfails with a clear reason rather than erroring — the masterplan
explicitly requires this gate to be informational until the team lead
flips the seed runner on with real API keys.

This test purposely does NOT require the full 25-row seed list; many
seed tasks will be skipped in environments without LLM keys / vision
fixtures / a populated demo merchant. The downstream ML acceptance tests
will enforce row-count thresholds per upgrade wave.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

BASELINE_PATH = Path(__file__).parent / "baseline_2026-06.json"


def _load() -> dict:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def test_baseline_artifact_present_and_nonempty() -> None:
    if not BASELINE_PATH.exists():
        pytest.xfail(
            f"{BASELINE_PATH.name} not yet generated. "
            "Run `python3 scripts/run_baseline_seed.py` in an env with "
            "DEMO_ORG_ID + at least one LLM provider key set, then "
            "`python3 scripts/dump_baseline.py` to produce the artifact."
        )

    payload = _load()
    assert isinstance(payload, dict), "baseline payload must be a JSON object"
    assert payload.get("schema_version") == 1, "unexpected schema_version"
    assert "rows" in payload, "baseline payload missing 'rows' key"

    rows = payload["rows"]
    assert isinstance(rows, list), "'rows' must be a list"

    if len(rows) == 0:
        pytest.xfail(
            "baseline artifact exists but is empty (zero rows in swarm_traces). "
            "Re-run scripts/run_baseline_seed.py in an env with real API keys."
        )

    # Sanity-check the first row has the expected columns.
    first = rows[0]
    for required in ("trace_id", "agent_name", "task_kind", "success",
                     "latency_ms", "created_at"):
        assert required in first, f"baseline row missing required field: {required}"


def test_baseline_columns_consistent_when_present() -> None:
    """Schema-level sanity: every row carries the same key set."""
    if not BASELINE_PATH.exists():
        pytest.xfail("baseline artifact not yet generated")
    payload = _load()
    rows = payload.get("rows", [])
    if not rows:
        pytest.xfail("baseline artifact is empty")
    first_keys = set(rows[0].keys())
    for idx, row in enumerate(rows[1:], start=1):
        assert set(row.keys()) == first_keys, (
            f"row {idx} keys diverge from row 0: "
            f"{set(row.keys()) ^ first_keys}"
        )
