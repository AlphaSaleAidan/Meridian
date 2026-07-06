"""
Tests for zero-hardware camera connect — Path A (phone/tablet as camera).

Covers:
  - HMAC frame token mint/verify (bind camera_id+org_id, reject tampered/expired/cross-camera)
  - POST /api/vision/camera/frame endpoint: rejects bad token (401), oversize (413),
    non-image content-type (415), garbage/undecodable payload (422), and on a valid
    token + valid frame feeds the pipeline (mocked) and returns the person count.
  - The frame router carries NO require_org_access JWT dependency (browsers have no JWT;
    they authenticate with the per-camera frame token instead).

Run:
    cd <repo> && python -m pytest tests/api/test_browser_camera_frame.py -v
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types
from unittest.mock import patch

import pytest
from fastapi import HTTPException, UploadFile

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _REPO_ROOT)

# Ensure a signing secret exists before importing the module under test.
os.environ.setdefault("VISION_INGEST_TOKEN", "test-ingest-secret")

# frame_ingest lazy-imports the heavy vision deps (cv2/supervision/ultralytics) inside
# its functions, but importing it via `src.camera` would trigger src/camera/__init__.py
# which eagerly pulls supervision. To keep this unit test runnable in a bare env AND in
# CI (where the deps exist), stub any missing heavy module and import frame_ingest by
# file path so the package __init__ chain is bypassed. When the real deps are present
# (CI), the stubs are not installed and the real modules are used.
for _mod in ("cv2", "supervision", "ultralytics"):
    if _mod not in sys.modules:
        try:
            __import__(_mod)
        except Exception:
            stub = types.ModuleType(_mod)
            if _mod == "cv2":
                stub.imdecode = lambda *a, **k: None
                stub.IMREAD_COLOR = 1
            if _mod == "ultralytics":
                # people_counter does `from ultralytics import YOLO` at module load.
                stub.YOLO = type("YOLO", (), {"__init__": lambda self, *a, **k: None})
            if _mod == "supervision":
                # Attributes referenced at module load / class-body import time.
                class _Any:
                    def __init__(self, *a, **k):
                        pass

                    def __getattr__(self, _n):
                        return _Any()

                stub.ByteTrack = _Any
                stub.HeatMapAnnotator = _Any
                stub.PolygonZone = _Any
                stub.LineZone = _Any
                stub.Point = _Any
                stub.Detections = _Any
                stub.Position = _Any()
            sys.modules[_mod] = stub

_spec = importlib.util.spec_from_file_location(
    "meridian_frame_ingest_under_test",
    os.path.join(_REPO_ROOT, "src", "camera", "frame_ingest.py"),
)
frame_ingest = importlib.util.module_from_spec(_spec)
# frame_ingest uses relative imports (`from .detector import ...`) only INSIDE functions,
# so loading it standalone is safe; set its package so those lazy imports resolve if hit.
frame_ingest.__package__ = "src.camera"
_spec.loader.exec_module(frame_ingest)

FrameIngestError = frame_ingest.FrameIngestError
mint_frame_token = frame_ingest.mint_frame_token
token_hash = frame_ingest.token_hash
verify_frame_token = frame_ingest.verify_frame_token


def _run(coro):
    return asyncio.run(coro)


CAM = "11111111-1111-1111-1111-111111111111"
ORG = "22222222-2222-2222-2222-222222222222"


# ─────────────────────────── token mint / verify ───────────────────────────
def test_token_roundtrips_for_matching_camera_and_org():
    token = mint_frame_token(CAM, ORG)
    assert verify_frame_token(token, CAM, ORG) is True


def test_token_rejected_for_wrong_camera():
    token = mint_frame_token(CAM, ORG)
    assert verify_frame_token(token, "99999999-9999-9999-9999-999999999999", ORG) is False


def test_token_rejected_for_wrong_org():
    token = mint_frame_token(CAM, ORG)
    assert verify_frame_token(token, CAM, "88888888-8888-8888-8888-888888888888") is False


def test_tampered_token_rejected():
    token = mint_frame_token(CAM, ORG)
    tampered = token[:-1] + ("0" if token[-1] != "0" else "1")
    assert verify_frame_token(tampered, CAM, ORG) is False


def test_expired_token_rejected():
    # issued 40 days ago; TTL is 30 days
    old = int(__import__("time").time()) - 60 * 60 * 24 * 40
    token = mint_frame_token(CAM, ORG, issued_at=old)
    assert verify_frame_token(token, CAM, ORG) is False


def test_garbage_token_rejected():
    for bad in ("", "not-a-token", "123", "123.deadbeef", "abc.def"):
        assert verify_frame_token(bad, CAM, ORG) is False


def test_token_hash_is_sha256_hex():
    h = token_hash("abc")
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)


def test_mint_fails_closed_without_secret():
    with patch.object(frame_ingest, "_secret", return_value=""):
        with pytest.raises(RuntimeError):
            mint_frame_token(CAM, ORG)


# ─────────────────────────── ingest_browser_frame guards ───────────────────────────
def test_ingest_rejects_empty_frame():
    with pytest.raises(FrameIngestError):
        frame_ingest.ingest_browser_frame(ORG, CAM, b"")


def test_ingest_rejects_oversize_frame():
    big = b"\x00" * (frame_ingest.MAX_FRAME_BYTES + 1)
    with pytest.raises(FrameIngestError):
        frame_ingest.ingest_browser_frame(ORG, CAM, big)


def test_ingest_rejects_undecodable_frame():
    # Small but not a valid image → cv2.imdecode returns None → FrameIngestError.
    with pytest.raises(FrameIngestError):
        frame_ingest.ingest_browser_frame(ORG, CAM, b"this is not a jpeg")


def test_ingest_feeds_pipeline_on_valid_frame():
    """A decodable frame is routed to the cached per-camera worker (the real
    detector/counter/writer). We patch _get_worker so the test doesn't need
    ultralytics/cv2 weights, and assert the worker was invoked with the frame."""
    calls = {}

    class FakeWorker:
        def process(self, frame):
            calls["frame_shape"] = getattr(frame, "shape", None)
            return {"persons": 3, "density": "low"}

    # Patch decode so we don't need a real JPEG, and the worker so we don't need YOLO.
    with patch("cv2.imdecode", return_value=_fake_frame()), \
         patch.object(frame_ingest, "_get_worker", return_value=FakeWorker()):
        out = frame_ingest.ingest_browser_frame(ORG, CAM, b"\xff\xd8\xff\xe0jpegish")

    assert out["persons"] == 3
    assert out["density"] == "low"
    assert calls["frame_shape"] is not None  # the decoded frame reached the pipeline


def _fake_frame():
    import numpy as np
    return np.zeros((720, 1280, 3), dtype=np.uint8)


# ─────────────────────────── endpoint: /api/vision/camera/frame ───────────────────────────
def _upload(content: bytes, content_type: str = "image/jpeg") -> UploadFile:
    import io
    from starlette.datastructures import Headers
    return UploadFile(
        file=io.BytesIO(content),
        filename="frame.jpg",
        headers=Headers({"content-type": content_type}),
    )


def _endpoint_module():
    """Import the real endpoint module (which pulls the real src.camera.frame_ingest).
    The heavy-dep stubs installed at the top of this file let src.camera.__init__ load
    in a bare env; in CI the real deps are used."""
    import src.api.routes.browser_camera as mod
    import src.camera.frame_ingest as real_fi
    return mod, real_fi


def _call_endpoint(token, frame_upload):
    mod, _ = _endpoint_module()
    return _run(mod.ingest_frame(camera_id=CAM, org_id=ORG, token=token, frame=frame_upload))


def test_endpoint_rejects_invalid_token():
    with pytest.raises(HTTPException) as exc:
        _call_endpoint("bogus.token", _upload(b"\xff\xd8\xff\xe0"))
    assert exc.value.status_code == 401


def test_endpoint_rejects_non_image_content_type():
    token = mint_frame_token(CAM, ORG)
    with pytest.raises(HTTPException) as exc:
        _call_endpoint(token, _upload(b"hello", content_type="text/plain"))
    assert exc.value.status_code == 415


def test_endpoint_rejects_oversize_frame():
    _, real_fi = _endpoint_module()
    token = mint_frame_token(CAM, ORG)
    big = b"\x00" * (real_fi.MAX_FRAME_BYTES + 10)
    with pytest.raises(HTTPException) as exc:
        _call_endpoint(token, _upload(big))
    assert exc.value.status_code == 413


def test_endpoint_rejects_garbage_frame_422():
    token = mint_frame_token(CAM, ORG)
    with pytest.raises(HTTPException) as exc:
        _call_endpoint(token, _upload(b"not a real jpeg payload"))
    assert exc.value.status_code == 422


def test_endpoint_ok_on_valid_token_and_frame():
    _, real_fi = _endpoint_module()
    token = mint_frame_token(CAM, ORG)

    class FakeWorker:
        def process(self, frame):
            return {"persons": 2, "density": "low"}

    with patch("cv2.imdecode", return_value=_fake_frame()), \
         patch.object(real_fi, "_get_worker", return_value=FakeWorker()):
        out = _call_endpoint(token, _upload(b"\xff\xd8\xff\xe0jpegish"))

    assert out["status"] == "ok"
    assert out["camera_id"] == CAM
    assert out["persons"] == 2


def test_frame_router_has_no_jwt_dependency():
    """The browser frame endpoint must NOT be gated by require_org_access — a phone
    has no Supabase JWT; it authenticates with the per-camera frame token."""
    from src.api.routes.browser_camera import router
    dep_names = {getattr(d.dependency, "__name__", "") for d in router.dependencies}
    assert "require_org_access" not in dep_names
