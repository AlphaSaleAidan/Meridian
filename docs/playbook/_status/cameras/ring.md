# Ring (Amazon)

## Status
CLOUD-ONLY (no RTSP, no ONVIF on Ring's own cameras) — effectively UNSUPPORTED for Meridian's pipeline.

## What they are
Amazon-owned consumer security brand (Ring Doorbell, Stick Up Cam, Spotlight Cam, Floodlight Cam, Indoor Cam, Ring Pan-Tilt) sold direct, Amazon, and big-box retail; everything funnels into the Ring app and Ring Protect cloud subscription. Built cloud-first from day one — Ring has never shipped RTSP on any camera.

## Market presence in SMB
Large in owner-adjacent contexts. Reps will see Ring everywhere: cafes, salons, smoke shops, contractor offices, home-based businesses, AirBnBs. Almost always installed by the owner for the doorbell or driveway alerts, not as a commercial CCTV system.

## Protocol support
- **RTSP:** No on every Ring-branded camera, every model, every firmware. Closed Amazon protocol, no local stream endpoint.
- **ONVIF:** No on Ring's own cameras. (Ring Edge with a Ring Alarm Pro subscription can *consume* a 3rd-party ONVIF camera as a Ring viewer — that's the reverse direction; doesn't help us.)
- **Proprietary cloud API:** Yes — Ring cloud only. No published developer API for video.
- **Local discovery (UPnP/Bonjour):** No.

## How to find the RTSP URL (exact path through their UI)
Not applicable. There is no RTSP URL anywhere in the Ring app, ring.com portal, or device webconfig — because none exists. There is no "enable RTSP" toggle, no Advanced settings menu, no developer mode. Cameras tunnel to Amazon servers over a proprietary encrypted channel.

## Authentication
N/A for streaming. Ring account email + password + 2FA gates the app. There is no per-camera credential to hand to Meridian.

## Models tested / known to work
| Model | Firmware | Notes |
|-------|----------|-------|
| Any Ring camera (Doorbell, Stick Up, Spotlight, Floodlight, Indoor, Pan-Tilt) | any | No official RTSP. Cloud only. |

Unofficial: the `ring-mqtt` open-source project reverse-engineers Ring's cloud stream and re-publishes it as RTSP on a local host. **Do not recommend** — it still routes through Amazon's cloud (so it offers no latency or reliability benefit), depends on Ring's auth token (which Ring rotates), and breaks on app updates.

## Common quirks
- Battery-powered Ring cameras sleep between motion events; even if a stream existed, it would not be 24/7.
- Ring Edge (an on-prem video processing tier introduced with Ring Alarm Pro) does NOT expose RTSP — it only enables local recording for the Ring app.
- Ring's ONVIF support article describes Ring as a *consumer* of 3rd-party ONVIF cameras inside its app — confusing for reps. Ring cameras themselves do not speak ONVIF.

## Troubleshooting (rep-facing)
- **"Stream won't open"** → Expected. Ring does not stream over RTSP. Stop troubleshooting and move to the recommendation below.
- **"Stream drops after N minutes"** → N/A — no stream to drop.
- **"Black frames / no video"** → N/A — no stream to render.
- **"Can't find the camera on the network"** → Expected. Ring cameras do not advertise on the LAN; they tunnel out to AWS.

## What blocks officially-supported status today
- No RTSP, no ONVIF, no documented local API on any Ring camera.
- Ring's business model is built on the Ring Protect subscription — opening a local stream is unlikely to ship.
- Reverse-engineered workarounds (ring-mqtt) still depend on Ring's cloud and break on auth-token rotation.

## Recommendation tier
NOT SUPPORTED

**Reasoning:** Ring is cloud-only with no local stream Meridian can ingest. Same script as Arlo and Nest: "Ring doesn't work with Meridian's vision analytics. Add a $60 PoE Reolink or Hikvision alongside the Ring — keep the Ring for doorbell/motion alerts, we use the PoE camera for the analytics stream."

## Sources consulted
- https://community.ring.com/t/rtsp-protocol-for-ring-devices/992
- https://ring.com/support/articles/snp6q/Using-Your-ONVIF-Compatible-Camera-with-Ring-Edge
- https://ring.com/onvif-support-ring-app
- https://www.smartrtsp.com/cameras/ring
- https://github.com/tsightler/ring-mqtt/wiki/Video-Streaming
- https://www.ispyconnect.com/camera/ring
