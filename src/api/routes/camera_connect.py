"""Camera-connect endpoints — "connect your EXISTING cameras" (no shipped hardware).

Corrected direction: connect the merchant's ALREADY-INSTALLED cameras, not a phone.
Ordered by merchant friction (easiest first):

  PRIMARY — vendor-cloud (no local install at all):
    POST /api/vision/connect/vendor/tuya/scan     resolve a scanned QR/UID sticker (design stub)
    GET  /api/vision/connect/vendor/tuya/oauth-url account-link consent URL (Smart Life login)
    POST /api/vision/connect/vendor/tuya/link      exchange OAuth code → list + register cameras

  FALLBACK — one-line LAN connector (for cameras with no supported cloud):
    POST /api/vision/connect/pairing-code          mint a pairing code + QR + one-line docker cmd
    POST /api/connector/pair                        connector exchanges code → device token
    POST /api/sites/{site_id}/cameras               connector registers a discovered camera

All merchant-facing routes are org-JWT scoped (require_org_access). The connector routes
use device-token auth (VISION_INGEST_TOKEN). Anonymous compliance is enforced everywhere;
opt-in identity stays gated behind CAMERA_IDENTITY_ENABLED. Cross-tenant → 404 (no leak).
"""
from __future__ import annotations

import json as _json
import logging
import os
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from ..auth import require_org_access
from ...camera.streaming import tuya_cloud
from ...camera.streaming.tokens import mint_pairing_code, verify_pairing_code

logger = logging.getLogger("meridian.api.camera_connect")

router = APIRouter(prefix="/api", tags=["camera-connect"])

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _get_db():
    from ...db import _db_instance as db
    return db


def _uuid(v: str, label: str):
    if not _UUID_RE.match(v or ""):
        raise HTTPException(400, f"Invalid {label}")


async def _default_site(db, org_id: str) -> str:
    """Return (creating if needed) the org's default camera_sites row id. The connector
    registers discovered cameras under a site. Idempotent, additive."""
    try:
        sites = await db.select("camera_sites", filters={"org_id": f"eq.{org_id}"}, limit=1)
        if sites:
            return sites[0]["id"]
    except Exception as e:  # table may be new / not yet migrated
        logger.warning("camera_sites lookup failed (migration applied?): %s", e)
    site = {"id": str(uuid4()), "org_id": org_id, "name": "Default site"}
    try:
        rows = await db.insert("camera_sites", site)
        return (rows[0] if rows else site)["id"]
    except Exception as e:
        logger.warning("camera_sites insert failed: %s", e)
        return site["id"]


def _enforce_anonymous(mode: str) -> str:
    """Anonymous is the only shipping tier unless CAMERA_IDENTITY_ENABLED=1."""
    if mode != "anonymous" and os.environ.get("CAMERA_IDENTITY_ENABLED", "") not in ("1", "true", "yes"):
        return "anonymous"
    return mode


# ───────────────────────── PRIMARY: vendor-cloud (Tuya) ─────────────────────────
class OrgBody(BaseModel):
    org_id: str


class TuyaScanBody(BaseModel):
    org_id: str
    qr_payload: str  # raw contents of the sticker QR (encodes a Tuya P2P UID / device id)


@router.post("/vision/connect/vendor/tuya/scan", dependencies=[Depends(require_org_access)])
async def tuya_scan(body: TuyaScanBody):
    """Merchant scans the QR/UID sticker already on their camera. We parse the device id and,
    if the account is already linked, resolve it via the Tuya cloud. If not configured or the
    account isn't linked yet, we return next_step='oauth' so the UI routes to account-link.

    (Full UID→cloud resolution requires the account OAuth link; the scan pre-fills the device.)"""
    if not tuya_cloud.is_configured():
        return {"vendor": "tuya", "configured": False, "next_step": "lan_connector",
                "message": "Vendor-cloud not configured on this deployment; use the LAN connector."}
    device_hint = (body.qr_payload or "").strip()[:128]
    return {"vendor": "tuya", "configured": True, "device_hint": device_hint,
            "next_step": "oauth",
            "message": "Sticker recognized. Authorize your Smart Life account to finish connecting."}


