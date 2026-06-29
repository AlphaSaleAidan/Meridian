# Reolink

> Status: **OFFICIALLY SUPPORTED**
> Stream: RTSP
> Availability: **Camera intelligence add-on**
> Recommended budget pick: **RLC-510A** (~$60 PoE camera — our recommended alternative for merchants whose existing cameras aren't supported)

## What you tell the merchant

"Reolink connects in 2 minutes via RTSP. It's also our recommended budget pick if you don't have cameras yet — the RLC-510A is about $60 PoE, perfect for analytics."

## How the merchant connects

1. Reolink admin (web UI or Reolink Client) → confirm RTSP enabled (default port 554)
2. RTSP URL format: `rtsp://username:password@camera-ip:554/h264Preview_01_sub` (substream — use this) or `_main`
3. Paste into Meridian's **Settings → Cameras → Add Camera**

Typical time to connect: **2 minutes**.

## What we use the stream for

Same person-detection pipeline. See [_index.md](./_index.md).

## Why we recommend Reolink for new buys

- **RLC-510A** — ~$60 PoE bullet camera, 5MP, IR night vision, perfect for entrance counting
- PoE → single cable for power + data → simple install
- RTSP works out of the box (no firmware tinkering)
- Wide-angle options (RLC-820A) for zone coverage
- Reolink hasn't had the federal/security banning issues Hikvision/Dahua face

## Sales angle

**Opener (new install):** "If you don't have cameras yet, here's what we recommend: Reolink RLC-510A, about $60 each, PoE so it's one cable. Get one at your entrance for foot traffic and one at checkout for queue. You're at $120 in hardware total and we handle the analytics."

**Opener (existing Reolink):** "You're on Reolink — easiest connection we do. 2 minutes once we have the password."

**For unsupported camera merchants:** "Your [Wyze/Nest/Arlo] doesn't expose the right stream type. Cheapest fix: $60 Reolink alongside what you've got. Keep the Wyze for mobile alerts, the Reolink does the analytics."

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Reolink Argus / battery cameras don't work | Battery cameras only stream when motion-triggered | Use PoE models for analytics |
| Stream choppy | WiFi signal weak | Move to PoE/Ethernet |

---

_Last updated: 2026-05-31_
_Sourced from: src/camera/rtsp_handler.py + docs/playbook/_status/phase-2-decisions.md (officially supported, recommended $60 PoE alternative)_
