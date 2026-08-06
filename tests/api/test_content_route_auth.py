"""Route-auth for the content studio router (CC6.6 public-endpoint burndown).

Four /api/content/* GETs were served with no auth dependency. They are all
reached from the signed-in studio (frontend/src/lib/content-api.ts always
attaches a Supabase bearer token), so they now require a session:

  GET /api/content/models              require_jwt
  GET /api/content/director/styles     require_jwt
  GET /api/content/video/status/{id}   require_jwt + org-scoped to the job owner
  GET /api/content/video/debug/{id}    require_admin_jwt (provider internals)

Run: python -m pytest tests/api/test_content_route_auth.py -v
"""
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.api import auth as auth_mod  # noqa: E402
import src.api.routes.content as content_mod  # noqa: E402

ORG = "11111111-1111-1111-1111-111111111111"
OTHER_ORG = "22222222-2222-2222-2222-222222222222"
JOB_ID = "abcd1234"

MEMBER = {"id": "owner-1", "email": "owner@acme.test"}
OUTSIDER = {"id": "intruder-9", "email": "intruder@evil.test"}
ADMIN = {"id": "admin-1", "email": "aidanpierce72@gmail.com"}

AUTHED = {"Authorization": "Bearer usertoken"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(content_mod, "_video_jobs", {
        JOB_ID: {
            "status": "processing",
            "merchantId": ORG,
            "model": "seedance-2-fast",
            "fal_status": "IN_QUEUE",
            "fal_status_url": "https://queue.fal.run/x/requests/r1/status",
            "fal_request_id": "r1",
            "submitted_at": 0.0,
            "poll_count": 1,
            "enhanced_prompt": "a warm shot of the acme dining room",
        }
    })
    app = FastAPI()
    app.include_router(content_mod.router)
    return TestClient(app, raise_server_exceptions=False)


def _as_user(monkeypatch, user, *, is_member: bool):
    async def _verify(_token):
        return user

    async def _check(_user, _org_id):
        return is_member

    monkeypatch.setattr(auth_mod, "_verify_supabase_token", _verify)
    monkeypatch.setattr(auth_mod, "_check_org_membership", _check)
    monkeypatch.delenv("TENANCY_ENFORCEMENT_DISABLED", raising=False)


@pytest.mark.parametrize("path", [
    "/api/content/models",
    "/api/content/director/styles",
    f"/api/content/video/status/{JOB_ID}",
    f"/api/content/video/debug/{JOB_ID}",
])
def test_anonymous_is_rejected(client, path):
    """No Authorization header — every one of these must 401, not serve data."""
    assert client.get(path).status_code == 401


def test_catalogs_served_to_signed_in_user(client, monkeypatch):
    _as_user(monkeypatch, MEMBER, is_member=False)
    assert "video" in client.get("/api/content/models", headers=AUTHED).json()
    styles = client.get("/api/content/director/styles", headers=AUTHED).json()
    assert "styles" in styles and "platforms" in styles


def test_video_status_scoped_to_job_owner(client, monkeypatch):
    _as_user(monkeypatch, MEMBER, is_member=True)
    body = client.get(f"/api/content/video/status/{JOB_ID}", headers=AUTHED).json()
    assert body["jobId"] == JOB_ID
    assert body["status"] == "processing"


def test_video_status_cross_tenant_denied(client, monkeypatch):
    """A signed-in user from another org must not read the job's prompt/model."""
    _as_user(monkeypatch, OUTSIDER, is_member=False)
    res = client.get(f"/api/content/video/status/{JOB_ID}", headers=AUTHED)
    assert res.status_code == 403
    assert "enhanced_prompt" not in res.text


def test_video_status_unknown_job_is_404_for_member(client, monkeypatch):
    _as_user(monkeypatch, MEMBER, is_member=True)
    assert client.get("/api/content/video/status/deadbeef", headers=AUTHED).status_code == 404


def test_video_debug_denied_to_non_admin(client, monkeypatch):
    """Org membership is not enough — debug leaks fal.ai queue URLs + raw bodies."""
    _as_user(monkeypatch, MEMBER, is_member=True)
    res = client.get(f"/api/content/video/debug/{JOB_ID}", headers=AUTHED)
    assert res.status_code == 403
    assert "queue.fal.run" not in res.text
