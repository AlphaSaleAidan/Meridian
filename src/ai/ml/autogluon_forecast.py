"""Wave 2A — AutoGluon-TimeSeries forecast backend (opt-in).

The incumbent forecaster (``BaseAgent.forecast`` / ``ForecasterAgent``)
uses a ``statsforecast`` ensemble (AutoARIMA/AutoETS/AutoTheta/MSTL).
AutoGluon-TimeSeries fits *and ensembles across* statistical **and**
gradient-boosted / deep models with automatic backtesting, which on
irregular retail revenue series typically lowers error at the cost of a
much heavier dependency (pulls torch).

Because of that weight this backend is:

  * **opt-in** via ``MERIDIAN_FORECAST_BACKEND=autogluon`` (default
    ``statsforecast`` — the value is resolved in ``BaseAgent.forecast``);
  * **lazy-imported** — ``autogluon.timeseries`` is NOT in the deployed
    Railway image (see ``requirements-ml.txt``), so the import guard
    keeps prod working;
  * **fail-safe** — every error path returns ``None`` and the caller
    falls back to the statsforecast ensemble, then manual extrapolation.

Output schema matches the statsforecast path in ``BaseAgent.forecast``
exactly (``date`` / ``predicted`` / ``lower`` / ``upper`` and the
``lower_80`` / ``upper_80`` 80% band), so downstream consumers cannot
tell which backend produced a row.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("meridian.ai.ml.autogluon")

# Quantiles requested from AutoGluon → mapped to the incumbent's bands.
# 0.025/0.975 = 95% interval (lower/upper); 0.1/0.9 = 80% band.
_QUANTILES = [0.025, 0.1, 0.5, 0.9, 0.975]

# Default training budget (seconds). AutoGluon batch-forecasts on a CPU
# box; keep it bounded so an opt-in run can't wedge a worker. Tunable.
_DEFAULT_TIME_LIMIT = int(os.environ.get("MERIDIAN_AUTOGLUON_TIME_LIMIT", "60"))

# Preset trades accuracy vs fit time. "medium_quality" is the sane batch
# default; "fast_training" for smoke tests, "best_quality" for offline.
_PRESET = os.environ.get("MERIDIAN_AUTOGLUON_PRESET", "medium_quality")

# AutoGluon needs a real minimum history to backtest; below this the
# statsforecast ensemble is both faster and not meaningfully worse.
MIN_OBS = 30


def autogluon_forecast(series: list[dict], periods: int = 30) -> list[dict] | None:
    """Forecast ``periods`` days ahead with AutoGluon-TimeSeries.

    ``series`` is a list of ``{"date"/"ds": ..., "revenue_cents"/"y": ...}``
    dicts (same shape ``BaseAgent.forecast`` accepts). Returns a list of
    forecast rows, or ``None`` if AutoGluon is unavailable, the series is
    too short, or anything fails — signalling the caller to fall back.
    """
    if len(series) < MIN_OBS:
        return None
    try:
        import pandas as pd
        from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor
    except Exception as exc:  # noqa: BLE001 — torch/CUDA init can raise non-ImportError
        logger.debug("autogluon unavailable (%s) — falling back", exc)
        return None

    try:
        df = pd.DataFrame(series)
        if "date" in df.columns:
            df = df.rename(columns={"date": "timestamp", "revenue_cents": "target"})
        elif "ds" in df.columns:
            df = df.rename(columns={"ds": "timestamp", "y": "target"})
        else:
            df.columns = ["timestamp", "target"] + list(df.columns[2:])

        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
        if len(df) < MIN_OBS:
            return None
        df["item_id"] = "revenue"
        # Regularize to a daily grid; AutoGluon requires a consistent freq.
        df = (
            df.set_index("timestamp")[["item_id", "target"]]
            .asfreq("D")
            .assign(item_id="revenue")
        )
        df["target"] = df["target"].interpolate(limit_direction="both")
        df = df.reset_index()

        tsdf = TimeSeriesDataFrame.from_data_frame(
            df, id_column="item_id", timestamp_column="timestamp"
        )

        predictor = TimeSeriesPredictor(
            target="target",
            prediction_length=periods,
            freq="D",
            quantile_levels=_QUANTILES,
            eval_metric="MASE",
            verbosity=0,
            log_to_file=False,
        )
        predictor.fit(
            tsdf,
            presets=_PRESET,
            time_limit=_DEFAULT_TIME_LIMIT,
            random_seed=42,
        )
        fc = predictor.predict(tsdf).reset_index()

        results: list[dict] = []
        for _, row in fc.iterrows():
            ts = row["timestamp"]
            predicted = max(0, round(float(row["mean"])))
            entry = {
                "date": ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts),
                "predicted": predicted,
            }
            if "0.1" in fc.columns and "0.9" in fc.columns:
                entry["lower_80"] = max(0, round(float(row["0.1"])))
                entry["upper_80"] = max(0, round(float(row["0.9"])))
            if "0.025" in fc.columns and "0.975" in fc.columns:
                entry["lower"] = max(0, round(float(row["0.025"])))
                entry["upper"] = max(0, round(float(row["0.975"])))
            else:
                entry["lower"] = int(predicted * 0.85)
                entry["upper"] = int(predicted * 1.15)
            results.append(entry)

        if not results:
            return None
        results[-1]["_backend"] = "autogluon"
        return results
    except Exception as exc:  # noqa: BLE001
        logger.warning("autogluon forecast failed: %s — falling back", exc)
        return None
