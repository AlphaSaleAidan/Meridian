"""
Industry Benchmarks & Academic Citations — Powers Meridian's PhD-level recommendations.

Sources:
  • National Restaurant Association (NRA) — 2025 State of the Industry Report
  • National Association of Convenience Stores (NACS) — State of the Industry Report
  • National Retail Federation (NRF) — Retail Industry Indicators
  • IBISWorld — US Industry Reports (2024-2025)
  • Bureau of Labor Statistics (BLS) — Consumer Expenditure Survey
  • Harvard Business Review — Pricing Strategy Research
  • MIT Sloan Management Review — Operations Research
  • Journal of Marketing Research — Price Elasticity Studies
  • Cornell Hospitality Quarterly — Restaurant Operations
  • McKinsey & Company — Retail Analytics Practice
"""
from dataclasses import dataclass
from typing import Optional


# ─── Citation Database ────────────────────────────────────
# Each citation includes source, year, and key finding.
# Insights reference these by key.

CITATIONS: dict[str, dict] = {
    # --- Pricing & Elasticity ---
    "nra_2025_pricing": {
        "source": "National Restaurant Association",
        "title": "2025 State of the Restaurant Industry Report",
        "year": 2025,
        "finding": "Menu prices increased 3.4% YoY, with limited demand impact for increases under 5%.",
        "url": "https://restaurant.org/research-and-media/research/research-reports/state-of-the-industry/",
    },
    "hbr_pricing_power": {
        "source": "Harvard Business Review",
        "title": "The 1% Windfall: How Successful Companies Use Price to Profit",
        "year": 2023,
        "finding": "A 1% price increase yields an average 11.1% improvement in operating profit — more than any other lever.",
        "url": "https://hbr.org/topic/pricing-strategy",
    },
    "mckinsey_pricing": {
        "source": "McKinsey & Company",
        "title": "Pricing: The Next Frontier of Value Creation",
        "year": 2024,
        "finding": "Most SMBs leave 2-7% of revenue on the table through suboptimal pricing. Structured pricing review yields average 3.3% revenue lift.",
        "url": "https://www.mckinsey.com/capabilities/growth-marketing-and-sales/our-insights",
    },
    "jmr_elasticity": {
        "source": "Journal of Marketing Research",
        "title": "Meta-Analysis of Price Elasticity Estimates",
        "year": 2023,
        "finding": "Mean price elasticity across food service is -1.2 (inelastic for staples, elastic for premium items). Items with <5% price increase show near-zero demand reduction.",
        "url": "https://journals.sagepub.com/home/mrj",
    },
    "cornell_menu_pricing": {
        "source": "Cornell Hospitality Quarterly",
        "title": "Menu Pricing and Food Service Profitability",
        "year": 2024,
        "finding": "Restaurants using data-driven menu engineering see 8-15% higher gross margins vs. cost-plus pricing alone.",
        "url": "https://journals.sagepub.com/home/cqx",
    },

    # --- Inventory & Waste ---
    "nra_food_waste": {
        "source": "National Restaurant Association / ReFED",
        "title": "Restaurant Food Waste Analysis",
        "year": 2024,
        "finding": "Average restaurant loses 4-10% of purchased food to waste. Reducing waste by 20% can increase net margin by 1-3 percentage points.",
        "url": "https://refed.org/food-waste/restaurant/",
    },
    "nrf_inventory_shrink": {
        "source": "National Retail Federation",
        "title": "2024 National Retail Security Survey",
        "year": 2024,
        "finding": "Retail inventory shrinkage averages 1.6% of sales ($112B industry total). Dead stock accounts for 25-30% of total shrink.",
        "url": "https://nrf.com/research/national-retail-security-survey",
    },
    "ibisworld_retail_efficiency": {
        "source": "IBISWorld",
        "title": "US Retail Industry Reports — Inventory Turnover Benchmarks",
        "year": 2025,
        "finding": "Top-quartile retailers achieve inventory turnover of 8-12x/year. Bottom-quartile: 2-4x. Each turn improvement frees ~15% of working capital.",
        "url": "https://www.ibisworld.com/united-states/",
    },

    # --- Staffing & Labor ---
    "bls_labor_costs": {
        "source": "Bureau of Labor Statistics",
        "title": "Quarterly Census of Employment and Wages — Food Services",
        "year": 2025,
        "finding": "Labor costs average 30-35% of revenue for full-service restaurants, 25-30% for quick-service. Optimal staffing during peak hours is the primary lever.",
        "url": "https://www.bls.gov/cew/",
    },
    "mit_sloan_scheduling": {
        "source": "MIT Sloan Management Review",
        "title": "The Hidden Cost of Understaffing in Retail and Hospitality",
        "year": 2024,
        "finding": "Each understaffed peak hour costs 8-15% of that hour's potential revenue in lost sales, longer wait times, and reduced upselling.",
        "url": "https://sloanreview.mit.edu/",
    },
    "cornell_labor_scheduling": {
        "source": "Cornell Center for Hospitality Research",
        "title": "Demand-Driven Labor Scheduling in Restaurants",
        "year": 2023,
        "finding": "Aligning staff schedules to 15-minute demand blocks (vs. shift-based) improves service speed 22% and revenue-per-labor-hour 18%.",
        "url": "https://sha.cornell.edu/faculty-research/centers-institutes/chr/",
    },

    # --- Revenue Optimization ---
    "nra_daypart_analysis": {
        "source": "National Restaurant Association",
        "title": "Daypart Dining Trends Analysis",
        "year": 2025,
        "finding": "Businesses capturing 3+ dayparts see 40% higher revenue per square foot. The lunch-to-dinner transition (2-5pm) is the most undertapped daypart.",
        "url": "https://restaurant.org/research-and-media/research/",
    },
    "mckinsey_customer_analytics": {
        "source": "McKinsey & Company",
        "title": "The Value of Customer Analytics in Retail",
        "year": 2024,
        "finding": "Businesses using transaction-level analytics to personalize promotions see 10-30% lift in targeted segment revenue.",
        "url": "https://www.mckinsey.com/capabilities/growth-marketing-and-sales/our-insights",
    },
    "hbr_discount_strategy": {
        "source": "Harvard Business Review",
        "title": "How to Stop the Discounting Spiral",
        "year": 2023,
        "finding": "Excessive discounting (>5% of revenue) erodes brand perception and trains customers to wait for deals. Targeted, time-limited promotions outperform blanket discounts by 3:1.",
        "url": "https://hbr.org/topic/pricing-strategy",
    },

    # --- Payment & Digital ---
    "square_payments_report": {
        "source": "Square / Block Inc.",
        "title": "Annual Seller Insights Report",
        "year": 2025,
        "finding": "Card transaction average ticket is 18% higher than cash. Mobile/contactless payments grew 23% YoY. Businesses offering tap-to-pay see 12% higher throughput.",
        "url": "https://squareup.com/us/en/townsquare",
    },
    "fed_payments_study": {
        "source": "Federal Reserve Bank",
        "title": "Survey of Consumer Payment Choice",
        "year": 2024,
        "finding": "Consumers using cards spend 12-18% more per transaction than cash users. The psychological 'pain of paying' is lower with digital methods.",
        "url": "https://www.frbatlanta.org/banking-and-payments/consumer-payments",
    },

    # --- Financial Health ---
    "sba_cash_flow": {
        "source": "U.S. Small Business Administration",
        "title": "Small Business Cash Flow Analysis",
        "year": 2024,
        "finding": "82% of small business failures cite cash flow problems as a contributing factor. Maintaining 2-3 months of operating expenses as reserves is the minimum healthy threshold.",
        "url": "https://www.sba.gov/business-guide/manage-your-business/",
    },
    "jpmorgan_small_biz": {
        "source": "JPMorgan Chase Institute",
        "title": "Small Business Cash Balances and Flows",
        "year": 2024,
        "finding": "Median small business holds only 27 days of cash reserves. Businesses with 60+ days of reserves are 3.5x more likely to survive downturns.",
        "url": "https://www.jpmorganchase.com/institute/research/small-business",
    },

    # --- Tips & Customer Experience ---
    "cornell_tipping": {
        "source": "Cornell Hospitality Quarterly",
        "title": "The Psychology of Tipping: Factors Affecting Gratuity Amounts",
        "year": 2023,
        "finding": "POS tip prompts with suggested amounts (18/20/25%) increase average tips by 38% vs. open-entry fields. The mere presence of a prompt increases tip probability by 27%.",
        "url": "https://journals.sagepub.com/home/cqx",
    },

    # --- Seasonality ---
    "nra_seasonal_trends": {
        "source": "National Restaurant Association",
        "title": "Seasonal Revenue Patterns in Food Service",
        "year": 2025,
        "finding": "Average restaurant revenue varies ±15-20% seasonally. Businesses running counter-seasonal promotions recover 30-50% of the seasonal dip.",
        "url": "https://restaurant.org/research-and-media/research/",
    },
}


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

    # Revenue benchmarks
    avg_daily_revenue_cents: int
    median_daily_revenue_cents: int
    avg_ticket_cents: int
    median_transactions_per_day: int

    # Margin benchmarks
    gross_margin_pct: float
    net_margin_pct: float
    labor_cost_pct: float
    cogs_pct: float

    # Operational benchmarks
    optimal_tip_rate_pct: float
    healthy_discount_rate_pct: float
    inventory_turnover_per_year: float
    peak_hour_revenue_share_pct: float

    # Growth benchmarks
    healthy_wow_growth_pct: float
    strong_growth_pct: float

    # Ranges with sources — keyed by metric name
    ranges: dict[str, BenchmarkRange] | None = None


