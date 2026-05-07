"""
Meridian AI Engine — The Analytics Brain.

Orchestrates all AI analysis pipelines:
  • Revenue analysis (trends, forecasting, anomalies)
  • Product intelligence (performance, optimization, dead stock)
  • Pattern detection (peak hours, seasonality, staffing)
  • Money Left on Table scoring
  • Actionable insight generation
  • Weekly report compilation

The engine works in two modes:
  1. BATCH — Runs nightly (all merchants) — full analysis + forecasts
  2. REAL-TIME — Triggered by sync events — anomaly detection only

Architecture:
  Analyzers produce raw analysis dicts.
  Generators consume analyses → produce insights, scores, forecasts.
  Engine orchestrates the pipeline and persists results.
"""
import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .analyzers.revenue import RevenueAnalyzer
from .analyzers.products import ProductAnalyzer
from .analyzers.patterns import PatternAnalyzer
from .analyzers.money_left import MoneyLeftCalculator
from .generators.insights import InsightGenerator
from .generators.forecasts import ForecastGenerator
from .generators.reports import ReportGenerator

logger = logging.getLogger("meridian.ai.engine")


@dataclass
class AnalysisContext:
    """
    All data needed for a single merchant analysis.
    
    Populated from the database before analysis begins.
    Passed to all analyzers for processing.
    """
    org_id: str
    location_id: str | None = None
    
    # Raw data from DB/sync
    daily_revenue: list[dict] = field(default_factory=list)
    hourly_revenue: list[dict] = field(default_factory=list)
    product_performance: list[dict] = field(default_factory=list)
    transactions: list[dict] = field(default_factory=list)
    inventory: list[dict] = field(default_factory=list)
    
    # Vision data from camera pipeline (ADR-011)
    vision_traffic: list[dict] = field(default_factory=list)
    vision_visits: list[dict] = field(default_factory=list)
    vision_visitors: list[dict] = field(default_factory=list)

    # Merchant metadata
    business_vertical: str = "other"
    timezone: str = "America/Los_Angeles"
    
    # Analysis period
    analysis_days: int = 30

    # Populated by run_agent_swarm after tier 1-4 agents complete
    agent_outputs: dict = field(default_factory=dict)

    # Generated at runtime
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class AnalysisResult:
    """Complete result of AI analysis for a merchant."""
    org_id: str
    
    # Raw analyses
    revenue_analysis: dict = field(default_factory=dict)
    product_analysis: dict = field(default_factory=dict)
    pattern_analysis: dict = field(default_factory=dict)
    money_left_score: dict = field(default_factory=dict)

    # Agent swarm outputs (27 agents: 22 POS + 5 vision)
    agent_outputs: dict = field(default_factory=dict)

    # Alerts fired
    alerts: list[dict] = field(default_factory=list)

    # Generated outputs
    insights: list[dict] = field(default_factory=list)
    forecasts: list[dict] = field(default_factory=list)
    weekly_report: dict | None = None

    # Metadata
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def summary(self) -> dict:
        return {
            "org_id": self.org_id,
            "insights_generated": len(self.insights),
            "forecasts_generated": len(self.forecasts),
            "alerts_fired": len(self.alerts),
            "agents_completed": sum(
                1 for v in self.agent_outputs.values()
                if isinstance(v, dict) and v.get("status") == "complete"
            ),
            "has_weekly_report": self.weekly_report is not None,
            "money_left_total_cents": self.money_left_score.get(
                "total_score_cents", 0
            ),
            "errors": len(self.errors),
            "duration_seconds": round(self.duration_seconds, 2),
        }


