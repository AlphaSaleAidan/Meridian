from .base import BaseAgent
from collections import defaultdict

class CategoryMixAgent(BaseAgent):
    name = "category_mix"
    description = "Category revenue share and mix optimization"
    tier = 2

    async def analyze(self) -> dict:
        path, confidence = self._select_path()
        products = self.ctx.product_performance

        if path == "minimal" or len(products) < 3:
            if len(products) < 3 and path != "minimal":
                return self._insufficient_data("At least 3 products with category data")
            bench = self.get_benchmark_range("category_concentration_max_pct")
            bench_conc = bench.mid if bench else 40.0
            return self._benchmark_fallback(
                "category_concentration_max_pct",
                f"Estimated healthy category concentration under {bench_conc}% (industry benchmark)",
                {"benchmark_concentration_max_pct": bench_conc, "product_count": len(products)},
            )

        cat_revenue = defaultdict(int)
        cat_quantity = defaultdict(int)
        cat_margin = defaultdict(int)
        cat_count = defaultdict(int)

        for p in products:
            cat = p.get("category", "Uncategorized") or "Uncategorized"
            rev = p.get("total_revenue_cents", 0)
            qty = p.get("quantity_sold", 0)
            cost = p.get("cost_cents", 0)
            cat_revenue[cat] += rev
            cat_quantity[cat] += qty
            cat_count[cat] += 1
            if cost > 0 and qty > 0:
                cat_margin[cat] += (p.get("price_cents", 0) - cost) * qty

        total_rev = sum(cat_revenue.values())
        categories = []
        for cat in cat_revenue:
            rev = cat_revenue[cat]
            share = round(rev / max(total_rev, 1) * 100, 1)
            categories.append({
                "category": cat,
                "revenue_cents": rev,
                "revenue_share_pct": share,
                "quantity_sold": cat_quantity[cat],
                "product_count": cat_count[cat],
                "margin_contribution_cents": cat_margin.get(cat, 0),
            })

        categories.sort(key=lambda c: c["revenue_cents"], reverse=True)

        # Over/under-indexed detection
        avg_share = 100 / max(len(categories), 1)
        over_indexed = [c for c in categories if c["revenue_share_pct"] > avg_share * 2]
        under_indexed = [c for c in categories if c["revenue_share_pct"] < avg_share * 0.3 and c["quantity_sold"] > 0]

        # Concentration risk
        top_cat_share = categories[0]["revenue_share_pct"] if categories else 0
        score = max(0, 100 - max(0, (top_cat_share - 50) * 2))

        insights = []
        if top_cat_share > 60:
            conc_insight = {"type": "concentration_risk", "detail": f"{categories[0]['category']} drives {top_cat_share}% of revenue — high concentration risk", "estimated": path != "full"}
            conc_range = self.get_benchmark_range("category_concentration_max_pct")
            if conc_range:
                conc_insight["benchmark"] = {"low": conc_range.low, "mid": conc_range.mid, "high": conc_range.high, "source": conc_range.source}
            insights.append(conc_insight)
        if under_indexed:
            insights.append({"type": "underperforming_categories", "detail": f"{len(under_indexed)} categories underperforming: {', '.join(c['category'] for c in under_indexed[:3])}", "estimated": path != "full"})

        recommendations = []
        if under_indexed:
            recommendations.append({"action": f"Promote underperforming categories: {', '.join(c['category'] for c in under_indexed[:3])}", "impact_cents": 0})
        if top_cat_share > 60:
            recommendations.append({"action": "Diversify revenue across categories to reduce concentration risk", "impact_cents": 0})

        if path == "partial":
            recommendations.append({"action": "Connect POS line-item data for precise analysis", "impact": "Improves accuracy from estimated to actual values", "effort": "low"})

        return self._result(
            summary=f"{len(categories)} categories, top category at {top_cat_share}% share",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "categories": categories,
                "over_indexed": over_indexed,
                "under_indexed": under_indexed,
                "category_count": len(categories),
            },
            confidence=confidence,
            calculation_path=path,
        )
