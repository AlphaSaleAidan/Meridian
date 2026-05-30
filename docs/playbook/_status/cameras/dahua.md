# Dahua

## Status
LIVE (RTSP supported)

## What they are
Chinese surveillance maker; #2 globally after Hikvision. Sells direct plus through OEMs: Amcrest, EmpireTech, older Lorex, parts of Honeywell.

## Market presence in SMB
Large. Common at independent integrators, SMB retrofits, prosumer installs.

## Protocol support
- **RTSP:** Yes (port 554; some HF-series use 1554)
- **ONVIF:** Yes (Profile S/T/G; enable ONVIF user on newer FW)
- **Proprietary cloud:** Yes (DMSS / P2P)
- **Local discovery:** Yes (Dahua proprietary UDP 37810 + UPnP)

## How to find the RTSP URL

**Web interface:**
1. Browse to device IP, log in as `admin`.
2. **Setup → Network → Port** — confirm RTSP port `554`; enable if off.
3. Build URL manually (Dahua doesn't display it):
   - Main: `rtsp://{user}:{pass}@{ip}:554/cam/realmonitor?channel=1&subtype=0`
   - Sub:  `rtsp://{user}:{pass}@{ip}:554/cam/realmonitor?channel=1&subtype=1`

**Dahua Config Tool (Windows, fastest for multi-camera sites):**
1. Download from dahuasecurity.com, run on same LAN.
2. **Search Setting** broadcasts UDP 37810, lists all Dahua/OEM devices.
3. Right-click → **Web Access** to confirm creds, then build URL above.

**DMSS app:** P2P only — no RTSP. Use it to confirm device online and grab local IP under **Device Details → Network Info**.

### Path parameters
- `channel=N` — NVRs use camera channel (1–16/32); standalone IP cams always `channel=1`.
- `subtype=0` main; `subtype=1` sub (preferred for analytics at scale).

## Authentication
Username + password, Digest auth. No factory default since 2017 firmware — first boot forces password set. Older units may still ship `admin/admin`.

## Models tested / known to work
| Model | Firmware | Notes |
|-------|----------|-------|
| IPC-HFW / IPC-HDW (Lite/Pro/Ultra) | 2.8x+ | Standalone; `channel=1` |
| NVR4xxx / NVR5xxx | 4.x | Multi-channel; vary `channel=N` |
| Amcrest IP2M/IP4M/IP8M | Amcrest-branded Dahua FW | Same URL format |
| EmpireTech IPC-T54 / Color4K-T | Stock Dahua FW | No rebrand |

## Common quirks
- H.265 default on newer firmware — switch to H.264 under **Encode → Video** if analytics chokes.
- Sub-stream disabled on some HFW1xxx Lite units; enable under **Encode → Video → Sub Stream**.
- HF-series uses `1554` — try it before assuming auth failure.

## Troubleshooting (rep-facing)
- **"Stream won't open"** → confirm 554 (try 1554) → confirm RTSP enabled on Network → Port → re-test in VLC.
- **"Stream drops"** → switch to sub-stream → set H.264 → check PoE budget.
- **"Black frames"** → codec mismatch (try H.264) → try sub-stream → confirm no privacy mask.
- **"Can't find on network"** → run Config Tool (UDP 37810) → check DHCP lease → factory reset.

## What blocks officially-supported status today
None for RTSP. **NDAA Section 889**: federal agencies and federal contractors cannot use Dahua (direct or OEM). Same posture as Hikvision — fine for SMB/retail/residential; not for fed or critical infrastructure.

## Recommendation tier
OFFICIALLY SUPPORTED

**Reasoning:** One URL pattern covers Dahua, Amcrest, EmpireTech, older Lorex — huge slice of SMB installed base from a single integration.

## Sources consulted
- https://www.videoexpertsgroup.com/glossary/dahua-rtsp
- https://securitycamcenter.com/rtsp-url-address-format-dahua/
- https://dahuatech.zendesk.com/hc/en-gb/articles/16320900884754-How-to-add-IP-cameras-to-NVR-via-RTSP
- https://ipvm.com/reports/dahua-oem
- https://ipcamtalk.com/threads/dahua-hikvision-and-other-non-ndaa-brands-are-no-longer-sold-in-the-usa.84997/
