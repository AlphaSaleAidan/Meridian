"""
Industry Analyzer Base — Abstract template for vertical-specific analysis.

Adding a new industry:
  1. Create src/ai/industry_templates/your_industry.py
  2. Inherit from IndustryAnalyzer
  3. Override methods with industry-specific logic
  4. Register with @register decorator

The engine auto-selects the right template based on org.business_type.
"""
import logging
from abc import ABC, abstractmethod
from ..economics.benchmarks import IndustryBenchmarks

logger = logging.getLogger("meridian.ai.industry_templates")


class IndustryAnalyzer(ABC):

    vertical: str = "other"
    label: str = "General Business"

    def __init__(self, org_id: str):
        self.org_id = org_id
        self.benchmarks = IndustryBenchmarks(self.vertical)

    @abstractmethod
    def analyze_revenue(self, data: dict) -> dict:
        ...

    @abstractmethod
    def analyze_products(self, data: dict) -> dict:
        ...

    @abstractmethod
    def analyze_patterns(self, data: dict) -> dict:
        ...

    @abstractmethod
    def calculate_money_left(self, data: dict) -> dict:
        ...

    def get_benchmarks(self) -> dict:
        b = self.benchmarks.data
        return {
            "vertical": b.vertical,
            "label": b.label,
            "avg_ticket_cents": b.avg_ticket_cents,
            "avg_daily_revenue_cents": b.avg_daily_revenue_cents,
            "gross_margin_pct": b.gross_margin_pct,
            "net_margin_pct": b.net_margin_pct,
            "labor_cost_pct": b.labor_cost_pct,
            "cogs_pct": b.cogs_pct,
            "inventory_turnover_per_year": b.inventory_turnover_per_year,
            "peak_hour_revenue_share_pct": b.peak_hour_revenue_share_pct,
        }

    def get_kpis(self) -> list[str]:
        return ["revenue", "avg_ticket", "transaction_count", "gross_margin"]

    def get_peak_hours(self) -> list[int]:
        return [11, 12, 13, 17, 18, 19]


class GenericAnalyzer(IndustryAnalyzer):

    vertical = "other"
    label = "General Business"

    def analyze_revenue(self, data: dict) -> dict:
        return {"industry_context": "general", "adjustments": []}

    def analyze_products(self, data: dict) -> dict:
        return {"industry_context": "general", "adjustments": []}

    def analyze_patterns(self, data: dict) -> dict:
        return {"industry_context": "general", "adjustments": []}

    def calculate_money_left(self, data: dict) -> dict:
        return {"industry_context": "general", "adjustments": []}


REGISTRY: dict[str, type[IndustryAnalyzer]] = {}


def register(cls: type[IndustryAnalyzer]) -> type[IndustryAnalyzer]:
    REGISTRY[cls.vertical] = cls
    return cls


_TEMPLATES_LOADED = False


def _ensure_templates_loaded() -> None:
    """Import every template module in this package once so their @register
    decorators fire and populate REGISTRY. Without this the registry is empty
    and every lookup falls through to GenericAnalyzer. Auto-discovers modules so
    new templates need no edit here."""
    global _TEMPLATES_LOADED
    if _TEMPLATES_LOADED:
        return
    import importlib
    import pkgutil

    pkg = importlib.import_module(__package__)
    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name == "base":
            continue
        try:
            importlib.import_module(f"{__package__}.{mod.name}")
        except Exception:  # a broken template must not take down analysis
            logger.exception("industry template %s failed to import", mod.name)
    _TEMPLATES_LOADED = True


# Maps the many vertical vocabularies (proposal-deck slugs, POS-detected labels,
# DB values) onto the 16 registered template keys. Anything unmapped falls
# through to GenericAnalyzer — same as before this map existed, so it can only
# improve selection, never regress it.
_VERTICAL_ALIASES: dict[str, str] = {
    "cafe": "coffee_shop", "coffee": "coffee_shop", "espresso": "coffee_shop",
    "qsr": "restaurant", "fast_food": "restaurant", "fastfood": "restaurant",
    "quick_service": "restaurant", "full_restaurant": "restaurant",
    "ghost_kitchen": "restaurant", "diner": "restaurant", "eatery": "restaurant",
    "smokeshop": "smoke_shop", "smoke": "smoke_shop", "vape": "smoke_shop", "vape_shop": "smoke_shop",
    "auto_shop": "auto_repair", "autoshop": "auto_repair", "auto": "auto_repair",
    "mechanic": "auto_repair", "autobody": "auto_repair", "auto_body": "auto_repair",
    "foodtruck": "food_truck",
    "dispensary": "cannabis", "weed": "cannabis", "marijuana": "cannabis", "cbd": "cannabis",
    "gym": "fitness", "yoga": "fitness", "crossfit": "fitness", "yoga_studio": "fitness",
    "martialarts": "fitness", "martial_arts": "fitness", "pilates": "fitness", "studio": "fitness",
    "nightclub": "bar", "club": "bar", "pub": "bar", "lounge": "bar", "tavern": "bar",
    "nailsalon": "salon", "nail": "salon", "nail_salon": "salon", "hair": "salon",
    "barber": "salon", "beauty": "salon", "hair_salon": "salon",
    "brewpub": "brewery", "taproom": "brewery", "microbrewery": "brewery",
    "pizzeria": "pizza",
    "massage": "spa", "wellness": "spa", "day_spa": "spa", "med_spa": "spa",
    "market": "grocery", "supermarket": "grocery", "grocer": "grocery",
    "boutique": "retail", "shop": "retail", "store": "retail", "apparel": "retail", "clothing": "retail",
    "cstore": "convenience", "corner_store": "convenience", "liquor": "convenience",
    "liquor_store": "convenience", "gas_station": "convenience", "bodega": "convenience",
}


def normalize_vertical(raw: str | None) -> str:
    """Fold a free-form vertical value onto a registered template key.
    Lowercases, unifies separators, strips ca-/us- market prefixes, then applies
    the alias map. Returns 'other' for empty input; returns the cleaned token
    (which the caller will map to GenericAnalyzer) for anything unrecognized."""
    if not raw:
        return "other"
    v = raw.strip().lower().replace(" ", "_").replace("-", "_")
    for pref in ("ca_", "us_"):
        if v.startswith(pref):
            v = v[len(pref):]
            break
    _ensure_templates_loaded()
    if v in REGISTRY:
        return v
    return _VERTICAL_ALIASES.get(v, v)


def get_industry_analyzer(business_type: str, org_id: str) -> IndustryAnalyzer:
    _ensure_templates_loaded()
    key = normalize_vertical(business_type)
    cls = REGISTRY.get(key, GenericAnalyzer)
    return cls(org_id=org_id)
