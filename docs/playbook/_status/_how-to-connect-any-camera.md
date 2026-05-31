# How to Connect Any Camera

Rep-facing field guide for finding the RTSP URL on a camera you've never seen before. Walk this in order — most cameras resolve at stage 1 or 2.

Use this in conjunction with [cameras-matrix.md](./cameras-matrix.md), which contains the per-brand URL patterns referenced below.

---

## The 4-stage diagnostic flow

Every camera integration boils down to four yes/no questions, in this exact order. Don't skip ahead.

### Stage 1 — Is RTSP even present?

If the answer is no, stop. No URL trick will conjure a stream out of a cloud-only camera. Common no-go brands: Ring, Arlo, Nest, eufy battery / doorbells, Wyze (without firmware flash), Lorex W-series standalone, Reolink Argus standalone. See the NOT SUPPORTED section of [cameras-matrix.md](./cameras-matrix.md) for the full list.

How to tell quickly:
1. **Brand recognition.** If the matrix says cloud-only, you're done — pitch a $60 PoE replacement.
2. **App inspection.** Open the merchant's vendor app and look for an "RTSP," "NAS," or "Advanced Network" toggle. If there isn't one anywhere in Settings, the camera doesn't speak RTSP.
3. **Port probe.** From a laptop on the LAN: `nmap -p 554 <camera-ip>`. Port closed = no RTSP service. Port open = continue to stage 2.

### Stage 2 — What's the URL format?

Three paths to get the URL, in order of speed:

1. **ONVIF auto-discovery** (universal first attempt). Most ONVIF-conformant cameras advertise their RTSP URL in their GetStreamUri response. Use ONVIF Device Manager (Windows) or the `onvif-cli` Python tool — point it at the LAN subnet, let it discover, then right-click each device → "Live Video" reveals the underlying RTSP URL. This catches roughly 70% of unknown cameras at most SMB sites in under 60 seconds.
2. **Brand pattern lookup.** Read the camera label / sticker for brand and model, then look up the URL in [cameras-matrix.md](./cameras-matrix.md). Examples:
   - Hikvision (or LaView / ANNKE / older Honeywell): `rtsp://{user}:{pass}@{ip}:554/Streaming/Channels/101`
   - Dahua (or Amcrest / EmpireTech / Lorex N-series): `rtsp://{user}:{pass}@{ip}:554/cam/realmonitor?channel=1&subtype=0`
   - Axis: `rtsp://{user}:{pass}@{ip}:554/axis-media/media.amp?videocodec=h264`
   - Reolink PoE: `rtsp://{user}:{pass}@{ip}:554/Preview_01_main`
   - UniFi: `rtsps://{ip}:7441/<stream-id>` (token-in-URL, RTSPS only)
   - Bosch: `rtsp://{user}:{pass}@{ip}:554/?inst=1&h26x=4`
   - Avigilon: `rtsp://{user}:{pass}@{ip}:554/defaultPrimary?streamType=u`
   - Verkada: per-camera URL generated in Command portal
3. **Vendor UI walkthrough.** See the next section.

### Stage 3 — What auth does it want?

Once you have a URL pattern, the auth is almost always one of three things:
- **Digest** (default on almost everything modern — Hikvision, Dahua, Axis, Bosch, Avigilon, Reolink, eufy).
- **Basic** (Hikvision when enabled in the security panel, some Wyze RTSP firmware, some older Swann Hikvision-OEM units).
- **Token-in-URL** (UniFi Protect — the random stream-id IS the auth, no user/pass).

If a brand-correct URL fails with 401, swap Digest ↔ Basic before assuming the password is wrong. See the **Common auth quirks** section below for the gotchas.

### Stage 4 — Does the network actually reach it?