class MeridianAI:
    """
    Main AI engine. Runs the full analysis pipeline.
    
    Usage:
        # With database
        ai = MeridianAI(db=supabase_client)
        result = await ai.analyze_merchant(org_id)
        
        # With raw data (for testing)
        ai = MeridianAI()
        ctx = AnalysisContext(
            org_id="test",
            daily_revenue=[...],
            product_performance=[...],
        )
        result = await ai.analyze(ctx)
    """

    MODEL_VERSION = "meridian-ai-v1.0"

    def __init__(self, db=None):
        self.db = db
        
        # Initialize analyzers
        self.revenue_analyzer = RevenueAnalyzer()
        self.product_analyzer = ProductAnalyzer()
        self.pattern_analyzer = PatternAnalyzer()
        self.money_left_calc = MoneyLeftCalculator()
        
        # Initialize generators
        self.insight_gen = InsightGenerator()
        self.forecast_gen = ForecastGenerator()
        self.report_gen = ReportGenerator()

    async def analyze_merchant(
        self,
        org_id: str,
        days: int = 30,
        include_forecasts: bool = True,
        include_report: bool = False,
    ) -> AnalysisResult:
        """
        Run full analysis pipeline for a merchant.
        
        Loads data from DB, runs all analyzers, generates insights.
        """
        if not self.db:
            raise ValueError("Database client required for analyze_merchant()")

        # Load data
        ctx = await self._load_context(org_id, days)
        
        # Run analysis
        result = await self.analyze(
            ctx,
            include_forecasts=include_forecasts,
            include_report=include_report,
        )
        
        # Persist results
        await self._persist_results(result)
        
        return result

    async def analyze(
        self,
        ctx: AnalysisContext,
        include_forecasts: bool = True,
        include_report: bool = False,
    ) -> AnalysisResult:
        """
        Run analysis pipeline on pre-loaded data.
        
        This is the core method — all analyzers run here.
        Can be used without a database for testing.
        """
        start = datetime.now(timezone.utc)
        result = AnalysisResult(org_id=ctx.org_id)

        logger.info(
            f"Starting AI analysis for org={ctx.org_id} "
            f"({ctx.analysis_days} days, {len(ctx.daily_revenue)} daily rows, "
            f"{len(ctx.product_performance)} products)"
        )

        # ── Phase 1: Run Analyzers (parallel) ─────────────────
        try:
            result.revenue_analysis = self.revenue_analyzer.analyze(ctx)
        except Exception as e:
            logger.error(f"Revenue analysis failed: {e}", exc_info=True)
            result.errors.append(f"revenue: {str(e)}")

        try:
            result.product_analysis = self.product_analyzer.analyze(ctx)
        except Exception as e:
            logger.error(f"Product analysis failed: {e}", exc_info=True)
            result.errors.append(f"products: {str(e)}")

        try:
            result.pattern_analysis = self.pattern_analyzer.analyze(ctx)
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}", exc_info=True)
            result.errors.append(f"patterns: {str(e)}")

        # ── Phase 2: Money Left on Table Score ────────────────
        try:
            result.money_left_score = self.money_left_calc.calculate(
                ctx=ctx,
                revenue=result.revenue_analysis,
                products=result.product_analysis,
                patterns=result.pattern_analysis,
            )
        except Exception as e:
            logger.error(f"Money Left calculation failed: {e}", exc_info=True)
            result.errors.append(f"money_left: {str(e)}")

        # ── Phase 2b: Industry-Specific Overlay ──────────────
        try:
            from .industry_templates import get_industry_analyzer
            industry = get_industry_analyzer(ctx.business_vertical, ctx.org_id)
            result.revenue_analysis["industry_overlay"] = industry.analyze_revenue(result.revenue_analysis)
            result.product_analysis["industry_overlay"] = industry.analyze_products(result.product_analysis)
            result.pattern_analysis["industry_overlay"] = industry.analyze_patterns(result.pattern_analysis)
            result.money_left_score["industry_overlay"] = industry.calculate_money_left(result.money_left_score)
            result.money_left_score["industry_benchmarks"] = industry.get_benchmarks()
        except Exception as e:
            logger.error(f"Industry template analysis failed: {e}", exc_info=True)
            result.errors.append(f"industry_template: {str(e)}")

        # ── Phase 3: Generate Insights ────────────────────────
        try:
            result.insights = self.insight_gen.generate(
                ctx=ctx,
                revenue=result.revenue_analysis,
                products=result.product_analysis,
                patterns=result.pattern_analysis,
                money_left=result.money_left_score,
            )
        except Exception as e:
            logger.error(f"Insight generation failed: {e}", exc_info=True)
            result.errors.append(f"insights: {str(e)}")

        # ── Phase 3b: LLM Enhancement (optional) ────────────
        if os.environ.get("ENABLE_LLM_INSIGHTS", "").lower() in ("1", "true"):
            try:
                from .llm_layer import enhance_insights
                result.insights = await enhance_insights(
                    raw_insights=result.insights,
                    business_context={
                        "org_id": ctx.org_id,
                        "business_vertical": ctx.business_vertical,
                        "analysis_days": ctx.analysis_days,
                    },
                )
            except Exception as e:
                logger.error(f"LLM enhancement failed: {e}", exc_info=True)
                result.errors.append(f"llm_enhancement: {str(e)}")

        # ── Phase 4: Forecasts (optional) ─────────────────────
        if include_forecasts:
            try:
                result.forecasts = self.forecast_gen.generate(ctx)
            except Exception as e:
                logger.error(f"Forecast generation failed: {e}", exc_info=True)
                result.errors.append(f"forecasts: {str(e)}")

        # ── Phase 5: Weekly Report (optional) ─────────────────
        if include_report:
            try:
                result.weekly_report = self.report_gen.generate(
                    ctx=ctx,
                    revenue=result.revenue_analysis,
                    products=result.product_analysis,
                    patterns=result.pattern_analysis,
                    money_left=result.money_left_score,
                    insights=result.insights,
                    forecasts=result.forecasts,
                )
            except Exception as e:
                logger.error(f"Report generation failed: {e}", exc_info=True)
                result.errors.append(f"report: {str(e)}")

        # ── Phase 5b: Agent Swarm (27 agents: 22 POS + 5 vision) ──
        try:
            result.agent_outputs = await run_agent_swarm(ctx)
            ctx.agent_outputs = result.agent_outputs

            for agent_name, output in result.agent_outputs.items():
                if isinstance(output, dict) and output.get("status") == "complete":
                    for insight in output.get("insights", []):
                        insight.setdefault("source_agent", agent_name)
                        result.insights.append(insight)
        except Exception as e:
            logger.error(f"Agent swarm failed: {e}", exc_info=True)
            result.errors.append(f"agent_swarm: {str(e)}")

        # ── Phase 5c: Autonomous Swarm Training ──────────────
        if result.agent_outputs:
            try:
                from .swarm_trainer import get_swarm_trainer
                trainer = get_swarm_trainer(db=self.db)
                training_result = await trainer.run_training_cycle(
                    result.agent_outputs, ctx.org_id
                )
                logger.info(f"Swarm training: {training_result}")
            except Exception as e:
                logger.error(f"Swarm training failed: {e}", exc_info=True)
                result.errors.append(f"swarm_training: {str(e)}")

        # ── Phase 6: Alert Evaluation ────────────────────────
        try:
            from .alerts import ALL_ALERTS
            for alert_cls in ALL_ALERTS:
                try:
                    alert = alert_cls(ctx, agent_outputs=result.agent_outputs)
                    fired = await alert.evaluate()
                    result.alerts.extend(fired)
                except Exception as e:
                    logger.error(f"Alert {alert_cls.__name__} failed: {e}")
                    result.errors.append(f"alert_{alert_cls.__name__}: {str(e)}")

            if result.alerts:
                logger.info(f"Fired {len(result.alerts)} alerts for {ctx.org_id}")
        except Exception as e:
            logger.error(f"Alert engine failed: {e}", exc_info=True)
            result.errors.append(f"alerts: {str(e)}")

        result.generated_at = datetime.now(timezone.utc)
        result.duration_seconds = (
            result.generated_at - start
        ).total_seconds()

        logger.info(f"AI analysis complete: {result.summary}")
        return result

    # ─── Private Methods ──────────────────────────────────────

    async def _load_context(self, org_id: str, days: int) -> AnalysisContext:
        """Load all data from DB for analysis."""
        ctx = AnalysisContext(org_id=org_id, analysis_days=days)
        
        # Load in parallel
        daily, hourly, products, transactions, inventory = await asyncio.gather(
            self.db.get_daily_revenue(org_id, days),
            self.db.get_hourly_revenue(org_id, days),
            self.db.get_product_performance(org_id, days),
            self.db.get_transaction_details(org_id, days),
            self.db.get_inventory_current(org_id),
        )

        ctx.daily_revenue = [dict(r) for r in daily]
        ctx.hourly_revenue = [dict(r) for r in hourly]
        ctx.product_performance = [dict(r) for r in products]
        ctx.transactions = [dict(r) for r in transactions]
        ctx.inventory = [dict(r) for r in inventory]

        logger.info(
            f"Loaded context for {org_id}: "
            f"{len(ctx.daily_revenue)} daily, "
            f"{len(ctx.hourly_revenue)} hourly, "
            f"{len(ctx.product_performance)} products, "
            f"{len(ctx.transactions)} transactions"
        )
        return ctx

    async def _persist_results(self, result: AnalysisResult):
        """Save analysis results to database."""
        if not self.db:
            return

        # Save insights
        for insight in result.insights:
            try:
                await self.db.save_insight(insight)
            except Exception as e:
                logger.error(f"Failed to save insight: {e}")

        # Save Money Left score
        if result.money_left_score:
            try:
                await self.db.save_money_left_score(result.money_left_score)
            except Exception as e:
                logger.error(f"Failed to save money_left_score: {e}")

        # Save forecasts
        if result.forecasts:
            try:
                await self.db.save_forecasts(result.forecasts)
            except Exception as e:
                logger.error(f"Failed to save forecasts: {e}")

        # Save weekly report
        if result.weekly_report:
            try:
                await self.db.save_weekly_report(result.weekly_report)
            except Exception as e:
                logger.error(f"Failed to save weekly report: {e}")

        # Save alerts
        if result.alerts:
            try:
                if hasattr(self.db, "save_alerts"):
                    await self.db.save_alerts(result.org_id, result.alerts)
            except Exception as e:
                logger.error(f"Failed to save alerts: {e}")

        # Save agent outputs snapshot
        if result.agent_outputs:
            try:
                if hasattr(self.db, "save_agent_outputs"):
                    await self.db.save_agent_outputs(result.org_id, result.agent_outputs)
            except Exception as e:
                logger.error(f"Failed to save agent outputs: {e}")

        logger.info(
            f"Persisted results for {result.org_id}: "
            f"{len(result.insights)} insights, "
            f"{len(result.forecasts)} forecasts, "
            f"{len(result.alerts)} alerts"
        )


