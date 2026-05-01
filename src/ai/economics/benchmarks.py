"""
Industry Benchmarks & Academic Citations — Powers Meridian's PhD-level recommendations.

Data loaded from YAML files in data/ directory.
"""
import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger("meridian.ai.economics.benchmarks")

_DATA_DIR = Path(__file__).parent / "data"


# ─── Load YAML Data ─────────────────────────────────────

def _load_citations() -> dict[str, dict]:
    path = _DATA_DIR / "citations.yaml"
    if not path.exists():
        logger.warning(f"Citations file not found: {path}")
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _load_benchmarks_raw() -> dict:
    path = _DATA_DIR / "benchmarks.yaml"
    if not path.exists():
        logger.warning(f"Benchmarks file not found: {path}")
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


CITATIONS: dict[str, dict] = _load_citations()


# ─── Benchmark Ranges with Sources ────────────────────────

@dataclass
class BenchmarkRange:
    low: float
    mid: float
    high: float
    source: str

    def percentile(self, actual: float) -> float:
        if self.high == self.low:
            return 0.5
        return max(0.0, min(1.0, (actual - self.low) / (self.high - self.low)))


# ─── Industry Benchmarks by Vertical ─────────────────────

@dataclass
class VerticalBenchmarks:
    """Benchmarks for a specific business vertical."""
    vertical: str
    label: str

    avg_daily_revenue_cents: int
    median_daily_revenue_cents: int
    avg_ticket_cents: int
    median_transactions_per_day: int

    gross_margin_pct: float
    net_margin_pct: float
    labor_cost_pct: float
    cogs_pct: float

    optimal_tip_rate_pct: float
    healthy_discount_rate_pct: float
    inventory_turnover_per_year: float
    peak_hour_revenue_share_pct: float

    healthy_wow_growth_pct: float
    strong_growth_pct: float

    ranges: dict[str, BenchmarkRange] | None = None


def _build_benchmarks() -> dict[str, VerticalBenchmarks]:
    raw = _load_benchmarks_raw()
    result = {}
    for key, data in raw.items():
        ranges = None
        if "ranges" in data:
            ranges = {
                metric: BenchmarkRange(
                    low=r["low"], mid=r["mid"], high=r["high"], source=r["source"]
                )
                for metric, r in data["ranges"].items()
            }
        result[key] = VerticalBenchmarks(
            vertical=key,
            label=data["label"],
            avg_daily_revenue_cents=data["avg_daily_revenue_cents"],
            median_daily_revenue_cents=data["median_daily_revenue_cents"],
            avg_ticket_cents=data["avg_ticket_cents"],
            median_transactions_per_day=data["median_transactions_per_day"],
            gross_margin_pct=data["gross_margin_pct"],
            net_margin_pct=data["net_margin_pct"],
            labor_cost_pct=data["labor_cost_pct"],
            cogs_pct=data["cogs_pct"],
            optimal_tip_rate_pct=data["optimal_tip_rate_pct"],
            healthy_discount_rate_pct=data["healthy_discount_rate_pct"],
            inventory_turnover_per_year=data["inventory_turnover_per_year"],
            peak_hour_revenue_share_pct=data["peak_hour_revenue_share_pct"],
            healthy_wow_growth_pct=data["healthy_wow_growth_pct"],
            strong_growth_pct=data["strong_growth_pct"],
            ranges=ranges,
        )
    return result


BENCHMARKS: dict[str, VerticalBenchmarks] = _build_benchmarks()


class IndustryBenchmarks:
    """
    Access industry benchmarks and format citation references.

    Usage:
        bench = IndustryBenchmarks("coffee_shop")
        bench.get("gross_margin_pct")  # 68.0
        bench.cite("hbr_pricing_power")  # formatted citation string
        bench.compare("avg_ticket_cents", actual_value)  # comparison analysis
    """

    def __init__(self, vertical: str = "other"):
        self.vertical = vertical
        self.data = BENCHMARKS.get(vertical, BENCHMARKS.get("other"))

    def get(self, metric: str, default=None):
        return getattr(self.data, metric, default)

    def get_range(self, metric: str) -> BenchmarkRange | None:
        if self.data.ranges:
            return self.data.ranges.get(metric)
        val = getattr(self.data, metric, None)
        if val is not None:
            spread = abs(val) * 0.15 if val != 0 else 1
            return BenchmarkRange(val - spread, val, val + spread, "Industry estimate")
        return None

    @staticmethod
    def cite(citation_key: str) -> str:
        c = CITATIONS.get(citation_key)
        if not c:
            return ""
        return f"[{c['source']}, {c['year']}]"

    @staticmethod
    def cite_detail(citation_key: str) -> str:
        c = CITATIONS.get(citation_key)
        if not c:
            return ""
        return (
            f"📚 {c['source']}: \"{c['title']}\" ({c['year']}) — "
            f"{c['finding']}"
        )

    def compare(self, metric: str, actual_value) -> dict:
        benchmark = getattr(self.data, metric, None)
        if benchmark is None or actual_value is None:
            return {"status": "no_benchmark"}

        if benchmark == 0:
            return {"status": "no_benchmark"}

        gap_pct = round((actual_value - benchmark) / benchmark * 100, 1)

        if gap_pct > 15:
            status = "above_benchmark"
            percentile_est = "top 20%"
        elif gap_pct > 0:
            status = "at_benchmark"
            percentile_est = "above median"
        elif gap_pct > -15:
            status = "near_benchmark"
            percentile_est = "near median"
        elif gap_pct > -30:
            status = "below_benchmark"
            percentile_est = "below median"
        else:
            status = "well_below_benchmark"
            percentile_est = "bottom quartile"

        rng = self.get_range(metric)
        result = {
            "status": status,
            "benchmark_value": benchmark,
            "actual_value": actual_value,
            "gap_pct": gap_pct,
            "percentile_estimate": percentile_est,
            "vertical": self.data.label,
        }
        if rng:
            result["range"] = {"low": rng.low, "mid": rng.mid, "high": rng.high, "source": rng.source}
            result["percentile_rank"] = round(rng.percentile(actual_value), 2)
        return result

    def get_relevant_citations(self, insight_type: str) -> list[str]:
        type_citations = {
            "pricing": [
                "hbr_pricing_power", "mckinsey_pricing", "jmr_elasticity",
                "cornell_menu_pricing",
            ],
            "product_recommendation": [
                "cornell_menu_pricing", "mckinsey_pricing",
                "nrf_inventory_shrink",
            ],
            "inventory": [
                "nrf_inventory_shrink", "ibisworld_retail_efficiency",
                "nra_food_waste",
            ],
            "staffing": [
                "bls_labor_costs", "mit_sloan_scheduling",
                "cornell_labor_scheduling",
            ],
            "money_left": [
                "mckinsey_pricing", "hbr_pricing_power",
                "mit_sloan_scheduling", "nra_food_waste",
            ],
            "general": [
                "nra_2025_pricing", "mckinsey_customer_analytics",
                "sba_cash_flow",
            ],
            "anomaly": [
                "nra_seasonal_trends", "mckinsey_customer_analytics",
            ],
            "tips": [
                "cornell_tipping", "square_payments_report",
            ],
            "payments": [
                "square_payments_report", "fed_payments_study",
            ],
            "discount": [
                "hbr_discount_strategy", "mckinsey_pricing",
            ],
        }
        return type_citations.get(insight_type, ["mckinsey_pricing"])
