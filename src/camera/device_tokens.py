"""Per-org device tokens for the vision ingest / camera-connector path.

A vision "device" (an on-site PC/POS agent running edge_agent.py, or the LAN
connector) authenticates with an opaque token sent as the ``X-Device-Token``
header — NOT a Supabase user JWT (a headless box has no login). Each token is
minted per org (optionally per site), and only its sha256 hash is persisted in
``vision_device_tokens``; the raw token lives on the device.

Resolution order (see ``resolve_device_token``):

  1. Legacy global ``VISION_INGEST_TOKEN`` env — kept for backward compatibility
     with existing single-tenant deployments. Resolves to org_id=None
     (unbound), so callers that enforce org-match will accept ANY org for it.
     Prefer per-org tokens; the global token should be retired once devices are
     re-provisioned.
  2. A row in ``vision_device_tokens`` matching sha256(token), not revoked →
     resolves to that row's org_id (+ site_id).

Fails closed: an unknown / revoked / empty token resolves to None.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timezone

logger = logging.getLogger("meridian.camera.device_tokens")

TOKEN_PREFIX = "mvd_"  # meridian vision device


def mint_device_token() -> str:
    """Generate a fresh opaque device token. Return the RAW token (store only its hash)."""
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    """sha256 hex of the raw token — what we persist in vision_device_tokens.token_hash."""
    return hashlib.sha256(raw.encode()).hexdigest()


def _legacy_global_token() -> str:
    return os.environ.get("VISION_INGEST_TOKEN", "")


async def resolve_device_token(db, raw: str | None) -> dict | None:
    """Resolve a raw device token to its principal, or None if invalid.

    Returns ``{"org_id": <uuid|None>, "site_id": <uuid|None>, "legacy": bool,
    "token_id": <uuid|None>}``. org_id is None ONLY for the legacy global token
    (unbound). Best-effort updates last_used_at; never raises on DB failure.
    """
    if not raw:
        return None

    legacy = _legacy_global_token()
    if legacy and hmac.compare_digest(raw, legacy):
        return {"org_id": None, "site_id": None, "legacy": True, "token_id": None}

    if db is None:
        return None

    try:
        rows = await db.select(
            "vision_device_tokens",
            "id,org_id,site_id,revoked",
            filters={"token_hash": f"eq.{hash_token(raw)}", "revoked": "eq.false"},
            limit=1,
        )
    except Exception as exc:  # table may be pre-migration; fail closed
        logger.warning("device token lookup failed: %s", exc)
        return None

    if not rows:
        return None
    row = rows[0]

    try:
        await db.update(
            "vision_device_tokens",
            {"last_used_at": datetime.now(timezone.utc).isoformat()},
            filters={"id": f"eq.{row['id']}"},
        )
    except Exception:
        pass  # last_used_at is telemetry, not correctness

    return {
        "org_id": row.get("org_id"),
        "site_id": row.get("site_id"),
        "legacy": False,
        "token_id": row.get("id"),
    }


async def create_device_token(
    db, org_id: str, site_id: str | None = None, label: str | None = None
) -> str:
    """Mint a per-org device token, persist its hash, and return the RAW token
    (shown to the caller exactly once). Raises on DB failure."""
    raw = mint_device_token()
    row = {"org_id": org_id, "token_hash": hash_token(raw)}
    if site_id:
        row["site_id"] = site_id
    if label:
        row["label"] = label
    await db.insert("vision_device_tokens", row)
    return raw


def enforce_org_match(principal: dict, body_org_id: str) -> None:
    """Raise 403 if a per-org token is used to write to a different org. A legacy
    (unbound) token has org_id=None and is allowed through (backward compat)."""
    from fastapi import HTTPException

    org = principal.get("org_id")
    if org is not None and str(org) != str(body_org_id):
        raise HTTPException(status_code=403, detail="Device token not authorized for this org")
