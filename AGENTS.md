# Meridian Agent Swarm

## Agent Registry

Meridian runs a 20-agent swarm for POS analytics and vision intelligence.
Each agent specializes in a specific analytical domain.

### POS Analytics Agents
| Agent | File | Domain |
|-------|------|--------|
| Transaction Analyst | `src/ai/agents/revenue_trend.py` | Transaction patterns, anomalies, fraud |
| Revenue Forecaster | `src/ai/agents/forecaster.py` | 7/30/90-day revenue forecasts |
| Product Intelligence | `src/ai/agents/product_velocity.py` | SKU ranking, dead stock, bundles |
| Customer Segmentor | `src/ai/agents/customer_ltv.py` | RFM segmentation, LTV prediction |
| Peak Hours Analyst | `src/ai/agents/peak_hours.py` | Hourly traffic patterns, staffing |
| Inventory Intel | `src/ai/agents/inventory_intel.py` | Stock levels, reorder alerts |
| Basket Analysis | `src/ai/agents/basket_analysis.py` | Cross-sell, attachment rates |
| Cash Flow | `src/ai/agents/cash_flow.py` | Daily cash position, projection |
| Employee Performance | `src/ai/agents/employee_perf.py` | Staff productivity, tip analysis |
| Staffing Optimizer | `src/ai/agents/staffing.py` | Shift scheduling optimization |
| Discount Analyzer | `src/ai/agents/discount_analyzer.py` | Promo ROI, discount impact |
| Category Mix | `src/ai/agents/category_mix.py` | Menu category optimization |
| Pricing Power | `src/ai/agents/pricing_power.py` | Price elasticity, margin analysis |
| Growth Score | `src/ai/agents/growth_score.py` | Business health scoring |
| Seasonality | `src/ai/agents/seasonality.py` | Seasonal pattern detection |
| Day of Week | `src/ai/agents/day_of_week.py` | Day-level performance patterns |
| Waste & Shrinkage | `src/ai/agents/waste_shrinkage.py` | Waste tracking, loss prevention |
| Money Left | `src/ai/agents/money_left.py` | Missed revenue opportunities |
| Payment Optimizer | `src/ai/agents/payment_optimizer.py` | Payment method optimization |
| Promo ROI | `src/ai/agents/promo_roi.py` | Promotion effectiveness |

### Vision Agents
| Agent | File | Domain |
|-------|------|--------|
| Foot Traffic | `src/ai/agents/foot_traffic.py` | Customer count from camera |
| Dwell Time | `src/ai/agents/dwell_time.py` | Time spent in zones |
| Queue Monitor | `src/ai/agents/queue_monitor.py` | Line length, wait times |
| Demographic Profiler | `src/ai/agents/demographic_profiler.py` | Customer demographics |
| Customer Recognizer | `src/ai/agents/customer_recognizer.py` | Repeat customer ID |

### Phone Order Agent
| Agent | File | Domain |
|-------|------|--------|
| Phone Agent | `services/phone_agent/` | AI phone order taking via LiveKit |

## Self-Evolution Protocol (GEP)

Meridian uses EvoMap Evolver for structured agent self-improvement.

### How to run an evolution cycle

```bash
# From ~/Meridian:
cd services/evolver

# Review mode (safe — shows prompt without applying)
./meridian_evolve.sh

# Harden mode (fix stability issues)
./meridian_evolve.sh harden

# Emergency repair (recurring failures)
./meridian_evolve.sh repair-only

# Continuous loop (autonomous improvement)
./meridian_evolve.sh balanced loop
```

### Evolution audit log
Every evolution event is recorded at:
`services/evolver/assets/gep/events.jsonl`

### Gene library
All Meridian-specific improvement patterns live at:
`services/evolver/assets/gep/genes.json`

### When to run Evolver
- After any agent produces 5+ consecutive errors in `logs/agents/`
- After a new feature is added to the agent swarm
- Weekly as a scheduled stability check
- Immediately after a production incident

### What Evolver does NOT do
- It does not automatically edit code without review mode
- It does not modify CLAUDE.md, ruflo.config.yaml, or pos_connector.py
- It does not touch the demo, sales portals, or merchant data

## Agent Log Pipeline

All agents write structured JSON-lines logs to `logs/agents/{AgentName}.log`.

Log entry format:
```json
{
  "timestamp": "2026-05-08T10:30:00Z",
  "agent": "RevenueAnalyst",
  "level": "error",
  "event": "analyze",
  "message": "Failed to fetch daily revenue",
  "error": "connection pool exhausted",
  "merchant_id": "uuid",
  "context": {}
}
```

Evolver scans these logs to extract failure signals and trigger
appropriate Gene-based repairs.

## Nightly Execution Order

| Time | Service | Purpose |
|------|---------|---------|
| 2:00 AM | Nightly Pipeline | Data sync, aggregation, insights |
| 3:00 AM | Ruflo | Agent swarm full analysis run |
| 3:30 AM | Evolver (repair-only) | Read Ruflo error logs, generate repairs |
| 4:00 AM | Weekly report | Sunday only: generate + email reports |
