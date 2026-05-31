# Bosch (Building Technologies / Inteox)

## Status
LIVE (RTSP works) on Bosch VIP devices (Flexidome, Dinion, AutoDome, MIC, Inteox) — port 554, parameterized URL, ONVIF Profile S/T/G/M conformance. Enterprise-grade; not common in true SMB.

## What they are
Bosch Building Technologies (now Keenfinity Group, post-2024 spin-off) is a German enterprise IP camera maker (Flexidome fixed dome, Dinion box, AutoDome PTZ, MIC ruggedized, Inteox open-platform line). Sold through certified integrators into airports, banks, government, large transit, factories, hospitals. Designed around BVMS (Bosch Video Management System), but ships full RTSP + ONVIF for 3rd-party VMS.

## Market presence in SMB
Small — Bosch is enterprise-tier ($500–$2,500 per camera). Reps will see it at higher-end clients: bank branches, hospitals, museums, multi-site retail headquarters, transit-adjacent QSRs. Not at standalone smoke shops or single-location restaurants.

## Protocol support
- **RTSP:** Yes (port 554)
- **ONVIF:** Yes — Profile S (live streaming), T (advanced), G (recording), M (analytics metadata). Bosch is a long-standing ONVIF member.
- **Proprietary API:** RCP+ (Bosch's HTTP-based remote control protocol) and BVIP SDK for deeper integration.
- **Local discovery:** Yes — Bosch IP Helper / Configuration Manager utilities; ONVIF WS-Discovery.

## How to find the RTSP URL (exact path through their UI)
1. Open **Bosch Configuration Manager** (Windows tool from boschsecurity.com) or browse to camera IP → log in as `service` (default admin role).
2. **Network → Network Access** — confirm RTSP enabled, port `554`. (Tunnel mode uses port `80` via `rtsp_tunnel` path — used when 554 is blocked.)
3. **Camera → Encoder Profile** — confirm at least one H.264 profile is active (Bosch defaults H.265 on newer firmware; many analytics pipelines prefer H.264).
4. Construct the URL (Bosch doesn't display it — documented format):
   - Main: `rtsp://<user>:<pass>@<ip>:554/?inst=1`
   - Sub:  `rtsp://<user>:<pass>@<ip>:554/?inst=2`
   - Multi-channel (encoder / multi-imager): add `&line=<N>` — e.g., `rtsp://<ip>/?line=2&inst=1`
   - Force codec: `&h26x=4` (H.264) or `&h26x=5` (H.265)
   - Tunnel mode (port 80): `rtsp://<user>:<pass>@<ip>/rtsp_tunnel?inst=1`
5. **Configuration Manager → Camera → Test stream** confirms the URL works before handing to Meridian.

## Authentication
Username + password, Digest auth. Default user roles: `live`, `user`, `service` — Bosch firmware enforces password set on first boot since 6.x. Older firmware (5.x and earlier) may still ship empty passwords for `service`.

## Models tested / known to work
| Model | Firmware | Notes |
|-------|----------|-------|
| Flexidome IP starlight 8000i | 7.x+ | Full RTSP + ONVIF; default H.265 |
| Flexidome IP 5000i / 4000i (mid-tier) | 7.x+ | Same URL pattern; standard fixed dome |
| Dinion IP starlight 7000i (box) | 7.x+ | Multi-stream; `inst=1` main, `inst=2` sub |
| AutoDome IP 7000i PTZ | 7.x+ | Add `&line=1`; PTZ control via ONVIF, not RTSP |
| MIC IP 7100i / 9000i (ruggedized) | 7.x+ | Same pattern; outdoor/industrial |
| Inteox CPP14 platform (new open line) | 8.x+ | Allows 3rd-party apps on-camera; RTSP unchanged |

## Common quirks
- Bosch defaults to H.265 on most new firmware — explicitly request `&h26x=4` in the RTSP URL if the analytics pipeline is H.264-only.
- Sub-stream (`inst=2`) is not guaranteed to be enabled — confirm in Encoder Profile that profile 2 has bitrate > 0.
- Multi-imager and panoramic cameras (Flexidome panoramic 7000) expose each sensor as a separate `line=<N>` — don't assume `line=1` is the whole view.
- ONVIF events / metadata are a separate stream (`meta=1` parameter for ONVIF metadata over RTSP).
- Bosch's IPv6 stack is strict — if the merchant's LAN runs dual-stack and the RTSP URL uses a hostname, force IPv4 with the literal IP.
- Bosch IP Helper announces devices via UDP broadcast; if discovery fails on a managed switch, RTSP almost always still works once you have the IP.

## Troubleshooting (rep-facing)
- **"Stream won't open"** → 1) Confirm port 554 reachable (try tunnel mode `:80/rtsp_tunnel?inst=1` if blocked). 2) Force `&h26x=4` in case decoder lacks H.265. 3) Test in VLC against the literal IP, not a hostname.
- **"Stream drops after N minutes"** → 1) Switch to RTSP-over-TCP in the client. 2) Lower fps in Encoder Profile. 3) Check **Network → Active connections** in Configuration Manager — Bosch caps simultaneous RTSP sessions on smaller models.
- **"Black frames / no video"** → 1) Codec mismatch — force H.264 via `h26x=4`. 2) Wrong `inst` (encoder profile disabled). 3) Privacy mask region covers the field of view.
- **"Can't find the camera on the network"** → 1) Run Bosch Configuration Manager / IP Helper. 2) Check VLAN — Bosch installs often segregate camera traffic. 3) If integrator owns the system, ask for the cameras' static IPs — Bosch deployments rarely use DHCP.

## What blocks officially-supported status today
- Bosch installs typically come with an integrator owning the BVMS and the network — getting RTSP credentials may require coordinating with that integrator rather than the merchant.
- Default H.265 on new firmware requires explicit codec parameter on Meridian's side.

## Recommendation tier
OFFICIALLY SUPPORTED

**Reasoning:** Bosch ships rock-solid RTSP + ONVIF with a documented parameterized URL, and is an ONVIF Profile S/T/G/M reference implementer. The integration "just works" once we have an IP and credentials — the friction is access, not protocol. Treat as a premium-tier opportunity at hospitals, banks, and large multi-site retail.

## Sources consulted
- https://knowledge.keenfinity-group.com/video-systems/article/how-is-rtsp-usage-supported-with-bosch-vip-devices
- https://www.ipcamlive.com/bosch
- https://www.ispyconnect.com/camera/bosch
- https://camlytics.com/camera/bosch
- https://community.boschsecurity.com/t5/Security-Video/How-to-request-a-RTSP-multicast-stream-from-a-BOSCH-IP-camera/ta-p/16494
- https://www.scribd.com/document/680102104/RTSP-usage-with-Bosch-Video-IP-Devices
