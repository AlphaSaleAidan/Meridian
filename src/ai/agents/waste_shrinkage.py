from .base import BaseAgent
from collections import defaultdict
from datetime import datetime


class WasteShrinkageAgent(BaseAgent):
    name = "waste_shrinkage"
    description = "Shrinkage rate, void patterns, annual loss projection"
    tier = 4

    async def analyze(self) -> dict:
        avail = self.get_data_availability()

        if avail.is_full:
            confidence = avail.quality_score
            path = "full"
        elif avail.is_partial:
            confidence = avail.quality_score
            path = "partial"
        else:
            confidence = min(0.4, avail.quality_score)
            path = "minimal"

        # --- MINIMAL path: cannot calculate without inventory ---
        if path == "minimal" or not avail.has_transactions:
            return self._insufficient_data(
                "Connect inventory to track waste — need transaction or inventory data for shrinkage analysis"
            )

        txns = self.ctx.transactions
        if len(txns) < 20:
            return self._insufficient_data("At least 20 transactions")

        # --- FULL path: real inventory adjustments ---
        if avail.has_inventory:
            confidence = 0.9
            path = "full"
        else:
            # --- PARTIAL path: estimate from void/refund patterns ---
            confidence = min(confidence, 0.5)
            path = "partial"

        total_rev = sum(t.get("total_cents", 0) for t in txns)
        voids = [
            t for t in txns
            if t.get("total_cents", 0) < 0 or t.get("status") == "voided"
        ]
        void_total = abs(sum(t.get("total_cents", 0) for t in voids))
        shrinkage_pct = round(void_total / max(total_rev, 1) * 100, 2)

        # Void patterns by employee
        emp_voids = defaultdict(int)
        for v in voids:
            emp = v.get("employee_name", "Unknown")
            emp_voids[emp] += 1

        # Void patterns by hour
        hour_voids = defaultdict(int)
        for v in voids:
            try:
                dt = datetime.fromisoformat(
                    v.get("transaction_at", "").replace("Z", "+00:00")
                )
                hour_voids[dt.hour] += 1
            except (ValueError, AttributeError):
                pass

        suspicious = [
            {"employee": e, "void_count": c}
            for e, c in emp_voids.items()
            if c >= 3
        ]
        suspicious.sort(key=lambda x: -x["void_count"])

        # Worst waste items: top 5 by void/waste cost
        item_waste = defaultdict(int)
        for v in voids:
            items = v.get("items") or v.get("line_items") or []
            for item in items:
                name = item.get("name") or item.get("product_name") or "Unknown"
                item_waste[name] += abs(item.get("total_cents", 0) or item.get("amount_cents", 0))
        if not item_waste and voids:
            # Fall back to transaction-level if no line items
            for v in voids:
                desc = v.get("description") or v.get("employee_name", "Void")
                item_waste[desc] += abs(v.get("total_cents", 0))
        worst_waste_items = sorted(
            [{"item": k, "waste_cost_cents": v} for k, v in item_waste.items()],
            key=lambda x: -x["waste_cost_cents"],
        )[:5]

        analysis_days = getattr(self.ctx, "analysis_days", 30)
        annual_loss = int(void_total * 365 / max(analysis_days, 1))
        bench_range = self.get_benchmark_range("shrinkage_pct")
        benchmark = bench_range.mid if bench_range else 1.6
        benchmark_source = bench_range.source if bench_range else "industry default"
        score = max(0, 100 - max(0, (shrinkage_pct - benchmark) * 25))

        insights = []
        insights.append({
            "type": "shrinkage_rate",
            "detail": (
                f"Shrinkage rate {shrinkage_pct}%"
                f" (industry avg: {benchmark}%, source: {benchmark_source})"
            ),
        })
        if worst_waste_items:
            top_item = worst_waste_items[0]
            insights.append({
                "type": "worst_waste_item",
                "detail": (
                    f"Highest waste item: {top_item['item']}"
                    f" (${top_item['waste_cost_cents'] / 100:,.2f})"
                ),
            })
        if suspicious:
            names = ", ".join(s["employee"] for s in suspicious[:3])
            insights.append({
                "type": "suspicious_clusters",
                "detail": (
                    f"{len(suspicious)} employees with 3+ voids: {names}"
                ),
                "severity": "high",
            })

        recommendations = []
        if shrinkage_pct > benchmark:
            savings = int(total_rev * (shrinkage_pct - benchmark) / 100)
            recommendations.append({
                "action": (
                    "Investigate void patterns — reducing to industry avg"
                    f" would save ${savings / 100:,.0f}"
                ),
                "impact_cents": savings,
            })
        if suspicious:
            names = ", ".join(s["employee"] for s in suspicious[:3])
            recommendations.append({
                "action": f"Review void activity for: {names}",
                "impact_cents": 0,
            })

        if path != "full":
            recommendations.append({
                "action": "Connect more data sources for precise analysis",
                "impact": "Improves accuracy from estimated to actual",
                "effort": "low",
            })

        return self._result(
            summary=(
                f"Shrinkage {shrinkage_pct}%"
                f" (${void_total / 100:,.0f}),"
                f" projected ${annual_loss / 100:,.0f}/year loss"
            ),
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "shrinkage_pct": shrinkage_pct,
                "void_total_cents": void_total,
                "void_count": len(voids),
                "projected_annual_loss_cents": annual_loss,
                "suspicious_employees": suspicious,
                "void_by_hour": dict(hour_voids),
                "worst_waste_items": worst_waste_items,
                "benchmark_source": benchmark_source,
            },
            confidence=confidence,
            calculation_path=path,
        )
