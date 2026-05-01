import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger("meridian.ai.alerts")


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    URGENT = "urgent"


class BaseAlert(ABC):
    name: str = "base_alert"
    description: str = ""
    cooldown_hours: int = 24

    def __init__(self, ctx, agent_outputs: dict | None = None):
        self.ctx = ctx
        self.agent_outputs = agent_outputs or getattr(ctx, "agent_outputs", {})
        self._fired: list[dict] = []

    @abstractmethod
    async def evaluate(self) -> list[dict]:
        """Return list of alert dicts, or empty list if no alerts."""
        ...

    def fire(
        self,
        severity: AlertSeverity,
        title: str,
        detail: str,
        metric_value: float | None = None,
        threshold: float | None = None,
        impact_cents: int = 0,
        metadata: dict | None = None,
    ) -> dict:
        alert = {
            "alert_name": self.name,
            "severity": severity.value,
            "title": title,
            "detail": detail,
            "metric_value": metric_value,
            "threshold": threshold,
            "impact_cents": impact_cents,
            "metadata": metadata or {},
            "fired_at": datetime.now(timezone.utc).isoformat(),
        }
        self._fired.append(alert)
        logger.info(f"Alert fired: [{severity.value}] {self.name}: {title}")
        return alert

    def no_alerts(self) -> list[dict]:
        return []
