# How to Connect Any IP Camera (Universal Diagnostic Flow)

If a merchant's camera brand isn't on the supported list but they swear it has RTSP, follow this.

## Step 1: Confirm RTSP capability

Check the camera's spec sheet or admin UI for:
- "RTSP" or "RTSP support"
- "ONVIF" (often implies RTSP)
- "Real Time Streaming Protocol"

If none of these appear → likely cloud-only (Arlo / current Wyze / current Nest). Stop. Recommend the $60 Reolink instead.

## Step 2: Get the RTSP URL

Common URL formats by manufacturer:

| Brand | URL pattern |
|-------|-------------|
| Hikvision | `rtsp://user:pass@ip:554/Streaming/Channels/101` (or `/102` substream) |
| Dahua / Amcrest | `rtsp://user:pass@ip:554/cam/realmonitor?channel=1&subtype=1` |
| Reolink | `rtsp://user:pass@ip:554/h264Preview_01_sub` |
| Axis | `rtsp://user:pass@ip:554/axis-media/media.amp?videocodec=h264` |
| UniFi | `rtsps://protect.unifi.io:7441/{token}?enableSrtp` (note `rtsps`, port 7441) |
| Generic ONVIF | Use an ONVIF discovery tool like `onvif-cli` to query the camera |

If unsure → camera admin UI → look for **Network → RTSP** or **Integration → RTSP**.

## Step 3: Test the URL in VLC FIRST

Before pasting into Meridian:

1. Open VLC Media Player
2. **Media → Open Network Stream**
3. Paste the RTSP URL
4. Click Play

**If VLC plays it:** the URL is valid; paste into Meridian.

**If VLC doesn't play it:** the URL or the camera's RTSP service is the problem, not Meridian.

## Step 4: Paste into Meridian

1. Meridian portal → **Settings → Cameras → Add Camera**
2. Paste URL
3. Name the camera (e.g., "Front Entrance", "Checkout")
4. Save
5. Within 60 seconds we'll show the first frame; within 5 minutes detections appear

## Diagnostic: stream connects but no detections

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Connected, 0 people detected at busy time | Bad camera angle (too far, wrong angle, glare) | Reposition: overhead 45° at entrance |
| Connected, detections work in main view but not in a zone | Zone polygon coordinates wrong | Redraw zone in Meridian UI |
| Connected, very low confidence detections | Bad lighting, dim camera | Increase camera exposure or replace with better camera |
| Connected, stream choppy | Bandwidth limit | Switch to substream (lower bitrate) — most cameras have a `/sub` or `subtype=1` variant |

## Diagnostic: VLC played it but Meridian can't open it

| Cause | Fix |
|-------|-----|
| Network: Meridian's edge service can't reach the camera (NAT, firewall) | Confirm port 554 (or 7441 for RTSPS) is reachable from where Meridian runs |
| TLS cert issue (UniFi RTSPS) | Confirm cert validity; our handler supports self-signed but logs warnings |
| Credential encoding (special chars in password) | URL-encode the password (e.g., `@` → `%40`) |
| Camera maxed out concurrent streams | Some cameras limit concurrent RTSP clients to 2–3 — close VLC, retry in Meridian |

## When to give up and use the $60 Reolink

If after 15 minutes of troubleshooting:
- VLC can't play the stream
- Or the camera admin doesn't expose an RTSP URL
- Or the merchant's network blocks the port

The right move: order a $60 Reolink RLC-510A. The merchant will be live in 2 minutes once it ships. Don't burn 2 hours forcing a non-cooperative camera.

## Edge case: ONVIF-only cameras

Some cameras (especially older IP cameras) expose ONVIF but not a direct RTSP URL. In that case:

1. Use `onvif-cli` or a similar tool to discover the camera
2. Query the `GetStreamUri` ONVIF operation → returns the actual RTSP URL
3. Use that URL in Meridian

If the merchant doesn't have technical bandwidth for this → recommend the Reolink.

---

_Last updated: 2026-05-31_
_Sourced from: src/camera/rtsp_handler.py + general IP camera knowledge (no _status/cameras/ source file existed at Phase 1 — stubbed per task spec)_

_[NEEDS AIDAN INPUT] — Confirm whether we want to publish detailed VLC-test step-by-step in the rep playbook, or keep this as engineering-team-only. Reps may not be technical enough to run the diagnostic; could be a CS escalation path instead._
