# Avigilon (Motorola Solutions)

## Status
LIVE (RTSP works) on Avigilon Unity (formerly ACC) cameras: H4, H5A, H6A, H6X — port 554, `/defaultPrimary` path with stream-type parameter. Avigilon Alta (cloud-native cameras, formerly Ava) is configured differently — see notes.

## What they are
Vancouver-founded enterprise IP camera + VMS maker, acquired by Motorola Solutions in 2018, rebranded into two product lines: **Avigilon Unity** (on-prem, evolved from Avigilon Control Center — H4/H5A/H6A/H6X cameras + ACC/Unity VMS) and **Avigilon Alta** (cloud-native, evolved from the Openpath + Ava acquisitions — Ava-derived cameras + Alta Aware cloud VMS). Sold through certified integrators into enterprise retail chains, banks, schools, hospitals, transit. Premium tier ($500–$3K+ per camera).

## Market presence in SMB
Small — Avigilon is integrator-channel and enterprise-priced. Reps will see it at multi-site retail headquarters, big-box chains, banks, school districts, hospitals, and government-adjacent customers. Almost never at standalone SMB.

## Protocol support
- **RTSP:** Yes on Unity-line cameras (port 554). On Alta cloud cameras, RTSP is provisioned through the Alta Aware portal (requires the cloud subscription).
- **ONVIF:** Yes on H4 Pro, H5A, H6A, H6X — Profile S streaming, Profile G for storage retrieval on H6 firmware 4.4.0+. Enabling ONVIF on multi-sensor cameras can cap resolution (e.g., 40/61 MP H5 Pro → 32 MP via ONVIF).
- **Proprietary API:** ACC/Unity SDK; Alta Aware REST API for cloud-line.
- **Local discovery:** Avigilon Camera Configuration Tool; ONVIF WS-Discovery; static IP common.

## How to find the RTSP URL (exact path through their UI)
**Unity-line cameras (H4/H5A/H6A/H6X), via camera web UI:**
1. Browse to camera IP → log in (default `administrator` / set on commissioning).
2. **Setup → Network → RTSP Stream URI** — Avigilon generates and displays the URL here. Copy it.
3. Expected format: `rtsp://<user>:<pass>@<camera-ip>:554/defaultPrimary?streamType=u`
   - `streamType=u` = unicast (use this)
   - `streamType=m` = multicast (only if the network supports it and integrator has configured IGMP)
   - Secondary stream: `/defaultSecondary?streamType=u` (where exposed; not on every model)
4. **Setup → Image and Display → Compression and Image Rate** — RTSP profile is tied to the stream profile here; confirm at least one H.264 profile is active.

**Unity / ACC server (Media Gateway) RTSP relay:**
- If the cameras are behind the ACC/Unity server and not directly reachable, the Unity Video Media Gateway can re-broadcast RTSP:
- Pattern (Media Gateway): `rtsp://<server-ip>:554/<camera-logical-id>/<stream>`
- Configured in the Unity Web Client → System Settings → Media Gateway.

**Alta-line cameras (cloud):**
- Configured in **Alta Aware web portal → Devices → [camera] → RTSP** — generates a per-camera URL with token auth. Stream is delivered local-only (LAN) like Verkada; requires the Alta subscription to be active.

## Authentication
Unity cameras: Username + password, Digest auth. Created at commissioning — no factory default since H5A firmware. Alta: portal-issued credentials embedded in the generated URL.

## Models tested / known to work
| Model | Line | Notes |
|-------|------|-------|
| H4 Pro / H4A (older) | Unity | Full RTSP + ONVIF; many still in field |
| H5A bullet/dome (current backbone) | Unity | `/defaultPrimary?streamType=u`; ONVIF Profile S |
| H5A Multisensor / Fisheye | Unity | Per-sensor stream; ONVIF caps resolution on 40/61MP |
| H6A / H6X (newest Unity-line) | Unity | Same URL pattern; Profile G recording retrieval added in 4.4.0+ |
| H4 Video Intercom (door station) | Unity | RTSP works; audio in stream |
| Avigilon Alta cameras (ex-Ava) | Alta | RTSP per-camera via Alta portal, LAN-local |

## Common quirks
- The RTSP URL is **only generated after** the camera's Compression/Image Rate profile is configured — a freshly-commissioned camera may show an empty URI field.
- Enabling ONVIF on multi-sensor / high-resolution cameras (40 MP, 61 MP H5 Pro) drops the ONVIF-exposed stream to 32 MP — the native Unity stream stays full-res.
- ACC/Unity-managed cameras may have RTSP disabled by default — integrator must enable it on the camera, not just at the VMS level.
- Multi-sensor cameras expose one stream per sensor head — the URI is the same but with sensor-id paths.
- Default H.264; H.265 available on H6A/H6X — analytics pipelines should explicitly request H.264 profile if needed.
- Static IPs are the norm — DHCP discovery often fails because the integrator configured fixed addresses.

## Troubleshooting (rep-facing)
- **"Stream won't open"** → 1) Confirm RTSP URI was generated in the web UI (Setup → Network → RTSP). 2) Confirm at least one compression profile is active. 3) Test the literal URI in VLC on the LAN.
- **"Stream drops after N minutes"** → 1) Switch to `streamType=u` (unicast) — multicast often fails on flat L2 networks. 2) Lower frame rate in the compression profile. 3) Check ACC/Unity server isn't holding an exclusive stream session.
- **"Black frames / no video"** → 1) Codec mismatch — confirm profile is H.264, not H.265. 2) Privacy mask region. 3) Reboot camera if the compression profile was just changed.
- **"Can't find the camera on the network"** → 1) Run Avigilon Camera Configuration Tool. 2) Ask the integrator for static IPs — Avigilon installs rarely use DHCP. 3) Check VLAN; camera traffic is usually segregated.

## What blocks officially-supported status today
- Integrator-channel access — RTSP credentials usually live with the integrator, not the merchant. First call is to the integrator, not the camera.
- Mixed Unity / Alta lineup — reps must know which generation they're looking at (H-series = Unity, Ava-derived = Alta).

## Recommendation tier
OFFICIALLY SUPPORTED (Unity-line H4 / H5A / H6A / H6X). BEST EFFORT on Alta-line cameras (works, but depends on an active Alta cloud subscription configured to expose RTSP).

**Reasoning:** Unity-line cameras ship reference-grade RTSP and ONVIF with a documented URL pattern; the friction is integrator access, not protocol. Alta is a credible path but adds a subscription dependency we'd rather avoid for SMB. Treat Avigilon installs as premium enterprise opportunities — usually multi-site retail HQ.

## Sources consulted
- https://docs.avigilon.com/bundle/unity-video-media-gateway-8-7/page/system-management/media-gateway-rtsp-url.htm
- https://help.avigilon.com/h3-webui/en-us/H3/WebUI/WebUI_ConfigRTSP.htm
- https://support.avigilon.com/s/article/Access-the-RTSP-Stream-or-Latest-JPEG-Image-from-an-H-264-Camera-or-Encoder
- https://support.avigilon.com/s/article/Examples-of-RTSP-Stream-URI-of-an-Avigilon-Multi-sensor-Camera
- https://docs.avigilon.com/bundle/alta-video/page/Products/aware/rtsp/assemble-rtsp.htm
- https://www.ipcamlive.com/avigilon
- https://www.ispyconnect.com/camera/avigilon
- https://d8eqw8u9b6kgn.cloudfront.net/file_library/pdf/web-ui/avigilon-h4-and-h5-web-interface-user-guide-en-v20.pdf
