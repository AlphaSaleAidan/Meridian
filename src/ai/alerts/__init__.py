from .base import BaseAlert, AlertSeverity
from .revenue_anomaly import RevenueAnomalyAlert
from .margin_erosion import MarginErosionAlert
from .stockout_predictor import StockoutAlert
from .employee_shift import EmployeeShiftAlert
from .payment_fraud import PaymentFraudAlert
from .trend_break import TrendBreakAlert

ALL_ALERTS = [
    RevenueAnomalyAlert,
    MarginErosionAlert,
    StockoutAlert,
    EmployeeShiftAlert,
    PaymentFraudAlert,
    TrendBreakAlert,
]
