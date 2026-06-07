# Meridian Agent Registry — Phase 0

Date: 2026-06-02
Status: pre-standard inventory. Pass/fail vs the Agent Modernization Standard (`MERIDIAN_AGENT_STANDARD_AND_REGISTRY.md`) is captured per row.

> Every agent is currently **FAIL** against the standard, for the same five reasons (no declared `tier`, no `memory_scope`, no `output_schema` frontmatter, no eval entry, no registry entry). Those will be remediated in Phase 2 once the masterplan is renegotiated against the real stack (see `swarm_inventory.md`).
>
> This document is the seed for the machine-readable `agents/registry.yaml` that Part 4B of the agent-standard requires.

## Summary

| Bucket | Count | LLM-calling? | Notes |
|--------|-------|--------------|-------|
| Tier 1–5 BaseAgent (POS) | 31 | No (deterministic + ML) | `src/ai/agents/*.py` |
| Cross-reference (camera×POS) | 10 | No | `src/ai/agents/cross_ref/*.py` |
| Predictive | 6 | No | `src/ai/predictive/*.py` |
| Alerts | 6 | No | `src/ai/alerts/*.py` |
| Industry overlays | 16 | No | `src/ai/industry_templates/*.py` |
| Generators (insight/forecast/report/Canada rules) | 4 | **Yes** (via `llm_layer.enhance_insights`) | `src/ai/generators/*.py` |
| Special LLM agents | 2 | **Yes** | `ClineAgent`, `CommercialDirector` |
| Pipecat voice bot (1 logical agent, multi-component) | 1 | **Yes** | `src/voice/*` / `services/postal-pipecat` (verify in Phase 1) |
| **Total** | **76** | **≈ 7** of 76 are LLM agents | |

> Counts differ slightly from the Explore agent's earlier estimate of 73 because the per-folder enumeration found 4 generators and 1 voice agent rather than the previously-collapsed counts. Treat 76 as the working number until the registry YAML is built.

The **prediction rule** in the standard applies to every agent that produces a numeric/probability/ranking output. That covers most tier 1–5 agents, all 6 predictive agents, all 6 alerts, and all 10 cross-ref agents. Most of them already use a real statistical model (statsforecast, mlxtend, sklearn, lifetimes, pyod) — they pass the *spirit* of the prediction rule today. The ones that violate it (numeric output via a hand-rolled formula instead of a learned model) are exactly the Wave 1–3 candidates in `MERIDIAN_ML_MODEL_UPGRADES_PROMPT.md`.

## Per-agent registry

Columns:
- **File** — relative to `/root/Meridian`
- **Category** — `analytics_ml` | `orchestration` | `extraction` | `voice_realtime` | `generation` | `integration`
- **Predicts** — yes if the output is a number/probability/ranking
- **LLM** — yes if the agent calls `llm_layer` directly
- **ML lever** — Wave from `MERIDIAN_ML_MODEL_UPGRADES_PROMPT.md` if applicable
- **Tier (proposed)** — initial T1/T2/T3 assignment for Phase 1

### Tier 1–5 POS agents (`src/ai/agents/*.py`, all extend `BaseAgent`)

