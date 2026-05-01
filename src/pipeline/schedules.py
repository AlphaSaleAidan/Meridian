"""
Dagster Schedules — Nightly and weekly pipeline runs.
"""
import dagster as dg

from .assets import raw_transactions, cleaned_transactions, daily_aggregates, agent_insights, merchant_reports


nightly_schedule = dg.ScheduleDefinition(
    name="nightly_pipeline",
    cron_schedule="0 2 * * *",  # 2 AM UTC
    target=dg.AssetSelection.assets(
        raw_transactions,
        cleaned_transactions,
        daily_aggregates,
        agent_insights,
    ),
    default_status=dg.DefaultScheduleStatus.RUNNING,
)

weekly_report_schedule = dg.ScheduleDefinition(
    name="weekly_reports",
    cron_schedule="0 3 * * 0",  # 3 AM UTC on Sundays
    target=dg.AssetSelection.assets(
        raw_transactions,
        cleaned_transactions,
        daily_aggregates,
        agent_insights,
        merchant_reports,
    ),
    default_status=dg.DefaultScheduleStatus.RUNNING,
)

all_schedules = [nightly_schedule, weekly_report_schedule]
