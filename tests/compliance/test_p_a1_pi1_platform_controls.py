"""
P (Privacy) — privacy request intake, export gating, unsubscribe, CASL guard.
A1 (Availability) — backup tooling presence (live status via collector).
PI1 (Processing integrity) — payment/POS reconciliation modules present.

Route-level assertions use the app's routing table (offline); admin-gating is
verified through dependency inspection, mirroring CC6.6.
"""
from pathlib import Path

CONTROL = "P/A1/PI1"

REPO = Path(__file__).parents[2]


def _route(app, method: str, path: str):
    from fastapi.routing import APIRoute
    for r in app.routes:
        if isinstance(r, APIRoute) and r.path == path and method in r.methods:
            return r
    return None


def test_privacy_request_intake_exists(app):
    """DSAR intake must be public (data subjects have no account)."""
    assert _route(app, "POST", "/api/privacy/request") is not None


def test_privacy_export_is_admin_gated(app):
    """Data export returns a person's full record — must be admin-gated."""
    from .conftest import route_auth_names, AUTH_DEPENDENCY_NAMES
    r = _route(app, "GET", "/api/privacy/export/{user_id}") or \
        _route(app, "GET", "/api/privacy/export/{uid}")
    assert r is not None, "privacy export endpoint missing"
    assert route_auth_names(r) & AUTH_DEPENDENCY_NAMES, (
        "privacy export endpoint is NOT auth-gated — full-record disclosure "
        "to anonymous callers"
    )


def test_unsubscribe_exists(app):
    assert _route(app, "POST", "/api/privacy/unsubscribe") is not None


def test_casl_guard_distinguishes_commercial_email():
    """CASL guard module exists and models the transactional/commercial split."""
    guard = (REPO / "src" / "compliance" / "casl_guard.py")
    assert guard.exists(), "src/compliance/casl_guard.py missing"
    text = guard.read_text()
    assert "transactional" in text and "commercial" in text.lower(), (
        "CASL guard no longer distinguishes transactional vs commercial email"
    )


def test_breach_register_endpoints_exist_and_gated(app):
    from .conftest import route_auth_names, AUTH_DEPENDENCY_NAMES
    r = _route(app, "POST", "/api/compliance/breach")
    assert r is not None, "breach register endpoint missing (CC7.3/P6.6)"
    assert route_auth_names(r) & AUTH_DEPENDENCY_NAMES, "breach register must be admin-gated"


def test_backup_tooling_present():
    """A1: the archive subsystem must exist in-repo (live Supabase PITR/backup
    status is collected read-only by scripts/compliance/collect_backup_evidence.py)."""
    anchors = [
        REPO / "src" / "api" / "routes" / "archives.py",
        *(REPO / "scripts").rglob("*backup*"),
        *(REPO / "scripts").rglob("*archive*"),
    ]
    assert any(p.exists() for p in anchors), (
        "no archive/backup tooling found (src/api/routes/archives.py or "
        "scripts/*backup*) — A1 evidence has no anchor"
    )


def test_payment_reconciliation_module_present():
    """PI1: Square reconciliation exists; mismatch handling is log-only today
    (tracked gap) but the module itself must not silently disappear."""
    hits = [p for p in (REPO / "src").rglob("*.py") if "reconcil" in p.name.lower()]
    hits += [p for p in (REPO / "scripts").rglob("*") if "reconcil" in p.name.lower()]
    assert hits, "no reconciliation module found under src/ or scripts/ (PI1)"
