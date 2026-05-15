"""
Business Health Score — Composite 0-100 score from POS data.
Weights: Financial 40%, Operational 30%, Market 20%, Risk 10%.
Grade scale: A+ (95) through F (<45).
"""
import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .ratios import FinancialRatioAnalyzer
from .benchmarks import PublicFinancialBenchmarks

logger = logging.getLogger("meridian.ai.financial.health_score")

_GRADE_MAP = [
    (95, "A+"), (90, "A"), (85, "A-"), (80, "B+"), (75, "B"),
    (70, "B-"), (65, "C+"), (60, "C"), (55, "C-"), (45, "D"), (0, "F"),
]


def _score_to_grade(score: float) -> str:
    for threshold, grade in _GRADE_MAP:
        if score >= threshold:
            return grade
    return "F"


@dataclass
class ComponentScore:
    name: str
    score: float  # 0-100
    weight: float
    details: list[dict] = field(default_factory=list)

    @property
    def weighted(self) -> float:
        return self.score * self.weight

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 1),
            "weight": self.weight,
            "weighted_contribution": round(self.weighted, 1),
            "details": self.details,
        }


class BusinessHealthScore:
    """Composite health score from POS transaction data.

    Usage:
        scorer = BusinessHealthScore("coffee_shop")
        result = scorer.calculate(
            daily_revenue=[...],
            transactions=[...],
            product_performance=[...],
            inventory=[...],
            hourly_revenue=[...],
        )
        print(result["overall_score"], result["grade"])
    """

    def __init__(self, vertical: str = "other"):
        self.vertical = vertical
        self._ratio_analyzer = FinancialRatioAnalyzer(vertical)
        self._benchmarks = PublicFinancialBenchmarks(vertical)

    def calculate(
        self,
        daily_revenue: list[dict],
        transactions: list[dict],
        product_performance: list[dict],
        inventory: list[dict] | None = None,
        hourly_revenue: list[dict] | None = None,
        employee_count: int | None = None,
    ) -> dict:
        """Calculate composite business health score."""
        # Run ratio analysis
        ratio_result = self._ratio_analyzer.analyze(
            daily_revenue=daily_revenue,
            transactions=transactions,
            product_performance=product_performance,
            inventory=inventory,
            hourly_revenue=hourly_revenue,
            employee_count=employee_count,
        )
        ratios = ratio_result.get("ratios", {})

        # Calculate component scores
        financial = self._financial_health(ratios, daily_revenue, transactions)
        operational = self._operational_health(ratios, hourly_revenue, product_performance, inventory)
        market = self._market_position(daily_revenue, transactions, employee_count)
        risk = self._risk_factors(daily_revenue, product_performance, transactions)

        components = [financial, operational, market, risk]
        overall = sum(c.weighted for c in components)
        grade = _score_to_grade(overall)

        # Identify top opportunities and risk alerts
        opportunities = self._find_opportunities(components)
        alerts = self._find_risk_alerts(components)

        return {
            "overall_score": round(overall, 1),
            "grade": grade,
            "components": {
                c.name: c.to_dict() for c in components
            },
            "top_opportunities": opportunities[:5],
            "risk_alerts": alerts[:5],
            "ratio_summary": ratio_result,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Financial Health (40%) ────────────────────────────────

    def _financial_health(
        self, ratios: dict, daily_revenue: list[dict], transactions: list[dict]
    ) -> ComponentScore:
        scores: list[float] = []
        details: list[dict] = []

        daily_totals = [d.get("total_revenue_cents", 0) or 0 for d in daily_revenue]

        # Profitability signal: revenue trend direction
        if len(daily_totals) >= 14:
            mid = len(daily_totals) // 2
            first = statistics.mean(daily_totals[:mid])
            second = statistics.mean(daily_totals[mid:])
            if first > 0:
                change = ((second - first) / first) * 100
                # Map: -20% = 0, 0% = 50, +20% = 100
                s = max(0, min(100, 50 + change * 2.5))
                scores.append(s)
                details.append({
                    "metric": "revenue_trend",
                    "score": round(s, 1),
                    "insight": f"Revenue {'up' if change > 0 else 'down'} {abs(change):.1f}% over period.",
                })

        # Cash flow consistency
        if len(daily_totals) >= 7:
            try:
                avg = statistics.mean(daily_totals)
                stdev = statistics.stdev(daily_totals)
                cv = (stdev / avg * 100) if avg > 0 else 100
                # Low CV = good (CV 0% = 100, CV 50% = 50, CV 100% = 0)
                s = max(0, min(100, 100 - cv))
                scores.append(s)
                details.append({
                    "metric": "cash_flow_consistency",
                    "score": round(s, 1),
                    "insight": f"Revenue CV: {cv:.1f}%. {'Stable' if cv < 30 else 'Volatile'}.",
                })
            except statistics.StatisticsError:
                pass

        # Growth momentum (WoW)
        growth_ratios = ratios.get("growth", [])
        for r in growth_ratios:
            if r.get("name") == "wow_revenue_growth":
                wow = r["value"]
                # Map: -10% = 0, 0% = 40, +5% = 70, +15% = 100
                s = max(0, min(100, 40 + wow * 4))
                scores.append(s)
                details.append({
                    "metric": "growth_momentum",
                    "score": round(s, 1),
                    "insight": f"WoW growth: {wow:+.1f}%.",
                })
                break

        # Transaction volume health
        if transactions and daily_totals:
            days = max(len(daily_totals), 1)
            txn_per_day = len(transactions) / days
            # For most SMBs, 50+ txn/day is healthy
            s = max(0, min(100, txn_per_day * 1.5))
            scores.append(s)
            details.append({
                "metric": "transaction_volume",
                "score": round(s, 1),
                "insight": f"{txn_per_day:.0f} transactions/day.",
            })

        final = statistics.mean(scores) if scores else 50
        return ComponentScore(name="financial", score=final, weight=0.40, details=details)

    # ── Operational Health (30%) ──────────────────────────────

    def _operational_health(self, ratios, hourly_revenue, products, inventory) -> ComponentScore:
        scores, details = [], []

        # Peak hour optimization
        if hourly_revenue:
            active = [h for h in hourly_revenue if (h.get("revenue_cents", 0) or 0) > 0]
            if active:
                revs = [h["revenue_cents"] for h in active]
                avg = statistics.mean(revs)
                if avg > 0:
                    conc = max(revs) / avg
                    s = max(20, min(100, 100 - (conc - 1) * 20))
                    scores.append(s)
                    details.append({"metric": "peak_distribution", "score": round(s, 1),
                                    "insight": f"Peak {conc:.1f}x avg. {'Balanced' if conc < 2 else 'Concentrated'}."})

        # Product diversity
        if products:
            rv = [p.get("revenue_cents", 0) or 0 for p in products if (p.get("revenue_cents", 0) or 0) > 0]
            if len(rv) >= 3:
                top_share = max(rv) / sum(rv)
                s = max(20, min(100, 120 - top_share * 150))
                scores.append(s)
                details.append({"metric": "product_diversity", "score": round(s, 1),
                                "insight": f"Top product: {top_share * 100:.0f}% of revenue."})

        # Inventory turnover from ratio results
        for r in ratios.get("efficiency", []):
            if r.get("name") == "inventory_turnover":
                s = max(0, min(100, r["value"] * 7))
                scores.append(s)
                details.append({"metric": "inventory_turnover", "score": round(s, 1),
                                "insight": f"Turnover: {r['value']:.1f}x."})
                break

        # Active products
        if products:
            active = sum(1 for p in products if (p.get("quantity_sold", 0) or 0) > 0)
            s = min(100, active * 5)
            scores.append(s)
            details.append({"metric": "active_products", "score": round(s, 1),
                            "insight": f"{active} active products."})

        return ComponentScore(name="operational", score=statistics.mean(scores) if scores else 50,
                              weight=0.30, details=details)

    # ── Market Position (20%) ─────────────────────────────────

    def _market_position(
        self,
        daily_revenue: list[dict],
        transactions: list[dict],
        employee_count: int | None,
    ) -> ComponentScore:
        scores: list[float] = []
        details: list[dict] = []

        comparison = self._benchmarks.compare(
            daily_revenue=daily_revenue,
            employee_count=employee_count,
        )

        for comp in comparison.get("comparisons", []):
            pct = comp.get("percentile", 50)
            scores.append(pct)
            details.append({
                "metric": comp["metric"],
                "score": round(pct, 1),
                "status": comp.get("status", ""),
                "insight": comp.get("insight", ""),
            })

        # Pricing competitiveness from ticket size
        if transactions:
            txn_values = [t.get("total_cents", 0) or 0 for t in transactions if t.get("total_cents")]
            if txn_values:
                avg_ticket = statistics.mean(txn_values)
                median_ticket = statistics.median(txn_values)
                # Spread between mean and median indicates pricing health
                if median_ticket > 0:
                    skew_ratio = avg_ticket / median_ticket
                    # skew_ratio near 1.0 = balanced, >1.3 = high-value outliers
                    s = max(30, min(100, 80 - abs(skew_ratio - 1.1) * 50))
                    scores.append(s)
                    details.append({
                        "metric": "pricing_health",
                        "score": round(s, 1),
                        "insight": f"Mean/median ticket ratio: {skew_ratio:.2f}.",
                    })

        final = statistics.mean(scores) if scores else 50
        return ComponentScore(name="market", score=final, weight=0.20, details=details)

    # ── Risk Factors (10%) ────────────────────────────────────

    def _risk_factors(self, daily_revenue, products, transactions) -> ComponentScore:
        scores, details = [], []
        daily_totals = [d.get("total_revenue_cents", 0) or 0 for d in daily_revenue]

        # Revenue concentration (HHI)
        if products:
            rv = [p.get("revenue_cents", 0) or 0 for p in products if (p.get("revenue_cents", 0) or 0) > 0]
            if rv:
                total = sum(rv)
                hhi = sum((v / total * 100) ** 2 for v in rv)
                s = 90 if hhi < 1500 else (60 if hhi < 2500 else 30)
                scores.append(s)
                details.append({"metric": "revenue_concentration", "score": round(s, 1),
                                "insight": f"HHI: {hhi:.0f}. {'Diversified' if hhi < 1500 else 'Concentrated'}."})

        # Day-of-week dependency
        if len(daily_totals) >= 14:
            dow_revs: dict[int, list] = defaultdict(list)
            for d in daily_revenue:
                date_str = str(d.get("date", d.get("day_bucket", "")))
                try:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    dow_revs[dt.weekday()].append(d.get("total_revenue_cents", 0) or 0)
                except (ValueError, TypeError):
                    continue
            if len(dow_revs) >= 5:
                dow_avgs = [statistics.mean(v) for v in dow_revs.values() if v]
                avg_all = statistics.mean(dow_avgs) if dow_avgs else 1
                if avg_all > 0:
                    mx = max(abs(a - avg_all) / avg_all for a in dow_avgs)
                    s = max(20, min(100, 100 - mx * 100))
                    scores.append(s)
                    details.append({"metric": "day_of_week_dependency", "score": round(s, 1),
                                    "insight": f"Max day deviation: {mx * 100:.0f}%."})

        # Zero-revenue days
        if daily_totals:
            zero_pct = sum(1 for d in daily_totals if d == 0) / len(daily_totals) * 100
            s = max(0, 100 - zero_pct * 5)
            scores.append(s)
            details.append({"metric": "zero_revenue_days", "score": round(s, 1),
                            "insight": f"{zero_pct:.0f}% zero-revenue days."})

        # Customer concentration
        if transactions:
            ct: dict[str, int] = {}
            for t in transactions:
                cid = t.get("customer_id")
                if cid:
                    ct[cid] = ct.get(cid, 0) + (t.get("total_cents", 0) or 0)
            if len(ct) >= 5:
                total_cr = sum(ct.values())
                if total_cr > 0:
                    top_share = max(ct.values()) / total_cr
                    s = max(20, min(100, 100 - top_share * 200))
                    scores.append(s)
                    details.append({"metric": "customer_concentration", "score": round(s, 1),
                                    "insight": f"Top customer: {top_share * 100:.1f}% of revenue."})

        return ComponentScore(name="risk", score=statistics.mean(scores) if scores else 65,
                              weight=0.10, details=details)

    # ── Opportunity & Alert Detection ─────────────────────────

    def _find_opportunities(self, components: list[ComponentScore]) -> list[dict]:
        opportunities = []
        for comp in components:
            for detail in comp.details:
                score = detail.get("score", 100)
                if score < 60:
                    opportunities.append({
                        "component": comp.name,
                        "metric": detail.get("metric", ""),
                        "current_score": score,
                        "potential_gain": round(min(30, 80 - score) * comp.weight, 1),
                        "insight": detail.get("insight", ""),
                        "priority": "high" if score < 40 else "medium",
                    })
        opportunities.sort(key=lambda x: x["potential_gain"], reverse=True)
        return opportunities

    def _find_risk_alerts(self, components: list[ComponentScore]) -> list[dict]:
        alerts = []
        for comp in components:
            for detail in comp.details:
                score = detail.get("score", 100)
                if score < 40:
                    alerts.append({
                        "component": comp.name,
                        "metric": detail.get("metric", ""),
                        "severity": "critical" if score < 20 else "warning",
                        "score": score,
                        "insight": detail.get("insight", ""),
                    })
        alerts.sort(key=lambda x: x["score"])
        return alerts
