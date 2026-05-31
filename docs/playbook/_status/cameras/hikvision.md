# Hikvision

## Status
LIVE (RTSP works)

## What they are
Chinese manufacturer; world's largest IP camera maker. Sold direct and through a vast OEM channel.

## Market presence in SMB
Dominant. Everywhere in retail, warehouses, multi-family. Hikvision silicon also ships as **LaView, ANNKE, older Honeywell Performance**, and dozens more — all identical over RTSP/ONVIF. SADP discovery surfaces them regardless of badge.

## Protocol support
- **RTSP:** Yes (port 554; 10554 on some firmware with auth)
- **ONVIF:** Yes (Profile S/T; ONVIF user added separately from admin)
- **Proprietary cloud:** Hik-Connect / EZVIZ (P2P, no RTSP)
- **Local discovery:** Yes — Hikvision SADP

## How to find the RTSP URL (exact path through their UI)
**Web interface (most reliable):**
1. Browse to camera/NVR IP, log in as admin
2. Configuration → Network → Advanced → Integration Protocol → enable ONVIF, add ONVIF user
3. Configuration → Network → Basic → Port → confirm RTSP port (default 554)
4. Configuration → System → Security → Authentication → set RTSP Auth to `digest/basic`
5. Build URL:
   - Main: `rtsp://{user}:{pass}@{ip}:554/Streaming/Channels/101`
   - Sub:  `rtsp://{user}:{pass}@{ip}:554/Streaming/Channels/102`
   - NVR channel N: `…/Streaming/Channels/N01` or `N02` (`401` = ch 4 main)

**iVMS-4200:** Device Management → device → Remote Configuration → Network → confirm port; build the URL yourself from IP + channel numbers.

**Hik-Connect (mobile):** P2P only — no RTSP. Use it to grab LAN IP, then go via the web path above.

## Authentication
User+pass (digest preferred; basic available). ONVIF needs its own user.



## Models tested / known to work
| Series | Notes |
|---|---|
| DS-2CD (commercial IP cams, incl. AcuSense + ColorVu) | Standard `/Streaming/Channels/101\|102` |
| DS-7xxx NVRs (4/8/16-ch) | Per-channel: `N01`/`N02` |
| OEM rebrands (LaView, ANNKE, older Honeywell Performance) | Identical URL format |

## Common quirks
- **H.265 default on newer firmware** — set sub-stream to H.264 if decoder is H.264-only
- **ColorVu** full-color 24/7 and **AcuSense** AI cameras use the same RTSP path; AcuSense events ride on ISAPI/ONVIF, not RTSP
- **Sub-stream for analytics, main for recording** — `/102` is low-bitrate (ideal for vision); `/101` is full-res for evidence

## Troubleshooting (rep-facing)
- **"Stream won't open"** → Ping IP; confirm port 554 open; toggle RTSP Auth digest/basic.
- **"Stream drops"** → Cap sub-stream at 1–2 Mbps; GOP = 1× FPS; switch sub to H.264.
- **"Black frames"** → Use `/102` if decoder rejects H.265; confirm ONVIF user; reboot.
- **"Can't find on network"** → Run SADP; check VLAN/PoE; default IP `192.0.0.64` after factory reset.

## What blocks officially-supported status today
- **NDAA Section 889** — federal agencies and federally-funded critical infrastructure can't use Hikvision or its OEM rebrands. Rare for SMB but ask if the customer touches federal contracts or critical infra.

## Recommendation tier
OFFICIALLY SUPPORTED

**Reasoning:** Universal RTSP, predictable URL scheme, and Hikvision silicon underpins much of the SMB market even when the badge differs. NDAA caveat applies only to a narrow federal slice.

## Sources consulted
- https://supportusa.hikvision.com/support/solutions/articles/17000129064-how-do-i-get-my-rtsp-stream-
- https://supportusa.hikvision.com/support/solutions/articles/17000129022-do-you-have-an-example-showing-the-format-for-getting-a-rtsp-stream-from-a-camera-
- http://enpinfo.hikvision.com/unzip/20201110210551_77443_doc/GUID-515FF2B5-5E01-4F03-8B81-4CA5BD621965.html
- https://securitycamcenter.com/hikvision-oem-list/
- https://ipvm.com/reports/hik-oems-dir
