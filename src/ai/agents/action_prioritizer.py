from .base import BaseAgent


class ActionPrioritizerAgent(BaseAgent):
    name = "action_prioritizer"
    description = "Ranks all agent recommendations by ROI and effort into Top 3 daily actions"
    tier = 5

    async def analyze(self) -> dict:
        agent_outputs = getattr(self.ctx, "agent_outputs", {})

        if not agent_outputs:
            return self._insufficient_data("Agent swarm outputs (run other agents first)")

        # Gather all recommendations from completed agents
        all_recs = []
        for agent_name, output in agent_outputs.items():
            if not isinstance(output, dict):
                continue
            if output.get("status") != "complete":
                continue
            recs = output.get("recommendations", [])
            for rec in recs:
                all_recs.append({
                    "source_agent": agent_name,
                    "action": rec.get("action", ""),
                    "impact_estimate": rec.get("impact_estimate", ""),
                    "urgency": rec.get("urgency", "MEDIUM"),
                    "confidence": rec.get("confidence", 0.5),
                })

        if not all_recs:
            return self._result(
                summary="No actionable recommendations from agents",
                score=50,
                insights=[{
                    "type": "no_actions",
                    "detail": "All agents completed but none produced actionable recommendations. The business may be performing well across all metrics.",
                    "severity": "info",
                }],
                recommendations=[],
            )

        # Score each recommendation
        urgency_weights = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        for rec in all_recs:
            urgency_score = urgency_weights.get(rec.get("urgency", "MEDIUM"), 2)
            confidence = rec.get("confidence", 0.5)
            rec["priority_score"] = round(urgency_score * confidence * 25, 1)

        # Sort by priority score
        all_recs.sort(key=lambda r: r["priority_score"], reverse=True)

        # Top 3 actions
        top_3 = all_recs[:3]
        backlog = all_recs[3:]

        insights = []
        for i, action in enumerate(top_3):
            insights.append({
                "type": f"top_action_{i + 1}",
                "detail": f"[{action['source_agent']}] {action['action']}",
                "impact": action["impact_estimate"],
                "priority_score": action["priority_score"],
                "severity": "high" if i == 0 else "medium",
            })

        recommendations = [
            {
                "action": action["action"],
                "impact_estimate": action["impact_estimate"],
                "source": action["source_agent"],
                "priority_score": action["priority_score"],
            }
            for action in top_3
        ]

        score = min(100, int(sum(r["priority_score"] for r in top_3)))

        return self._result(
            summary=f"Top 3 actions from {len(all_recs)} total recommendations across {len(agent_outputs)} agents",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "total_recommendations": len(all_recs),
                "top_3": top_3,
                "backlog_count": len(backlog),
                "agents_with_recs": len(set(r["source_agent"] for r in all_recs)),
            },
        )
