# Dahua

> Status: **OFFICIALLY SUPPORTED**
> Stream: RTSP
> Required plan: Premium or Command
> OEM coverage: Amcrest (sister-brand), newer Lorex (Dahua acquired Lorex)

## What you tell the merchant

"Dahua and its sister-brand Amcrest connect in about 3 minutes via RTSP. If you've got a newer Lorex, that's also Dahua underneath — same handler. We pull the substream to save bandwidth."

## How the merchant connects

1. Camera admin UI (typically `http://camera-ip`) → log in
2. **Setting → Network → RTSP** → confirm RTSP enabled (default port 554)
3. RTSP URL format: `rtsp://username:password@camera-ip:554/cam/realmonitor?channel=1&subtype=1` (`subtype=0` is main, `subtype=1` is substream)
4. Paste into Meridian's **Settings → Cameras → Add Camera**

Typical time to connect: **3 minutes**.

## What we use the stream for

Same pipeline as Hikvision: YOLO11n person detection + ByteTrack + per-zone assignment. See [_index.md](./_index.md) for what cameras enable which features.

## Compatibility notes

- **Amcrest** is Dahua's US sister-brand — identical firmware lineage, same handler works
- **Newer Lorex** (post-Dahua acquisition) — use this Dahua handler, not the Hikvision one
- Older Lorex (pre-Dahua era) → use [hikvision.md](./hikvision.md)
- Dahua DH-IPC series is most common

## Federal / critical-infrastructure note

**Dahua is also banned for federal US use** under Section 889 (NDAA/TAA). Same as Hikvision. Route federal customers to [axis.md](./axis.md).

## Sales angle

**Opener:** "Are you on Dahua, Amcrest, or newer Lorex? All same handler. Plug in the RTSP URL, you'll see foot traffic by end of day. Most retail/restaurant merchants find their dwell-time-to-ticket correlation in week 1 — that's the cross-reference that pays for Premium."

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Stream opens but no detections | Confidence threshold too high for dim lighting | Adjust camera exposure or threshold |
| Auth fails | Dahua uses a specific URL-encoded password format | Test in VLC first to confirm the URL |
| Lorex doesn't work with Dahua handler | Older Lorex was Hikvision OEM | Switch to Hikvision handler |

---

_Last updated: 2026-05-31_
_Sourced from: src/camera/rtsp_handler.py + src/camera/detector.py + docs/playbook/_status/phase-2-decisions.md_
