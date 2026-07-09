"""Device-auth for vision metric ingest — the fix that lets an on-site PC/POS
agent (or LAN connector) actually push camera metrics without a user JWT.

Before the fix, POST /api/vision/ingest/* was behind require_org_access (a
Supabase JWT), so every headless device got 401 and NO metrics landed. These
tests lock in: per-org device token works, cross-org is 403, bad/missing token
is 401, and the legacy global token still works.

Run: /root/Meridian/.venv/bin/python -m pytest tests/api/test_vision_ingest_auth.py -v
"""
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.camera import device_tokens as dt  # noqa: E402
import src.api.routes.vision_ingest as vi  # noqa: E402

ORG_A = "11111111-1111-1111-1111-111111111111"
ORG_B = "22222222-2222-2222-2222-222222222222"
CAM = "33333333-3333-3333-3333-333333333333"

# A per-org token for ORG_A and its stored hash.
TOKEN_A = "mvd_org_a_token"
HASH_A = dt.hash_token(TOKEN_A)


class StubDB:
    """Minimal async DB stub: resolves the ORG_A device token and records writes."""

    def __init__(self):
        self.writes = []

    async def select(self, table, columns="*", filters=None, order=None, limit=None, offset=None):
        filters = filters or {}
        if table == "vision_device_tokens":
            if filters.get("token_hash") == f"eq.{HASH_A}" and filters.get("revoked") == "eq.false":
                return [{"id": "tok-a", "org_id": ORG_A, "site_id": None, "revoked": False}]
            return []
        if table == "vision_cameras":
            return [{"id": CAM, "org_id": ORG_A, "rtsp_url": "rtsp://x", "zone_config": {}}]
        return []

    async def update(self, table, data, filters=None):
        return [{"id": "tok-a"}]

    async def upsert(self, table, row, on_conflict=None):
        self.writes.append((table, row))
        return [row]

    async def insert(self, table, row):
        self.writes.append((table, row))
        return [dict(row, id="new-1")]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("VISION_INGEST_TOKEN", raising=False)  # no legacy token by default
    stub = StubDB()
    monkeypatch.setattr(vi, "_get_db", lambda: stub)
    app = FastAPI()
    app.include_router(vi.router)
    c = TestClient(app, raise_server_exceptions=False)
    c._stub = stub
    return c


def _traffic_body(org):
    return {
        "org_id": org, "camera_id": CAM, "bucket": "2026-07-09T14:00:00+00:00",
        "entries": 12, "exits": 11, "occupancy_avg": 5,
    }


def test_missing_token_401(client):
    r = client.post("/api/vision/ingest/traffic", json=_traffic_body(ORG_A))
    assert r.status_code == 401
    assert client._stub.writes == []


def test_bad_token_401(client):
    r = client.post("/api/vision/ingest/traffic", json=_traffic_body(ORG_A),
                    headers={"X-Device-Token": "mvd_wrong"})
    assert r.status_code == 401
    assert client._stub.writes == []


def test_valid_per_org_token_writes(client):
    r = client.post("/api/vision/ingest/traffic", json=_traffic_body(ORG_A),
                    headers={"X-Device-Token": TOKEN_A})
    assert r.status_code == 200, r.text
    assert any(t == "vision_traffic" for t, _ in client._stub.writes)


def test_cross_org_token_403(client):
    # ORG_A's token trying to write ORG_B's data must be rejected before any write.
    r = client.post("/api/vision/ingest/traffic", json=_traffic_body(ORG_B),
                    headers={"X-Device-Token": TOKEN_A})
    assert r.status_code == 403
    assert client._stub.writes == []


def test_legacy_global_token_writes(client, monkeypatch):
    monkeypatch.setenv("VISION_INGEST_TOKEN", "legacy-global")
    r = client.post("/api/vision/ingest/traffic", json=_traffic_body(ORG_B),
                    headers={"X-Device-Token": "legacy-global"})
    # Legacy token is unbound (org_id=None) → allowed for any org (backward compat).
    assert r.status_code == 200, r.text


def test_device_camera_list_scoped_to_token_org(client):
    r = client.get("/api/vision/device/cameras", headers={"X-Device-Token": TOKEN_A})
    assert r.status_code == 200
    body = r.json()
    assert body["org_id"] == ORG_A and body["total"] == 1


def test_visits_ingest_valid_token(client):
    r = client.post("/api/vision/ingest/visits", headers={"X-Device-Token": TOKEN_A}, json={
        "org_id": ORG_A, "camera_id": CAM, "entered_at": "2026-07-09T14:00:00+00:00",
        "dwell_seconds": 42, "zones_visited": ["floor", "checkout"], "converted": True,
    })
    assert r.status_code == 200, r.text
    assert any(t == "vision_visits" for t, _ in client._stub.writes)
