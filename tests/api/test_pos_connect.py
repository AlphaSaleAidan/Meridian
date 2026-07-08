"""POS connect framework — gating + state signing contract.

The framework must NEVER offer a provider unless it is both `verified` and has
server-side credentials, and its signed state must reject tampering, expiry, and
provider mismatch. These pin that contract; no network calls.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("OAUTH_STATE_SECRET", "test-only-secret-not-for-production")

from dataclasses import replace  # noqa: E402

from src.pos_connect.registry import PROVIDERS, enabled_providers, get_provider  # noqa: E402
from src.pos_connect.oauth import sign_state, verify_state, GenericOAuthManager  # noqa: E402


def test_all_registry_providers_start_unverified():
    # Nothing ships pre-verified — every provider must be validated against a real
    # app before it can be offered. This guards against an accidental live flip.
    assert PROVIDERS, "registry should not be empty"
    for key, cfg in PROVIDERS.items():
        assert cfg.verified is False, f"{key} must stay verified=False until validated"


def test_enabled_requires_verified_and_credentials(monkeypatch):
    cfg = get_provider("sumup")
    assert cfg is not None
    # creds present but unverified → not enabled
    monkeypatch.setenv(cfg.client_id_env, "id")
    monkeypatch.setenv(cfg.client_secret_env, "secret")
    assert cfg.enabled() is False
    # verified but no creds → not enabled
    verified_cfg = replace(cfg, verified=True)
    monkeypatch.delenv(cfg.client_id_env, raising=False)
    monkeypatch.delenv(cfg.client_secret_env, raising=False)
    assert verified_cfg.enabled() is False
    # verified AND creds → enabled
    monkeypatch.setenv(cfg.client_id_env, "id")
    monkeypatch.setenv(cfg.client_secret_env, "secret")
    assert verified_cfg.enabled() is True


def test_enabled_providers_empty_by_default():
    # With no provider verified, the frontend is offered nothing.
    assert enabled_providers() == []


def test_state_roundtrip():
    state = sign_state("lightspeed_xseries", "biz_abc123def4567890", "/us/dashboard")
    out = verify_state(state)
    assert out == ("lightspeed_xseries", "biz_abc123def4567890", "/us/dashboard")


def test_state_rejects_tamper():
    state = sign_state("sumup", "biz_abc123def4567890", "/us/dashboard")
    tampered = state[:-1] + ("0" if state[-1] != "0" else "1")
    assert verify_state(tampered) is None


def test_state_rejects_expired(monkeypatch):
    import src.pos_connect.oauth as oauth_mod
    state = sign_state("sumup", "biz_abc123def4567890", "")
    # Jump wall-clock past the 10-minute TTL (capture real now() before patching).
    future = time.time() + 3600
    monkeypatch.setattr(oauth_mod.time, "time", lambda: future)
    assert verify_state(state) is None


def test_authorize_url_shape():
    cfg = replace(get_provider("sumup"), verified=True)
    os.environ["SUMUP_CLIENT_ID"] = "myclient"
    os.environ["SUMUP_CLIENT_SECRET"] = "mysecret"
    mgr = GenericOAuthManager(cfg, "https://api.meridian.tips/api/pos/sumup/callback")
    url = mgr.authorize_url("STATE123")
    assert url.startswith("https://api.sumup.com/authorize?")
    assert "client_id=myclient" in url
    assert "response_type=code" in url
    assert "state=STATE123" in url
    assert "scope=transactions.history" in url
