# Meridian Connector — one-click local camera analytics

Tap the merchant's **existing** cameras and run Meridian's vision analytics on a
machine they **already own** (POS back-office PC, a spare box). No dedicated
hardware, no router changes, no video off-site — it dials **outbound** to Meridian
and only **anonymous counts** leave the network.

> For cameras with a supported vendor cloud (Tuya / Smart Life), try
> "Connect via your camera app" in the portal first — there's nothing to install
> at all. Use this connector for standard ONVIF/RTSP cameras.

## Run (Docker — one line)

```sh
docker run -d --network host --restart unless-stopped \
  -e MERIDIAN_PAIRING_CODE=<code from the "Connect cameras" wizard> \
  -e MERIDIAN_API=https://api.meridian.tips \
  ghcr.io/alphasaleaidan/meridian-connector
```

`--network host` lets it auto-discover ONVIF cameras on your LAN. Cameras appear in
your portal within seconds and metrics start flowing.

## How it works

```
 ONVIF/RTSP cameras ──(LAN)──▶ go2rtc          (discovery + local frame API; creds stay here)
                                  │
                                  ▼
                              local_agent.py    (YOLO11 + ByteTrack on CPU: entries, occupancy,
                                  │              dwell, queue — the SAME pipeline as the cloud)
                                  ▼
                   POST /api/vision/ingest/*     (per-org X-Device-Token; anonymous counts only)
                                  │
                                  ▼
                           Meridian dashboard
```

1. You paste the **pairing code** from the portal wizard → it exchanges for a
   **per-org device token** (that connector can only write to that one merchant).
2. **go2rtc** (bundled) auto-discovers your ONVIF cameras and exposes a local JPEG
   snapshot API. Camera usernames/passwords stay **only on this machine** (in
   `go2rtc.yaml`), never in the cloud.
3. **local_agent.py** pulls frames from go2rtc, runs the real Meridian pipeline on
   CPU (no GPU), buckets metrics every 5 minutes, and POSTs anonymous counts.

## Build

Built from the **repo root** (bundles `src/camera` + the YOLO weights):

```sh
docker build -f edge/connector/local_agent.Dockerfile \
  -t ghcr.io/alphasaleaidan/meridian-connector .
```

## Env

| Var | Default | Purpose |
|-----|---------|---------|
| `MERIDIAN_API` | `https://api.meridian.tips` | Meridian API base |
| `MERIDIAN_PAIRING_CODE` | — | one-time code from the wizard (15-min TTL) |
| `GO2RTC_API` | `http://127.0.0.1:1984` | local discovery + frame API |
| `FRAME_INTERVAL_SEC` | `0.3` | snapshot poll interval (~3 fps) |
| `BUCKET_SEC` | `300` | metric bucket size (5 min) |

Advanced: add a manual `rtsp://user:pass@…` under `streams:` in `go2rtc.yaml` if a
camera isn't ONVIF-discoverable.

## Privacy

Anonymous by default — no faces, no identity, no images stored or transmitted, just
tallies. The identity tier stays disabled unless the server enables it.

## Files

- `local_agent.py` — discovery loop + per-camera pipeline worker + ingest client
- `local_agent.Dockerfile` / `entrypoint-local.sh` — CPU image (go2rtc + pipeline + weights)
- `go2rtc.yaml` — ONVIF discovery config
- `connector.py` — older thin supervisor (register + heartbeat only), superseded by
  `local_agent.py` for local processing
