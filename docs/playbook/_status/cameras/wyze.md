# Wyze

## Status
NEEDS BRAND-SPECIFIC URL FORMAT — only works after manual RTSP firmware flash, only on supported models. RTSP is a perpetual beta that Wyze has paused, un-paused, and partially deprecated since 2019.

## What they are
Ultra-low-cost consumer security cameras (~$25–$40) sold direct-to-consumer and on Amazon; cloud-first product, RTSP treated as a hobbyist side-channel.

## Market presence in SMB
Small-to-Medium — common in food trucks, small smoke shops, single-operator retail, and budget-constrained SMBs who bought consumer gear before standing up real ops.

## Protocol support
- **RTSP:** Yes, but only on a separate "RTSP firmware" build that must be flashed manually. Default port 554 (unsecured), port 322 (RTSPS).
- **ONVIF:** No.
- **Proprietary cloud API:** Yes — Wyze app / Cam Plus cloud (not RTSP).
- **Local discovery (UPnP/Bonjour):** No.

## How to find the RTSP URL (exact path through their UI)
1. Flash the RTSP firmware first (see procedure below). The stock firmware does not expose RTSP at all.
2. Open the Wyze app → select the camera → **Settings → Advanced Settings → RTSP**.
3. Toggle RTSP **On**, set a username and password (4–10 chars, alphanumeric only).
4. Tap **Generate URL**. Expected format:
   - `rtsp://[user]:[pass]@[camera-ip]:554/live`
   - Secured variant: `rtsps://[user]:[pass]@[camera-ip]:322/live`

## Authentication
Username + password set in-app at firmware-flash time. Stored on-device, not federated.

## Models tested / known to work
| Model | Firmware | Notes |
|-------|----------|-------|
| Cam v2 | 4.9.8.1002 (RTSP) | Works; product line deprecated by Wyze |
| Cam v3 | 4.36.16.5055 (beta) | Works; beta — Wyze has pulled/restored downloads multiple times |
| Cam Pan v2 | 4.49.x (RTSP) | Works |
| Cam Pan v3 | 4.55.16.5055 (beta) | Works (same beta drop as v3) |
| Cam v4 | — | Uncertain; no official RTSP firmware as of writing |
| Cam OG / OG Telephoto | — | No RTSP firmware available |
| Cam v3 Pro / Floodlight Pro / Battery Cam | — | No RTSP firmware available |

## Common quirks
- H.264 only on RTSP firmware (no H.265).
- Cam Plus AI features, person detection, and event clips become unstable or inaccessible once flashed.
- Running RTSP + Cam Plus live stream simultaneously causes lag.
- Beta firmware receives security updates only — no new features ever.
- Wyze has historically pulled the firmware download links without warning.

## Troubleshooting (rep-facing)
- **"Stream won't open"** → Confirm camera is on RTSP firmware (Settings → Device Info shows `..._rtsp` build). If stock firmware, RTSP does not exist — must flash.
- **"Stream drops after N minutes"** → Disable Cam Plus live view in the app; the two streams fight.
- **"Black frames / no video"** → Power-cycle and reconnect; RTSP firmware is unstable on weak Wi-Fi.
- **"Can't find the camera on the network"** → Wyze does not advertise via ONVIF/UPnP; rep must read the IP from the router DHCP table.

## Firmware flash procedure (deal-breaker for non-technical merchants)
1. Download model-specific RTSP firmware from Wyze's S3 (links change; verify current URL).
2. Rename file to `demo_wcv3.bin` (or model equivalent) on a **FAT32**-formatted microSD card ≤32 GB, in root.
3. Unplug camera, insert SD, hold **SETUP** button while plugging in USB power until LED turns purple.
4. Wait 3–5 minutes for flash to complete.
5. Reconfigure camera in Wyze app, then enable RTSP under Advanced Settings.

## What blocks officially-supported status today
- Requires manual firmware flash — non-starter for most SMB merchants.
- RTSP firmware is officially beta; Wyze has not committed to maintaining it and has previously removed downloads.
- No support on v4, OG, v3 Pro, Floodlight, or Battery Cam lines (the models Wyze is actively selling).

## Recommendation tier
NOT SUPPORTED

**Reasoning:** The flash procedure is a support nightmare for non-technical merchants, and even when it works the firmware is a frozen beta on aging hardware. If a merchant insists, walk them through the procedure above and flag heavy hand-holding; otherwise recommend they replace with a Reolink or Amcrest unit that ships with RTSP enabled by default.

## Sources consulted
- [Wyze Cam RTSP — official support article](https://support.wyze.com/hc/en-us/articles/360026245231-Wyze-Cam-RTSP)
- [Does Wyze Cam v3 support RTSP? — Wyze support](https://support.wyze.com/hc/en-us/articles/360051619871-Does-Wyze-Cam-v3-support-RTSP)
- [Wyze RTSP Testing Instructions (S3 beta page)](https://wyze-beta.s3.us-west-2.amazonaws.com/rtsp.html)
- [RTSP BETA RELEASE FOR v3 and Pan v3 — Wyze Forum](https://forums.wyze.com/t/rtsp-beta-release-for-v3-and-pan-v3/338245)
- [Installing RTSP Firmware on Wyze V3 Camera — gigasecurehome.com](https://gigasecurehome.com/wyze-v3-rtsp-firmware/)
