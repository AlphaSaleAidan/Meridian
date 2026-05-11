from .base import BaseAgent
from .revenue_trend import RevenueTrendAgent
from .cash_flow import CashFlowAgent
from .pricing_power import PricingPowerAgent
from .discount_analyzer import DiscountAnalyzerAgent
from .product_velocity import ProductVelocityAgent
from .basket_analysis import BasketAnalysisAgent
from .category_mix import CategoryMixAgent
from .inventory_intel import InventoryIntelAgent
from .peak_hours import PeakHoursAgent
from .seasonality import SeasonalityAgent
from .day_of_week import DayOfWeekAgent
from .employee_perf import EmployeePerformanceAgent
from .payment_optimizer import PaymentOptimizerAgent
from .waste_shrinkage import WasteShrinkageAgent
from .staffing import StaffingAgent
from .benchmark import BenchmarkAgent
from .money_left import MoneyLeftAgent
from .forecaster import ForecasterAgent
from .customer_ltv import CustomerLTVAgent
from .promo_roi import PromoROIAgent
from .cashflow_forecast import CashFlowForecastAgent
from .growth_score import GrowthScoreAgent
from .foot_traffic import FootTrafficAgent
from .dwell_time import DwellTimeAgent
from .customer_recognizer import CustomerRecognizerAgent
from .demographic_profiler import DemographicProfilerAgent
from .queue_monitor import QueueMonitorAgent

# Cross-Reference Intelligence Agents (camera + POS fusion)
from .cross_ref import (
    BaseCrossRefAgent,
    CrossRefContext,
    PathToPurchaseAgent,
    ZoneConversionAgent,
    LostSaleAgent,
    InfluenceZoneAgent,
    StaffEffectAgent,
    PeakBasketAgent,
    ReturnCustomerAgent,
    QueueBasketAgent,
    PosturePurchaseAgent,
    ProductPlacementAgent,
    ALL_CROSS_REF_AGENTS,
)
