# Meridian — Connect EXISTING Cameras via QR Pairing + One-Line LAN Connector

**Author:** autonomous session · **Date:** 2026-07-04
**Branch:** `feat/camera-existing-cams` (worktree `/root/meridian-cam-existing`, off `origin/main`)
**Status:** wiring + vendor-cloud increment (PR for review — DO NOT MERGE)

## Corrected direction + full creative latitude (Aidan)

The prior "phone-as-camera" path (PR #263) was the **wrong primary**. Aidan's real
requirement: connect the merchant's **already-installed security cameras** with **zero
hardware shipped by us** and near-zero config — and he gave full latitude to *invent* the
easiest possible way.

**The easiest way is to NOT reach into the LAN at all.** Most existing small-business
cameras already talk to a **manufacturer cloud**. So we meet them there:

> **PRIMARY = camera-cloud aggregation.** Merchant either (a) **scans the QR/serial sticker
> already on their camera**, or (b) **picks their camera brand and authorizes their existing
> camera account (OAuth)** — and we pull streams **cloud-to-cloud with NO local install**.
> "Scan the sticker already on your camera" / "log into the app you already use" = the
> Bluetooth-easy moment.

> **FALLBACK = the one-line LAN connector** (below) only for cameras with **no supported
> cloud API** — a single `docker run` on a PC the merchant already owns; no shipped hardware.

Phone-as-camera stays as a last-resort fallback for merchants with no IP cameras at all.

## Vendor-cloud feasibility (researched 2026 — be honest)

| Vendor | Official API | Access | Auth | Cloud stream | QR/UID sticker | Verdict |
|--------|-------------|--------|------|--------------|----------------|---------|
| **Tuya / Smart Life** | Yes (IoT Cloud, stream allocate) | **OPEN self-serve** | OAuth account-link + project key | RTSP/HLS/WebRTC URL per device | **Yes** | **BUILD FIRST.** Only vendor that's self-serve + OAuth + sticker + huge cheap-cam share. Caveat: streaming is a **paid metered** Tuya service past free trial. |
| UniFi Protect | Yes (API keys, RTSPS) | Open self-serve | API key | Yes (per camera) | No fleet UID | Good for UniFi shops, but **console-local, not a hosted cloud broker** — reach the merchant's own console. |
| Google Nest (SDM) | Yes (GenerateRtspStream/WebRTC) | **Commercial partner-gated + currently CLOSED** | OAuth | Yes (5-min sessions) | No | Sandbox-only today — cannot be the commercial path. |
| Ring | Yes (Appstore WebRTC/WHEP) | **Partner-gated** (app certification) | OAuth-in-Appstore | Yes | No | Needs Amazon/Ring approval → partner track only. |
| Hikvision Hik-Connect / Dahua | Yes (OpenAPI) | **Partner-gated** (approval) | API key after approval | Yes | serial sticker | Partner track; NDAA/procurement sensitivity in US. |
| Wyze | **No official cloud API** | Unavailable | — | reverse-engineered only | serial | **Do NOT build** (ToS risk). |
| Reolink | **No official cloud API** | Unavailable | — | LAN/local only, closed P2P | UID (own app only) | **Do NOT build** cloud path; LAN only. |

**Ranked to prototype:** **1) Tuya — confirmed quickest legit self-serve.** 2) UniFi Protect
(self-serve but console-local). Nest **refuted** as a fast second (commercial access closed).
Ring/Hik = partner-gated. Wyze/Reolink = no official cloud API, excluded.

**What this increment prototypes:** a **Tuya cloud adapter** (`src/camera/streaming/tuya_cloud.py`)
— signed Tuya v2 requests, OAuth account-link URL, device list, and cloud stream-URL
allocation — plus the connect endpoints (`/vision/connect/vendor/tuya/*`). It is **inert
until `TUYA_ACCESS_ID`/`TUYA_ACCESS_SECRET` are set**, and every entry point fails closed to
the LAN-connector fallback when unconfigured.

## The honest reality (state this plainly)

For **generic on-prem IP cameras**, SOME software MUST run on a merchant-owned device on
the same LAN as the cameras. This is **unavoidable** and here's why:

- **NAT** — the cameras sit on a private LAN (192.168.x.x). The cloud cannot reach them
  inbound without port-forwarding (which we refuse to ask for — it's insecure and beyond
  most merchants).
- **Locked cameras** — ONVIF discovery (WS-Discovery) is a LAN-multicast protocol; RTSP
  pull needs the camera's on-LAN address + credentials. None of this is reachable from a
  browser tab or from the cloud.
- **Browsers can't do it** — a web page cannot open raw UDP multicast (WS-Discovery), cannot
  speak RTSP, and cannot reach `192.168.x.x` devices. So "browser-only discovery of on-prem
  cameras" is **impossible**. Be honest: a small native/agent install on a LAN device is
  required for Path B.

**The win** is not "no software" — it's that it's **OUR software on THEIR existing hardware
via a one-line install**, not a box we ship. No Jetson, no appliance, no port-forwarding,
no typing RTSP URLs.

