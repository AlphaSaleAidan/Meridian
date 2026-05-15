"""
Canada Benchmark Overlay — Adjusts US-centric benchmarks for Canadian market.

Applies:
  - USD → CAD conversion (exchange rate 1.38, Bank of Canada noon rate Q1 2025)
  - Higher labor costs (Canadian minimum wages exceed most US state minimums)
  - Lower tip rates (15-18% vs US 18-22%, Statistics Canada / Restaurants Canada)
  - Provincial sales tax impact on consumer pricing
  - Seasonal revenue adjustments for Canadian climate patterns
  - COGS adjustment for USD-denominated supplier costs

Sources:
  - Bank of Canada daily exchange rate (2025 Q1 average: 1.38)
  - Statistics Canada Table 14-10-0064: Wages by province
  - Restaurants Canada (CRFA) 2024 Foodservice Facts
  - CFIB Business Barometer 2024
  - Leger Marketing tipping survey 2024
"""
import logging
from dataclasses import dataclass

from .provincial import (
    MINIMUM_WAGE_CENTS,
    PROVINCIAL_TAX,
    PROVINCE_PROFILES,
    SEASONAL_TRAFFIC_FACTORS,
    ProvincialAnalyzer,
)

logger = logging.getLogger("meridian.ai.canada.benchmarks")

# ─── Constants ──────────────────────────────────────────────

USD_TO_CAD: float = 1.38  # Bank of Canada Q1 2025 average
CAD_TO_USD: float = 1.0 / USD_TO_CAD

# Canadian tip rates by vertical (Leger Marketing 2024, Statistics Canada)
# US benchmarks in benchmarks.yaml use US tipping norms — override here.
CANADIAN_TIP_RATES: dict[str, float] = {
    "coffee_shop": 12.0,   # Quick counter — lower than US 15-18%
    "restaurant": 17.0,    # Full-service — lower than US 20%
    "quick_service": 10.0, # QSR — lower than US 15%
    "bar": 16.0,           # Bar — lower than US 20%
    "salon": 15.0,         # Salon — similar to US
    "other": 10.0,
}

# Canadian labor cost premium over US by vertical.
# Source: CFIB + Statistics Canada vs BLS comparison.
# Canadian minimum wages generally run 15-30% above US federal ($7.25)
# and 5-15% above most US state minimums.
LABOR_COST_PREMIUM_PCT: dict[str, float] = {
    "coffee_shop": 12.0,
    "restaurant": 10.0,
    "quick_service": 14.0,
    "bar": 8.0,
    "retail": 10.0,
    "salon": 6.0,
    "grocery": 12.0,
    "smoke_shop": 8.0,
    "cannabis": 10.0,
    "other": 10.0,
}

# COGS adjustment: percentage of COGS that is USD-denominated imports.
# Affects food service (US produce, equipment), retail (US brands).
# Source: Statistics Canada Table 12-10-0011 (Imports by commodity)
USD_COGS_SHARE_PCT: dict[str, float] = {
    "coffee_shop": 35.0,   # Beans, syrups, equipment
    "restaurant": 25.0,    # Produce, specialty items
    "quick_service": 30.0, # Paper goods, frozen items
    "bar": 20.0,           # Some imported spirits
    "retail": 45.0,        # Consumer goods
    "salon": 40.0,         # Products from US brands
    "grocery": 30.0,       # Fresh produce imports
    "smoke_shop": 25.0,    # Some tobacco/vape imports
    "auto_repair": 50.0,   # US auto parts
    "fitness": 35.0,       # Equipment
    "other": 30.0,
}


# ─── Benchmark Adjustment Dataclass ────────────────────────

@dataclass
class BenchmarkAdjustment:
    """A single adjustment to a US benchmark metric."""
    metric: str
    us_value: float
    ca_value: float
    delta_pct: float
    reason: str
    source: str


# ─── CanadaBenchmarkOverlay Class ───────────────────────────

