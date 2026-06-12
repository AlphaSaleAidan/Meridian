#!/usr/bin/env python3
"""Swarm upgrade eval harness (masterplan Phase 5).

One entrypoint that exercises the swarm-upgrade surface and prints a
consolidated pass/fail report:

  1. Agent registry validation (scripts/validate_agents.py) — schema, class
     resolvability, and the BaseAgent drift gate.
  2. Routing/registry unit suite (tests/swarm_eval) — tier resolution,
     one-step confidence escalation, registry-driven tiers.
  3. ML model evals (tests/ml_eval) — Wave 1 upgrades vs their incumbents
     (importorskip'd; rows with missing optional deps are reported skipped).

Usage:
    python scripts/run_swarm_eval.py            # everything
    python scripts/run_swarm_eval.py --fast     # skip the slow ml_eval suite

Exit code is non-zero if any selected section fails, so CI can gate on it.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(label: str, cmd: list[str]) -> bool:
    print(f"\n{'=' * 70}\n {label}\n{'=' * 70}")
    proc = subprocess.run(cmd, cwd=_REPO_ROOT)
    ok = proc.returncode == 0
    print(f"  → {label}: {'PASS' if ok else 'FAIL'} (exit {proc.returncode})")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="Swarm upgrade eval harness")
    ap.add_argument("--fast", action="store_true",
                    help="skip the slow ml_eval suite (model training)")
    args = ap.parse_args()

    py = sys.executable
    results: dict[str, bool] = {}

    results["agent_registry"] = _run(
        "1/3 Agent registry validation",
        [py, "scripts/validate_agents.py"],
    )
    results["swarm_eval"] = _run(
        "2/3 Routing + registry unit suite",
        [py, "-m", "pytest", "tests/swarm_eval", "-q"],
    )
    if args.fast:
        print("\n  (skipping ml_eval — --fast)")
    else:
        results["ml_eval"] = _run(
            "3/3 ML model evals (Wave 1 vs incumbents)",
            [py, "-m", "pytest", "tests/ml_eval", "-q"],
        )

    print(f"\n{'=' * 70}\n SWARM EVAL SUMMARY\n{'=' * 70}")
    for name, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    all_ok = all(results.values())
    print(f"\n  OVERALL: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
