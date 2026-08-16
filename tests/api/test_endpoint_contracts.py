"""Every endpoint, probed the two ways they actually break.

The suite has good coverage of endpoints somebody thought to test. This walks
the whole router table instead — 400+ routes — and asks two questions of each
one that no happy-path test asks:

    1. Does an unauthenticated caller get REFUSED, rather than served?
    2. Does a malformed body produce a 422, rather than a 500?

A 500 is the finding that matters. It means an unhandled exception reached the
client: the error is opaque to the caller, it is a stack trace in the log
instead of a validation message, and on a POST it can mean a half-written row.
A 200 on an unauthenticated data endpoint is worse — it is a leak.

Deliberately in-process (TestClient, no network, no DB), so it is fast enough
to run on every change and cannot touch live data.
"""
from __future__ import annotations

import os
import re

import pytest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key")

from fastapi.testclient import TestClient  # noqa: E402

from src.api.app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


# Routes that are SUPPOSED to answer an anonymous caller. Each one is public
# for a stated reason — a third party posts to it, a person clicks it, or a
# load balancer polls it. Anything not on this list must refuse.
PUBLIC_PREFIXES = (
    "/health", "/healthz", "/ready", "/metrics", "/docs", "/openapi", "/redoc",
    "/api/webhooks",            # providers post here, signed not logged in
    "/api/vapi/webhook",        # Vapi calls it mid-call
    "/b/",                      # booking short links — a customer taps them
    "/c/",                      # customer portal links
    "/api/public",
    "/api/oauth",               # provider redirects land here
    "/api/pos/square/callback",
    "/api/pos/clover/callback",
    "/api/pos/stripe/callback",
    "/api/bookings/feed/",      # calendar subscription URL, token in the path
    "/api/clover/hco/webhook",  # Clover hosted-checkout callback
    "/api/marketplace/webhook",
    "/api/billing/webhook",
    "/api/stripe/",             # Stripe posts signed events
    "/api/menu/csv-template",   # a blank template, nothing tenant-specific
    "/api/credits/packs",       # public price list
    "/api/phone/fees",          # public price list
    "/api/pos/providers",       # which integrations exist, not who uses them
)


def _routes():
    out = []
    for r in app.routes:
        methods = getattr(r, "methods", None)
        path = getattr(r, "path", "")
        if not methods or not path.startswith(("/api", "/b/", "/c/")):
            continue
        for m in sorted(methods - {"HEAD", "OPTIONS"}):
            out.append((m, path))
    return sorted(set(out))


def _fill(path: str) -> str:
    """Substitute path params with values shaped like the real thing.

    A UUID where a UUID is expected, so validation passes far enough to reach
    the auth check rather than short-circuiting on a 422 that would hide it.
    """
    def sub(match):
        name = match.group(1).split(":")[0]
        if "id" in name.lower():
            return "00000000-0000-4000-8000-000000000000"
        if "code" in name.lower() or "token" in name.lower():
            return "abc123"
        return "test"
    return re.sub(r"\{([^}]+)\}", sub, path)


def _is_public(path: str) -> bool:
    return any(path.startswith(p) for p in PUBLIC_PREFIXES)


ROUTES = _routes()


def test_the_walk_found_the_routes():
    # Guards the guard: a broken enumeration makes everything below pass
    # vacuously, which is the worst outcome for a test like this.
    assert len(ROUTES) > 300, f"only found {len(ROUTES)} routes"


@pytest.mark.parametrize("method,path", ROUTES, ids=lambda v: str(v))
def test_no_endpoint_returns_500_to_an_anonymous_caller(method, path):
    """An unauthenticated probe must never reach an unhandled exception.

    Refusing is fine. Erroring is not: it means the request got past the
    guard and died inside the handler, which on a write can leave a
    half-finished row behind.
    """
    url = _fill(path)
    kwargs = {"json": {}} if method in ("POST", "PUT", "PATCH") else {}
    res = client.request(method, url, **kwargs)
    # 500 EXACTLY, not >=500. A 503 here is a deliberate, handled answer —
    # "Database not initialized" is this environment telling the truth, and
    # treating it as a crash buries the real 500s in 78 false positives.
    assert res.status_code != 500, (
        f"{method} {path} -> 500: {res.text[:200]}"
    )


@pytest.mark.parametrize(
    "method,path",
    [(m, p) for m, p in ROUTES if not _is_public(p)],
    ids=lambda v: str(v),
)
def test_private_endpoints_refuse_an_anonymous_caller(method, path):
    """No data endpoint answers 200 without credentials."""
    url = _fill(path)
    kwargs = {"json": {}} if method in ("POST", "PUT", "PATCH") else {}
    res = client.request(method, url, **kwargs)
    assert res.status_code != 200, (
        f"{method} {path} served an anonymous caller: {res.text[:200]}"
    )


@pytest.mark.parametrize(
    "method,path",
    [(m, p) for m, p in ROUTES if m in ("POST", "PUT", "PATCH")],
    ids=lambda v: str(v),
)
def test_a_garbage_body_is_rejected_not_crashed(method, path):
    """Junk in must produce a refusal, never a stack trace.

    The body is deliberately the wrong SHAPE — a list where an object is
    expected — because that is what slips past a handler that only checks for
    missing keys.
    """
    url = _fill(path)
    res = client.request(method, url, json=["not", "an", "object", 12345])
    assert res.status_code != 500, (
        f"{method} {path} crashed on a malformed body: {res.text[:200]}"
    )
