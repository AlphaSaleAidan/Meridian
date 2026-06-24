# Meridian Connector (software-only)

Connect your cameras with **no hardware and no router changes**. Runs on a machine you
already have on-site (POS back-office PC, a spare box). It dials **outbound** to Meridian —
nothing needs to be opened on your network.

## Run (Docker — one line)

```sh
docker run -d --network host --restart unless-stopped \
  -e MERIDIAN_PAIRING_CODE=<code from the "Connect cameras" wizard> \
  -e MERIDIAN_API=https://api.meridian.tips \
  ghcr.io/alphasaleaidan/meridian-connector
```

`--network host` lets it auto-discover ONVIF cameras on your LAN. That's it — cameras
appear in your portal within seconds.

## How it works
1. You paste the **pairing code** from the portal wizard → it exchanges for a scoped device token.
2. **go2rtc** auto-discovers your ONVIF cameras and publishes each one **outbound** to the gateway.
3. The connector registers each camera and sends heartbeats; you name them in the portal.

Camera usernames/passwords stay **only on this machine** (in `go2rtc.yaml`), never in the cloud.
Advanced: add a manual `rtsp://user:pass@…` under `streams:` in `go2rtc.yaml` if a camera
isn't ONVIF-discoverable.