This is where 30% of "RTSP doesn't work" calls actually live. Three checks:
1. **Same subnet?** A camera on `10.0.0.0/24` and a Meridian collector on `192.168.1.0/24` need a route. PoE cameras hanging off an NVR's built-in switch are particularly easy to miss — the cameras live on the NVR's internal subnet, not the merchant LAN.
2. **Firewall / VLAN?** Many enterprise sites segregate camera VLANs. Ask: "where do your IT folks let camera traffic go?"
3. **Port reachable from where Meridian will pull?** `nc -zv <camera-ip> 554` (or 7441 for UniFi, 4100 for Verkada Local Streaming) from a host on the same subnet Meridian will run on.

---

## Vendor UI walkthrough — finding the URL in 6 common apps

When ONVIF discovery fails or the merchant doesn't know the brand, walk these in order of likelihood.

### Hik-Connect / iVMS-4200 / Hikvision web UI

- **Hik-Connect mobile app** does NOT display the RTSP URL — it's a P2P client only.
- Use the camera **web UI** (browse to the camera IP, log in as `admin`). **Configuration → Network → Advanced Settings → Integration Protocol** confirms ONVIF/RTSP enabled.
- The RTSP URL is not displayed — construct it: `rtsp://{user}:{pass}@{ip}:554/Streaming/Channels/101` (main) / `102` (sub). For multi-channel NVRs: `/Streaming/Channels/N01` where N = channel number.
- ONVIF needs its own user — created under **Configuration → Network → Advanced → Integration Protocol → ONVIF**.

### Dahua Smart PSS / DMSS / web UI

- **DMSS mobile app** is P2P-only — no RTSP URL displayed. Use it to confirm device online and grab the LAN IP under Device Details → Network Info.
- **Smart PSS (Windows)** broadcasts UDP 37810, lists every Dahua/Amcrest/Lorex N-series device on the LAN. Right-click → Web Access opens the camera in a browser.
- In the **camera web UI**: **Setup → Network → Port** confirms RTSP enabled on 554 (or 1554 on HF-series).
- Construct the URL: `rtsp://{user}:{pass}@{ip}:554/cam/realmonitor?channel=1&subtype=0` (main) / `subtype=1` (sub). For NVRs, vary `channel=N`.
- Same flow for Amcrest IP Config Tool and the Amcrest View Pro app.

### Reolink app / Reolink Client

- **Reolink mobile app:** Tap camera → gear → **Device Settings → Advanced → Network Settings → Server Settings** — confirms RTSP enabled. URL not displayed in the app.
- **Reolink Client (Windows/Mac)** is the fastest path: right-click camera → **Device Settings → Network → Advanced → Server Settings**, then build the URL.
- Current format: `rtsp://{user}:{pass}@{ip}:554/Preview_01_main` (sub: `Preview_01_sub`). Legacy `h264Preview_01_main` still works on most firmware.
- If you're looking at an Argus (battery) without a Home Hub, RTSP is not available — stop here.

### UniFi Protect (web UI / mobile app)

- UniFi is the brand-specific one. **RTSPS only, port 7441.**
- **UniFi Protect web UI → [camera] → Settings → Advanced** — enable RTSPS per quality tier (Low / Medium / High). Use **Medium** for analytics.
- The URL is generated and displayed in the UI: `rtsps://{controller-ip}:7441/<random-stream-id>` — the random stream-id is the auth (no user/pass).
- Each enabled tier gets its own stream-id. If RTSPS is disabled, no URL exists.
- For remote ingestion, use the official Protect HTTP API instead of port-forwarding 7441.

### Axis Companion / AXIS Device Manager / web UI

- **AXIS Companion** does NOT display the RTSP URL — it's an end-user viewer.
- Use the **camera web UI** (browse to camera IP, log in as `root` or installer-set admin on OS 11+).
- **Settings → System → Plain config → Network → RTSP** confirms enabled on 554.
- **Settings → Stream → Stream profiles** — pick or create one (e.g., name it `Meridian`).
- Construct: `rtsp://{user}:{pass}@{ip}:554/axis-media/media.amp?videocodec=h264` (or `?streamprofile=Meridian`).
- AXIS Device Manager (installer tool) shows all devices on the LAN via Bonjour/SSDP.

### ONVIF Device Manager (Windows) — the universal fallback

