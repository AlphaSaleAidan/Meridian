"""Short-lived, single-camera stream tokens (HMAC, stdlib only — ponytail: no JWT dep).

mint_stream_token() is used by the FastAPI /cameras/:id/live-token endpoint (Phase 3);
verify_stream_token() is used by the gateway auth hook. Fails CLOSED if no secret is set.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time


def _secret() -> bytes:
    return os.environ.get("GATEWAY_JWT_SECRET", "").encode()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def mint_stream_token(camera_id: str, *, ttl_seconds: int = 60, subject: str | None = None) -> str:
    """Mint a token scoped to ONE camera, valid for ttl_seconds (capped at 60)."""
    secret = _secret()
    if not secret:
        raise RuntimeError("GATEWAY_JWT_SECRET not configured")
    ttl = max(1, min(int(ttl_seconds), 60))
    payload = {"cam": camera_id, "exp": int(time.time()) + ttl, "sub": subject}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def mint_pairing_code(org_id: str, site_id: str, *, ttl_seconds: int = 900) -> str:
    """Wizard-shown pairing code (stateless HMAC; default 15 min). The connector exchanges
    it at /api/connector/pair for a device token. ponytail: no pairings table needed."""
    secret = _secret()
    if not secret:
        raise RuntimeError("GATEWAY_JWT_SECRET not configured")
    payload = {"org": org_id, "site": site_id, "exp": int(time.time()) + int(ttl_seconds)}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_pairing_code(code: str) -> dict | None:
    """Return {org, site} if the pairing code is valid + unexpired, else None."""
    secret = _secret()
    if not secret or not code or "." not in code:
        return None
    try:
        body, sig = code.split(".", 1)
        if not hmac.compare_digest(sig, _b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())):
            return None
        payload = json.loads(_unb64(body))
        if payload.get("exp", 0) < time.time():
            return None
        return {"org": payload["org"], "site": payload["site"]}
    except Exception:
        return None


def verify_stream_token(token: str, camera_id: str) -> bool:
    """True only if signature valid, not expired, and scoped to camera_id."""
    secret = _secret()
    if not secret or not token or "." not in token:
        return False
    try:
        body, sig = token.split(".", 1)
        expected = _b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return False
        payload = json.loads(_unb64(body))
        return payload.get("cam") == camera_id and payload.get("exp", 0) >= time.time()
    except Exception:
        return False
