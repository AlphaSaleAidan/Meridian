from .base import BaseAgent


class MoneyLeftAgent(BaseAgent):
    name = "money_left_on_table"
    description = "Headline $ opportunity from all agent outputs"
    tier = 5

    async def analyze(self) -> dict:
        # ── Phase 1: Data Discovery ──────────────────────────
        agent_outputs = getattr(self.ctx, "agent_outputs", {})
        if not agent_outputs:
            return self._insufficient_data("Outputs from tier 1-4 agents")

        avail = self.get_data_availability()

        # ── Phase 2: Path Selection ──────────────────────────
        # Assess quality of upstream agent inputs
        input_confidences = []
        input_paths = []
        for out in agent_outputs.values():
            if isinstance(out, dict) and out.get("status") == "complete":
                input_confidences.append(out.get("data_quality", 0.5))
                input_paths.append(out.get("calculation_path", "minimal"))

        if input_paths:
            minimal_ratio = input_paths.count("minimal") / len(input_paths)
        else:
            minimal_ratio = 1.0

        if minimal_ratio < 0.3:
            calc_path = "full"
        elif minimal_ratio < 0.6:
            calc_path = "partial"
        else:
            calc_path = "minimal"

        # ── Phase 3: Dynamic Calculation ─────────────────────
        source_map = {
            "pricing_power": "Pricing Optimization",
            "discount_analyzer": "Discount Optimization",
            "product_velocity": "Dead Stock Elimination",
            "peak_hours": "Peak Hour Optimization",
            "staffing": "Staffing Efficiency",
            "payment_optimizer": "Payment Fee Reduction",
            "inventory_intel": "Inventory Optimization",
            "waste_shrinkage": "Shrinkage Reduction",
            "employee_performance": "Employee Coaching",
            "revenue_trend": "Revenue Growth",
        }

        breakdown = []
        total_opportunity = 0

        for agent_name, label in source_map.items():
            output = agent_outputs.get(agent_name, {})
            if isinstance(output, dict) and output.get("status") == "complete":
                recs = output.get("recommendations", [])
                agent_total = sum(
                    r.get("impact_cents", 0)
                    for r in recs
                    if isinstance(r.get("impact_cents"), (int, float))
                )
                if agent_total > 0:
                    agent_path = output.get("calculation_path", "minimal")
                    agent_dq = output.get("data_quality", 0.5)
                    is_estimated = agent_path != "full"

                    entry = {
                        "source": label,
                        "agent": agent_name,
                        "impact_cents": agent_total,
                        "estimated": is_estimated,
                        "data_quality": round(agent_dq, 2),
                    }
                    if is_estimated:
                        entry["note"] = (
                            "Based on industry benchmarks — "
                            "connect POS data for precise values"
                        )
                    breakdown.append(entry)
                    total_opportunity += agent_total

        # Sort by opportunity size, add share percentages
        breakdown.sort(key=lambda x: -x["impact_cents"])
        for entry in breakdown:
            entry["monthly_opportunity_cents"] = entry["impact_cents"]
            entry["share_pct"] = round(
                entry["impact_cents"] / max(total_opportunity, 1) * 100, 1,
            )

        score = min(100, max(0, 30 + len(breakdown) * 10))

        insights = []
        estimated_count = sum(1 for b in breakdown if b["estimated"])
        if total_opportunity > 0:
            headline = f"${total_opportunity/100:,.0f}/month left on the table across {len(breakdown)} areas"
            if estimated_count > 0:
                headline += f" ({estimated_count} estimated from benchmarks)"
            insights.append({"type": "headline", "detail": headline})

            if breakdown:
                top = breakdown[0]
                opp_detail = f"Biggest opportunity: {top['source']} — ${top['impact_cents']/100:,.0f}/month"
                if top["estimated"]:
                    opp_detail += " (estimated)"
                insights.append({"type": "biggest_opportunity", "detail": opp_detail})

        recommendations = []
        for b in breakdown[:3]:
            recommendations.append({
                "action": f"Capture {b['source']} opportunity",
                "impact_cents": b["monthly_opportunity_cents"],
            })

        # Confidence = MIN(input confidences) * 0.9
        if input_confidences:
            confidence = round(min(input_confidences) * 0.9, 2)
        else:
            confidence = 0.3

        # Cap confidence if most inputs used minimal path
        if minimal_ratio > 0.5:
            confidence = min(confidence, 0.4)

        return self._result(
            summary=f"${total_opportunity/100:,.0f}/month total opportunity across {len(breakdown)} sources",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "total_opportunity_cents": total_opportunity,
                "breakdown": breakdown,
                "source_count": len(breakdown),
                "estimated_count": estimated_count,
            },
            confidence=confidence,
            calculation_path=calc_path,
        )
