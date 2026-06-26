# Verify live camera from a laptop

This proves the full streaming chain — **WHIP publish → Cloudflare → watch in a
browser** — without a Jetson or the portal. It's the same publish the production
edge agent does; if this works, the portal "Go live" button works (it drives the
same publish through the backend we already deployed).

## Prereqs
- Docker (Desktop is fine — works on Intel and Apple-Silicon Macs).
- Your Cloudflare Stream creds (account-level, no domain needed).

## 1. Set creds
```bash
cd edge
cp verify.env.example verify.env      # then edit verify.env:
#   CLOUDFLARE_ACCOUNT_ID=...
#   CLOUDFLARE_STREAM_TOKEN=...
```

## 2. Run it
**Test pattern** (no camera needed — proves the pipeline):
```bash
docker compose -f docker-compose.verify.yml run --rm verify
```
**A real camera** (any RTSP IP cam on your network):
```bash
docker compose -f docker-compose.verify.yml run --rm verify --rtsp rtsp://USER:PASS@192.168.1.50:554/stream1
```

## 3. Watch
The command prints a line like:
```
  WATCH IT HERE (open in a browser):
    https://customer-xxxx.cloudflarestream.com/<id>/iframe?autoplay=true&muted=true
```
Open that URL. Live video within a few seconds = the chain works. **Ctrl+C** to
stop (it auto-deletes the Live Input).

## What this confirms vs. the portal
- ✅ Confirms: ffmpeg-WHIP from a laptop → Cloudflare relay → browser playback.
- The portal flow adds the backend orchestration (`POST /cameras/{id}/live` →
  edge `live-state` poll → publish), which is already deployed. To test that end,
  register a camera for your org with `live_view` on, run the **full** edge agent
  (not this verifier) with `MERIDIAN_DEVICE_TOKEN`, and click **Go live** in the
  Camera pillar.

Note: the production edge image (`Dockerfile`) now also bundles ffmpeg ≥7.x, so
real Jetson/Linux edges can WHIP-publish too.
