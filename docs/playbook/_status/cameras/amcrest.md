# Amcrest

## Status
LIVE (RTSP works) — but Amcrest is a Dahua OEM rebrand on the IP camera / NVR side. URL format, ports, ONVIF behavior, and NDAA posture are identical to Dahua. See [dahua.md](./dahua.md) for the deep integration notes; this entry is the brand cheat-sheet so a rep walking into an Amcrest install knows the playbook.

## What they are
Houston-based brand (Amcrest Technologies, est. 2014) that resells Dahua hardware in the US with Amcrest-branded firmware, app (Amcrest View Pro), and support. Sold direct, Amazon, and through small integrators. Their lineup splits into two pieces with very different protocol stories:
1. **IP cameras + NVRs (IP* / NV* model numbers)** — Dahua-OEM, full RTSP.
2. **Smart Home line (ASH* / cloud-first doorbell / pan-tilt Wi-Fi)** — Amcrest-specific, mostly cloud, partial RTSP.

## Market presence in SMB
Large in the same niches as Reolink and Dahua — independent retail, smoke shops, small QSRs, contractor offices, self-installed prosumer setups. Often the Amazon default after "Reolink ran out of stock."

## Protocol support
- **RTSP:** Yes on IP cameras and NVRs (port 554). Partial on the Smart Home / Wi-Fi line — varies by SKU.
- **ONVIF:** Yes (Profile S/T) on IP cameras and NVRs — inherited from Dahua firmware.
- **Proprietary cloud API:** Yes (Amcrest Cloud / Amcrest View Pro app, both Dahua P2P under the hood).
- **Local discovery (UPnP/Bonjour):** Yes (Dahua UDP 37810; Amcrest IP Config Tool finds them).

## How to find the RTSP URL (exact path through their UI)
**Web UI (IP cameras and NVRs):**
1. Browse to camera/NVR IP → log in as `admin`.
2. **Setup → Network → Connection** — confirm RTSP port `554`.
3. Build URL manually (Amcrest does not display it — same as Dahua):
   - Main: `rtsp://<user>:<pass>@<ip>:554/cam/realmonitor?channel=1&subtype=0`
   - Sub: same with `subtype=1`
   - NVR multi-channel: `channel=<N>` for camera input N.

**Amcrest IP Config Tool (Windows):** broadcasts UDP 37810 (Dahua discovery), lists all Amcrest/Dahua devices on the LAN. Right-click → **Web Access** to confirm credentials.

**Amcrest View Pro app:** P2P only — no RTSP. Use only to confirm the device is online and grab the LAN IP.

**Smart Home line (ASH series, Doorbell, Pan-Tilt Wi-Fi):** RTSP support varies — newer firmware exposes `/cam/realmonitor?channel=1&subtype=0` on the higher-end IP4M/IP8M models, but cloud-first SKUs (ASH26, doorbells) may not expose RTSP at all. Always verify on the specific model in the Amcrest support article.

## Authentication
Username + password, Digest auth. First-boot setup forces a password (Dahua firmware behavior). Some older Amcrest units still ship `admin/admin`.

## Models tested / known to work
| Model | Firmware | Notes |
|-------|----------|-------|
| IP2M / IP4M / IP8M (PoE bullet/turret) | recent | Same `/cam/realmonitor` as Dahua |
| NV4108 / NV4116 series NVRs | recent | Multi-channel; vary `channel=N` |
| IP4M-1052W / 1053W (Wi-Fi pan-tilt) | recent | RTSP exposed on current firmware |
| Doorbell AD110 / AD410 | recent | Cloud-first; RTSP unreliable, check per firmware |
| ASH26 (Smart Home Wi-Fi) | any | Cloud-only — no RTSP |

## Common quirks
- **Identical to Dahua under the hood.** If you can integrate a Dahua camera, you can integrate Amcrest. URL, auth, port, ONVIF setup — all the same.
- H.265 default on 4K+ main streams — pull `subtype=1` for H.264 if needed.
- **NDAA Section 889:** Amcrest is Dahua-OEM, so it is *not* NDAA-compliant — same federal/critical-infra blocker as Hikvision/Dahua/Lorex.
- Amcrest tech support is more responsive than Dahua's US support — useful for tricky merchant calls.
- Smart Home line uses a different firmware tree — don't assume RTSP works on a doorbell just because it works on an IP4M camera.

## Troubleshooting (rep-facing)
- **"Stream won't open"** → Treat as Dahua. 1) Confirm RTSP enabled on Network → Connection (port 554). 2) Verify URL pattern `/cam/realmonitor?channel=1&subtype=0` in VLC. 3) Sub-stream for H.264 fallback.
- **"Stream drops after N minutes"** → 1) Switch to sub-stream. 2) Force H.264. 3) Check PoE switch budget on multi-camera installs.
- **"Black frames / no video"** → 1) Codec mismatch (try sub-stream). 2) Disable audio if device fights with the decoder. 3) Privacy mask?
- **"Can't find the camera on the network"** → 1) Amcrest IP Config Tool (UDP 37810). 2) Check DHCP table on the router. 3) Factory-reset and re-add via Amcrest View Pro.

## What blocks officially-supported status today
None on the IP camera / NVR line — it's already covered by the Dahua integration. Smart Home Wi-Fi line is per-SKU and should be flagged as BEST EFFORT.

## Recommendation tier
OFFICIALLY SUPPORTED (IP cameras + NVRs — same path as Dahua). BEST EFFORT on the Smart Home Wi-Fi and doorbell line (verify per SKU). Treat the whole brand as Dahua for federal/NDAA qualification.

**Reasoning:** Amcrest is the friendliest US-facing channel for Dahua hardware. One integration covers Dahua + Amcrest + EmpireTech + older Lorex, and rep training transfers 1:1.

## Sources consulted
- https://support.amcrest.com/hc/en-us/articles/360052688931-Accessing-Amcrest-Products-Using-RTSP
- https://support.amcrest.com/hc/en-us/articles/360001211792-RTSP-Stream-URLs-for-NVRs-NVR
- https://support.amcrest.com/hc/en-us/articles/360058619531-Accessing-Amcrest-Smart-Home-Products-Using-RTSP
- https://support.amcrest.com/hc/en-us/articles/13512258834445-Accessing-Amcrest-Products-Using-RTSP-IP4M-1052W-AI
- https://www.visioforge.com/help/docs/dotnet/camera-brands/amcrest/
- https://securitycamcenter.com/rtsp-url-address-format-dahua/
- https://ipvm.com/reports/dahua-oem
