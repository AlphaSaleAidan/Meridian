"""Background error detection for the Cline self-healing agent.

Monitors:
  • Agent runs table for failures and timeouts
  • POS sync freshness (alert if > 6 hours stale)
  • Frontend error reports (scored by severity)
  • System health metrics

Triggers auto-remediation for Level 1 issues automatically.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("meridian.cline.detector")

SYNC_STALE_THRESHOLD_HOURS = 6
AGENT_FAILURE_THRESHOLD = 3
ERROR_RATE_THRESHOLD = 0.1  # 10% error rate triggers alert


@dataclass
class DetectedError:
    """An error discovered by the background detector."""
    error_type: str
    message: str
    severity: int  # 1-4 matching RemediationLevel
    business_id: str = ""
    agent_name: str = ""
    context: dict = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_error_context(self) -> dict:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "business_id": self.business_id,
            "agent_name": self.agent_name,
            "failure_count": self.context.get("failure_count", 1),
            "recent_events": self.context.get("recent_events", []),
            "detected_at": self.detected_at.isoformat(),
        }


class ErrorDetector:
    """Background error detector that scans for system issues."""

    def __init__(self, db=None):
        self.db = db

    async def scan_all(self, business_id: str = "") -> list[DetectedError]:
        """Run all detection checks. Returns list of detected errors."""
        errors: list[DetectedError] = []

        checks = [
            self.check_agent_failures,
            self.check_sync_freshness,
            self.check_error_rate,
            self.check_merchant_health,
        ]

        for check in checks:
            try:
                found = await check(business_id)
                errors.extend(found)
            except Exception as e:
                logger.error("Detection check %s failed: %s", check.__name__, e)

        errors.sort(key=lambda e: e.severity, reverse=True)
        return errors

    async def check_agent_failures(self, business_id: str = "") -> list[DetectedError]:
        """Check agent_reasoning_chains for recent failures."""
        errors: list[DetectedError] = []
        if not self.db:
            return errors

        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            query = self.db.table("agent_reasoning_chains").select(
                "agent_name, error, business_id, created_at"
            ).not_.is_("error", "null").gte("created_at", cutoff)

            if business_id:
                query = query.eq("business_id", business_id)

            resp = await query.limit(50).execute()

            failure_counts: dict[str, int] = {}
            for row in resp.data or []:
                key = f"{row['business_id']}:{row['agent_name']}"
                failure_counts[key] = failure_counts.get(key, 0) + 1

            for key, count in failure_counts.items():
                if count >= AGENT_FAILURE_THRESHOLD:
                    biz_id, agent = key.split(":", 1)
                    severity = 2 if count < 10 else 3
                    errors.append(DetectedError(
                        error_type="agent_timeout" if count < 5 else "integration_failure",
                        message=f"Agent '{agent}' failed {count} times in 24h",
                        severity=severity,
                        business_id=biz_id,
                        agent_name=agent,
                        context={"failure_count": count},
                    ))
        except Exception as e:
            logger.warning("Agent failure check failed: %s", e)

        return errors

    async def check_sync_freshness(self, business_id: str = "") -> list[DetectedError]:
        """Check if POS sync data is stale (> 6 hours since last sync)."""
        errors: list[DetectedError] = []
        if not self.db:
            return errors

        try:
            query = self.db.table("pos_connections").select(
                "organization_id, provider, last_sync_at, status"
            ).eq("status", "active")

            if business_id:
                query = query.eq("organization_id", business_id)

            resp = await query.execute()
            now = datetime.now(timezone.utc)

            for conn in resp.data or []:
                last_sync = conn.get("last_sync_at")
                if not last_sync:
                    errors.append(DetectedError(
                        error_type="sync_stale",
                        message=f"{conn['provider']} has never synced",
                        severity=2,
                        business_id=conn["organization_id"],
                        context={"provider": conn["provider"]},
                    ))
                    continue

                try:
                    sync_time = datetime.fromisoformat(last_sync.replace("Z", "+00:00"))
                    hours_stale = (now - sync_time).total_seconds() / 3600
                    if hours_stale > SYNC_STALE_THRESHOLD_HOURS:
                        severity = 1 if hours_stale < 12 else 2 if hours_stale < 24 else 3
                        errors.append(DetectedError(
                            error_type="sync_stale",
                            message=f"{conn['provider']} sync is {hours_stale:.1f}h stale",
                            severity=severity,
                            business_id=conn["organization_id"],
                            context={"hours_stale": round(hours_stale, 1), "provider": conn["provider"]},
                        ))
                except (ValueError, TypeError):
                    pass
        except Exception as e:
            logger.warning("Sync freshness check failed: %s", e)

        return errors

    async def check_error_rate(self, business_id: str = "") -> list[DetectedError]:
        """Check cline_errors table for high error rates."""
        errors: list[DetectedError] = []
        if not self.db:
            return errors

        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            query = self.db.table("cline_errors").select(
                "agent_name, business_id, error_type"
            ).gte("created_at", cutoff)

            if business_id:
                query = query.eq("business_id", business_id)

            resp = await query.limit(100).execute()
            count = len(resp.data or [])

            if count > 20:
                errors.append(DetectedError(
                    error_type="api_degradation",
                    message=f"High error rate: {count} errors in the last hour",
                    severity=3,
                    business_id=business_id,
                    context={"error_count_1h": count},
                ))
            elif count > 5:
                errors.append(DetectedError(
                    error_type="retry_failed",
                    message=f"Elevated error rate: {count} errors in the last hour",
                    severity=1,
                    business_id=business_id,
                    context={"error_count_1h": count},
                ))
        except Exception as e:
            logger.warning("Error rate check failed: %s", e)

        return errors

    async def check_merchant_health(self, business_id: str = "") -> list[DetectedError]:
        """Check merchant_health for declining scores."""
        errors: list[DetectedError] = []
        if not self.db:
            return errors

        try:
            query = self.db.table("merchant_health").select(
                "business_id, score, category, trend"
            ).eq("category", "overall").eq("trend", "declining")

            if business_id:
                query = query.eq("business_id", business_id)

            resp = await query.order("measured_at", desc=True).limit(20).execute()

            for row in resp.data or []:
                if row["score"] < 40:
                    errors.append(DetectedError(
                        error_type="data_inconsistency",
                        message=f"Merchant health critically low: {row['score']}/100 (declining)",
                        severity=2,
                        business_id=row["business_id"],
                        context={"health_score": row["score"], "trend": "declining"},
                    ))
        except Exception as e:
            logger.warning("Merchant health check failed: %s", e)

        return errors

    async def report_frontend_error(
        self,
        business_id: str,
        error_data: dict[str, Any],
    ) -> DetectedError:
        """Accept and score a frontend error report."""
        message = error_data.get("message", "Unknown frontend error")
        stack = error_data.get("stack_trace", "")
        url = error_data.get("url", "")
        user_agent = error_data.get("user_agent", "")

        severity = 1
        if any(kw in message.lower() for kw in ("chunk", "module", "import")):
            severity = 1  # JS bundle issue — retry/refresh fixes it
        elif any(kw in message.lower() for kw in ("auth", "token", "unauthorized", "403")):
            severity = 2  # Auth issue
        elif any(kw in message.lower() for kw in ("network", "fetch", "timeout", "500")):
            severity = 2  # API issue
        elif any(kw in message.lower() for kw in ("data", "undefined", "null", "type")):
            severity = 1  # Frontend data handling

        detected = DetectedError(
            error_type="cache_miss" if severity == 1 else "integration_failure",
            message=message[:500],
            severity=severity,
            business_id=business_id,
            context={
                "stack_trace": stack[:2000],
                "url": url,
                "user_agent": user_agent,
                "source": "frontend",
            },
        )

        if self.db:
            try:
                await self.db.table("cline_errors").insert({
                    "agent_name": "frontend",
                    "business_id": business_id,
                    "error_type": "data_error" if severity == 1 else "api_error",
                    "message": message[:500],
                    "stack_trace": stack[:2000],
                    "context": {"url": url, "user_agent": user_agent},
                }).execute()
            except Exception as e:
                logger.error("Failed to persist frontend error: %s", e)

        return detected