| Agent file | Category | Predicts | LLM | ML lever | Tier proposed |
|------------|----------|----------|-----|----------|---------------|
| `action_prioritizer.py` | analytics_ml | yes | no | — | T1 |
| `basket_analysis.py` | analytics_ml | yes | no | Wave 1C (FP-Growth) | T1 |
| `benchmark.py` | analytics_ml | yes | no | — | T1 |
| `cash_flow.py` | analytics_ml | yes | no | — | T1 |
| `cashflow_forecast.py` | analytics_ml | yes | no | Wave 2A (AutoGluon) | T1 |
| `category_mix.py` | analytics_ml | yes | no | — | T1 |
| `customer_ltv.py` | analytics_ml | yes | no | Wave 1B (PyMC-Marketing) | T1 |
| `customer_recognizer.py` | analytics_ml | yes | no | — | T1 |
| `day_of_week.py` | analytics_ml | yes | no | Wave 3 (STL consolidation) | T1 |
| `demographic_profiler.py` | analytics_ml | yes | no | — | T1 |
| `discount_analyzer.py` | analytics_ml | yes | no | Wave 1A (DML) | T1 |
| `dwell_time.py` | analytics_ml | yes | no | — | T1 |
| `employee_perf.py` | analytics_ml | yes | no | — | T1 |
| `feature_engineer.py` | analytics_ml | no | no | — | T1 |
| `foot_traffic.py` | analytics_ml | yes | no | Wave 2A | T1 |
| `forecaster.py` | analytics_ml | yes | no | **Wave 2A** (consolidate on AutoGluon) | T1 |
| `growth_score.py` | analytics_ml | yes | no | — | T1 |
| `inventory_intel.py` | analytics_ml | yes | no | Wave 2A | T1 |
| `location_analyst.py` | analytics_ml | yes | no | — | T1 |
| `loyalty_architect.py` | analytics_ml | yes | no | — | T1 |
| `money_left.py` | analytics_ml | yes | no | — | T1 |
| `payment_optimizer.py` | analytics_ml | yes | no | — | T1 |
| `peak_hours.py` | analytics_ml | yes | no | Wave 3 (STL) | T1 |
| `pricing_power.py` | analytics_ml | yes | no | Wave 1A (DML) | T1 |
| `product_velocity.py` | analytics_ml | yes | no | Wave 2A | T1 |
| `promo_roi.py` | analytics_ml | yes | no | Wave 1A | T1 |
| `queue_monitor.py` | analytics_ml | yes | no | — | T1 |
| `revenue_trend.py` | analytics_ml | yes | no | Wave 2A | T1 |
| `seasonality.py` | analytics_ml | yes | no | Wave 3 (STL/MSTL) | T1 |
| `staffing.py` | analytics_ml | yes | no | — | T1 |
| `waste_shrinkage.py` | analytics_ml | yes | no | — | T1 |

### Cross-reference camera×POS (`src/ai/agents/cross_ref/*.py`)

| Agent file | Category | Predicts | LLM | ML lever | Tier proposed |
|------------|----------|----------|-----|----------|---------------|
| `influence_zone_agent.py` | analytics_ml | yes | no | — | T1 |
| `lost_sale_agent.py` | analytics_ml | yes | no | — | T1 |
| `path_to_purchase_agent.py` | analytics_ml | yes | no | — | T1 |
| `peak_basket_agent.py` | analytics_ml | yes | no | — | T1 |
| `posture_purchase_agent.py` | analytics_ml | yes | no | — | T1 |
| `product_placement_agent.py` | analytics_ml | yes | no | — | T1 |
| `queue_basket_agent.py` | analytics_ml | yes | no | — | T1 |
| `return_customer_agent.py` | analytics_ml | yes | no | — | T1 |
| `staff_effect_agent.py` | analytics_ml | yes | no | — | T1 |
| `zone_conversion_agent.py` | analytics_ml | yes | no | — | T1 |

### Predictive (`src/ai/predictive/*.py`)

| Agent file | Category | Predicts | LLM | ML lever | Tier proposed |
|------------|----------|----------|-----|----------|---------------|
| `churn_warning.py` | analytics_ml | yes | no | **Wave 1D + 2B** (XGB/LGB calibrated + survival) | T1 |
| `demand_forecast.py` | analytics_ml | yes | no | Wave 2A | T1 |
| `dynamic_pricing.py` | analytics_ml | yes | no | Wave 1A (DML) | T1 |
| `goal_tracker.py` | analytics_ml | yes | no | — | T1 |
| `root_cause.py` | analytics_ml | yes | no | — | T1 |
| `scenario_engine.py` | analytics_ml | yes | no | — | T1 |

### Alerts (`src/ai/alerts/*.py`)

