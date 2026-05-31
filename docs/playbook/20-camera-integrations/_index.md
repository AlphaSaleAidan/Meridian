# Camera Integrations — Index

Camera Intelligence is a **Premium** ($599/CA$685) or **Command** ($1,199/CA$1,370) feature. Standard plans cannot connect cameras.

## What Camera Intelligence does

- **Foot traffic counts** (hourly / daily / weekly)
- **Queue length + wait time**
- **Dwell time per zone** (entrance, displays, checkout, seating)
- **Path analysis** (how customers move through the store)
- **Cross-reference** with POS (which zones correlate with higher tickets)

All processing produces **anonymous counts and heatmaps**. We do **not** do facial recognition. We do **not** store individual customer images.

## Officially supported (5)

| Brand | Stream | OEM coverage | Doc |
|-------|--------|--------------|-----|
| **Hikvision** | RTSP | Covers LaView, ANNKE, EmpireTech, older Lorex, older Honeywell | [hikvision.md](./hikvision.md) |
| **Dahua** | RTSP | Covers Amcrest (sister-brand) | [dahua.md](./dahua.md) |
| **Reolink** | RTSP | — | [reolink.md](./reolink.md) |
| **UniFi** | **RTSPS** (port 7441) | — | [unifi.md](./unifi.md) |
| **Axis** | RTSP | NDAA/TAA + CAGE 3DJU8 → unlocks federal/critical-infra | [axis.md](./axis.md) |

## Not supported (3)

| Brand | Why | Doc |
|-------|-----|-----|
| **Wyze** | Stock firmware has no RTSP on current SKUs (v4 / OG / v3 Pro / Floodlight / Battery); flash is fragile and brittle | [wyze.md](./wyze.md) |
| **Nest** | Current-gen is WebRTC-only; legacy SDM RTSP is single-client, 5-min sessions, + $5/merchant Device Access fee | [nest.md](./nest.md) |
| **Arlo** | Cloud-only encrypted streams; no RTSP, no ONVIF, no local | [arlo.md](./arlo.md) |

## In research (research swarm landed — outcomes below)

The camera expansion research swarm completed during Phase 3. Findings (full per-brand writeups in `docs/playbook/_status/cameras/`):

| Brand | Outcome | Rep takeaway |
|-------|---------|--------------|
| **Amcrest** | LIVE | Use Dahua handler — Amcrest is Dahua's US sister-brand |
| **Lorex (modern)** | LIVE | Use Dahua handler (post-Dahua acquisition); use Hikvision handler for older Lorex |
| **Eufy** | PARTIAL | Wired/indoor models with RTSP work; battery/doorbell are cloud-only (treat like Wyze — recommend Reolink alongside) |
| **Ring** | NOT SUPPORTED | Cloud-only (Amazon). Same playbook as Arlo — recommend $60 Reolink alongside |
| **Verkada** | PARTIAL | RTSP works but LAN-only + opt-in per camera. Enterprise-friendly but needs IT involvement |
| **Avigilon** | RESEARCH | See `_status/cameras/avigilon.md` |
| **Bosch** | RESEARCH | See `_status/cameras/bosch.md` |
| **Swann** | RESEARCH | See `_status/cameras/swann.md` |
| **Camect** | RESEARCH | See `_status/cameras/camect.md` |

Rep-facing writeups for these are in the `_status/cameras/` reference directory until they're promoted. For now, treat them as: "let me check, I'll get back to you in 24 hours" if a merchant asks.

## Federal / critical infrastructure customers

If the merchant is government, critical infrastructure, or has NDAA/TAA requirements (Section 889): **only Axis qualifies.** Hikvision and Dahua are banned for federal use. Disqualify those merchants out of Hik/Dahua early.

## How to connect any IP camera (universal)

If a brand isn't on the supported list but has RTSP:

1. Confirm the camera supports RTSP (check spec sheet or admin UI)
2. Get the RTSP URL — typically `rtsp://username:password@camera-ip:554/stream1` (port + path varies)
3. Test it in VLC first (`File → Open Network Stream`)
4. If it plays in VLC, paste it into Meridian's **Settings → Cameras → Add Camera**
5. We start consuming the stream within 60 seconds

See [_how-to-connect-any-camera.md](./_how-to-connect-any-camera.md) for the full diagnostic flow.

## Rep response for unsupported cameras

The merchant has a Wyze, Nest, or Arlo and wants to use it for analytics. Honest answer:

> "Those cameras don't expose the right stream type for analytics. The fix is cheap — a $60 PoE camera (Reolink RLC-510A or Hikvision DS-2CD2043G2-I) gives you analytics, and you keep the Wyze/Nest/Arlo for mobile alerts. Two cameras, two purposes, no compromises."

That's the right play almost every time. Don't try to make an Arlo work — you'll burn a deal trying.

## Hardware merchant supplies vs. we supply

**We don't sell cameras.** Merchant supplies their own. We provide:
- Compatibility list (this page)
- Recommended budget PoE models (above)
- Installation positioning guidance (45° overhead at entrance, wide coverage at zones)
- Network requirements (2–4 Mbps per camera, same network as Meridian edge device or accessible via merchant public IP with port forward)

## PIPEDA / Privacy (Canada)

For Canadian merchants running Camera Intelligence:

1. **Visible signage at entrances** notifying visitors of video analytics — Meridian provides bilingual templates (English/French, mandatory in Quebec)
2. **Posted privacy policy** — Meridian provides a customizable template
3. **30-day raw footage retention** — auto-enforced; merchants can't override

Key talking point: "This is anonymous analytics, not surveillance. We count people and track movement patterns — we don't identify individuals. Same tech major retailers use, made affordable for independents."

---

_Last updated: 2026-05-31_
_Sourced from: src/camera/ (5 modules: detector, line_counter, people_counter, pipeline, rtsp_handler) + docs/playbook/_status/phase-2-decisions.md (camera support list)_
