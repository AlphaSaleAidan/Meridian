# Arlo

## Status
CLOUD-ONLY (no RTSP)

## What they are
Battery-powered, wireless consumer security cameras (Arlo Pro, Ultra, Essential, Go series) sold direct-to-consumer and through big-box retail; the business is built around the Arlo Secure cloud subscription.

## Market presence in SMB
Small — heavily residential. Reps will mainly see Arlo in home-based businesses, pop-up retail, short-term rentals, and small offices where the owner reused a personal camera. Almost never in purpose-built commercial deployments.

## Protocol support
- **RTSP:** No (never officially supported on any current model; Arlo's stream is proprietary and encrypted)
- **ONVIF:** No
- **Proprietary cloud API:** Yes — Arlo Secure cloud only; live view and recordings flow through Arlo's servers
- **Local discovery (UPnP/Bonjour):** No

## How to find the RTSP URL (exact path through their UI)
Not applicable. There is no RTSP URL to expose. The Arlo Secure app and `my.arlo.com` web portal do not surface a stream URL because none is published by the device. Cameras talk to a Smart Hub / base station or directly to Arlo cloud over a proprietary encrypted channel.

## Authentication
N/A for streaming. Arlo account login (email + password, optional 2FA) gates the cloud app; there is no local stream credential to hand off to Meridian.

## Models tested / known to work
| Model | Firmware | Notes |
|-------|----------|-------|
| Any Arlo (Pro 3/4/5S Ultra, Essential, Go) | any | No official RTSP. Cloud-only. |

Historical note: Arlo Pro and Pro 2 (now end-of-life) had limited RTSP capability in older firmware. Current shipping cameras and the VMB5000 Smart Hub do not expose RTSP, including for cameras with local microSD storage — local recordings are accessible only through the Arlo Secure app.

## Common quirks
- Battery-powered models sleep between motion events; even if a stream existed, it would not be 24/7
- Smart Hub local storage (microSD on VMB5000) is viewable only via the Arlo app, not over the network
- Unofficial Scrypted plugin (`@scrypted/arlo-local`) reverse-engineers the base station to extract a stream — not supported by Arlo, breaks on firmware updates, do not recommend to merchants
- No ONVIF profile, so generic NVRs and VMS platforms cannot ingest Arlo either

## Troubleshooting (rep-facing)
- **"Stream won't open"** → Expected. Arlo does not stream over RTSP. Stop troubleshooting and move to the recommendation below.
- **"Stream drops after N minutes"** → N/A — no stream to drop.
- **"Black frames / no video"** → N/A — no stream to render.
- **"Can't find the camera on the network"** → Expected. Arlo cameras do not advertise on the LAN; they tunnel out to Arlo cloud.

## What blocks officially-supported status today
- No RTSP, no ONVIF, no documented local API
- Arlo's business model depends on the Secure subscription, so an open local stream is unlikely to ship

## Recommendation tier
NOT SUPPORTED

**Reasoning:** Arlo is cloud-only with no local stream protocol Meridian can ingest. Tell the merchant: "Arlo doesn't work with Meridian's vision analytics. Add a cheap PoE camera (Reolink or Hikvision) alongside the Arlo for analytics — keep the Arlo for the mobile app alerts they already use."

## Sources consulted
- https://community.arlo.com/t5/Arlo-Pro-5S-2K/RTSP-stream/td-p/1933804
- https://community.arlo.com/t5/Arlo-Secure/No-RTSP-stream/td-p/2454657
- https://community.arlo.com/t5/Arlo/RTSP-amp-standards/td-p/2443066
- https://kb.arlo.com/000062284/Arlo-SmartHub-and-Base-Station-Compatibility
- https://us.arlo.com/products/vmb5000-100nas
- https://www.npmjs.com/package/@scrypted/arlo-local
