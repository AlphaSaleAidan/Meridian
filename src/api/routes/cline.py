"""Cline self-healing agent API routes.

Endpoints:
  POST /api/cline/chat               → Chat with Cline about system health
  POST /api/cline/report-error        → Report a frontend error
  GET  /api/cline/conversations/{id}  → Get conversation history
  GET  /api/cline/health/{org_id}     → Get org health summary
  GET  /api/cline/errors/{org_id}     → Get recent errors for org
  GET  /api/admin/it-dashboard        → IT overview across all orgs
"""
import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger("meridian.api.cline")

router = APIRouter()


# ── Request / Response Models ────────────────────────────

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = Field(default=None, description="Existing conversation ID or null for new")
    org_id: str = Field(..., description="Organization ID")
    message: str = Field(..., min_length=1, max_length=2000)

class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    health_score: Optional[int] = None

class ErrorReport(BaseModel):
    org_id: str
    message: str = Field(..., max_length=500)
    stack_trace: Optional[str] = Field(default=None, max_length=2000)
    url: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[dict] = None

class ErrorReportResponse(BaseModel):
    error_id: str
    severity: int
    auto_remediation: bool
    message: str


# ── Helper: get DB + ClineAgent ──────────────────────────

async def _get_cline():
    from ...cline.agent import ClineAgent
    from ...db import _db_instance
    return ClineAgent(db=_db_instance)

async def _get_detector():
    from ...cline.error_detector import ErrorDetector
    from ...db import _db_instance
    return ErrorDetector(db=_db_instance)


# ── POST /api/cline/chat ─────────────────────────────────

@router.post("/api/cline/chat", response_model=ChatResponse)
async def cline_chat(req: ChatRequest):
    """Chat with the Cline IT agent about system health."""
    cline = await _get_cline()
    conv_id = req.conversation_id or str(uuid.uuid4())

    response = await cline.chat(
        conversation_id=conv_id,
        user_message=req.message,
        org_id=req.org_id,
    )

    health = await cline._get_org_health(req.org_id)

    return ChatResponse(
        conversation_id=conv_id,
        response=response,
        health_score=health.get("overall_score"),
    )


# ── POST /api/cline/report-error ─────────────────────────

@router.post("/api/cline/report-error", response_model=ErrorReportResponse)
async def report_error(req: ErrorReport):
    """Report a frontend error for Cline to analyze and potentially auto-fix."""
    detector = await _get_detector()

    detected = await detector.report_frontend_error(
        business_id=req.org_id,
        error_data={
            "message": req.message,
            "stack_trace": req.stack_trace or "",
            "url": req.url or "",
            "user_agent": req.user_agent or "",
        },
    )

    auto_remediate = detected.severity <= 1
    message = "Error logged"

    if auto_remediate:
        try:
            cline = await _get_cline()
            diagnosis = await cline.diagnose(detected.to_error_context())
            result = await cline.auto_remediate(diagnosis)
            message = result.message if result.success else "Auto-remediation attempted but failed"
        except Exception as e:
            logger.error("Auto-remediation failed: %s", e)
            message = "Error logged — auto-remediation failed"
            auto_remediate = False

    return ErrorReportResponse(
        error_id=str(uuid.uuid4()),
        severity=detected.severity,
        auto_remediation=auto_remediate,
        message=message,
    )


# ── GET /api/cline/conversations/{org_id} ─────────────────

@router.get("/api/cline/conversations/{org_id}")
async def get_conversations(org_id: str, limit: int = 20):
    """Get recent Cline conversations for an organization."""
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        resp = await db.table("cline_conversations").select(
            "id, agent_name, status, started_at, ended_at"
        ).eq("business_id", org_id).order(
            "created_at", desc=True
        ).limit(limit).execute()

        conversations = resp.data or []

        for conv in conversations:
            msgs = await db.table("cline_messages").select(
                "role, content, phase, created_at"
            ).eq("conversation_id", conv["id"]).order(
                "created_at"
            ).limit(50).execute()
            conv["messages"] = msgs.data or []

        return {"org_id": org_id, "conversations": conversations}
    except Exception as e:
        logger.error("Failed to fetch conversations: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch conversations")


# ── GET /api/cline/health/{org_id} ────────────────────────

@router.get("/api/cline/health/{org_id}")
async def get_health(org_id: str):
    """Get system health summary for an organization."""
    cline = await _get_cline()
    detector = await _get_detector()

    health = await cline._get_org_health(org_id)
    errors = await detector.scan_all(business_id=org_id)

    return {
        "org_id": org_id,
        "health_score": health.get("overall_score", 0),
        "trend": health.get("trend", "unknown"),
        "active_errors": len(errors),
        "errors": [
            {
                "type": e.error_type,
                "message": e.message,
                "severity": e.severity,
                "agent": e.agent_name,
                "detected_at": e.detected_at.isoformat(),
            }
            for e in errors[:10]
        ],
    }


# ── GET /api/cline/errors/{org_id} ────────────────────────

@router.get("/api/cline/errors/{org_id}")
async def get_errors(org_id: str, limit: int = 25):
    """Get recent Cline errors for an organization."""
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        resp = await db.table("cline_errors").select("*").eq(
            "business_id", org_id
        ).order("created_at", desc=True).limit(limit).execute()

        return {"org_id": org_id, "errors": resp.data or []}
    except Exception as e:
        logger.error("Failed to fetch errors: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch errors")


# ── GET /api/admin/it-dashboard ───────────────────────────

@router.get("/api/admin/it-dashboard")
async def it_dashboard():
    """IT dashboard — aggregated system health across all organizations.

    This endpoint bypasses org-level RLS (uses service role) to provide
    a global view for the engineering/IT team.
    """
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        health_resp = await db.table("merchant_health").select(
            "business_id, score, category, trend, measured_at"
        ).eq("category", "overall").order("measured_at", desc=True).limit(100).execute()

        errors_resp = await db.table("cline_errors").select(
            "agent_name, error_type, business_id, created_at"
        ).order("created_at", desc=True).limit(50).execute()

        chains_resp = await db.table("agent_reasoning_chains").select(
            "agent_name, verdict, final_confidence, error, created_at"
        ).order("created_at", desc=True).limit(50).execute()

        health_data = health_resp.data or []
        errors_data = errors_resp.data or []
        chains_data = chains_resp.data or []

        total_orgs = len(set(h["business_id"] for h in health_data))
        avg_score = (
            sum(h["score"] for h in health_data) / max(len(health_data), 1)
            if health_data else 0
        )
        declining = sum(1 for h in health_data if h.get("trend") == "declining")
        recent_errors = len(errors_data)
        failed_chains = sum(1 for c in chains_data if c.get("error"))

        return {
            "summary": {
                "total_organizations": total_orgs,
                "average_health_score": round(avg_score, 1),
                "declining_orgs": declining,
                "recent_errors_count": recent_errors,
                "failed_reasoning_chains": failed_chains,
            },
            "health_by_org": health_data[:20],
            "recent_errors": errors_data[:20],
            "recent_chains": chains_data[:20],
        }
    except Exception as e:
        logger.error("IT dashboard query failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to load IT dashboard")
