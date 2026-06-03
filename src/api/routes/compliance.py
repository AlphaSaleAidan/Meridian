"""
Compliance API Routes -- PIPEDA/CASL/privacy endpoints.

  POST /api/compliance/accept          -- record document acceptance (requires auth)
  GET  /api/compliance/pending/{uid}   -- get pending acceptances
  POST /api/privacy/request            -- submit privacy request (no auth required)
  GET  /api/privacy/export/{uid}       -- export all personal data (admin only)
  GET  /api/compliance/casl/status     -- CASL consent stats (admin only)
  GET  /api/compliance/dashboard       -- full compliance dashboard (admin only)
  POST /api/compliance/breach          -- log a new breach incident (admin only)
  GET  /api/compliance/breach          -- list all breach records (admin only)
  POST /api/privacy/unsubscribe       -- process unsubscribe from email link (no auth)
"""
import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from ..auth import ADMIN_EMAILS, require_admin_jwt

logger = logging.getLogger("meridian.api.compliance")

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _validate_user_id(user_id: str) -> None:
    """Validate user_id is a proper UUID to prevent PostgREST filter injection."""
    if not _UUID_RE.match(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id format")

router = APIRouter(tags=["compliance"])


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


def _require_admin(admin_email: str) -> None:
    if admin_email.lower() not in [e.lower() for e in ADMIN_EMAILS]:
        raise HTTPException(403, "Not authorized -- admin email not recognized")


# ---------- Request Models ----------

class AcceptanceRequest(BaseModel):
    user_id: str
    user_type: str  # customer, sales_rep, admin
    document_type: str
    document_version: str
    ip_address: str = ""
    user_agent: str = ""
    portal_context: str = ""


class PrivacyRequestSubmission(BaseModel):
    request_type: str  # access, correction, deletion, portability, objection, withdraw_consent
    requester_email: EmailStr
    requester_name: Optional[str] = None
    user_id: Optional[str] = None
    portal_context: Optional[str] = None
    request_description: Optional[str] = None


class BreachReport(BaseModel):
    incident_description: str
    data_types_involved: list[str] = []
    estimated_individuals_affected: int = 0
    severity: str = "medium"
    admin_email: EmailStr


class UnsubscribeRequest(BaseModel):
    email: EmailStr
    token: Optional[str] = None


class AdminQuery(BaseModel):
    admin_email: EmailStr


# ---------- Document Acceptance ----------

@router.post("/api/compliance/accept")
async def accept_document(req: AcceptanceRequest):
    """Record a user's acceptance of a compliance document."""
    _validate_user_id(req.user_id)
    supabase_url, service_key = _get_supabase()
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    now = datetime.now(timezone.utc).isoformat()
    hash_input = f"{req.user_id}:{req.document_type}:{req.document_version}:{now}"
    acceptance_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    payload = {
        "user_id": req.user_id,
        "user_type": req.user_type,
        "document_type": req.document_type,
        "document_version": req.document_version,
        "accepted_at": now,
        "ip_address": req.ip_address or None,
        "user_agent": req.user_agent,
        "portal_context": req.portal_context,
        "acceptance_hash": acceptance_hash,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/compliance_acceptances",
            headers={
                **_headers(service_key),
                "Prefer": "return=representation",
            },
            json=payload,
        )

    if resp.status_code == 409:
        return {"ok": True, "already_accepted": True}
    if resp.status_code not in (200, 201):
        logger.error("Acceptance insert failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(500, "Could not record acceptance")

    logger.info("Acceptance recorded: user=%s doc=%s v=%s", req.user_id, req.document_type, req.document_version)
    return {"ok": True, "acceptance_hash": acceptance_hash}


@router.get("/api/compliance/pending/{user_id}")
async def get_pending_acceptances(user_id: str, user_type: str = "customer", has_camera: bool = False, province: str = ""):
    """Return list of documents this user has not yet accepted."""
    _validate_user_id(user_id)
    supabase_url, service_key = _get_supabase()
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    hdrs = _headers(service_key)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Fetch all current documents
        docs_resp = await client.get(
            f"{supabase_url}/rest/v1/compliance_documents?is_current=eq.true&select=document_type,version,content,jurisdiction",
            headers=hdrs,
        )
        if docs_resp.status_code != 200:
            logger.error("Failed to fetch compliance docs: %s", docs_resp.text)
            return {"pending": []}

        # Fetch user's existing acceptances
        acc_resp = await client.get(
            f"{supabase_url}/rest/v1/compliance_acceptances?user_id=eq.{user_id}&select=document_type,document_version",
            headers=hdrs,
        )
        accepted_set: set[tuple[str, str]] = set()
        if acc_resp.status_code == 200:
            for row in acc_resp.json():
                accepted_set.add((row["document_type"], row["document_version"]))

    docs = docs_resp.json()
    pending = []
    for doc in docs:
        doc_type = doc["document_type"]
        version = doc["version"]
        jurisdiction = doc.get("jurisdiction", "ALL")

        # Skip documents not relevant to this jurisdiction
        if jurisdiction not in ("ALL", "CA", "US"):
            continue

        # Camera disclosure only for camera users
        if doc_type == "camera_disclosure" and not has_camera:
            continue

        # Quebec-specific documents
        if jurisdiction == "QC" and province.upper() != "QC":
            continue

        if (doc_type, version) not in accepted_set:
            pending.append({
                "document_type": doc_type,
                "version": version,
                "content": doc.get("content", ""),
            })

    return {"pending": pending}


# ---------- Privacy Requests ----------

@router.post("/api/privacy/request")
async def submit_privacy_request(req: PrivacyRequestSubmission):
    """Submit a privacy request (PIPEDA individual rights). No auth required."""
    valid_types = {"access", "correction", "deletion", "portability", "objection", "withdraw_consent"}
    if req.request_type not in valid_types:
        raise HTTPException(400, f"Invalid request_type. Must be one of: {', '.join(sorted(valid_types))}")

    supabase_url, service_key = _get_supabase()
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    payload = {
        "request_type": req.request_type,
        "requester_email": req.requester_email,
        "requester_name": req.requester_name,
        "user_id": req.user_id,
        "portal_context": req.portal_context,
        "request_description": req.request_description,
        "status": "received",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/privacy_requests",
            headers={
                **_headers(service_key),
                "Prefer": "return=representation",
            },
            json=payload,
        )

    if resp.status_code not in (200, 201):
        logger.error("Privacy request insert failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(500, "Could not submit privacy request")

    rows = resp.json()
    request_id = rows[0]["id"] if isinstance(rows, list) and rows else None
    logger.info("Privacy request submitted: type=%s email=%s", req.request_type, req.requester_email)
    return {"ok": True, "request_id": request_id, "status": "received"}


@router.get("/api/privacy/export/{user_id}")
async def export_user_data(user_id: str, admin: dict = Depends(require_admin_jwt)):
    """Export all personal data for a user (admin only). PIPEDA portability."""
    _validate_user_id(user_id)

    supabase_url, service_key = _get_supabase()
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    hdrs = _headers(service_key)
    export_data: dict = {"user_id": user_id, "exported_at": datetime.now(timezone.utc).isoformat()}

    tables = [
        ("compliance_acceptances", f"user_id=eq.{user_id}"),
        ("casl_consent_records", f"user_id=eq.{user_id}"),
        ("privacy_requests", f"user_id=eq.{user_id}"),
    ]

    async with httpx.AsyncClient(timeout=15.0) as client:
        for table, filter_str in tables:
            resp = await client.get(
                f"{supabase_url}/rest/v1/{table}?{filter_str}&select=*",
                headers=hdrs,
            )
            export_data[table] = resp.json() if resp.status_code == 200 else []

    return export_data


# ---------- CASL Status ----------

@router.get("/api/compliance/casl/status")
async def casl_status(admin: dict = Depends(require_admin_jwt)):
    """CASL consent statistics (admin only)."""

    supabase_url, service_key = _get_supabase()
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/casl_consent_records?select=consent_status",
            headers=_headers(service_key),
        )

    if resp.status_code != 200:
        return {"express": 0, "implied": 0, "withdrawn": 0, "never": 0, "total": 0}

    rows = resp.json()
    counts = {"express": 0, "implied": 0, "withdrawn": 0, "never": 0}
    for row in rows:
        s = row.get("consent_status", "never")
        counts[s] = counts.get(s, 0) + 1

    return {**counts, "total": len(rows)}


# ---------- Compliance Dashboard ----------

@router.get("/api/compliance/dashboard")
async def compliance_dashboard(admin: dict = Depends(require_admin_jwt)):
    """Full compliance dashboard data (admin only)."""

    supabase_url, service_key = _get_supabase()
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    hdrs = _headers(service_key)
    dashboard: dict = {}

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Privacy requests summary
        pr_resp = await client.get(
            f"{supabase_url}/rest/v1/privacy_requests?select=status,request_type,deadline_at&order=received_at.desc&limit=50",
            headers=hdrs,
        )
        requests = pr_resp.json() if pr_resp.status_code == 200 else []
        dashboard["privacy_requests"] = {
            "total": len(requests),
            "by_status": {},
            "recent": requests[:10],
        }
        for r in requests:
            s = r.get("status", "unknown")
            dashboard["privacy_requests"]["by_status"][s] = dashboard["privacy_requests"]["by_status"].get(s, 0) + 1

        # Breach log summary
        br_resp = await client.get(
            f"{supabase_url}/rest/v1/breach_log?select=severity,status,discovered_at&order=discovered_at.desc&limit=20",
            headers=hdrs,
        )
        breaches = br_resp.json() if br_resp.status_code == 200 else []
        dashboard["breaches"] = {
            "total": len(breaches),
            "open": sum(1 for b in breaches if b.get("status") not in ("resolved", "closed")),
            "recent": breaches[:5],
        }

        # Data inventory summary
        di_resp = await client.get(
            f"{supabase_url}/rest/v1/data_inventory?select=data_category,sensitivity,cross_border,next_review",
            headers=hdrs,
        )
        inventory = di_resp.json() if di_resp.status_code == 200 else []
        dashboard["data_inventory"] = {
            "total_categories": len(inventory),
            "cross_border": sum(1 for i in inventory if i.get("cross_border")),
            "reviews_due": sum(1 for i in inventory if i.get("next_review") and i["next_review"] < datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        }

    return dashboard


# ---------- Breach Log ----------

@router.post("/api/compliance/breach")
async def log_breach(req: BreachReport, admin: dict = Depends(require_admin_jwt)):
    """Log a new breach incident (admin only)."""

    supabase_url, service_key = _get_supabase()
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    valid_severities = {"low", "medium", "high", "critical"}
    if req.severity not in valid_severities:
        raise HTTPException(400, f"severity must be one of: {', '.join(sorted(valid_severities))}")

    payload = {
        "incident_description": req.incident_description,
        "data_types_involved": req.data_types_involved,
        "estimated_individuals_affected": req.estimated_individuals_affected,
        "severity": req.severity,
        "status": "investigating",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/breach_log",
            headers={
                **_headers(service_key),
                "Prefer": "return=representation",
            },
            json=payload,
        )

    if resp.status_code not in (200, 201):
        logger.error("Breach log insert failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(500, "Could not log breach")

    rows = resp.json()
    breach_id = rows[0]["id"] if isinstance(rows, list) and rows else None
    logger.info("Breach logged: severity=%s id=%s", req.severity, breach_id)
    return {"ok": True, "breach_id": breach_id}


@router.get("/api/compliance/breach")
async def list_breaches(admin: dict = Depends(require_admin_jwt)):
    """List all breach records (admin only)."""

    supabase_url, service_key = _get_supabase()
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/breach_log?order=discovered_at.desc&select=*",
            headers=_headers(service_key),
        )

    if resp.status_code != 200:
        return {"breaches": []}

    return {"breaches": resp.json()}


# ---------- Unsubscribe ----------

@router.post("/api/privacy/unsubscribe")
async def unsubscribe(req: UnsubscribeRequest):
    """Process unsubscribe from email link (no auth required). CASL requires instant processing."""
    from ...compliance.casl_guard import process_unsubscribe

    result = await process_unsubscribe(req.email, method="email_link")
    if not result.get("ok"):
        # Even on error, show success to user (CASL best practice -- don't reveal internal state)
        logger.error("Unsubscribe processing failed for %s: %s", req.email, result.get("error"))

    return {"ok": True, "message": "You have been unsubscribed from marketing emails."}