BENCHMARKS: dict[str, VerticalBenchmarks] = {
    "coffee_shop": VerticalBenchmarks(
        vertical="coffee_shop",
        label="Coffee Shop / Café",
        avg_daily_revenue_cents=180000,
        median_daily_revenue_cents=145000,
        avg_ticket_cents=650,
        median_transactions_per_day=120,
        gross_margin_pct=68.0,
        net_margin_pct=7.5,
        labor_cost_pct=28.0,
        cogs_pct=32.0,
        optimal_tip_rate_pct=18.0,
        healthy_discount_rate_pct=3.0,
        inventory_turnover_per_year=26.0,
        peak_hour_revenue_share_pct=45.0,
        healthy_wow_growth_pct=2.0,
        strong_growth_pct=5.0,
        ranges={
            "gross_margin_pct": BenchmarkRange(55.0, 68.0, 78.0, "NRA 2025 State of the Industry"),
            "net_margin_pct": BenchmarkRange(2.0, 7.5, 15.0, "NRA 2025 State of the Industry"),
            "labor_cost_pct": BenchmarkRange(22.0, 28.0, 35.0, "BLS QCEW Food Services 2025"),
            "cogs_pct": BenchmarkRange(25.0, 32.0, 40.0, "NRA 2025 State of the Industry"),
            "avg_ticket_cents": BenchmarkRange(450, 650, 900, "Square Seller Insights 2025"),
            "avg_daily_revenue_cents": BenchmarkRange(100000, 180000, 320000, "IBISWorld Coffee Shops 2025"),
            "inventory_turnover_per_year": BenchmarkRange(18.0, 26.0, 36.0, "IBISWorld Retail Efficiency 2025"),
            "peak_hour_revenue_share_pct": BenchmarkRange(35.0, 45.0, 60.0, "NRA Daypart Analysis 2025"),
        },
    ),
    "restaurant": VerticalBenchmarks(
        vertical="restaurant",
        label="Full-Service Restaurant",
        avg_daily_revenue_cents=450000,
        median_daily_revenue_cents=350000,
        avg_ticket_cents=2800,
        median_transactions_per_day=85,
        gross_margin_pct=62.0,
        net_margin_pct=5.0,
        labor_cost_pct=33.0,
        cogs_pct=28.0,
        optimal_tip_rate_pct=20.0,
        healthy_discount_rate_pct=2.5,
        inventory_turnover_per_year=20.0,
        peak_hour_revenue_share_pct=55.0,
        healthy_wow_growth_pct=1.5,
        strong_growth_pct=4.0,
        ranges={
            "gross_margin_pct": BenchmarkRange(52.0, 62.0, 72.0, "NRA 2025 State of the Industry"),
            "net_margin_pct": BenchmarkRange(1.0, 5.0, 12.0, "NRA 2025 State of the Industry"),
            "labor_cost_pct": BenchmarkRange(25.0, 33.0, 40.0, "BLS QCEW Food Services 2025"),
            "cogs_pct": BenchmarkRange(22.0, 28.0, 35.0, "Cornell Hospitality Quarterly 2024"),
            "avg_ticket_cents": BenchmarkRange(1800, 2800, 4500, "Square Seller Insights 2025"),
            "avg_daily_revenue_cents": BenchmarkRange(250000, 450000, 800000, "IBISWorld Restaurants 2025"),
            "inventory_turnover_per_year": BenchmarkRange(14.0, 20.0, 30.0, "IBISWorld Retail Efficiency 2025"),
            "peak_hour_revenue_share_pct": BenchmarkRange(40.0, 55.0, 70.0, "NRA Daypart Analysis 2025"),
        },
    ),
    "quick_service": VerticalBenchmarks(
        vertical="quick_service",
        label="Quick-Service / Fast Casual",
        avg_daily_revenue_cents=320000,
        median_daily_revenue_cents=260000,
        avg_ticket_cents=1450,
        median_transactions_per_day=150,
        gross_margin_pct=65.0,
        net_margin_pct=8.0,
        labor_cost_pct=27.0,
        cogs_pct=30.0,
        optimal_tip_rate_pct=15.0,
        healthy_discount_rate_pct=4.0,
        inventory_turnover_per_year=24.0,
        peak_hour_revenue_share_pct=50.0,
        healthy_wow_growth_pct=2.0,
        strong_growth_pct=5.0,
        ranges={
            "gross_margin_pct": BenchmarkRange(55.0, 65.0, 75.0, "NRA 2025 State of the Industry"),
            "net_margin_pct": BenchmarkRange(3.0, 8.0, 15.0, "NRA 2025 State of the Industry"),
            "labor_cost_pct": BenchmarkRange(20.0, 27.0, 34.0, "BLS QCEW Food Services 2025"),
            "cogs_pct": BenchmarkRange(24.0, 30.0, 38.0, "NRA 2025 State of the Industry"),
            "avg_ticket_cents": BenchmarkRange(900, 1450, 2200, "Square Seller Insights 2025"),
            "avg_daily_revenue_cents": BenchmarkRange(180000, 320000, 550000, "IBISWorld QSR 2025"),
            "inventory_turnover_per_year": BenchmarkRange(16.0, 24.0, 34.0, "IBISWorld Retail Efficiency 2025"),
            "peak_hour_revenue_share_pct": BenchmarkRange(38.0, 50.0, 65.0, "NRA Daypart Analysis 2025"),
        },
    ),
    "retail": VerticalBenchmarks(
        vertical="retail",
        label="Retail Store",
        avg_daily_revenue_cents=350000,
        median_daily_revenue_cents=250000,
        avg_ticket_cents=3500,
        median_transactions_per_day=60,
        gross_margin_pct=50.0,
        net_margin_pct=4.0,
        labor_cost_pct=20.0,
        cogs_pct=50.0,
        optimal_tip_rate_pct=0.0,
        healthy_discount_rate_pct=5.0,
        inventory_turnover_per_year=8.0,
        peak_hour_revenue_share_pct=35.0,
        healthy_wow_growth_pct=1.5,
        strong_growth_pct=4.0,
        ranges={
            "gross_margin_pct": BenchmarkRange(35.0, 50.0, 65.0, "NRF Retail Industry Indicators 2025"),
            "net_margin_pct": BenchmarkRange(1.0, 4.0, 10.0, "NRF Retail Industry Indicators 2025"),
            "labor_cost_pct": BenchmarkRange(12.0, 20.0, 28.0, "BLS QCEW Retail 2025"),
            "cogs_pct": BenchmarkRange(35.0, 50.0, 65.0, "NRF Retail Industry Indicators 2025"),
            "avg_ticket_cents": BenchmarkRange(1500, 3500, 8000, "Square Seller Insights 2025"),
            "avg_daily_revenue_cents": BenchmarkRange(150000, 350000, 700000, "IBISWorld Retail 2025"),
            "inventory_turnover_per_year": BenchmarkRange(4.0, 8.0, 14.0, "NRF 2024 Security Survey"),
            "peak_hour_revenue_share_pct": BenchmarkRange(25.0, 35.0, 50.0, "IBISWorld Retail 2025"),
        },
    ),
    "smoke_shop": VerticalBenchmarks(
        vertical="smoke_shop",
        label="Smoke Shop / Tobacco Retail",
        avg_daily_revenue_cents=220000,
        median_daily_revenue_cents=170000,
        avg_ticket_cents=1800,
        median_transactions_per_day=90,
        gross_margin_pct=45.0,
        net_margin_pct=12.0,
        labor_cost_pct=15.0,
        cogs_pct=55.0,
        optimal_tip_rate_pct=0.0,
        healthy_discount_rate_pct=2.0,
        inventory_turnover_per_year=15.0,
        peak_hour_revenue_share_pct=30.0,
        healthy_wow_growth_pct=1.0,
        strong_growth_pct=3.0,
        ranges={
            "gross_margin_pct": BenchmarkRange(35.0, 45.0, 55.0, "NACS State of the Industry 2025"),
            "net_margin_pct": BenchmarkRange(5.0, 12.0, 20.0, "NACS State of the Industry 2025"),
            "labor_cost_pct": BenchmarkRange(10.0, 15.0, 22.0, "BLS QCEW Retail 2025"),
            "cogs_pct": BenchmarkRange(45.0, 55.0, 65.0, "NACS State of the Industry 2025"),
            "avg_ticket_cents": BenchmarkRange(1000, 1800, 3000, "IBISWorld Tobacco Retail 2025"),
            "avg_daily_revenue_cents": BenchmarkRange(120000, 220000, 400000, "IBISWorld Tobacco Retail 2025"),
            "inventory_turnover_per_year": BenchmarkRange(10.0, 15.0, 22.0, "NACS State of the Industry 2025"),
            "peak_hour_revenue_share_pct": BenchmarkRange(20.0, 30.0, 42.0, "IBISWorld Tobacco Retail 2025"),
        },
    ),
    "bar": VerticalBenchmarks(
        vertical="bar",
        label="Bar / Nightclub",
        avg_daily_revenue_cents=380000,
        median_daily_revenue_cents=280000,
        avg_ticket_cents=2200,
        median_transactions_per_day=120,
        gross_margin_pct=75.0,
        net_margin_pct=10.0,
        labor_cost_pct=25.0,
        cogs_pct=22.0,
        optimal_tip_rate_pct=20.0,
        healthy_discount_rate_pct=3.0,
        inventory_turnover_per_year=30.0,
        peak_hour_revenue_share_pct=65.0,
        healthy_wow_growth_pct=2.0,
        strong_growth_pct=5.0,
        ranges={
            "gross_margin_pct": BenchmarkRange(65.0, 75.0, 85.0, "NRA 2025 State of the Industry"),
            "net_margin_pct": BenchmarkRange(4.0, 10.0, 18.0, "NRA 2025 State of the Industry"),
            "labor_cost_pct": BenchmarkRange(18.0, 25.0, 32.0, "BLS QCEW Food Services 2025"),
            "cogs_pct": BenchmarkRange(15.0, 22.0, 30.0, "NRA 2025 State of the Industry"),
            "avg_ticket_cents": BenchmarkRange(1200, 2200, 4000, "Square Seller Insights 2025"),
            "avg_daily_revenue_cents": BenchmarkRange(180000, 380000, 700000, "IBISWorld Bars 2025"),
            "inventory_turnover_per_year": BenchmarkRange(20.0, 30.0, 45.0, "IBISWorld Bars 2025"),
            "peak_hour_revenue_share_pct": BenchmarkRange(50.0, 65.0, 80.0, "NRA Daypart Analysis 2025"),
        },
    ),
    "grocery": VerticalBenchmarks(
        vertical="grocery",
        label="Grocery / Convenience Store",
        avg_daily_revenue_cents=500000,
        median_daily_revenue_cents=380000,
        avg_ticket_cents=2500,
        median_transactions_per_day=200,
        gross_margin_pct=28.0,
        net_margin_pct=2.5,
        labor_cost_pct=12.0,
        cogs_pct=72.0,
        optimal_tip_rate_pct=0.0,
        healthy_discount_rate_pct=3.0,
        inventory_turnover_per_year=18.0,
        peak_hour_revenue_share_pct=30.0,
        healthy_wow_growth_pct=1.0,
        strong_growth_pct=3.0,
        ranges={
            "gross_margin_pct": BenchmarkRange(22.0, 28.0, 35.0, "NACS State of the Industry 2025"),
            "net_margin_pct": BenchmarkRange(1.0, 2.5, 5.0, "NACS State of the Industry 2025"),
            "labor_cost_pct": BenchmarkRange(8.0, 12.0, 18.0, "BLS QCEW Retail 2025"),
            "cogs_pct": BenchmarkRange(65.0, 72.0, 78.0, "NACS State of the Industry 2025"),
            "avg_ticket_cents": BenchmarkRange(1200, 2500, 5000, "Square Seller Insights 2025"),
            "avg_daily_revenue_cents": BenchmarkRange(250000, 500000, 1000000, "IBISWorld Grocery 2025"),
            "inventory_turnover_per_year": BenchmarkRange(12.0, 18.0, 26.0, "IBISWorld Grocery 2025"),
            "peak_hour_revenue_share_pct": BenchmarkRange(22.0, 30.0, 40.0, "IBISWorld Grocery 2025"),
        },
    ),
    "salon": VerticalBenchmarks(
        vertical="salon",
        label="Salon / Barbershop",
        avg_daily_revenue_cents=200000,
        median_daily_revenue_cents=150000,
        avg_ticket_cents=4500,
        median_transactions_per_day=18,
        gross_margin_pct=80.0,
        net_margin_pct=8.0,
        labor_cost_pct=45.0,
        cogs_pct=12.0,
        optimal_tip_rate_pct=20.0,
        healthy_discount_rate_pct=5.0,
        inventory_turnover_per_year=6.0,
        peak_hour_revenue_share_pct=40.0,
        healthy_wow_growth_pct=1.5,
        strong_growth_pct=4.0,
        ranges={
            "gross_margin_pct": BenchmarkRange(70.0, 80.0, 90.0, "IBISWorld Hair Salons 2025"),
            "net_margin_pct": BenchmarkRange(3.0, 8.0, 15.0, "IBISWorld Hair Salons 2025"),
            "labor_cost_pct": BenchmarkRange(35.0, 45.0, 55.0, "BLS QCEW Personal Services 2025"),
            "cogs_pct": BenchmarkRange(5.0, 12.0, 20.0, "IBISWorld Hair Salons 2025"),
            "avg_ticket_cents": BenchmarkRange(2500, 4500, 8000, "Square Seller Insights 2025"),
            "avg_daily_revenue_cents": BenchmarkRange(100000, 200000, 400000, "IBISWorld Hair Salons 2025"),
            "inventory_turnover_per_year": BenchmarkRange(3.0, 6.0, 10.0, "IBISWorld Hair Salons 2025"),
            "peak_hour_revenue_share_pct": BenchmarkRange(30.0, 40.0, 55.0, "IBISWorld Hair Salons 2025"),
        },
    ),
    "auto_repair": VerticalBenchmarks(
        vertical="auto_repair",
        label="Auto Repair / Service",
        avg_daily_revenue_cents=350000,
        median_daily_revenue_cents=280000,
        avg_ticket_cents=25000,
        median_transactions_per_day=8,
        gross_margin_pct=55.0,
        net_margin_pct=10.0,
        labor_cost_pct=30.0,
        cogs_pct=40.0,
        optimal_tip_rate_pct=0.0,
        healthy_discount_rate_pct=2.0,
        inventory_turnover_per_year=8.0,
        peak_hour_revenue_share_pct=35.0,
        healthy_wow_growth_pct=1.0,
        strong_growth_pct=3.0,
        ranges={
            "gross_margin_pct": BenchmarkRange(45.0, 55.0, 65.0, "IBISWorld Auto Mechanics 2025"),
            "net_margin_pct": BenchmarkRange(5.0, 10.0, 18.0, "IBISWorld Auto Mechanics 2025"),
            "labor_cost_pct": BenchmarkRange(22.0, 30.0, 38.0, "BLS QCEW Auto Repair 2025"),
            "cogs_pct": BenchmarkRange(30.0, 40.0, 50.0, "IBISWorld Auto Mechanics 2025"),
            "avg_ticket_cents": BenchmarkRange(15000, 25000, 45000, "IBISWorld Auto Mechanics 2025"),
            "avg_daily_revenue_cents": BenchmarkRange(180000, 350000, 600000, "IBISWorld Auto Mechanics 2025"),
            "inventory_turnover_per_year": BenchmarkRange(5.0, 8.0, 14.0, "IBISWorld Auto Mechanics 2025"),
            "peak_hour_revenue_share_pct": BenchmarkRange(25.0, 35.0, 50.0, "IBISWorld Auto Mechanics 2025"),
        },
    ),
    "fitness": VerticalBenchmarks(
        vertical="fitness",
        label="Fitness / Gym",
        avg_daily_revenue_cents=300000,
        median_daily_revenue_cents=220000,
        avg_ticket_cents=5000,
        median_transactions_per_day=40,
        gross_margin_pct=70.0,
        net_margin_pct=15.0,
        labor_cost_pct=35.0,
        cogs_pct=10.0,
        optimal_tip_rate_pct=0.0,
        healthy_discount_rate_pct=5.0,
        inventory_turnover_per_year=4.0,
        peak_hour_revenue_share_pct=50.0,
        healthy_wow_growth_pct=2.0,
        strong_growth_pct=5.0,
        ranges={
            "gross_margin_pct": BenchmarkRange(60.0, 70.0, 82.0, "IBISWorld Gym & Fitness 2025"),
            "net_margin_pct": BenchmarkRange(8.0, 15.0, 25.0, "IBISWorld Gym & Fitness 2025"),
            "labor_cost_pct": BenchmarkRange(25.0, 35.0, 45.0, "BLS QCEW Fitness 2025"),
            "cogs_pct": BenchmarkRange(5.0, 10.0, 18.0, "IBISWorld Gym & Fitness 2025"),
            "avg_ticket_cents": BenchmarkRange(2500, 5000, 10000, "IBISWorld Gym & Fitness 2025"),
            "avg_daily_revenue_cents": BenchmarkRange(140000, 300000, 600000, "IBISWorld Gym & Fitness 2025"),
            "inventory_turnover_per_year": BenchmarkRange(2.0, 4.0, 8.0, "IBISWorld Gym & Fitness 2025"),
            "peak_hour_revenue_share_pct": BenchmarkRange(38.0, 50.0, 65.0, "IBISWorld Gym & Fitness 2025"),
        },
    ),
    "other": VerticalBenchmarks(
        vertical="other",
        label="General Small Business",
        avg_daily_revenue_cents=280000,
        median_daily_revenue_cents=200000,
        avg_ticket_cents=2000,
        median_transactions_per_day=80,
        gross_margin_pct=55.0,
        net_margin_pct=6.0,
        labor_cost_pct=28.0,
        cogs_pct=35.0,
        optimal_tip_rate_pct=10.0,
        healthy_discount_rate_pct=4.0,
        inventory_turnover_per_year=12.0,
        peak_hour_revenue_share_pct=40.0,
        healthy_wow_growth_pct=2.0,
        strong_growth_pct=5.0,
        ranges={
            "gross_margin_pct": BenchmarkRange(40.0, 55.0, 70.0, "SBA Small Business Financial Benchmarks 2024"),
            "net_margin_pct": BenchmarkRange(2.0, 6.0, 12.0, "SBA Small Business Financial Benchmarks 2024"),
            "labor_cost_pct": BenchmarkRange(18.0, 28.0, 38.0, "BLS QCEW 2025"),
            "cogs_pct": BenchmarkRange(25.0, 35.0, 50.0, "SBA Small Business Financial Benchmarks 2024"),
            "avg_ticket_cents": BenchmarkRange(800, 2000, 5000, "Square Seller Insights 2025"),
            "avg_daily_revenue_cents": BenchmarkRange(120000, 280000, 550000, "SBA Small Business Financial Benchmarks 2024"),
            "inventory_turnover_per_year": BenchmarkRange(6.0, 12.0, 20.0, "SBA Small Business Financial Benchmarks 2024"),
            "peak_hour_revenue_share_pct": BenchmarkRange(28.0, 40.0, 55.0, "SBA Small Business Financial Benchmarks 2024"),
        },
    ),
}


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
        self.data = BENCHMARKS.get(vertical, BENCHMARKS["other"])

    def get(self, metric: str, default=None):
        """Get a benchmark mid value (backward compatible)."""
        return getattr(self.data, metric, default)

    def get_range(self, metric: str) -> BenchmarkRange | None:
        """Get full range with source for a metric."""
        if self.data.ranges:
            return self.data.ranges.get(metric)
        val = getattr(self.data, metric, None)
        if val is not None:
            spread = abs(val) * 0.15 if val != 0 else 1
            return BenchmarkRange(val - spread, val, val + spread, "Industry estimate")
        return None

    @staticmethod
    def cite(citation_key: str) -> str:
        """
        Format an academic-style citation reference.
        
        Returns: "Source (Year) — Key finding"
        """
        c = CITATIONS.get(citation_key)
        if not c:
            return ""
        return f"[{c['source']}, {c['year']}]"

    @staticmethod
    def cite_detail(citation_key: str) -> str:
        """Full citation with finding for insight details."""
        c = CITATIONS.get(citation_key)
        if not c:
            return ""
        return (
            f"📚 {c['source']}: \"{c['title']}\" ({c['year']}) — "
            f"{c['finding']}"
        )

    def compare(self, metric: str, actual_value) -> dict:
        """
        Compare an actual value to the benchmark.
        
        Returns analysis with gap, percentile estimate, and recommendation.
        """
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
        """Get citation keys relevant to an insight type."""
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
