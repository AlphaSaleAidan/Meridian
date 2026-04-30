from .base import BaseAgent


class GrowthScoreAgent(BaseAgent):
    name = "growth_score"
    description = "Executive growth opportunity score 0-100 with monthly action plan"
    tier = 5

    async def analyze(self) -> dict:
        avail = self.get_data_availability()
        agent_outputs = getattr(self.ctx, "agent_outputs", {})

        if not agent_outputs:
            return self._insufficient_data("Requires tier 1-4 agent outputs")

        # Determine path from upstream quality
        completed = {k: v for k, v in agent_outputs.items()
                     if isinstance(v, dict) and v.get("status") == "complete"}
        if not completed:
            return self._insufficient_data("No completed agent analyses available")

        minimal_count = sum(1 for v in completed.values() if v.get("calculation_path") == "minimal")
        minimal_ratio = minimal_count / max(len(completed), 1)

        if minimal_ratio < 0.3:
            path = "full"
            confidence = min(0.8, avail.quality_score)
        elif minimal_ratio < 0.6:
            path = "partial"
            confidence = min(0.55, avail.quality_score)
        else:
            path = "minimal"
            confidence = min(0.35, avail.quality_score)

        # Score each component (0-100)
        def agent_score(name: str, default: int = 50) -> int:
            out = completed.get(name, {})
            return out.get("score", default) if isinstance(out, dict) else default

        def get_recs(name: str) -> list:
            out = completed.get(name, {})
            return out.get("recommendations", []) if isinstance(out, dict) else []

        # Weighted components
        components = {
            "pricing_headroom": {"weight": 0.20, "score": agent_score("pricing_power", 50), "agent": "pricing_power"},
            "staffing_efficiency": {"weight": 0.15, "score": agent_score("staffing", 50), "agent": "staffing"},
            "product_optimization": {"weight": 0.15, "score": (agent_score("product_velocity", 50) + agent_score("inventory_intel", 50)) // 2, "agent": "product_velocity+inventory_intel"},
            "day_leveling": {"weight": 0.10, "score": agent_score("day_of_week", 50), "agent": "day_of_week"},
            "waste_reduction": {"weight": 0.10, "score": agent_score("waste_shrinkage", 50), "agent": "waste_shrinkage"},
            "forecast_accuracy": {"weight": 0.10, "score": agent_score("forecaster", 50), "agent": "forecaster"},
            "customer_retention": {"weight": 0.10, "score": agent_score("customer_ltv", 50), "agent": "customer_ltv"},
            "promotion_roi": {"weight": 0.10, "score": agent_score("promo_roi", 50), "agent": "promo_roi"},
        }

        growth_score = sum(c["weight"] * c["score"] for c in components.values())
        growth_score = max(0, min(100, int(growth_score)))

        # Collect ALL recommendations from ALL agents, ranked by impact
        all_recs = []
        for name, output in completed.items():
            if not isinstance(output, dict):
                continue
            for rec in output.get("recommendations", []):
                if isinstance(rec, dict) and rec.get("impact_cents", 0) > 0:
                    all_recs.append({
                        **rec,
                        "source_agent": name,
                        "estimated": output.get("calculation_path") != "full",
                    })

        all_recs.sort(key=lambda r: r.get("impact_cents", 0), reverse=True)
        top_3 = all_recs[:3]

        insights = []
        insights.append({
            "type": "growth_score",
            "title": f"Growth Opportunity Score: {growth_score}/100",
            "detail": f"Based on {len(completed)} agent analyses. "
                      f"Strongest: {max(components, key=lambda k: components[k]['score'])}. "
                      f"Weakest: {min(components, key=lambda k: components[k]['score'])}.",
            "impact_cents": sum(r.get("impact_cents", 0) for r in top_3),
            "estimated": path != "full",
        })

        # Component breakdown
        for name, comp in sorted(components.items(), key=lambda x: x[1]["score"]):
            insights.append({
                "type": "growth_component",
                "title": f"{name.replace('_', ' ').title()}: {comp['score']}/100",
                "detail": f"Weight: {comp['weight']:.0%} | Source: {comp['agent']}",
                "impact_cents": 0,
            })

        recommendations = []
        for i, rec in enumerate(top_3):
            recommendations.append({
                "rank": i + 1,
                "action": rec.get("action", ""),
                "impact_cents": rec.get("impact_cents", 0),
                "effort": rec.get("effort", "medium"),
                "source_agent": rec.get("source_agent", ""),
                "estimated": rec.get("estimated", True),
            })

        total_opportunity = sum(r.get("impact_cents", 0) for r in all_recs)

        data = {
            "growth_score": growth_score,
            "components": {k: {"score": v["score"], "weight": v["weight"]} for k, v in components.items()},
            "total_opportunity_cents": total_opportunity,
            "top_actions": top_3,
            "agents_analyzed": len(completed),
            "agents_estimated": minimal_count,
        }

        return self._result(
            summary=f"Growth Score {growth_score}/100 | "
                    f"${total_opportunity / 100:,.0f}/mo total opportunity | "
                    f"Top action: {top_3[0]['action'][:60] if top_3 else 'N/A'}",
            score=growth_score,
            insights=insights,
            recommendations=recommendations,
            data=data,
            confidence=confidence,
            calculation_path=path,
        )
