"""TimesFM forecasting — engine guard, swarm agent, and generator wiring.

TimesFM (torch + weights) is never installed in CI, so these tests mock the engine
and pin the two things that matter:
  1. With TimesFM OFF (the default), everything degrades gracefully — the agent
     reports `skipped` and the ForecastGenerator falls back to its WMA method.
  2. With a (mocked) TimesFM available, the agent emits the standard forecast shape
     and the generator's persisted rows carry the timesfm model_version.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import date, timedelta
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.ai.predictive.timesfm_engine import TimesFMForecast, get_timesfm_engine

ORG = "168b6df2-e9af-4b00-8fec-51e51149ff19"


def _run(coro):
    return asyncio.run(coro)


class _FakeEngine:
    def __init__(self, available: bool = True, per_day: float = 10000.0):
        self._available = available
        self._per_day = per_day

    def is_available(self) -> bool:
        return self._available

    @property
    def unavailable_reason(self):
        return None if self._available else "TIMESFM_ENABLED not set"

    def forecast(self, series, horizon, freq=0):
        if not self._available:
            return None
        pt = [float(self._per_day)] * horizon
        return TimesFMForecast(point=pt, lower=[p * 0.9 for p in pt], upper=[p * 1.1 for p in pt])


def _daily_revenue(days: int = 30, value: int = 9000) -> list[dict]:
    start = date(2026, 1, 1)
    return [
        {"date": (start + timedelta(days=i)).isoformat(),
         "revenue_cents": value, "total_revenue_cents": value}
        for i in range(days)
    ]


def _ctx(daily):
    return SimpleNamespace(
        org_id=ORG, location_id="LOC1", business_vertical="other",
        daily_revenue=daily, agent_outputs={}, transactions=[], products=[],
    )


# ── 1. Engine modes: primary by default, disable flag, endpoint ──

def _fresh_engine():
    eng = get_timesfm_engine()
    eng._model = None
    eng._load_attempted = False
    eng._load_error = None
    return eng


def test_engine_disable_flag(monkeypatch):
    monkeypatch.setenv("TIMESFM_DISABLED", "1")
    monkeypatch.delenv("TIMESFM_ENDPOINT", raising=False)
    eng = _fresh_engine()
    assert eng.is_available() is False
    assert eng.forecast([1.0, 2.0, 3.0], 7) is None


def test_engine_local_unavailable_without_package(monkeypatch):
    # Default (primary) mode, but the timesfm package isn't installed in CI → local
    # load fails → unavailable, so callers fall back. No endpoint set.
    monkeypatch.delenv("TIMESFM_DISABLED", raising=False)
    monkeypatch.delenv("TIMESFM_ENDPOINT", raising=False)
    eng = _fresh_engine()
    assert eng.is_available() is False
    assert eng.forecast([1.0, 2.0, 3.0], 7) is None


def test_engine_endpoint_mode(monkeypatch):
    # With TIMESFM_ENDPOINT set, the engine is available and POSTs the series.
    monkeypatch.delenv("TIMESFM_DISABLED", raising=False)
    monkeypatch.setenv("TIMESFM_ENDPOINT", "http://timesfm.local/forecast")
    eng = _fresh_engine()
    assert eng.is_available() is True

    import io
    import src.ai.predictive.timesfm_engine as te

    captured = {}

    class _Resp(io.BytesIO):
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        return _Resp(json.dumps({
            "point": [100.0] * 7,
            "lower": [90.0] * 7,
            "upper": [110.0] * 7,
        }).encode())

    monkeypatch.setattr(te.urllib.request, "urlopen", fake_urlopen)
    fc = eng.forecast([1.0, 2.0, 3.0, 4.0], 7)
    assert fc is not None
    assert fc.point == [100.0] * 7
    assert captured["body"]["horizon"] == 7
    assert captured["url"] == "http://timesfm.local/forecast"


def test_engine_endpoint_failure_falls_back(monkeypatch):
    monkeypatch.delenv("TIMESFM_DISABLED", raising=False)
    monkeypatch.setenv("TIMESFM_ENDPOINT", "http://timesfm.local/forecast")
    eng = _fresh_engine()
    import src.ai.predictive.timesfm_engine as te

    def boom(req, timeout=None):
        raise te.urllib.error.URLError("connection refused")

    monkeypatch.setattr(te.urllib.request, "urlopen", boom)
    assert eng.forecast([1.0, 2.0, 3.0], 7) is None  # caller falls back to WMA


# ── 2. Agent skips cleanly when TimesFM is unavailable ───────

def test_agent_skips_when_unavailable(monkeypatch):
    from src.ai.agents import timesfm_forecaster as mod
    monkeypatch.setattr(mod, "get_timesfm_engine", lambda: _FakeEngine(available=False))
    agent = mod.TimesFMForecasterAgent(_ctx(_daily_revenue()))
    result = _run(agent.analyze())
    assert result["status"] == "skipped"
    assert result["score"] == 0


def test_agent_insufficient_history(monkeypatch):
    from src.ai.agents import timesfm_forecaster as mod
    monkeypatch.setattr(mod, "get_timesfm_engine", lambda: _FakeEngine(available=True))
    agent = mod.TimesFMForecasterAgent(_ctx(_daily_revenue(days=5)))
    result = _run(agent.analyze())
    assert result["status"] == "insufficient_data"


# ── 3. Agent produces the standard forecast shape when available ─

def test_agent_emits_forecast_shape(monkeypatch):
    from src.ai.agents import timesfm_forecaster as mod
    monkeypatch.setattr(mod, "get_timesfm_engine", lambda: _FakeEngine(available=True, per_day=12345))
    agent = mod.TimesFMForecasterAgent(_ctx(_daily_revenue(days=30)))
    result = _run(agent.analyze())
    assert result["status"] == "complete"
    fc = result["data"]["forecasts"]
    assert len(fc["7_day"]) == 7
    assert len(fc["30_day"]) == 4   # every 7th day of 30
    assert len(fc["90_day"]) == 3   # every 30th day of 90
    row = fc["7_day"][0]
    assert row["predicted_cents"] == 12345
    assert row["lower_bound_cents"] <= row["predicted_cents"] <= row["upper_bound_cents"]
    assert result["data"]["model"] == "timesfm"


# ── 4. ForecastGenerator: TimesFM path + graceful fallback ───

def test_generator_uses_timesfm_when_available(monkeypatch):
    from src.ai.generators import forecasts as gen
    monkeypatch.setattr(gen, "get_timesfm_engine", lambda: _FakeEngine(available=True, per_day=8000))
    rows = gen.ForecastGenerator().generate(_ctx(_daily_revenue(days=30)))
    assert rows, "expected forecasts"
    daily_rows = [r for r in rows if r["forecast_type"] == "daily_revenue"]
    weekly_rows = [r for r in rows if r["forecast_type"] == "weekly_revenue"]
    assert daily_rows and weekly_rows
    assert all(r["model_version"] == gen.ForecastGenerator.TIMESFM_MODEL_VERSION for r in daily_rows)
    assert daily_rows[0]["predicted_value_cents"] == 8000
    # weekly = roll-up of 7 daily points
    assert weekly_rows[0]["predicted_value_cents"] == 8000 * 7


def test_generator_falls_back_to_wma_when_unavailable(monkeypatch):
    from src.ai.generators import forecasts as gen
    monkeypatch.setattr(gen, "get_timesfm_engine", lambda: _FakeEngine(available=False))
    rows = gen.ForecastGenerator().generate(_ctx(_daily_revenue(days=30)))
    assert rows, "expected WMA forecasts"
    # No TimesFM rows — every row uses the statistical model version.
    assert all(r["model_version"] == gen.ForecastGenerator.MODEL_VERSION for r in rows)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
