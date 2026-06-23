"""Internal gateway auth hook — MediaMTX calls POST /gateway/auth to authorize every
publish (connector) and read (viewer). NEVER expose this publicly via nginx; MediaMTX
reaches it on 127.0.0.1:8000. Fails CLOSED (deny) when secrets are unset.

2xx = allow, anything else = deny (MediaMTX semantics).
"""
from __future__ import annotations

import logging
import os
from urllib.parse import parse_qs

from fastapi import APIRouter, Request, Response

from src.camera.streaming.tokens import verify_stream_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["gateway"])


def _camera_id_from_path(path: str) -> str | None:
    # paths look like "cam/<camera_id>"
    if path.startswith("cam/"):
        return path.split("/", 1)[1].split("/", 1)[0] or None
    return None


@router.post("/gateway/auth")
async def gateway_auth(req: Request) -> Response:
    try:
        body = await req.json()
    except Exception:
        return Response(status_code=400)

    action = (body.get("action") or "").lower()
    camera_id = _camera_id_from_path(body.get("path") or "")

    # Connector publishing a camera: validate the publish secret (Phase 4 swaps this
    # for per-device scoped tokens). Fail closed if the secret isn't configured.
    if action == "publish":
        secret = os.environ.get("GATEWAY_PUBLISH_SECRET", "")
        if secret and body.get("password") == secret:
            return Response(status_code=204)
        logger.warning("gateway publish denied (path=%s)", body.get("path"))
        return Response(status_code=401)

    # Viewer reading a camera: require a valid short-lived, single-camera token.
    if action in ("read", "playback"):
        if not camera_id:
            return Response(status_code=403)
        token = body.get("password") or ""
        if not token:  # also accept ?jwt= in the query
            token = (parse_qs(body.get("query") or "").get("jwt") or [""])[0]
        if verify_stream_token(token, camera_id):
            return Response(status_code=204)
        logger.warning("gateway read denied (cam=%s)", camera_id)
        return Response(status_code=401)

    # api / metrics / anything else: deny by default.
    return Response(status_code=403)
