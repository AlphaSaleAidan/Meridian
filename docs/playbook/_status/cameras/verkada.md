# Verkada

## Status
LIVE (RTSP works) on every current Verkada camera model — but **LAN-only** (RFC 1918 private addresses), opt-in per-camera via the Verkada Command portal, and disabled by default. Audio over RTSP unavailable on D-Series, Bullet Series, CM41-S; the CR63-E Remote Camera does not support RTSP at all.

## What they are
San Mateo enterprise cloud-managed camera + access control vendor. Cameras are proprietary hardware that record locally (onboard storage) and stream metadata/clips to the Verkada Command cloud — no on-prem NVR. Sold direct-only (no integrators) into mid-market and enterprise: multi-site retail, schools, healthcare, corporate offices, fitness chains. Strong "no NVR" pitch is the differentiator.

## Market presence in SMB
Small-to-Medium — Verkada targets 50+ camera deployments. Reps will see it at chain retail (regional grocery, multi-location boutique fitness), school districts, mid-sized offices, and any merchant that bought into the "no on-site server" pitch. Rare at single-location SMB; common at multi-site SMB rolling up to a corporate IT team.

## Protocol support
- **RTSP:** Yes on every current camera model (port 554) — opt-in, LAN-only, per-camera credential.
- **ONVIF:** No. Verkada does not implement ONVIF — RTSP is the only standards-based stream surface they expose.
- **Proprietary cloud API:** Yes — Verkada Command REST API (for management, events, clips), separate from RTSP.
- **Local discovery (UPnP/Bonjour):** No. Cameras are reached via their LAN IP (visible in Command); they advertise an FQDN backed by a public DNS A record pointing to the camera's private IP.

## How to find the RTSP URL (exact path through their UI)
1. Log into **Verkada Command** (web portal, admin role).
2. **All Products → Cameras → [select camera] → Settings**.
3. Under **Device**, toggle **Real Time Streaming Protocol (RTSP)** on.
4. Set a **username and password** — Verkada recommends a long random password, different from any other credential. **The password will not be shown again after creation.** Save it immediately.
5. Click **Enable**. Command displays the RTSP URL.
6. Expected format: `rtsp://<user>:<pass>@<camera-fqdn-or-lan-ip>:554/<stream-id>` — Verkada uses a camera-specific FQDN that resolves to the private LAN IP via a public DNS A record (this gives them a valid TLS cert for the Local Streaming feature, which is a separate HTTPS service on port 4100).
7. Two streams available: standard-quality and high-quality (per-camera setting in Command).

**Bulk enable:** Devices tab → multi-select cameras → enable RTSP across the fleet (still requires unique password per camera).

## Authentication
Username + password (set in Command), Digest auth. Verkada strongly recommends a random long password; the system refuses to reveal it after creation. The credential lives on the camera, not in Verkada cloud — losing it requires regenerating.

## Models tested / known to work
| Model | Firmware | Notes |
|-------|----------|-------|
| CD-series (dome) | current | RTSP main + sub; audio in stream |
| CB-series (bullet) | current | RTSP main + sub; **no audio in RTSP** |
| CF-series (fisheye) | current | Single fisheye stream |
| CM-series (mini indoor) | current | RTSP; CM41-S excluded from audio |
| CG-series (gun) | current | Recent line; RTSP supported |
| D-series (entry tier) | current | RTSP; **no audio in RTSP** |
| CR63-E Remote Camera | current | **No RTSP support** |

## Common quirks
- **LAN-only enforcement is hard.** Verkada's RTSP service refuses to serve a stream to a non-RFC1918 source address. No port-forwarding workaround — if Meridian needs to ingest, the Meridian collector must sit on the merchant's LAN (or a VPN tunnel into it).
- Cameras with **non-standard NAT'd internal IPs** (outside 10/8, 172.16/12, 192.168/16) will fail silently — confirm camera IPs are in standard private space.
- No ONVIF discovery — every camera must be enabled manually in Command. No way to auto-enroll a Verkada fleet.
- The Verkada cloud Command portal is the **only** way to enable RTSP — the camera itself has no local web UI.
- Audio is unavailable on D-Series, Bullet Series, and CM41-S even with RTSP enabled (hardware/firmware limitation).
- Network ports: **554** for RTSP (analytics path), **4100 TCP/UDP** for Verkada's Local Streaming (browser viewing — separate feature).

## Troubleshooting (rep-facing)
- **"Stream won't open"** → 1) Confirm RTSP toggled on for that camera in Command. 2) Confirm Meridian collector is on an RFC1918 LAN address — RTSP is silently refused from any other source. 3) Test the URL in VLC from a LAN host on the same subnet as the camera.
- **"Stream drops after N minutes"** → 1) Check Command for camera-side firmware updates (Verkada auto-pushes — reboot may interrupt). 2) Verify the camera's DNS lookup resolves to its current LAN IP (the FQDN-based URL fails if the IP changed). 3) Set a DHCP reservation on the camera IP.
- **"Black frames / no video"** → 1) Confirm at least one stream profile (standard or high-quality) is enabled in Command. 2) Try the alternate quality stream. 3) Bullet / D-series have no audio over RTSP — confirm Meridian isn't blocking on audio negotiation.
- **"Can't find the camera on the network"** → 1) Command → Cameras → [camera] → Network Info shows the LAN IP. 2) No ONVIF/UPnP discovery — must come from Command. 3) Verify the camera reports "online" in Command — if offline, the LAN IP entry may be stale.

## What blocks officially-supported status today
- Hard LAN-only restriction — Meridian's collector must live on the merchant's network, or we need a site-to-site VPN. No remote-pull architecture works.
- Per-camera manual enable in Command — fleet onboarding for a 100-camera customer is slow without their cooperation.
- Customer must agree to expose RTSP — some Verkada buyers chose the platform precisely because "cameras don't speak any open protocol" and may resist enabling it.

## Recommendation tier
OFFICIALLY SUPPORTED (LAN) — with the caveats above

**Reasoning:** Verkada actually ships standards-based RTSP on every current model, which is unusual for a cloud-native vendor. The blocker is operational, not protocol: Meridian must be on the LAN, and the customer's admin must enable it. Pitch fits well for multi-site retail customers who chose Verkada for cloud management but want analytics on top.

## Sources consulted
- https://www.verkada.com/blog/verkada-announces-low-latency-rtsp-streaming/
- https://help.verkada.com/verkada-cameras/video-streaming-and-sharing/live-streaming/low-latency-rtsp-streaming
- https://help.verkada.com/verkada-cameras/video-streaming-and-sharing/live-streaming/local-streaming-on-verkada-cameras
- https://help.verkada.com/verkada-cameras/video-streaming-and-sharing/live-streaming
- https://help.verkada.com/command-connector/command-connector-network-settings
- https://www.visioforge.com/help/docs/dotnet/camera-brands/verkada/
