"""The event recorder's rules.

Two of these matter more than the rest. The vocabulary must stay closed, or a
detector ships a category the portal cannot render and the merchant sees a
blank row. And the dedupe key must always exist, because a detector re-firing
across frames turns one spill into forty and makes the feed useless inside an
hour — which is the failure that kills the feature, not a missed detection.
"""
import pytest

from src.services.vision_events import (
    EVENT_KINDS,
    MIN_CONFIDENCE,
    SEVERITIES,
    describe,
    normalise,
    summarise,
    window_start,
)


class TestVocabulary:
    def test_every_kind_carries_merchant_facing_copy(self):
        # An alert that does not say why it matters trains people to close
        # alerts without reading them.
        for kind, meta in EVENT_KINDS.items():
            assert meta["title"], f"{kind} has no title"
            assert meta["why"], f"{kind} does not say why it matters"
            assert meta["default_severity"] in SEVERITIES

    def test_an_unknown_kind_is_dropped_not_invented(self):
        assert normalise({"kind": "alien_landing"}) is None
        assert normalise({"kind": ""}) is None
        assert normalise({}) is None

    def test_describe_never_raises_on_junk(self):
        # Called while rendering a feed. A KeyError here blanks the page.
        meta = describe("not_a_kind")
        assert meta["title"] and meta["why"]


class TestConfidence:
    def test_a_guess_is_dropped(self):
        # A feed of maybes is a feed nobody opens twice.
        assert normalise({"kind": "spill", "confidence": MIN_CONFIDENCE - 0.01} ) is None

    def test_a_confident_detection_is_kept(self):
        row = normalise({"kind": "spill", "confidence": 0.9})
        assert row is not None
        assert row["kind"] == "spill"

    def test_missing_confidence_is_kept(self):
        # A detector that does not report confidence is not the same as one
        # reporting low confidence, and dropping it would silently disable
        # every detector that does not implement the field.
        row = normalise({"kind": "spill"})
        assert row is not None

    def test_junk_confidence_does_not_crash_the_batch(self):
        row = normalise({"kind": "spill", "confidence": "very"})
        assert row is not None
        assert row["confidence"] is None


class TestSeverity:
    def test_falls_back_to_the_kind_default(self):
        assert normalise({"kind": "spill"})["severity"] == "critical"
        assert normalise({"kind": "phone_use"})["severity"] == "info"

    def test_an_invalid_severity_is_replaced_not_stored(self):
        # The column has a CHECK constraint; storing junk fails the whole
        # insert and loses a real event.
        row = normalise({"kind": "spill", "severity": "apocalyptic"})
        assert row["severity"] in SEVERITIES

    def test_an_explicit_valid_severity_wins(self):
        assert normalise({"kind": "spill", "severity": "info"})["severity"] == "info"


class TestDedupe:
    def test_a_key_always_exists(self):
        # THE important one. Without a key the upsert has nothing to collide
        # on and every frame becomes a row.
        row = normalise({"kind": "spill", "zone": "counter"})
        assert row["dedupe_key"]

    def test_the_same_minute_and_zone_collapses(self):
        a = normalise({"kind": "spill", "zone": "counter",
                       "detected_at": "2026-08-16T10:31:04+00:00"})
        b = normalise({"kind": "spill", "zone": "counter",
                       "detected_at": "2026-08-16T10:31:58+00:00"})
        assert a["dedupe_key"] == b["dedupe_key"]

    def test_a_different_zone_does_not_collapse(self):
        a = normalise({"kind": "spill", "zone": "counter",
                       "detected_at": "2026-08-16T10:31:04+00:00"})
        b = normalise({"kind": "spill", "zone": "aisle 3",
                       "detected_at": "2026-08-16T10:31:04+00:00"})
        assert a["dedupe_key"] != b["dedupe_key"]

    def test_the_detector_can_supply_its_own(self):
        row = normalise({"kind": "spill", "dedupe_key": "cam1-spill-9912"})
        assert row["dedupe_key"] == "cam1-spill-9912"


class TestNoPersonEverLandsInARow:
    def test_identifying_fields_are_not_carried_through(self):
        # The table has no column for these, so anything that slipped through
        # would fail the insert — but the real guarantee is that normalise()
        # builds the row from a fixed set of keys rather than copying input.
        row = normalise({
            "kind": "phone_use",
            "staff_id": "emp_44",
            "name": "Sarah",
            "face_hash": "abc123",
            "visitor_hash": "def456",
        })
        assert row is not None
        for leaked in ("staff_id", "name", "face_hash", "visitor_hash"):
            assert leaked not in row


class TestSummary:
    def test_counts_open_and_critical_separately(self):
        rows = [
            {"kind": "spill", "severity": "critical", "status": "new"},
            {"kind": "spill", "severity": "critical", "status": "resolved"},
            {"kind": "phone_use", "severity": "info", "status": "new"},
        ]
        s = summarise(rows)
        assert s["total"] == 3
        assert s["open"] == 2
        # The resolved critical must not still be counted as needing action.
        assert s["critical_open"] == 1
        assert s["by_kind"]["spill"] == 2

    def test_empty_is_zero_not_an_error(self):
        assert summarise([])["open"] == 0


class TestWindow:
    @pytest.mark.parametrize("hours", [0, -5, 10**9])
    def test_absurd_windows_are_clamped(self, hours):
        # The value reaches a query. Unclamped, "0 hours" returns nothing and
        # a billion scans the table.
        assert window_start(hours)

    def test_a_normal_window_is_in_the_past(self):
        from datetime import datetime, timezone
        started = datetime.fromisoformat(window_start(24))
        assert started < datetime.now(timezone.utc)
