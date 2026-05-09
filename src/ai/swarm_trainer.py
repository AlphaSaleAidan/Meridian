"""
Autonomous Swarm Trainer — self-improving agent loop.

Runs continuously (or on schedule) to train the agent swarm by:
  1. Replaying past analysis results and grading quality
  2. Storing successful reasoning patterns in agent memory
  3. Feeding labeled examples to DSPy for prompt optimization
  4. Tracking agent accuracy scores over time for drift detection

Training signals:
  - Merchant engagement (did they view/act on the insight?)
  - Revenue correlation (did predicted trends actually happen?)
  - Agent agreement (do multiple agents converge on the same finding?)
  - Reasoning chain quality (confidence calibration, hypothesis hit rate)
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("meridian.ai.swarm_trainer")

TRAINING_DIR = Path(__file__).parent.parent.parent / ".claude-flow" / "data"
SCORES_FILE = TRAINING_DIR / "agent-scores.json"
PATTERNS_FILE = TRAINING_DIR / "learned-patterns.jsonl"
TRAINING_LOG = TRAINING_DIR / "training-log.jsonl"


@dataclass
class TrainingSignal:
    agent_name: str
    org_id: str
    signal_type: str  # engagement, accuracy, agreement, quality
    score: float  # 0.0 - 1.0
    detail: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class AgentScorecard:
    agent_name: str
    total_runs: int = 0
    avg_confidence: float = 0.0
    accuracy_score: float = 0.5
    engagement_rate: float = 0.0
    agreement_score: float = 0.0
    trend: str = "stable"  # improving, degrading, stable
    last_trained: str = ""
    pattern_count: int = 0


class SwarmTrainer:
    """Autonomous training loop for the Meridian agent swarm.

    Runs as a background task, continuously improving agent quality
    by analyzing past outputs and reinforcing successful patterns.
    """

    def __init__(self, db=None):
        self.db = db
        self._scores: dict[str, AgentScorecard] = {}
        self._training_examples: list[dict] = []
        self._running = False
        self._cycle_count = 0
        self._load_scores()

    def _load_scores(self):
        if SCORES_FILE.exists():
            try:
                data = json.loads(SCORES_FILE.read_text())
                for name, raw in data.items():
                    self._scores[name] = AgentScorecard(
                        agent_name=name,
                        total_runs=raw.get("total_runs", 0),
                        avg_confidence=raw.get("avg_confidence", 0.0),
                        accuracy_score=raw.get("accuracy_score", 0.5),
                        engagement_rate=raw.get("engagement_rate", 0.0),
                        agreement_score=raw.get("agreement_score", 0.0),
                        trend=raw.get("trend", "stable"),
                        last_trained=raw.get("last_trained", ""),
                        pattern_count=raw.get("pattern_count", 0),
                    )
            except Exception as e:
                logger.warning(f"Failed to load scores: {e}")

    def _save_scores(self):
        TRAINING_DIR.mkdir(parents=True, exist_ok=True)
        data = {}
        for name, card in self._scores.items():
            data[name] = {
                "total_runs": card.total_runs,
                "avg_confidence": round(card.avg_confidence, 3),
                "accuracy_score": round(card.accuracy_score, 3),
                "engagement_rate": round(card.engagement_rate, 3),
                "agreement_score": round(card.agreement_score, 3),
                "trend": card.trend,
                "last_trained": card.last_trained,
                "pattern_count": card.pattern_count,
            }
        SCORES_FILE.write_text(json.dumps(data, indent=2))

    def _log_training(self, event: dict):
        TRAINING_DIR.mkdir(parents=True, exist_ok=True)
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        event["cycle"] = self._cycle_count
        with open(TRAINING_LOG, "a") as f:
            f.write(json.dumps(event) + "\n")

    def _store_pattern(self, pattern: dict):
        TRAINING_DIR.mkdir(parents=True, exist_ok=True)
        pattern["stored_at"] = datetime.now(timezone.utc).isoformat()
        with open(PATTERNS_FILE, "a") as f:
            f.write(json.dumps(pattern) + "\n")

    # ─── Training Signals ──────────────────────────────────

    def record_signal(self, signal: TrainingSignal):
        card = self._scores.setdefault(
            signal.agent_name,
            AgentScorecard(agent_name=signal.agent_name),
        )
        card.total_runs += 1

        if signal.signal_type == "accuracy":
            alpha = 0.1
            card.accuracy_score = (
                card.accuracy_score * (1 - alpha) + signal.score * alpha
            )
        elif signal.signal_type == "engagement":
            alpha = 0.15
            card.engagement_rate = (
                card.engagement_rate * (1 - alpha) + signal.score * alpha
            )
        elif signal.signal_type == "agreement":
            alpha = 0.1
            card.agreement_score = (
                card.agreement_score * (1 - alpha) + signal.score * alpha
            )
        elif signal.signal_type == "quality":
            alpha = 0.1
            card.avg_confidence = (
                card.avg_confidence * (1 - alpha) + signal.score * alpha
            )

        self._log_training({
            "event": "signal",
            "agent": signal.agent_name,
            "type": signal.signal_type,
            "score": signal.score,
            "detail": signal.detail,
        })

    # ─── Core Training Cycle ───────────────────────────────

    async def run_training_cycle(self, agent_outputs: dict, ctx_org_id: str = ""):
        """Run a single training cycle on a completed swarm run.

        Extracts quality signals, stores patterns, and updates scores.
        """
        self._cycle_count += 1
        start = time.monotonic()

        completed = {
            k: v for k, v in agent_outputs.items()
            if isinstance(v, dict) and v.get("status") == "complete"
        }
        failed = {
            k: v for k, v in agent_outputs.items()
            if isinstance(v, dict) and v.get("status") == "error"
        }

        logger.info(
            f"Training cycle {self._cycle_count}: "
            f"{len(completed)} complete, {len(failed)} failed agents"
        )

        # Phase 1: Grade reasoning quality
        for name, output in completed.items():
            reasoning = output.get("_reasoning", {})
            confidence = output.get("reasoning_confidence", 0.5)
            insights_count = len(output.get("insights", []))

            quality_score = self._grade_reasoning(reasoning, confidence, insights_count)
            self.record_signal(TrainingSignal(
                agent_name=name,
                org_id=ctx_org_id,
                signal_type="quality",
                score=quality_score,
                detail=f"confidence={confidence:.2f}, insights={insights_count}",
            ))

        # Phase 2: Check inter-agent agreement
        agreement_signals = self._check_agreement(completed)
        for signal in agreement_signals:
            self.record_signal(signal)

        # Phase 3: Store successful patterns
        patterns_stored = 0
        for name, output in completed.items():
            card = self._scores.get(name, AgentScorecard(agent_name=name))
            if card.accuracy_score > 0.6 and output.get("insights"):
                self._store_pattern({
                    "agent": name,
                    "org_id": ctx_org_id,
                    "insight_count": len(output["insights"]),
                    "confidence": output.get("reasoning_confidence", 0),
                    "top_insight": output["insights"][0] if output["insights"] else {},
                    "data_keys": list(output.get("data", {}).keys())[:10],
                })
                card.pattern_count += 1
                patterns_stored += 1

        # Phase 4: Store agent memory (cross-cycle learning)
        await self._store_agent_memories(completed, ctx_org_id)

        # Phase 5: Build DSPy training examples from high-quality outputs
        dspy_examples = self._build_dspy_examples(completed)
        self._training_examples.extend(dspy_examples)

        # Phase 6: Trigger DSPy compilation if enough examples
        if len(self._training_examples) >= 10:
            await self._compile_dspy()

        # Phase 7: Update trend detection
        self._update_trends()

        # Save
        self._save_scores()

        elapsed = time.monotonic() - start
        self._log_training({
            "event": "cycle_complete",
            "agents_graded": len(completed),
            "agents_failed": len(failed),
            "patterns_stored": patterns_stored,
            "dspy_examples": len(dspy_examples),
            "duration_ms": int(elapsed * 1000),
        })

        logger.info(
            f"Training cycle {self._cycle_count} complete in {elapsed:.1f}s: "
            f"{patterns_stored} patterns, {len(dspy_examples)} DSPy examples"
        )

        return {
            "cycle": self._cycle_count,
            "agents_graded": len(completed),
            "patterns_stored": patterns_stored,
            "dspy_examples_total": len(self._training_examples),
            "duration_seconds": round(elapsed, 2),
        }

    def _grade_reasoning(self, reasoning: dict, confidence: float, insights_count: int) -> float:
        score = 0.3
        steps = reasoning.get("steps", [])
        if len(steps) >= 4:
            score += 0.15
        if len(steps) >= 5:
            score += 0.1
        experiments = [s for s in steps if s.get("phase") == "experiment"]
        if experiments:
            exp_content = experiments[0].get("content", {})
            exps = exp_content.get("experiments", [])
            confirmed = sum(1 for e in exps if e.get("result") == "CONFIRMED")
            if exps:
                score += 0.15 * (confirmed / len(exps))
        if 0.4 <= confidence <= 0.9:
            score += 0.15
        elif confidence > 0.9:
            score += 0.05
        if insights_count >= 2:
            score += 0.15
        return min(1.0, score)

    def _check_agreement(self, completed: dict) -> list[TrainingSignal]:
        signals = []
        insight_themes = {}
        for name, output in completed.items():
            for insight in output.get("insights", []):
                theme = insight.get("type", "unknown")
                insight_themes.setdefault(theme, []).append(name)

        for theme, agents in insight_themes.items():
            if len(agents) >= 2:
                for agent_name in agents:
                    signals.append(TrainingSignal(
                        agent_name=agent_name,
                        org_id="",
                        signal_type="agreement",
                        score=min(1.0, len(agents) / 3),
                        detail=f"theme={theme}, agreed_with={agents}",
                    ))
        return signals

    async def _store_agent_memories(self, completed: dict, org_id: str):
        try:
            from .agent_memory import get_agent_memory
            memory = get_agent_memory()
            for name, output in completed.items():
                if not output.get("insights"):
                    continue
                top_insights = output["insights"][:3]
                summary = "; ".join(
                    i.get("detail", i.get("type", ""))[:100]
                    for i in top_insights
                )
                memory.store(
                    merchant_id=org_id or "training",
                    agent_name=name,
                    content=f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d')}] {summary}",
                    metadata={
                        "confidence": output.get("reasoning_confidence", 0),
                        "score": output.get("score", 0),
                        "cycle": self._cycle_count,
                    },
                )
        except Exception as e:
            logger.warning(f"Agent memory storage failed: {e}")

    def _build_dspy_examples(self, completed: dict) -> list[dict]:
        examples = []
        for name, output in completed.items():
            card = self._scores.get(name, AgentScorecard(agent_name=name))
            if card.accuracy_score < 0.55:
                continue
            for insight in output.get("insights", []):
                detail = insight.get("detail", "")
                if len(detail) < 20:
                    continue
                recs = output.get("recommendations", [])
                action = recs[0].get("action", "") if recs else ""
                if not action:
                    continue
                examples.append({
                    "raw_insight": detail,
                    "business_context": f"agent={name}, score={output.get('score', 0)}",
                    "enhanced_insight": detail,
                    "action_item": action,
                })
        return examples

    async def _compile_dspy(self):
        try:
            from .dspy_optimizer import MeridianOptimizer
            optimizer = MeridianOptimizer()
            if optimizer.is_available:
                optimizer.compile_with_examples(self._training_examples[-50:])
                self._training_examples = self._training_examples[-20:]
                self._log_training({
                    "event": "dspy_compiled",
                    "examples_used": min(50, len(self._training_examples)),
                })
                logger.info("DSPy optimizer recompiled with new training data")
        except Exception as e:
            logger.warning(f"DSPy compilation failed: {e}")

    def _update_trends(self):
        for name, card in self._scores.items():
            if card.total_runs < 5:
                card.trend = "stable"
                continue
            combined = (
                card.accuracy_score * 0.4
                + card.engagement_rate * 0.3
                + card.agreement_score * 0.2
                + card.avg_confidence * 0.1
            )
            if combined > 0.65:
                card.trend = "improving"
            elif combined < 0.4:
                card.trend = "degrading"
            else:
                card.trend = "stable"

    # ─── Autonomous Training Loop ──────────────────────────

    async def start_autonomous(self, interval_seconds: int = 300):
        """Run the training loop continuously.

        Pulls the latest agent outputs from DB (if available) or from
        the last run stored in .claude-flow/data, and trains on them.
        """
        self._running = True
        logger.info(
            f"Autonomous swarm trainer started (interval: {interval_seconds}s)"
        )
        self._log_training({"event": "autonomous_start", "interval": interval_seconds})

        while self._running:
            try:
                outputs = await self._fetch_latest_outputs()
                if outputs:
                    result = await self.run_training_cycle(outputs)
                    logger.info(f"Autonomous training: {result}")
                else:
                    logger.debug("No new agent outputs to train on")
            except Exception as e:
                logger.error(f"Autonomous training error: {e}", exc_info=True)
                self._log_training({"event": "error", "error": str(e)})

            await asyncio.sleep(interval_seconds)

    def stop(self):
        self._running = False
        self._save_scores()
        self._log_training({"event": "autonomous_stop"})
        logger.info("Autonomous swarm trainer stopped")

    async def _fetch_latest_outputs(self) -> dict | None:
        if self.db and hasattr(self.db, "get_latest_agent_outputs"):
            try:
                return await self.db.get_latest_agent_outputs()
            except Exception as e:
                logger.warning(f"DB fetch failed: {e}")

        pending = TRAINING_DIR / "pending-insights.jsonl"
        if pending.exists():
            lines = pending.read_text().strip().split("\n")
            if lines and lines[0]:
                outputs = {}
                for line in lines:
                    try:
                        data = json.loads(line)
                        agent = data.get("agent", data.get("source_agent", "unknown"))
                        outputs.setdefault(agent, {
                            "status": "complete",
                            "insights": [],
                            "recommendations": [],
                            "data": {},
                        })
                        outputs[agent]["insights"].append(data)
                    except json.JSONDecodeError:
                        continue
                if outputs:
                    pending.write_text("")
                    return outputs
        return None

    # ─── Status / Reporting ────────────────────────────────

    def get_scorecards(self) -> dict[str, dict]:
        return {
            name: {
                "total_runs": card.total_runs,
                "accuracy": round(card.accuracy_score, 2),
                "engagement": round(card.engagement_rate, 2),
                "agreement": round(card.agreement_score, 2),
                "confidence": round(card.avg_confidence, 2),
                "trend": card.trend,
                "patterns": card.pattern_count,
            }
            for name, card in self._scores.items()
        }

    def get_training_stats(self) -> dict:
        total_runs = sum(c.total_runs for c in self._scores.values())
        improving = sum(1 for c in self._scores.values() if c.trend == "improving")
        degrading = sum(1 for c in self._scores.values() if c.trend == "degrading")
        total_patterns = sum(c.pattern_count for c in self._scores.values())
        return {
            "agents_tracked": len(self._scores),
            "total_training_runs": total_runs,
            "training_cycles": self._cycle_count,
            "dspy_examples_queued": len(self._training_examples),
            "agents_improving": improving,
            "agents_degrading": degrading,
            "total_patterns_stored": total_patterns,
            "is_running": self._running,
        }


_shared_trainer: SwarmTrainer | None = None


def get_swarm_trainer(db=None) -> SwarmTrainer:
    global _shared_trainer
    if _shared_trainer is None:
        _shared_trainer = SwarmTrainer(db=db)
    return _shared_trainer
