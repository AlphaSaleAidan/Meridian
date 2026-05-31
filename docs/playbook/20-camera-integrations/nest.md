# Nest — NOT SUPPORTED

> Status: **NOT SUPPORTED**
> Why: Current-gen Nest cameras are WebRTC-only (not RTSP). Legacy SDM RTSP requires single-client sessions, 5-minute session limit, and a $5/merchant Device Access fee — all dealbreakers for production analytics.

## What to say when a merchant asks

> "Nest is built for consumer mobile viewing, not for analytics partners like us. The current cameras only stream via WebRTC, which is a different protocol than what our system uses. There was an older SDM API with RTSP, but it's single-client (so only one connection at a time — we can't run analytics if you're watching the camera on your phone), sessions cap at 5 minutes, and Google charges a $5/merchant Device Access fee on top.
>
> Easy alternative: $60 Reolink RLC-510A alongside your Nest. Reolink runs the analytics; Nest stays as your mobile alert camera."

## Why we don't support it (technical)

- **Current-gen Nest (Cam, Doorbell battery, indoor/outdoor wired)** — WebRTC-only. No RTSP, no ONVIF.
- **Legacy SDM RTSP** — single-client (incompatible with simultaneous merchant viewing), 5-minute session limit (forces constant reconnection storms), $5/merchant Device Access program fee (cuts our economics).

Even if we built SDM support, the merchant would have to choose between us streaming or them watching on their phone — they can't do both. That's a non-starter.

## What we sell instead

Recommend: **Reolink RLC-510A** ($60) or **Hikvision DS-2CD2043G2-I** ($80–$100).

Pitch script:

> "Keep your Nest for the doorbell and your phone alerts — that's what it's great at. Add a $60 Reolink at the entrance for the analytics piece. Two-camera setup, total $60 in new hardware. We'll have foot traffic running by tomorrow."

## Sales math

Same as Wyze:
- Nest already there: $0
- Reolink alternative: $60 one-time
- Premium tier upsell: $239/mo commission to you, recurring
- Payback week 1

## Watch out

If a merchant insists on Nest-only because they have many cameras and don't want to mix systems, the honest answer is:

> "If you're committed to Nest-only, Meridian's camera intelligence isn't going to work for you today. The POS analytics still work (Standard plan). When/if Nest opens up RTSP on current-gen cameras, you'll be first on the list."

Don't oversell — losing the Premium upsell is better than losing the whole account in 60 days when the camera piece doesn't work.

---

_Last updated: 2026-05-31_
_Sourced from: docs/playbook/_status/phase-2-decisions.md (cameras NOT SUPPORTED list — Nest WebRTC + SDM constraints)_
