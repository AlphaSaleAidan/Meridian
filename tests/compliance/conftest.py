"""
SOC 2 prebuilt control tests — shared fixtures.

Every test in this package maps to a Trust Services Criteria control
(see tests/compliance/README.md). Tests are OFFLINE — no live Supabase,
Railway, or payment-provider calls. Live evidence is collected separately
by scripts/compliance/ (read-only) so CI can run this suite on every PR.

Evidence: when COMPLIANCE_EVIDENCE_DIR is set (the compliance workflow sets
it), each test session writes a machine-readable summary the auditor can
diff across runs. Locally it's a no-op.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Auth dependencies recognized as access-control gates (src/api/auth.py).
# A route is "authenticated" when at least one of these is in its FastAPI
# dependency tree. Inline checks inside handler bodies are NOT visible here —
# such endpoints belong in the public-endpoint baseline with category
# "inline-auth" and a pointer to the check.
AUTH_DEPENDENCY_NAMES = {
    "require_admin",
    "require_jwt",
    "require_admin_jwt",
    "require_service_auth",
    "require_org_access",
    "require_org_member",
}

_results: list[dict] = []


@pytest.fixture(scope="session")
def app():
    """The FastAPI app, imported with stub env so import never needs secrets."""
    os.environ.setdefault("SUPABASE_URL", "")
    os.environ.setdefault("SUPABASE_ANON_KEY", "")
    from src.api.app import app as _app
    return _app


def route_auth_names(route) -> set[str]:
    """All dependency callable names in a route's dependency tree."""
    names: set[str] = set()
    stack = [route.dependant]
    while stack:
        dep = stack.pop()
        call = getattr(dep, "call", None)
        if call is not None and getattr(call, "__name__", ""):
            names.add(call.__name__)
        stack.extend(dep.dependencies)
    return names


def public_routes(app) -> list[str]:
    """'METHOD /path' for every APIRoute with no recognized auth dependency."""
    from fastapi.routing import APIRoute
    out = []
    for r in app.routes:
        if not isinstance(r, APIRoute):
            continue
        if route_auth_names(r) & AUTH_DEPENDENCY_NAMES:
            continue
        for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
            out.append(f"{m} {r.path}")
    return sorted(out)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and item.path.parent == Path(__file__).parent:
        _results.append({
            "test": item.nodeid,
            "control": getattr(item.module, "CONTROL", "unmapped"),
            "outcome": rep.outcome,
        })


def pytest_sessionfinish(session, exitstatus):
    evidence_dir = os.environ.get("COMPLIANCE_EVIDENCE_DIR", "")
    if not evidence_dir or not _results:
        return
    out = Path(evidence_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "generated_at": stamp,
        "suite": "tests/compliance",
        "exit_status": int(exitstatus),
        "results": _results,
    }
    (out / f"control_tests_{stamp}.json").write_text(json.dumps(payload, indent=2))
