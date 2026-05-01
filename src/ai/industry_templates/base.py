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


def get_industry_analyzer(business_type: str, org_id: str) -> IndustryAnalyzer:
    # Import all template modules to trigger @register decorators
    from . import restaurant, smoke_shop, retail, bar_nightclub, salon, coffee_shop
    cls = REGISTRY.get(business_type, GenericAnalyzer)
    return cls(org_id=org_id)
