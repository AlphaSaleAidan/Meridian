"""
Canadian Holiday Calendar — Seasonal impact analysis for merchant intelligence.

Holiday impact types:
  closed            — Most businesses closed, no revenue expected
  mixed             — Some businesses open, foot traffic varies
  boost             — General uptick in spending
  boost_outdoor     — Outdoor/patio businesses surge
  major_boost       — Significant revenue increase for most verticals
  major_boost_restaurant — Restaurants/food service see outsized gains
  back_to_school    — Retail surge, restaurant shift to weekday patterns
  closed_retail_boost_prior — Closed day but run-up generates high volume
  massive_retail    — Highest single-day retail volume of the year

Sources: Statistics Canada Table 13-10-0114, CRFA Holiday Spending Reports 2024.
"""
import logging
from datetime import date, timedelta

logger = logging.getLogger("meridian.ai.canada.holidays")

# ─── Holiday Definitions ────────────────────────────────────

CANADIAN_HOLIDAYS: dict[str, dict] = {
    "new_years": {
        "name": "New Year's Day",
        "month": 1,
        "day": 1,
        "rule": "fixed",
        "impact": "closed",
        "revenue_multiplier": 0.05,
        "provinces": "all",
        "statutory": True,
    },
    "family_day": {
        "name": "Family Day",
        "month": 2,
        "day": "third_monday",
        "rule": "nth_weekday",
        "n": 3,
        "weekday": 0,  # Monday
        "impact": "mixed",
        "revenue_multiplier": 0.70,
        "provinces": ["ON", "AB", "BC", "SK", "NB"],
        "statutory": True,
    },
    "islander_day": {
        "name": "Islander Day",
        "month": 2,
        "day": "third_monday",
        "rule": "nth_weekday",
        "n": 3,
        "weekday": 0,
        "impact": "mixed",
        "revenue_multiplier": 0.70,
        "provinces": ["PE"],
        "statutory": True,
    },
    "louis_riel_day": {
        "name": "Louis Riel Day",
        "month": 2,
        "day": "third_monday",
        "rule": "nth_weekday",
        "n": 3,
        "weekday": 0,
        "impact": "mixed",
        "revenue_multiplier": 0.70,
        "provinces": ["MB"],
        "statutory": True,
    },
    "heritage_day_ns": {
        "name": "Heritage Day",
        "month": 2,
        "day": "third_monday",
        "rule": "nth_weekday",
        "n": 3,
        "weekday": 0,
        "impact": "mixed",
        "revenue_multiplier": 0.70,
        "provinces": ["NS"],
        "statutory": False,
    },
    "good_friday": {
        "name": "Good Friday",
        "month": "variable",
        "day": "variable",
        "rule": "easter_offset",
        "offset_days": -2,
        "impact": "closed",
        "revenue_multiplier": 0.10,
        "provinces": "all",
        "statutory": True,
    },
    "easter_monday": {
        "name": "Easter Monday",
        "month": "variable",
        "day": "variable",
        "rule": "easter_offset",
        "offset_days": 1,
        "impact": "mixed",
        "revenue_multiplier": 0.60,
        "provinces": "all",
        "statutory": False,
    },
    "victoria_day": {
        "name": "Victoria Day",
        "month": 5,
        "day": "last_monday_before_25",
        "rule": "victoria_day",
        "impact": "boost_outdoor",
        "revenue_multiplier": 1.15,
        "provinces": "all",
        "statutory": True,
        "notes": "Unofficial start of patio season, camping, outdoor retail",
    },
    "st_jean_baptiste": {
        "name": "Saint-Jean-Baptiste Day",
        "month": 6,
        "day": 24,
        "rule": "fixed",
        "impact": "major_boost",
        "revenue_multiplier": 1.30,
        "provinces": ["QC"],
        "statutory": True,
        "notes": "Quebec national holiday — bars and restaurants surge",
    },
    "canada_day": {
        "name": "Canada Day",
        "month": 7,
        "day": 1,
        "rule": "fixed",
        "impact": "major_boost",
        "revenue_multiplier": 1.35,
        "provinces": "all",
        "statutory": True,
        "notes": "Outdoor events, BBQ retail, restaurants peak",
    },
    "civic_holiday": {
        "name": "Civic Holiday",
        "month": 8,
        "day": "first_monday",
        "rule": "nth_weekday",
        "n": 1,
        "weekday": 0,
        "impact": "boost",
        "revenue_multiplier": 1.10,
        "provinces": ["ON", "AB", "BC", "SK", "MB", "NB", "NU", "NT"],
        "statutory": False,
        "notes": "Not statutory in most provinces but widely observed",
    },
    "labour_day": {
        "name": "Labour Day",
        "month": 9,
        "day": "first_monday",
        "rule": "nth_weekday",
        "n": 1,
        "weekday": 0,
        "impact": "back_to_school",
        "revenue_multiplier": 1.20,
        "provinces": "all",
        "statutory": True,
        "notes": "End of patio season, back-to-school retail surge",
    },
    "national_day_truth_reconciliation": {
        "name": "National Day for Truth and Reconciliation",
        "month": 9,
        "day": 30,
        "rule": "fixed",
        "impact": "mixed",
        "revenue_multiplier": 0.80,
        "provinces": ["BC", "MB", "PE", "NT", "NU", "YT"],
        "statutory": True,
        "notes": "Federal stat but only some provinces observe provincially",
    },
    "thanksgiving": {
        "name": "Thanksgiving",
        "month": 10,
        "day": "second_monday",
        "rule": "nth_weekday",
        "n": 2,
        "weekday": 0,
        "impact": "major_boost_restaurant",
        "revenue_multiplier": 1.40,
        "provinces": "all",
        "statutory": True,
        "notes": "Grocery +40%, restaurants surge, retail moderate",
    },
    "remembrance_day": {
        "name": "Remembrance Day",
        "month": 11,
        "day": 11,
        "rule": "fixed",
        "impact": "mixed",
        "revenue_multiplier": 0.75,
        "provinces": "all",
        "statutory": True,
        "notes": "Not statutory in ON, QC, NS, MB — business as usual there",
    },
    "christmas_eve": {
        "name": "Christmas Eve",
        "month": 12,
        "day": 24,
        "rule": "fixed",
        "impact": "closed_retail_boost_prior",
        "revenue_multiplier": 1.50,
        "provinces": "all",
        "statutory": False,
        "notes": "Last-minute shopping rush, early closures",
    },
    "christmas": {
        "name": "Christmas Day",
        "month": 12,
        "day": 25,
        "rule": "fixed",
        "impact": "closed",
        "revenue_multiplier": 0.02,
        "provinces": "all",
        "statutory": True,
    },
    "boxing_day": {
        "name": "Boxing Day",
        "month": 12,
        "day": 26,
        "rule": "fixed",
        "impact": "massive_retail",
        "revenue_multiplier": 2.20,
        "provinces": "all",
        "statutory": True,
        "notes": "Largest single-day retail revenue in Canada (Retail Council of Canada 2024)",
    },
}


