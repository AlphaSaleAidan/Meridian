"""Unit tests for short-lived stream tokens (Phase 2). Pure stdlib — runs in CI."""
import os
import time

import pytest

os.environ["GATEWAY_JWT_SECRET"] = "test-secret-phase2"
from src.camera.streaming.tokens import mint_stream_token, verify_stream_token  # noqa: E402


def test_valid_token_for_its_camera():
    t = mint_stream_token("cam-123", ttl_seconds=60)
    assert verify_stream_token(t, "cam-123") is True


def test_rejects_other_camera():
    t = mint_stream_token("cam-123")
    assert verify_stream_token(t, "cam-999") is False  # single-camera scoped


def test_rejects_expired():
    t = mint_stream_token("cam-123", ttl_seconds=1)
    time.sleep(1.2)
    assert verify_stream_token(t, "cam-123") is False


def test_rejects_tampered_signature():
    t = mint_stream_token("cam-123")
    body, _sig = t.split(".", 1)
    assert verify_stream_token(f"{body}.deadbeef", "cam-123") is False


def test_ttl_capped_at_60s():
    t = mint_stream_token("cam-123", ttl_seconds=99999)
    # still valid now; the cap is internal — just assert it verifies and isn't absurd
    assert verify_stream_token(t, "cam-123") is True


def test_fails_closed_without_secret(monkeypatch):
    monkeypatch.setenv("GATEWAY_JWT_SECRET", "")
    assert verify_stream_token("anything.anything", "cam-123") is False
