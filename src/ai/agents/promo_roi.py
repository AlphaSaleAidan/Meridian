from .base import BaseAgent
from collections import defaultdict


class PromoROIAgent(BaseAgent):
    name = "promo_roi"
    description = "Promotion ROI calculator with diminishing returns detection"
    tier = 5

    async def analyze(self) -> dict:
        avail = self.get_data_availability()
        agent_outputs = getattr(self.ctx, "agent_outputs", {})
        txns = getattr(self.ctx, "transactions", []) or []
        daily = getattr(self.ctx, "daily_revenue", []) or []

        discount_output = agent_outputs.get("discount_analyzer", {})
        dow_output = agent_outputs.get("day_of_week", {})

        if not txns and not daily:
            return self._insufficient_data("Transaction data required for promotion analysis")

        # Path selection
        has_discounts = any(t.get("discount_cents", 0) > 0 for t in txns[:100])
        if avail.is_full and has_discounts:
            path = "full"
            confidence = min(0.8, avail.quality_score)
        elif has_discounts:
            path = "partial"
            confidence = min(0.55, avail.quality_score)
        else:
            path = "minimal"
            confidence = min(0.3, avail.quality_score)

        insights = []
        recommendations = []
        promo_days = {}
        roi = 0.0
        incremental = 0
        promo_discount_total = 0

        if path in ("full", "partial"):
            # Identify promotion periods (days with above-average discount rate)
            daily_discounts = defaultdict(lambda: {"discount": 0, "revenue": 0, "count": 0})
            for t in txns:
                date = str(t.get("transaction_at", t.get("created_at", "")))[:10]
                if date:
                    daily_discounts[date]["discount"] += t.get("discount_cents", 0)
                    daily_discounts[date]["revenue"] += t.get("total_cents", 0)
                    daily_discounts[date]["count"] += 1

            if not daily_discounts:
                for d in daily:
                    date = d.get("date", "")
                    daily_discounts[date]["revenue"] = d.get("revenue_cents", 0)

            total_discount = sum(d["discount"] for d in daily_discounts.values())
            total_revenue = sum(d["revenue"] for d in daily_discounts.values())
            avg_daily_discount = total_discount / max(len(daily_discounts), 1)

            # Promo days = days with discount > 2x average
            non_promo_days = {}
            for date, vals in daily_discounts.items():
                if vals["discount"] > avg_daily_discount * 2 and avg_daily_discount > 0:
                    promo_days[date] = vals
                else:
                    non_promo_days[date] = vals

            if promo_days:
                promo_avg_rev = sum(d["revenue"] for d in promo_days.values()) / len(promo_days)
                baseline_avg_rev = sum(d["revenue"] for d in non_promo_days.values()) / max(len(non_promo_days), 1)
                promo_discount_total = sum(d["discount"] for d in promo_days.values())

                incremental = (promo_avg_rev - baseline_avg_rev) * len(promo_days)
                roi = (incremental - promo_discount_total) / max(promo_discount_total, 1)

                insights.append({
                    "type": "promo_roi",
                    "title": f"Promotion ROI: {roi:.0%}",
                    "detail": f"{len(promo_days)} promo days detected. "
                              f"Avg promo day ${promo_avg_rev / 100:.0f} vs "
                              f"baseline ${baseline_avg_rev / 100:.0f}. "
                              f"Discount cost ${promo_discount_total / 100:.0f}.",
                    "impact_cents": int(incremental),
                    "estimated": path != "full",
                })

                # Best promo day analysis
                if dow_output.get("data", {}).get("day_stats"):
                    weakest = dow_output["data"]["day_stats"][-1] if dow_output["data"]["day_stats"] else None
                    if weakest:
                        recommendations.append({
                            "action": f"Focus promotions on {weakest.get('day', 'weekday')} — weakest day benefits most",
                            "impact_cents": int(baseline_avg_rev * 0.15),
                            "effort": "low",
                        })

                # Diminishing returns check
                if len(promo_days) >= 4:
                    sorted_promos = sorted(promo_days.items())
                    first_half = sorted_promos[:len(sorted_promos) // 2]
                    second_half = sorted_promos[len(sorted_promos) // 2:]
                    first_roi_proxy = sum(d["revenue"] - d["discount"] for _, d in first_half) / max(len(first_half), 1)
                    second_roi_proxy = sum(d["revenue"] - d["discount"] for _, d in second_half) / max(len(second_half), 1)

                    if first_roi_proxy > 0 and second_roi_proxy / first_roi_proxy < 0.8:
                        insights.append({
                            "type": "promo_fatigue",
                            "title": "Promotion fatigue detected",
                            "detail": "Recent promo ROI is declining >20% vs earlier promos. "
                                      "Customers may be expecting discounts.",
                            "impact_cents": int(abs(first_roi_proxy - second_roi_proxy) * len(second_half)),
                        })
                        recommendations.append({
                            "action": "Reduce promo frequency — switch to targeted, time-limited offers",
                            "impact_cents": int(promo_discount_total * 0.3 / max(len(promo_days), 1) * 30),
                            "effort": "medium",
                        })
            else:
                insights.append({
                    "type": "promo_roi",
                    "title": "No significant promotion activity detected",
                    "detail": f"Total discounts ${total_discount / 100:.0f} over {len(daily_discounts)} days "
                              f"({total_discount / max(total_revenue, 1) * 100:.1f}% of revenue)",
                    "impact_cents": 0,
                })
                roi = 0.0
                incremental = 0
                promo_discount_total = 0

            # Cannibalization check
            if promo_days and non_promo_days:
                promo_non_discount_rev = sum(d["revenue"] - d["discount"] for d in promo_days.values()) / max(len(promo_days), 1)
                non_promo_net = sum(d["revenue"] for d in non_promo_days.values()) / max(len(non_promo_days), 1)
                if promo_non_discount_rev < non_promo_net * 0.95:
                    net_impact = int((promo_non_discount_rev - non_promo_net) * len(promo_days))
                    insights.append({
                        "type": "cannibalization",
                        "title": "Possible promotion cannibalization",
                        "detail": "Non-discounted revenue drops during promo periods, "
                                  "suggesting customers shift purchases to discounted items.",
                        "impact_cents": net_impact,
                    })

        else:
            # Minimal path
            discount_rate = self.get_benchmark("healthy_discount_rate_pct") or 3.0
            total_revenue = sum(d.get("revenue_cents", 0) for d in daily) if daily else 0
            est_discount = int(total_revenue * discount_rate / 100)
            roi = 0.0
            incremental = 0
            promo_discount_total = est_discount

            insights.append({
                "type": "promo_roi",
                "title": "Promotion ROI unavailable — no discount data",
                "detail": f"Industry avg discount rate: {discount_rate:.1f}%. "
                          f"Connect line-item data to track promotion effectiveness.",
                "impact_cents": 0,
                "estimated": True,
            })
            recommendations.append({
                "action": "Connect POS discount data to track promotion ROI",
                "impact": "Enables precise measurement of promotion effectiveness",
                "effort": "low",
            })

        score = max(0, min(100, int(50 + roi * 30))) if roi else 30

        data = {
            "roi": round(roi, 3) if isinstance(roi, float) else 0,
            "incremental_revenue_cents": int(incremental) if incremental else 0,
            "total_discount_cost_cents": int(promo_discount_total),
            "promo_day_count": len(promo_days) if path != "minimal" else 0,
        }

        return self._result(
            summary=f"Promo ROI {roi:.0%} | ${int(incremental) / 100:.0f} incremental" if roi else "Insufficient promotion data for ROI analysis",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data=data,
            confidence=confidence,
            calculation_path=path,
        )
