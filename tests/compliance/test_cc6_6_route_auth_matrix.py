"""
CC6.6 — Logical access: every API route is authenticated or deliberately public.

Two controls:

1. RATCHET — the set of routes served without a recognized auth dependency
   must exactly match public_endpoint_baseline.yaml. A new unauthenticated
   route fails CI (add an auth dependency, or allowlist it in review with a
   category). An entry that gained auth also fails, so the baseline shrinks
   in lockstep with remediation and can never go stale.

2. FAIL-CLOSED WEBHOOKS — the money-path webhooks must reject requests when
   their verification secret is unconfigured or the signature is absent.
   (A webhook that processes unsigned payloads is an unauthenticated write
   path into orders/payments regardless of how obscure the URL is.)
"""
from pathlib import Path

import pytest
import yaml

from .conftest import public_routes

CONTROL = "CC6.6"

BASELINE_FILE = Path(__file__).parent / "public_endpoint_baseline.yaml"


def _baseline() -> dict[str, list[str]]:
    data = yaml.safe_load(BASELINE_FILE.read_text()) or {}
    return {cat: sorted(entries or []) for cat, entries in data.items()}


def test_no_new_unauthenticated_routes(app):
    """Every route without an auth dependency is in the reviewed baseline."""
    current = set(public_routes(app))
    allowed = {r for entries in _baseline().values() for r in entries}

    new_public = sorted(current - allowed)
    assert not new_public, (
        "Routes are served WITHOUT an auth dependency and are not in the "
        "public-endpoint baseline. Add require_* auth, or (in review) add "
        f"them to {BASELINE_FILE.name} with a category+reason:\n  "
        + "\n  ".join(new_public)
    )


def test_baseline_has_no_stale_entries(app):
    """Baseline entries that gained auth (or were removed) must be deleted."""
    current = set(public_routes(app))
    allowed = {r for entries in _baseline().values() for r in entries}

    stale = sorted(allowed - current)
    assert not stale, (
        "Baseline entries are no longer served unauthenticated — remove them "
        f"from {BASELINE_FILE.name} so the ratchet tightens:\n  "
        + "\n  ".join(stale)
    )


def test_unreviewed_bucket_never_grows(app):
    """The 'unreviewed' category is a burn-down list frozen at 34 (2026-07-12).

    Reviewed endpoints move to an explicit category (or gain auth and leave
    the file); nothing new may be filed as unreviewed.
    """
    unreviewed = _baseline().get("unreviewed", [])
    assert len(unreviewed) <= 34, (
        f"'unreviewed' grew to {len(unreviewed)} — new public endpoints must "
        "be categorized deliberately, not parked as unreviewed."
    )


@pytest.fixture()
def client(app, monkeypatch):
    from fastapi.testclient import TestClient
    # Ensure verification secrets are UNSET so fail-closed paths are exercised.
    for var in ("VAPI_SERVER_SECRET", "STRIPE_WEBHOOK_SECRET",
                "POS_SQUARE_WEBHOOK_SIGNATURE_KEY", "SQUARE_WEBHOOK_SIGNATURE_KEY"):
        monkeypatch.delenv(var, raising=False)
    return TestClient(app, raise_server_exceptions=False)


def test_vapi_webhook_fails_closed(client):
    """Voice-order webhook: unauthenticated POST must not process (401/503)."""
    res = client.post("/api/vapi/webhook", json={"message": {"type": "tool-calls"}})
    assert res.status_code in (401, 503), (
        f"/api/vapi/webhook accepted an unauthenticated payload ({res.status_code}) "
        "— order placement would be open to anyone."
    )


def test_stripe_webhook_rejects_unsigned(client):
    """Stripe webhook: missing/invalid signature must be rejected."""
    res = client.post("/api/stripe/webhook", content=b"{}",
                      headers={"content-type": "application/json"})
    # 501 = handler's explicit "secret not configured — refusing" fail-closed.
    assert res.status_code in (400, 401, 501, 503), (
        f"/api/stripe/webhook accepted an unsigned payload ({res.status_code})."
    )


def test_square_pos_webhook_rejects_unsigned(client):
    """Square POS webhook: no signature key configured → refuse to process."""
    res = client.post("/api/webhooks/square", content=b"{}",
                      headers={"content-type": "application/json"})
    assert res.status_code in (400, 401, 403, 503), (
        f"/api/webhooks/square accepted an unsigned payload ({res.status_code})."
    )
