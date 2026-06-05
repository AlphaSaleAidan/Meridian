"""Agentic staffing recommendation engine.

Pure-logic core that combines three demand signals into shift
recommendations for the schedule builder:

  1. Peak hours   — POS transaction intensity (the demand backbone)
  2. Holidays     — deterministic, country-aware surge / coverage flags
  3. Weather      — best-effort forecast that nudges coverage up or down

The engine performs no I/O. Callers gather the signals (peaks from the
POS heatmap, holidays from ``_compute_holidays``, weather from
``WeatherService``) and pass them in. This keeps the agent deterministic
and unit-testable, and lets the route layer own all network / DB access.

Day-of-week convention: 0 = Monday … 6 = Sunday (matches
``schedule_shifts.day_of_week`` and the frontend ``DAY_LABELS``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

# WMO weather codes the engine reasons about. Mirrored from weather_service
# so the engine has no import-time dependency on that module.
RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
SEVERE_CODES = {65, 67, 75, 82, 86, 95, 96, 99}

# Default coverage window for a holiday with no peak history (local hours).
HOLIDAY_DEFAULT_START = 11
HOLIDAY_DEFAULT_END = 15

# A merchant's rain revenue swing must clear this magnitude before it
# moves staffing priority (below it, rain is informational only).
RAIN_IMPACT_THRESHOLD = 10.0

PRIORITY_RANK = {"critical": 0, "recommended": 1, "optional": 2}


@dataclass
class WeatherDay:
    """Forecast for a single day within the planning week."""

    weathercode: int = 0
    precipitation: float = 0.0
    label: str = ""

    @property
    def severe(self) -> bool:
        return self.weathercode in SEVERE_CODES or self.precipitation > 10

    @property
    def rainy(self) -> bool:
        return self.weathercode in RAIN_CODES or self.precipitation > 2


@dataclass
class _Window:
    day: int
    start: int
    end: int
    peak_intensity: float
    priority: str
    factors: list[dict] = field(default_factory=list)


def _required_coverage(intensity: float) -> int:
    """How many staff this hour should be covered by, given intensity 0..1."""
    if intensity >= 0.75:
        return 3
    if intensity >= 0.5:
        return 2
    if intensity >= 0.25:
        return 1
    return 0


def _merge_contiguous(hours: list[int], min_run: int = 2) -> list[tuple[int, int]]:
    """Group sorted ints into [(start_inclusive, end_exclusive)] runs >= min_run."""
    if not hours:
        return []
    runs: list[tuple[int, int]] = []
    start = prev = hours[0]
    for h in hours[1:]:
        if h == prev + 1:
            prev = h
            continue
        if prev - start + 1 >= min_run:
            runs.append((start, prev + 1))
        start = prev = h
    if prev - start + 1 >= min_run:
        runs.append((start, prev + 1))
    return runs


def _base_priority(intensity: float) -> str:
    if intensity >= 0.75:
        return "critical"
    if intensity >= 0.5:
        return "recommended"
    return "optional"


def _bump(priority: str) -> str:
    return {"optional": "recommended", "recommended": "critical"}.get(priority, "critical")


def _demote(priority: str) -> str:
    return {"critical": "recommended", "recommended": "optional"}.get(priority, "optional")


def _peak_windows(
    peaks: list[dict],
    coverage: dict[tuple[int, int], int],
) -> dict[int, list[_Window]]:
    """Uncovered peak windows grouped by day-of-week."""
    by_day_hours: dict[int, list[tuple[int, float]]] = {}
    for p in peaks:
        need = _required_coverage(p["intensity"])
        if need <= 0:
            continue
        if need - coverage.get((p["day"], p["hour"]), 0) <= 0:
            continue
        by_day_hours.setdefault(p["day"], []).append((p["hour"], p["intensity"]))

    windows: dict[int, list[_Window]] = {}
    for day, hours_data in by_day_hours.items():
        hours_data.sort(key=lambda x: x[0])
        hours_only = [h for h, _ in hours_data]
        intensities = {h: i for h, i in hours_data}
        for start, end in _merge_contiguous(hours_only, min_run=2):
            window_intensities = [intensities[h] for h in range(start, end) if h in intensities]
            peak_intensity = max(window_intensities) if window_intensities else 0.0
            windows.setdefault(day, []).append(
                _Window(
                    day=day,
                    start=start,
                    end=end,
                    peak_intensity=round(peak_intensity, 3),
                    priority=_base_priority(peak_intensity),
                    factors=[{
                        "kind": "peak",
                        "label": f"{int(peak_intensity * 100)}% peak demand",
                    }],
                )
            )
    return windows


def _apply_holiday(window: _Window, holiday_name: str) -> None:
    """A holiday lifts demand — bump priority and record the factor."""
    window.priority = _bump(window.priority)
    window.factors.append({"kind": "holiday", "label": f"{holiday_name} holiday"})


def _apply_weather(window: _Window, weather: WeatherDay, rain_impact_pct: float | None) -> None:
    """Weather nudges staffing using the merchant's own rain/revenue history.

    With a known correlation we move priority (rain that lifts revenue bumps
    up; rain that cuts it eases down). Without one, weather is informational.
    """
    if not (weather.rainy or weather.severe):
        return
    cond = weather.label or ("Severe weather" if weather.severe else "Rain")

    if rain_impact_pct is not None and abs(rain_impact_pct) >= RAIN_IMPACT_THRESHOLD:
        pct = int(round(rain_impact_pct))
        if rain_impact_pct > 0:
            window.priority = _bump(window.priority)
            window.factors.append({"kind": "weather", "label": f"{cond} (+{pct}% typical)"})
        else:
            window.priority = _demote(window.priority)
            window.factors.append({"kind": "weather", "label": f"{cond} ({pct}% typical)"})
    else:
        window.factors.append({"kind": "weather", "label": f"{cond} forecast"})


def _reason(window: _Window) -> str:
    return " · ".join(f["label"] for f in window.factors)


def _to_rec(window: _Window) -> dict:
    return {
        "id": str(uuid4()),
        "day_of_week": window.day,
        "start_time": f"{window.start:02d}:00",
        "end_time": f"{window.end:02d}:00",
        "role": "any",
        "reason": _reason(window),
        "priority": window.priority,
        "peak_intensity": window.peak_intensity,
        "factors": window.factors,
    }


def build_recommendations(
    *,
    peaks: list[dict],
    coverage: dict[tuple[int, int], int],
    holidays_by_dow: dict[int, str] | None = None,
    weather_by_dow: dict[int, WeatherDay] | None = None,
    rain_impact_pct: float | None = None,
) -> dict:
    """Combine peaks + holidays + weather into ranked shift recommendations.

    Returns ``{"recommendations": [...], "signals": [...]}``.

    Holidays bump existing peak windows; a holiday with no peak history still
    seeds a default mid-day window so the day is never left uncovered. Weather
    only modulates windows that already exist — it never invents new ones.
    """
    holidays_by_dow = holidays_by_dow or {}
    weather_by_dow = weather_by_dow or {}

    windows_by_day = _peak_windows(peaks, coverage)

    # Apply holiday + weather signals to every peak-derived window.
    for day, windows in windows_by_day.items():
        holiday = holidays_by_dow.get(day)
        weather = weather_by_dow.get(day)
        for w in windows:
            if holiday:
                _apply_holiday(w, holiday)
            if weather is not None:
                _apply_weather(w, weather, rain_impact_pct)

    recommendations = [_to_rec(w) for ws in windows_by_day.values() for w in ws]

    # Holiday-only days: no peak window but the day is a holiday → seed a
    # default mid-day coverage window if it isn't already staffed.
    for day, name in holidays_by_dow.items():
        if windows_by_day.get(day):
            continue
        uncovered = any(
            coverage.get((day, h), 0) < 1
            for h in range(HOLIDAY_DEFAULT_START, HOLIDAY_DEFAULT_END)
        )
        if not uncovered:
            continue
        w = _Window(
            day=day,
            start=HOLIDAY_DEFAULT_START,
            end=HOLIDAY_DEFAULT_END,
            peak_intensity=0.0,
            priority="recommended",
            factors=[{"kind": "holiday", "label": f"{name} holiday hours"}],
        )
        weather = weather_by_dow.get(day)
        if weather is not None:
            _apply_weather(w, weather, rain_impact_pct)
        recommendations.append(_to_rec(w))

    recommendations.sort(
        key=lambda r: (PRIORITY_RANK.get(r["priority"], 9), r["day_of_week"], r["start_time"])
    )

    return {"recommendations": recommendations, "signals": _signals(holidays_by_dow, weather_by_dow, rain_impact_pct)}


def _signals(
    holidays_by_dow: dict[int, str],
    weather_by_dow: dict[int, WeatherDay],
    rain_impact_pct: float | None,
) -> list[dict]:
    """Week-level context the UI can surface above the recommendation list."""
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    out: list[dict] = []
    for day in sorted(holidays_by_dow):
        out.append({
            "kind": "holiday",
            "label": f"{holidays_by_dow[day]} ({day_labels[day]})",
        })
    for day in sorted(weather_by_dow):
        w = weather_by_dow[day]
        if not (w.rainy or w.severe):
            continue
        cond = w.label or ("Severe weather" if w.severe else "Rain")
        suffix = ""
        if rain_impact_pct is not None and abs(rain_impact_pct) >= RAIN_IMPACT_THRESHOLD:
            suffix = f" — {int(round(rain_impact_pct)):+d}% typical revenue"
        out.append({"kind": "weather", "label": f"{cond} {day_labels[day]}{suffix}"})
    return out
