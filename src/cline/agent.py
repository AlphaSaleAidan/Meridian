"""Cline self-healing IT agent — diagnose, remediate, chat.

Uses the Karpathy 5-phase reasoning loop (THINK → HYPOTHESIZE →
EXPERIMENT → SYNTHESIZE → REFLECT) adapted for IT diagnosis:
  THINK    → Gather error context, system state, recent changes
  PLAN     → Generate remediation hypotheses ranked by safety
  ACT      → Execute safest viable fix (Level 1-2 auto, 3-4 escalate)
  OBSERVE  → Verify fix worked, check for regressions
  REFLECT  → Confidence rating, log chain, update merchant_health
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Optional

from ..ai.reasoning import KarpathyReasoning, ReasoningChain

logger = logging.getLogger("meridian.cline")


class RemediationLevel(IntEnum):
    """Remediation severity — Level 1-2 auto, 3-4 require human approval."""
    RETRY = 1       # retry_sync, clear_cache, restart_agent, reset_session
    RECONFIGURE = 2 # update_config, rerun_pipeline, fix_data_record
    ESCALATE = 3    # create_github_issue, notify_it_team
    INCIDENT = 4    # page_oncall, create_incident


@dataclass
class ClineDiagnosis:
    """Output of the Cline diagnostic reasoning loop."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error_type: str = ""
    root_cause: str = ""
    remediation_level: int = 1
    action_plan: list[dict] = field(default_factory=list)
    reasoning_chain: Optional[ReasoningChain] = None
    confidence: float = 0.5
    requires_approval: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "error_type": self.error_type,
            "root_cause": self.root_cause,
            "remediation_level": self.remediation_level,
            "action_plan": self.action_plan,
            "confidence": self.confidence,
            "requires_approval": self.requires_approval,
            "reasoning": self.reasoning_chain.to_dict() if self.reasoning_chain else None,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class RemediationResult:
    """Result of an auto-remediation attempt."""
    diagnosis_id: str = ""
    actions_taken: list[dict] = field(default_factory=list)
    success: bool = False
    rolled_back: bool = False
    message: str = ""
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "diagnosis_id": self.diagnosis_id,
            "actions_taken": self.actions_taken,
            "success": self.success,
            "rolled_back": self.rolled_back,
            "message": self.message,
            "duration_ms": self.duration_ms,
        }