| Agent file | Category | Predicts | LLM | ML lever | Tier proposed |
|------------|----------|----------|-----|----------|---------------|
| `employee_shift.py` | analytics_ml | yes | no | — | T1 |
| `margin_erosion.py` | analytics_ml | yes | no | — | T1 |
| `payment_fraud.py` | analytics_ml | yes | no | Keep IsolationForest + add ECOD/COPOD | T1 |
| `revenue_anomaly.py` | analytics_ml | yes | no | Keep STL+MAD; Wave 3 modified z-score | T1 |
| `stockout_predictor.py` | analytics_ml | yes | no | — | T1 |
| `trend_break.py` | analytics_ml | yes | no | Wave 3 (STL consolidation) | T1 |

### Industry overlays (`src/ai/industry_templates/*.py`)

All 16 (`auto_repair`, `bakery`, `bar_nightclub`, `brewery`, `cannabis`, `coffee_shop`, `convenience`, `fitness`, `food_truck`, `grocery`, `pizza`, `restaurant`, `retail`, `salon`, `smoke_shop`, `spa`) are deterministic config/overlay objects — they don't make LLM calls. Category `analytics_ml`, no ML lever, tier proposed `T1`.

### Generators (LLM-calling) (`src/ai/generators/*.py`)

| Agent file | Category | Predicts | LLM | Notes | Tier proposed |
|------------|----------|----------|-----|-------|---------------|
| `insight_generator.py` (verify exact filename) | generation | no | **yes** (via `llm_layer.enhance_insights`) | Strict output schema needed | T2 |
| `forecast_generator.py` | generation | partially (narrative around numbers) | **yes** | Numeric forecast comes from forecaster; LLM only narrates | T2 |
| `report_generator.py` | generation | no | **yes** | Weekly report | T2 |
| `canada_rules.py` / sales rules | generation | no | maybe | Verify in Phase 1 | T1 if rule-only |

> Phase 1 must read `src/ai/generators/` to confirm exact filenames; counted 10 .py files in the dir, of which 4 are the LLM-touching generators.

### Special agents

| Agent | File | Category | Predicts | LLM | Tier proposed |
|-------|------|----------|----------|-----|---------------|
| `ClineAgent` (self-healing IT) | `src/ai/agents/...` (verify) | orchestration | no | **yes** | T3 (heavy reasoning) |
| `CommercialDirector` | `src/ai/commercial_director.py` | generation | no | **yes** | T2 default; T3 for video planning |
| `Pipecat voice bot` (phone-orders) | `src/voice/*` or `services/postal-pipecat` | voice_realtime | no | **yes (latency-critical)** | T1 |

## Standard compliance — current state

Per Part 1 of `MERIDIAN_AGENT_STANDARD_AND_REGISTRY.md`, every agent must satisfy 10 items. Current state across all 76 agents:

| Standard item | Pass count | Fail count |
|---------------|------------|------------|
| Single responsibility | 60 / 76 (generators and special are multi-purpose) | 16 |
| Declared `tier` | 0 | 76 |
| Least-privilege tools | n/a — most agents have no tool access at all | n/a |
| `max_turns` cap | 0 | 76 (LiteLLM `num_retries=2` is the only cap) |
| `memory_scope` | 0 | 76 (all share `ctx`) |
| Structured output | partial — `BaseAgent.run()` returns a dict, but no schema validation | 76 |
| Prediction rule | ~60 agents already use real ML; the rest are hand-rolled formulas | ~16 |
| Eval entry | none | 76 |
| Standard frontmatter | none | 76 |
| Observability | `agent_logger.py` exists but `logs/agents/` is empty — not wired | 76 |

Pass/fail summary: **0 agents currently meet the standard.** This is expected pre-Phase-2.

## Action items for Phase 1 / Phase 2 (post-approval)

1. Confirm the 4 generator filenames in `src/ai/generators/` and add them to this registry.
2. Confirm `ClineAgent` location (likely `src/ai/cline/` or `src/ai/agents/cline.py`).
3. Confirm Pipecat voice bot path under `services/` and whether it's one agent or several (STT, LLM, TTS).
4. Build `agents/registry.yaml` from the rows above.
5. Build `agents/_TEMPLATE.md` and `scripts/validate_agents.py` per Part 4.
