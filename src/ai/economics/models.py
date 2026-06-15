"""
Economic Models — Financial analysis frameworks for Meridian.

Implements:
  • Price elasticity estimation (arc elasticity + panel OLS + DoubleML)
  • Break-even analysis
  • Marginal revenue analysis
  • Revenue concentration risk (Herfindahl-Hirschman Index)
  • Working capital efficiency scoring
  • Seasonal decomposition (additive model)
  • Customer acquisition cost estimation
"""
import math
import logging

logger = logging.getLogger("meridian.ai.economics.models")

# Optional ML deps for the Wave-1A causal-elasticity path. Both are heavy
# (statsmodels pulls scipy; econml pulls LightGBM + scikit-learn). Gated
# behind try/except so that the file imports cleanly in the current prod
# Python where neither is installed; estimate_price_elasticity_panel
# returns a partial result with the unavailable estimator marked
# ``unavailable`` rather than crashing.
try:
    import statsmodels.api as _sm  # type: ignore[import-not-found]
    HAS_STATSMODELS = True
except Exception:  # noqa: BLE001
    HAS_STATSMODELS = False

try:
    from econml.dml import LinearDML  # type: ignore[import-not-found]
    HAS_ECONML = True
except Exception:  # noqa: BLE001
    HAS_ECONML = False


