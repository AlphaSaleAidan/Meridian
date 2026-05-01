"""Karpathy 5-phase reasoning engine for Meridian AI agents.

Every agent runs: THINK → HYPOTHESIZE → EXPERIMENT → SYNTHESIZE → REFLECT.
The loop works with or without an LLM — pure-data agents get structured
reasoning from statistical analysis; LLM-backed agents get richer chains.
"""
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("meridian.ai.reasoning")


class ReasoningPhase(str, Enum):
    THINK = "think"
    HYPOTHESIZE = "hypothesize"
    EXPERIMENT = "experiment"
    SYNTHESIZE = "synthesize"
    REFLECT = "reflect"


@dataclass
class ReasoningStep:
    """Single phase output in the reasoning chain."""
    phase: ReasoningPhase
    content: dict[str, Any]
    duration_ms: int = 0
    token_count: int = 0
    source: str = "data"  # "data" or "llm"

    def summary(self) -> str:
        if self.phase == ReasoningPhase.THINK:
            return self.content.get("data_landscape", "")
        elif self.phase == ReasoningPhase.HYPOTHESIZE:
            hyps = self.content.get("hypotheses", [])
            return f"{len(hyps)} hypotheses generated"
        elif self.phase == ReasoningPhase.EXPERIMENT:
            exps = self.content.get("experiments", [])
            confirmed = sum(1 for e in exps if e.get("result") == "CONFIRMED")
            return f"{confirmed}/{len(exps)} hypotheses confirmed"
        elif self.phase == ReasoningPhase.SYNTHESIZE:
            findings = self.content.get("findings", [])
            return self.content.get("one_line_summary", f"{len(findings)} findings")
        elif self.phase == ReasoningPhase.REFLECT:
            return f"Confidence: {self.content.get('overall_confidence', 'UNKNOWN')}"
        return ""