- Free, open-source — install on a Windows laptop on the merchant's LAN.
- Auto-discovers every ONVIF-conformant device on the subnet within 10 seconds.
- Click a device, enter the camera credentials, and the **Live Video** tab reveals the underlying RTSP URL.
- Works on Hikvision, Dahua, Axis, Bosch, Reolink wired, eufy wired (sometimes), most cheap white-label cameras.
- Does NOT work on UniFi (Protect-only), Verkada (no ONVIF), Arlo, Ring, Nest, Wyze, eufy battery, Reolink battery.
- When in doubt, this is the right first move on an unfamiliar LAN.

---

## Port / protocol notes

| Port | Protocol | Brand / use |
|------|----------|-------------|
| 554 | RTSP (plain) | Default for nearly every brand: Hikvision, Dahua, Amcrest, Lorex N-series, Axis, Bosch, Avigilon, Reolink PoE, eufy wired, Verkada |
| 1554 | RTSP (plain) | Dahua HF-series alternate |
| 1025 / 1085 | RTSP (plain) | Some Swann DVRs remap RTSP to non-standard ports |
| 7441 | RTSPS (TLS) | UniFi Protect — token-in-URL auth, encrypted by default |
| 322 | RTSPS (TLS) | Wyze RTSP firmware secured variant |
| 80 | RTSP-over-HTTP tunnel | Bosch `/rtsp_tunnel` when 554 is blocked |
| 4100 TCP/UDP | Verkada Local Streaming | Separate from RTSP (port 554) — used for browser local viewing only |
| 37810 UDP | Dahua discovery broadcast | Used by Dahua Config Tool and Amcrest IP Config Tool |
| 5353 UDP | mDNS / Bonjour | Axis, UniFi, Apple-friendly devices |

Always confirm the **actual port** in the camera's web UI before building the URL. Reading the port from a vendor PDF that's two firmware revs old is the #1 cause of silent "RTSP doesn't work" failures.

---

## Common auth quirks

- **Digest vs Basic.** Default is Digest on modern firmware. Hikvision lets the admin force "Basic only" in the Security panel — if a Digest URL fails with 401, swap to Basic before assuming the password is wrong.
- **Special characters in passwords.** Passwords with `@`, `:`, `/`, `#`, `?`, `%` MUST be percent-encoded in the URL. Example: `P@ss/word!` becomes `P%40ss%2Fword%21`. This breaks roughly 1 in 5 "auth fails" tickets.
- **Channel and subtype/stream params.** Multi-channel NVRs require `channel=N` (Dahua) or `/N01` vs `/N02` (Hikvision). For analytics, prefer the sub-stream (`subtype=1`, `Channels/102`, `Preview_01_sub`, `inst=2`) — lower bandwidth and CPU, same scene.
- **ONVIF separate user.** On Hikvision and some Dahua firmware, ONVIF discovery uses a different user account than RTSP. If `GetStreamUri` returns "unauthorized" but RTSP works directly, create an ONVIF user in **Network → Integration Protocol**.
- **Camera-local vs cloud account.** eufy, Wyze, Verkada all distinguish "camera-local RTSP user" from "vendor cloud account." The RTSP creds are NOT the merchant's app login.
- **First-boot password.** Modern firmware (Hikvision 5.4+, Dahua 2017+, Reolink, Bosch 6.x+, Avigilon H5A+) refuses to ship with a default password. If a merchant says "admin/admin doesn't work," that's expected — they set one at first boot.

---

## Troubleshooting decision tree

Walk these in order. Each branch is a 3-step diagnostic — do all three before moving to the next branch.

### Stream won't open at all

1. **Is RTSP actually enabled on the camera?** Open the web UI / vendor app and confirm the toggle. Many cameras ship with RTSP disabled by default (UniFi, Verkada, Bosch on some integrators, eufy on every camera).
2. **Is port 554 (or 7441 for UniFi) reachable from where Meridian runs?** Run `nc -zv <camera-ip> 554` from a host on the same subnet. If closed, it's network/firewall — not a URL problem.
3. **Is the URL syntactically right for this brand?** Pull the matrix entry and test the literal URL in VLC on the same LAN. VLC's error log tells you whether it's auth, connection, or codec.

