# Axis Communications

## Status
LIVE (RTSP works) — plus VAPIX HTTP API and reference-grade ONVIF.

## What they are
Swedish enterprise IP-camera maker (HQ Lund). Sold through certified integrators into banks, large retail, transit, government, critical infra.

## Market presence in SMB
Small. Axis is premium — reps will see it at higher-budget customers: bank branches, multi-site retail, hospitals, schools, anything federal or critical-infra (NDAA Section 889 compliant; CAGE 3DJU8 for TAA/GSA).

## Protocol support
- **RTSP:** Yes (port 554)
- **ONVIF:** Yes — Profile S/G/T/M; Axis co-founded ONVIF
- **Proprietary API:** VAPIX (HTTP/CGI), open and documented at developer.axis.com
- **Local discovery:** Bonjour + SSDP; AXIS IP Utility / Device Manager

## How to find the RTSP URL (exact path through their UI)
1. Browse to camera IP → log in (default `root`, or installer-set admin on OS 11+).
2. **Settings → System → Plain config → Network → RTSP** — confirm enabled on 554.
3. **Settings → Stream → Stream profiles** — note or create one pinned to H.264.
4. Construct the URL (Axis has no copy button — documented format):
   `rtsp://{user}:{pass}@{ip}:554/axis-media/media.amp?videocodec=h264`
   - Multi-sensor: `&camera=1` (or 2/3/4).
   - Named profile: `?streamprofile=Meridian` instead of codec params.
   - Optional: `resolution=1920x1080`, `fps=15`, `compression=30`.
5. AXIS Camera Station / Companion does not expose the RTSP URL — use the camera web UI.

## Authentication
Username + password over Digest auth (Basic supported but disabled by default on newer firmware).

## Models tested / known to work
| Model | Firmware | Notes |
|-------|----------|-------|
| M-line (M3216-LVE) | OS 11.x | Compact entry tier; full RTSP + VAPIX |
| P-line (P3265-LVE) | OS 11.x | Premium fixed dome; most common in retail/bank branches |
| Q-line (Q6135-LE PTZ) | OS 11.x | High-end PTZ/specialty; full feature set |
| F-line (F44 + F1015) | OS 11.x | Modular — main unit owns RTSP; sensors via `?camera=N` |

## Common quirks
- H.265 only on ARTPEC-7+ SoCs — default to `videocodec=h264` until confirmed.
- Audio is a separate sub-stream; enable under **Audio → Device settings**.
- MJPEG is HTTP-only (`/axis-cgi/mjpg/video.cgi`), not in RTSP.
- VAPIX fallback when RTSP egress blocked: snapshots `/axis-cgi/jpg/image.cgi`, PTZ `/axis-cgi/com/ptz.cgi`, metadata via event subscription.

## Troubleshooting (rep-facing)
- **Stream won't open** → confirm 554 reachable; try `?streamprofile=quality`; test in VLC.
- **Drops after N min** → check **System → Events → Active connections**; lower fps; switch to RTSP-over-TCP.
- **Black frames** → force `videocodec=h264`; verify profile isn't `storage`; reboot.
- **Can't find camera** → run AXIS IP Utility; check VLAN/DHCP; ask integrator (may be on VMS-only VLAN).

## What blocks officially-supported status today
None. Validate one M/P/Q model end-to-end against Meridian's pipeline to formally certify.

## Recommendation tier
OFFICIALLY SUPPORTED

**Reasoning:** Axis co-founded ONVIF, ships open APIs, and the RTSP path is identical across the modern lineup. NDAA + TAA compliance unlocks federal/critical-infra customers no other major brand can serve cleanly.

## Sources consulted
- https://developer.axis.com/vapix/network-video/rtsp-adjustable-live-stream/
- https://developer.axis.com/vapix/network-video/video-streaming/
- https://www.visioforge.com/help/docs/dotnet/camera-brands/axis/
- https://www.axis.com/en-us/solutions/government/compliance
- https://www.axis.com/vapix-library/subjects/t10175981/section/t10051110/display
