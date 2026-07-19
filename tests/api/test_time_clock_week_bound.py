"""time-clock weekly views must bound the HIGH end ([week_start, +7d))."""
from src.api.routes.time_clock import _week_end, _within_week


def test_week_end():
    assert _week_end("2026-07-01") == "2026-07-08"
    assert _week_end("") is None
    assert _week_end("not-a-date") is None


def test_within_week_bounds_both_ends():
    rows = [
        {"clock_in_at": "2026-07-01T09:00:00+00:00"},  # start day — kept
        {"clock_in_at": "2026-07-07T23:59:00+00:00"},  # last day — kept
        {"clock_in_at": "2026-07-08T00:00:00+00:00"},  # next week — dropped
        {"clock_in_at": "2026-08-01T09:00:00+00:00"},  # far future — dropped
    ]
    kept = _within_week(rows, "2026-07-01")
    assert [r["clock_in_at"][:10] for r in kept] == ["2026-07-01", "2026-07-07"]


def test_within_week_noop_without_week():
    rows = [{"clock_in_at": "2026-07-01T09:00:00+00:00"}]
    assert _within_week(rows, "") == rows