## Existing pieces we WIRE UP (do not rebuild)

Built already in `/root/meridian-camera` (never merged into Meridian main):

| Piece | File | What it does |
|-------|------|--------------|
| `mint_pairing_code(org, site)` | `src/camera/streaming/tokens.py` | Stateless HMAC pairing code, short-lived (15 min). No pairings table needed. |
| `verify_pairing_code(code)` | same | Returns `{org, site}` if valid+unexpired. |
| `POST /api/connector/pair` | `src/api/routes/camera_streaming.py` | Connector exchanges pairing code → device token + org/site. |
| `POST /api/sites/{site}/cameras` | same | Connector registers a discovered camera (device-token auth). |
| connector supervisor | `edge/connector/connector.py` | stdlib-only: pair → poll go2rtc discovered streams → register each → heartbeat. |
| go2rtc config | `edge/connector/go2rtc.yaml` | off-the-shelf (Apache-2.0): ONVIF WS-Discovery + RTSP→WHIP outbound publish. Camera creds stay on-box. |
| Docker one-liner | `edge/connector/README.md` | `docker run --network host … -e MERIDIAN_PAIRING_CODE=…` |

The existing **vision pipeline in Meridian main** (reused unchanged):
`vision_cameras` rows → `vision_traffic`/`vision_visits` → swarm vision agents. Ingest is
`X-Device-Token == VISION_INGEST_TOKEN` on `/api/vision/ingest/*`.

## The connection flow (end-to-end)

```
1. Merchant clicks "Connect my cameras" in the portal (primary option).
2. Backend mints a pairing code (mint_pairing_code) + shows:
     • a QR code / short-link
     • a ONE-LINE docker command with the code baked in
3. Merchant runs the connector on a device they ALREADY own on the camera LAN:
     (a) back-office PC / POS terminal  → `docker run … -e MERIDIAN_PAIRING_CODE=CODE …`
     (b) NVR with app/Docker support (UniFi/Synology) → same image
     (c) a tiny cross-platform binary (follow-up packaging)
4. Connector: POST /api/connector/pair {code} → device token + org/site.
5. go2rtc runs ONVIF WS-Discovery on the LAN → finds cameras (no RTSP typed).
6. Connector registers each discovered camera: POST /api/sites/{site}/cameras
   (device-token auth) → vision_cameras row (source='onvif').
7. Merchant sees the discovered cameras appear LIVE in the portal, taps which to enable.
8. Connector authenticates to each (ONVIF creds / defaults), pulls RTSP LOCALLY, relays
   frames to the cloud pipeline using the pairing/device token.
   Merchant NEVER types an RTSP URL.
```

### Transport choice (simpler working path)

Two options existed: (a) go2rtc relays RTSP→WHIP to a MediaMTX gateway (continuous WebRTC),
or (b) reuse the PR #263 frame-ingest endpoint (`POST /api/vision/camera/frame`, JPEG +
frame-token) and have the connector push periodic JPEGs. **This increment wires the
registration + pairing + portal path** and keeps relay pluggable: the connector already
targets go2rtc's WHIP publish; a JPEG-push adapter is the documented fallback for sites
with no gateway. Registration/pairing is the load-bearing new wiring; both relay transports
feed the SAME detector/writer.

## Path C — cloud-camera OAuth (nothing local at all) — design only

For cameras that expose a **cloud API**, no local install is needed:

| Vendor | API | Feasibility |
|--------|-----|-------------|
| UniFi Protect | official API keys, RTSPS export per camera | Medium (controller reachable) |
| Google Nest (SDM) | Device Access, `GenerateRtspStream`/WebRTC, OAuth | Medium ($5 one-time reg) |
| Verkada / Rhombus | official REST + streaming | High if merchant already runs one (enterprise HW they bought) |
| Ring / Wyze | no official public streaming API | Low — ToS risk, avoid |

Each becomes a `source='cloud:<vendor>'` adapter that pulls a stream URL / periodic snapshot
and feeds the same detector. **Recommend UniFi Protect + Nest SDM first.** Not in this PR.

## Friction rating (per path, easiest first)

| Path | Merchant does | Friction vs Bluetooth |
|------|---------------|-----------------------|
| **Vendor-cloud — scan sticker (PRIMARY)** | Open portal → scan the QR/UID sticker already on the camera → authorize the camera app they already use | **~1x Bluetooth.** Genuinely tap-to-pair, zero install, connects their INSTALLED cameras. Only works for supported clouds (Tuya today). |
| **Vendor-cloud — pick brand + OAuth (PRIMARY)** | "Which brand?" → log into their existing Smart Life / vendor account → tap which cameras to enable | **~1.2x Bluetooth.** No install, cloud-to-cloud; one OAuth screen. |
| **LAN connector one-liner (FALLBACK)** | Run one `docker run` line on a PC they already have → tap which auto-discovered cameras to enable | **~2.5x Bluetooth.** No hardware, no RTSP typing, no port-forward, but needs a LAN device with Docker/a binary. For cameras with no supported cloud. |
| Phone-as-camera (last resort) | Open a QR link on any phone, allow camera, prop it | **~1x Bluetooth** but it's a NEW camera, not their installed ones — only when they have no IP cameras. |
| Old manual-RTSP + shipped Jetson (REPLACED) | Buy an edge box, find each camera IP+creds, type `rtsp://user:pass@…` per camera | **~10x Bluetooth.** The status quo this PR removes. |