class ClineAgent:
    """Self-healing IT agent. Diagnoses errors, auto-remediates safe issues,
    escalates dangerous ones, and chats with business owners about system health."""

    def __init__(self, db=None):
        self.db = db
        self.reasoning = KarpathyReasoning()

    async def diagnose(
        self,
        error_context: dict[str, Any],
        user_message: str = "",
    ) -> ClineDiagnosis:
        """Run 5-phase diagnostic reasoning on an error or system issue.

        Args:
            error_context: Dict with keys like error_type, message, agent_name,
                          business_id, stack_trace, recent_events, system_state.
            user_message: Optional natural language from the business owner.
        """
        ctx = self._build_diagnostic_context(error_context, user_message)
        chain = await self.reasoning.reason(
            agent_name="cline_it",
            domain="system_health",
            context=ctx,
        )

        diagnosis = self._chain_to_diagnosis(chain, error_context)

        if self.db:
            await self._persist_diagnosis(diagnosis, error_context)

        return diagnosis

    async def auto_remediate(self, diagnosis: ClineDiagnosis) -> RemediationResult:
        """Execute remediation plan. Level 1-2 auto-execute, 3-4 escalate."""
        from .remediator import Remediator

        remediator = Remediator(db=self.db)

        if diagnosis.remediation_level >= RemediationLevel.ESCALATE:
            logger.info(
                "Diagnosis %s requires Level %d — escalating (not auto-remediating)",
                diagnosis.id, diagnosis.remediation_level,
            )
            result = await remediator.escalate(diagnosis)
            return result

        result = await remediator.execute(diagnosis)

        if not result.success and not result.rolled_back:
            logger.warning("Remediation failed for %s — attempting rollback", diagnosis.id)
            await remediator.rollback(diagnosis, result)
            result.rolled_back = True

        if self.db:
            await self._persist_remediation(diagnosis, result)

        return result

    async def chat(
        self,
        conversation_id: str,
        user_message: str,
        org_id: str = "",
    ) -> str:
        """Natural language chat with a business owner about system health.

        Fetches recent errors, health scores, and agent status to provide
        context-aware responses.
        """
        health = await self._get_org_health(org_id) if org_id else {}
        recent_errors = await self._get_recent_errors(org_id) if org_id else []

        error_summary = "No recent errors." if not recent_errors else (
            f"{len(recent_errors)} recent issue(s): "
            + "; ".join(e.get("message", "unknown")[:60] for e in recent_errors[:3])
        )

        health_score = health.get("overall_score", "unknown")
        health_trend = health.get("trend", "stable")

        response_parts = []

        msg_lower = user_message.lower()
        if any(w in msg_lower for w in ("status", "health", "how", "working")):
            response_parts.append(
                f"System health score: {health_score}/100 (trend: {health_trend}). "
                f"{error_summary}"
            )
        elif any(w in msg_lower for w in ("error", "issue", "problem", "broken", "fail")):
            if recent_errors:
                top = recent_errors[0]
                response_parts.append(
                    f"Most recent issue ({top.get('error_type', 'unknown')}): "
                    f"{top.get('message', 'No details')}. "
                    f"Status: {top.get('status', 'investigating')}."
                )
            else:
                response_parts.append("No active errors detected. All systems operational.")
        elif any(w in msg_lower for w in ("fix", "resolve", "remediate")):
            response_parts.append(
                "I can attempt auto-remediation for Level 1-2 issues (retries, cache clears, "
                "config resets). Level 3-4 issues are escalated to the engineering team. "
                "Would you like me to check for fixable issues?"
            )
        else:
            response_parts.append(
                f"I'm Cline, your IT health assistant. System score: {health_score}/100. "
                f"{error_summary} Ask me about errors, health status, or request a fix."
            )

        if self.db and org_id:
            await self._persist_chat_message(conversation_id, org_id, user_message, "user")
            response = " ".join(response_parts)
            await self._persist_chat_message(conversation_id, org_id, response, "agent")
            return response

        return " ".join(response_parts)

    def _build_diagnostic_context(self, error_ctx: dict, user_msg: str) -> dict:
        """Transform error context into the format expected by KarpathyReasoning."""
        transactions = []
        daily_revenue = []

        if "recent_events" in error_ctx:
            for event in error_ctx["recent_events"][:50]:
                daily_revenue.append({
                    "date": event.get("timestamp", ""),
                    "revenue_cents": 1 if event.get("status") == "success" else 0,
                })

        return {
            "transactions": transactions,
            "daily_revenue": daily_revenue,
            "product_performance": [],
            "products": [],
            "inventory": [],
            "employees": [],
            "hourly_revenue": [],
            "business_vertical": "system_health",
            "_error_context": error_ctx,
            "_user_message": user_msg,
        }

    def _chain_to_diagnosis(self, chain: ReasoningChain, error_ctx: dict) -> ClineDiagnosis:
        """Convert a reasoning chain into a ClineDiagnosis."""
        error_type = error_ctx.get("error_type", "unknown")
        level = self._classify_severity(error_type, error_ctx, chain)

        action_plan = []
        for finding in chain.findings:
            action_plan.append({
                "action": finding.get("action", "investigate"),
                "urgency": finding.get("urgency", "LOW"),
                "confidence": finding.get("confidence", 0.5),
            })

        if not action_plan:
            action_plan.append({
                "action": "monitor_and_retry",
                "urgency": "LOW",
                "confidence": 0.5,
            })

        return ClineDiagnosis(
            error_type=error_type,
            root_cause=chain.findings[0].get("insight", "Unknown") if chain.findings else "Unknown",
            remediation_level=level,
            action_plan=action_plan,
            reasoning_chain=chain,
            confidence=chain.confidence,
            requires_approval=level >= RemediationLevel.ESCALATE,
        )

    def _classify_severity(self, error_type: str, ctx: dict, chain: ReasoningChain) -> int:
        """Classify error into remediation level 1-4."""
        level_1_types = {"sync_stale", "cache_miss", "agent_timeout", "session_expired", "retry_failed"}
        level_2_types = {"config_error", "pipeline_stuck", "data_inconsistency", "schema_drift"}
        level_3_types = {"integration_failure", "api_degradation", "auth_error", "webhook_dead"}
        level_4_types = {"data_loss", "security_breach", "total_outage", "billing_error"}

        if error_type in level_4_types:
            return RemediationLevel.INCIDENT
        if error_type in level_3_types:
            return RemediationLevel.ESCALATE
        if error_type in level_2_types:
            return RemediationLevel.RECONFIGURE
        if error_type in level_1_types:
            return RemediationLevel.RETRY

        failure_count = ctx.get("failure_count", 0)
        if failure_count >= 10:
            return RemediationLevel.ESCALATE
        if failure_count >= 3:
            return RemediationLevel.RECONFIGURE
        return RemediationLevel.RETRY

    async def _get_org_health(self, org_id: str) -> dict:
        """Fetch latest merchant health scores."""
        if not self.db:
            return {"overall_score": 85, "trend": "stable"}
        try:
            resp = await self.db.table("merchant_health").select("*").eq(
                "business_id", org_id
            ).order("measured_at", desc=True).limit(1).execute()
            if resp.data:
                row = resp.data[0]
                return {"overall_score": row["score"], "trend": row.get("trend", "stable")}
        except Exception as e:
            logger.warning("Failed to fetch merchant health: %s", e)
        return {"overall_score": 0, "trend": "unknown"}

    async def _get_recent_errors(self, org_id: str) -> list[dict]:
        """Fetch recent cline errors for an org."""
        if not self.db:
            return []
        try:
            resp = await self.db.table("cline_errors").select("*").eq(
                "business_id", org_id
            ).order("created_at", desc=True).limit(10).execute()
            return resp.data or []
        except Exception as e:
            logger.warning("Failed to fetch cline errors: %s", e)
            return []

    async def _persist_diagnosis(self, diagnosis: ClineDiagnosis, error_ctx: dict):
        """Store diagnosis and reasoning chain in DB."""
        try:
            chain = diagnosis.reasoning_chain
            await self.db.table("agent_reasoning_chains").insert({
                "id": diagnosis.id,
                "business_id": error_ctx.get("business_id", ""),
                "agent_name": "cline_it",
                "domain": "system_health",
                "trigger": "error_detected",
                "phases": [s.content for s in chain.steps] if chain else [],
                "final_confidence": diagnosis.confidence,
                "confidence_level": chain.confidence_level if chain else "LOW",
                "verdict": chain.verdict if chain else "monitoring",
                "impact_cents": 0,
                "caveats": chain.caveats if chain else [],
                "total_duration_ms": chain.total_duration_ms if chain else 0,
                "started_at": chain.started_at.isoformat() if chain and chain.started_at else None,
                "completed_at": chain.completed_at.isoformat() if chain and chain.completed_at else None,
            }).execute()
        except Exception as e:
            logger.error("Failed to persist diagnosis: %s", e)

    async def _persist_remediation(self, diagnosis: ClineDiagnosis, result: RemediationResult):
        """Store remediation result in DB."""
        try:
            await self.db.table("cline_messages").insert({
                "conversation_id": diagnosis.id,
                "role": "system",
                "phase": "reflect",
                "content": result.message,
                "data": result.to_dict(),
            }).execute()
        except Exception as e:
            logger.error("Failed to persist remediation result: %s", e)

    async def _persist_chat_message(self, conv_id: str, org_id: str, content: str, role: str):
        """Store a chat message in cline_conversations/cline_messages."""
        try:
            existing = await self.db.table("cline_conversations").select("id").eq(
                "id", conv_id
            ).limit(1).execute()
            if not existing.data:
                await self.db.table("cline_conversations").insert({
                    "id": conv_id,
                    "business_id": org_id,
                    "agent_name": "cline_chat",
                    "status": "active",
                    "context": {},
                }).execute()

            await self.db.table("cline_messages").insert({
                "conversation_id": conv_id,
                "role": role,
                "content": content,
            }).execute()
        except Exception as e:
            logger.error("Failed to persist chat message: %s", e)
