"""
Canada Intelligence Engine — Market-aware overlay for Canadian merchants.

Detects Canadian merchants and applies province-specific adjustments
to the Meridian analysis pipeline: benchmarks, money-left scoring,
seasonal patterns, competitive landscape, and insight generation.

The overlay is non-destructive: it augments the existing US-centric
analysis with a `canada_overlay` key.

Sources:
  - Statistics Canada (CANSIM), Restaurants Canada (CRFA),
    CFIB Business Barometer, Leger Marketing, provincial legislation.
"""
import logging
from datetime import date

from .benchmarks import (
    CanadaBenchmarkOverlay, LABOR_COST_PREMIUM_PCT, USD_TO_CAD,
)
from .competitive import COMPETITIVE_LANDSCAPE
from .holidays import get_upcoming_holidays
from .insights import generate_provincial_insights, generate_overlay_insights
from .provincial import PROVINCE_PROFILES, ProvincialAnalyzer

logger = logging.getLogger("meridian.ai.canada.intelligence")

# ─── Timezone -> Province Mapping ───────────────────────────

TIMEZONE_TO_PROVINCE: dict[str, str] = {
    "America/Toronto": "ON", "America/Montreal": "QC",
    "America/Vancouver": "BC", "America/Edmonton": "AB",
    "America/Calgary": "AB", "America/Winnipeg": "MB",
    "America/Regina": "SK", "America/Halifax": "NS",
    "America/Moncton": "NB", "America/St_Johns": "NL",
    "America/Whitehorse": "YT", "America/Yellowknife": "NT",
    "America/Iqaluit": "NU", "America/Charlottetown": "PE",
    "Canada/Eastern": "ON", "Canada/Central": "MB",
    "Canada/Mountain": "AB", "Canada/Pacific": "BC",
    "Canada/Atlantic": "NS", "Canada/Newfoundland": "NL",
}
CANADIAN_TIMEZONES: set[str] = set(TIMEZONE_TO_PROVINCE.keys())


