"""
TimesFM inference sidecar.

A tiny FastAPI service that loads Google's TimesFM model once and serves zero-shot
forecasts over HTTP. It exists so the main Meridian API container can stay lean
(torch OOMs Railway — see ../../requirements-ml.txt); the API talks to this service
in TimesFM "endpoint mode".

Contract — must match src/ai/predictive/timesfm_engine.py `_forecast_via_endpoint`:
  POST /forecast  {"series": [float, ...], "horizon": int, "freq": int}
       -> {"point": [float]*horizon, "lower": [float]*horizon, "upper": [float]*horizon}
  GET  /health    -> {"status": "ok", "model_loaded": bool}

Wire it up: deploy this on a host with enough RAM (TimesFM 2.0-500m wants a few GB),
then set TIMESFM_ENDPOINT=http://<this-host>:8080/forecast on the Meridian API
service. The model lazy-loads on the first /forecast (weights download from
HuggingFace once); hit /forecast once after deploy to warm it.
"""
from __future__ import annotations

import os

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Meridian TimesFM sidecar")

_model = None


def get_model():
    """Lazy-load the pretrained model once per process."""
    global _model
    if _model is None:
        import timesfm  # heavy; only imported here
        hparams = timesfm.TimesFmHparams(
            backend=os.getenv("TIMESFM_BACKEND", "cpu"),
            per_core_batch_size=32,
            context_len=int(os.getenv("TIMESFM_CONTEXT", "512")),
        )
        checkpoint = timesfm.TimesFmCheckpoint(
            huggingface_repo_id=os.getenv("TIMESFM_REPO", "google/timesfm-2.0-500m-pytorch")
        )
        _model = timesfm.TimesFm(hparams=hparams, checkpoint=checkpoint)
    return _model


class ForecastRequest(BaseModel):
    series: list[float]
    horizon: int
    freq: int = 0


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None}


@app.post("/forecast")
def forecast(req: ForecastRequest):
    model = get_model()
    point_fc, quantile_fc = model.forecast(
        [np.array(req.series, dtype=float)], freq=[req.freq]
    )
    point = [float(v) for v in np.asarray(point_fc[0])[: req.horizon]]
    lower, upper = _bounds(quantile_fc, point, req.horizon)
    return {"point": point, "lower": lower, "upper": upper}


def _bounds(quantile_fc, point, horizon):
    """Low/high band from TimesFM's experimental quantile heads, falling back to a
    ±15% band if the layout isn't as expected (quantile order is version-dependent)."""
    try:
        q = np.asarray(quantile_fc[0])
        if q.ndim == 2 and q.shape[1] >= 2:
            lower = [max(0.0, float(v)) for v in q[:horizon, 1]]
            upper = [float(v) for v in q[:horizon, -1]]
            if len(lower) == len(point) and len(upper) == len(point):
                return lower, upper
    except Exception:
        pass
    return [max(0.0, p * 0.85) for p in point], [p * 1.15 for p in point]
