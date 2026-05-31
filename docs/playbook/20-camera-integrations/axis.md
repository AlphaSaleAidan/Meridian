# Axis

> Status: **OFFICIALLY SUPPORTED**
> Stream: RTSP
> Required plan: Premium or Command
> **Federal/critical-infrastructure qualifier:** NDAA/TAA compliant + CAGE 3DJU8 — the only camera brand we support that's federal-eligible

## What you tell the merchant

"Axis cameras work great. They're the Cadillac of IP cameras — more expensive than Hikvision/Dahua/Reolink, but they're the only brand on our list that's NDAA/TAA compliant. If you have any federal contracts or government customers, Axis is the only option."

## How the merchant connects

1. Camera admin UI (typically `http://camera-ip`) → log in
2. **System → Plain config → Network** → confirm RTSP enabled (default port 554)
3. RTSP URL format: `rtsp://username:password@camera-ip:554/axis-media/media.amp?videocodec=h264`
4. Paste into Meridian's **Settings → Cameras → Add Camera**

Typical time to connect: **3 minutes**.

## What we use the stream for

Same person-detection pipeline. See [_index.md](./_index.md).

## Compatibility notes

- Axis M, P, Q series all work — uniform RTSP endpoint
- Axis cameras have superior low-light performance — useful for restaurants with mood lighting or 24-hour shops
- Axis ACAP analytics modules can co-exist (we read RTSP independently)

## Federal / critical infrastructure — the qualifier

This is where Axis is unique:

- **NDAA Section 889 compliant** (Hikvision and Dahua are not)
- **TAA compliant** (Trade Agreements Act — required for federal procurement)
- **CAGE code 3DJU8** (DoD vendor registration)

**Who needs this:**
- Federal agencies (any branch)
- Defense contractors (DoD prime/sub contracts)
- Critical infrastructure (power, water, telecom)
- Some state/municipal contracts that follow federal procurement rules

**Qualifying discovery questions:**
1. "Do you have any federal contracts or government customers?"
2. "Does your security policy reference NDAA Section 889 or TAA?"

If yes to either → Axis is the only camera we can support. Disqualify them from Hikvision/Dahua early (it's a hard ban, not a preference).

## Sales angle

**Opener (commercial):** "Are you on Axis? Top-tier camera brand — only one on our list that's federal-eligible. Connection is 3 minutes. You'll see foot traffic patterns in 24 hours and the dwell-time-to-ticket correlation in week 1."

**Opener (federal/critical-infra):** "If you have any federal exposure — DoD contracts, government customers, critical infrastructure — Axis is the only camera brand we can support. Hikvision and Dahua are 889-banned. Let me show you what the analytics look like — it's the same pipeline, just on a compliant camera."

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Higher per-camera cost than Hikvision/Dahua | Real — Axis is premium-priced | Reframe: it's a one-time hardware cost; the analytics ROI dwarfs the camera cost over 12 months |
| RTSP URL format varies by firmware | Older Axis firmware uses different endpoint | Check Axis VAPIX docs for the merchant's firmware version |

---

_Last updated: 2026-05-31_
_Sourced from: src/camera/rtsp_handler.py + docs/playbook/_status/phase-2-decisions.md (officially supported, NDAA/TAA + CAGE 3DJU8 federal qualifier)_
