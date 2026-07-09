"""End-to-end test of the one-click LOCAL processing loop (no hardware, no cloud
media gateway): frame -> pipeline -> 5-min bucket -> POST /api/vision/ingest/traffic
with a per-org device token -> 200 + metrics written.

This is the path the merchant runs on their own PC/POS. We mock only the camera
frames + the YOLO detector/counter (so the test needs no GPU / model), and route
the HTTP through the REAL vision_ingest router + device-token auth.

Run: /root/Meridian/.venv/bin/python -m pytest tests/edge/test_local_agent.py -v
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import src.api.routes.vision_ingest as vi  # noqa: E402
from src.camera.device_tokens import hash_token  # noqa: E402
from edge.connector import local_agent as la  # noqa: E402

ORG = "11111111-1111-1111-1111-111111111111"
CAM = "33333333-3333-3333-3333-333333333333"
TOKEN = "mvd_local_agent_token"
HASH = hash_token(TOKEN)


class StubDB:
    def __init__(self):
        self.writes = []

    async def select(self, table, columns="*", filters=None, order=None, limit=None, offset=None):
        filters = filters or {}
        if table == "vision_device_tokens" and filters.get("token_hash") == f"eq.{HASH}":
            return [{"id": "tok", "org_id": ORG, "site_id": None, "revoked": False}]
        return []

    async def update(self, *a, **k):
        return [{"id": "tok"}]

    async def upsert(self, table, row, on_conflict=None):
        self.writes.append((table, row))
        return [row]

    async def insert(self, table, row):
        self.writes.append((table, row))
        return [dict(row, id="x")]


class FakeCounter:
    """Stand-in for MeridianPeopleCounter: 2 people in frame, 1 entry crossing."""
    zone_configs: dict = {}

    def process_frame(self, frame, precomputed_detections=None):
        class R:
            total_count = 2
            entries_this_frame = 1
            exits_this_frame = 0
            zone_counts: dict = {}
            tracked_ids = [1, 2]
        return R()

    def flush_dwell(self, ids):
        return []


class FakeDetector:
    def process_frame(self, frame, merchant_id, camera_id):
        return {"persons": [], "total_detected": 2}


@pytest.fixture
def ingest_via_api(monkeypatch):
    monkeypatch.delenv("VISION_INGEST_TOKEN", raising=False)
    stub = StubDB()
    monkeypatch.setattr(vi, "_get_db", lambda: stub)
    app = FastAPI()
    app.include_router(vi.router)
    tc = TestClient(app, raise_server_exceptions=False)
    tc.headers.update({"X-Device-Token": TOKEN})  # the agent's device auth
    client = la.IngestClient("http://testserver", TOKEN, ORG)
    client._http = tc  # route the agent's posts through the real API
    return client, stub


def test_local_loop_posts_real_metrics(ingest_via_api):
    ingest, stub = ingest_via_api
    ok, buf = cv2.imencode(".jpg", np.zeros((64, 64, 3), np.uint8))
    jpeg = buf.tobytes()

    worker = la.CameraWorker(
        CAM, ORG, "front-door", ingest,
        frame_source=lambda name: jpeg,
        bucket_sec=1,
        _detector=FakeDetector(),
        _counter=FakeCounter(),
    )

    t0 = 1_000_000.0
    assert worker.tick(now=t0) is None            # opens the bucket, nothing flushed yet
    metrics = worker.tick(now=t0 + 1.5)           # bucket_sec elapsed -> flush + POST

    assert metrics is not None, "a bucket should have flushed"
    assert metrics["entries"] >= 1
    assert metrics["occupancy_peak"] == 2
    assert metrics["org_id"] == ORG and metrics["camera_id"] == CAM
    # The POST actually reached the API and wrote a vision_traffic row.
    assert any(t == "vision_traffic" for t, _ in stub.writes)


def test_cross_org_token_cannot_write(ingest_via_api, monkeypatch):
    """A per-org token posting another org's metrics is rejected by the API (403)."""
    ingest, stub = ingest_via_api
    other = dict(org_id="99999999-9999-9999-9999-999999999999", camera_id=CAM,
                 bucket="2026-07-09T14:00:00+00:00", entries=5, exits=4, occupancy_avg=3)
    assert ingest.post_traffic(other) is False
    assert stub.writes == []


def test_bucket_ignores_empty_periods():
    b = la.TrafficBucket(bucket_sec=300)
    # no adds -> nothing to flush
    assert b.flush(ORG, CAM, now=1000.0) is None
