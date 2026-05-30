# Google Nest

## Status
CLOUD-ONLY (no local RTSP) — effectively UNSUPPORTED for Meridian's pipeline

## What they are
Google's consumer smart-home camera line (Nest Cam, Nest Doorbell, Nest Hub Max), sold through retail and the Google Store, tightly bound to the Google Home / Nest app and Google Cloud.

## Market presence in SMB
Medium-to-Large in owner-adjacent contexts. Reps will frequently see Nest in restaurants, cafes, and retail because owners install consumer cameras at home and in mixed home/business spaces. Rare as a primary business CCTV system.

## Protocol support
- **RTSP:** No local RTSP. RTSP only exists *inside* Google's Smart Device Management (SDM) API and only for legacy devices (Nest Cam legacy, Nest Doorbell legacy, Nest Hub Max). Newer wired/battery models are WebRTC-only.
- **ONVIF:** No
- **Proprietary cloud API:** Yes — Smart Device Management (SDM) API via Device Access
- **Local discovery (UPnP/Bonjour):** No (no LAN streaming surface)

## How to find the RTSP URL (exact path through their UI)
Not applicable. Nest exposes no user-facing RTSP URL in the Nest or Google Home app. There is no "RTSP enable" toggle. The only way to obtain an RTSP URL is programmatically via the SDM `CameraLiveStream.GenerateRtspStream` command, and only for the three legacy device types above.

## Authentication
OAuth 2.0 against a Google consumer account + a Device Access project. Requires a Google Cloud project, a partner connections manager link, and end-user consent. No username/password camera login exists.

## Models tested / known to work
| Model | Firmware | Notes |
|-------|----------|-------|
| None | — | Meridian has not validated any Nest device end-to-end. SDM RTSP streams are 5-minute sessions, single-client, and require constant `ExtendRtspStream` calls. |

## Common quirks
- Stream sessions expire every 5 minutes and must be extended via API call
- RTSP URLs are single-consumer — one viewer per stream, period
- Modern Nest Cam (battery) and Nest Cam (wired, 2nd gen) return WebRTC only — no RTSP at all
- No audio guarantees; codec mix varies by device generation
- All streams traverse Google's cloud — no LAN-only path exists

## Troubleshooting (rep-facing)
- **"Can I use my Nest cam with Meridian?"** → No. Recommend a cheap PoE camera alongside it.
- **"Why not?"** → Nest has no local stream. Everything goes through Google's cloud API with 5-minute sessions and a paid developer account.
- **"What should I buy instead?"** → Reolink RLC-510A or Hikvision DS-2CD2043G2-I (~$60-90), PoE, native RTSP, plug-and-play with Meridian.

## What blocks officially-supported status today
- No local stream surface — analytics latency and reliability depend entirely on Google's cloud
- $5 Device Access fee + Google Cloud project + OAuth consent flow per merchant
- 5-minute stream lifetime requires a session-extension worker we don't have
- WebRTC-only on all current-gen hardware; Meridian's pipeline consumes RTSP
- Single-client RTSP means we'd compete with the merchant's own viewing

## Recommendation tier
NOT SUPPORTED

**Reasoning:** Integration cost (SDM OAuth per merchant, $5 developer fee, WebRTC ingestion pipeline, session-extension service) is high while coverage is partial — only legacy devices get RTSP at all. Steer every Nest merchant to a $60 PoE camera for analytics.

## Sources consulted
- https://developers.google.com/nest/device-access/traits/device/camera-live-stream
- https://developers.google.com/nest/device-access/api/camera
- https://developers.google.com/nest/device-access/api/camera-wired
- https://developers.google.com/nest/device-access/api/camera-battery
- https://developers.google.com/nest/device-access/registration
