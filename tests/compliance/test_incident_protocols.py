"""Incident protocols are wired, not decorative: every alert email references
a runbook that exists, and every runbook is linked from the index. Keeps the
"the alert told me exactly what to do" contract from rotting."""
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_INCIDENTS = _ROOT / "docs" / "runbooks" / "incidents"

PROTOCOLS = {
    "server-down.md", "pay-mismatch.md", "payments-unconfirmed.md",
    "phone-fleet-down.md", "vendor-billing.md",
}


def test_all_protocol_files_exist():
    for name in PROTOCOLS:
        assert (_INCIDENTS / name).is_file(), f"missing protocol {name}"


def test_index_links_every_protocol():
    index = (_INCIDENTS / "README.md").read_text()
    for name in PROTOCOLS:
        assert name in index, f"{name} not linked from incidents/README.md"


def test_alert_sources_reference_a_real_protocol():
    """Any source that names a docs/runbooks/incidents/*.md path must point at
    a file that actually exists — a renamed/deleted protocol fails here."""
    referenced = []
    for src in [
        _ROOT / "src" / "services" / "billing_monitor.py",
        _ROOT / "services" / "phone_agent" / "pay_on_phone.py",
        _ROOT / "src" / "email" / "templates" / "edge_status.py",
    ]:
        text = src.read_text()
        referenced += re.findall(r"docs/runbooks/incidents/([\w-]+\.md)", text)
    assert referenced, "no alert source references a protocol — wiring lost"
    for name in referenced:
        assert (_INCIDENTS / name).is_file(), (
            f"alert references docs/runbooks/incidents/{name} which does not exist")


def test_each_protocol_has_scope_and_mitigation():
    """Every protocol must be actionable: a scoping section and a
    mitigation/rollback step (mitigate-before-diagnose is the house rule)."""
    for name in PROTOCOLS - {"vendor-billing.md"}:  # vendor is SEV-2, different shape
        text = (_INCIDENTS / name).read_text().lower()
        assert "first 5 minutes" in text or "first 5" in text, f"{name}: no scope section"
        assert any(w in text for w in ("mitigat", "rollback", "roll back",
                                       "fallback", "unset", "redeploy")), \
            f"{name}: no mitigation/rollback step"
