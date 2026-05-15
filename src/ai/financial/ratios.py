"""
Financial Ratio Analyzer — Computes financial ratios from POS transaction data.
Categories: Liquidity, Profitability, Efficiency, Growth, Cash Flow.
All monetary values in cents.
"""
import logging
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger("meridian.ai.financial.ratios")


@dataclass
class RatioResult:
    """A single computed financial ratio."""
    name: str
    category: str
    value: float
    unit: str  # "pct", "ratio", "cents", "days", "count"
    trend: str = "stable"  # up, down, stable
    benchmark_value: float | None = None
    percentile_rank: float | None = None
    insight: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "value": round(self.value, 4),
            "unit": self.unit,
            "trend": self.trend,
            "benchmark_value": self.benchmark_value,
            "percentile_rank": self.percentile_rank,
            "insight": self.insight,
        }


class FinancialRatioAnalyzer:
    """Computes financial ratios from POS data.

    Accepts the same data shapes found in AnalysisContext:
      - daily_revenue: list[dict] with keys date, total_revenue_cents
      - hourly_revenue: list[dict] with keys hour, revenue_cents
      - transactions: list[dict] with keys created_at, total_cents, customer_id
      - product_performance: list[dict] with keys name, revenue_cents, quantity_sold
      - inventory: list[dict] with keys name, quantity_on_hand, cost_cents
    """

    def __init__(self, vertical: str = "other"):
        self.vertical = vertical

    def analyze(
        self,
        daily_revenue: list[dict],
        transactions: list[dict],
        product_performance: list[dict],
        inventory: list[dict] | None = None,
        hourly_revenue: list[dict] | None = None,
        employee_count: int | None = None,
        sq_ft: int | None = None,
    ) -> dict[str, list[dict]]:
        """Run all ratio calculations. Returns ratios grouped by category."""
        ratios: list[RatioResult] = []

        ratios.extend(self._liquidity(daily_revenue, transactions))
        ratios.extend(self._profitability(daily_revenue, transactions, employee_count, sq_ft))
        ratios.extend(self._efficiency(transactions, product_performance, inventory, hourly_revenue))
        ratios.extend(self._growth(daily_revenue, transactions))
        ratios.extend(self._cash_flow(daily_revenue, transactions))

        grouped: dict[str, list[dict]] = {}
        for r in ratios:
            grouped.setdefault(r.category, []).append(r.to_dict())

        return {
            "ratios": grouped,
            "total_ratios": len(ratios),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Liquidity ──────────────────────────────────────────────

    def _liquidity(self, daily_revenue: list[dict], transactions: list[dict]) -> list[RatioResult]:
        results = []
        if not daily_revenue:
            return results
        daily_totals = [d.get("total_revenue_cents", 0) or 0 for d in daily_revenue]
        avg_daily = statistics.mean(daily_totals) if daily_totals else 0

        # Current ratio proxy (revenue / estimated daily expenses at 90%)
        est_exp = avg_daily * 0.90
        if est_exp > 0:
            crp = avg_daily / est_exp
            results.append(RatioResult(
                name="current_ratio_proxy", category="liquidity", value=crp, unit="ratio",
                insight=f"Revenue-to-expense proxy: {crp:.2f}x. {'Healthy' if crp > 1.0 else 'Below cost coverage'}."))

        # Days cash on hand
        if len(daily_totals) >= 7:
            r7 = daily_totals[-7:]
            avg_r = statistics.mean(r7)
            days_cash = sum(r7) / max(avg_r * 0.90, 1)
            label = "Low" if days_cash < 15 else ("Adequate" if days_cash < 30 else "Strong")
            results.append(RatioResult(
                name="days_cash_on_hand", category="liquidity", value=days_cash, unit="days",
                trend="up" if avg_r > avg_daily else "down", insight=f"{label} ({days_cash:.0f} days)."))
        return results

    # ── Profitability ─────────────────────────────────────────

    def _profitability(
        self,
        daily_revenue: list[dict],
        transactions: list[dict],
        employee_count: int | None,
        sq_ft: int | None,
    ) -> list[RatioResult]:
        results = []
        if not daily_revenue:
            return results

        daily_totals = [d.get("total_revenue_cents", 0) or 0 for d in daily_revenue]
        total_rev = sum(daily_totals)
        days = len(daily_totals) or 1

        # Gross margin trend (compare first half vs second half)
        if len(daily_totals) >= 14:
            mid = len(daily_totals) // 2
            first_half_avg = statistics.mean(daily_totals[:mid])
            second_half_avg = statistics.mean(daily_totals[mid:])
            if first_half_avg > 0:
                margin_change_pct = ((second_half_avg - first_half_avg) / first_half_avg) * 100
                trend = "up" if margin_change_pct > 1 else ("down" if margin_change_pct < -1 else "stable")
                results.append(RatioResult(
                    name="gross_margin_trend",
                    category="profitability",
                    value=margin_change_pct,
                    unit="pct",
                    trend=trend,
                    insight=(
                        f"Revenue {'increased' if margin_change_pct > 0 else 'decreased'} "
                        f"{abs(margin_change_pct):.1f}% comparing recent vs earlier period."
                    ),
                ))

        # Revenue per employee / per sq ft
        annual_rev_est = (total_rev / days) * 365
        if employee_count and employee_count > 0:
            rev_per_emp = annual_rev_est / employee_count
            results.append(RatioResult(
                name="revenue_per_employee", category="profitability",
                value=rev_per_emp, unit="cents",
                insight=f"${rev_per_emp / 100:,.0f}/yr per employee (annualized).",
            ))
        if sq_ft and sq_ft > 0:
            rev_per_sqft = annual_rev_est / sq_ft
            results.append(RatioResult(
                name="revenue_per_sqft", category="profitability",
                value=rev_per_sqft, unit="cents",
                insight=f"${rev_per_sqft / 100:,.0f}/yr per sq ft.",
            ))

        # Average transaction value
        if transactions:
            txn_values = [t.get("total_cents", 0) or 0 for t in transactions if t.get("total_cents")]
            if txn_values:
                avg_ticket = statistics.mean(txn_values)
                results.append(RatioResult(
                    name="avg_ticket_value",
                    category="profitability",
                    value=avg_ticket,
                    unit="cents",
                    insight=f"Average ticket: ${avg_ticket / 100:.2f}.",
                ))

        return results

    # ── Efficiency ────────────────────────────────────────────

    def _efficiency(
        self,
        transactions: list[dict],
        products: list[dict],
        inventory: list[dict] | None,
        hourly_revenue: list[dict] | None,
    ) -> list[RatioResult]:
        results = []

        # Inventory turnover (if data available)
        if inventory and products:
            total_cogs = sum(p.get("cost_cents", 0) or 0 for p in products)
            total_inv_value = sum(
                (i.get("quantity_on_hand", 0) or 0) * (i.get("cost_cents", 0) or 0)
                for i in inventory
            )
            if total_inv_value > 0 and total_cogs > 0:
                # Annualize COGS from observed period
                turnover = total_cogs / total_inv_value
                if turnover < 4:
                    insight = "Low turnover — consider clearance sales or order reduction."
                elif turnover < 12:
                    insight = "Moderate turnover. Room for optimization."
                else:
                    insight = "Strong inventory velocity."
                results.append(RatioResult(
                    name="inventory_turnover",
                    category="efficiency",
                    value=turnover,
                    unit="ratio",
                    insight=insight,
                ))

        # Sales per labor hour (from hourly revenue data)
        if hourly_revenue:
            operating_hours = [h for h in hourly_revenue if (h.get("revenue_cents", 0) or 0) > 0]
            if operating_hours:
                total_hourly_rev = sum(h.get("revenue_cents", 0) for h in operating_hours)
                avg_per_hour = total_hourly_rev / len(operating_hours)
                results.append(RatioResult(
                    name="sales_per_operating_hour",
                    category="efficiency",
                    value=avg_per_hour,
                    unit="cents",
                    insight=f"${avg_per_hour / 100:.0f} per operating hour on average.",
                ))

        # Transactions per day
        if transactions:
            dates = set()
            for t in transactions:
                d = t.get("created_at", "")
                if isinstance(d, str) and len(d) >= 10:
                    dates.add(d[:10])
            if dates:
                txn_per_day = len(transactions) / len(dates)
                results.append(RatioResult(
                    name="transactions_per_day",
                    category="efficiency",
                    value=txn_per_day,
                    unit="count",
                    insight=f"{txn_per_day:.0f} transactions per operating day.",
                ))

        return results

    # ── Growth ────────────────────────────────────────────────

    def _growth(self, daily_revenue: list[dict], transactions: list[dict]) -> list[RatioResult]:
        results = []
        if not daily_revenue:
            return results

        daily_totals = [d.get("total_revenue_cents", 0) or 0 for d in daily_revenue]

        # WoW growth (last 7 vs prior 7)
        if len(daily_totals) >= 14:
            recent_7 = sum(daily_totals[-7:])
            prior_7 = sum(daily_totals[-14:-7])
            if prior_7 > 0:
                wow = ((recent_7 - prior_7) / prior_7) * 100
                trend = "up" if wow > 0.5 else ("down" if wow < -0.5 else "stable")
                results.append(RatioResult(
                    name="wow_revenue_growth",
                    category="growth",
                    value=wow,
                    unit="pct",
                    trend=trend,
                    insight=f"Week-over-week revenue {'grew' if wow > 0 else 'declined'} {abs(wow):.1f}%.",
                ))

        # MoM growth (last 30 vs prior 30)
        if len(daily_totals) >= 60:
            recent_30 = sum(daily_totals[-30:])
            prior_30 = sum(daily_totals[-60:-30])
            if prior_30 > 0:
                mom = ((recent_30 - prior_30) / prior_30) * 100
                trend = "up" if mom > 0.5 else ("down" if mom < -0.5 else "stable")
                results.append(RatioResult(
                    name="mom_revenue_growth", category="growth",
                    value=mom, unit="pct", trend=trend,
                    insight=f"MoM revenue {'grew' if mom > 0 else 'declined'} {abs(mom):.1f}%.",
                ))

        # Basket size trend
        if transactions and len(transactions) >= 20:
            txn_values = [t.get("total_cents", 0) or 0 for t in transactions if t.get("total_cents")]
            if len(txn_values) >= 20:
                mid = len(txn_values) // 2
                first_avg = statistics.mean(txn_values[:mid])
                second_avg = statistics.mean(txn_values[mid:])
                if first_avg > 0:
                    basket_change = ((second_avg - first_avg) / first_avg) * 100
                    trend = "up" if basket_change > 1 else ("down" if basket_change < -1 else "stable")
                    results.append(RatioResult(
                        name="basket_size_trend",
                        category="growth",
                        value=basket_change,
                        unit="pct",
                        trend=trend,
                        insight=(
                            f"Average basket size {'increased' if basket_change > 0 else 'decreased'} "
                            f"{abs(basket_change):.1f}% over the analysis period."
                        ),
                    ))

        # Customer growth (unique customers per week)
        if transactions:
            weekly_customers: dict[str, set] = {}
            for t in transactions:
                cid = t.get("customer_id")
                d = t.get("created_at", "")
                if cid and isinstance(d, str) and len(d) >= 10:
                    try:
                        dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
                        week_key = dt.strftime("%Y-W%W")
                        weekly_customers.setdefault(week_key, set()).add(cid)
                    except (ValueError, TypeError):
                        continue
            if len(weekly_customers) >= 2:
                weeks_sorted = sorted(weekly_customers.keys())
                recent_count = len(weekly_customers[weeks_sorted[-1]])
                prior_count = len(weekly_customers[weeks_sorted[-2]])
                if prior_count > 0:
                    cust_growth = ((recent_count - prior_count) / prior_count) * 100
                    results.append(RatioResult(
                        name="customer_growth_wow",
                        category="growth",
                        value=cust_growth,
                        unit="pct",
                        trend="up" if cust_growth > 0 else "down",
                        insight=(
                            f"Unique customers {'grew' if cust_growth > 0 else 'declined'} "
                            f"{abs(cust_growth):.1f}% week-over-week."
                        ),
                    ))

        return results

    # ── Cash Flow ─────────────────────────────────────────────

    _EXPENSE_RATIOS = {
        "coffee_shop": 0.92, "restaurant": 0.95, "quick_service": 0.92,
        "retail": 0.85, "bar": 0.88, "grocery": 0.97, "salon": 0.82,
        "auto_repair": 0.80, "fitness": 0.78, "other": 0.88,
    }

    def _cash_flow(self, daily_revenue: list[dict], transactions: list[dict]) -> list[RatioResult]:
        results = []
        if not daily_revenue:
            return results

        daily_totals = [d.get("total_revenue_cents", 0) or 0 for d in daily_revenue]
        avg_daily_rev = statistics.mean(daily_totals) if daily_totals else 0
        if avg_daily_rev <= 0:
            return results

        results.append(RatioResult(
            name="daily_cash_generation", category="cash_flow",
            value=avg_daily_rev, unit="cents",
            insight=f"Generating ${avg_daily_rev / 100:,.0f}/day on average.",
        ))

        expense_ratio = self._EXPENSE_RATIOS.get(self.vertical, 0.88)
        daily_burn = avg_daily_rev * expense_ratio
        daily_net = avg_daily_rev - daily_burn
        results.append(RatioResult(
            name="estimated_daily_profit", category="cash_flow",
            value=daily_net, unit="cents", trend="up" if daily_net > 0 else "down",
            insight=f"Est. ${daily_net / 100:,.0f}/day net ({expense_ratio * 100:.0f}% expense ratio).",
        ))

        # Break-even daily revenue (fixed ~45% of expenses for SMBs)
        est_monthly_fixed = daily_burn * 30 * 0.45
        variable_per_dollar = expense_ratio * 0.55
        if (1.0 - variable_per_dollar) > 0:
            breakeven_daily = (est_monthly_fixed / (1.0 - variable_per_dollar)) / 30
            above = avg_daily_rev > breakeven_daily
            results.append(RatioResult(
                name="breakeven_daily_revenue", category="cash_flow",
                value=breakeven_daily, unit="cents",
                insight=f"Break-even: ${breakeven_daily / 100:,.0f}/day. {'Above.' if above else 'Below — act now.'}",
            ))

        # Revenue volatility
        if len(daily_totals) >= 7:
            try:
                cv = (statistics.stdev(daily_totals) / avg_daily_rev) * 100
                label = "Low" if cv < 20 else ("Moderate" if cv < 40 else "High")
                results.append(RatioResult(
                    name="revenue_volatility_cv", category="cash_flow",
                    value=cv, unit="pct", insight=f"{label} revenue volatility (CV {cv:.0f}%).",
                ))
            except statistics.StatisticsError:
                pass

        return results
