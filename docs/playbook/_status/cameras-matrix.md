# Camera Matrix — All 8 Brands

Single-page scan of every camera vendor playbook entry. Sorted by recommendation tier (OFFICIALLY SUPPORTED → BEST EFFORT → NOT SUPPORTED).

---

| Vendor | RTSP support | Auth | Status | Recommendation | Quirk to know |
|--------|--------------|------|--------|----------------|---------------|
| [axis.md](./cameras/axis.md) | Yes (port 554) | Digest (Basic disabled by default on newer FW) | LIVE | OFFICIALLY SUPPORTED | URL has no copy button — construct as `rtsp://{user}:{pass}@{ip}:554/axis-media/media.amp?videocodec=h264`. NDAA/TAA compliant — unlocks federal/critical-infra deals no other brand can serve. |
| [hikvision.md](./cameras/hikvision.md) | Yes (port 554; some 10554) | User+pass (digest preferred); ONVIF needs separate user | LIVE | OFFICIALLY SUPPORTED | Path `/Streaming/Channels/101` (main) or `/102` (sub) — use sub for analytics. Same URL works on OEM rebrands (LaView, ANNKE, older Honeywell Performance). NDAA Section 889 blocks federal customers. |
| [dahua.md](./cameras/dahua.md) | Yes (port 554; HF-series 1554) | Digest; no factory default since 2017 FW | LIVE | OFFICIALLY SUPPORTED | Path `/cam/realmonitor?channel=1&subtype=0` (main) or `subtype=1` (sub). One URL pattern covers Dahua + Amcrest + EmpireTech + older Lorex. NDAA blocks federal. |
| [unifi.md](./cameras/unifi.md) | RTSPS only (TLS, port **7441**) | Token-in-URL (random stream-id IS the auth) | LIVE (BRAND-SPECIFIC URL FORMAT) | OFFICIALLY SUPPORTED (LAN) / BEST EFFORT (remote) | `rtsps://` not `rtsp://`. Must be enabled per-camera, per-tier (Low/Medium/High) — owner toggles each manually. Use Medium for analytics. For remote, use official Protect HTTP API instead of port-forwarding 7441. |
| [reolink.md](./cameras/reolink.md) | Yes on PoE / wired Wi-Fi (port 554) — **No on standalone battery cams** | User+pass (digest) | LIVE (PoE) / CLOUD-ONLY (battery) | OFFICIALLY SUPPORTED (PoE/wired) / NOT SUPPORTED (Argus battery without Home Hub) | Current path: `Preview_01_main` / `Preview_01_sub`; legacy `h264Preview_01_main` still works. H.265 default on 8MP+ main — pull sub for H.264. |
| [wyze.md](./cameras/wyze.md) | Only after manual RTSP firmware flash; only on Cam v2/v3/Pan v2/Pan v3 | User+pass set at flash time | NEEDS BRAND-SPECIFIC URL FORMAT | NOT SUPPORTED | Stock firmware has NO RTSP. Flash procedure is a non-starter for most merchants. Cam v4, OG, v3 Pro, Floodlight, and Battery Cam have no RTSP option at all. Recommend Reolink/Amcrest replacement. |
| [nest.md](./cameras/nest.md) | No local RTSP — only via Google SDM API, only legacy devices, 5-min sessions | OAuth 2.0 + Device Access ($5 fee + Google Cloud project) | CLOUD-ONLY | NOT SUPPORTED | All current-gen Nest Cams are WebRTC-only. SDM RTSP is single-client, 5-min sessions requiring constant `ExtendRtspStream` calls. Steer every Nest merchant to a $60 PoE camera. |
| [arlo.md](./cameras/arlo.md) | No (current models) | N/A for streaming — Arlo cloud account only | CLOUD-ONLY | NOT SUPPORTED | No RTSP, no ONVIF, no local API. Even local microSD on Smart Hub (VMB5000) is viewable only via the Arlo app. Unofficial Scrypted reverse-engineering breaks on firmware updates. |

---

## Rep heuristic (field cheat-sheet)

1. **If it's PoE/wired and the badge is Axis, Hikvision, Dahua (or its OEMs — Amcrest, EmpireTech, LaView, ANNKE, older Lorex/Honeywell), UniFi, or Reolink** → you can integrate. Get on the LAN, log into the camera/controller, enable RTSP, and grab the URL using the brand pattern in the matrix above. UniFi is the exception — it's `rtsps://` on port 7441, not plain RTSP.

2. **If it's Wyze, Nest, Arlo, or any standalone battery Reolink (Argus without Home Hub)** → it's a hard no. Don't promise an integration. Pitch a $60 Reolink RLC-510A or Hikvision DS-2CD2043G2-I PoE camera alongside the consumer gear they already own — they keep the mobile app alerts, we get the analytics stream.

3. **If the customer is federal, federally-funded, or critical infrastructure** → only Axis works (NDAA Section 889 blocks Hikvision and Dahua, including their OEM rebrands). For everyone else, NDAA is a non-issue — confirm during qualification only if they mention federal contracts.
