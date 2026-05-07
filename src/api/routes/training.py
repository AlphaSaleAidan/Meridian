"""
Swarm training API — status, scorecards, and manual triggers.

GET  /api/training/status       → Training loop stats
GET  /api/training/scorecards   → Per-agent accuracy & trend
POST /api/training/trigger      → Force a training cycle
POST /api/training/signal       → Submit engagement signal from dashboard
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("meridian.api.training")
router = APIRouter(prefix="/api/training", tags=["training"])


class EngagementSignal(BaseModel):
    org_id: str
    agent_name: str
    insight_id: str = ""
    action: str = "viewed"  # viewed, acted, dismissed


@router.get("/status")
async def training_status():
    from ...ai.swarm_trainer import get_swarm_trainer
    trainer = get_swarm_trainer()
    return trainer.get_training_stats()


@router.get("/scorecards")
async def agent_scorecards():
    from ...ai.swarm_trainer import get_swarm_trainer
    trainer = get_swarm_trainer()
    cards = trainer.get_scorecards()
    return {
        "agents": cards,
        "count": len(cards),
        "improving": sum(1 for c in cards.values() if c["trend"] == "improving"),
        "degrading": sum(1 for c in cards.values() if c["trend"] == "degrading"),
    }


@router.post("/trigger")
async def trigger_training():
    from ...ai.swarm_trainer import get_swarm_trainer
    trainer = get_swarm_trainer()
    outputs = await trainer._fetch_latest_outputs()
    if not outputs:
        return {"status": "no_data", "message": "No pending agent outputs to train on"}
    result = await trainer.run_training_cycle(outputs)
    return {"status": "complete", **result}


@router.post("/signal")
async def submit_signal(signal: EngagementSignal):
    from ...ai.swarm_trainer import get_swarm_trainer, TrainingSignal
    trainer = get_swarm_trainer()

    score_map = {"viewed": 0.3, "acted": 1.0, "dismissed": 0.0}
    score = score_map.get(signal.action, 0.3)

    trainer.record_signal(TrainingSignal(
        agent_name=signal.agent_name,
        org_id=signal.org_id,
        signal_type="engagement",
        score=score,
        detail=f"action={signal.action}, insight={signal.insight_id}",
    ))
    return {"status": "recorded", "agent": signal.agent_name, "score": score}
