"""
Dagster Definitions — Entry point for the Dagster pipeline.

Run with: dagster dev -m src.pipeline.definitions
"""
import dagster as dg

from .assets import raw_transactions, cleaned_transactions, daily_aggregates, agent_insights, merchant_reports
from .schedules import all_schedules

defs = dg.Definitions(
    assets=[
        raw_transactions,
        cleaned_transactions,
        daily_aggregates,
        agent_insights,
        merchant_reports,
    ],
    schedules=all_schedules,
)
