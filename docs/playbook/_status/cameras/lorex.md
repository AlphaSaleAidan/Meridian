# Lorex (Skywatch, post-Dahua)

## Status
LIVE on N-series wired NVR systems and most wired/PoE IP cameras (still using the Dahua-format RTSP URL — Skywatch kept the firmware stack). CLOUD-ONLY on the W-series Wi-Fi cameras (W282 / W462 / W881AAD) when not paired with a Lorex NVR. NOT SUPPORTED on battery / Smart Hub-only models.

> Legacy Dahua-OEM Lorex gear (anything before the 2023 Skywatch acquisition, or sold under Dahua firmware) is already covered in [dahua.md](./dahua.md) — same `cam/realmonitor` URL pattern. This entry covers the **post-divestment** lineup specifically.

## What they are
Lorex was acquired by Dahua in 2018, then sold to Taiwan-based **Skywatch** in Feb 2023 for $72M after the FCC ban on Dahua components. Skywatch kept the Lorex brand and continues to ship Dahua-derived firmware on existing SKUs while gradually moving to Vivotek-sourced NDAA-compliant hardware for new lines. Sold direct (lorex.com), Costco, Amazon, Home Depot.

## Market presence in SMB
Large — heavy presence in independent retail, small offices, restaurants, body shops, self-storage. Especially common where the merchant bought a Costco kit. Often the camera a rep walks into without knowing whether they're looking at old Dahua-OEM gear or new Skywatch-era gear.

## Protocol support
- **RTSP:** Yes on N-series NVRs and wired/PoE IP cameras (port 554). No on standalone W-series Wi-Fi cameras connected only to the cloud. No on battery cameras paired only with the Smart Hub.
- **ONVIF:** Yes on wired/NVR-coupled cameras (Profile S inherited from Dahua firmware). Not on cloud-only Wi-Fi.
- **Proprietary cloud API:** Yes (Lorex Home / Lorex Cloud).
- **Local discovery (UPnP/Bonjour):** Yes (Dahua-style UDP 37810 still works on N-series NVRs).

## How to find the RTSP URL (exact path through their UI)
**N-series NVR (web UI):**
1. Browse to NVR IP → log in as **admin**.
2. **Setup → Network → Port** — confirm RTSP port `554` enabled.
3. **Setup → Network → Connection** — copy the local IP.
4. Build URL (NVR doesn't display it):
   - Main: `rtsp://<user>:<pass>@<nvr-ip>:554/cam/realmonitor?channel=<N>&subtype=0`
   - Sub: same with `subtype=1`
   - `channel` = camera input number on the NVR (1–8 / 1–16).

**Standalone wired IP camera (web UI):**
- Same `/cam/realmonitor?channel=1&subtype=0` pattern. Camera always uses `channel=1`.

**Lorex Home app (mobile):** P2P only — does **not** display the RTSP URL. Use it to confirm the NVR/camera is online and grab the LAN IP under **Device Info → Network**.

**W-series Wi-Fi cameras (W282CAD, W462AQ, W881AAD):**
- If paired only with the Lorex Home app / cloud: **no RTSP**. The W881AAD is explicitly cloud-enabled and does not expose a local stream.
- If paired with a Lorex Fusion NVR (W-series can be ingested as a Wi-Fi channel on Fusion NVRs): the RTSP URL is served by the NVR using the same `/cam/realmonitor?channel=N&subtype=0` pattern.

## Authentication
Username + password, Digest auth. First-boot setup forces a password (no `admin/admin` default on post-2017 firmware).

## Models tested / known to work
| Model | Firmware | Notes |
|-------|----------|-------|
| N864 series (Fusion 4K 16ch NVR) | recent | `/cam/realmonitor` works; channel = input N |
| N881 / N882 series (4K wired NVR) | recent | Same pattern |
| LNB-series (wired bullet/turret IP cams) | recent | Standalone; `channel=1` |
| W282CAD (Wi-Fi 1080p) | recent | RTSP only via Fusion NVR; cloud-only standalone |
| W462AQ (Wi-Fi 2K Pan/Tilt) | recent | Same as W282 — needs NVR pairing for RTSP |
| W881AAD (Wi-Fi 6, 4K Spotlight) | recent | Cloud-only standalone; check Fusion NVR pairing |
| Smart Hub + battery cams | any | **No RTSP** — Lorex Home app only |

## Common quirks
- Skywatch-era firmware still uses Dahua's UDP discovery (37810) and Dahua's URL format — when in doubt, treat as Dahua.
- **NDAA / FCC ban:** Lorex (including Skywatch-era) is **not** NDAA-compliant — the components are still Dahua-sourced. Costco continued selling Lorex post-ban, which drew Congressional scrutiny. Same federal/critical-infra blocker as Hikvision/Dahua.
- H.265 default on 4K W-series and recent N-series — pull `subtype=1` (sub-stream) for H.264 if the analytics pipeline chokes.
- Some Fusion NVRs ship with RTSP disabled by default — must be toggled on under Network → Port.

## Troubleshooting (rep-facing)
- **"Stream won't open"** → 1) Confirm on N-series NVR (not Smart Hub). 2) NVR web UI → Network → Port → RTSP enabled on 554. 3) Test sub-stream URL (`subtype=1`) in VLC on the LAN.
- **"Stream drops after N minutes"** → 1) Switch to sub-stream. 2) Force H.264 in encode settings. 3) Check PoE switch budget if multiple cameras on one switch.
- **"Black frames / no video"** → 1) Codec mismatch — try sub-stream (H.264). 2) Privacy mask enabled on that channel? 3) Reboot NVR after firmware update.
- **"Can't find the camera on the network"** → 1) Try Dahua Config Tool (UDP 37810 still works on Skywatch firmware). 2) Check DHCP lease on the NVR, not on individual cameras (PoE cams sit on the NVR's internal switch). 3) For W-series Wi-Fi: confirm 2.4 GHz SSID and same subnet.

## What blocks officially-supported status today
- W-series cloud-only Wi-Fi cameras (standalone) cannot stream — flag at qualification.
- Mixed lineup: pre-2023 = Dahua firmware, post-2023 = Skywatch shipping more Vivotek hardware — rep can't always tell which they're looking at without checking the model number against lorex.com.

## Recommendation tier
OFFICIALLY SUPPORTED for N-series NVR + wired/PoE IP cameras (same as Dahua — one integration covers it). NOT SUPPORTED for W-series standalone Wi-Fi (W282/W462/W881AAD without a Fusion NVR) and Smart Hub-tethered battery cameras.

**Reasoning:** Lorex's wired/NVR lineup is functionally Dahua and works identically. The Wi-Fi/battery consumer line is built for the Lorex Home cloud app and does not expose RTSP standalone.

## Sources consulted
- https://www.dahuasecurity.com/newsEvents/pressRelease/7717
- https://www.securityworldmarket.com/int/News/Business-News/dahua-to-sell-lorex-to-skywatch-for-usd-72-million
- https://www.lorex.com/blogs/help/ip-cameras-using-real-time-streaming-protocol-rtsp-with-your-dvr-nvr
- https://www.ispyconnect.com/camera/lorex
- https://www.lorex.com/blogs/products/w881aad-series
- https://help.lorex.com/support/solutions/articles/72000640976-lorex-fusion-frequently-asked-questions
- https://techcrunch.com/2023/11/01/lawmakers-costco-lorex-dahua-entity-list/
- https://ipcamtalk.com/threads/lorex-rtsp-url-help.50284/
