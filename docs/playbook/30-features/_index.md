# Features — Index

Meridian's AI agents grouped by tier. Each agent is auto-generated from its source-of-truth class metadata in `src/ai/agents/`.

## Tier 1 — POS Analytics (transaction-only, no cameras needed)

**Standard plan (CA$343 / $299)** unlocks all of these.

| Agent | What it does | Data tier |
|-------|--------------|-----------|
| [revenue_trend](./pos-analytics/revenue_trend.md) | Daily/weekly/monthly growth rates and trend signals | 1 |
| [cash_flow](./pos-analytics/cash_flow.md) | 14-day cash position forecast and fee analysis | 1 |
| [pricing_power](./pos-analytics/pricing_power.md) | Price elasticity analysis and pricing optimization | 1 |
| [discount_analyzer](./pos-analytics/discount_analyzer.md) | Discount ROI and cannibalization analysis | 1 |
| [foot_traffic](./pos-analytics/foot_traffic.md) | Hourly/daily footfall, entry patterns, conversion vs POS | 1 (cameras boost) |
| [queue_monitor](./pos-analytics/queue_monitor.md) | Real-time queue length, wait time, staffing alerts | 1 (cameras boost) |
| [basket_analysis](./pos-analytics/basket_analysis.md) | Co-purchase pairs and bundle recommendations | 2 |
| [product_velocity](./pos-analytics/product_velocity.md) | Velocity ranking, rising stars, dead stock | 2 |
| [inventory_intel](./pos-analytics/inventory_intel.md) | Days-of-stock, reorder alerts, EOQ model | 2 |
| [category_mix](./pos-analytics/category_mix.md) | Category revenue share and mix optimization | 2 |
| [customer_recognizer](./pos-analytics/customer_recognizer.md) | Repeat-visitor frequency, new vs returning, loyalty without a card | 2 |
| [dwell_time](./pos-analytics/dwell_time.md) | Avg dwell by zone, browse-to-buy funnel | 2 (cameras required) |
| [peak_hours](./pos-analytics/peak_hours.md) | Revenue heatmap, peak-hour optimization | 3 |
| [day_of_week](./pos-analytics/day_of_week.md) | Best/worst days, day-specific patterns | 3 |
| [seasonality](./pos-analytics/seasonality.md) | Seasonal decomposition and calendar effects | 3 |
| [location_analyst](./pos-analytics/location_analyst.md) | Multi-location comparison, best-practice transfer | 3 (Command) |
| [loyalty_architect](./pos-analytics/loyalty_architect.md) | Loyalty program design, redemption rates, retention impact | 3 |
| [demographic_profiler](./pos-analytics/demographic_profiler.md) | Age/gender distribution, daypart demographics | 3 (cameras required) |
| [employee_performance](./pos-analytics/employee_performance.md) | Per-employee revenue, upsell, tip analysis | 4 |
| [staffing](./pos-analytics/staffing.md) | Optimal headcount per hour, labor efficiency | 4 |
| [payment_optimizer](./pos-analytics/payment_optimizer.md) | Payment mix and fee optimization | 4 |
| [waste_shrinkage](./pos-analytics/waste_shrinkage.md) | Shrinkage rate, void patterns, annual loss projection | 4 |
| [forecaster](./pos-analytics/forecaster.md) | 7/30/90-day revenue forecasts with confidence intervals | 5 |
| [growth_score](./pos-analytics/growth_score.md) | Executive growth score 0–100 + monthly action plan | 5 |
| [customer_ltv](./pos-analytics/customer_ltv.md) | Customer lifetime value prediction and churn risk | 5 |
| [cashflow_forecast](./pos-analytics/cashflow_forecast.md) | 30-day cash flow projection with danger zone detection | 5 |
| [promo_roi](./pos-analytics/promo_roi.md) | Promo ROI calculator with diminishing-returns detection | 5 |
| [benchmark](./pos-analytics/benchmark.md) | You-vs-industry scorecard with percentile estimates | 5 |
| [action_prioritizer](./pos-analytics/action_prioritizer.md) | Ranks all agent outputs into Top 3 daily actions | 5 |
| [money_left_on_table](./pos-analytics/money_left_on_table.md) | Headline $ opportunity, roll-up of all agents — **the demo hook** | 5 |

