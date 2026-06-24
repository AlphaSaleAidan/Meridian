"""Unit tests for the overlay emitter transforms (Phase 6). Pure — runs in CI."""
from src.camera.streaming.overlay_emitter import (
    boxes_from_detection, build_overlay_frame, insight_to_xref, clip_evidence_url,
)


def _det():
    return {
        "camera_id": "cam1",
        "frame_shape": [100, 200],  # h, w
        "persons": [
            {"tracker_id": 7, "bbox": [20, 10, 60, 50], "confidence": 0.9},
        ],
    }


def test_boxes_normalized():
    b = boxes_from_detection(_det())[0]
    assert b["id"] == 7
    assert b["x"] == 0.1 and b["y"] == 0.1      # 20/200, 10/100
    assert b["w"] == 0.2 and b["h"] == 0.4      # 40/200, 40/100
    assert b["conf"] == 0.9


def test_build_frame_has_ts_and_boxes():
    f = build_overlay_frame(_det(), exceptions=[{"id": 1, "x": 0.5, "y": 0.5, "kind": "loiter"}])
    assert f["frame_ts"] > 0
    assert len(f["boxes"]) == 1
    assert f["exceptions"][0]["kind"] == "loiter"
    assert f["xref"] == []


def test_insight_to_xref_requires_person_linkage():
    assert insight_to_xref({"data": {}}) is None
    x = insight_to_xref({"data": {"tracker_id": 7, "basket_cents": 2400, "item_count": 3, "checked_out": True}})
    assert x["basketCents"] == 2400 and x["items"] == 3 and x["checkedOut"] is True


def test_evidence_url():
    u = clip_evidence_url("https://api.meridian.tips/", "cam1", "T1", "T2", "biz_A")
    assert u == "https://api.meridian.tips/api/cameras/cam1/clip?from=T1&to=T2&org_id=biz_A"
