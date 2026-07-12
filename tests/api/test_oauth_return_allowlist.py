"""Post-OAuth return-path allowlist — US + CA surfaces pass, open redirects rejected.

The allowlist lived duplicated in oauth.py (Square) + clover_oauth.py (Clover) and
drifted: US `/onboard` was never added, so US merchants got bounced to /app/settings
after authorizing. It's now centralized in src/api/routes/_oauth_return.py and both
callbacks import it. These pin the contract.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api.routes._oauth_return import safe_return_to


def test_us_surfaces_pass():
    for p in ("/onboard", "/onboard?oauth=success", "/app/settings", "/dashboard", "/settings",
              "/us/merchant/onboard", "/us/merchant", "/us/setup"):
        assert safe_return_to(p) == p, p


def test_canada_surfaces_still_pass():
    for p in ("/canada/merchant/onboard", "/canada/onboard", "/canada/dashboard", "/canada/setup"):
        assert safe_return_to(p) == p, p


def test_open_redirects_rejected():
    for p in ("//evil.com", "https://evil.com", "http://evil.com/x",
              "/\\evil", "javascript:alert(1)", "/evil", "/random", "", None):
        assert safe_return_to(p) == "", p


def test_both_callbacks_use_the_shared_allowlist():
    # Importing the modules binds _safe_return_to to the shared function — proves
    # neither file kept a private copy that could drift again.
    from src.api.routes import oauth as square_oauth
    from src.api.routes import clover_oauth
    assert square_oauth._safe_return_to is safe_return_to
    assert clover_oauth._safe_return_to is safe_return_to


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
