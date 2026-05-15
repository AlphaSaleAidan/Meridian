"""
Canada Insight Generator — Produces province-specific and seasonal insights.

Called by CanadaIntelligence to generate the provincial_insights and
canada_insights sections of the overlay.
"""
import logging
from datetime import date

from .benchmarks import CANADIAN_TIP_RATES, LABOR_COST_PREMIUM_PCT
from .provincial import MINIMUM_WAGE_CENTS, PROVINCE_PROFILES, PROVINCIAL_TAX

logger = logging.getLogger("meridian.ai.canada.insights")


def generate_provincial_insights(
    province: str, vertical: str
) -> list[dict]:
    """Generate province-specific business insights."""
    insights: list[dict] = []
    p = PROVINCE_PROFILES[province]
    tax = PROVINCIAL_TAX[province]
    min_wage = MINIMUM_WAGE_CENTS[province]
    national_avg_wage = 1567

    # Labor cost
    wage_delta = min_wage - national_avg_wage
    if wage_delta > 100:
        insights.append({
            "type": "labor_cost_warning", "severity": "medium",
            "title": f"{p.name} minimum wage above national average",
            "detail": (
                f"At ${min_wage/100:.2f}/hr, {p.name}'s minimum wage is "
                f"${wage_delta/100:.2f}/hr above national average."),
            "recommendation": (
                "Optimize scheduling to minimize overstaffing. Consider "
                "technology (kiosks, mobile ordering) for labor productivity."),
            "source": "Provincial Employment Standards Act 2025"})
    elif wage_delta < -50:
        insights.append({
            "type": "labor_cost_advantage", "severity": "positive",
            "title": f"{p.name} labor costs below national average",
            "detail": (
                f"At ${min_wage/100:.2f}/hr, {p.name}'s minimum wage is "
                f"${abs(wage_delta)/100:.2f}/hr below national average."),
            "recommendation": (
                "Invest the labor savings into service quality — "
                "higher staffing levels improve customer experience."),
            "source": "Provincial Employment Standards Act 2025"})

    # Tax impact
    if tax.total_sales_tax_pct >= 15.0:
        insights.append({
            "type": "high_tax_environment", "severity": "medium",
            "title": f"High sales tax environment ({tax.total_sales_tax_pct}%)",
            "detail": (
                f"{p.name} charges {tax.total_sales_tax_pct}% total sales tax "
                f"({tax.model}). Reduces consumer purchasing power vs AB (5%)."),
            "recommendation": (
                "Emphasize value in pricing. Consider tax-inclusive menu "
                "pricing for food service to reduce sticker shock."),
            "source": "Canada Revenue Agency 2025"})
    elif tax.total_sales_tax_pct <= 5.0:
        insights.append({
            "type": "low_tax_advantage", "severity": "positive",
            "title": f"Low tax environment ({tax.total_sales_tax_pct}%)",
            "detail": (
                f"{p.name} has only {tax.total_sales_tax_pct}% sales tax — "
                f"the lowest in Canada. More consumer purchasing power."),
            "recommendation": (
                "Leverage low tax as a competitive advantage. "
                "Neighbouring province customers may cross-border shop."),
            "source": "Canada Revenue Agency 2025"})

    # Winter severity
    if p.winter_severity in ("harsh", "extreme"):
        patio_months = len(p.patio_season_months)
        month_names = _month_names(p.patio_season_months)
        insights.append({
            "type": "seasonal_risk",
            "severity": "high" if p.winter_severity == "extreme" else "medium",
            "title": f"{p.winter_severity.title()} winters limit outdoor revenue",
            "detail": (
                f"{p.name} has only {patio_months} months of patio season "
                f"({', '.join(month_names)}). Expect 15-25% foot traffic decline Dec-Mar."),
            "recommendation": (
                "Build a winter revenue strategy: delivery partnerships, "
                "loyalty programs, comfort-food promotions, holiday marketing."),
            "source": "Statistics Canada Table 20-10-0056, CRFA 2024"})

    # Tipping culture
    ca_tip = CANADIAN_TIP_RATES.get(vertical, 10.0)
    if vertical in ("restaurant", "bar", "coffee_shop", "salon"):
        insights.append({
            "type": "tipping_culture", "severity": "info",
            "title": "Canadian tipping norms differ from US",
            "detail": (
                f"Canadian tip rates for {vertical.replace('_', ' ')} average "
                f"{ca_tip}%, vs US norms of {ca_tip + 3}-{ca_tip + 5}%."),
            "recommendation": (
                "Use Canadian norms for tip-related benchmarks. Tip pooling "
                "and transparent policies improve staff retention."),
            "source": "Leger Marketing tipping survey 2024"})

    # Cannabis regulation
    if vertical == "cannabis":
        model_label = p.cannabis_model.replace("_", " ")
        insights.append({
            "type": "cannabis_regulation", "severity": "high",
            "title": f"Cannabis retail model: {model_label}",
            "detail": p.cannabis_notes,
            "recommendation": _cannabis_recommendation(p.cannabis_model),
            "source": "Provincial cannabis legislation 2025"})

    return insights