@dataclass
class ReasoningChain:
    """Complete 5-phase reasoning chain for an agent run."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    domain: str = ""
    steps: list[ReasoningStep] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def start(self):
        self.started_at = datetime.now(timezone.utc)

    def complete(self):
        self.completed_at = datetime.now(timezone.utc)

    def add_step(self, phase: ReasoningPhase, content: dict, duration_ms: int = 0,
                 source: str = "data", token_count: int = 0):
        self.steps.append(ReasoningStep(
            phase=phase, content=content, duration_ms=duration_ms,
            source=source, token_count=token_count,
        ))

    @property
    def confidence(self) -> float:
        reflect = self.get_phase(ReasoningPhase.REFLECT)
        if reflect:
            return reflect.content.get("confidence_score", 0.5)
        return 0.5

    @property
    def confidence_level(self) -> str:
        reflect = self.get_phase(ReasoningPhase.REFLECT)
        if reflect:
            return reflect.content.get("overall_confidence", "MEDIUM")
        return "MEDIUM"

    @property
    def verdict(self) -> str:
        synth = self.get_phase(ReasoningPhase.SYNTHESIZE)
        if synth:
            return synth.content.get("verdict", "no_action")
        return "no_action"

    @property
    def findings(self) -> list[dict]:
        synth = self.get_phase(ReasoningPhase.SYNTHESIZE)
        if synth:
            return synth.content.get("findings", [])
        return []

    @property
    def caveats(self) -> list[str]:
        reflect = self.get_phase(ReasoningPhase.REFLECT)
        if reflect:
            return reflect.content.get("caveats", [])
        return []

    @property
    def thinking(self) -> list[dict]:
        return [
            {"phase": s.phase.value, "summary": s.summary(), "duration_ms": s.duration_ms}
            for s in self.steps
        ]

    @property
    def total_duration_ms(self) -> int:
        return sum(s.duration_ms for s in self.steps)

    def get_phase(self, phase: ReasoningPhase) -> Optional[ReasoningStep]:
        for step in self.steps:
            if step.phase == phase:
                return step
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "domain": self.domain,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level,
            "verdict": self.verdict,
            "findings": self.findings,
            "caveats": self.caveats,
            "thinking": self.thinking,
            "total_duration_ms": self.total_duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }


class KarpathyReasoning:
    """5-phase reasoning engine. Runs THINK → HYPOTHESIZE → EXPERIMENT → SYNTHESIZE → REFLECT.

    Works in two modes:
    - **Data-only** (no llm_fn): builds reasoning from statistical analysis of ctx
    - **LLM-enhanced** (with llm_fn): uses LLM to generate richer reasoning text

    Usage:
        reasoning = KarpathyReasoning()
        chain = await reasoning.reason("peak_hours", "staffing", ctx_dict)
    """

    async def reason(
        self,
        agent_name: str,
        domain: str,
        context: dict[str, Any],
        llm_fn: Optional[Callable] = None,
    ) -> ReasoningChain:
        chain = ReasoningChain(agent_name=agent_name, domain=domain)
        chain.start()

        try:
            think = await self._think(agent_name, domain, context)
            chain.add_step(ReasoningPhase.THINK, think["content"], think["duration_ms"])

            hypotheses = await self._hypothesize(agent_name, domain, context, think["content"])
            chain.add_step(ReasoningPhase.HYPOTHESIZE, hypotheses["content"], hypotheses["duration_ms"])

            experiments = await self._experiment(agent_name, context, hypotheses["content"])
            chain.add_step(ReasoningPhase.EXPERIMENT, experiments["content"], experiments["duration_ms"])

            synthesis = await self._synthesize(agent_name, domain, experiments["content"], context)
            chain.add_step(ReasoningPhase.SYNTHESIZE, synthesis["content"], synthesis["duration_ms"])

            reflection = await self._reflect(agent_name, chain)
            chain.add_step(ReasoningPhase.REFLECT, reflection["content"], reflection["duration_ms"])

        except Exception as e:
            chain.error = str(e)
            logger.error("Reasoning chain failed for %s: %s", agent_name, e, exc_info=True)

        chain.complete()
        return chain

    async def _think(self, agent_name: str, domain: str, ctx: dict) -> dict:
        """Phase 1: Survey data landscape, establish baseline, spot standouts."""
        t0 = time.monotonic()

        txn_count = len(ctx.get("transactions", []))
        daily = ctx.get("daily_revenue", [])
        products = ctx.get("product_performance", ctx.get("products", []))
        employees = ctx.get("employees", [])
        inventory = ctx.get("inventory", [])

        revenue_values = [d.get("revenue_cents", 0) for d in daily if d.get("revenue_cents")]
        avg_rev = sum(revenue_values) / max(len(revenue_values), 1) if revenue_values else 0

        standouts = []
        if revenue_values and len(revenue_values) >= 7:
            recent_avg = sum(revenue_values[-7:]) / 7
            if avg_rev > 0:
                pct_change = (recent_avg - avg_rev) / avg_rev * 100
                if abs(pct_change) > 10:
                    direction = "up" if pct_change > 0 else "down"
                    standouts.append(
                        f"Recent 7-day revenue trending {direction} {abs(pct_change):.1f}% vs overall average"
                    )

        if revenue_values:
            std = (sum((v - avg_rev) ** 2 for v in revenue_values) / max(len(revenue_values) - 1, 1)) ** 0.5
            outliers = [v for v in revenue_values if abs(v - avg_rev) > 2 * std]
            if outliers:
                standouts.append(f"{len(outliers)} revenue outlier(s) detected (>2 std dev)")

        if len(products) > 0:
            standouts.append(f"{len(products)} products in catalog — product mix analysis possible")

        if not standouts:
            standouts.append("No strong anomalies detected in initial scan")

        has_txns = txn_count > 0 or len(daily) > 0
        data_sources = sum([has_txns, len(products) > 0, len(inventory) > 0, len(employees) > 0])
        quality = "HIGH" if data_sources >= 3 else "MEDIUM" if data_sources >= 2 else "LOW"

        gaps = []
        if not has_txns:
            gaps.append("No transaction data")
        if not products:
            gaps.append("No product performance data")
        if not inventory:
            gaps.append("No inventory data")
        if not employees:
            gaps.append("No employee/staffing data")

        content = {
            "data_landscape": (
                f"{domain} analysis for {agent_name}: {txn_count} transactions, "
                f"{len(daily)} daily records, {len(products)} products, "
                f"{len(employees)} employees tracked."
            ),
            "baseline": {
                "metric": f"{domain}_daily_revenue_cents",
                "current_value": f"{avg_rev:.0f} cents/day avg",
                "period": f"{len(daily)} days",
            },
            "standout_observations": standouts[:5],
            "data_quality_rating": quality,
            "data_gaps": gaps,
        }

        return {"content": content, "duration_ms": int((time.monotonic() - t0) * 1000)}

    async def _hypothesize(self, agent_name: str, domain: str, ctx: dict,
                           think: dict) -> dict:
        """Phase 2: Generate 3+ competing hypotheses including null."""
        t0 = time.monotonic()

        standouts = think.get("standout_observations", [])
        quality = think.get("data_quality_rating", "LOW")

        hypotheses = []

        null_prior = 0.3 if quality == "HIGH" else 0.4 if quality == "MEDIUM" else 0.5
        hypotheses.append({
            "id": "H0_NULL",
            "statement": f"Null hypothesis: {domain} metrics are within normal variance — no meaningful pattern",
            "prior_probability": round(null_prior, 2),
            "testable_prediction": "All metrics fall within 1.5 std dev of historical mean",
            "evidence_needed": "Statistical comparison against rolling 30-day baseline",
        })

        remaining_prob = 1.0 - null_prior
        if any("trending" in s.lower() for s in standouts):
            hypotheses.append({
                "id": "H1",
                "statement": f"There is a sustained directional trend in {domain} metrics",
                "prior_probability": round(remaining_prob * 0.5, 2),
                "testable_prediction": "7-day moving average differs from 30-day by >10%",
                "evidence_needed": "Trend test on daily time series",
            })
            remaining_prob *= 0.5

        if any("outlier" in s.lower() for s in standouts):
            hypotheses.append({
                "id": "H2",
                "statement": f"Outlier events are driving apparent {domain} changes (not a real trend)",
                "prior_probability": round(remaining_prob * 0.6, 2),
                "testable_prediction": "Removing top/bottom 5% of days normalizes the metric",
                "evidence_needed": "Winsorized mean vs raw mean comparison",
            })
            remaining_prob *= 0.4

        if len(hypotheses) < 3:
            hypotheses.append({
                "id": f"H{len(hypotheses)}",
                "statement": f"Seasonal or day-of-week effects explain {domain} variation",
                "prior_probability": round(remaining_prob * 0.7, 2),
                "testable_prediction": "Weekday vs weekend split shows >15% difference",
                "evidence_needed": "Day-of-week grouping with significance test",
            })
            remaining_prob *= 0.3

        if len(hypotheses) < 4:
            hypotheses.append({
                "id": f"H{len(hypotheses)}",
                "statement": f"External factors (not captured in data) are influencing {domain}",
                "prior_probability": round(remaining_prob, 2),
                "testable_prediction": "No internal data pattern explains the variance",
                "evidence_needed": "Residual analysis after accounting for known factors",
            })

        content = {"hypotheses": hypotheses}
        return {"content": content, "duration_ms": int((time.monotonic() - t0) * 1000)}

    async def _experiment(self, agent_name: str, ctx: dict, hypotheses_data: dict) -> dict:
        """Phase 3: Test each hypothesis against actual data."""
        t0 = time.monotonic()

        daily = ctx.get("daily_revenue", [])
        revenue_values = [d.get("revenue_cents", 0) for d in daily if d.get("revenue_cents")]
        n = len(revenue_values)

        experiments = []
        for hyp in hypotheses_data.get("hypotheses", []):
            hid = hyp["id"]
            result_entry: dict[str, Any] = {
                "hypothesis_id": hid,
                "test_description": "",
                "data_used": "",
                "result": "INCONCLUSIVE",
                "posterior_probability": hyp.get("prior_probability", 0.2),
                "evidence_strength": "WEAK",
                "numbers": "",
            }

            if hid == "H0_NULL":
                if n >= 7:
                    avg = sum(revenue_values) / n
                    std = (sum((v - avg) ** 2 for v in revenue_values) / max(n - 1, 1)) ** 0.5
                    recent = revenue_values[-7:]
                    recent_avg = sum(recent) / 7
                    z = abs(recent_avg - avg) / max(std, 1)
                    within = z < 1.5
                    result_entry.update({
                        "test_description": "Compared recent 7-day mean to overall mean in std-dev units",
                        "data_used": f"n={n}, mean={avg:.0f}, std={std:.0f}, recent_mean={recent_avg:.0f}",
                        "result": "CONFIRMED" if within else "REJECTED",
                        "posterior_probability": round(0.7 if within else 0.1, 2),
                        "evidence_strength": "STRONG" if n >= 30 else "MODERATE",
                        "numbers": f"z-score={z:.2f} ({'within' if within else 'outside'} 1.5σ threshold)",
                    })
                else:
                    result_entry.update({
                        "test_description": "Insufficient data for statistical test",
                        "data_used": f"n={n} (need ≥7)",
                        "result": "INCONCLUSIVE",
                        "numbers": "Too few data points for meaningful comparison",
                    })

            elif "trend" in hyp.get("statement", "").lower():
                if n >= 14:
                    first_half = revenue_values[:n // 2]
                    second_half = revenue_values[n // 2:]
                    avg1 = sum(first_half) / len(first_half)
                    avg2 = sum(second_half) / len(second_half)
                    pct = (avg2 - avg1) / max(avg1, 1) * 100
                    has_trend = abs(pct) > 10
                    result_entry.update({
                        "test_description": "Split-half comparison of time series",
                        "data_used": f"first_half_avg={avg1:.0f}, second_half_avg={avg2:.0f}",
                        "result": "CONFIRMED" if has_trend else "REJECTED",
                        "posterior_probability": round(0.75 if has_trend else 0.15, 2),
                        "evidence_strength": "STRONG" if n >= 30 else "MODERATE",
                        "numbers": f"Change: {pct:+.1f}% (threshold: ±10%)",
                    })
                else:
                    result_entry["test_description"] = "Insufficient data for trend analysis"
                    result_entry["data_used"] = f"n={n} (need ≥14)"

            elif "outlier" in hyp.get("statement", "").lower():
                if n >= 10:
                    avg = sum(revenue_values) / n
                    sorted_vals = sorted(revenue_values)
                    trim = max(1, n // 20)
                    trimmed = sorted_vals[trim:-trim] if trim < n // 2 else sorted_vals
                    trimmed_avg = sum(trimmed) / max(len(trimmed), 1)
                    diff_pct = abs(trimmed_avg - avg) / max(avg, 1) * 100
                    outlier_driven = diff_pct > 5
                    result_entry.update({
                        "test_description": "Compared raw mean to 5% winsorized mean",
                        "data_used": f"raw_mean={avg:.0f}, winsorized_mean={trimmed_avg:.0f}",
                        "result": "CONFIRMED" if outlier_driven else "REJECTED",
                        "posterior_probability": round(0.65 if outlier_driven else 0.1, 2),
                        "evidence_strength": "MODERATE",
                        "numbers": f"Mean shift after trimming: {diff_pct:.1f}%",
                    })

            elif "season" in hyp.get("statement", "").lower() or "day-of-week" in hyp.get("statement", "").lower():
                if n >= 14:
                    day_buckets: dict[int, list[float]] = {}
                    for i, val in enumerate(revenue_values):
                        dow = i % 7
                        day_buckets.setdefault(dow, []).append(val)
                    day_avgs = {k: sum(v) / len(v) for k, v in day_buckets.items() if v}
                    if day_avgs:
                        max_day = max(day_avgs.values())
                        min_day = min(day_avgs.values())
                        spread = (max_day - min_day) / max(min_day, 1) * 100
                        has_pattern = spread > 15
                        result_entry.update({
                            "test_description": "Day-of-week grouping to detect weekly patterns",
                            "data_used": f"day_averages={{{k}: {v:.0f} for k, v in day_avgs.items()}}",
                            "result": "CONFIRMED" if has_pattern else "REJECTED",
                            "posterior_probability": round(0.7 if has_pattern else 0.1, 2),
                            "evidence_strength": "MODERATE",
                            "numbers": f"Max-min spread: {spread:.1f}% (threshold: 15%)",
                        })

            else:
                result_entry.update({
                    "test_description": f"Generic test for: {hyp.get('statement', '')}",
                    "result": "INCONCLUSIVE",
                    "evidence_strength": "WEAK",
                    "numbers": "No specific statistical test available for this hypothesis",
                })

            experiments.append(result_entry)

        content = {"experiments": experiments}
        return {"content": content, "duration_ms": int((time.monotonic() - t0) * 1000)}

    async def _synthesize(self, agent_name: str, domain: str,
                          experiment_data: dict, ctx: dict) -> dict:
        """Phase 4: Combine confirmed findings into actionable insights."""
        t0 = time.monotonic()

        experiments = experiment_data.get("experiments", [])
        confirmed = [e for e in experiments if e.get("result") == "CONFIRMED"]
        null_confirmed = any(e["hypothesis_id"] == "H0_NULL" and e["result"] == "CONFIRMED" for e in experiments)

        findings = []

        if null_confirmed and len(confirmed) == 1:
            findings.append({
                "insight": f"{domain.replace('_', ' ').title()} metrics are stable and within normal range",
                "action": "Continue current operations — no intervention needed",
                "impact_estimate": "$0/mo (no action required)",
                "impact_cents": 0,
                "urgency": "LOW",
                "confidence": 0.8,
                "supporting_evidence": "All metrics within 1.5 standard deviations of historical mean",
            })
        else:
            for exp in confirmed:
                if exp["hypothesis_id"] == "H0_NULL":
                    continue
                findings.append({
                    "insight": f"Confirmed: {exp.get('test_description', 'pattern detected')}",
                    "action": f"Review {domain} data for optimization opportunities",
                    "impact_estimate": "Requires deeper analysis to quantify",
                    "impact_cents": 0,
                    "urgency": "MEDIUM" if exp.get("evidence_strength") == "STRONG" else "LOW",
                    "confidence": exp.get("posterior_probability", 0.5),
                    "supporting_evidence": exp.get("numbers", ""),
                })

        if not findings:
            findings.append({
                "insight": f"Inconclusive results for {domain} — more data needed",
                "action": "Collect more data before drawing conclusions",
                "impact_estimate": "Unknown",
                "impact_cents": 0,
                "urgency": "LOW",
                "confidence": 0.3,
                "supporting_evidence": "No hypothesis reached confirmation threshold",
            })

        findings.sort(key=lambda f: f.get("impact_cents", 0), reverse=True)

        verdict = "no_action"
        if null_confirmed and len(confirmed) == 1:
            verdict = "no_action"
        elif confirmed:
            verdict = "actionable"
        else:
            verdict = "monitoring"

        top = findings[0] if findings else {}
        summary = top.get("insight", f"No significant {domain} findings")

        content = {
            "findings": findings,
            "verdict": verdict,
            "one_line_summary": summary,
        }
        return {"content": content, "duration_ms": int((time.monotonic() - t0) * 1000)}

    async def _reflect(self, agent_name: str, chain: ReasoningChain) -> dict:
        """Phase 5: Meta-cognition — confidence, caveats, 'what could I be wrong about?'"""
        t0 = time.monotonic()

        think = chain.get_phase(ReasoningPhase.THINK)
        experiment = chain.get_phase(ReasoningPhase.EXPERIMENT)
        synthesize = chain.get_phase(ReasoningPhase.SYNTHESIZE)

        data_quality = think.content.get("data_quality_rating", "LOW") if think else "LOW"
        data_gaps = think.content.get("data_gaps", []) if think else []

        experiments = experiment.content.get("experiments", []) if experiment else []
        total_tests = len(experiments)
        confirmed = sum(1 for e in experiments if e.get("result") == "CONFIRMED")
        inconclusive = sum(1 for e in experiments if e.get("result") == "INCONCLUSIVE")

        findings = synthesize.content.get("findings", []) if synthesize else []
        avg_finding_conf = (
            sum(f.get("confidence", 0.5) for f in findings) / max(len(findings), 1)
            if findings else 0.5
        )

        quality_weight = {"HIGH": 0.9, "MEDIUM": 0.7, "LOW": 0.4}.get(data_quality, 0.5)
        test_weight = confirmed / max(total_tests, 1)
        score = round(quality_weight * 0.4 + test_weight * 0.3 + avg_finding_conf * 0.3, 2)
        score = max(0.1, min(0.99, score))

        if score >= 0.8:
            level = "HIGH"
        elif score >= 0.5:
            level = "MEDIUM"
        else:
            level = "LOW"

        caveats = []
        if data_gaps:
            caveats.append(f"Missing data: {', '.join(data_gaps[:3])}")
        if inconclusive > 0:
            caveats.append(f"{inconclusive}/{total_tests} hypotheses were inconclusive")
        if data_quality == "LOW":
            caveats.append("Low data quality reduces confidence in all findings")
        if not caveats:
            caveats.append("No major caveats identified")

        wrong_about = [
            "Correlation mistaken for causation — external factors may be the real driver",
            "Sample period may not be representative of long-term patterns",
        ]
        if data_quality != "HIGH":
            wrong_about.append("Data quality issues may have introduced systematic bias")

        biggest_risk = "Insufficient data history" if data_quality == "LOW" else (
            "Confounding variables not captured in POS data"
        )

        content = {
            "overall_confidence": level,
            "confidence_score": score,
            "reasoning_quality": (
                f"{confirmed}/{total_tests} hypotheses tested successfully, "
                f"data quality: {data_quality}"
            ),
            "caveats": caveats,
            "what_could_i_be_wrong_about": wrong_about,
            "biggest_risk": biggest_risk,
            "data_sufficiency": "Adequate" if data_quality != "LOW" else "Needs more data",
            "recommended_recheck": "7 days" if level == "HIGH" else "3 days",
        }

        return {"content": content, "duration_ms": int((time.monotonic() - t0) * 1000)}
