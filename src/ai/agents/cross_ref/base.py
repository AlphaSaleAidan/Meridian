"""
Base Cross-Reference Agent — Foundation for camera + POS fusion agents.

Extends BaseAgent with cross-reference data access and emit_finding()
for inter-agent communication. Each cross-ref agent receives a
CrossRefContext with correlated journey + transaction data.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..base import BaseAgent

logger = logging.getLogger("meridian.ai.agents.cross_ref")

_shared_findings: list[dict] = []


@dataclass
class CrossRefContext:
    org_id: str
    journeys: list[dict] = field(default_factory=list)
    transactions: list[dict] = field(default_factory=list)
    zone_correlations: list[dict] = field(default_factory=list)
    vision_traffic: list[dict] = field(default_factory=list)
    vision_visitors: list[dict] = field(default_factory=list)
    vision_visits: list[dict] = field(default_factory=list)
    staff_positions: list[dict] = field(default_factory=list)
    skeletal_data: list[dict] = field(default_factory=list)
    analysis_days: int = 30
    business_vertical: str = "other"
    agent_outputs: dict = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseCrossRefAgent(BaseAgent):
    name = "cross_ref_base"
    description = ""
    tier = 3
    domain = "cross_reference"

    def __init__(self, ctx: CrossRefContext):
        self.ctx = ctx
        self._data_avail = None
        self._chain = None
        from ...agent_logger import get_agent_logger
        self._json_logger = get_agent_logger(self.__class__.__name__)

    @property
    def journeys(self) -> list[dict]:
        return self.ctx.journeys

    @property
    def converted_journeys(self) -> list[dict]:
        return [j for j in self.journeys if j.get("converted")]

    @property
    def unconverted_journeys(self) -> list[dict]:
        return [j for j in self.journeys if not j.get("converted")]

    def emit_finding(self, finding_type: str, detail: str, data: dict | None = None, severity: str = "info"):
        """Publish a finding visible to all cross-ref agents."""
        finding = {
            "source_agent": self.name,
            "type": finding_type,
            "detail": detail,
            "severity": severity,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _shared_findings.append(finding)
        self._json_logger.info(
            f"Finding: {finding_type}",
            extra={"event": "finding_emitted", "context": finding},
        )

    def get_findings(self, source: str | None = None) -> list[dict]:
        """Read findings from other agents."""
        if source:
            return [f for f in _shared_findings if f["source_agent"] == source]
        return list(_shared_findings)

    @staticmethod
    def clear_findings():
        _shared_findings.clear()

    def _zone_dwell_avg(self, zone_name: str) -> float:
        """Average dwell time in a specific zone across all journeys."""
        dwells = []
        for j in self.journeys:
            for stop in j.get("zone_stops", []):
                if stop.get("zone_name") == zone_name:
                    dwells.append(stop.get("dwell_seconds", 0))
        return sum(dwells) / max(len(dwells), 1)

    def _conversion_rate(self) -> float:
        total = len(self.journeys)
        if total == 0:
            return 0.0
        return len(self.converted_journeys) / total

    def _avg_basket_cents(self) -> int:
        totals = [j["transaction_total_cents"] for j in self.converted_journeys if j.get("transaction_total_cents")]
        if not totals:
            return 0
        return int(sum(totals) / len(totals))
