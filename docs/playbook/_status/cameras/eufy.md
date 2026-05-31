# Eufy (Anker)

## Status
LIVE on a narrow slice of wired/indoor models (RTSP enabled per-camera in the Eufy Security app) — CLOUD-ONLY on the rest of the lineup (battery eufyCam / SoloCam E20/E40, video doorbells, most plug-in indoor newer-gen).

## What they are
Anker's prosumer smart-home camera line (eufyCam, SoloCam, Indoor Cam, Floodlight Cam, Video Doorbell, Garage-Control Cam) sold direct (eufy.com), Amazon, Costco; built around the HomeBase 2 / HomeBase 3 hub and the Eufy Security app. "Local storage, no monthly fees" is the marketing hook — RTSP is a side feature, not the product.

## Market presence in SMB
Medium — common in small storefronts, salons, smoke shops, and home-based businesses where the owner already used eufy at home. Heavier consumer skew than Reolink; rarely a primary commercial install.

## Protocol support
- **RTSP:** Yes on select wired models only (port 554) — toggleable per camera in the app. No on battery eufyCam / SoloCam E20/E40, no on video doorbells.
- **ONVIF:** No (eufy advertises RTSP, not ONVIF — no profile conformance).
- **Proprietary cloud API:** Yes (Eufy Security cloud, used by the Eufy Security app via HomeBase or direct).
- **Local discovery (UPnP/Bonjour):** Partial — HomeBase advertises on LAN; individual cameras are reached via the Hub on most product lines.

## How to find the RTSP URL (exact path through their UI)
1. Open **Eufy Security app** → tap the target camera → **gear icon (Settings)**.
2. **Advanced Settings → NAS Settings** (or **RTSP Stream** on indoor cams) → toggle **RTSP** on.
3. Set a username + password (camera-local, not your eufy account).
4. App displays the URL — expected format: `rtsp://<user>:<pass>@<camera-ip>/live0` (main) and `/live1` (sub) for indoor / SoloCam wired. URL varies by model and firmware — **always copy the one the app shows**.

If the **RTSP toggle is absent** in Advanced Settings, that model does not support RTSP — period. No firmware flash, no workaround.

## Authentication
Username + password set in-app when RTSP is enabled. Digest auth. Stored on the camera, separate from the eufy account.

## Models tested / known to work
| Model | Firmware | Notes |
|-------|----------|-------|
| Indoor Cam 2K (C24/C22) | recent | RTSP toggle in Advanced Settings |
| Indoor Cam E220 (Pan & Tilt) | recent | RTSP works; H.264 |
| SoloCam wired (S40, S230 wired variants) | recent | RTSP on wired-power models only |
| Garage-Control Cam (T8452) | recent | Has explicit "RTSP & NAS" support per eufy docs |
| Floodlight Cam 2 / 2 Pro (wired) | recent | RTSP available |
| eufyCam 2 / 2C / 3 / S3 Pro (battery) | any | **No RTSP** — battery sleep design, cloud only |
| SoloCam E20 / E40 (battery) | any | **No RTSP** |
| Video Doorbell (any gen) | any | **No RTSP** |

## Common quirks
- The same product family (e.g., SoloCam) has wired and battery SKUs with very different protocol support — check the exact model number, not the family name.
- HomeBase 3 (S380) adds local AI and BionicMind features but does **not** rebroadcast battery cameras as RTSP — battery cams still won't expose a stream.
- RTSP is H.264 only on supported models; no H.265 over RTSP even when the camera records H.265 to HomeBase.
- Enabling RTSP can disable some cloud features (motion notifications continue, but the live preview in the app may slow).
- eufy has historically pulled RTSP from product roadmaps then reinstated it — track per-model rather than per-brand.

## Troubleshooting (rep-facing)
- **"Stream won't open"** → 1) Confirm camera is on the supported list (wired only). 2) App → camera → Settings → Advanced → RTSP toggle visible? If no, RTSP unsupported on that SKU. 3) Test the exact URL the app displays in VLC on the LAN.
- **"Stream drops after N minutes"** → 1) Confirm it's a wired model, not battery. 2) Set DHCP reservation on the camera IP. 3) Disable HomeBase cloud-recording double-stream (Settings → Storage).
- **"Black frames / no video"** → 1) Force `live1` sub-stream. 2) Toggle RTSP off → on in the app. 3) Power-cycle the camera (not the HomeBase).
- **"Can't find the camera on the network"** → 1) Camera is reachable via the HomeBase, not standalone — check HomeBase IP first. 2) Some wired indoor cams expose their own IP only after RTSP is enabled. 3) Read the IP off the router DHCP table.

## What blocks officially-supported status today
- Per-model RTSP support fragmentation — reps must check the exact SKU, not the brand or family.
- No ONVIF means no auto-discovery — every camera needs manual URL entry.
- Battery and doorbell lines (the highest-selling SKUs) have no RTSP path at all.

## Recommendation tier
BEST EFFORT on wired indoor / SoloCam wired / Floodlight wired (works, but always verify per-SKU). NOT SUPPORTED on battery eufyCam, SoloCam E20/E40, and video doorbells.

**Reasoning:** RTSP works reliably on a defined wired subset, but the brand's bestsellers are battery cams that cannot stream. Treat eufy the same way you treat Reolink — wired/PoE works, battery doesn't — and confirm the SKU before promising integration.

## Sources consulted
- https://service.eufy.com/article-description/Does-eufy-Garage-Control-Cam-support-RTSP-NAS
- https://www.smartrtsp.com/cameras/eufy
- https://www.ispyconnect.com/camera/eufy
- https://www.visioforge.com/help/docs/dotnet/camera-brands/eufy/
- https://github.com/bropat/eufy-security-client/blob/master/README.md
