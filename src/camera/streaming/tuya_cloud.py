"""Tuya / Smart Life cloud adapter — the PRIMARY "connect your existing cameras" path.

Most cheap small-business IP cameras already talk to the Tuya (Smart Life) cloud. Instead
of reaching into the merchant's LAN, we meet the camera at the vendor cloud: the merchant
authorizes their existing Smart Life account (OAuth account-link) OR scans the QR/UID
sticker already on the camera, and we pull a stream URL (RTSP/HLS/WebRTC) **cloud-to-cloud
with NO local install**. That relayed stream feeds the SAME MeridianDetector pipeline.

Feasibility (researched 2026): Tuya is the only major vendor that is BOTH self-serve (no
partner-approval gate) AND supports OAuth account-link + QR-sticker onboarding + real
stream-URL allocation. Video streaming is a paid/metered Tuya value-added service past the
free trial — budget per-stream cost. Nest SDM commercial access is currently closed;
UniFi Protect is console-local; Ring/Hikvision are partner-gated.

This module is a thin, dependency-light client (httpx, already a project dep). It is
INERT unless TUYA_ACCESS_ID / TUYA_ACCESS_SECRET are configured — every entry point
returns a clear "not configured" result so the portal can fall back to the LAN connector.

Tuya signature scheme (v2): sign = HMAC-SHA256(access_id + access_token + t + nonce +
stringToSign, secret).upper(); stringToSign = method + "\n" + sha256(body) + "\n" +
headers + "\n" + path. Token requests omit access_token from the sign string.

Docs: https://developer.tuya.com/en/docs/cloud/
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any

import httpx

_TUYA_HOST = os.environ.get("TUYA_API_HOST", "https://openapi.tuyaus.com").rstrip("/")
_EMPTY_BODY_SHA = hashlib.sha256(b"").hexdigest()


def is_configured() -> bool:
    """True only if the Tuya project credentials are present. Fails closed → LAN fallback."""
    return bool(os.environ.get("TUYA_ACCESS_ID") and os.environ.get("TUYA_ACCESS_SECRET"))


def _access_id() -> str:
    return os.environ.get("TUYA_ACCESS_ID", "")


def _access_secret() -> bytes:
    return os.environ.get("TUYA_ACCESS_SECRET", "").encode()


def _sign(str_to_sign: str, *, access_token: str = "") -> tuple[str, str]:
    """Return (signature, timestamp_ms) for a Tuya v2 request."""
    t = str(int(time.time() * 1000))
    payload = _access_id() + access_token + t + str_to_sign
    sig = hmac.new(_access_secret(), payload.encode(), hashlib.sha256).hexdigest().upper()
    return sig, t


def _string_to_sign(method: str, path: str, body: str = "") -> str:
    content_sha = hashlib.sha256(body.encode()).hexdigest() if body else _EMPTY_BODY_SHA
    # No signature-headers used → the headers segment is empty.
    return f"{method}\n{content_sha}\n\n{path}"


async def _request(
    method: str, path: str, *, access_token: str = "", body: str = ""
) -> dict[str, Any]:
    """Signed Tuya API request. Returns the parsed JSON (with Tuya's success/result envelope)."""
    if not is_configured():
        return {"success": False, "code": "not_configured", "msg": "Tuya not configured"}
    sts = _string_to_sign(method, path, body)
    sig, t = _sign(sts, access_token=access_token)
    headers = {
        "client_id": _access_id(),
        "sign": sig,
        "t": t,
        "sign_method": "HMAC-SHA256",
        "Content-Type": "application/json",
    }
    if access_token:
        headers["access_token"] = access_token
    async with httpx.AsyncClient(base_url=_TUYA_HOST, timeout=15) as http:
        r = await http.request(method, path, headers=headers, content=body or None)
        try:
            return r.json()
        except Exception:
            return {"success": False, "code": r.status_code, "msg": r.text[:200]}


async def get_app_token() -> dict[str, Any]:
    """Project-level access token (grant_type=1). Used before end-user account queries."""
    return await _request("GET", "/v1.0/token?grant_type=1")


async def exchange_oauth_code(code: str) -> dict[str, Any]:
    """Exchange an OAuth authorization-code (from the Tuya account-link consent screen) for
    a user access_token. The merchant authorized their existing Smart Life account."""
    path = f"/v1.0/token?grant_type=1&code={code}"
    return await _request("GET", path)


async def list_devices(uid: str, access_token: str) -> list[dict[str, Any]]:
    """List the merchant's Tuya devices; caller filters to cameras (category 'sp')."""
    res = await _request("GET", f"/v1.0/users/{uid}/devices", access_token=access_token)
    if not res.get("success"):
        return []
    return [d for d in (res.get("result") or []) if d.get("category") == "sp"]


async def allocate_stream(device_id: str, access_token: str, *, stream_type: str = "RTSP") -> dict[str, Any]:
    """Allocate a cloud stream URL for one camera (RTSP | HLS). Cloud-to-cloud, no LAN.

    Returns {"ok": bool, "url": str|None, "raw": <tuya envelope>}. The URL is relayed into
    the same MeridianDetector pipeline (source='cloud:tuya'); anonymous tier enforced upstream.
    """
    import json as _json
    body = _json.dumps({"type": stream_type}, separators=(",", ":"))
    path = f"/v1.0/devices/{device_id}/stream/actions/allocate"
    res = await _request("POST", path, access_token=access_token, body=body)
    url = (res.get("result") or {}).get("url") if isinstance(res.get("result"), dict) else None
    return {"ok": bool(res.get("success") and url), "url": url, "raw": res}


def oauth_authorize_url(*, redirect_uri: str, state: str) -> str | None:
    """Build the Smart Life account-link consent URL the merchant clicks. None if unconfigured."""
    if not is_configured():
        return None
    from urllib.parse import urlencode
    q = urlencode({
        "response_type": "code",
        "client_id": _access_id(),
        "redirect_uri": redirect_uri,
        "state": state,
    })
    # Region-specific auth host; merchant logs in with their existing Smart Life account.
    auth_host = os.environ.get("TUYA_AUTH_HOST", "https://auth.tuya.com")
    return f"{auth_host.rstrip('/')}/?{q}"