def generate_overlay_insights(
    overlay: dict, provincial_get_seasonal_factor
) -> list[dict]:
    """Generate actionable insights from holidays and seasonal transitions."""
    insights: list[dict] = []

    # Holiday preparation
    for h in overlay.get("upcoming_holidays", [])[:3]:
        if h.get("days_away", 999) > 14:
            continue
        mult = h.get("revenue_multiplier", 1.0)
        if mult > 1.2:
            insights.append({
                "type": "holiday_opportunity", "priority": "high",
                "title": f"{h['name']} in {h['days_away']} days — prepare now",
                "detail": (
                    f"Expected revenue multiplier: {mult:.0%}. "
                    f"{'Statutory holiday.' if h.get('statutory') else 'Not statutory.'}"),
                "actions": [
                    "Review staffing schedule for the holiday period",
                    "Launch targeted promotions 5-7 days before",
                    "Stock up on high-demand inventory"]})
        elif mult < 0.5:
            insights.append({
                "type": "holiday_closure", "priority": "medium",
                "title": f"{h['name']} in {h['days_away']} days — plan for closure",
                "detail": (
                    f"Most businesses close. "
                    f"{'Statutory — open businesses must pay premium wages.' if h.get('statutory') else ''}"),
                "actions": [
                    "Confirm holiday hours and communicate to customers",
                    "Shift revenue targets to surrounding days"]})

    # Seasonal transition
    today = date.today()
    cur = provincial_get_seasonal_factor(today.month)
    nxt = provincial_get_seasonal_factor(today.month % 12 + 1)
    if nxt - cur > 0.10:
        insights.append({
            "type": "seasonal_upswing", "priority": "medium",
            "title": "Seasonal upswing approaching",
            "detail": f"Traffic factor rising from {cur:.2f} to {nxt:.2f} next month.",
            "actions": ["Increase inventory orders", "Begin hiring seasonal staff",
                        "Launch spring/summer marketing"]})
    elif cur - nxt > 0.10:
        insights.append({
            "type": "seasonal_decline", "priority": "medium",
            "title": "Seasonal slowdown approaching",
            "detail": f"Traffic factor dropping from {cur:.2f} to {nxt:.2f} next month.",
            "actions": ["Review staffing for reduced traffic",
                        "Consider reduced hours on slow days",
                        "Activate loyalty/retention campaigns"]})

    return insights


def _cannabis_recommendation(model: str) -> str:
    if model == "government_only":
        return ("Government monopoly — no private retail. Focus on "
                "ancillary products or consider adjacent provinces.")
    if model == "private_retail":
        return ("Private retail — competitive. Differentiate through "
                "product knowledge, experience, and loyalty programs.")
    return ("Hybrid market — focus on convenience, extended hours, "
            "and product range that government stores may not offer.")


def _month_names(months: list[int]) -> list[str]:
    names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return [names[m] for m in months if 1 <= m <= 12]
