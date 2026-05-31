# Wyze — NOT SUPPORTED

> Status: **NOT SUPPORTED**
> Why: Stock firmware has no RTSP on current SKUs (v4 / OG / v3 Pro / Floodlight / Battery). Older v2 and v3 had a community RTSP flash but it's brittle, fragile, and not something we'll support in production.

## What to say when a merchant asks

> "Wyze is great for the price, terrible for analytics. The current cameras don't expose RTSP at all — they're cloud-only. The older v2 and v3 had a community RTSP firmware flash but it breaks with every Wyze update and we can't support that in production.
>
> Here's the easy fix: $60 Reolink RLC-510A. Same place at your entrance, runs analytics, and you keep your Wyze for mobile push alerts on your phone. Two cameras, two jobs, no compromises."

## Why we don't support it (technical)

- **v4 / OG / v3 Pro / Floodlight / Battery** — no RTSP capability at all on stock firmware. Wyze's API is also closed.
- **v2 / v3** — community RTSP firmware exists but Wyze regularly pushes updates that overwrite it. We've seen production deployments break weekly. Not viable.
- **Wyze Cam Pan** — same story as v2/v3.

## What we sell instead

Recommend: **Reolink RLC-510A** (~$60) or **Hikvision DS-2CD2043G2-I** (~$80–$100).

Both are PoE, both work with our handler in 2 minutes, both keep working forever.

Pitch script:

> "Cheapest path: Reolink RLC-510A, $60 from Amazon or a local supplier, PoE so it's one cable. Get one at the entrance, plug into your network, give me the RTSP URL — you'll have foot traffic counts within an hour."

## Don't try this

Do NOT try to make Wyze work with RTSP firmware flashing in a paying production setup. It will fail, you'll burn the merchant relationship, and you'll lose recurring commission. The $60 alternative is genuinely the right answer.

## Sales math

- Wyze cam they already own: $0 sunk
- Reolink alternative: $60 one-time
- Premium tier upsell: $342/mo recurring → $239/mo commission for you, every month they stay
- Payback on the $60 in week 1

---

_Last updated: 2026-05-31_
_Sourced from: docs/playbook/_status/phase-2-decisions.md (cameras NOT SUPPORTED list — Wyze)_