async def run_agent_swarm(ctx: AnalysisContext) -> dict:
    """Run all analysis agents in tiered parallel execution.

    Phase 1: Tiers 1-4 run in parallel (foundation agents).
    Phase 2: Tier 5 strategic agents run after, consuming tier 1-4 outputs.
    """
    from .agents.revenue_trend import RevenueTrendAgent
    from .agents.cash_flow import CashFlowAgent
    from .agents.pricing_power import PricingPowerAgent
    from .agents.discount_analyzer import DiscountAnalyzerAgent
    from .agents.product_velocity import ProductVelocityAgent
    from .agents.basket_analysis import BasketAnalysisAgent
    from .agents.category_mix import CategoryMixAgent
    from .agents.inventory_intel import InventoryIntelAgent
    from .agents.peak_hours import PeakHoursAgent
    from .agents.seasonality import SeasonalityAgent
    from .agents.day_of_week import DayOfWeekAgent
    from .agents.employee_perf import EmployeePerformanceAgent
    from .agents.payment_optimizer import PaymentOptimizerAgent
    from .agents.waste_shrinkage import WasteShrinkageAgent
    from .agents.staffing import StaffingAgent
    from .agents.benchmark import BenchmarkAgent
    from .agents.money_left import MoneyLeftAgent
    from .agents.forecaster import ForecasterAgent
    from .agents.customer_ltv import CustomerLTVAgent
    from .agents.promo_roi import PromoROIAgent
    from .agents.cashflow_forecast import CashFlowForecastAgent
    from .agents.growth_score import GrowthScoreAgent
    from .agents.foot_traffic import FootTrafficAgent
    from .agents.dwell_time import DwellTimeAgent
    from .agents.customer_recognizer import CustomerRecognizerAgent
    from .agents.demographic_profiler import DemographicProfilerAgent
    from .agents.queue_monitor import QueueMonitorAgent

    tier_1_4_agents = [
        RevenueTrendAgent(ctx),
        CashFlowAgent(ctx),
        PricingPowerAgent(ctx),
        DiscountAnalyzerAgent(ctx),
        ProductVelocityAgent(ctx),
        BasketAnalysisAgent(ctx),
        CategoryMixAgent(ctx),
        InventoryIntelAgent(ctx),
        PeakHoursAgent(ctx),
        SeasonalityAgent(ctx),
        DayOfWeekAgent(ctx),
        EmployeePerformanceAgent(ctx),
        PaymentOptimizerAgent(ctx),
        WasteShrinkageAgent(ctx),
        StaffingAgent(ctx),
        FootTrafficAgent(ctx),
        QueueMonitorAgent(ctx),
        CustomerRecognizerAgent(ctx),
        DwellTimeAgent(ctx),
        DemographicProfilerAgent(ctx),
    ]

    use_reasoning = os.environ.get("MERIDIAN_REASONING", "1") == "1"
    if use_reasoning:
        results = await asyncio.gather(
            *[agent.analyze_with_reasoning() for agent in tier_1_4_agents],
            return_exceptions=True,
        )
    else:
        results = await asyncio.gather(
            *[agent.analyze() for agent in tier_1_4_agents],
            return_exceptions=True,
        )

    agent_outputs: dict[str, Any] = {}
    for agent, result in zip(tier_1_4_agents, results):
        if isinstance(result, Exception):
            logger.error(f"Agent {agent.name} failed: {result}")
            agent_outputs[agent.name] = {"status": "error", "error": str(result)}
        else:
            agent_outputs[agent.name] = result

    # Phase 2: Run tier 5 strategic agents (need tier 1-4 outputs)
    ctx.agent_outputs = agent_outputs
    strategic_agents = [
        BenchmarkAgent(ctx),
        MoneyLeftAgent(ctx),
        ForecasterAgent(ctx),
        CustomerLTVAgent(ctx),
        PromoROIAgent(ctx),
        CashFlowForecastAgent(ctx),
        GrowthScoreAgent(ctx),
    ]

    if use_reasoning:
        strategic_results = await asyncio.gather(
            *[agent.analyze_with_reasoning() for agent in strategic_agents],
            return_exceptions=True,
        )
    else:
        strategic_results = await asyncio.gather(
            *[agent.analyze() for agent in strategic_agents],
            return_exceptions=True,
        )

    for agent, result in zip(strategic_agents, strategic_results):
        if isinstance(result, Exception):
            logger.error(f"Strategic agent {agent.name} failed: {result}")
            agent_outputs[agent.name] = {"status": "error", "error": str(result)}
        else:
            agent_outputs[agent.name] = result

    succeeded = sum(
        1 for v in agent_outputs.values()
        if isinstance(v, dict) and v.get("status") == "complete"
    )
    logger.info(
        f"Agent swarm complete: {len(agent_outputs)} agents, "
        f"{succeeded} succeeded"
    )
    return agent_outputs
