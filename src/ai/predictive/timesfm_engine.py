"""
TimesFM forecasting engine — Meridian's PRIMARY revenue forecaster.

TimesFM is Google Research's decoder-only time-series foundation model, pretrained
on ~100B real-world time points. It produces zero-shot point + quantile forecasts
with no per-series training — a strong upgrade over the moving-average / AutoARIMA
paths. Meridian uses it as the primary forecaster (swarm agent + persisted dashboard
forecasts); the statistical WMA method is the automatic fallback.

Two backends, chosen by environment (so it works without bloating the lean API host):

  • ENDPOINT mode (recommended for prod) — set ``TIMESFM_ENDPOINT`` to a small
    TimesFM inference sidecar. The engine POSTs the series and gets back the
    forecast over HTTP. No torch in the API container. This is the prod path
    because the API image deliberately excludes torch (it OOMs Railway — see
    requirements-ml.txt).
  • LOCAL mode — in-process model via the ``timesfm`` package + weights. Only
    viable on a host with enough RAM (NOT the Railway API box). Activates when no
    endpoint is set and the package is importable.

Fallback is always safe: if TimesFM is disabled (``TIMESFM_DISABLED=1``), the
endpoint is unreachable, or local load/inference fails, ``forecast()`` returns
``None`` and every caller falls back to the WMA forecaster. This mirrors the repo's
existing "try the heavy path, fall back gracefully" pattern.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger("meridian.ai.predictive.timesfm")

# Context cap: TimesFM 2.5 supports up to 16k, but daily revenue history is short
# and a smaller window keeps memory modest.
_MAX_CONTEXT = 512


@dataclass
class TimesFMForecast:
    """Point forecast + lower/upper bound per future step (all the same length)."""
    point: list[float]
    lower: list[float]
    upper: list[float]


def _disabled() -> bool:
    return os.environ.get("TIMESFM_DISABLED", "").lower() in ("1", "true", "yes")


def _endpoint() -> str:
    return os.environ.get("TIMESFM_ENDPOINT", "").strip()


class TimesFMEngine:
    """Lazy, process-wide singleton wrapper around TimesFM (endpoint or local).

    Obtain the shared instance via the module-level ``get_timesfm_engine()``.
    A failed local load is remembered so we don't repeatedly retry an impossible
    import; an unreachable endpoint just falls back per-call.
    """

    _instance: "TimesFMEngine | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._model = None
        self._load_attempted = False
        self._load_error: str | None = None

    # ── mode / availability ──────────────────────────────────
    def _mode(self) -> str:
        if _disabled():
            return "off"
        if _endpoint():
            return "endpoint"
        return "local"

    def is_available(self) -> bool:
        mode = self._mode()
        if mode == "off":
            self._load_error = "TIMESFM_DISABLED set"
            return False
        if mode == "endpoint":
            return True  # actual reachability is validated per-call (with fallback)
        return self._ensure_loaded()

    @property
    def unavailable_reason(self) -> str | None:
        return self._load_error

    def _ensure_loaded(self) -> bool:
        """Local in-process model load (lazy, once)."""
        if self._model is not None:
            return True
        if self._load_attempted:
            return False  # already tried and failed — don't hammer the import
        self._load_attempted = True
        try:
            import timesfm  # noqa: F401  (heavy; only imported in local mode)
        except ImportError as e:
            self._load_error = f"timesfm package not installed (use TIMESFM_ENDPOINT in prod): {e}"
            logger.info("TimesFM local unavailable — %s", self._load_error)
            return False
        try:
            self._model = self._load_model(timesfm)
            logger.info("TimesFM model loaded (local)")
            return True
        except Exception as e:  # weights download / OOM / version drift
            self._load_error = f"TimesFM local load failed: {e}"
            logger.warning(self._load_error)
            self._model = None
            return False

    def _load_model(self, timesfm):
        """Instantiate the pretrained model. Isolated so constructor API
        differences between timesfm releases stay contained in one place."""
        hparams = timesfm.TimesFmHparams(
            backend=os.environ.get("TIMESFM_BACKEND", "cpu"),
            per_core_batch_size=32,
            context_len=_MAX_CONTEXT,
        )
        checkpoint = timesfm.TimesFmCheckpoint(
            huggingface_repo_id=os.environ.get("TIMESFM_REPO", "google/timesfm-2.0-500m-pytorch")
        )
        return timesfm.TimesFm(hparams=hparams, checkpoint=checkpoint)

    # ── forecasting ──────────────────────────────────────────
    def forecast(self, series: list[float], horizon: int, freq: int = 0) -> TimesFMForecast | None:
        """Zero-shot forecast ``horizon`` steps ahead (oldest→newest series).

        Returns ``None`` if TimesFM is unavailable or anything goes wrong — callers
        MUST fall back to the statistical forecaster.
        """
        if horizon <= 0 or len(series) < 2:
            return None
        mode = self._mode()
        if mode == "off":
            return None
        if mode == "endpoint":
            return self._forecast_via_endpoint(series, horizon, freq)
        return self._forecast_local(series, horizon, freq)

    def _forecast_via_endpoint(self, series, horizon, freq) -> TimesFMForecast | None:
        url = _endpoint()
        payload = json.dumps({
            "series": [float(x) for x in series[-_MAX_CONTEXT:]],
            "horizon": int(horizon),
            "freq": int(freq),
        }).encode()
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            timeout = float(os.environ.get("TIMESFM_TIMEOUT", "20"))
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode() or "{}")
            point = [float(v) for v in body["point"][:horizon]]
            lower = [float(v) for v in body.get("lower", [])[:horizon]] or [p * 0.85 for p in point]
            upper = [float(v) for v in body.get("upper", [])[:horizon]] or [p * 1.15 for p in point]
            if len(point) != horizon:
                return None
            return TimesFMForecast(point=point, lower=lower, upper=upper)
        except (urllib.error.URLError, KeyError, ValueError, TimeoutError) as e:
            logger.warning("TimesFM endpoint failed, caller will fall back: %s", e)
            return None

    def _forecast_local(self, series, horizon, freq) -> TimesFMForecast | None:
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
            logger.warning("TimesFM local forecast failed, caller will fall back: %s", e)
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