### Stream drops after N minutes

1. **Switch to RTSP-over-TCP.** UDP-mode RTSP gets dropped by NATs, dual-NAT setups, and firewalls with idle timeouts. Most clients have a flag; in VLC it's `--rtsp-tcp`.
2. **Switch to the sub-stream.** Lower bitrate = fewer dropouts on weak networks. Sub-streams across brands: Hikvision `/102`, Dahua `subtype=1`, Reolink `Preview_01_sub`, Bosch `inst=2`, eufy `live1`.
3. **Check session caps.** Some cameras limit concurrent RTSP sessions (Bosch small models: 4; Verkada: per-camera default). If the merchant's own VMS is also pulling, Meridian may get dropped.

### Black frames / no video (audio negotiates but image is blank)

1. **Codec mismatch.** Default H.265 on Bosch, Dahua 4K+, Reolink 8MP+, Hikvision 6MP+. If the analytics pipeline doesn't decode H.265, force H.264 in the camera profile or pull the sub-stream (which usually stays H.264).
2. **Privacy mask covers the field of view.** Open the camera's privacy/zone config — entire-frame masks render black RTSP frames silently.
3. **Wrong stream-index / profile disabled.** On Hikvision/Bosch/Avigilon, the camera will negotiate RTSP successfully even if the requested encoder profile is disabled — the result is no video. Confirm the profile is enabled with a non-zero bitrate.

### Auth fails (401)

1. **Digest vs Basic.** Swap, re-test. Hikvision often enforces one or the other based on the Security panel setting.
2. **Special characters in the password.** Percent-encode `@ : / # ? %` and any other reserved URL characters.
3. **Wrong user type.** Hikvision/Dahua: ONVIF user ≠ RTSP user ≠ web admin user. Verkada/eufy: RTSP user is set in the app/portal, not the cloud account. Confirm you're using the camera-local credential.

---

## When to recommend replacing the merchant's existing cameras

Reps should default to integrating with what's already on the wall — but there are clear cases to pitch a $60 PoE camera alongside or in place:

**Recommend replacement when:**
- The existing cameras are Ring, Arlo, Nest, Wyze, eufy battery/doorbell, Lorex W-series standalone, Reolink Argus standalone, or any cloud-only brand. There's nothing to integrate with.
- The merchant is on Swann Wi-Fi/battery (SwannSecurity or Tracker app) — same situation.
- The existing cameras are Hikvision/Dahua/Reolink PoE but the firmware is too old for current RTSP patterns (pre-2017 on Dahua, pre-5.4 on Hikvision) AND the merchant won't update firmware.
- The merchant is federal / NDAA-restricted and has Hikvision, Dahua, Amcrest, or Lorex — those won't pass procurement audit even if integration works.

**The pitch:** "Your current cameras keep doing exactly what they do — you keep the mobile app and motion alerts you already use. We add a single $60 Reolink RLC-510A or Hikvision DS-2CD2043G2-I PoE camera per area we want analytics on. It runs on Power-over-Ethernet (no new outlet, no batteries), takes 15 minutes to install, and gives us a clean RTSP feed for foot traffic counting, dwell time, and queue monitoring without touching your existing security setup."

**The two go-to replacement SKUs:**
1. **Reolink RLC-510A** — ~$60 retail, PoE, 5MP, RTSP enabled by default, ONVIF Profile S, indoor/outdoor IP66. Best price-to-performance for general SMB.
2. **Hikvision DS-2CD2043G2-I** — ~$90 retail, PoE, 4MP, full-feature RTSP + ONVIF, better low-light. Use when the merchant has a dim interior or already runs other Hikvision gear.

For both, the install crew should: assign a static IP or DHCP reservation, set a non-default password, create a dedicated non-admin RTSP user, and confirm sub-stream (`subtype=1` or `Channels/102`) is enabled before leaving site.
