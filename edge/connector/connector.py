#!/usr/bin/env python3
"""meridian-connector — software-only camera connector (Phase 4).

Runs on a machine the customer already has on-site. Outbound only — no router
changes, no port-forwarding, no hardware. go2rtc (sidecar) does ONVIF discovery +
RTSP->WebRTC publish to the cloud gateway; this supervisor pairs, registers cameras,
and heartbeats. Camera credentials stay on this box (in go2rtc.yaml), never in the cloud.

Env:
  MERIDIAN_API           e.g. https://api.meridian.tips
  MERIDIAN_PAIRING_CODE  shown in the portal "Connect cameras" wizard
  GO2RTC_API             local go2rtc API (default http://127.0.0.1:1984)
ponytail: stdlib only (urllib), retry loops, no frameworks.
"""
import json
import logging
import os
import time
import urllib.error
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s connector %(levelname)s %(message)s")
log = logging.getLogger("connector")

API = os.environ.get("MERIDIAN_API", "https://api.meridian.tips").rstrip("/")
PAIRING_CODE = os.environ.get("MERIDIAN_PAIRING_CODE", "")
GO2RTC = os.environ.get("GO2RTC_API", "http://127.0.0.1:1984").rstrip("/")
HEARTBEAT_SEC = int(os.environ.get("HEARTBEAT_SEC", "30"))


def _post(url, body, headers=None):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode() or "{}")


def _get(url):
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode() or "{}")


def pair() -> dict:
    """Exchange the wizard pairing code for a scoped device token + site/org."""
    while True:
        try:
            res = _post(f"{API}/api/connector/pair", {"code": PAIRING_CODE})
            log.info("paired: site=%s", res.get("site_id"))
            return res
        except Exception as e:  # noqa: BLE001 - retry forever until paired
            log.warning("pairing failed (%s), retrying in 10s", e)
            time.sleep(10)


def discovered_cameras() -> dict:
    """go2rtc lists streams it discovered (ONVIF) / has configured."""
    try:
        return _get(f"{GO2RTC}/api/streams") or {}
    except Exception as e:  # noqa: BLE001
        log.warning("go2rtc discovery query failed: %s", e)
        return {}


def register(site_id: str, token: str, org_id: str, name: str) -> str | None:
    try:
        res = _post(f"{API}/api/sites/{site_id}/cameras",
                    {"org_id": org_id, "name": name},
                    headers={"X-Device-Token": token})
        return (res.get("camera") or {}).get("id")
    except Exception as e:  # noqa: BLE001
        log.warning("register %s failed: %s", name, e)
        return None


def heartbeat(camera_id: str, token: str):
    try:
        _post(f"{API}/api/vision/cameras/{camera_id}/heartbeat", {"status": "online"},
              headers={"X-Device-Token": token})
    except Exception as e:  # noqa: BLE001
        log.debug("heartbeat %s failed: %s", camera_id, e)


def main():
    if not PAIRING_CODE:
        log.error("MERIDIAN_PAIRING_CODE not set"); return 2
    paired = pair()
    token, org_id, site_id = paired["device_token"], paired["org_id"], paired["site_id"]

    registered: dict[str, str] = {}  # go2rtc stream name -> camera_id
    while True:
        for name in discovered_cameras():
            if name not in registered:
                cam_id = register(site_id, token, org_id, name)
                if cam_id:
                    registered[name] = cam_id
                    log.info("registered camera %s -> %s", name, cam_id)
        for cam_id in registered.values():
            heartbeat(cam_id, token)
        time.sleep(HEARTBEAT_SEC)


if __name__ == "__main__":
    raise SystemExit(main())
