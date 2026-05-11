"""
Cross-Reference Orchestrator — Real-time fusion of camera + POS data.

Coordinates PersonReIDService, JourneyTracker, and SkeletalTracker to
build customer journeys, then runs the 10 cross-reference analytics
agents on the fused data.

Can run in two modes:
  1. REAL-TIME — process_detections() + process_transaction() called per event
  2. BATCH — analyze_batch() runs agents on accumulated historical data
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from .reid.person_reid_service import PersonReIDService
from .reid.journey_tracker import JourneyTracker, SkeletalMoment
from .freemocap.skeletal_tracker import SkeletalTracker

logger = logging.getLogger("meridian.ai.cross_reference")


class CrossReferenceOrchestrator:

    def __init__(self, org_id: str, reid_config: str | None = None):
        self._org_id = org_id
        self._reid = PersonReIDService(model_config=reid_config)
        self._tracker = JourneyTracker(org_id=org_id)
        self._skeletal = SkeletalTracker()
        self._findings: list[dict] = []

    @property
    def reid_available(self) -> bool:
        return self._reid.has_reid

    @property
    def skeletal_available(self) -> bool:
        return self._skeletal.is_available

    @property
    def active_journeys(self) -> int:
        return self._tracker.active_count

    def process_detections(
        self,
        detections: list[dict[str, Any]],
        camera_id: str,
        frame=None,
    ) -> list[dict]:
        """Process camera detections through ReID and journey tracking."""
        sightings = self._reid.process_detections(detections, camera_id, frame)

        for s in sightings:
            self._tracker.process_sighting(s.person_id, s.camera_id, s.zone, s.timestamp)

            if self._skeletal.is_available and frame is not None:
                pose_result = self._skeletal.process_frame_for_person(frame, s.bbox)
                if pose_result:
                    moment = SkeletalMoment(
                        timestamp=s.timestamp,
                        pose_landmarks=pose_result["landmarks"],
                        gesture=pose_result.get("gesture"),
                        confidence=pose_result.get("gesture_confidence", 0),
                    )
                    self._tracker.add_skeletal_moment(s.person_id, moment)

        return [
            {
                "person_id": s.person_id,
                "camera_id": s.camera_id,
                "zone": s.zone,
                "confidence": s.confidence,
            }
            for s in sightings
        ]

    def process_transaction(self, txn_id: str, total_cents: int, txn_time: datetime | None = None) -> str | None:
        """Correlate a POS transaction to an active journey."""
        ts = txn_time or datetime.now(timezone.utc)
        journey_id = self._tracker.correlate_transaction(txn_id, total_cents, ts)
        return journey_id

    def flush(self) -> list[dict]:
        """Flush stale journeys and return them for persistence."""
        completed = self._tracker.flush_stale()
        return [j.to_dict() for j in completed]

    async def analyze_batch(
        self,
        journeys: list[dict] | None = None,
        transactions: list[dict] | None = None,
        vision_traffic: list[dict] | None = None,
        vision_visitors: list[dict] | None = None,
        vision_visits: list[dict] | None = None,
        skeletal_data: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Run all 10 cross-reference agents on accumulated data."""
        from .agents.cross_ref import ALL_CROSS_REF_AGENTS, CrossRefContext, BaseCrossRefAgent

        if journeys is None:
            active = self._tracker.get_active_journeys()
            completed = self._tracker.drain_completed()
            journeys = [j.to_dict() for j in active + completed]

        ctx = CrossRefContext(
            org_id=self._org_id,
            journeys=journeys,
            transactions=transactions or [],
            vision_traffic=vision_traffic or [],
            vision_visitors=vision_visitors or [],
            vision_visits=vision_visits or [],
            skeletal_data=skeletal_data or [],
        )

        BaseCrossRefAgent.clear_findings()

        use_reasoning = os.environ.get("MERIDIAN_REASONING", "1") == "1"
        agents = [cls(ctx) for cls in ALL_CROSS_REF_AGENTS]

        if use_reasoning:
            results = await asyncio.gather(
                *[a.analyze_with_reasoning() for a in agents],
                return_exceptions=True,
            )
        else:
            results = await asyncio.gather(
                *[a.analyze() for a in agents],
                return_exceptions=True,
            )

        outputs: dict[str, Any] = {}
        for agent, result in zip(agents, results):
            if isinstance(result, Exception):
                logger.error(f"Cross-ref agent {agent.name} failed: {result}")
                outputs[agent.name] = {"status": "error", "error": str(result)}
            else:
                outputs[agent.name] = result

        self._findings = BaseCrossRefAgent("").get_findings() if False else []
        try:
            self._findings = [f for f in BaseCrossRefAgent.clear_findings() or []]
        except Exception:
            self._findings = []

        succeeded = sum(
            1 for v in outputs.values()
            if isinstance(v, dict) and v.get("status") == "complete"
        )
        logger.info(f"Cross-reference analysis: {succeeded}/{len(agents)} agents succeeded")

        return outputs

    async def persist_journeys(self, journeys: list[dict]):
        """Save completed journeys to database."""
        try:
            from ..db import get_db
            db = get_db()
            for j in journeys:
                await db.insert("customer_journeys", {
                    "id": j["journey_id"],
                    "org_id": j["org_id"],
                    "person_id": j["person_id"],
                    "entry_time": j["entry_time"],
                    "exit_time": j.get("exit_time"),
                    "zone_stops": j.get("zone_stops", []),
                    "cameras_seen": j.get("cameras_seen", []),
                    "total_dwell_seconds": j.get("total_dwell_seconds", 0),
                    "transaction_id": j.get("transaction_id"),
                    "transaction_total_cents": j.get("transaction_total_cents"),
                    "converted": j.get("converted", False),
                    "zones_visited": j.get("zones_visited", []),
                })
        except Exception as e:
            logger.error(f"Failed to persist journeys: {e}", exc_info=True)

    async def persist_insights(self, agent_outputs: dict):
        """Save cross-reference insights to database."""
        try:
            from ..db import get_db
            db = get_db()
            for agent_name, output in agent_outputs.items():
                if not isinstance(output, dict) or output.get("status") != "complete":
                    continue
                for insight in output.get("insights", []):
                    await db.insert("cross_reference_insights", {
                        "org_id": self._org_id,
                        "agent_name": agent_name,
                        "insight_type": insight.get("type", ""),
                        "detail": insight.get("detail", ""),
                        "data": insight,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    })
        except Exception as e:
            logger.error(f"Failed to persist insights: {e}", exc_info=True)
