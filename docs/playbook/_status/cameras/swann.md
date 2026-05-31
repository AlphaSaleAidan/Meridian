# Swann

## Status
NEEDS BRAND-SPECIFIC URL FORMAT — RTSP works on most current DVR/NVR systems, but Swann uses multiple OEMs (Raysharp today, older Hikvision and Dahua), so the URL pattern depends on the model year. Wi-Fi-only and battery cameras tied to the SwannSecurity / Tracker app are cloud-only.

## What they are
Australian-founded consumer surveillance brand, owned since 2014 by Infinova Group (American-Chinese conglomerate). Sold through Costco, Walmart, Sam's Club, Bunnings, JB Hi-Fi, Amazon. Heavy big-box retail presence — the "first DVR kit" for budget-conscious SMBs and prosumers. OEM-switches mean rep cheat-sheets for "Swann" must always start with "what model?".

## Market presence in SMB
Medium — common at single-location retail, restaurants, body shops, small offices in markets where Costco/Bunnings is the default channel (US, AU, UK). Less common than Reolink/Hikvision in the integrator channel because installers don't carry it.

## Protocol support
- **RTSP:** Yes on wired DVR/NVR systems (port 554). Varies on standalone IP cameras. No on Wi-Fi-only / battery cams tied to SwannSecurity or Swann Tracker apps.
- **ONVIF:** Yes on most DVR/NVR-connected cameras (Profile S, inherited from the underlying OEM firmware). Partial on standalone.
- **Proprietary cloud API:** Yes (SwannView, SwannSecurity, Swann Tracker — different apps for different product lines).
- **Local discovery (UPnP/Bonjour):** Partial — DVRs advertise; Wi-Fi cams typically do not.

## How to find the RTSP URL (exact path through their UI)
**SwannView Plus / Swann Security app (DVR/NVR):**
1. Open app → tap the DVR → **Settings → Device Info** — note the local IP and HTTP port (often `85` on older units, `80` on newer).
2. Browser to the DVR IP, log in as `admin`.
3. **Network → RTSP** (path varies) — confirm enabled, note RTSP port (`554` standard, but some kits ship `1085` or `1025`).
4. Build URL using the OEM family pattern (try in this order):

   **Raysharp-OEM (most current 2020+ Swann DVRs/NVRs — NHD-865, NHD-885, SWNHD-887):**
   `rtsp://<user>:<pass>@<ip>:554/ch<N>/<S>`
   - `N` = camera channel (1–8 or 01–16 depending on firmware)
   - `S` = stream (`0` main, `1` sub)
   - Examples: `rtsp://admin:pass@192.168.1.10:554/ch1/0` or `rtsp://admin:pass@192.168.1.10:554/ch01/0`

   **Hikvision-OEM (pre-2020 Swann, e.g., NHD-831 = DS-2CD2732F-I rebrand):**
   `rtsp://<user>:<pass>@<ip>:554/Streaming/Channels/<N>01` (main) or `/<N>02` (sub) — see [hikvision.md](./hikvision.md).

   **Dahua-OEM (some 2014–2018 Swann hardware):**
   `rtsp://<user>:<pass>@<ip>:554/cam/realmonitor?channel=<N>&subtype=0` — see [dahua.md](./dahua.md).

5. If none work, fall back to **ONVIF Device Manager** (Windows) on the LAN — most Swann DVRs advertise their RTSP URL via ONVIF discovery even when the manual doesn't document it.

## Authentication
Username + password (Digest preferred, Basic sometimes required on older Hikvision-OEM SKUs). First-boot password set is enforced on current firmware. Older units may have `admin/12345` or `admin/admin`.

