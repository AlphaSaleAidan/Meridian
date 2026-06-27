"""Security regression tests for the tenancy / fail-close hardening branch.

Covers:
  - Toast webhook HMAC signature verification (pure).
  - require_admin_auth: machine/admin only, rejects anonymous.
  - require_service_auth: returns a typed principal.
  - enforce_service_member: no-op for machine principals.
"""

import os

import pytest
from fastapi import HTTPException

from src.toast.webhook_verify import compute_signature, verify_signature
from src.api import auth as auth_mod


# ── Toast signature verification ──────────────────────────────────────────

def test_toast_signature_roundtrip():
    secret, body = "whsec_toast", b'{"eventType":"orders.modified"}'
    sig = compute_signature(secret, body)
    assert verify_signature(secret, body, sig) is True


@pytest.mark.parametrize("secret,body,sig", [
    ("whsec", b"{}", "not-the-signature"),     # wrong signature
    ("whsec", b"{}", None),                      # missing signature
    ("", b"{}", "anything"),                      # no secret configured
])
def test_toast_signature_rejects(secret, body, sig):
    assert verify_signature(secret, body, sig) is False


def test_toast_signature_rejects_tampered_body():
    secret = "whsec"
    sig = compute_signature(secret, b'{"amount":10}')
    assert verify_signature(secret, b'{"amount":9999}', sig) is False


# ── Admin / service auth ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_require_admin_auth_accepts_admin_key(monkeypatch):
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret")
    principal = await auth_mod.require_admin_auth(admin_key="topsecret", auth_header="")
    assert principal == {"kind": "admin"}


@pytest.mark.asyncio
async def test_require_admin_auth_rejects_anonymous(monkeypatch):
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret")
    monkeypatch.setenv("MERIDIAN_SERVICE_TOKEN", "")
    with pytest.raises(HTTPException) as ei:
        await auth_mod.require_admin_auth(admin_key="", auth_header="")
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_auth_rejects_plain_user(monkeypatch):
    """A valid session user who is NOT in ADMIN_EMAILS must be rejected."""
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret")
    monkeypatch.setenv("MERIDIAN_SERVICE_TOKEN", "svc")
    monkeypatch.setattr(auth_mod, "ADMIN_EMAILS", [], raising=False)

    async def _fake_verify(_token):
        return {"id": "u1", "email": "merchant@example.com"}

    monkeypatch.setattr(auth_mod, "_verify_supabase_token", _fake_verify)
    with pytest.raises(HTTPException) as ei:
        await auth_mod.require_admin_auth(admin_key="", auth_header="Bearer usertoken")
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_require_service_auth_returns_principal(monkeypatch):
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret")
    principal = await auth_mod.require_service_auth(admin_key="topsecret", auth_header="")
    assert principal["kind"] == "admin"


@pytest.mark.asyncio
async def test_enforce_service_member_noop_for_machine():
    # Should not raise for admin/service principals (no org membership needed).
    await auth_mod.enforce_service_member({"kind": "admin"}, "any-org")
    await auth_mod.enforce_service_member({"kind": "service"}, "any-org")
