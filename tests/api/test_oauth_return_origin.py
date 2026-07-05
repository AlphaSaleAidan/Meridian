"""Cross-subdomain OAuth return-origin — allowlist + state-format compatibility.

Sessions are per-origin (localStorage), so the Square/Clover callbacks must send
the merchant back to the origin they STARTED on, not the static FRONTEND_URL.
The origin is captured from the Referer at /authorize time, carried inside the
HMAC-signed state, and validated against a strict allowlist on the way out.

These pin three contracts:
  1. Only the three known frontend origins are accepted; everything else falls
     back to FRONTEND_URL ("" from the helpers).
  2. Referer parsing never lets a hostile or malformed referer through.
  3. Old-format states (signed before this change — 4/5-part Square, 5-part
     Clover) still verify mid-deploy; new 6-part states carry the origin.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import sys
import time
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api.routes._oauth_return import origin_from_referer, safe_origin
from src.api.routes import clover_oauth, oauth as square_oauth

ORG = "biz_0123456789abcdef"


# ── 1. Origin allowlist ──────────────────────────────────────────────


def test_allowlisted_origins_accepted():
    for o in (
        "https://meridian.tips",
        "https://www.meridian.tips",
        "https://canada.meridian.tips",
        "https://meridian.tips/",  # trailing slash normalized
    ):
        assert safe_origin(o) == o.rstrip("/"), o


def test_unknown_origins_rejected():
    for o in (
        "http://meridian.tips",                      # scheme downgrade
        "https://evil.com",
        "https://canada.meridian.tips.evil.com",     # suffix trick
        "https://staging.meridian.tips",             # unlisted subdomain
        "https://meridian.tips.evil.com",
        "meridian.tips",                             # no scheme
        "",
        None,
    ):
        assert safe_origin(o) == "", o


def test_origin_from_referer_extracts_and_validates():
    assert origin_from_referer("https://meridian.tips/app/settings?x=1") == "https://meridian.tips"
    assert origin_from_referer(
        "https://canada.meridian.tips/canada/merchant/onboard"
    ) == "https://canada.meridian.tips"
    for bad in (
        "https://evil.com/canada/merchant",
        "https://meridian.tips.evil.com/app",
        "not a url",
        "//meridian.tips/app",
        "",
        None,
    ):
        assert origin_from_referer(bad) == "", bad


# ── 2. Old-format state compatibility (mid-deploy safety) ────────────


def _sign(module, payload: str) -> str:
    sig = hmac.new(
        module._STATE_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:32]
    return f"{payload}:{sig}"


def _rt_b64(return_to: str) -> str:
    return (
        base64.urlsafe_b64encode(return_to.encode()).decode().rstrip("=")
        if return_to
        else "_"
    )


def test_square_legacy_4_part_state_still_verifies():
    expires = int(time.time()) + 600
    state = _sign(square_oauth, f"{ORG}:{uuid4().hex[:16]}:{expires}")
    assert square_oauth._verify_state(state) == (ORG, "", "")


def test_square_old_5_part_state_still_verifies():
    expires = int(time.time()) + 600
    rt = "/canada/merchant/onboard"
    state = _sign(square_oauth, f"{ORG}:{uuid4().hex[:16]}:{expires}:{_rt_b64(rt)}")
    assert square_oauth._verify_state(state) == (ORG, rt, "")


def test_clover_old_5_part_state_still_verifies():
    expires = int(time.time()) + 600
    rt = "/canada/dashboard"
    state = _sign(clover_oauth, f"{ORG}:{uuid4().hex[:16]}:{expires}:{_rt_b64(rt)}")
    assert clover_oauth._verify_state(state) == (ORG, rt, "")


def test_origin_less_sign_emits_old_format():
    # No origin captured → the signed state must stay old-format so an OLD
    # callback instance (rolling deploy) can still verify it.
    for module in (square_oauth, clover_oauth):
        state = module._sign_state(ORG, "/canada/merchant/onboard")
        assert len(state.split(":")) == 5, module.__name__


# ── 3. New-format state carries a validated origin ───────────────────


def test_new_state_roundtrip_carries_origin():
    for module in (square_oauth, clover_oauth):
        state = module._sign_state(
            ORG, "/canada/merchant/onboard", "https://meridian.tips"
        )
        assert len(state.split(":")) == 6, module.__name__
        assert module._verify_state(state) == (
            ORG,
            "/canada/merchant/onboard",
            "https://meridian.tips",
        ), module.__name__


def test_non_allowlisted_origin_in_state_is_stripped():
    # Even if a hostile origin somehow got signed, verification re-validates
    # against the allowlist — the callback then falls back to FRONTEND_URL.
    for module in (square_oauth, clover_oauth):
        state = module._sign_state(ORG, "", "https://evil.com")
        verified = module._verify_state(state)
        assert verified is not None
        assert verified[2] == "", module.__name__


def test_tampered_state_rejected():
    state = square_oauth._sign_state(ORG, "/canada/setup", "https://meridian.tips")
    # Swap the origin field without re-signing.
    parts = state.split(":")
    parts[4] = base64.urlsafe_b64encode(b"https://evil.com").decode().rstrip("=")
    assert square_oauth._verify_state(":".join(parts)) is None


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
