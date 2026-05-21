"""
Compliance Acceptance Gate -- tracks which legal documents users have accepted.

Provides helpers to check for pending acceptances and record new ones with
SHA-256 hash proof for audit trail.
"""
import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger("meridian.compliance.acceptance")

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _get_supabase() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    return url, key


def _headers(service_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Content-Type": "application/json",
    }


async def get_pending_acceptances(
    user_id: str,
    user_type: str = "customer",
    has_camera: bool = False,
    province: str = "",
) -> list[dict[str, Any]]:
    """Return documents the user has not yet accepted."""
    if not _UUID_RE.match(user_id):
        logger.error("Invalid user_id format: %s", user_id)
        return []
    supabase_url, service_key = _get_supabase()
    if not supabase_url or not service_key:
        logger.error("Supabase not configured")
        return []

    hdrs = _headers(service_key)

    async with httpx.AsyncClient(timeout=10.0) as client:
        docs_resp = await client.get(
            f"{supabase_url}/rest/v1/compliance_documents"
            f"?is_current=eq.true&select=document_type,version,content,jurisdiction",
            headers=hdrs,
        )
        if docs_resp.status_code != 200:
            logger.error("Failed to fetch compliance docs: %s", docs_resp.text)
            return []

        acc_resp = await client.get(
            f"{supabase_url}/rest/v1/compliance_acceptances"
            f"?user_id=eq.{user_id}&select=document_type,document_version",
            headers=hdrs,
        )
        accepted_set: set[tuple[str, str]] = set()
        if acc_resp.status_code == 200:
            for row in acc_resp.json():
                accepted_set.add((row["document_type"], row["document_version"]))

    pending = []
    for doc in docs_resp.json():
        doc_type = doc["document_type"]
        version = doc["version"]
        jurisdiction = doc.get("jurisdiction", "ALL")

        if jurisdiction not in ("ALL", "CA", "US"):
            continue
        if doc_type == "camera_disclosure" and not has_camera:
            continue
        if jurisdiction == "QC" and province.upper() != "QC":
            continue

        if (doc_type, version) not in accepted_set:
            pending.append({
                "document_type": doc_type,
                "version": version,
                "content": doc.get("content", ""),
            })

    return pending


async def record_acceptance(
    user_id: str,
    user_type: str,
    document_type: str,
    document_version: str,
    ip_address: str = "",
    user_agent: str = "",
    portal_context: str = "",
) -> dict[str, Any]:
    """Record acceptance with SHA-256 hash proof."""
    if not _UUID_RE.match(user_id):
        return {"ok": False, "error": "invalid_user_id_format"}
    supabase_url, service_key = _get_supabase()
    if not supabase_url or not service_key:
        return {"ok": False, "error": "supabase_not_configured"}

    now = datetime.now(timezone.utc).isoformat()
    hash_input = f"{user_id}:{document_type}:{document_version}:{now}"
    acceptance_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    payload = {
        "user_id": user_id,
        "user_type": user_type,
        "document_type": document_type,
        "document_version": document_version,
        "accepted_at": now,
        "ip_address": ip_address or None,
        "user_agent": user_agent,
        "portal_context": portal_context,
        "acceptance_hash": acceptance_hash,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/compliance_acceptances",
            headers={**_headers(service_key), "Prefer": "return=representation"},
            json=payload,
        )

    if resp.status_code == 409:
        return {"ok": True, "already_accepted": True, "acceptance_hash": ""}

    if resp.status_code not in (200, 201):
        logger.error("Acceptance record failed: %s %s", resp.status_code, resp.text)
        return {"ok": False, "error": resp.text}

    logger.info(
        "Acceptance recorded: user=%s doc=%s v=%s hash=%s",
        user_id, document_type, document_version, acceptance_hash[:16],
    )
    return {"ok": True, "acceptance_hash": acceptance_hash}