## Vision (camera pipeline)

The vision system is **Premium+ only** ($599 / CA$685 minimum). It's not packaged as discrete "agents" — it's a real-time pipeline running on each connected RTSP stream. See [vision/](./vision/) for the per-module breakdown.

| Module | What it does |
|--------|--------------|
| [rtsp_handler](./vision/rtsp_handler.md) | Connects to the camera's RTSP/RTSPS stream, maintains the frame buffer |
| [detector](./vision/detector.md) | YOLO11n + ByteTrack person detection per frame |
| [people_counter](./vision/people_counter.md) | Counts unique people crossing entry lines |
| [line_counter](./vision/line_counter.md) | Directional crossings (in vs out) over virtual lines |
| [pipeline](./vision/pipeline.md) | Orchestrates the above + writes to Supabase via supabase_writer |

These feed data into the POS Analytics agents that have "cameras boost" or "cameras required" markers above (foot_traffic, queue_monitor, dwell_time, demographic_profiler), and into the Cross-Reference agents below.

## Cross-Reference (POS × Camera fusion)

**Premium+ only.** Requires cameras connected + POS data. These are where the platform earns Premium pricing — nobody else does this fusion at SMB scale.

| Agent | What it does |
|-------|--------------|
| [influence_zone](./cross-reference/influence_zone.md) | Identifies zones that correlate with higher basket size |
| [lost_sale](./cross-reference/lost_sale.md) | Walkaway patterns + estimates recoverable revenue |
| [path_to_purchase](./cross-reference/path_to_purchase.md) | Zone sequences leading to purchase vs walkaway |
| [peak_basket](./cross-reference/peak_basket.md) | Traffic-density-to-basket-size correlation |
| [posture_purchase](./cross-reference/posture_purchase.md) | Body posture/gesture patterns and purchase likelihood |
| [product_placement](./cross-reference/product_placement.md) | Optimizes product positioning by cross-referencing zone traffic with sales |
| [queue_basket](./cross-reference/queue_basket.md) | Queue wait time vs basket size and abandonment |
| [return_customer](./cross-reference/return_customer.md) | Returning vs first-time customer journey and spend |
| [staff_effect](./cross-reference/staff_effect.md) | Staff zone presence vs customer conversion and basket size |
| [zone_conversion](./cross-reference/zone_conversion.md) | Per-zone conversion rates and purchase acceleration |

## Coordination (orchestrators, not user-facing)

These run the swarm. Reps don't pitch these directly, but they're worth knowing about.

| Component | What it does |
|-----------|--------------|
| [cross_reference_orchestrator](./coordination/cross_reference_orchestrator.md) | Real-time fusion of camera + POS events; batch mode for historical |
| [swarm_trainer](./coordination/swarm_trainer.md) | Trains and tunes the agent fleet across customer-base patterns |

## How features map to plans

See [_data-requirements-matrix.md](./_data-requirements-matrix.md) for which features need which data, from which POS systems.

| Plan | Tier-1/2 POS agents | Tier-3/4 POS agents | Tier-5 (headline) | Vision pipeline | Cross-reference |
|------|---------------------|--------------------|-------------------|-----------------|-----------------|
| Standard ($299 / CA$343) | Yes | Yes | Yes | — | — |
| Premium ($599 / CA$685) | Yes | Yes | Yes | Yes | Yes |
| Command ($1,199 / CA$1,370) | Yes | Yes | Yes | Yes | Yes + multi-location + API |

The big upsell from Standard → Premium isn't the POS analytics (Standard has all of them). It's the **vision pipeline + cross-reference fusion**. That's the dwell-time-to-ticket correlation merchants can't get anywhere else.

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ (30 POS analytics agents + cross_ref/ 10 agents) + src/camera/ (5 vision modules) + src/ai/cross_reference_orchestrator.py + src/ai/swarm_trainer.py_

_Note: task spec referenced "20 pos_analytics + 5 vision agents + 13 cross-reference + 2 coordination = 40 features." Actual code: 30 pos_analytics + 5 vision modules + 10 cross-reference + 2 coordination = 47. Documented what's real per anti-goal #3._
