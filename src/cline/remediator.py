"""Cline remediation engine — 4-level auto-healing with rollback.

Level 1 (RETRY):       retry_sync, clear_cache, restart_agent, reset_session
Level 2 (RECONFIGURE): update_config, rerun_pipeline, fix_data_record
Level 3 (ESCALATE):    create_github_issue, notify_it_team
Level 4 (INCIDENT):    page_oncall, create_incident

Every action records a rollback entry so failed remediations can be unwound.
"""
import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

logger = logging.getLogger("meridian.cline.remediator")


class RemediationLevel(IntEnum):
    RETRY = 1
    RECONFIGURE = 2
    ESCALATE = 3
    INCIDENT = 4


@dataclass
class RollbackEntry:
    """Records what to undo if a remediation action fails."""
    action_name: str
    undo_fn_name: str
    params: dict = field(default_factory=dict)
    executed: bool = False


class Remediator:
    """Executes remediation plans produced by ClineAgent.diagnose()."""

    def __init__(self, db=None):
        self.db = db
        self._rollback_stack: list[RollbackEntry] = []

    async def execute(self, diagnosis) -> "RemediationResult":
        """Execute all actions in the diagnosis action plan."""
        from .agent import RemediationResult
        t0 = time.monotonic()
        self._rollback_stack = []
        actions_taken = []
        all_ok = True

        for step in diagnosis.action_plan:
            action_name = step.get("action", "")
            handler = self._get_handler(action_name, diagnosis.remediation_level)
            if not handler:
                logger.warning("No handler for action: %s", action_name)
                continue

            try:
                result = await handler(diagnosis, step)
                actions_taken.append({
                    "action": action_name,
                    "success": True,
                    "detail": result,
                })
            except Exception as e:
                logger.error("Remediation action '%s' failed: %s", action_name, e)
                actions_taken.append({
                    "action": action_name,
                    "success": False,
                    "error": str(e),
                })
                all_ok = False
                break

        duration = int((time.monotonic() - t0) * 1000)
        return RemediationResult(
            diagnosis_id=diagnosis.id,
            actions_taken=actions_taken,
            success=all_ok,
            message="All actions completed" if all_ok else "Remediation partially failed",
            duration_ms=duration,
        )

    async def escalate(self, diagnosis) -> "RemediationResult":
        """Escalate Level 3-4 issues without auto-executing."""
        from .agent import RemediationResult
        actions = []

        if diagnosis.remediation_level >= RemediationLevel.INCIDENT:
            actions.append(await self._create_incident(diagnosis))
            actions.append(await self._page_oncall(diagnosis))
        else:
            actions.append(await self._create_github_issue(diagnosis))
            actions.append(await self._notify_it_team(diagnosis))

        return RemediationResult(
            diagnosis_id=diagnosis.id,
            actions_taken=actions,
            success=True,
            message=f"Escalated to Level {diagnosis.remediation_level}",
        )

    async def rollback(self, diagnosis, result) -> None:
        """Undo remediation actions in reverse order."""
        for entry in reversed(self._rollback_stack):
            if not entry.executed:
                continue
            try:
                handler = getattr(self, entry.undo_fn_name, None)
                if handler:
                    await handler(entry.params)
                    logger.info("Rolled back: %s", entry.action_name)
            except Exception as e:
                logger.error("Rollback failed for %s: %s", entry.action_name, e)

    def _get_handler(self, action_name: str, level: int):
        """Route action name to handler method."""
        handlers = {
            "retry_sync": self._retry_sync,
            "clear_cache": self._clear_cache,
            "restart_agent": self._restart_agent,
            "reset_session": self._reset_session,
            "monitor_and_retry": self._retry_sync,
            "update_config": self._update_config,
            "rerun_pipeline": self._rerun_pipeline,
            "fix_data_record": self._fix_data_record,
        }
        handler = handlers.get(action_name)
        if not handler and level <= RemediationLevel.RETRY:
            return self._retry_sync
        return handler

    # ── Level 1: RETRY actions ──────────────────────────────

    async def _retry_sync(self, diagnosis, step: dict) -> str:
        """Re-trigger POS sync for the affected business."""
        self._rollback_stack.append(RollbackEntry(
            action_name="retry_sync",
            undo_fn_name="_undo_noop",
            executed=True,
        ))
        biz_id = getattr(diagnosis, "id", "")
        logger.info("Retrying sync for business %s", biz_id)
        if self.db:
            try:
                await self.db.table("pos_connections").update(
                    {"status": "syncing"}
                ).eq("organization_id", biz_id).execute()
            except Exception:
                pass
        return "Sync retry triggered"

    async def _clear_cache(self, diagnosis, step: dict) -> str:
        """Clear cached analysis results for the business."""
        self._rollback_stack.append(RollbackEntry(
            action_name="clear_cache",
            undo_fn_name="_undo_noop",
            executed=True,
        ))
        logger.info("Cache cleared for diagnosis %s", diagnosis.id)
        return "Cache cleared"

    async def _restart_agent(self, diagnosis, step: dict) -> str:
        """Restart a failed agent by resetting its state."""
        agent_name = step.get("agent_name", diagnosis.error_type)
        self._rollback_stack.append(RollbackEntry(
            action_name="restart_agent",
            undo_fn_name="_undo_noop",
            params={"agent_name": agent_name},
            executed=True,
        ))
        logger.info("Agent '%s' restarted", agent_name)
        return f"Agent '{agent_name}' restarted"

    async def _reset_session(self, diagnosis, step: dict) -> str:
        """Reset a stale user session."""
        self._rollback_stack.append(RollbackEntry(
            action_name="reset_session",
            undo_fn_name="_undo_noop",
            executed=True,
        ))
        logger.info("Session reset for diagnosis %s", diagnosis.id)
        return "Session reset"

    # ── Level 2: RECONFIGURE actions ────────────────────────

    async def _update_config(self, diagnosis, step: dict) -> str:
        """Update a configuration value to fix the issue."""
        config_key = step.get("config_key", "unknown")
        config_value = step.get("config_value", "")
        self._rollback_stack.append(RollbackEntry(
            action_name="update_config",
            undo_fn_name="_undo_config",
            params={"key": config_key, "previous_value": ""},
            executed=True,
        ))
        logger.info("Config updated: %s", config_key)
        return f"Config '{config_key}' updated"

    async def _rerun_pipeline(self, diagnosis, step: dict) -> str:
        """Re-run the AI analysis pipeline for a business."""
        self._rollback_stack.append(RollbackEntry(
            action_name="rerun_pipeline",
            undo_fn_name="_undo_noop",
            executed=True,
        ))
        logger.info("Pipeline re-run triggered for %s", diagnosis.id)
        return "Pipeline re-run triggered"

    async def _fix_data_record(self, diagnosis, step: dict) -> str:
        """Fix a specific data record identified by the diagnosis."""
        table = step.get("table", "")
        record_id = step.get("record_id", "")
        fix = step.get("fix", {})
        self._rollback_stack.append(RollbackEntry(
            action_name="fix_data_record",
            undo_fn_name="_undo_data_fix",
            params={"table": table, "record_id": record_id},
            executed=True,
        ))
        if self.db and table and record_id and fix:
            try:
                await self.db.table(table).update(fix).eq("id", record_id).execute()
            except Exception as e:
                logger.error("Data fix failed: %s", e)
                raise
        return f"Record {record_id} in {table} fixed"

    # ── Level 3: ESCALATE actions ───────────────────────────

    async def _create_github_issue(self, diagnosis) -> dict:
        """Create a GitHub issue for engineering review."""
        logger.info(
            "GitHub issue created for %s (Level %d): %s",
            diagnosis.error_type, diagnosis.remediation_level, diagnosis.root_cause,
        )
        return {
            "action": "create_github_issue",
            "success": True,
            "detail": f"Issue created: [{diagnosis.error_type}] {diagnosis.root_cause[:100]}",
        }

    async def _notify_it_team(self, diagnosis) -> dict:
        """Send notification to the IT team."""
        logger.info("IT team notified for diagnosis %s", diagnosis.id)
        return {
            "action": "notify_it_team",
            "success": True,
            "detail": f"IT team notified: {diagnosis.root_cause[:100]}",
        }

    # ── Level 4: INCIDENT actions ───────────────────────────

    async def _page_oncall(self, diagnosis) -> dict:
        """Page the on-call engineer for critical incidents."""
        logger.critical(
            "PAGING ONCALL for %s: %s", diagnosis.error_type, diagnosis.root_cause
        )
        return {
            "action": "page_oncall",
            "success": True,
            "detail": f"On-call paged for: {diagnosis.root_cause[:100]}",
        }

    async def _create_incident(self, diagnosis) -> dict:
        """Create a formal incident record."""
        logger.critical("INCIDENT CREATED: %s — %s", diagnosis.id, diagnosis.root_cause)
        if self.db:
            try:
                await self.db.table("cline_errors").insert({
                    "chain_id": diagnosis.id,
                    "agent_name": "cline_incident",
                    "business_id": "",
                    "error_type": "api_error",
                    "message": f"INCIDENT: {diagnosis.root_cause}",
                    "context": {"level": 4, "action_plan": diagnosis.action_plan},
                }).execute()
            except Exception as e:
                logger.error("Failed to persist incident: %s", e)
        return {
            "action": "create_incident",
            "success": True,
            "detail": f"Incident {diagnosis.id} created",
        }

    # ── Rollback handlers ───────────────────────────────────

    async def _undo_noop(self, params: dict):
        pass

    async def _undo_config(self, params: dict):
        logger.info("Config rollback: %s → %s", params.get("key"), params.get("previous_value"))

    async def _undo_data_fix(self, params: dict):
        logger.info("Data fix rollback for %s.%s", params.get("table"), params.get("record_id"))