@router.get("/vision/connect/vendor/tuya/oauth-url", dependencies=[Depends(require_org_access)])
async def tuya_oauth_url(org_id: str):
    """Return the Smart Life account-link consent URL. Merchant logs into their EXISTING
    camera account; we then pull their cameras cloud-to-cloud. No local install."""
    if not tuya_cloud.is_configured():
        raise HTTPException(503, "Vendor-cloud (Tuya) not configured")
    redirect = os.environ.get("TUYA_OAUTH_REDIRECT", "https://api.meridian.tips/api/vision/connect/vendor/tuya/callback")
    url = tuya_cloud.oauth_authorize_url(redirect_uri=redirect, state=org_id)
    return {"vendor": "tuya", "authorize_url": url, "state": org_id}


class TuyaLinkBody(BaseModel):
    org_id: str
    code: str                      # OAuth authorization code from the Tuya consent redirect
    uid: str | None = None         # Tuya user id (from the account link), if known
    compliance_mode: str = "anonymous"


@router.post("/vision/connect/vendor/tuya/link", dependencies=[Depends(require_org_access)])
async def tuya_link(body: TuyaLinkBody):
    """Exchange the OAuth code, list the merchant's Tuya cameras, and register each as a
    source='cloud:tuya' vision_cameras row (cloud-to-cloud, no local install)."""
    if not tuya_cloud.is_configured():
        raise HTTPException(503, "Vendor-cloud (Tuya) not configured")
    db = _get_db()
    if not db:
        raise HTTPException(503, "Database not available")

    tok = await tuya_cloud.exchange_oauth_code(body.code)
    if not tok.get("success"):
        raise HTTPException(400, f"Tuya OAuth exchange failed: {tok.get('msg', 'unknown')}")
    result = tok.get("result") or {}
    access_token = result.get("access_token", "")
    uid = body.uid or result.get("uid", "")
    if not access_token or not uid:
        raise HTTPException(400, "Tuya OAuth did not return an access token / uid")

    cameras = await tuya_cloud.list_devices(uid, access_token)
    mode = _enforce_anonymous(body.compliance_mode)
    registered = []
    for cam in cameras:
        dev_id = cam.get("id")
        if not dev_id:
            continue
        row = {
            "org_id": body.org_id,
            "name": cam.get("name") or f"Tuya camera {dev_id[:6]}",
            "rtsp_url": f"cloud:tuya:{dev_id}",   # sentinel; real URL allocated on demand
            "source": "cloud:tuya",
            "compliance_mode": mode,
            "status": "online" if cam.get("online") else "offline",
        }
        try:
            saved = await db.insert("vision_cameras", row)
            registered.append(saved[0] if saved else row)
        except Exception as e:
            logger.warning("register tuya camera %s failed: %s", dev_id, e)
    return {"vendor": "tuya", "linked": True, "count": len(registered), "cameras": registered}


# ───────────────────────── FALLBACK: one-line LAN connector ─────────────────────────
@router.post("/vision/connect/pairing-code", dependencies=[Depends(require_org_access)])
async def connect_pairing_code(body: OrgBody):
    """Mint a pairing code for the LAN-connector fallback + return the QR payload and the
    ONE-LINE docker command the merchant runs on a device they already own. Used only when
    their cameras have no supported vendor cloud."""
    db = _get_db()
    if not db:
        raise HTTPException(503, "Database not available")
    site_id = await _default_site(db, body.org_id)
    try:
        code = mint_pairing_code(body.org_id, site_id)
    except RuntimeError:
        raise HTTPException(503, "Connector pairing not configured (GATEWAY_JWT_SECRET unset)")
    api = os.environ.get("MERIDIAN_PUBLIC_API", "https://api.meridian.tips")
    image = os.environ.get("CONNECTOR_IMAGE", "ghcr.io/alphasaleaidan/meridian-connector")
    one_line = (
        f"docker run -d --network host --restart unless-stopped "
        f"-e MERIDIAN_PAIRING_CODE={code} -e MERIDIAN_API={api} {image}"
    )
    return {
        "pairing_code": code,
        "site_id": site_id,
        "expires_in": 900,
        "install_command": one_line,
        # QR encodes the code + api so a companion scan can hand off to a helper.
        "qr_payload": _json.dumps({"t": "meridian-connect", "code": code, "api": api}),
        "docs": "Run this one line on a PC/POS terminal on the same network as your cameras. "
                "It auto-discovers your ONVIF cameras — no RTSP URLs, no hardware, no port forwarding.",
    }


