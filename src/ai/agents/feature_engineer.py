from .base import BaseAgent
from collections import Counter


class FeatureEngineerAgent(BaseAgent):
    name = "feature_engineer"
    description = "Identifies highest-value features based on agent findings and data gaps"
    tier = 6

    async def analyze(self) -> dict:
        agent_outputs = getattr(self.ctx, "agent_outputs", {})

        if not agent_outputs:
            return self._insufficient_data("Agent swarm outputs")

        # Analyze agent outputs to find patterns and gaps
        data_gaps = []
        feature_ideas = []
        agent_errors = []
        insufficient_data_agents = []

        for agent_name, output in agent_outputs.items():
            if not isinstance(output, dict):
                continue

            status = output.get("status", "")
            if status == "error":
                agent_errors.append(agent_name)
            elif status == "insufficient_data":
                insufficient_data_agents.append(agent_name)
                missing = output.get("missing", "")
                if missing:
                    data_gaps.append({
                        "agent": agent_name,
                        "missing_data": missing,
                        "feature": f"Data connector for {missing}",
                        "priority": "high",
                    })

        # Identify feature opportunities based on what IS working
        working_agents = [
            name for name, out in agent_outputs.items()
            if isinstance(out, dict) and out.get("status") == "complete"
        ]

        # Count recommendation themes
        theme_counter: Counter = Counter()
        for output in agent_outputs.values():
            if not isinstance(output, dict):
                continue
            for rec in output.get("recommendations", []):
                action = rec.get("action", "").lower()
                if "loyalty" in action or "retention" in action:
                    theme_counter["loyalty_features"] += 1
                if "pricing" in action or "margin" in action:
                    theme_counter["pricing_tools"] += 1
                if "staff" in action or "schedule" in action:
                    theme_counter["scheduling_tools"] += 1
                if "inventory" in action or "stock" in action:
                    theme_counter["inventory_automation"] += 1
                if "marketing" in action or "promo" in action:
                    theme_counter["marketing_automation"] += 1
                if "camera" in action or "traffic" in action or "vision" in action:
                    theme_counter["vision_enhancements"] += 1

        # Build feature roadmap from themes
        for theme, count in theme_counter.most_common(5):
            feature_ideas.append({
                "feature": theme.replace("_", " ").title(),
                "demand_signals": count,
                "priority": "high" if count >= 3 else "medium" if count >= 2 else "low",
                "source": "agent_recommendation_analysis",
            })

        insights = []

        if data_gaps:
            insights.append({
                "type": "data_gaps",
                "detail": f"{len(data_gaps)} agents lack required data — connecting these sources would unlock {len(data_gaps)} more analytics",
                "severity": "high",
                "gaps": data_gaps[:5],
            })

        if feature_ideas:
            top = feature_ideas[0]
            insights.append({
                "type": "top_feature_opportunity",
                "detail": f"Most-requested capability: {top['feature']} ({top['demand_signals']} signals from agents)",
                "severity": "medium",
            })

        if agent_errors:
            insights.append({
                "type": "reliability_gap",
                "detail": f"{len(agent_errors)} agents failed — reliability improvements needed: {', '.join(agent_errors[:5])}",
                "severity": "high",
            })

        coverage = len(working_agents) / max(len(agent_outputs), 1)
        insights.append({
            "type": "agent_coverage",
            "detail": f"{len(working_agents)}/{len(agent_outputs)} agents producing insights ({coverage:.0%} coverage)",
            "severity": "info" if coverage > 0.8 else "medium",
        })

        recommendations = []
        for gap in data_gaps[:3]:
            recommendations.append({
                "action": f"Build {gap['feature']} to enable {gap['agent']} agent",
                "impact_estimate": "Unlocks new analytics dimension",
            })
        for idea in feature_ideas[:2]:
            recommendations.append({
                "action": f"Invest in {idea['feature']} — {idea['demand_signals']} demand signals",
                "impact_estimate": "Directly addresses most common agent recommendations",
            })

        score = int(coverage * 60 + min(len(feature_ideas), 5) * 8)

        return self._result(
            summary=(
                f"Coverage {coverage:.0%}, {len(data_gaps)} data gaps, "
                f"{len(feature_ideas)} feature opportunities, {len(agent_errors)} agent errors"
            ),
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "working_agents": working_agents,
                "insufficient_data_agents": insufficient_data_agents,
                "agent_errors": agent_errors,
                "data_gaps": data_gaps,
                "feature_ideas": feature_ideas,
                "theme_counts": dict(theme_counter),
                "coverage": round(coverage, 3),
            },
        )
