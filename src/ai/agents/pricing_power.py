from .base import BaseAgent

class PricingPowerAgent(BaseAgent):
    name = "pricing_power"
    description = "Price elasticity analysis and pricing optimization"
    tier = 1

    async def analyze(self) -> dict:
        avail = self.get_data_availability()
        products = self.ctx.product_performance

        # Choose calculation path
        if avail.is_full:
            # FULL: use real product cost data for margin-based elasticity
            confidence = avail.quality_score
            path = "full"
        elif avail.is_partial:
            # PARTIAL: estimate elasticity from price/velocity
            confidence = avail.quality_score
            path = "partial"
        else:
            # MINIMAL: use benchmark margins + industry elasticity
            confidence = min(0.4, avail.quality_score)
            path = "minimal"

        # MINIMAL: no product data, use benchmarks
        if path == "minimal" or len(products) < 3:
            if len(products) < 3 and path != "minimal":
                return self._insufficient_data("At least 3 products with sales data")
            margin_range = self.get_benchmark_range("gross_margin_pct")
            bench_margin = margin_range.mid if margin_range else 65.0
            insights = [{"type": "benchmark_estimate", "detail": f"Using industry benchmark gross margin of {bench_margin}%"}]
            if margin_range:
                insights[0]["benchmark"] = {"low": margin_range.low, "mid": margin_range.mid, "high": margin_range.high, "source": margin_range.source}
                insights[0]["estimated"] = True
            recommendations = [{
                "action": "Connect POS line-item data for precise analysis",
                "impact": "Improves accuracy from estimated to actual values",
                "effort": "low",
            }]
            return self._result(
                summary=f"Estimated gross margin ~{bench_margin}% (industry benchmark, no product data)",
                score=50,
                insights=insights,
                recommendations=recommendations,
                data={"benchmark_margin_pct": bench_margin, "source": "benchmark", "product_count": len(products)},
                confidence=confidence,
                calculation_path=path,
            )

        safe_to_raise = []
        price_ceiling = []
        total_opportunity_cents = 0

        for p in products:
            price = p.get("price_cents", 0)
            quantity = p.get("quantity_sold", 0)
            revenue = p.get("total_revenue_cents", 0)
            name = p.get("name", "Unknown")
            cost = p.get("cost_cents", 0)

            if price <= 0 or quantity <= 0:
                continue

            # Heuristic: high-volume items with consistent sales are typically inelastic
            avg_daily_qty = quantity / max(self.ctx.analysis_days, 1)

            if avg_daily_qty >= 5:
                # High velocity = likely inelastic
                # FULL path: use cost data to refine increase suggestion
                if path == "full" and cost > 0:
                    margin_pct = (price - cost) / price * 100
                    potential_increase_pct = 3 if margin_pct < 30 else 5 if margin_pct < 60 else 7
                else:
                    potential_increase_pct = 5
                potential_gain = int(revenue * potential_increase_pct / 100)
                entry = {
                    "product": name,
                    "current_price_cents": price,
                    "suggested_increase_pct": potential_increase_pct,
                    "estimated_monthly_gain_cents": potential_gain,
                    "daily_velocity": round(avg_daily_qty, 1),
                    "confidence": "high" if avg_daily_qty >= 10 else "medium",
                }
                if path == "full" and cost > 0:
                    entry["margin_pct"] = round(margin_pct, 1)
                safe_to_raise.append(entry)
                total_opportunity_cents += potential_gain
            elif avg_daily_qty < 1:
                # Low velocity = possibly overpriced
                price_ceiling.append({
                    "product": name,
                    "current_price_cents": price,
                    "daily_velocity": round(avg_daily_qty, 2),
                    "suggestion": "Consider 10-15% price reduction or bundling",
                })

        safe_to_raise.sort(key=lambda x: x["estimated_monthly_gain_cents"], reverse=True)
        score = min(100, 40 + len(safe_to_raise) * 5)

        insights = []
        if safe_to_raise:
            opp_insight = {
                "type": "pricing_opportunity",
                "detail": f"{len(safe_to_raise)} products identified as safe to raise prices — ${total_opportunity_cents/100:,.0f}/month potential",
                "estimated": path != "full",
            }
            margin_range = self.get_benchmark_range("gross_margin_pct")
            if margin_range:
                opp_insight["benchmark"] = {"low": margin_range.low, "mid": margin_range.mid, "high": margin_range.high, "source": margin_range.source}
            insights.append(opp_insight)
        if price_ceiling:
            insights.append({
                "type": "overpriced_items",
                "detail": f"{len(price_ceiling)} products may be overpriced (low velocity)",
                "estimated": path != "full",
            })

        recommendations = []
        for item in safe_to_raise[:3]:
            increase = item["suggested_increase_pct"]
            recommendations.append({
                "action": f"Raise {item['product']} by {increase}% (${item['current_price_cents']/100:.2f} -> ${item['current_price_cents']*(1+increase/100)/100:.2f})",
                "impact_cents": item["estimated_monthly_gain_cents"],
            })

        if path == "partial":
            recommendations.append({"action": "Connect POS line-item data for precise analysis", "impact": "Improves accuracy from estimated to actual values", "effort": "low"})

        return self._result(
            summary=f"${total_opportunity_cents/100:,.0f}/month pricing opportunity across {len(safe_to_raise)} products",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "safe_to_raise": safe_to_raise[:10],
                "price_ceiling_items": price_ceiling[:10],
                "total_opportunity_cents": total_opportunity_cents,
            },
            confidence=confidence,
            calculation_path=path,
        )
