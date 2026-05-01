"""
Dagster Software-Defined Assets — The Meridian data pipeline.

Asset graph:
  raw_transactions → cleaned_transactions → daily_aggregates
                                          → agent_insights → merchant_reports

Each asset is a materialized table in Supabase, tracked by Dagster.
"""
import logging
from datetime import datetime, timezone

import dagster as dg
import pandas as pd

logger = logging.getLogger("meridian.pipeline.assets")


@dg.asset(
    group_name="ingestion",
    description="Raw transactions from POS sync, validated via Great Expectations",
)
def raw_transactions(context: dg.AssetExecutionContext) -> pd.DataFrame:
    """Load raw transactions from Supabase and validate."""
    import asyncio
    from ..db import init_db, close_db

    async def _load():
        db = await init_db()
        if not db:
            return []
        try:
            orgs = await db.query("organizations", select="id", filters={"status": "eq.active"})
            all_txns = []
            for org in orgs:
                txns = await db.get_transaction_details(org["id"], days=1)
                all_txns.extend([dict(t) for t in txns])
            return all_txns
        finally:
            await close_db()

    txns = asyncio.run(_load())
    df = pd.DataFrame(txns) if txns else pd.DataFrame()
    context.log.info(f"Loaded {len(df)} raw transactions")

    if not df.empty:
        from ..data_quality.runner import validate_dataframe
        result = validate_dataframe(df, "transactions")
        context.log.info(f"Validation: {result}")

    return df


@dg.asset(
    group_name="transformation",
    description="Cleaned transactions — nulls removed, amounts validated, status filtered",
    deps=[raw_transactions],
)
def cleaned_transactions(context: dg.AssetExecutionContext, raw_transactions: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize transaction data."""
    if raw_transactions.empty:
        return raw_transactions

    df = raw_transactions.copy()

    if "total_cents" in df.columns:
        df = df[df["total_cents"].notna()]
        df = df[df["total_cents"] >= 0]
        df = df[df["total_cents"] <= 100_000_00]

    if "status" in df.columns:
        df = df[df["status"].isin(["COMPLETED", "REFUNDED"])]

    if "transaction_at" in df.columns:
        df["transaction_at"] = pd.to_datetime(df["transaction_at"], errors="coerce")
        df = df[df["transaction_at"].notna()]

    context.log.info(f"Cleaned: {len(raw_transactions)} → {len(df)} transactions")
    return df


@dg.asset(
    group_name="aggregation",
    description="Daily revenue aggregates per org — revenue, txn count, avg basket",
    deps=[cleaned_transactions],
)
def daily_aggregates(context: dg.AssetExecutionContext, cleaned_transactions: pd.DataFrame) -> pd.DataFrame:
    """Aggregate transactions into daily summaries per org."""
    if cleaned_transactions.empty:
        return pd.DataFrame()

    df = cleaned_transactions.copy()
    if "transaction_at" not in df.columns or "business_id" not in df.columns:
        return pd.DataFrame()

    df["date"] = df["transaction_at"].dt.date

    agg = df.groupby(["business_id", "date"]).agg(
        revenue_cents=("total_cents", "sum"),
        transaction_count=("id", "count"),
        avg_basket_cents=("total_cents", "mean"),
    ).reset_index()

    agg["avg_basket_cents"] = agg["avg_basket_cents"].round(0).astype(int)

    context.log.info(f"Aggregated into {len(agg)} daily rows across {agg['business_id'].nunique()} orgs")
    return agg


@dg.asset(
    group_name="intelligence",
    description="AI agent insights generated from daily aggregates",
    deps=[daily_aggregates],
)
def agent_insights(context: dg.AssetExecutionContext, daily_aggregates: pd.DataFrame) -> list[dict]:
    """Run AI agents on aggregated data and collect insights."""
    if daily_aggregates.empty:
        return []

    import asyncio
    from ..ai.engine import MeridianAI, AnalysisContext

    async def _analyze():
        all_insights = []
        ai = MeridianAI()

        for org_id in daily_aggregates["business_id"].unique():
            org_data = daily_aggregates[daily_aggregates["business_id"] == org_id]
            ctx = AnalysisContext(
                org_id=org_id,
                daily_revenue=org_data.to_dict("records"),
                analysis_days=len(org_data),
            )
            result = await ai.analyze(ctx, include_forecasts=False, include_report=False)
            all_insights.extend(result.insights)

        return all_insights

    insights = asyncio.run(_analyze())
    context.log.info(f"Generated {len(insights)} insights")
    return insights


@dg.asset(
    group_name="output",
    description="Weekly merchant reports compiled from agent insights",
    deps=[agent_insights],
)
def merchant_reports(context: dg.AssetExecutionContext, agent_insights: list[dict]) -> list[dict]:
    """Compile insights into per-merchant report summaries."""
    if not agent_insights:
        return []

    from collections import defaultdict
    by_org: dict[str, list] = defaultdict(list)
    for insight in agent_insights:
        org = insight.get("org_id", "unknown")
        by_org[org].append(insight)

    reports = []
    for org_id, insights in by_org.items():
        reports.append({
            "org_id": org_id,
            "insight_count": len(insights),
            "categories": list({i.get("category", "general") for i in insights}),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

    context.log.info(f"Compiled {len(reports)} merchant reports")
    return reports
