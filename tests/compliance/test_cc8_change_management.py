"""
CC8.1 — Change management: the pipeline controls an auditor will sample.

Verifies the change-control tooling EXISTS and stays wired: CI secret
scanning, static security analysis, syntax/import gate, pre-commit hooks,
and this compliance suite itself. Deleting or de-triggering any of these is
a control failure and should read as one in CI.
"""
from pathlib import Path

import yaml

CONTROL = "CC8.1"

REPO = Path(__file__).parents[2]
WORKFLOWS = REPO / ".github" / "workflows"


def _workflow(name: str) -> dict:
    path = WORKFLOWS / name
    assert path.exists(), f"required CI workflow missing: .github/workflows/{name}"
    return yaml.safe_load(path.read_text()) or {}


def _triggers(wf: dict) -> set[str]:
    # YAML 1.1 parses bare `on:` as boolean True.
    on = wf.get("on", wf.get(True, {}))
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return set(on)
    return set(on.keys())


def test_secret_scanning_runs_on_prs():
    wf = _workflow("gitleaks.yml")
    assert "pull_request" in _triggers(wf), "gitleaks must run on every PR"


def test_security_scanning_runs_on_prs():
    wf = _workflow("security.yml")
    assert "pull_request" in _triggers(wf), "bandit/safety must run on every PR"


def test_syntax_gate_runs_on_prs():
    wf = _workflow("syntax-check.yml")
    assert "pull_request" in _triggers(wf), "syntax/import gate must run on every PR"


def test_compliance_suite_runs_on_prs_and_schedule():
    wf = _workflow("compliance.yml")
    trig = _triggers(wf)
    assert "pull_request" in trig, "compliance suite must run on every PR"
    assert "schedule" in trig, (
        "compliance suite must also run on a schedule — Type II evidence "
        "needs periodic runs, not just change-triggered ones"
    )


def test_precommit_config_present():
    assert (REPO / ".pre-commit-config.yaml").exists() or \
           (REPO / ".pre-commit-config.yml").exists(), (
        "pre-commit config missing — local secret scan + checks are part of "
        "the documented change-management control"
    )
