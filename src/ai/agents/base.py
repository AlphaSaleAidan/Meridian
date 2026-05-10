"""
Base Agent — Foundation for all Meridian AI analysis agents.

Every agent inherits from BaseAgent and implements analyze().
Agents are organized in tiers (1-5) that determine execution order:
  Tiers 1-4 run in parallel, Tier 5 runs after (needs all outputs).

3-Phase Data Pattern:
  Phase 1 — Data Discovery: get_data_availability() checks what's populated
  Phase 2 — Formula Selection: FULL / PARTIAL / MINIMAL path
  Phase 3 — Dynamic Calculation: real values, derived estimates, or LLM fallback

5-Phase Karpathy Reasoning (wraps every analyze() call):
  THINK → HYPOTHESIZE → EXPERIMENT → SYNTHESIZE → REFLECT
  Provides auditable reasoning chains, null hypothesis testing, and
  confidence-calibrated outputs. Chain stored under result["_reasoning"].
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..agent_logger import get_agent_logger

logger = logging.getLogger("meridian.ai.agents")


@dataclass
class DataAvailability:
    has_transactions: bool = False
    has_items: bool = False
    has_products: bool = False
    has_inventory: bool = False
    has_employees: bool = False
    has_categories: bool = False
    transaction_count: int = 0
    item_count: int = 0
    date_range_days: int = 0
    quality: str = "minimal"
    quality_score: float = 0.0

    @property
    def is_full(self) -> bool:
        return self.quality == "full"

    @property
    def is_partial(self) -> bool:
        return self.quality == "partial"

    @property
    def is_minimal(self) -> bool:
        return self.quality == "minimal"


class BaseAgent(ABC):

    name: str = "base"
    description: str = ""
    tier: int = 1
    domain: str = ""

    def __init__(self, ctx):
        self.ctx = ctx
        self._data_avail: DataAvailability | None = None
        self._chain = None
        self._json_logger = get_agent_logger(self.__class__.__name__)

    @abstractmethod
    async def analyze(self) -> dict:
        ...

    async def analyze_with_reasoning(self) -> dict:
        """Run analyze() wrapped in a Karpathy 5-phase reasoning chain.

        The chain runs BEFORE analyze() to establish context, then the
        analysis result is enriched with reasoning metadata. Fully
        backward-compatible — agents that call analyze() directly are unaffected.
        """
        from ..reasoning import KarpathyReasoning
        reasoning = KarpathyReasoning()
        ctx_dict = self._build_reasoning_context()
        domain = self.domain or self.name
        self._chain = await reasoning.reason(self.name, domain, ctx_dict)
        result = await self.analyze()
        result["_reasoning"] = self._chain.to_dict()
        if self._chain.confidence_level != "UNKNOWN":
            result["reasoning_confidence"] = self._chain.confidence
            result["reasoning_verdict"] = self._chain.verdict
        return result

    def _build_reasoning_context(self) -> dict:
        """Extract data from agent context for the reasoning engine."""
        ctx = self.ctx
        return {
            "transactions": getattr(ctx, "transactions", []) or [],
            "daily_revenue": getattr(ctx, "daily_revenue", []) or [],
            "product_performance": getattr(ctx, "product_performance", []) or [],
            "products": getattr(ctx, "products", []) or [],
            "inventory": getattr(ctx, "inventory", []) or [],
            "employees": getattr(ctx, "employees", []) or [],
            "hourly_revenue": getattr(ctx, "hourly_revenue", []) or [],
            "business_vertical": getattr(ctx, "business_vertical", "other"),
        }

    # ─── ML Engine Methods (lazy-loaded, graceful fallback) ──

    def forecast(self, series: list[dict], periods: int = 30) -> list[dict]:
        """Forecast using statsforecast (preferred), Prophet, or manual fallback."""
        if len(series) >= 7:
            # --- Tier 1: statsforecast AutoARIMA (fast, no cmdstan dependency) ---
            try:
                import pandas as pd
                from statsforecast import StatsForecast
                from statsforecast.models import AutoARIMA

                df = pd.DataFrame(series)
                if "date" in df.columns:
                    df = df.rename(columns={"date": "ds", "revenue_cents": "y"})
                elif "ds" not in df.columns:
                    df.columns = ["ds", "y"] + list(df.columns[2:])

                df["ds"] = pd.to_datetime(df["ds"])
                df["unique_id"] = "series_1"
                df = df[["unique_id", "ds", "y"]].sort_values("ds").reset_index(drop=True)

                season_length = 7  # weekly seasonality
                sf = StatsForecast(
                    models=[AutoARIMA(season_length=season_length)],
                    freq="D",
                    n_jobs=1,
                )
                sf.fit(df)
                fc = sf.predict(h=periods, level=[90])
                return [
                    {
                        "date": row["ds"].strftime("%Y-%m-%d") if hasattr(row["ds"], "strftime") else str(row["ds"]),
                        "predicted": round(row["AutoARIMA"]),
                        "lower": round(row.get("AutoARIMA-lo-90", row["AutoARIMA"] * 0.85)),
                        "upper": round(row.get("AutoARIMA-hi-90", row["AutoARIMA"] * 1.15)),
                    }
                    for _, row in fc.reset_index().iterrows()
                ]
            except ImportError:
                logger.debug("statsforecast not installed — trying Prophet")
            except Exception as e:
                logger.warning(f"statsforecast forecast failed: {e} — trying Prophet")

        if len(series) >= 30:
            # --- Tier 2: Prophet (requires cmdstan, heavier) ---
            try:
                import pandas as pd
                from prophet import Prophet

                df = pd.DataFrame(series)
                if "date" in df.columns:
                    df = df.rename(columns={"date": "ds", "revenue_cents": "y"})
                elif "ds" not in df.columns:
                    df.columns = ["ds", "y"] + list(df.columns[2:])

                m = Prophet(
                    yearly_seasonality=True,
                    weekly_seasonality=True,
                    daily_seasonality=False,
                )
                m.fit(df[["ds", "y"]])
                future = m.make_future_dataframe(periods=periods)
                fc = m.predict(future)
                return [
                    {
                        "date": row["ds"].strftime("%Y-%m-%d"),
                        "predicted": round(row["yhat"]),
                        "lower": round(row["yhat_lower"]),
                        "upper": round(row["yhat_upper"]),
                    }
                    for _, row in fc.tail(periods).iterrows()
                ]
            except ImportError:
                logger.debug("Prophet not installed — using manual forecast")
            except Exception as e:
                logger.warning(f"Prophet forecast failed: {e}")

        return self._manual_forecast(series, periods)

    def _manual_forecast(self, series: list[dict], periods: int) -> list[dict]:
        """Simple linear extrapolation fallback."""
        values = [s.get("revenue_cents", s.get("y", 0)) for s in series]
        if not values:
            return []
        avg = sum(values) / len(values)
        if len(values) >= 7:
            recent = sum(values[-7:]) / 7
            trend = (recent - avg) / max(avg, 1)
        else:
            trend = 0
        return [
            {"date": f"forecast_day_{i+1}", "predicted": round(avg * (1 + trend * i / periods))}
            for i in range(periods)
        ]

    def detect_anomalies(self, values: list[float], contamination: float = 0.05) -> list[int]:
        """Anomaly detection: PyOD IsolationForest or z-score fallback."""
        if len(values) >= 20:
            try:
                import numpy as np
                from pyod.models.iforest import IForest

                arr = np.array(values).reshape(-1, 1)
                clf = IForest(contamination=contamination, random_state=42)
                clf.fit(arr)
                return clf.labels_.tolist()
            except ImportError:
                logger.debug("PyOD not installed — using z-score fallback")
            except Exception as e:
                logger.warning(f"PyOD anomaly detection failed: {e}")

        if not values:
            return []
        avg = sum(values) / len(values)
        std = (sum((v - avg) ** 2 for v in values) / max(len(values) - 1, 1)) ** 0.5
        if std == 0:
            return [0] * len(values)
        return [1 if abs(v - avg) / std > 2.5 else 0 for v in values]

    def find_associations(
        self, baskets: list[list[str]], min_support: float = 0.01, min_lift: float = 1.2
    ) -> list[dict]:
        """Basket analysis: mlxtend Apriori or manual pair counting."""
        if len(baskets) >= 50:
            try:
                import pandas as pd
                from mlxtend.frequent_patterns import apriori, association_rules
                from mlxtend.preprocessing import TransactionEncoder

                te = TransactionEncoder()
                te_arr = te.fit(baskets).transform(baskets)
                df = pd.DataFrame(te_arr, columns=te.columns_)
                freq = apriori(df, min_support=min_support, use_colnames=True)
                if freq.empty:
                    return []
                rules = association_rules(freq, metric="lift", min_threshold=min_lift)
                return [
                    {
                        "antecedents": list(row["antecedents"]),
                        "consequents": list(row["consequents"]),
                        "support": round(row["support"], 4),
                        "confidence": round(row["confidence"], 4),
                        "lift": round(row["lift"], 3),
                    }
                    for _, row in rules.head(20).iterrows()
                ]
            except ImportError:
                logger.debug("mlxtend not installed — using manual pair counting")
            except Exception as e:
                logger.warning(f"mlxtend basket analysis failed: {e}")

        pairs: dict[tuple, int] = {}
        for basket in baskets:
            items = sorted(set(basket))
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    pair = (items[i], items[j])
                    pairs[pair] = pairs.get(pair, 0) + 1
        total = max(len(baskets), 1)
        return [
            {"antecedents": [a], "consequents": [b], "support": round(c / total, 4), "frequency": c}
            for (a, b), c in sorted(pairs.items(), key=lambda x: x[1], reverse=True)[:20]
        ]

    def get_data_availability(self) -> DataAvailability:
        if self._data_avail is not None:
            return self._data_avail

        ctx = self.ctx
        txns = getattr(ctx, "transactions", []) or []
        products = getattr(ctx, "product_performance", []) or []
        inventory = getattr(ctx, "inventory", []) or []
        daily = getattr(ctx, "daily_revenue", []) or []
        hourly = getattr(ctx, "hourly_revenue", []) or []

        has_items = any(t.get("items") or t.get("line_items") for t in txns[:50])
        has_employees = any(t.get("employee_name") or t.get("employee_id") for t in txns[:50])
        has_categories = any(p.get("category") for p in products[:50])

        dates = sorted(d.get("date", "") for d in daily if d.get("date"))
        if len(dates) >= 2:
            try:
                d0 = datetime.fromisoformat(dates[0])
                d1 = datetime.fromisoformat(dates[-1])
                date_range_days = max((d1 - d0).days + 1, len(daily))
            except (ValueError, TypeError):
                date_range_days = len(daily)
        else:
            date_range_days = len(daily)

        has_transactions = len(txns) > 0 or len(daily) > 0
        has_products = len(products) > 0
        has_inventory = len(inventory) > 0

        if has_transactions and has_items and has_products and has_inventory:
            quality = "full"
            quality_score = 1.0
        elif has_transactions and (has_items or has_products):
            quality = "partial"
            quality_score = 0.6
        elif has_transactions:
            quality = "partial"
            quality_score = 0.5
        else:
            quality = "minimal"
            quality_score = 0.2

        if date_range_days >= 30:
            quality_score = min(1.0, quality_score + 0.1)
        elif date_range_days < 7:
            quality_score = max(0.1, quality_score - 0.2)

        self._data_avail = DataAvailability(
            has_transactions=has_transactions,
            has_items=has_items,
            has_products=has_products,
            has_inventory=has_inventory,
            has_employees=has_employees,
            has_categories=has_categories,
            transaction_count=len(txns),
            item_count=sum(len(t.get("items", []) or t.get("line_items", [])) for t in txns[:200]),
            date_range_days=date_range_days,
            quality=quality,
            quality_score=round(quality_score, 2),
        )
        return self._data_avail

    def get_benchmark(self, metric: str) -> Any:
        from ..economics.benchmarks import IndustryBenchmarks
        bench = IndustryBenchmarks(getattr(self.ctx, "business_vertical", "other"))
        return bench.get(metric)

    def get_benchmark_range(self, metric: str):
        from ..economics.benchmarks import IndustryBenchmarks
        bench = IndustryBenchmarks(getattr(self.ctx, "business_vertical", "other"))
        return bench.get_range(metric)

    def _select_path(self) -> tuple[str, float]:
        """Standard 3-path selection based on data availability.

        Override in subclasses that need custom path logic (e.g. tier-5
        agents that inspect upstream outputs).
        """
        avail = self.get_data_availability()
        if avail.is_full:
            return "full", avail.quality_score
        elif avail.is_partial:
            return "partial", avail.quality_score
        else:
            return "minimal", min(0.4, avail.quality_score)

    def _benchmark_fallback(self, metric_key: str, summary: str, extra_data: dict | None = None) -> dict:
        """Build a minimal-path result using industry benchmarks."""
        bench_range = self.get_benchmark_range(metric_key)
        insight: dict = {"type": "benchmark_estimate", "detail": summary, "estimated": True}
        if bench_range:
            insight["benchmark"] = {"low": bench_range.low, "mid": bench_range.mid, "high": bench_range.high, "source": bench_range.source}
        data = {"source": "benchmark"}
        if extra_data:
            data.update(extra_data)
        return self._result(
            summary=summary,
            score=50,
            insights=[insight],
            recommendations=[{"action": "Connect POS line-item data for precise analysis", "impact": "Improves accuracy from estimated to actual values", "effort": "low"}],
            data=data,
            confidence=min(0.4, self.get_data_availability().quality_score),
            calculation_path="minimal",
        )

    def _insufficient_data(self, reason: str) -> dict:
        return {
            "agent_name": self.name,
            "status": "insufficient_data",
            "minimum_required": reason,
            "summary": f"Not enough data for {self.name} analysis",
            "score": 0,
            "insights": [],
            "recommendations": [],
            "data": {},
            "data_quality": 0.0,
            "calculation_path": "none",
        }

    def _result(
        self,
        summary: str,
        score: float,
        insights: list[dict],
        recommendations: list[dict],
        data: dict,
        confidence: float | None = None,
        calculation_path: str = "full",
    ) -> dict:
        avail = self.get_data_availability()
        dq = confidence if confidence is not None else avail.quality_score
        for insight in insights:
            if "data_quality" not in insight:
                insight["data_quality"] = dq
            if "estimated" not in insight:
                insight["estimated"] = calculation_path != "full"
        result = {
            "agent_name": self.name,
            "status": "complete",
            "summary": summary,
            "score": round(max(0, min(100, score))),
            "insights": insights,
            "recommendations": recommendations,
            "data": data,
            "data_quality": round(dq, 2),
            "calculation_path": calculation_path,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if self._chain is not None:
            result["_reasoning"] = self._chain.to_dict()
            result["reasoning_confidence"] = self._chain.confidence
            result["reasoning_verdict"] = self._chain.verdict
        return result
