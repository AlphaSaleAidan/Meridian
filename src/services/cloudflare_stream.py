"""
Cloudflare Stream — Live Inputs for on-demand camera live view (WHIP/WHEP).

The edge agent WHIP-publishes a camera's RTSP feed to a Cloudflare Live Input
only while a viewer is watching; the browser plays the WHEP URL. Cloudflare is
the relay — nothing video runs on our own hosts. Verified 2026-06-26: RTMPS test
publish drove a Live Input to state=connected; WHIP/WHEP URLs returned on create.

Creds (account-level, no domain needed) from env / /root/.secrets/cloudflare.env:
  CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_STREAM_TOKEN (Account·Stream:Edit).
All calls fail soft (return None) so the camera flow never 500s if unconfigured.
"""
import logging
import os

import httpx

logger = logging.getLogger("meridian.cloudflare_stream")

_BASE = os.getenv("CLOUDFLARE_API_BASE", "https://api.cloudflare.com/client/v4")


def _cfg() -> tuple[str, str] | None:
    acct = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    token = os.getenv("CLOUDFLARE_STREAM_TOKEN", "")
    return (acct, token) if acct and token else None


def _urls(result: dict) -> dict:
    """Extract the WHIP (ingest) + WHEP (playback) URLs from a Live Input."""
    return {
        "uid": result.get("uid"),
        "whip_url": (result.get("webRTC") or {}).get("url"),
        "whep_url": (result.get("webRTCPlayback") or {}).get("url"),
    }


async def create_live_input(name: str, creator: str = "") -> dict | None:
    """Create a recording-off Live Input. Returns {uid, whip_url, whep_url}."""
    cfg = _cfg()
    if not cfg:
        logger.warning("Cloudflare Stream not configured — skipping live input create")
        return None
    acct, token = cfg
    body = {"meta": {"name": name[:100]}, "recording": {"mode": "off"}}
    if creator:
        body["defaultCreator"] = creator[:100]
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(f"{_BASE}/accounts/{acct}/stream/live_inputs",
                             headers={"Authorization": f"Bearer {token}"}, json=body)
        data = r.json()
        if not data.get("success"):
            logger.error("CF live input create failed: %s", data.get("errors"))
            return None
        return _urls(data.get("result") or {})
    except Exception as e:  # noqa: BLE001
        logger.error("CF live input create error: %s", e)
        return None


async def get_live_input(uid: str) -> dict | None:
    """Fetch an existing Live Input's WHIP/WHEP URLs (None if gone)."""
    cfg = _cfg()
    if not cfg or not uid:
        return None
    acct, token = cfg
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(f"{_BASE}/accounts/{acct}/stream/live_inputs/{uid}",
                            headers={"Authorization": f"Bearer {token}"})
        data = r.json()
        if not data.get("success"):
            return None
        return _urls(data.get("result") or {})
    except Exception as e:  # noqa: BLE001
        logger.error("CF live input get error: %s", e)
        return None


async def delete_live_input(uid: str) -> bool:
    cfg = _cfg()
    if not cfg or not uid:
        return False
    acct, token = cfg
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.delete(f"{_BASE}/accounts/{acct}/stream/live_inputs/{uid}",
                               headers={"Authorization": f"Bearer {token}"})
        return r.json().get("success", False)
    except Exception as e:  # noqa: BLE001
        logger.error("CF live input delete error: %s", e)
        return False
