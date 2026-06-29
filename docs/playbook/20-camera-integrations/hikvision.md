# Hikvision

> Status: **OFFICIALLY SUPPORTED**
> Stream: RTSP
> Availability: **Camera intelligence add-on**
> OEM coverage: LaView, ANNKE, EmpireTech, older Lorex, older Honeywell — our Hikvision handler works with all of these

## What you tell the merchant

"Hikvision works out of the box — most common security camera brand, and our handler also covers the rebrands (LaView, ANNKE, EmpireTech, older Lorex, older Honeywell). Connection is 2 minutes once we have the RTSP URL."

## How the merchant connects

1. Camera admin UI (typically `http://camera-ip`) → log in (default admin/admin or admin/12345 — get them to set a real password if they haven't)
2. **Configuration → Network → Advanced → Integration Protocol → enable ONVIF** (best path) or grab the RTSP URL directly
3. RTSP URL format: `rtsp://username:password@camera-ip:554/Streaming/Channels/101` (substream is `102` — use that for analytics to save bandwidth)
4. Paste into Meridian's **Settings → Cameras → Add Camera**
5. Stream goes live within 60 seconds

Typical time to connect: **3–5 minutes** (most time is the merchant finding their camera password).

## What we use the stream for

| Feature | Camera position |
|---------|----------------|
| Foot traffic counting | Entrance, overhead 45° |
| Queue length | Checkout, top-down |
| Dwell time per zone | Wide coverage of the floor |
| Heatmap | Same as dwell |

YOLO11n + ByteTrack runs on each frame (see `src/camera/detector.py`). Person-only detection (class 0). Confidence threshold 0.35. Per-person zone assignment if zones are configured.

## Compatibility notes

- Hikvision DS-2CD2xxx series is the most common; works with our handler unchanged
- OEM rebrands (LaView, ANNKE, EmpireTech) use the same firmware family — same RTSP path works
- Older Lorex (pre-Dahua acquisition era) used Hikvision OEM — works
- Older Honeywell (pre-2020) used Hikvision OEM — works
- Newer Lorex (Dahua era) → use the [dahua.md](./dahua.md) handler

## Federal / critical-infrastructure note

**Hikvision is banned for federal US use** under Section 889 (NDAA/TAA). If a merchant is government, defense contractor, or critical infrastructure → route them to [axis.md](./axis.md).

## Sales angle

**Opener:** "You probably have a Hikvision or one of the rebrands — LaView, ANNKE, Lorex if it's older. Plugs into our system in 2 minutes once we have the password. You'll see foot traffic patterns by the end of week 1."

**Why Hikvision merchants close fast:**
- Most common brand → no "is this compatible" objection
- Already have cameras installed → no hardware cost
- Premium tier ($599 / CA$685) feels like a small add-on vs. a new line item

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Stream fails to open | Wrong RTSP path (main vs sub) | Try `/Streaming/Channels/102` for substream |
| Frequent disconnects | Network/QoS issue | Confirm 2–4 Mbps available per camera |
| Password rejected | Default credentials | Force password change in camera admin |
| Hikvision firmware update breaks stream | Recent firmware sometimes changes RTSP path | Re-check path in camera admin → Network |

---

_Last updated: 2026-05-31_
_Sourced from: src/camera/rtsp_handler.py + src/camera/detector.py + docs/playbook/_status/phase-2-decisions.md (officially supported, OEM coverage)_
