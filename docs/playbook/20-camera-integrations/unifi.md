# UniFi (Ubiquiti)

> Status: **OFFICIALLY SUPPORTED**
> Stream: **RTSPS** (TLS-wrapped RTSP, port **7441**)
> Required plan: Premium or Command

## What you tell the merchant

"UniFi cameras work, but they use RTSPS — that's RTSP wrapped in TLS, on port 7441 instead of the standard 554. Our handler supports it. Connection takes about 5 minutes because UniFi Protect requires enabling RTSPS in the UI before you can grab the URL."

## How the merchant connects

1. UniFi Protect admin → **Cameras → [select camera] → Manage → RTSP**
2. Toggle **Enable RTSPS** (it's off by default)
3. Copy the RTSPS URL — format: `rtsps://protect.unifi.io:7441/{stream_token}?enableSrtp`
4. Paste into Meridian's **Settings → Cameras → Add Camera**
5. We handle the TLS handshake

Typical time to connect: **5 minutes** (extra step is enabling RTSPS in the UI).

## What we use the stream for

Same person-detection pipeline. See [_index.md](./_index.md).

## Compatibility notes

- **Port 7441** is required (not 554) — if the merchant's network blocks it, we can't connect
- TLS certificates from UniFi Protect must be valid (self-signed works but flag in our logs)
- UniFi G3, G4, AI series all work — same RTSPS endpoint pattern
- Cloud Key / UDM-Pro / UNVR all expose RTSPS the same way

## Federal / critical-infrastructure note

UniFi is generally acceptable for non-federal use (no Section 889 ban). Not specifically NDAA/TAA-listed like Axis, but cleaner posture than Hikvision/Dahua. For strict federal customers, still route to [axis.md](./axis.md).

## Sales angle

**Opener:** "You're on UniFi — clean install. Slightly more setup than other cameras because you have to enable RTSPS in the Protect UI, but once it's on, it's solid. Most UniFi merchants are tech-comfortable so this isn't a friction point."

**Best fit:** merchants who already invested in the Ubiquiti ecosystem (UDM, switches, APs). They tend to be Premium-tier ready.

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Stream won't open | Port 7441 blocked by firewall | Whitelist 7441 in router/firewall |
| TLS handshake fails | Self-signed cert without proper config | Our handler supports self-signed; check `src/camera/rtsp_handler.py` config |
| URL token expired | UniFi rotates stream tokens periodically | Regenerate in Protect UI; one-click in Meridian to update |

---

_Last updated: 2026-05-31_
_Sourced from: src/camera/rtsp_handler.py + docs/playbook/_status/phase-2-decisions.md (officially supported, RTSPS on 7441)_