## Models tested / known to work
| Model | OEM | Notes |
|-------|-----|-------|
| NHD-831 (older) | Hikvision (DS-2CD2732F-I) | Use Hikvision URL pattern |
| NHD-865 / NHD-885 / SWNHD-887 | Raysharp | `/ch<N>/<S>` pattern |
| DVR-1580 / 4575 / 5680 series | Raysharp (current) | `/ch<N>/<S>` pattern, RTSP port may be `1085` |
| Master-series 4K DVR (current kit) | Raysharp | Same as above |
| SwannBuddy / Tracker (battery Wi-Fi doorbell, battery cam) | Swann-proprietary | **No RTSP** — cloud only |
| AllSecure600 / 4K (battery Wi-Fi) | Swann-proprietary | **No RTSP** — cloud only |

## Common quirks
- **No single Swann URL pattern.** Reps must check the model number, then look up which OEM family it falls into. Treat "Swann" as a label, not a protocol guarantee.
- Some Swann DVRs ship with non-standard ports — `1085` (HTTP), `8000` (server), `554` (RTSP) — but a few kits remap RTSP to `1025` or `1085`. Always confirm in the DVR web UI before troubleshooting.
- ONVIF discovery often succeeds even when the documented RTSP URL doesn't — try that before assuming the camera is broken.
- Swann's SwannSecurity / Tracker apps are designed to lock users into the cloud — Wi-Fi/battery SKUs sold under those apps have no LAN streaming surface.
- Audio is in-stream when enabled on the camera channel; off by default on most DVR setups.

## Troubleshooting (rep-facing)
- **"Stream won't open"** → 1) Check the DVR HTTP port (often 85, not 80) and the RTSP port (may be 1085 or 1025, not 554). 2) Try all three URL patterns above. 3) Fall back to ONVIF Device Manager on the LAN.
- **"Stream drops after N minutes"** → 1) Switch to sub-stream (`/ch<N>/1` or subtype=1). 2) Force H.264 in the DVR's encode settings. 3) Confirm DHCP reservation on the DVR.
- **"Black frames / no video"** → 1) Codec mismatch — switch to sub-stream. 2) Camera channel disabled in the DVR? 3) PoE budget exceeded on the DVR's built-in switch.
- **"Can't find the camera on the network"** → 1) The DVR usually puts cameras on its own internal switch — the cameras are not on the merchant LAN, the DVR is. Connect to the DVR's IP and pull RTSP for each channel from there. 2) ONVIF Device Manager. 3) Check the DHCP lease on the router for the DVR only.

## What blocks officially-supported status today
- Multiple OEMs across the catalog — no single URL pattern reps can memorize.
- Wi-Fi/battery cameras tied to SwannSecurity/Tracker apps have no RTSP path at all.
- Non-standard port assignments on some kits cause silent failures even when RTSP is technically working.

## Recommendation tier
BEST EFFORT on wired DVR/NVR systems (works, but rep must identify the OEM family first). NOT SUPPORTED on Wi-Fi-only / battery cameras under SwannSecurity or Swann Tracker apps.

**Reasoning:** The wired DVR line is functional but requires per-model investigation. Lower-effort to pitch a $60 Reolink PoE camera alongside the existing Swann kit on tricky installs — Swann's installed cameras can keep recording to the DVR while Meridian pulls a parallel stream from the new PoE unit.

## Sources consulted
- https://www.ispyconnect.com/camera/swann
- https://support.swann.com/hc/en-us/articles/4738459123737-How-to-access-the-DVR-or-NVR-using-hostname-on-SwannView-Plus-app
- https://forum.monoclecam.com/topic/179/swann-dvr-rstp-feeds
- https://ipcamtalk.com/threads/updated-success-cracked-swann-proprietary-camera-cant-see-it-on-the-network-swann-swnhd-865msb.30232/page-3
- https://www.flynsarmy.com/2023/07/how-to-access-swann-cameras-remotely-without-swannview/
- https://www.getscw.com/decoding/rtsp
- https://ipvm.com/reports/the-billion-dollar-chinese-manufacturer-who-bought-march-just-bought-swann
- https://us.swann.com/company/about-swann/
