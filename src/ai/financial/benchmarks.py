"""
Public Financial Benchmarks — NAICS industry classifications.
Sources: Census ABS 2023, BLS QCEW 2024, IBIS World 2025, NRA 2025, SBA 2024.
All monetary values in cents (annual basis unless noted).
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger("meridian.ai.financial.benchmarks")


# ── NAICS code mapping ────────────────────────────────────────

NAICS_MAP: dict[str, str] = {
    "coffee_shop": "722515",
    "restaurant": "722511",
    "quick_service": "722513",
    "retail": "44-45",
    "bar": "722410",
    "grocery": "445110",
    "cannabis": "453998",
    "salon": "812111",
    "auto_repair": "811111",
    "fitness": "713940",
    "pharmacy": "446110",
    "bakery": "311811",
    "hotel": "721110",
    "convenience": "445120",
    "brewery": "312120",
}


@dataclass
class IndustryBenchmark:
    """Financial benchmarks for a single NAICS sector."""
    naics_code: str
    label: str
    vertical: str

    # Annual revenue (cents) — 25th/50th/75th percentile
    revenue_p25_cents: int
    revenue_p50_cents: int
    revenue_p75_cents: int

    # Employee count ranges
    employees_p25: int
    employees_p50: int
    employees_p75: int

    # Profit margin range (percent)
    profit_margin_low: float
    profit_margin_mid: float
    profit_margin_high: float

    # Failure rates (percent)
    failure_rate_1yr: float
    failure_rate_3yr: float
    failure_rate_5yr: float

    # Growth rate vs GDP (percent)
    growth_vs_gdp: float

    # Revenue per employee (cents, annual)
    rev_per_employee_cents: int

    # Gross margin (percent)
    gross_margin_pct: float

    # Source citations
    source: str

    def to_dict(self) -> dict:
        return {
            "naics_code": self.naics_code,
            "label": self.label,
            "vertical": self.vertical,
            "revenue_percentiles_cents": {
                "p25": self.revenue_p25_cents,
                "p50": self.revenue_p50_cents,
                "p75": self.revenue_p75_cents,
            },
            "employee_count": {
                "p25": self.employees_p25,
                "p50": self.employees_p50,
                "p75": self.employees_p75,
            },
            "profit_margin_pct": {
                "low": self.profit_margin_low,
                "mid": self.profit_margin_mid,
                "high": self.profit_margin_high,
            },
            "failure_rates_pct": {
                "year_1": self.failure_rate_1yr,
                "year_3": self.failure_rate_3yr,
                "year_5": self.failure_rate_5yr,
            },
            "growth_vs_gdp_pct": self.growth_vs_gdp,
            "rev_per_employee_cents": self.rev_per_employee_cents,
            "gross_margin_pct": self.gross_margin_pct,
            "source": self.source,
        }


# ── Benchmark Data ────────────────────────────────────────────
# Data compiled from Census ABS, BLS QCEW, IBIS World, NRA, SBA

_BENCHMARKS: dict[str, IndustryBenchmark] = {
    "coffee_shop": IndustryBenchmark(
        "722515", "Coffee Shop / Cafe", "coffee_shop",
        21_000_000_00, 42_000_000_00, 78_000_000_00, 4, 8, 15,
        2.0, 7.5, 15.0, 18.0, 45.0, 60.0, 1.8, 5_250_000_00, 68.0,
        "Census ABS 2023; IBIS World 72251; NRA 2025"),
    "restaurant": IndustryBenchmark(
        "722511", "Full-Service Restaurant", "restaurant",
        50_000_000_00, 110_000_000_00, 240_000_000_00, 10, 22, 45,
        1.0, 5.0, 12.0, 17.0, 50.0, 65.0, 0.5, 5_000_000_00, 62.0,
        "Census ABS 2023; NRA 2025; BLS QCEW 2024"),
    "quick_service": IndustryBenchmark(
        "722513", "Quick-Service Restaurant", "quick_service",
        35_000_000_00, 85_000_000_00, 180_000_000_00, 8, 15, 30,
        3.0, 8.0, 15.0, 15.0, 40.0, 55.0, 2.5, 5_667_000_00, 65.0,
        "Census ABS 2023; IBIS World 72251; NRA 2025"),
    "retail": IndustryBenchmark(
        "44-45", "Retail Trade", "retail",
        30_000_000_00, 95_000_000_00, 300_000_000_00, 3, 8, 20,
        1.5, 5.0, 10.0, 12.0, 36.0, 50.0, 0.8, 11_875_000_00, 50.0,
        "Census ABS 2023; NRF 2024; BLS QCEW 2024"),
    "bar": IndustryBenchmark(
        "722410", "Bar / Drinking Place", "bar",
        25_000_000_00, 60_000_000_00, 130_000_000_00, 4, 10, 20,
        4.0, 10.0, 18.0, 20.0, 50.0, 65.0, 0.3, 6_000_000_00, 72.0,
        "Census ABS 2023; IBIS World 72241; BLS QCEW 2024"),
    "grocery": IndustryBenchmark(
        "445110", "Supermarket / Grocery", "grocery",
        200_000_000_00, 600_000_000_00, 1_500_000_000_00, 15, 40, 100,
        1.0, 2.5, 4.0, 8.0, 25.0, 40.0, 1.2, 15_000_000_00, 28.0,
        "Census ABS 2023; FMI 2024; BLS QCEW 2024"),
    "cannabis": IndustryBenchmark(
        "453998", "Cannabis Dispensary", "cannabis",
        80_000_000_00, 200_000_000_00, 500_000_000_00, 5, 12, 25,
        5.0, 15.0, 25.0, 20.0, 40.0, 55.0, 8.0, 16_667_000_00, 50.0,
        "IBIS World 45399; Headset Analytics 2024"),
    "salon": IndustryBenchmark(
        "812111", "Barber / Beauty Salon", "salon",
        15_000_000_00, 35_000_000_00, 80_000_000_00, 2, 5, 12,
        4.0, 10.0, 18.0, 14.0, 38.0, 52.0, 1.0, 7_000_000_00, 55.0,
        "Census ABS 2023; IBIS World 81211; BLS QCEW 2024"),
    "auto_repair": IndustryBenchmark(
        "811111", "General Auto Repair", "auto_repair",
        30_000_000_00, 70_000_000_00, 150_000_000_00, 3, 6, 12,
        5.0, 12.0, 20.0, 12.0, 32.0, 45.0, 1.5, 11_667_000_00, 55.0,
        "Census ABS 2023; IBIS World 81111; Auto Care Assoc. 2024"),
    "fitness": IndustryBenchmark(
        "713940", "Fitness / Recreation Center", "fitness",
        20_000_000_00, 55_000_000_00, 150_000_000_00, 4, 10, 25,
        5.0, 14.0, 25.0, 16.0, 42.0, 58.0, 3.0, 5_500_000_00, 60.0,
        "Census ABS 2023; IBIS World 71394; IHRSA 2024"),
    "pharmacy": IndustryBenchmark(
        "446110", "Pharmacy / Drug Store", "pharmacy",
        150_000_000_00, 400_000_000_00, 900_000_000_00, 5, 12, 25,
        1.5, 4.0, 8.0, 6.0, 18.0, 30.0, 2.0, 33_333_000_00, 28.0,
        "Census ABS 2023; IBIS World 44611; NACDS 2024"),
    "bakery": IndustryBenchmark(
        "311811", "Retail Bakery", "bakery",
        18_000_000_00, 40_000_000_00, 90_000_000_00, 3, 7, 15,
        3.0, 8.0, 15.0, 16.0, 42.0, 58.0, 1.5, 5_714_000_00, 60.0,
        "Census ABS 2023; IBIS World 31181; ABA 2024"),
    "hotel": IndustryBenchmark(
        "721110", "Hotel / Motel", "hotel",
        100_000_000_00, 350_000_000_00, 1_200_000_000_00, 10, 30, 80,
        5.0, 15.0, 30.0, 10.0, 28.0, 40.0, 2.0, 11_667_000_00, 72.0,
        "Census ABS 2023; IBIS World 72111; STR/CoStar 2024"),
    "convenience": IndustryBenchmark(
        "445120", "Convenience Store", "convenience",
        80_000_000_00, 180_000_000_00, 350_000_000_00, 3, 7, 15,
        1.5, 4.0, 7.0, 10.0, 30.0, 45.0, 1.0, 25_714_000_00, 32.0,
        "Census ABS 2023; NACS 2024; BLS QCEW 2024"),
    "brewery": IndustryBenchmark(
        "312120", "Brewery / Taproom", "brewery",
        25_000_000_00, 70_000_000_00, 200_000_000_00, 5, 12, 25,
        3.0, 10.0, 20.0, 15.0, 38.0, 52.0, 1.5, 5_833_000_00, 65.0,
        "Census ABS 2023; IBIS World 31212; Brewers Assoc. 2024"),
}


class PublicFinancialBenchmarks:
    """Compare a merchant's financials against NAICS industry benchmarks.

    Usage:
        bench = PublicFinancialBenchmarks("coffee_shop")
        comparison = bench.compare(annual_revenue_cents=3500000_00, employee_count=6)
        print(comparison)
    """

    def __init__(self, vertical: str = "other"):
        self.vertical = vertical
        self.benchmark = _BENCHMARKS.get(vertical)
        self.naics_code = NAICS_MAP.get(vertical, "")

    @property
    def available_verticals(self) -> list[str]:
        return list(_BENCHMARKS.keys())

    def get_benchmark(self) -> dict | None:
        if self.benchmark:
            return self.benchmark.to_dict()
        return None

    def compare(
        self,
        annual_revenue_cents: int | None = None,
        employee_count: int | None = None,
        profit_margin_pct: float | None = None,
        daily_revenue: list[dict] | None = None,
    ) -> dict:
        """Compare merchant metrics against industry benchmarks.

        If daily_revenue is provided and annual_revenue_cents is not,
        annualizes from the daily data.
        """
        if not self.benchmark:
            return {
                "status": "no_benchmark",
                "vertical": self.vertical,
                "message": f"No benchmark data for vertical '{self.vertical}'.",
            }

        b = self.benchmark
        comparisons: list[dict] = []

        # Annualize from daily data if needed
        if annual_revenue_cents is None and daily_revenue:
            daily_totals = [d.get("total_revenue_cents", 0) or 0 for d in daily_revenue]
            if daily_totals:
                import statistics
                avg_daily = statistics.mean(daily_totals)
                annual_revenue_cents = int(avg_daily * 365)

        # Revenue percentile
        if annual_revenue_cents is not None:
            pct = self._percentile(
                annual_revenue_cents, b.revenue_p25_cents, b.revenue_p50_cents, b.revenue_p75_cents
            )
            status = self._status_label(pct)
            comparisons.append({
                "metric": "annual_revenue",
                "actual_cents": annual_revenue_cents,
                "p25_cents": b.revenue_p25_cents,
                "p50_cents": b.revenue_p50_cents,
                "p75_cents": b.revenue_p75_cents,
                "percentile": pct,
                "status": status,
                "insight": (
                    f"${annual_revenue_cents / 100:,.0f}/yr puts you at the "
                    f"{pct:.0f}th percentile among {b.label} businesses."
                ),
            })

        # Revenue per employee
        if annual_revenue_cents is not None and employee_count and employee_count > 0:
            rev_per_emp = annual_revenue_cents // employee_count
            bench_rev_per_emp = b.rev_per_employee_cents
            if bench_rev_per_emp > 0:
                ratio = rev_per_emp / bench_rev_per_emp
                status = "above" if ratio > 1.1 else ("below" if ratio < 0.9 else "at_benchmark")
                comparisons.append({
                    "metric": "revenue_per_employee",
                    "actual_cents": rev_per_emp,
                    "benchmark_cents": bench_rev_per_emp,
                    "ratio": round(ratio, 2),
                    "status": status,
                    "insight": (
                        f"${rev_per_emp / 100:,.0f}/employee vs industry "
                        f"${bench_rev_per_emp / 100:,.0f} ({ratio:.1f}x benchmark)."
                    ),
                })

        # Profit margin
        if profit_margin_pct is not None:
            pct = self._percentile(
                profit_margin_pct, b.profit_margin_low, b.profit_margin_mid, b.profit_margin_high
            )
            comparisons.append({
                "metric": "profit_margin",
                "actual_pct": profit_margin_pct,
                "low_pct": b.profit_margin_low,
                "mid_pct": b.profit_margin_mid,
                "high_pct": b.profit_margin_high,
                "percentile": pct,
                "status": self._status_label(pct),
                "insight": (
                    f"{profit_margin_pct:.1f}% margin vs industry range "
                    f"{b.profit_margin_low:.1f}%-{b.profit_margin_high:.1f}%."
                ),
            })

        # Industry context
        context = {
            "failure_rates_pct": {
                "year_1": b.failure_rate_1yr,
                "year_3": b.failure_rate_3yr,
                "year_5": b.failure_rate_5yr,
            },
            "growth_vs_gdp_pct": b.growth_vs_gdp,
            "gross_margin_pct": b.gross_margin_pct,
            "source": b.source,
        }

        return {
            "vertical": self.vertical,
            "naics_code": self.naics_code,
            "label": b.label,
            "comparisons": comparisons,
            "industry_context": context,
        }

    @staticmethod
    def _percentile(value: float, p25: float, p50: float, p75: float) -> float:
        """Estimate percentile rank given 25th/50th/75th reference points."""
        if value <= p25:
            if p25 > 0:
                return max(0, 25 * (value / p25))
            return 0
        elif value <= p50:
            return 25 + 25 * ((value - p25) / max(p50 - p25, 1))
        elif value <= p75:
            return 50 + 25 * ((value - p50) / max(p75 - p50, 1))
        else:
            # Extrapolate above p75 (cap at 99)
            overshoot = (value - p75) / max(p75 - p50, 1)
            return min(99, 75 + 25 * overshoot)

    @staticmethod
    def _status_label(percentile: float) -> str:
        if percentile >= 75:
            return "top_quartile"
        elif percentile >= 50:
            return "above_median"
        elif percentile >= 25:
            return "below_median"
        else:
            return "bottom_quartile"
