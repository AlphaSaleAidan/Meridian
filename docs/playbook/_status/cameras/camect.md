# Camect

## Status
NOT A CAMERA VENDOR — Camect is an AI Smart Camera Hub (effectively a small on-prem NVR + AI alerting box) that **ingests** RTSP/ONVIF cameras. It does not manufacture cameras. Question for this matrix: can Meridian pull a stream from Camect, or do we go directly to the cameras Camect is consuming? Answer: **go directly to the cameras.** Camect itself does not expose a documented, supported RTSP rebroadcast API for 3rd-party analytics pipelines.

## What they are
US startup (Mountain View, CA) selling a $279–$499 home/small-business NVR appliance ("Smart Camera Hub") that does on-device AI object detection ("not bugs, not rain, not leaves") and pushes intelligent alerts to the Camect app. Sells to integrators (Netwatch, monitoring partners), prosumers, and small businesses tired of cloud subscription fees. Lifetime AI updates, no recurring cost.

## Market presence in SMB
Small in true SMB — Camect is more common in prosumer residential, small contractor offices, and Netwatch-monitored sites. Reps may see it at small commercial customers where a single integrator standardized on the hub.

## Protocol support (Camect's role)
- **RTSP (inbound to Camect):** Yes — Camect ingests cameras over RTSP and ONVIF. Most ONVIF-conformant cameras auto-discover; RTSP-only cameras require manual URL entry in the Camect app.
- **RTSP (outbound from Camect to 3rd parties like Meridian):** **Not documented as a supported feature.** Camect's public docs and FAQs do not describe a rebroadcast endpoint. The `camect-py` GitHub library exposes hub metadata, camera lists, and alert management — but not a video stream URL for 3rd-party consumption.
- **ONVIF:** Consumer-side (Camect speaks ONVIF to discover cameras). Camect does not present itself as an ONVIF source to 3rd parties.
- **Cloud / API:** Camect cloud for app access; Eagle Eye Networks and Netwatch integrations are partner-specific (not general 3rd-party APIs).
- **Local discovery:** Camect discovers cameras on the LAN; Camect itself advertises on the LAN to its app.

## How to find the RTSP URL (exact path through their UI)
**The right move is: bypass Camect and go directly to the underlying cameras.** Whatever brand of camera the merchant has Camect ingesting (Hikvision, Dahua, Reolink, Amcrest, UniFi, Axis), use that brand's playbook entry. Camect's IP and credentials are not the path to a Meridian-consumable stream.

If a rep is forced to look anyway:
1. Open the **Camect app** (web or mobile) → **Cameras**.
2. For each camera, the **camera's own RTSP URL** is visible in **Camera Settings → RTSP URL** (this is the URL Camect uses to ingest, not a Camect-served URL). That URL points at the camera directly.
3. Hand that camera-direct URL to Meridian — and follow the relevant vendor playbook ([hikvision.md](./hikvision.md), [dahua.md](./dahua.md), [reolink.md](./reolink.md), [unifi.md](./unifi.md), [axis.md](./axis.md)).

## Authentication
Camect itself uses account-based auth for its app. The camera credentials Camect stores are per-camera (Digest / Basic, depending on brand). Reps will need camera-level credentials regardless.

## Models / scope
| Item | Notes |
|------|-------|
| Camect Smart Camera Hub (Home) | $279, 8 cameras |
| Camect Smart Camera Hub (Pro / All-In) | $499+, more cameras, lifetime AI |
| Camect-py (GitHub) | Python client for hub metadata and alerts — not video |

## Common quirks
- Camect is **inventory, not protocol** — the question "does Camect support RTSP" almost always means "what cameras is the merchant running through Camect," not "can we integrate with the hub."
- Camect's value-add (AI alerting, false-positive filtering) is at the application layer and doesn't help or hurt Meridian's pipeline either way.
- If a merchant has Camect and wants Meridian, they can run both: Camect ingests cameras for the merchant's alerting/recording, Meridian pulls the same RTSP streams from the cameras directly for analytics. No conflict — RTSP supports multiple readers per camera as long as the camera's session cap isn't hit.
- Do not promise a "Camect integration" — none exists today as a supported path.

## Troubleshooting (rep-facing)
- **"Can Meridian work with my Camect?"** → Yes, but we connect to the underlying cameras, not to Camect. Open Camect, identify the camera brand and IP for each feed, then use the vendor playbook for that brand.
- **"Will running Meridian alongside Camect overload the cameras?"** → Usually no — most modern IP cameras support 2–4 concurrent RTSP sessions. If the camera does drop sessions, switch Meridian to the sub-stream.
- **"Camect has the AI alerts already — why do I need Meridian?"** → Camect does generic object alerts ("person detected"); Meridian does retail-specific analytics (foot traffic, dwell time, queue length, conversion). Different products, both pull from the same RTSP source.

## What blocks officially-supported status today
- Camect is not a camera vendor — there's nothing to "officially support" at the brand level.
- No documented Camect → 3rd-party RTSP rebroadcast API.

## Recommendation tier
NOT SUPPORTED (as a brand)

**Reasoning:** Camect doesn't make cameras and doesn't expose a Meridian-consumable stream. The correct rep behavior when walking into a Camect site is to identify the cameras Camect is using and integrate with those directly, following the vendor playbooks. Treat Camect's presence as a positive signal (the merchant cares enough about cameras to buy a smart hub) but route around it.

## Sources consulted
- https://camect.com/
- https://camect.com/which-cameras-work-with-camect/
- https://camect.com/frequently-asked-questions/
- https://camect.com/integrations/
- https://github.com/camect/camect-py
- https://www.een.com/partner/camect/
- https://netwatchusa.com/netwatch-platform/technology-partners/netwatch-camect-integration/