class PairBody(BaseModel):
    code: str


@router.post("/connector/pair")
async def connector_pair(body: PairBody):
    """Connector exchanges a wizard pairing code for a device token + its site/org.
    The pairing code itself is the credential (stateless HMAC, short-lived).

    Mints a PER-ORG device token (vision_device_tokens) scoped to this org+site so
    one connector can't write to another merchant's data. Falls back to the legacy
    global VISION_INGEST_TOKEN only when no DB is available (dev/single-tenant)."""
    from ...camera.device_tokens import create_device_token

    info = verify_pairing_code(body.code)
    if not info:
        raise HTTPException(401, "Invalid or expired pairing code")

    db = _get_db()
    device_token = None
    if db:
        try:
            device_token = await create_device_token(
                db, info["org"], site_id=info["site"], label="LAN connector"
            )
        except Exception as e:
            logger.warning("per-org device token mint failed, falling back to global: %s", e)
    if not device_token:
        device_token = os.environ.get("VISION_INGEST_TOKEN", "")
    if not device_token:
        raise HTTPException(503, "Connector pairing not configured")
    return {
        "device_token": device_token,
        "org_id": info["org"],
        "site_id": info["site"],
        "gateway": os.environ.get("MEDIA_STREAM_HOST", "stream.meridian.tips"),
    }


async def require_device_token(x_device_token: str | None = Header(None)):
    """Connector auth. Accepts a per-org device token (vision_device_tokens) OR the
    legacy global VISION_INGEST_TOKEN, via X-Device-Token. Fails closed."""
    from ...camera.device_tokens import resolve_device_token

    principal = await resolve_device_token(_get_db(), x_device_token)
    if principal is None:
        raise HTTPException(401, "Invalid device token")
    return principal


class ConnectorCameraRegister(BaseModel):
    org_id: str
    name: str
    rtsp_url: str | None = None        # blank on the ONVIF happy path (creds stay on-box)
    compliance_mode: str = "anonymous"


@router.post("/sites/{site_id}/cameras")
async def register_connector_camera(
    site_id: str,
    body: ConnectorCameraRegister,
    principal: dict = Depends(require_device_token),
):
    """Connector registers an auto-discovered ONVIF camera under a site (device-token auth)."""
    from ...camera.device_tokens import enforce_org_match

    _uuid(site_id, "site_id")
    enforce_org_match(principal, body.org_id)
    db = _get_db()
    if not db:
        raise HTTPException(503, "Database not available")
    sites = await db.select("camera_sites", filters={"id": f"eq.{site_id}", "org_id": f"eq.{body.org_id}"})
    if not sites:
        raise HTTPException(404, "Site not found")
    row = {
        "id": str(uuid4()),
        "org_id": body.org_id,
        "site_id": site_id,
        "name": body.name,
        "rtsp_url": body.rtsp_url or "",     # blank on the ONVIF happy path
        "source": "onvif",
        "compliance_mode": _enforce_anonymous(body.compliance_mode),
        "status": "offline",
    }
    try:
        saved = await db.insert("vision_cameras", row)
        return {"camera": saved[0] if saved else row}
    except Exception as e:
        logger.error("connector camera register failed: %s", e)
        raise HTTPException(500, "Failed to register camera")
