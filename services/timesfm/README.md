# TimesFM inference sidecar

Serves Google's TimesFM time-series foundation model over HTTP so the Meridian API
can use TimesFM as its primary forecaster **without** bundling torch into the lean
API image (torch OOMs Railway — see `requirements-ml.txt`).

The API calls this in "endpoint mode" (`src/ai/predictive/timesfm_engine.py`). When
no endpoint is configured, the API falls back to its WMA forecaster — so this
service is what flips TimesFM from "ready" to "live".

## Contract

```
POST /forecast
  { "series": [float, ...],   # historical values, oldest → newest
    "horizon": int,           # steps to forecast
    "freq": int }             # 0 = high-frequency (daily)
  -> { "point": [float]*horizon,
       "lower": [float]*horizon,
       "upper": [float]*horizon }

GET /health -> { "status": "ok", "model_loaded": bool }
```

## Run locally

```bash
cd services/timesfm
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8080
# first call downloads weights + loads the model (slow); subsequent calls are fast
curl -s localhost:8080/forecast -H 'content-type: application/json' \
  -d '{"series":[100,120,90,140,110,130,150,...],"horizon":7,"freq":0}'
```

## Deploy

Any host with a few GB of RAM (TimesFM 2.0-500m). NOT the Railway API box and NOT
the RAM-tight Contabo edge host.

```bash
docker build -t meridian-timesfm services/timesfm
docker run -d -p 8080:8080 --name timesfm \
  -v timesfm-weights:/root/.cache/huggingface \   # persist weights across restarts
  meridian-timesfm
```

Env (all optional):
- `TIMESFM_REPO`   — HF checkpoint (default `google/timesfm-2.0-500m-pytorch`; use a
  smaller checkpoint to cut RAM).
- `TIMESFM_BACKEND` — `cpu` (default) or `gpu`.
- `TIMESFM_CONTEXT` — context length (default 512).

## Wire it into Meridian

Set on the Meridian API service, then redeploy:

```
TIMESFM_ENDPOINT=http://<sidecar-host>:8080/forecast
```

Warm it once (`curl .../forecast`), then the swarm `TimesFMForecasterAgent` and the
persisted dashboard forecasts switch to TimesFM automatically. To roll back, unset
`TIMESFM_ENDPOINT` (falls back to WMA) or set `TIMESFM_DISABLED=1`.