class EconomicModels:
    """
    Financial analysis toolkit used by insight generators.
    
    Each method returns a dict with:
      - Calculated metrics
      - Plain-English interpretation
      - Recommended actions
      - Relevant citations
    """

    @staticmethod
    def estimate_price_elasticity(
        price_change_pct: float,
        quantity_change_pct: float,
    ) -> dict:
        """
        Arc price elasticity of demand.
        
        Ed = %ΔQ / %ΔP
        
        |Ed| < 1 → Inelastic (safe to raise prices)
        |Ed| = 1 → Unit elastic
        |Ed| > 1 → Elastic (price-sensitive customers)
        
        Citation: Journal of Marketing Research meta-analysis (2023)
        """
        if abs(price_change_pct) < 0.01:
            return {"elasticity": 0, "interpretation": "insufficient_data"}

        elasticity = round(quantity_change_pct / price_change_pct, 2)
        abs_e = abs(elasticity)

        if abs_e < 0.5:
            interp = "highly_inelastic"
            guidance = (
                "Demand is highly insensitive to price changes. "
                "You have significant pricing power — a 5-10% price increase "
                "would likely result in less than 2.5-5% volume decline, "
                "yielding a net revenue increase."
            )
        elif abs_e < 1.0:
            interp = "inelastic"
            guidance = (
                "Demand is moderately inelastic. Price increases in the "
                "3-5% range should yield net revenue gains, as volume decline "
                "will be less than proportional to the price increase."
            )
        elif abs_e < 1.5:
            interp = "slightly_elastic"
            guidance = (
                "Demand is near unit-elastic. Small price increases (1-3%) "
                "may be feasible, but test carefully. Consider value-add "
                "strategies (bundling, premiumization) rather than straight increases."
            )
        else:
            interp = "elastic"
            guidance = (
                "Demand is price-sensitive. Avoid price increases without "
                "added perceived value. Instead, focus on cost optimization, "
                "upselling complementary items, or selective premiumization."
            )

        return {
            "elasticity": elasticity,
            "abs_elasticity": abs_e,
            "interpretation": interp,
            "guidance": guidance,
            "citations": ["jmr_elasticity", "hbr_pricing_power"],
        }

    @staticmethod
    def estimate_price_elasticity_panel(
        observations: list[dict],
        confounders: list[str] | None = None,
        dml_n_splits: int = 5,
    ) -> dict:
        """
        Panel-data price elasticity with two estimators side-by-side:

          * ``ols_elasticity`` — log-log OLS, ``log(Q) ~ log(P)`` (with
            confounders if provided). Interpretable baseline; biased when
            price is endogenous.
          * ``dml_elasticity`` — EconML LinearDML with cross-fitted
            gradient-boosted nuisance models. Recovers the causal price
            coefficient by partialling out the confounders. This is the
            estimator the masterplan tells us to act on for pricing
            decisions.

        Inputs
        ------
        observations : list of dicts
            Each row must carry ``price`` and ``quantity`` keys
            (positive numbers). Optional confounder columns named in
            ``confounders`` are read directly off the dicts.
        confounders : list[str], optional
            Names of additional columns to treat as demand shifters in
            both OLS and DML. Typical: ``["dow", "promo", "competitor_price",
            "weather", "holiday"]``.
        dml_n_splits : int
            K for the DML cross-fitting. The masterplan asked for 5.

        Returns
        -------
        dict with keys:
          * ``ols_elasticity``, ``ols_ci_95``, ``ols_r_squared``
          * ``dml_elasticity``, ``dml_ci_95``, ``dml_fold_estimates``
          * ``dml_fold_stability`` — std/mean(fold estimates), unitless
          * ``n_observations``, ``backend_status`` (per-estimator
            ``ok|unavailable|insufficient_data|error``)

        Sanity / acceptance criteria (see tests/ml_eval/test_elasticity.py):
          * Both estimators produce a negative elasticity on normal-goods
            synthetic data.
          * DML's per-fold estimates are fold-stable (std/mean < 0.5).
          * Where a confounder biases price upward with demand, DML's
            estimate is closer to the true elasticity than OLS.
        """
        result: dict = {
            "n_observations": len(observations),
            "backend_status": {"ols": "unavailable", "dml": "unavailable"},
            "ols_elasticity": None,
            "dml_elasticity": None,
        }
        if not observations:
            result["backend_status"] = {
                "ols": "insufficient_data", "dml": "insufficient_data",
            }
            return result

        confounder_cols = list(confounders or [])

        # Extract aligned arrays once and reuse.
        prices = [float(o.get("price", 0) or 0) for o in observations]
        quantities = [float(o.get("quantity", 0) or 0) for o in observations]
        confounder_data = {
            col: [float(o.get(col, 0) or 0) for o in observations]
            for col in confounder_cols
        }

        valid_idx = [
            i for i, (p, q) in enumerate(zip(prices, quantities))
            if p > 0 and q > 0
        ]
        if len(valid_idx) < max(20, 4 * (1 + len(confounder_cols))):
            result["backend_status"] = {
                "ols": "insufficient_data", "dml": "insufficient_data",
            }
            return result

        log_p = [math.log(prices[i]) for i in valid_idx]
        log_q = [math.log(quantities[i]) for i in valid_idx]
        W_cols = [
            [confounder_data[col][i] for i in valid_idx]
            for col in confounder_cols
        ]

        # ─── OLS log(Q) ~ log(P) + W ────────────────────────────────────
        if HAS_STATSMODELS:
            try:
                import numpy as np

                X = np.column_stack(
                    [log_p] + W_cols
                ) if W_cols else np.array(log_p).reshape(-1, 1)
                X = _sm.add_constant(X)
                y = np.array(log_q)
                ols = _sm.OLS(y, X).fit()
                ols_beta = float(ols.params[1])  # coefficient on log(P)
                ols_ci_lo, ols_ci_hi = (float(x) for x in ols.conf_int()[1])
                result.update({
                    "ols_elasticity": round(ols_beta, 4),
                    "ols_ci_95": [round(ols_ci_lo, 4), round(ols_ci_hi, 4)],
                    "ols_r_squared": round(float(ols.rsquared), 4),
                })
                result["backend_status"]["ols"] = "ok"
            except Exception as exc:  # noqa: BLE001
                logger.warning("OLS elasticity failed: %s", exc)
                result["backend_status"]["ols"] = f"error:{exc!r}"[:200]

        # ─── DoubleML / LinearDML ───────────────────────────────────────
        if HAS_ECONML and W_cols:
            try:
                import numpy as np
                from sklearn.ensemble import (  # type: ignore[import-not-found]
                    GradientBoostingRegressor,
                )

                Y = np.array(log_q)
                T = np.array(log_p)
                W = np.column_stack(W_cols)
                est = LinearDML(
                    model_y=GradientBoostingRegressor(),
                    model_t=GradientBoostingRegressor(),
                    cv=dml_n_splits,
                    random_state=0,
                )
                est.fit(Y, T, W=W)
                ate = float(est.const_marginal_ate(X=None) if hasattr(est, "const_marginal_ate") else est.ate(X=None))
                # const_marginal_ate / ate return the average causal
                # coefficient on T (== elasticity since both are logs).
                ci_lo, ci_hi = (
                    float(x) for x in est.const_marginal_ate_interval(X=None, alpha=0.05)
                ) if hasattr(est, "const_marginal_ate_interval") else (
                    float("nan"), float("nan")
                )

                # Fold-stability: refit on K folds, collect ATE per fold.
                from sklearn.model_selection import (  # type: ignore[import-not-found]
                    KFold,
                )
                fold_atts: list[float] = []
                kf = KFold(n_splits=min(dml_n_splits, 5), shuffle=True, random_state=0)
                for tr_idx, _ in kf.split(Y):
                    fold_est = LinearDML(
                        model_y=GradientBoostingRegressor(),
                        model_t=GradientBoostingRegressor(),
                        cv=2,
                        random_state=0,
                    )
                    fold_est.fit(Y[tr_idx], T[tr_idx], W=W[tr_idx])
                    fold_ate = float(
                        fold_est.const_marginal_ate(X=None)
                        if hasattr(fold_est, "const_marginal_ate")
                        else fold_est.ate(X=None)
                    )
                    fold_atts.append(fold_ate)
                mean = sum(fold_atts) / len(fold_atts)
                var = sum((a - mean) ** 2 for a in fold_atts) / max(len(fold_atts) - 1, 1)
                std = var ** 0.5
                stability = (std / abs(mean)) if mean else float("inf")

                result.update({
                    "dml_elasticity": round(ate, 4),
                    "dml_ci_95": [round(ci_lo, 4), round(ci_hi, 4)],
                    "dml_fold_estimates": [round(a, 4) for a in fold_atts],
                    "dml_fold_stability": round(stability, 4),
                })
                result["backend_status"]["dml"] = "ok"
            except Exception as exc:  # noqa: BLE001
                logger.warning("DML elasticity failed: %s", exc)
                result["backend_status"]["dml"] = f"error:{exc!r}"[:200]
        elif HAS_ECONML and not W_cols:
            # DML without confounders collapses to OLS — call it out so
            # the caller knows to provide demand shifters.
            result["backend_status"]["dml"] = "no_confounders_provided"

        return result

    @staticmethod
    def break_even_analysis(
        fixed_costs_cents: int,
        avg_revenue_per_unit_cents: int,
        variable_cost_per_unit_cents: int,
    ) -> dict:
        """
        Break-even analysis.
        
        Break-Even Units = Fixed Costs / (Revenue per Unit - Variable Cost per Unit)
        Break-Even Revenue = Break-Even Units × Revenue per Unit
        
        Contribution Margin = (Revenue - Variable Cost) / Revenue
        """
        contribution_margin_cents = avg_revenue_per_unit_cents - variable_cost_per_unit_cents
        
        if contribution_margin_cents <= 0:
            return {
                "status": "negative_contribution",
                "interpretation": (
                    "Each unit sold operates at a loss. Variable costs exceed "
                    "revenue per unit. Immediately review pricing and/or "
                    "renegotiate supplier costs."
                ),
            }

        break_even_units = math.ceil(fixed_costs_cents / contribution_margin_cents)
        break_even_revenue = break_even_units * avg_revenue_per_unit_cents
        contribution_margin_pct = round(
            contribution_margin_cents / avg_revenue_per_unit_cents * 100, 1
        )

        return {
            "break_even_units": break_even_units,
            "break_even_revenue_cents": break_even_revenue,
            "contribution_margin_cents": contribution_margin_cents,
            "contribution_margin_pct": contribution_margin_pct,
            "interpretation": (
                f"You need {break_even_units:,} transactions "
                f"(${break_even_revenue/100:,.0f} revenue) to cover fixed costs. "
                f"Your contribution margin is {contribution_margin_pct}% — "
                f"every dollar above break-even contributes "
                f"${contribution_margin_pct/100:.2f} to profit."
            ),
            "citations": ["sba_cash_flow"],
        }

    @staticmethod
    def revenue_concentration_hhi(
        product_revenue_shares: list[float],
    ) -> dict:
        """
        Herfindahl-Hirschman Index for revenue concentration risk.
        
        HHI = Σ(si²) where si is market share of product i (as %)
        
        HHI < 1500 → Low concentration (diversified)
        1500 ≤ HHI < 2500 → Moderate concentration
        HHI ≥ 2500 → High concentration (risky)
        
        Adapted from DOJ/FTC merger guidelines for product portfolio analysis.
        """
        if not product_revenue_shares:
            return {"hhi": 0, "risk_level": "no_data"}

        # Normalize to percentages
        total = sum(product_revenue_shares)
        if total == 0:
            return {"hhi": 0, "risk_level": "no_data"}

        shares_pct = [(s / total * 100) for s in product_revenue_shares]
        hhi = round(sum(s ** 2 for s in shares_pct), 0)

        # Products needed for 80% of revenue
        sorted_shares = sorted(shares_pct, reverse=True)
        cumulative = 0
        products_for_80 = 0
        for s in sorted_shares:
            cumulative += s
            products_for_80 += 1
            if cumulative >= 80:
                break

        if hhi < 1500:
            risk_level = "low"
            interpretation = (
                f"Revenue is well-diversified (HHI: {hhi:.0f}). "
                f"No single product dominates excessively. "
                f"This is a healthy portfolio structure."
            )
        elif hhi < 2500:
            risk_level = "moderate"
            interpretation = (
                f"Moderate revenue concentration (HHI: {hhi:.0f}). "
                f"Only {products_for_80} products drive 80% of revenue. "
                f"Consider developing 2-3 new revenue streams to reduce risk."
            )
        else:
            risk_level = "high"
            top_share = sorted_shares[0] if sorted_shares else 0
            interpretation = (
                f"High revenue concentration risk (HHI: {hhi:.0f}). "
                f"Your top product represents {top_share:.0f}% of revenue. "
                f"If that product underperforms, your entire business is at risk. "
                f"Urgently diversify your product mix."
            )

        return {
            "hhi": int(hhi),
            "risk_level": risk_level,
            "products_for_80_pct": products_for_80,
            "top_product_share_pct": round(sorted_shares[0], 1) if sorted_shares else 0,
            "interpretation": interpretation,
        }

    @staticmethod
    def marginal_revenue_analysis(
        hourly_revenue: list[dict],
        labor_cost_per_hour_cents: int = 2500,
    ) -> dict:
        """
        Marginal revenue per staffing hour.
        
        Identifies hours where marginal revenue exceeds marginal cost
        (worth adding staff) vs. hours where it doesn't.
        
        MR > MC → Add staff (profitable)
        MR < MC → Reduce staff or close (unprofitable)
        
        Citation: MIT Sloan Management Review (2024)
        """
        if not hourly_revenue:
            return {"status": "insufficient_data"}

        profitable_hours = []
        unprofitable_hours = []
        sum(h.get("revenue_cents", 0) for h in hourly_revenue)

        for hour_data in hourly_revenue:
            rev = hour_data.get("revenue_cents", 0)
            hour = hour_data.get("hour", "")
            
            # Estimate if adding one more staff member would be profitable
            # Rule of thumb: each staff member should generate 3x their cost
            min_revenue_per_staff = labor_cost_per_hour_cents * 3
            
            if rev >= min_revenue_per_staff:
                profitable_hours.append({
                    "hour": hour,
                    "revenue_cents": rev,
                    "revenue_to_cost_ratio": round(rev / max(labor_cost_per_hour_cents, 1), 1),
                })
            else:
                unprofitable_hours.append({
                    "hour": hour,
                    "revenue_cents": rev,
                    "revenue_to_cost_ratio": round(rev / max(labor_cost_per_hour_cents, 1), 1),
                })

        return {
            "profitable_hours": len(profitable_hours),
            "unprofitable_hours": len(unprofitable_hours),
            "best_hours": sorted(
                profitable_hours, 
                key=lambda x: x["revenue_cents"], 
                reverse=True
            )[:3],
            "worst_hours": sorted(
                unprofitable_hours, 
                key=lambda x: x["revenue_cents"]
            )[:3],
            "interpretation": (
                f"{len(profitable_hours)} of {len(hourly_revenue)} operating hours "
                f"generate revenue above the 3:1 labor cost threshold. "
                f"Focus staffing and inventory on these high-return windows."
            ),
            "citations": ["mit_sloan_scheduling", "cornell_labor_scheduling"],
        }

    @staticmethod
    def seasonal_index(
        daily_revenue: list[dict],
    ) -> dict:
        """
        Compute day-of-week seasonal indices.
        
        Index = (Average revenue for day) / (Overall average revenue)
        Index > 1.0 → Above-average day
        Index < 1.0 → Below-average day
        
        Used for demand forecasting and staff scheduling.
        """
        from collections import defaultdict
        
        dow_totals: dict[int, list[int]] = defaultdict(list)
        
        for day in daily_revenue:
            date_str = str(day.get("date", day.get("day_bucket", "")))
            rev = day.get("total_revenue_cents", day.get("revenue_cents", 0)) or 0
            
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                dow = dt.weekday()  # 0=Mon, 6=Sun
            except (ValueError, TypeError):
                continue
            
            dow_totals[dow].append(rev)

        if not dow_totals:
            return {"status": "insufficient_data"}

        # Compute averages per day of week
        dow_avgs = {}
        dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for dow, revenues in dow_totals.items():
            dow_avgs[dow] = sum(revenues) / len(revenues) if revenues else 0

        overall_avg = sum(dow_avgs.values()) / len(dow_avgs) if dow_avgs else 1

        indices = {}
        for dow, avg in sorted(dow_avgs.items()):
            name = dow_names[dow] if dow < 7 else f"Day {dow}"
            indices[name] = round(avg / max(overall_avg, 1), 2)

        best_day = max(indices.items(), key=lambda x: x[1])
        worst_day = min(indices.items(), key=lambda x: x[1])
        volatility = round((best_day[1] - worst_day[1]) / max(best_day[1], 1) * 100, 1)

        return {
            "indices": indices,
            "best_day": {"name": best_day[0], "index": best_day[1]},
            "worst_day": {"name": worst_day[0], "index": worst_day[1]},
            "volatility_pct": volatility,
            "interpretation": (
                f"{best_day[0]} is your strongest day (index: {best_day[1]}x average), "
                f"while {worst_day[0]} is weakest ({worst_day[1]}x). "
                f"The {volatility}% weekly volatility suggests "
                f"{'significant room for weekday promotions' if volatility > 30 else 'a relatively balanced week'}."
            ),
            "citations": ["nra_daypart_analysis", "nra_seasonal_trends"],
        }

    @staticmethod
    def discount_roi_analysis(
        total_revenue_cents: int,
        total_discount_cents: int,
        total_transactions: int,
        benchmark_discount_rate: float = 3.0,
    ) -> dict:
        """
        Analyze the return on investment of discounting.
        
        Excessive discounting (>5%) signals pricing strategy issues.
        
        Citation: Harvard Business Review (2023) — How to Stop the Discounting Spiral
        """
        if total_revenue_cents == 0:
            return {"status": "no_revenue_data"}

        actual_rate = round(total_discount_cents / total_revenue_cents * 100, 2)
        excess_rate = max(0, actual_rate - benchmark_discount_rate)
        excess_cents = int(total_revenue_cents * excess_rate / 100)
        int(excess_cents * 30 / max(1, 1))  # normalize

        if actual_rate <= benchmark_discount_rate:
            status = "healthy"
            guidance = (
                f"Your discount rate ({actual_rate}%) is within the healthy "
                f"range (≤{benchmark_discount_rate}%). Discounts are being "
                f"used strategically. No action needed."
            )
        elif actual_rate <= benchmark_discount_rate * 2:
            status = "elevated"
            guidance = (
                f"Your discount rate ({actual_rate}%) exceeds the industry "
                f"benchmark of {benchmark_discount_rate}%. "
                f"This costs you an estimated ${excess_cents/100:,.0f} in unnecessary margin erosion. "
                f"Shift from blanket discounts to targeted, time-limited promotions — "
                f"research shows targeted promotions outperform blanket discounts 3:1."
            )
        else:
            status = "excessive"
            guidance = (
                f"Your discount rate ({actual_rate}%) is {actual_rate/benchmark_discount_rate:.1f}x "
                f"the industry benchmark. You're leaving ${excess_cents/100:,.0f} on the table. "
                f"This level of discounting erodes brand perception and trains customers "
                f"to expect deals. Implement a structured pricing strategy immediately."
            )

        return {
            "actual_rate_pct": actual_rate,
            "benchmark_rate_pct": benchmark_discount_rate,
            "excess_rate_pct": round(excess_rate, 2),
            "excess_cents": excess_cents,
            "status": status,
            "guidance": guidance,
            "citations": ["hbr_discount_strategy", "mckinsey_pricing"],
        }

    @staticmethod
    def tip_optimization_potential(
        current_tip_rate: float,
        total_revenue_cents: int,
        days: int,
        optimal_rate: float = 18.0,
    ) -> dict:
        """
        Calculate potential revenue from optimizing tip rates.
        
        Citation: Cornell Hospitality Quarterly — POS tip prompts study
        """
        if current_tip_rate >= optimal_rate:
            return {
                "status": "optimal",
                "guidance": (
                    f"Your tip rate ({current_tip_rate:.1f}%) meets or exceeds "
                    f"the target ({optimal_rate:.1f}%). Your tip prompt strategy "
                    f"is working well."
                ),
            }

        gap_pct = optimal_rate - current_tip_rate
        daily_revenue = total_revenue_cents / max(days, 1)
        monthly_potential = int(daily_revenue * 30 * gap_pct / 100)

        return {
            "status": "below_optimal",
            "current_rate_pct": current_tip_rate,
            "optimal_rate_pct": optimal_rate,
            "gap_pct": round(gap_pct, 1),
            "monthly_potential_cents": monthly_potential,
            "guidance": (
                f"Your tip rate ({current_tip_rate:.1f}%) is {gap_pct:.1f} points "
                f"below the optimal {optimal_rate:.1f}%. Research from Cornell shows "
                f"that POS tip prompts with suggested amounts (18%/20%/25%) increase "
                f"average tips by 38% vs. open-entry fields. "
                f"Implementing this alone could add ~${monthly_potential/100:,.0f}/month "
                f"to your staff's take-home pay, improving retention."
            ),
            "citations": ["cornell_tipping", "square_payments_report"],
        }
