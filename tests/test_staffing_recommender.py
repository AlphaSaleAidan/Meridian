"""Unit tests for the agentic staffing recommendation engine."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai.scheduling.staffing_recommender import (  # noqa: E402
    WeatherDay,
    build_recommendations,
)

# Day convention: 0=Mon … 6=Sun.
# Build a clear two-hour peak window on Saturday (day 5) at high intensity.
SAT_PEAKS = [
    {"day": 5, "hour": 11, "intensity": 0.9},
    {"day": 5, "hour": 12, "intensity": 0.85},
]


def test_peaks_only_produces_critical_window():
    res = build_recommendations(peaks=SAT_PEAKS, coverage={})
    recs = res["recommendations"]
    assert len(recs) == 1
    r = recs[0]
    assert r["day_of_week"] == 5
    assert r["start_time"] == "11:00"
    assert r["end_time"] == "13:00"
    assert r["priority"] == "critical"
    assert any(f["kind"] == "peak" for f in r["factors"])
    assert res["signals"] == []


def test_covered_peak_is_dropped():
    coverage = {(5, 11): 3, (5, 12): 3}
    res = build_recommendations(peaks=SAT_PEAKS, coverage=coverage)
    assert res["recommendations"] == []


def test_holiday_bumps_priority_and_adds_factor():
    # Moderate peak that would normally be "recommended"…
    peaks = [
        {"day": 2, "hour": 14, "intensity": 0.6},
        {"day": 2, "hour": 15, "intensity": 0.55},
    ]
    res = build_recommendations(
        peaks=peaks, coverage={}, holidays_by_dow={2: "Canada Day"}
    )
    r = res["recommendations"][0]
    assert r["priority"] == "critical"  # bumped from recommended
    assert any(f["kind"] == "holiday" and "Canada Day" in f["label"] for f in r["factors"])
    assert any(s["kind"] == "holiday" for s in res["signals"])


def test_holiday_only_day_seeds_default_window():
    # No peaks at all, but Wednesday is a holiday → default mid-day window.
    res = build_recommendations(
        peaks=[], coverage={}, holidays_by_dow={2: "Christmas Day"}
    )
    recs = res["recommendations"]
    assert len(recs) == 1
    r = recs[0]
    assert r["day_of_week"] == 2
    assert r["start_time"] == "11:00"
    assert r["end_time"] == "15:00"
    assert r["priority"] == "recommended"
    assert r["peak_intensity"] == 0.0


def test_holiday_only_day_skipped_when_already_covered():
    coverage = {(2, h): 1 for h in range(11, 15)}
    res = build_recommendations(
        peaks=[], coverage=coverage, holidays_by_dow={2: "Christmas Day"}
    )
    assert res["recommendations"] == []


def test_rain_with_negative_impact_eases_priority():
    weather = {5: WeatherDay(weathercode=61, precipitation=5.0, label="Slight rain")}
    res = build_recommendations(
        peaks=SAT_PEAKS, coverage={}, weather_by_dow=weather, rain_impact_pct=-20.0
    )
    r = res["recommendations"][0]
    assert r["priority"] == "recommended"  # demoted from critical
    assert any(f["kind"] == "weather" for f in r["factors"])
    assert any(s["kind"] == "weather" for s in res["signals"])


def test_rain_with_positive_impact_bumps_priority():
    # Start from a recommended-level peak so a bump is observable.
    peaks = [
        {"day": 5, "hour": 11, "intensity": 0.6},
        {"day": 5, "hour": 12, "intensity": 0.6},
    ]
    weather = {5: WeatherDay(weathercode=63, precipitation=8.0, label="Moderate rain")}
    res = build_recommendations(
        peaks=peaks, coverage={}, weather_by_dow=weather, rain_impact_pct=25.0
    )
    r = res["recommendations"][0]
    assert r["priority"] == "critical"


def test_weather_without_correlation_is_informational_only():
    weather = {5: WeatherDay(weathercode=61, precipitation=5.0, label="Slight rain")}
    res = build_recommendations(
        peaks=SAT_PEAKS, coverage={}, weather_by_dow=weather, rain_impact_pct=None
    )
    r = res["recommendations"][0]
    assert r["priority"] == "critical"  # unchanged
    assert any(f["kind"] == "weather" and "forecast" in f["label"] for f in r["factors"])


def test_clear_weather_adds_no_factor():
    weather = {5: WeatherDay(weathercode=0, precipitation=0.0, label="Clear sky")}
    res = build_recommendations(
        peaks=SAT_PEAKS, coverage={}, weather_by_dow=weather, rain_impact_pct=-30.0
    )
    r = res["recommendations"][0]
    assert all(f["kind"] != "weather" for f in r["factors"])
    assert res["signals"] == []


def test_recommendations_sorted_by_priority():
    peaks = [
        {"day": 1, "hour": 9, "intensity": 0.3},   # optional
        {"day": 1, "hour": 10, "intensity": 0.3},
        {"day": 3, "hour": 12, "intensity": 0.9},  # critical
        {"day": 3, "hour": 13, "intensity": 0.9},
    ]
    res = build_recommendations(peaks=peaks, coverage={})
    priorities = [r["priority"] for r in res["recommendations"]]
    assert priorities[0] == "critical"