class CanadaIntelligence:
    """
    Main Canada intelligence engine.

    Enriches analysis results with province-specific benchmarks,
    seasonal patterns, competitive landscape, and holiday-aware insights.
    """

    def __init__(
        self, org_id: str, province: str | None = None,
        vertical: str = "other", timezone: str | None = None,
        currency: str | None = None,
    ):
        self.org_id = org_id
        self.vertical = vertical
        self.timezone = timezone
        self.currency = currency
        self.province = self._resolve_province(province, timezone)
        self.is_canadian = self.province is not None

        if self.is_canadian:
            self.provincial = ProvincialAnalyzer(self.province)
            self.benchmark_overlay = CanadaBenchmarkOverlay(
                province=self.province, vertical=self.vertical)
        else:
            self.provincial = None
            self.benchmark_overlay = None

    def _resolve_province(self, province, timezone) -> str | None:
        if province:
            p = province.upper()
            if p in PROVINCE_PROFILES:
                return p
            logger.warning(f"Unknown province code: {province}")
        if timezone and timezone in CANADIAN_TIMEZONES:
            return TIMEZONE_TO_PROVINCE[timezone]
        if self.currency and self.currency.upper() == "CAD":
            return "ON"
        return None

    # ─── Core Overlay ───────────────────────────────────────

    def apply_overlay(self, analysis_result: dict) -> dict:
        """Apply all Canada-specific adjustments to an analysis result."""
        if not self.is_canadian:
            return analysis_result

        logger.info(f"Applying Canada overlay org={self.org_id} "
                     f"province={self.province} vertical={self.vertical}")

        overlay: dict = {
            "province": self.province,
            "province_name": PROVINCE_PROFILES[self.province].name,
            "vertical": self.vertical, "is_canadian": True,
        }

        if "industry_benchmarks" in analysis_result:
            overlay["adjusted_benchmarks"] = (
                self.benchmark_overlay.adjust_benchmarks(
                    analysis_result["industry_benchmarks"]))

        overlay["seasonal_factors"] = (
            self.benchmark_overlay.get_seasonal_revenue_factors())
        overlay["provincial_insights"] = self.get_provincial_insights()
        overlay["competitive_landscape"] = self.get_competitive_landscape()
        overlay["currency_impact"] = (
            self.benchmark_overlay.get_currency_impact_summary())
        overlay["upcoming_holidays"] = get_upcoming_holidays(
            from_date=date.today(), days_ahead=60, province=self.province)
        overlay["tax_context"] = self.provincial.get_tax_summary()
        overlay["regulatory"] = self.provincial.get_regulatory_context(
            self.vertical)

        if "money_left_score" in analysis_result:
            overlay["adjusted_money_left"] = self.adjust_money_left(
                analysis_result["money_left_score"])

        overlay["canada_insights"] = generate_overlay_insights(
            overlay, self.provincial.get_seasonal_factor)

        analysis_result["canada_overlay"] = overlay
        return analysis_result

    # ─── Seasonal Adjustments ───────────────────────────────

    def get_seasonal_adjustments(self, month: int) -> dict:
        """Get seasonal factors, patio status, holidays, and recommendations."""
        if not self.is_canadian:
            return {"is_canadian": False}

        factor = self.provincial.get_seasonal_factor(month)
        is_patio = self.provincial.is_patio_season(month)
        holidays = get_upcoming_holidays(
            from_date=date(date.today().year, month, 1),
            days_ahead=31, province=self.province)

        recs: list[str] = []
        if factor < 0.80:
            recs.append("Winter slowdown expected. Focus on delivery/takeout, "
                        "loyalty programs, and indoor comfort marketing.")
        if factor < 0.70:
            recs.append("Deep winter — consider reduced hours on slowest days.")
        if is_patio:
            recs.append("Patio season active — maximize outdoor seating. "
                        "Patio customers spend 15-20% more (CRFA 2024).")
        if month == 9:
            recs.append("Back-to-school: weekday lunch traffic increases.")
        if month == 12:
            recs.append("Boxing Day (Dec 26) is Canada's biggest retail day.")

        return {"month": month, "province": self.province,
                "traffic_factor": factor, "is_patio_season": is_patio,
                "holidays_this_month": holidays, "recommendations": recs}

    # ─── Provincial Insights ────────────────────────────────

    def get_provincial_insights(self) -> list[dict]:
        if not self.is_canadian:
            return []
        return generate_provincial_insights(self.province, self.vertical)

    # ─── Competitive Landscape ──────────────────────────────

    def get_competitive_landscape(self) -> dict:
        if not self.is_canadian:
            return {}

        vertical_data = COMPETITIVE_LANDSCAPE.get(self.vertical, {})
        national = vertical_data.get("national", [])
        provincial = vertical_data.get(self.province, [])
        total_locs = sum(c.get("locations", 0) for c in national)
        p = PROVINCE_PROFILES[self.province]

        return {
            "vertical": self.vertical, "province": self.province,
            "national_chains": national, "provincial_chains": provincial,
            "total_chain_locations": total_locs,
            "market_context": {
                "province_population": p.population,
                "restaurant_density_per_10k": p.restaurant_density_per_10k,
                "chain_density_per_10k": round(
                    total_locs / (p.population / 10_000), 1
                ) if p.population and total_locs else 0,
            },
            "positioning_advice": self._positioning_advice(national),
        }

    # ─── Money Left Adjustments ─────────────────────────────

    def adjust_money_left(self, money_left_score: dict) -> dict:
        """Adjust money-left for Canadian labor costs, pricing, seasonality."""
        if not self.is_canadian:
            return money_left_score

        adjusted = dict(money_left_score)
        components = adjusted.get("components", {})
        applied: list[dict] = []

        # Peak hour waste: higher Canadian labor cost
        peak = components.get("peak_hour_waste", {})
        if peak.get("potential_monthly_cents", 0) > 0:
            prem = LABOR_COST_PREMIUM_PCT.get(self.vertical, 10.0)
            orig = peak["potential_monthly_cents"]
            peak["potential_monthly_cents"] = round(orig * (1 + prem / 100))
            peak["canada_note"] = f"Adjusted +{prem:.0f}% for higher labor costs"
            applied.append({"component": "peak_hour_waste",
                           "original_cents": orig,
                           "adjusted_cents": peak["potential_monthly_cents"],
                           "reason": f"Canadian labor premium {prem:.0f}%"})

        # Underpriced: CAD benchmark comparison
        under = components.get("underpriced", {})
        if under.get("potential_monthly_cents", 0) > 0:
            orig = under["potential_monthly_cents"]
            under["potential_monthly_cents"] = round(orig * USD_TO_CAD)
            under["canada_note"] = "CAD benchmark — prices should exceed US equivalents"
            applied.append({"component": "underpriced",
                           "original_cents": orig,
                           "adjusted_cents": under["potential_monthly_cents"],
                           "reason": "USD to CAD price adjustment"})

        # Scheduling: winter amplification
        sched = components.get("scheduling_gaps", {})
        if sched.get("potential_monthly_cents", 0) > 0:
            profile = PROVINCE_PROFILES[self.province]
            if profile.winter_severity in ("harsh", "extreme"):
                orig = sched["potential_monthly_cents"]
                sched["potential_monthly_cents"] = round(orig * 1.20)
                sched["canada_note"] = (
                    f"{profile.winter_severity.title()} winters make "
                    f"seasonal optimization 20% more impactful")
                applied.append({"component": "scheduling_gaps",
                               "original_cents": orig,
                               "adjusted_cents": sched["potential_monthly_cents"],
                               "reason": f"{profile.winter_severity} winter"})

        new_total = sum(c.get("potential_monthly_cents", 0)
                        for c in components.values() if isinstance(c, dict))
        adjusted["total_score_cents"] = new_total
        adjusted["total_score_dollars"] = f"${new_total / 100:,.0f}"
        adjusted["canada_adjustments"] = applied
        adjusted["currency"] = "CAD"
        return adjusted

    # ─── Private Helpers ────────────────────────────────────

    def _positioning_advice(self, chains: list[dict]) -> str:
        if not chains:
            return ("Limited chain competition — "
                    "focus on building local brand awareness.")
        top = chains[0]
        share = top.get("market_share_pct", 0)
        name = top.get("name", "leading chain")
        if share > 40:
            return (f"{name} dominates (~{share:.0f}% share). Compete on "
                    f"quality, local sourcing, and personal service — not price.")
        if share > 20:
            return (f"{name} leads (~{share:.0f}% share) but market is "
                    f"fragmented. Differentiate through specialty offerings.")
        return ("Fragmented market — opportunity to build local share "
                "through quality and community engagement.")


# ─── Detection Helper ──────────────────────────────────────

def is_canadian_merchant(
    timezone: str | None = None, currency: str | None = None,
    province: str | None = None,
) -> bool:
    """Quick check: is this merchant Canadian?"""
    if province and province.upper() in PROVINCE_PROFILES:
        return True
    if timezone and timezone in CANADIAN_TIMEZONES:
        return True
    if currency and currency.upper() == "CAD":
        return True
    return False
