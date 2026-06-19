"""
TimesFM forecasting engine — thin wrapper around Google Research's TimesFM
(Time Series Foundation Model) for zero-shot revenue forecasting.

TimesFM is a decoder-only foundation model pretrained on ~100B real-world time
points. It produces zero-shot point + quantile forecasts with no per-series
training, which makes it a strong drop-in upgrade over the moving-average /
AutoARIMA paths once a series has enough history.

This wrapper is intentionally OPTIONAL and OFF by default:
  - torch + the `timesfm` package + the model weights (hundreds of MB) are heavy;
    we do NOT add them to core requirements and load nothing unless TIMESFM_ENABLED=1.
  - When unavailable (package missing, weights missing, load/inference error), the
    engine reports unavailable and callers fall back to their existing forecasters.
This mirrors the repo's existing "try the heavy lib, fall back gracefully" pattern
(see ForecasterAgent's statsforecast guard).

Provision (on a host with enough RAM — NOT the current edge box):
    pip install -r requirements-timesfm.txt   # torch + timesfm
    export TIMESFM_ENABLED=1
The model weights download from HuggingFace on first load (overridable via
TIMESFM_REPO). The real-model code path is written against the documented TimesFM
2.x API and is exercised only once provisioned; until then this module is inert and
every caller keeps its existing forecaster.
"""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass

logger = logging.getLogger("meridian.ai.predictive.timesfm")

# Context cap: TimesFM 2.5 supports up to 16k, but daily revenue history is short
# and a smaller window keeps memory modest on shared hosts.
_MAX_CONTEXT = 512


@dataclass
class TimesFMForecast:
    """Point forecast + lower/upper bound per future step (all the same length)."""
    point: list[float]
    lower: list[float]
    upper: list[float]


def _enabled() -> bool:
    return os.environ.get("TIMESFM_ENABLED", "").lower() in ("1", "true", "yes")


class TimesFMEngine:
    """Lazy, process-wide singleton wrapper around a loaded TimesFM model.

    Obtain the shared instance via the module-level ``get_timesfm_engine()``.
    A failed load is remembered so we don't repeatedly retry an impossible import.
    """

    _instance: "TimesFMEngine | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._model = None
        self._load_attempted = False
        self._load_error: str | None = None

    # ── availability / lazy load ─────────────────────────────
    def _ensure_loaded(self) -> bool:
        if self._model is not None:
            return True
        if self._load_attempted:
            return False  # already tried and failed — don't hammer the import
        self._load_attempted = True
        if not _enabled():
            self._load_error = "TIMESFM_ENABLED not set"
            return False
        try:
            import timesfm  # noqa: F401  (heavy; imported only when enabled)
        except ImportError as e:
            self._load_error = f"timesfm package not installed: {e}"
            logger.info("TimesFM disabled — %s", self._load_error)
            return False
        try:
            self._model = self._load_model(timesfm)
            logger.info("TimesFM model loaded")
            return True
        except Exception as e:  # weights download / OOM / version drift
            self._load_error = f"TimesFM load failed: {e}"
            logger.warning(self._load_error)
            self._model = None
            return False

    def _load_model(self, timesfm):
        """Instantiate the pretrained model. Isolated so the constructor API
        differences between timesfm releases stay contained in one place."""
        hparams = timesfm.TimesFmHparams(
            backend=os.environ.get("TIMESFM_BACKEND", "cpu"),
            per_core_batch_size=32,
            context_len=_MAX_CONTEXT,
        )
        checkpoint = timesfm.TimesFmCheckpoint(
            huggingface_repo_id=os.environ.get(
                "TIMESFM_REPO", "google/timesfm-2.0-500m-pytorch"
            )
        )
        return timesfm.TimesFm(hparams=hparams, checkpoint=checkpoint)

    def is_available(self) -> bool:
        return self._ensure_loaded()

    @property
    def unavailable_reason(self) -> str | None:
        return self._load_error

    # ── forecasting ──────────────────────────────────────────
    def forecast(self, series: list[float], horizon: int, freq: int = 0) -> TimesFMForecast | None:
        """Zero-shot forecast ``horizon`` steps ahead.

        ``series`` is the historical values oldest→newest; ``freq`` is TimesFM's
        frequency indicator (0 = high-frequency, e.g. daily). Returns ``None`` if
        the model is unavailable or anything goes wrong — callers MUST fall back.
        """
        if horizon <= 0 or len(series) < 2:
            return None
        if not self._ensure_loaded():
            return None
        try:
            import numpy as np

            context = [float(x) for x in series[-_MAX_CONTEXT:]]
            point_fc, quantile_fc = self._model.forecast([np.array(context, dtype=float)], freq=[freq])
            point = [float(v) for v in np.asarray(point_fc[0])[:horizon]]
            lo, hi = self._extract_bounds(quantile_fc, point, horizon, np)
            return TimesFMForecast(point=point, lower=lo, upper=hi)
        except Exception as e:
            logger.warning("TimesFM forecast failed, caller will fall back: %s", e)
            return None

    @staticmethod
    def _extract_bounds(quantile_fc, point, horizon, np):
        """Pull a low/high band from TimesFM's experimental quantile heads,
        falling back to a ±15% band if the layout isn't what we expect (the exact
        quantile column order is version-dependent and validated when provisioned)."""
        try:
            q = np.asarray(quantile_fc[0])
            if q.ndim == 2 and q.shape[1] >= 2:
                lo = [max(0.0, float(v)) for v in q[:horizon, 1]]    # ~q10
                hi = [float(v) for v in q[:horizon, -1]]             # ~q90
                if len(lo) == len(point) and len(hi) == len(point):
                    return lo, hi
        except Exception:
            pass
        lo = [max(0.0, p * 0.85) for p in point]
        hi = [p * 1.15 for p in point]
        return lo, hi


def get_timesfm_engine() -> TimesFMEngine:
    """Return the process-wide TimesFM engine singleton."""
    if TimesFMEngine._instance is None:
        with TimesFMEngine._lock:
            if TimesFMEngine._instance is None:
                TimesFMEngine._instance = TimesFMEngine()
    return TimesFMEngine._instance
