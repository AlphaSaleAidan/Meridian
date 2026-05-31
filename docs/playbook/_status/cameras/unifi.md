# Ubiquiti UniFi Protect

## Status
LIVE but NEEDS BRAND-SPECIFIC URL FORMAT — `rtsps://` (TLS) on port **7441**, not plain RTSP. Must be enabled per-camera, per-quality-tier.

## What they are
Ubiquiti's prosumer/SMB camera + NVR ecosystem (Cloud Key, UNVR, Dream Machine) — self-hosted alternative to cloud cam services.

## Market presence in SMB
**Medium-Large in tech-savvy SMB.** Common in newer/modern restaurants, cafes, retail, coworking — anywhere the owner or IT person picked the system themselves. Apple-store-modern storefront? Expect UniFi.

## Protocol support
- **RTSP:** Yes — served as **RTSPS** (TLS) on port `7441` from the Protect controller
- **ONVIF:** No (Protect cameras don't expose ONVIF)
- **Proprietary cloud API:** Yes — **Official UniFi Protect API** (HTTP, released in Protect 5.3, formalized 2026). Docs at `developer.ui.com/protect-api/gettingstarted`. Supports LOCAL and REMOTE.
- **Local discovery:** Cameras auto-discovered by Protect controller only

## How to find the RTSP URL (exact path)
1. Open **UniFi Protect** web UI (or mobile app) — log in to the controller
2. **Protect → Cameras → [select camera] → Settings → Advanced → RTSP**
3. **Enable** one or more tiers: **Low**, **Medium**, **High** (each is a separate sub-stream with its own URL)
4. Copy the generated URL:
   ```
   rtsps://{controller-ip}:7441/{stream-id}?enableSrtp
   ```
   `{stream-id}` is a random token, one per tier per camera.

## Authentication
**Token-in-URL** — the random `{stream-id}` IS the auth. No username/password. Regenerating the URL in the UI is the only way to revoke.

## Models tested / known to work
| Model | Firmware | Notes |
|-------|----------|-------|
| _populate as reps test_ | _Protect 5.x_ | RTSPS confirmed working when enabled per-tier |

## Common quirks
- **`rtsps://` not `rtsp://`** — plain-RTSP-only clients will fail; ingest must accept TLS-wrapped RTSP
- **OFF by default** on every camera, every tier — owner must toggle each one
- **Stream ID changes if regenerated** — treat URLs as semi-secret credentials
- **High tier = main encode** (often H.265 on G4/G5); Low/Medium are H.264 sub-streams — prefer **Medium** for analytics
- **Audio** included by default; can be disabled per-camera

## Troubleshooting (rep-facing)
- **"Stream won't open"** → (1) confirm `rtsps://` and port `7441`, (2) verify RTSP toggle ON for that tier, (3) test on LAN with VLC first
- **"Stream drops after N minutes"** → (1) check controller CPU (Cloud Key Gen1 chokes), (2) drop to Medium, (3) check WAN upload
- **"Black frames / no video"** → (1) likely H.265 decode — switch to Medium/Low, (2) restart camera from UI, (3) regenerate stream ID
- **"Can't reach from internet"** → port-forward `7441/tcp` OR (preferred) use the official Protect API with remote tokens

## What blocks officially-supported status today
- Per-camera, per-tier manual enablement — no auto-provisioning over RTSP
- For multi-site/remote rollouts, migrate to the **Official Protect API** instead of exposing 7441

## Recommendation tier
**OFFICIALLY SUPPORTED (RTSPS local) / BEST EFFORT (remote)**

**Reasoning:** RTSPS is reliable on-LAN once enabled. For remote Meridian deployments, the official Protect HTTP API beats port-forwarding.

## Sources consulted
- [HostiFi: UniFi Protect RTSP feed guide](https://www.hostifi.com/blog/how-to-stream-a-unifi-protect-rtsp-feed-to-wordpress)
- [UI Community: Access UniFi Protect camera RTSP](https://community.ui.com/questions/Access-UniFi-Protect-camera-RTSP-stream/b1ba4c62-0764-4223-80d0-650768b0f87f)
- [Getting Started with the Official UniFi API](https://help.ui.com/hc/en-us/articles/30076656117655-Getting-Started-with-the-Official-UniFi-API)
- [Official Protect API released in 5.3](https://github.com/uilibs/uiprotect/discussions/442)
