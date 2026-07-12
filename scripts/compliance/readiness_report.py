#!/usr/bin/env python3
"""
SOC 2 readiness report — aggregates the control-test suite + live collectors
into one markdown snapshot an auditor (or Aidan) can read in 60 seconds.

Runs:  pytest tests/compliance (offline)  →  per-control pass/fail
Reads: COMPLIANCE_EVIDENCE_DIR/*.json     →  live collector verdicts
Writes: COMPLIANCE_EVIDENCE_DIR/readiness_report_<stamp>.md

Readiness % here is TEST-BACKED readiness only — it deliberately scores lower
than the design-readiness % in compliance/gap-analysis.md (PR #196), because
a control only counts when a running check proves it. The two converge as
gaps close.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = Path(os.environ.get("COMPLIANCE_EVIDENCE_DIR", "compliance-evidence"))


def run_suite() -> list[dict]:
    env = dict(os.environ, COMPLIANCE_EVIDENCE_DIR=str(EVIDENCE_DIR))
    subprocess.run(
        [sys.executable, "-m", "pytest", "tests/compliance", "-q", "--no-header"],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    runs = sorted(EVIDENCE_DIR.glob("control_tests_*.json"))
    if not runs:
        return []
    return json.loads(runs[-1].read_text())["results"]


def latest_collector_artifacts() -> list[dict]:
    out = []
    for pattern in ("rls_posture_*.json", "backup_status_*.json"):
        arts = sorted(EVIDENCE_DIR.glob(pattern))
        if arts:
            out.append(json.loads(arts[-1].read_text()))
    return out


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    results = run_suite()
    collectors = latest_collector_artifacts()

    controls: dict[str, dict] = {}
    for r in results:
        c = controls.setdefault(r["control"], {"passed": 0, "failed": 0, "tests": []})
        c["passed" if r["outcome"] == "passed" else "failed"] += 1
        c["tests"].append(r)
    for art in collectors:
        c = controls.setdefault(art["control"], {"passed": 0, "failed": 0, "tests": []})
        ok = not art.get("violations") if "violations" in art else True
        c["passed" if ok else "failed"] += 1
        c["tests"].append({"test": art.get("method", "live collector"),
                           "outcome": "passed" if ok else "failed"})

    total_pass = sum(c["passed"] for c in controls.values())
    total = sum(c["passed"] + c["failed"] for c in controls.values())
    pct = round(100 * total_pass / total) if total else 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "# Meridian — SOC 2 test-backed readiness snapshot",
        "",
        f"Generated {stamp} · {total_pass}/{total} checks passing · **{pct}% test-backed**",
        "",
        "> Readiness ≠ certification. This score counts only controls proven by a",
        "> running check (offline suite + read-only live collectors). Design-level",
        "> readiness is tracked in compliance/gap-analysis.md.",
        "",
        "| Control | Checks | Passing | State |",
        "|---|---|---|---|",
    ]
    for control in sorted(controls):
        c = controls[control]
        n = c["passed"] + c["failed"]
        state = "✅" if c["failed"] == 0 else "❌"
        lines.append(f"| {control} | {n} | {c['passed']} | {state} |")
    lines += ["", "## Failing checks", ""]
    failing = [t for c in controls.values() for t in c["tests"] if t["outcome"] != "passed"]
    if failing:
        lines += [f"- `{t['test']}`" for t in failing]
    else:
        lines.append("None — all prebuilt checks green.")

    report = EVIDENCE_DIR / f"readiness_report_{stamp}.md"
    report.write_text("\n".join(lines) + "\n")
    print(f"report: {report} — {pct}% test-backed ({total_pass}/{total})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
