"""Camera event detection: the rules that stop it becoming noise.

Aidan chose to ship all six detectors now, three of which are heuristics, in
full knowledge that a feed of phantom spills is what kills a feature like
this. These tests cover the three mechanisms that make that survivable —
persistence, dedupe, and never reporting a person as an object — because
those are what stand between "useful" and "ignored by Friday".
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "edge"))

pytest.importorskip("cv2")
from event_detectors import (  # noqa: E402
    CONFIDENCE, HOLD_SECONDS, EventDetectors, _overlaps, _rect,
)

ZONES = {
    "checkout": {"x1": 0.0, "y1": 0.0, "x2": 0.5, "y2": 0.5},
    "waiting_area": {"x1": 0.5, "y1": 0.0, "x2": 1.0, "y2": 0.5},
    "floor": {"x1": 0.0, "y1": 0.5, "x2": 1.0, "y2": 1.0},
}


def det(hours=None):
    return EventDetectors("cam-1", ZONES, hours or {"start": "00:00", "end": "23:59"})


class TestZoneGeometry:
    def test_normalised_zones_scale_to_the_frame(self):
        assert _rect({"x1": 0, "y1": 0, "x2": 0.5, "y2": 0.5}, 200, 100) == (0, 0, 100, 50)

    def test_native_pixel_zones_pass_through(self):
        assert _rect({"x1": 10, "y1": 10, "x2": 90, "y2": 90}, 200, 100) == (10, 10, 90, 90)

    def test_a_degenerate_zone_is_dropped(self):
        # A zero-width zone would make every area fraction a division by zero
        # and report constantly.
        assert _rect({"x1": 0.5, "y1": 0.5, "x2": 0.5, "y2": 0.5}, 200, 100) is None
        assert _rect({}, 200, 100) is None


class TestPersistence:
    def test_nothing_fires_on_a_single_frame(self):
        d = det()
        assert d._hold("spill", "floor", True, datetime.now(timezone.utc)) is None

    def test_it_fires_once_the_hold_elapses(self):
        d = det()
        t0 = datetime.now(timezone.utc)
        assert d._hold("spill", "floor", True, t0) is None
        later = t0 + timedelta(seconds=HOLD_SECONDS["spill"] + 1)
        assert d._hold("spill", "floor", True, later) is not None

    def test_a_candidate_that_goes_away_resets(self):
        # THE rule that stops a person walking through a zone accumulating
        # toward a spill over the course of an afternoon.
        d = det()
        t0 = datetime.now(timezone.utc)
        d._hold("spill", "floor", True, t0)
        d._hold("spill", "floor", False, t0 + timedelta(seconds=10))
        late = t0 + timedelta(seconds=HOLD_SECONDS["spill"] + 1)
        assert d._hold("spill", "floor", True, late) is None

    def test_one_spill_is_one_event(self):
        # Without this a detector that keeps seeing the same puddle files a
        # new row every frame and the feed is unusable within the hour.
        d = det()
        t0 = datetime.now(timezone.utc)
        d._hold("spill", "floor", True, t0)
        fired = t0 + timedelta(seconds=HOLD_SECONDS["spill"] + 1)
        assert d._hold("spill", "floor", True, fired) is not None
        assert d._hold("spill", "floor", True, fired + timedelta(seconds=30)) is None

    def test_it_reports_again_much_later_if_still_there(self):
        d = det()
        t0 = datetime.now(timezone.utc)
        d._hold("spill", "floor", True, t0)
        fired = t0 + timedelta(seconds=HOLD_SECONDS["spill"] + 1)
        d._hold("spill", "floor", True, fired)
        assert d._hold("spill", "floor", True, fired + timedelta(seconds=1000)) is not None


class TestOpeningHours:
    def test_a_normal_day(self):
        d = det({"start": "09:00", "end": "17:00"})
        assert d._is_open(datetime(2026, 8, 16, 12, 0).astimezone())
        assert not d._is_open(datetime(2026, 8, 16, 3, 0).astimezone())

    def test_hours_that_cross_midnight(self):
        # A late bar closing at 2am. Treating start<=now<=end here would call
        # the entire trading night "after hours" and alarm every evening.
        d = det({"start": "17:00", "end": "02:00"})
        assert d._is_open(datetime(2026, 8, 16, 23, 0).astimezone())
        assert d._is_open(datetime(2026, 8, 16, 1, 0).astimezone())
        assert not d._is_open(datetime(2026, 8, 16, 10, 0).astimezone())


class TestPhoneUse:
    def _frame(self):
        return np.zeros((100, 200, 3), dtype=np.uint8)

    def test_a_handset_alone_is_not_phone_use(self):
        # A phone left on the counter is not somebody using one. Reporting it
        # is the fastest way to lose trust in the whole feed.
        d = det()
        phone = [(10, 10, 30, 30)]
        t = datetime.now(timezone.utc)
        d._phone_use([], phone, 200, 100, t)
        later = t + timedelta(seconds=HOLD_SECONDS["phone_use"] + 1)
        assert d._phone_use([], phone, 200, 100, later) == []

    def test_a_handset_held_by_someone_in_a_work_zone_fires(self):
        d = det()
        person = [(5, 5, 60, 60)]
        phone = [(10, 10, 30, 30)]
        t = datetime.now(timezone.utc)
        assert d._phone_use(person, phone, 200, 100, t) == []
        later = t + timedelta(seconds=HOLD_SECONDS["phone_use"] + 1)
        out = d._phone_use(person, phone, 200, 100, later)
        assert len(out) == 1
        assert out[0]["kind"] == "phone_use"
        assert out[0]["zone"] == "checkout"

    def test_it_names_no_one(self):
        d = det()
        t = datetime.now(timezone.utc)
        d._phone_use([(5, 5, 60, 60)], [(10, 10, 30, 30)], 200, 100, t)
        out = d._phone_use([(5, 5, 60, 60)], [(10, 10, 30, 30)], 200, 100,
                           t + timedelta(seconds=HOLD_SECONDS["phone_use"] + 1))
        # The API has no column for a person and neither does the payload.
        for banned in ("person_id", "track_id", "staff_id", "name", "face"):
            assert banned not in out[0]


class TestUnattended:
    def test_needs_both_zones_to_mean_anything(self):
        # Without a waiting area, an empty counter is a quiet afternoon.
        d = EventDetectors("cam-1", {"checkout": ZONES["checkout"]}, None)
        t = datetime.now(timezone.utc)
        assert d._unattended([], 200, 100, t) == []

    def test_customers_waiting_with_nobody_serving(self):
        d = det()
        waiting = [(150, 10, 190, 40)]   # in waiting_area, not checkout
        t = datetime.now(timezone.utc)
        assert d._unattended(waiting, 200, 100, t) == []
        later = t + timedelta(seconds=HOLD_SECONDS["unattended"] + 1)
        out = d._unattended(waiting, 200, 100, later)
        assert len(out) == 1 and out[0]["kind"] == "unattended"

    def test_a_staffed_counter_is_silent(self):
        d = det()
        both = [(150, 10, 190, 40), (10, 10, 40, 40)]  # waiting + at checkout
        t = datetime.now(timezone.utc)
        d._unattended(both, 200, 100, t)
        later = t + timedelta(seconds=HOLD_SECONDS["unattended"] + 1)
        assert d._unattended(both, 200, 100, later) == []


class TestAfterHours:
    def test_a_closed_shop_reports_movement_and_nothing_else(self):
        d = det({"start": "09:00", "end": "17:00"})
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        # Force the closed branch by asking at 3am.
        import event_detectors as mod
        real_now = mod._now
        mod._now = lambda: datetime(2026, 8, 16, 3, 0, tzinfo=timezone.utc).astimezone()
        try:
            d.run(frame, [[5, 5, 40, 40, 0.9]], [])
            mod._now = lambda: (datetime(2026, 8, 16, 3, 0, tzinfo=timezone.utc)
                                + timedelta(seconds=HOLD_SECONDS["after_hours"] + 1)).astimezone()
            out = d.run(frame, [[5, 5, 40, 40, 0.9]], [])
        finally:
            mod._now = real_now
        kinds = {e["kind"] for e in out}
        assert kinds == {"after_hours"}, kinds


class TestContract:
    def test_every_kind_declares_a_hold_and_a_confidence(self):
        # A kind missing either falls back to a default and silently behaves
        # unlike everything around it.
        assert set(HOLD_SECONDS) == set(CONFIDENCE)

    def test_heuristics_claim_less_than_real_detections(self):
        # The number the merchant reads next to the event has to be honest
        # about which half of the feature produced it.
        for heuristic in ("spill", "product_loss", "blocked_exit"):
            for real in ("phone_use", "unattended", "after_hours"):
                assert CONFIDENCE[heuristic] < CONFIDENCE[real]

    def test_the_server_would_accept_every_confidence_we_emit(self):
        from src.services.vision_events import MIN_CONFIDENCE
        for kind, c in CONFIDENCE.items():
            assert c >= MIN_CONFIDENCE, f"{kind} would be dropped by the API"

    def test_kinds_match_the_api_vocabulary(self):
        from src.services.vision_events import EVENT_KINDS
        assert set(CONFIDENCE) == set(EVENT_KINDS)

    def test_overlap_is_exclusive_at_the_edges(self):
        assert _overlaps((0, 0, 10, 10), (5, 5, 15, 15))
        assert not _overlaps((0, 0, 10, 10), (10, 0, 20, 10))


class TestItShipsWhereMerchantsRunIt:
    """The connector is the agent that actually reaches a merchant.

    It runs as one Docker line on a POS back-office PC they already own.
    Detection that exists only in the other agent — the dedicated-hardware
    flavour — reaches nobody, and both images have to physically contain the
    module or the import fails at runtime on their counter.
    """

    def _repo(self):
        from pathlib import Path
        return Path(__file__).resolve().parents[2]

    def test_the_connector_runs_the_detectors(self):
        src = (self._repo() / "edge/connector/local_agent.py").read_text()
        assert "EventDetectors(" in src, "the connector does not run event detection"
        assert "post_events" in src, "the connector cannot report what it saw"

    def test_both_images_contain_the_module(self):
        connector = (self._repo() / "edge/connector/local_agent.Dockerfile").read_text()
        assert "event_detectors.py" in connector, "connector image would fail to import it"
        edge = (self._repo() / "edge/Dockerfile").read_text()
        assert "event_detectors.py" in edge, "edge image would fail to import it"

    def test_the_shared_detector_keeps_phone_boxes(self):
        # The model already runs every class and the person mask threw the
        # phones away. Without them the connector cannot see a handset.
        src = (self._repo() / "src/camera/detector.py").read_text()
        assert "PHONE_CLASS = 67" in src
        assert '"phones"' in src, "phones never reach the caller"
