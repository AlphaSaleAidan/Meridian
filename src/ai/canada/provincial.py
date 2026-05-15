"""
Provincial Analyzer — Province-specific tax, labor, regulatory, and climate data.

All monetary values in cents. Tax rates as percentages.

Sources:
  - Canada Revenue Agency: GST/HST rates (2025)
  - Provincial Employment Standards Acts (2025 minimum wage schedules)
  - Statistics Canada Tables 14-10-0064, 17-10-0009, 20-10-0056
  - CRFA Restaurant Industry Snapshot 2024
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger("meridian.ai.canada.provincial")


# ─── Tax Structures ─────────────────────────────────────────

@dataclass(frozen=True)
class ProvincialTax:
    gst_pct: float
    pst_pct: float
    hst_pct: float
    qst_pct: float
    total_sales_tax_pct: float
    model: str  # "HST", "GST+PST", "GST+QST", "GST_only"

# (gst, pst, hst, qst, total, model)
_TAX_DATA = {
    "ON": (5.0, 0.0, 13.0, 0.0, 13.0, "HST"),
    "BC": (5.0, 7.0, 0.0, 0.0, 12.0, "GST+PST"),
    "AB": (5.0, 0.0, 0.0, 0.0, 5.0, "GST_only"),
    "QC": (5.0, 0.0, 0.0, 9.975, 14.975, "GST+QST"),
    "SK": (5.0, 6.0, 0.0, 0.0, 11.0, "GST+PST"),
    "MB": (5.0, 7.0, 0.0, 0.0, 12.0, "GST+PST"),
    "NS": (5.0, 0.0, 15.0, 0.0, 15.0, "HST"),
    "NB": (5.0, 0.0, 15.0, 0.0, 15.0, "HST"),
    "PE": (5.0, 0.0, 15.0, 0.0, 15.0, "HST"),
    "NL": (5.0, 0.0, 15.0, 0.0, 15.0, "HST"),
    "YT": (5.0, 0.0, 0.0, 0.0, 5.0, "GST_only"),
    "NT": (5.0, 0.0, 0.0, 0.0, 5.0, "GST_only"),
    "NU": (5.0, 0.0, 0.0, 0.0, 5.0, "GST_only"),
}
PROVINCIAL_TAX: dict[str, ProvincialTax] = {
    k: ProvincialTax(*v) for k, v in _TAX_DATA.items()
}

# ─── Minimum Wage (cents/hour, 2025) ────────────────────────

MINIMUM_WAGE_CENTS: dict[str, int] = {
    "BC": 1740, "ON": 1655, "AB": 1500, "QC": 1575, "SK": 1500,
    "MB": 1530, "NS": 1520, "NB": 1530, "PE": 1540, "NL": 1560,
    "YT": 1712, "NT": 1605, "NU": 1600,
}

# ─── Province Profiles (compact) ────────────────────────────

@dataclass
class ProvinceProfile:
    code: str
    name: str
    population: int
    major_cities: list[str]
    climate_zone: str
    winter_severity: str
    patio_season_months: list[int]
    timezone_hint: str
    alcohol_model: str
    cannabis_model: str
    cannabis_notes: str = ""
    alcohol_notes: str = ""
    avg_household_income_cents: int = 0
    restaurant_density_per_10k: float = 0.0

def _p(code, name, pop, cities, climate, winter, patio, tz,
       alc_model, alc_notes, can_model, can_notes, income, rest_dens):
    return ProvinceProfile(
        code=code, name=name, population=pop, major_cities=cities,
        climate_zone=climate, winter_severity=winter,
        patio_season_months=patio, timezone_hint=tz,
        alcohol_model=alc_model, alcohol_notes=alc_notes,
        cannabis_model=can_model, cannabis_notes=can_notes,
        avg_household_income_cents=income,
        restaurant_density_per_10k=rest_dens)

PROVINCE_PROFILES: dict[str, ProvinceProfile] = {p.code: p for p in [
    _p("ON", "Ontario", 15_801_768,
       ["Toronto", "Ottawa", "Mississauga", "Hamilton", "London"],
       "continental", "harsh", [5,6,7,8,9], "America/Toronto",
       "provincial_monopoly", "LCBO monopoly on spirits/wine; Beer Store + grocery for beer",
       "hybrid", "OCS online + private retail licensed by AGCO", 10_640_000, 7.8),
    _p("BC", "British Columbia", 5_581_127,
       ["Vancouver", "Victoria", "Surrey", "Burnaby", "Kelowna"],
       "pacific", "mild", [4,5,6,7,8,9,10], "America/Vancouver",
       "mixed", "BC Liquor Stores + private licensees; LDB wholesale",
       "private_retail", "Private retail licensed by LCRB; BC Cannabis Stores as gov option",
       10_120_000, 8.5),
    _p("AB", "Alberta", 4_756_408,
       ["Calgary", "Edmonton", "Red Deer", "Lethbridge"],
       "continental", "harsh", [5,6,7,8,9], "America/Edmonton",
       "private", "Fully privatized retail since 1993; AGLC regulates",
       "private_retail", "Fully private retail licensed by AGLC — highest store density in Canada",
       11_280_000, 7.2),
    _p("QC", "Quebec", 8_945_709,
       ["Montreal", "Quebec City", "Laval", "Gatineau", "Longueuil"],
       "continental", "harsh", [5,6,7,8,9], "America/Toronto",
       "provincial_monopoly", "SAQ monopoly on wine/spirits; beer/cider in depanneurs/grocery",
       "government_only", "SQDC is sole legal retailer — no private cannabis retail",
       9_160_000, 8.1),
    _p("SK", "Saskatchewan", 1_218_073,
       ["Saskatoon", "Regina", "Prince Albert", "Moose Jaw"],
       "continental", "extreme", [6,7,8], "America/Regina",
       "mixed", "SLGA stores + private retail; SLGA regulates wholesale",
       "private_retail", "Private retail licensed by SLGA", 9_740_000, 6.0),
    _p("MB", "Manitoba", 1_444_190,
       ["Winnipeg", "Brandon", "Steinbach", "Thompson"],
       "continental", "extreme", [6,7,8], "America/Winnipeg",
       "provincial_monopoly", "Manitoba Liquor Marts; LGCA regulates",
       "private_retail", "Private retail licensed by LGCA; first province to allow private sales",
       9_000_000, 6.5),
    _p("NS", "Nova Scotia", 1_058_094,
       ["Halifax", "Dartmouth", "Sydney", "Truro"],
       "mild_maritime", "moderate", [5,6,7,8,9], "America/Halifax",
       "provincial_monopoly", "NSLC stores monopoly; agency stores in rural areas",
       "government_only", "NSLC is sole legal retailer", 8_640_000, 7.0),
    _p("NB", "New Brunswick", 832_322,
       ["Moncton", "Saint John", "Fredericton"],
       "mild_maritime", "moderate", [5,6,7,8,9], "America/Moncton",
       "provincial_monopoly", "NB Liquor stores monopoly",
       "government_only", "Cannabis NB is sole legal retailer", 8_320_000, 6.2),
    _p("PE", "Prince Edward Island", 175_853,
       ["Charlottetown", "Summerside"],
       "mild_maritime", "moderate", [5,6,7,8,9], "America/Halifax",
       "provincial_monopoly", "PEI Liquor Control Commission stores",
       "government_only", "PEI Cannabis Management Corp. retail", 8_180_000, 7.5),
    _p("NL", "Newfoundland and Labrador", 531_948,
       ["St. John's", "Mount Pearl", "Corner Brook"],
       "mild_maritime", "harsh", [6,7,8], "America/St_Johns",
       "provincial_monopoly", "NLC stores; Labrador has some agency stores",
       "hybrid", "NLC retail + limited private retail licenses", 8_560_000, 6.8),
    _p("YT", "Yukon", 44_238,
       ["Whitehorse", "Dawson City"],
       "arctic", "extreme", [6,7,8], "America/Whitehorse",
       "provincial_monopoly", "Yukon Liquor Corporation",
       "hybrid", "Government + private retail", 10_800_000, 9.0),
    _p("NT", "Northwest Territories", 44_895,
       ["Yellowknife", "Hay River", "Inuvik"],
       "arctic", "extreme", [6,7,8], "America/Yellowknife",
       "mixed", "NTLCC operates stores; some community prohibitions",
       "government_only", "NTLCC sole retailer", 12_160_000, 5.5),
    _p("NU", "Nunavut", 40_586,
       ["Iqaluit", "Rankin Inlet"],
       "arctic", "extreme", [7,8], "America/Iqaluit",
       "mixed", "Community-by-community alcohol restrictions; NULC",
       "government_only", "NLC sole retailer; very limited access", 11_520_000, 3.0),
]}

# ─── Seasonal Climate Impact ────────────────────────────────
# Source: Statistics Canada Table 20-10-0056, CRFA 2024

SEASONAL_TRAFFIC_FACTORS: dict[str, dict[int, float]] = {
    "continental": {
        1: 0.72, 2: 0.74, 3: 0.82, 4: 0.92, 5: 1.05,
        6: 1.18, 7: 1.22, 8: 1.20, 9: 1.08, 10: 0.98, 11: 0.88, 12: 1.05},
    "pacific": {
        1: 0.85, 2: 0.87, 3: 0.92, 4: 0.97, 5: 1.05,
        6: 1.12, 7: 1.15, 8: 1.14, 9: 1.06, 10: 0.98, 11: 0.92, 12: 1.00},
    "mild_maritime": {
        1: 0.78, 2: 0.80, 3: 0.87, 4: 0.95, 5: 1.05,
        6: 1.15, 7: 1.18, 8: 1.16, 9: 1.06, 10: 0.96, 11: 0.88, 12: 1.02},
    "arctic": {
        1: 0.60, 2: 0.62, 3: 0.70, 4: 0.80, 5: 0.95,
        6: 1.20, 7: 1.30, 8: 1.25, 9: 1.00, 10: 0.82, 11: 0.70, 12: 0.90},
}

# ─── ProvincialAnalyzer ─────────────────────────────────────

class ProvincialAnalyzer:
    """Province-specific analysis for Canadian merchants."""

    def __init__(self, province: str = "ON"):
        self.province = province.upper()
        self.profile = PROVINCE_PROFILES.get(self.province)
        self.tax = PROVINCIAL_TAX.get(self.province)
        if not self.profile:
            logger.warning(f"Unknown province '{self.province}', defaulting to ON")
            self.province = "ON"
            self.profile = PROVINCE_PROFILES["ON"]
            self.tax = PROVINCIAL_TAX["ON"]

    def get_tax_summary(self) -> dict:
        t = self.tax
        return {
            "province": self.province, "model": t.model,
            "gst_pct": t.gst_pct, "pst_pct": t.pst_pct,
            "hst_pct": t.hst_pct, "qst_pct": t.qst_pct,
            "total_sales_tax_pct": t.total_sales_tax_pct,
            "effective_on_100_dollar_sale_cents": round(10000 * t.total_sales_tax_pct / 100),
        }

    def get_minimum_wage_cents(self) -> int:
        return MINIMUM_WAGE_CENTS.get(self.province, 1500)

    def estimate_hourly_labor_cost_cents(self, wage_multiplier: float = 1.15) -> int:
        """True hourly cost incl. CPP, EI, vacation pay, WCB. Source: CFIB 2024."""
        return round(MINIMUM_WAGE_CENTS.get(self.province, 1500) * wage_multiplier)

    def get_seasonal_factor(self, month: int) -> float:
        if not self.profile:
            return 1.0
        return SEASONAL_TRAFFIC_FACTORS.get(self.profile.climate_zone, {}).get(month, 1.0)

    def is_patio_season(self, month: int) -> bool:
        if not self.profile:
            return 5 <= month <= 9
        return month in self.profile.patio_season_months

    def get_regulatory_context(self, vertical: str = "other") -> dict:
        p = self.profile
        ctx: dict = {"province": self.province, "province_name": p.name,
                     "vertical": vertical, "regulations": []}

        if vertical in ("bar", "restaurant"):
            ctx["regulations"].append({
                "area": "alcohol", "model": p.alcohol_model,
                "details": p.alcohol_notes,
                "impact": "Affects wholesale sourcing costs and licensing requirements"})
            if self.province == "QC":
                ctx["regulations"].append({
                    "area": "language",
                    "details": ("Charter of the French Language (Bill 96): all signage, "
                                "menus, and customer-facing materials must be in French"),
                    "impact": "Menu printing, POS display, marketing materials affected"})

        if vertical in ("cannabis", "smoke_shop"):
            ctx["regulations"].append({
                "area": "cannabis", "model": p.cannabis_model,
                "details": p.cannabis_notes,
                "impact": self._cannabis_impact()})

        if vertical == "smoke_shop":
            ctx["regulations"].append({
                "area": "tobacco",
                "details": "Tobacco and Vaping Products Act + provincial display bans",
                "impact": "Higher labor cost for retrieval-based service model"})

        ctx["regulations"].append({
            "area": "labor",
            "minimum_wage_cents": self.get_minimum_wage_cents(),
            "details": f"Provincial minimum wage: ${self.get_minimum_wage_cents()/100:.2f}/hr",
            "impact": "Directly affects labor cost as % of revenue"})
        return ctx

    def _cannabis_impact(self) -> str:
        m = self.profile.cannabis_model
        if m == "government_only":
            return "Government monopoly — no private retail. Limited pricing flexibility."
        if m == "private_retail":
            return "Private retail — competitive market with licensing requirements."
        return "Hybrid model — government and private retail coexist."

    def get_market_context(self) -> dict:
        p = self.profile
        return {
            "province": self.province, "province_name": p.name,
            "population": p.population, "major_cities": p.major_cities,
            "avg_household_income_cents": p.avg_household_income_cents,
            "restaurant_density_per_10k": p.restaurant_density_per_10k,
            "climate_zone": p.climate_zone, "winter_severity": p.winter_severity,
            "patio_season_months": p.patio_season_months}

    def get_provincial_holidays(self, year: int) -> list[dict]:
        from .holidays import get_holidays_for_month
        result = []
        for m in range(1, 13):
            result.extend(get_holidays_for_month(year, m, self.province))
        return result

    def compare_to_national(self) -> dict:
        """Compare this province to national averages (StatsCan)."""
        nat_wage, nat_income, nat_tax = 1567, 9_840_000, 11.5
        w = self.get_minimum_wage_cents()
        i = self.profile.avg_household_income_cents
        t = self.tax.total_sales_tax_pct
        return {
            "province": self.province,
            "minimum_wage": {"provincial_cents": w, "national_avg_cents": nat_wage,
                             "delta_pct": round((w - nat_wage) / nat_wage * 100, 1)},
            "household_income": {"provincial_cents": i, "national_avg_cents": nat_income,
                                 "delta_pct": round((i - nat_income) / nat_income * 100, 1)},
            "sales_tax": {"provincial_pct": t, "national_avg_pct": nat_tax,
                          "delta_pp": round(t - nat_tax, 1)},
        }