**Net:** the vendor-cloud primary is a **~10x → ~1x** friction reduction over the old
manual-RTSP + shipped-hardware flow, and it connects the merchant's ACTUAL installed cameras
with zero install. The LAN connector (~2.5x) covers cameras with no cloud API. The only path
that honestly requires a local agent is the LAN fallback — and that's unavoidable for
cloud-less on-prem cameras behind NAT (browsers cannot do WS-Discovery / RTSP / reach
192.168.x.x).

## What THIS increment ships

**Vendor-cloud PRIMARY (prototyped):**
1. `src/camera/streaming/tuya_cloud.py` — Tuya cloud adapter: Tuya v2 request signing,
   `oauth_authorize_url` (Smart Life account-link), `exchange_oauth_code`, `list_devices`
   (filters to cameras), `allocate_stream` (RTSP/HLS URL, cloud-to-cloud). Inert unless
   `TUYA_ACCESS_ID`/`TUYA_ACCESS_SECRET` set; fails closed to the LAN fallback.
2. `POST /api/vision/connect/vendor/tuya/scan` — resolve a scanned QR/UID sticker (routes to
   OAuth to finish). `GET …/tuya/oauth-url` — the account-link consent URL.
   `POST …/tuya/link` — exchange code → list + register each camera as `source='cloud:tuya'`.

**LAN connector FALLBACK (wired):**
3. Port pairing tokens (`src/camera/streaming/tokens.py`), `/api/connector/pair`, and
   `/api/sites/{site}/cameras` register into Meridian main; mount `camera_connect` in `app.py`.
4. `POST /api/vision/connect/pairing-code` (org-JWT) → mints a pairing code + QR payload +
   the ONE-LINE `docker run` command + a bootstrapped default site.

**Shared:**
5. Additive migration `024_camera_source_sites.sql`: `source` + `connect_token_hash` on
   `vision_cameras`, and `camera_sites` table (idempotent, `IF NOT EXISTS`, RLS).
6. Rewrite `CameraSetupWizard.tsx`: PRIMARY = "Connect existing cameras" (scan sticker /
   pick brand → OAuth); FALLBACK = one-line LAN connector; manual RTSP demoted to Advanced.
   Removes the shipped-Jetson step.
7. Tests: pytest (14) — pairing-code mint/verify (tamper/expiry/no-secret), Tuya
   config/sign/link (anonymous enforced), `/connector/pair` auth, connector register
   (device-token reject, site-ownership 404, happy path). tsc clean on the wizard.

## What can't run locally / manual-test recipe

- **ONVIF discovery** (WS-Discovery multicast) and **real RTSP pull** need a real LAN + a
  physical camera — not reproducible on this box. Covered by mocked/unit tests; the connector
  code itself is the already-tested `edge/connector/` from meridian-camera.
- **Tuya cloud calls** need real project credentials + a linked Smart Life account. The
  adapter is unit-tested with mocked cloud responses; a live run needs `TUYA_ACCESS_ID/SECRET`
  and a merchant OAuth link.
- **Manual test recipe (LAN fallback):** set `GATEWAY_JWT_SECRET`+`VISION_INGEST_TOKEN`,
  call `POST /api/vision/connect/pairing-code` with a valid org JWT → get the `docker run`
  line → run the meridian-camera connector on a LAN box with an ONVIF camera → confirm a
  `source='onvif'` row appears via `GET /api/vision/cameras/{org}`.
- **Manual test recipe (Tuya):** set `TUYA_ACCESS_ID/SECRET`, `GET …/tuya/oauth-url` →
  complete Smart Life consent → `POST …/tuya/link` with the returned code → confirm
  `source='cloud:tuya'` rows.

## What remains (follow-ups, not this PR)

- Live relay wiring: allocate Tuya stream URLs on a schedule → feed `MeridianDetector`
  (cloud path); go2rtc→MediaMTX WHIP gateway (or JPEG-push) for the LAN path.
- Publish the connector container image / cross-platform binary (packaging + CI).
- Per-device scoped tokens (connector currently uses shared `VISION_INGEST_TOKEN`).
- Additional vendor adapters: UniFi Protect (self-serve, console-local) next; Ring/Hikvision
  via partner programs; Nest SDM when Google reopens commercial access.
- Rate-limiting / fps caps + Tuya streaming-cost accounting before scale.

## Guardrails honored

- FEATURE = PR only, never merge/deploy.
- Reuse the already-built ONVIF/go2rtc connector + existing pipeline — no reinvention.
- Anonymous compliance is the default and only shipping tier; `opt_in_identity` stays gated
  behind `CAMERA_IDENTITY_ENABLED`. No biometric backdoor.
- Additive migration only (`IF NOT EXISTS`), no destructive change.
