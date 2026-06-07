"""Wave 2A — AutoGluon-TimeSeries forecast backend eval.

Asserts the backend (1) returns the same row schema as the incumbent
statsforecast path, (2) produces the requested horizon length with
non-negative point forecasts and ordered intervals, and (3) no-ops
(returns ``None``) on a too-short series so the caller falls back.

AutoGluon pulls torch and is slow to fit; the smoke test caps the
training budget hard via env so it stays CI-tolerable, and importorskip
keeps environments without the dep green.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta

import pytest

pytest.importorskip(
    "autogluon.timeseries",
    reason="AutoGluon-TimeSeries powers the Wave 2A forecast backend. "
           "Install with `pip install autogluon.timeseries`.",
)

from src.ai.ml import autogluon_forecast as agf  # noqa: E402


def _series(n=60):
    start = datetime(2026, 1, 1)
    out = []
    for i in range(n):
        # trend + weekly seasonality + mild noise, all positive cents
        val = 50000 + 300 * i + 8000 * math.sin(2 * math.pi * (i % 7) / 7)
        out.append({"date": (start + timedelta(days=i)).strftime("%Y-%m-%d"),
                    "revenue_cents": int(val)})
    return out


def test_schema_and_horizon(monkeypatch):
    # Keep the fit fast and deterministic for CI.
    monkeypatch.setenv("MERIDIAN_AUTOGLUON_TIME_LIMIT", "30")
    monkeypatch.setenv("MERIDIAN_AUTOGLUON_PRESET", "fast_training")
    # env is read at import time → reload the module so caps apply.
    import importlib
    importlib.reload(agf)

    fc = agf.autogluon_forecast(_series(60), periods=14)
    assert fc is not None, "expected a forecast on 60 days of clean data"
    assert len(fc) == 14
    for row in fc:
        assert "date" in row and "predicted" in row
        assert row["predicted"] >= 0
        assert row["lower"] <= row["predicted"] <= row["upper"]
        if "lower_80" in row:
            assert row["lower"] <= row["lower_80"] <= row["upper_80"] <= row["upper"]
    assert fc[-1].get("_backend") == "autogluon"


def test_short_series_is_noop():
    # Below MIN_OBS → None so BaseAgent.forecast falls back to statsforecast.
    assert agf.autogluon_forecast(_series(10), periods=7) is None
