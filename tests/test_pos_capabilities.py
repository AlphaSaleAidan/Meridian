"""
/api/pos/{provider}/capabilities — framework twin of /api/clover/capabilities.

Same rationale: the org-free, public half of the old /status payload, split out
so /status (which returns a specific org's connection state) can be
tenancy-guarded in a follow-up without breaking surfaces that only ever read
oauth_available.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api.routes import pos_connect  # noqa: E402


def _route(router, tail):
    for r in router.routes:
        if getattr(r, "path", "").endswith(tail):
            return r
    raise AssertionError(f"route {tail} not found")


def test_capabilities_route_exists_and_is_public():
    route = _route(pos_connect.router, "/capabilities")
    assert not getattr(route, "dependencies", []), (
        "capabilities must stay public — portal-token surfaces have no JWT"
    )


def test_capabilities_takes_no_org_id():
    """No org param means no per-org data can leak from this endpoint."""
    route = _route(pos_connect.router, "/capabilities")
    assert all(p.name != "org_id" for p in route.dependant.query_params)


async def test_capabilities_payload_is_config_only():
    body = await pos_connect.capabilities("stripe")
    assert set(body) == {"oauth_available"}
    assert isinstance(body["oauth_available"], bool)


async def test_capabilities_unknown_provider_404s():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await pos_connect.capabilities("not-a-real-pos")
    assert exc.value.status_code == 404
