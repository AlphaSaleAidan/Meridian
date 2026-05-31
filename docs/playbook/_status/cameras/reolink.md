# Reolink

## Status
LIVE (RTSP works on PoE / wired Wi-Fi models) — CLOUD-ONLY on standalone battery models (Argus and other battery cams without Home Hub)

## What they are
Shenzhen-based consumer / prosumer IP camera brand sold direct (reolink.com), Amazon, and Costco; popular with SMBs because PoE bullets/turrets are $50–$150 and the app is friendly.

## Market presence in SMB
Large — extremely common in independent retail, smoke shops, convenience stores, smaller QSRs, and self-installed gyms/salons. Often the "first real camera" after a Wyze/Ring setup.

## Protocol support
- **RTSP:** Yes on wired/PoE and most plug-in Wi-Fi cams (default port: 554). No on standalone battery cams.
- **ONVIF:** Yes on wired/PoE; no on standalone battery.
- **Proprietary cloud API:** Yes (Reolink Cloud, used by Reolink App / Client).
- **Local discovery (UPnP/Bonjour):** Yes (UID + LAN scan via Reolink Client).

## How to find the RTSP URL (exact path through their UI)
**Reolink App (iOS/Android):**
1. Tap camera → **gear icon (Settings)** → **Device settings** → **Advanced Network Settings** → **Server Settings**
2. Confirm **RTSP** is enabled; note the port (default 554).

**Reolink Client (Windows/Mac):**
1. Right-click camera → **Device Settings** → **Network** → **Advanced** → **Server Settings**
2. Confirm RTSP enabled, port = 554, **Save**.
3. Get IP from **Network → Network Status**.
4. Build URL — current official format: `rtsp://<user>:<pass>@<ip>:554/Preview_01_main` (sub: `Preview_01_sub`). Legacy format still works on most firmware: `rtsp://<user>:<pass>@<ip>:554/h264Preview_01_main`.

## Authentication
Username + password (digest auth). Create a dedicated non-admin user in **Settings → User Management**.

## Models tested / known to work
| Model | Firmware | Notes |
|-------|----------|-------|
| RLC-510A / 520A / 810A (PoE bullet) | recent | Main stream H.265; use sub for H.264 |
| RLC-820A / 822A / 833A | recent | 4K, H.265 default; sub stream H.264 |
| E1 Pro / E1 Zoom (plug-in Wi-Fi) | recent | RTSP works, indoor pan-tilt |
| Argus 2 / 3 / 3 Pro (battery, standalone) | any | **No RTSP** — cloud only |
| Battery cam + Reolink Home Hub | — | RTSP/ONVIF exposed via the Hub |

## Common quirks
- **H.265 default on 8MP+ main stream**, H.264 on sub. Meridian's RTSP handler should pull `Preview_01_sub` when H.264-only is required.
- Audio is in-stream when enabled on the camera (off by default on some PoE models).
- Two streams: `main` (full res) and `sub` (lower res / lower bitrate) — prefer sub for analytics.
- App-only "UID" cloud connections won't expose RTSP; camera must be reachable on the LAN.

## Troubleshooting (rep-facing)
- **"Stream won't open"** → 1) Confirm camera is wired/Wi-Fi PoE, not battery. 2) Settings → Advanced Network → Server → RTSP enabled. 3) Try sub stream URL (`Preview_01_sub`).
- **"Stream drops after N minutes"** → 1) Check if it's a battery cam on a Home Hub (5-min preview sleep). 2) Move to PoE model. 3) Update firmware in Reolink Client.
- **"Black frames / no video"** → 1) Decoder lacks H.265 — switch to sub stream. 2) Disable audio in camera settings. 3) Confirm IP didn't change (set DHCP reservation).
- **"Can't find the camera on the network"** → 1) Reolink Client → Add Device → scan LAN. 2) Same subnet as the router. 3) Power-cycle the PoE injector / switch port.

## What blocks officially-supported status today
- Standalone battery models (Argus line without Home Hub) cannot stream RTSP at all — must be flagged at qualification.

## Recommendation tier
OFFICIALLY SUPPORTED for RLC-* PoE and E-series plug-in Wi-Fi. NOT SUPPORTED for standalone battery (Argus/B-series) unless paired with a Reolink Home Hub.

**Reasoning:** RTSP is enabled by default on PoE/wired models with a well-documented URL pattern; battery models lack the protocol entirely by hardware design.

## Sources consulted
- https://support.reolink.com/articles/900000630706-Introduction-to-RTSP/
- https://support.reolink.com/hc/en-us/articles/360004441753-Can-Reolink-Battery-Powered-Cameras-Work-with-3rd-Party-Software/
- https://support.reolink.com/articles/900000621783-How-to-Configure-Reolink-Ports-Settings/
- https://support.reolink.com/hc/en-us/articles/900000638523-What-s-the-Format-of-the-RTSP-Video-Audio-that-Reolink-Cameras-Use/
- https://support.reolink.com/hc/en-us/articles/900000604803-Do-Reolink-Cameras-Support-H-265/
- https://community.reolink.com/topic/1182/rtsp-urls