# ─── Easter Calculation (Anonymous Gregorian) ───────────────

def _compute_easter(year: int) -> date:
    """Compute Easter Sunday using the Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l_val = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_val) // 451
    month = (h + l_val - 7 * m + 114) // 31
    day = ((h + l_val - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """Get the nth occurrence of a weekday in a month. weekday: 0=Mon..6=Sun."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    result = first + timedelta(days=offset + 7 * (n - 1))
    return result


def _victoria_day(year: int) -> date:
    """Last Monday on or before May 24."""
    may24 = date(year, 5, 24)
    offset = (may24.weekday() - 0) % 7  # Monday = 0
    return may24 - timedelta(days=offset)


# ─── Public API ─────────────────────────────────────────────

def resolve_holiday_date(holiday_key: str, year: int) -> date | None:
    """Resolve a holiday key to a concrete date for the given year."""
    h = CANADIAN_HOLIDAYS.get(holiday_key)
    if not h:
        return None

    rule = h.get("rule", "fixed")

    if rule == "fixed":
        return date(year, h["month"], h["day"])

    if rule == "nth_weekday":
        return _nth_weekday_of_month(year, h["month"], h["weekday"], h["n"])

    if rule == "easter_offset":
        easter = _compute_easter(year)
        return easter + timedelta(days=h["offset_days"])

    if rule == "victoria_day":
        return _victoria_day(year)

    logger.warning(f"Unknown holiday rule: {rule} for {holiday_key}")
    return None


def get_holidays_for_month(year: int, month: int, province: str = "ON") -> list[dict]:
    """
    Return all Canadian holidays in a given month applicable to a province.

    Returns list of dicts with: key, name, date, impact, revenue_multiplier.
    """
    results = []
    for key, h in CANADIAN_HOLIDAYS.items():
        # Check province applicability
        provinces = h.get("provinces", "all")
        if provinces != "all" and province not in provinces:
            continue

        resolved = resolve_holiday_date(key, year)
        if resolved and resolved.month == month:
            results.append({
                "key": key,
                "name": h["name"],
                "date": resolved.isoformat(),
                "impact": h["impact"],
                "revenue_multiplier": h["revenue_multiplier"],
                "statutory": h.get("statutory", False),
                "notes": h.get("notes", ""),
            })

    results.sort(key=lambda x: x["date"])
    return results


def get_upcoming_holidays(
    from_date: date, days_ahead: int = 30, province: str = "ON"
) -> list[dict]:
    """Get holidays in the next N days for a province."""
    end = from_date + timedelta(days=days_ahead)
    results = []

    for key, h in CANADIAN_HOLIDAYS.items():
        provinces = h.get("provinces", "all")
        if provinces != "all" and province not in provinces:
            continue

        for year in (from_date.year, from_date.year + 1):
            resolved = resolve_holiday_date(key, year)
            if resolved and from_date <= resolved <= end:
                results.append({
                    "key": key,
                    "name": h["name"],
                    "date": resolved.isoformat(),
                    "days_away": (resolved - from_date).days,
                    "impact": h["impact"],
                    "revenue_multiplier": h["revenue_multiplier"],
                    "statutory": h.get("statutory", False),
                    "notes": h.get("notes", ""),
                })

    results.sort(key=lambda x: x["days_away"])
    return results


def get_annual_holiday_impact(year: int, province: str = "ON") -> dict:
    """
    Summarize full-year holiday impact for forecasting.

    Returns month-by-month holiday counts and average revenue multipliers.
    """
    monthly: dict[int, list[float]] = {m: [] for m in range(1, 13)}

    for key, h in CANADIAN_HOLIDAYS.items():
        provinces = h.get("provinces", "all")
        if provinces != "all" and province not in provinces:
            continue

        resolved = resolve_holiday_date(key, year)
        if resolved:
            monthly[resolved.month].append(h["revenue_multiplier"])

    summary = {}
    for month, multipliers in monthly.items():
        if multipliers:
            avg_mult = sum(multipliers) / len(multipliers)
            summary[month] = {
                "holiday_count": len(multipliers),
                "avg_revenue_multiplier": round(avg_mult, 2),
                "has_closure": any(m < 0.2 for m in multipliers),
                "has_major_boost": any(m > 1.3 for m in multipliers),
            }
        else:
            summary[month] = {
                "holiday_count": 0,
                "avg_revenue_multiplier": 1.0,
                "has_closure": False,
                "has_major_boost": False,
            }

    return summary
