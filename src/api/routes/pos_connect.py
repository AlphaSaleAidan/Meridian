"""
Generic POS connect routes (framework — see src/pos_connect/).

  GET /api/pos/providers            → enabled providers for the frontend
  GET /api/pos/{provider}/authorize → redirect merchant to the provider
  GET /api/pos/{provider}/callback  → exchange code, store connection

Square and Clover keep their own routes; this only serves registry providers
that are BOTH verified and credential-configured. Unknown/disabled providers 404.
"""
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from fastapi.responses import RedirectResponse

from ...pos_connect.registry import get_provider, enabled_providers
from ...pos_connect.oauth import GenericOAuthManager, OAuthError, sign_state, verify_state
from ...security.encryption import encrypt_token
from ._oauth_return import (
    origin_from_referer as _origin_from_referer,
    safe_origin as _safe_origin,
    safe_return_to as _safe_return_to,
)

logger = logging.getLogger("meridian.api.pos_connect")

router = APIRouter(prefix="/api/pos", tags=["pos-connect"])

_ORG_ID_RE = re.compile(
    r'^(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    r'|biz_[0-9a-f]{16,40})$', re.I,
)
_DEFAULT_RETURN_TO = "/app/settings"

import os
_FRONTEND_URL = os.environ.get(
    "FRONTEND_URL", os.environ.get("FRONTEND_ORIGIN", "https://meridian.tips")
)


def _redirect_to(return_to: str, params: dict, origin: str = "") -> RedirectResponse:
    base = _safe_origin(origin) or _FRONTEND_URL
    return RedirectResponse(url=f"{base}{return_to or _DEFAULT_RETURN_TO}?{urlencode(params)}")


def _redirect_uri(request: Request, provider_key: str) -> str:
    # Callback must exactly match the redirect_uri registered with the provider.
    base = os.environ.get("API_PUBLIC_URL") or str(request.base_url).rstrip("/")
    return f"{base}/api/pos/{provider_key}/callback"


@router.get("/providers")
async def list_providers():
    """Providers a merchant can 1-click connect right now (verified + configured)."""
    return {
        "providers": [
            {"key": p.key, "label": p.label,
             "authorize_path": f"/api/pos/{p.key}/authorize"}
            for p in enabled_providers()
        ]
    }


@router.get("/{provider}/authorize")
async def authorize(provider: str, request: Request,
                    org_id: str | None = None, return_to: str | None = None):
    cfg = get_provider(provider)
    if cfg is None or not cfg.enabled():
        raise HTTPException(404, "Unknown or unavailable POS provider")
    if not org_id:
        raise HTTPException(400, "org_id is required")

    state = sign_state(provider, org_id, _safe_return_to(return_to))
    mgr = GenericOAuthManager(cfg, _redirect_uri(request, provider))
    logger.info("pos_connect: redirecting org %s to %s", org_id, provider)
    return RedirectResponse(url=mgr.authorize_url(state))


@router.get("/{provider}/callback")
async def callback(provider: str, request: Request, background_tasks: BackgroundTasks,
                   code: str | None = None, state: str | None = None,
                   error: str | None = None, error_description: str | None = None):
    cfg = get_provider(provider)
    if cfg is None or not cfg.enabled():
        raise HTTPException(404, "Unknown or unavailable POS provider")

    origin = _origin_from_referer(request.headers.get("referer"))

    if error:
        verified = verify_state(state) if state else None
        rt = verified[2] if verified else ""
        return _redirect_to(rt, {"oauth": "denied",
                                 "error": error_description or "Authorization was denied."}, origin)
    if not code or not state:
        raise HTTPException(400, "Missing code or state parameter")

    verified = verify_state(state)
    if verified is None or verified[0] != provider:
        raise HTTPException(403, "Invalid or expired state — possible CSRF attack")
    _, org_id, return_to = verified

    mgr = GenericOAuthManager(cfg, _redirect_uri(request, provider))
    # Lightspeed X-Series returns the account's domain_prefix on the callback and
    # its token host is per-account; pass it through when present.
    domain_prefix = request.query_params.get("domain_prefix", "")
    try:
        tokens = await mgr.exchange_code(code, domain_prefix=domain_prefix)
    except OAuthError as e:
        return _redirect_to(return_to, {"oauth": "error", "error": str(e)}, origin)

    merchant_id = await mgr.resolve_merchant_id(tokens) or f"{provider}:{org_id}"

    try:
        from ...db import _db_instance
        if not _db_instance:
            logger.warning("DB not initialized — %s tokens not persisted", provider)
            return _redirect_to(return_to, {"oauth": "partial",
                                            "warning": "Connected but not saved — please retry."}, origin)

        existing = await _db_instance.select(
            "pos_connections",
            filters={"org_id": f"eq.{org_id}", "provider": f"eq.{provider}"},
            limit=1,
        )
        conn_fields = {
            "status": "connected",
            "external_merchant_id": merchant_id,
            "access_token_enc": encrypt_token(tokens["access_token"]),
            "refresh_token_enc": encrypt_token(tokens.get("refresh_token", "")),
            "token_expires_at": tokens.get("expires_at") or None,
            "last_error": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if existing:
            await _db_instance.update("pos_connections", conn_fields,
                                      filters={"id": f"eq.{existing[0]['id']}"})
        else:
            await _db_instance.insert("pos_connections", {
                "id": str(uuid4()), "org_id": org_id, "provider": provider,
                "historical_import_complete": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **conn_fields,
            })

        # Reflect connected state where the dashboard reads it.
        await _db_instance.update("businesses", {"pos_connected": True},
                                  filters={"id": f"eq.{org_id}"})
        await _db_instance.update("organizations",
                                  {"pos_system": provider, "pos_connection_status": "connected"},
                                  filters={"id": f"eq.{org_id}"})
        # NOTE: no data backfill is queued here. run_backfill is Square-specific;
        # each provider's historical sync is a separate build gated on a test
        # merchant (docs/POS_1CLICK_ONBOARDING.md). The connection + tokens are
        # stored so sync can run once that engine exists.
    except Exception as e:
        logger.error("Failed to store %s connection: %s", provider, e, exc_info=True)
        return _redirect_to(return_to, {"oauth": "partial",
                                        "warning": "Connected but failed to save — please retry."}, origin)

    return _redirect_to(return_to, {"oauth": "success", "provider": provider,
                                    "merchant_id": merchant_id}, origin)