class CanadaBenchmarkOverlay:
    """
    Adjusts US-centric industry benchmarks for Canadian merchants.

    Takes the output of IndustryBenchmarks (from benchmarks.yaml)
    and applies Canadian-specific corrections.
    """

    def __init__(self, province: str = "ON", vertical: str = "other"):
        self.province = province.upper()
        self.vertical = vertical
        self.provincial = ProvincialAnalyzer(self.province)
        self.tax = PROVINCIAL_TAX.get(self.province, PROVINCIAL_TAX["ON"])
        self.profile = PROVINCE_PROFILES.get(self.province, PROVINCE_PROFILES["ON"])

    def adjust_benchmarks(self, us_benchmarks: dict) -> dict:
        """
        Apply all Canadian adjustments to a US benchmark dict.

        Expects a dict with keys like avg_ticket_cents, labor_cost_pct, etc.
        Returns a new dict with Canadian-adjusted values and audit trail.
        """
        adjusted = dict(us_benchmarks)
        adjustments: list[dict] = []

        # 1. Convert monetary values from USD to CAD
        for key in ("avg_ticket_cents", "avg_daily_revenue_cents",
                     "median_daily_revenue_cents"):
            if key in adjusted:
                us_val = adjusted[key]
                ca_val = round(us_val * USD_TO_CAD)
                adjustments.append({
                    "metric": key,
                    "us_value": us_val,
                    "ca_value": ca_val,
                    "delta_pct": round((ca_val - us_val) / us_val * 100, 1),
                    "reason": "USD to CAD conversion",
                    "source": f"Bank of Canada rate {USD_TO_CAD}",
                })
                adjusted[key] = ca_val

        # 2. Adjust labor cost percentage
        labor_premium = LABOR_COST_PREMIUM_PCT.get(self.vertical, 10.0)
        if "labor_cost_pct" in adjusted:
            us_labor = adjusted["labor_cost_pct"]
            ca_labor = round(us_labor * (1 + labor_premium / 100), 1)
            adjustments.append({
                "metric": "labor_cost_pct",
                "us_value": us_labor,
                "ca_value": ca_labor,
                "delta_pct": labor_premium,
                "reason": f"Canadian labor premium ({self.province} min wage "
                          f"${MINIMUM_WAGE_CENTS.get(self.province, 1500)/100:.2f}/hr)",
                "source": "Statistics Canada vs BLS wage comparison",
            })
            adjusted["labor_cost_pct"] = ca_labor

        # 3. Adjust tip rate
        ca_tip = CANADIAN_TIP_RATES.get(self.vertical, 10.0)
        if "optimal_tip_rate_pct" in adjusted:
            us_tip = adjusted["optimal_tip_rate_pct"]
            if us_tip > 0:
                adjustments.append({
                    "metric": "optimal_tip_rate_pct",
                    "us_value": us_tip,
                    "ca_value": ca_tip,
                    "delta_pct": round((ca_tip - us_tip) / us_tip * 100, 1)
                    if us_tip > 0 else 0,
                    "reason": "Canadian tipping norms (15-18% vs US 18-22%)",
                    "source": "Leger Marketing tipping survey 2024",
                })
                adjusted["optimal_tip_rate_pct"] = ca_tip

        # 4. Adjust COGS for currency impact
        usd_cogs_share = USD_COGS_SHARE_PCT.get(self.vertical, 30.0)
        if "cogs_pct" in adjusted:
            us_cogs = adjusted["cogs_pct"]
            # USD portion of COGS is more expensive in CAD
            currency_impact = us_cogs * (usd_cogs_share / 100) * (USD_TO_CAD - 1)
            ca_cogs = round(us_cogs + currency_impact, 1)
            adjustments.append({
                "metric": "cogs_pct",
                "us_value": us_cogs,
                "ca_value": ca_cogs,
                "delta_pct": round((ca_cogs - us_cogs) / us_cogs * 100, 1),
                "reason": f"{usd_cogs_share:.0f}% of COGS is USD-sourced, "
                          f"costing more in CAD",
                "source": "Statistics Canada imports + Bank of Canada FX",
            })
            adjusted["cogs_pct"] = ca_cogs

        # 5. Net margin adjustment (higher labor + COGS squeeze margins)
        # Canadian businesses partially offset costs through higher nominal
        # prices (CAD), so only ~40% of the cost increase flows to margin.
        # Source: CFIB Business Barometer 2024 — CA net margins average
        # 1.5-2pp below US equivalents, not the full cost delta.
        if "net_margin_pct" in adjusted:
            labor_drag = (adjusted.get("labor_cost_pct", 0)
                          - us_benchmarks.get("labor_cost_pct", 0))
            cogs_drag = (adjusted.get("cogs_pct", 0)
                         - us_benchmarks.get("cogs_pct", 0))
            passthrough_rate = 0.40  # 60% offset by higher CAD prices
            us_net = us_benchmarks["net_margin_pct"]
            net_drag = (labor_drag + cogs_drag) * passthrough_rate
            ca_net = round(max(1.0, us_net - net_drag), 1)
            adjustments.append({
                "metric": "net_margin_pct",
                "us_value": us_net,
                "ca_value": ca_net,
                "delta_pct": round((ca_net - us_net) / us_net * 100, 1)
                if us_net > 0 else 0,
                "reason": "Compressed by higher Canadian labor and COGS costs",
                "source": "CFIB Business Barometer 2024",
            })
            adjusted["net_margin_pct"] = ca_net

        adjusted["_canada_overlay"] = True
        adjusted["_adjustments"] = adjustments
        adjusted["_province"] = self.province
        adjusted["_exchange_rate"] = USD_TO_CAD
        adjusted["_tax_rate_pct"] = self.tax.total_sales_tax_pct

        return adjusted

    def get_seasonal_revenue_factors(self) -> dict[int, dict]:
        """
        Return month-by-month revenue adjustment factors.

        Combines climate-based foot traffic with patio season bonuses
        and holiday calendar effects.
        """
        from .holidays import get_annual_holiday_impact
        from datetime import date

        climate = self.profile.climate_zone
        traffic = SEASONAL_TRAFFIC_FACTORS.get(climate, {})
        holiday_impact = get_annual_holiday_impact(date.today().year, self.province)

        monthly: dict[int, dict] = {}
        for month in range(1, 13):
            base_traffic = traffic.get(month, 1.0)
            is_patio = month in self.profile.patio_season_months
            holiday_info = holiday_impact.get(month, {})

            # Patio bonus for food/drink verticals
            patio_bonus = 0.0
            if is_patio and self.vertical in (
                "restaurant", "bar", "coffee_shop", "quick_service"
            ):
                patio_bonus = 0.08  # 8% revenue boost from patio seating

            composite = round(base_traffic + patio_bonus, 3)

            monthly[month] = {
                "base_traffic_factor": base_traffic,
                "patio_bonus": patio_bonus,
                "is_patio_season": is_patio,
                "composite_factor": composite,
                "holiday_count": holiday_info.get("holiday_count", 0),
                "has_major_holiday": holiday_info.get("has_major_boost", False),
            }

        return monthly

    def get_currency_impact_summary(self) -> dict:
        """
        Summarize the USD/CAD impact on this merchant's cost structure.

        Useful for the dashboard "Currency Impact" widget.
        """
        usd_share = USD_COGS_SHARE_PCT.get(self.vertical, 30.0)
        fx_premium = (USD_TO_CAD - 1) * 100  # 38%

        # For every $100 CAD in COGS, how much more does the USD portion cost?
        cost_per_100_cad = round(usd_share * fx_premium / 100, 2)

        return {
            "exchange_rate": USD_TO_CAD,
            "usd_cogs_share_pct": usd_share,
            "fx_premium_pct": round(fx_premium, 1),
            "extra_cost_per_100_cad_cogs": cost_per_100_cad,
            "recommendation": self._currency_recommendation(usd_share),
        }

    def _currency_recommendation(self, usd_share: float) -> str:
        if usd_share >= 40:
            return (
                "High USD exposure. Consider Canadian-sourced alternatives "
                "or negotiate CAD-denominated contracts with US suppliers."
            )
        if usd_share >= 25:
            return (
                "Moderate USD exposure. Monitor CAD/USD rate for pricing "
                "adjustments — a 5% currency swing impacts your margins."
            )
        return "Low USD exposure. Currency fluctuations have minimal impact."

    def adjust_ranges(self, ranges: dict) -> dict:
        """
        Adjust benchmark ranges (low/mid/high) for Canadian context.

        Input: dict of {metric: {low, mid, high, source}}
        Returns the same structure with CAD-adjusted values.
        """
        adjusted = {}
        monetary_metrics = {
            "avg_ticket_cents", "avg_daily_revenue_cents",
        }

        for metric, rng in ranges.items():
            if not isinstance(rng, dict):
                adjusted[metric] = rng
                continue

            new_rng = dict(rng)

            if metric in monetary_metrics:
                for k in ("low", "mid", "high"):
                    if k in new_rng and isinstance(new_rng[k], (int, float)):
                        new_rng[k] = round(new_rng[k] * USD_TO_CAD)
                new_rng["source"] = rng.get("source", "") + " (CAD-adjusted)"

            if metric == "labor_cost_pct":
                premium = LABOR_COST_PREMIUM_PCT.get(self.vertical, 10.0)
                for k in ("low", "mid", "high"):
                    if k in new_rng and isinstance(new_rng[k], (int, float)):
                        new_rng[k] = round(new_rng[k] * (1 + premium / 100), 1)
                new_rng["source"] = (
                    rng.get("source", "")
                    + f" + Canadian labor premium ({self.province})"
                )

            adjusted[metric] = new_rng

        return adjusted
