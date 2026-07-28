"""
/api/clover/capabilities — the public, org-free half of the old /status payload.

Split out so /status (which returns a specific org's connection state) can be
tenancy-guarded in a follow-up without breaking the customer onboarding wizard,
which is portal-token authed, has no JWT, and only ever read oauth_available.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api.routes import clover_oauth  # noqa: E402


def _route(router, tail):
    for r in router.routes:
        if getattr(r, "path", "").endswith(tail):
            return r
    raise AssertionError(f"route {tail} not found")


def test_capabilities_route_exists_and_is_public():
    route = _route(clover_oauth.router, "/capabilities")
    assert not getattr(route, "dependencies", []), (
        "capabilities must stay public — the portal wizard has no JWT"
    )


def test_capabilities_takes_no_org_id():
    """No org param means no per-org data can leak from this endpoint."""
    route = _route(clover_oauth.router, "/capabilities")
    assert "org_id" not in route.dependant.query_params_names if hasattr(
        route.dependant, "query_params_names"
    ) else True
    assert all(p.name != "org_id" for p in route.dependant.query_params)


async def test_capabilities_payload_is_config_only():
    body = await clover_oauth.capabilities()
    assert set(body) == {"oauth_available", "clover_available"}
    assert all(isinstance(v, bool) for v in body.values())
