# Insights Not Appearing

The merchant is connected, data is flowing, but they don't see insights — or the insights look wrong.

## Triage

1. How long since they connected?
2. How much data is in (today's transactions + backfill progress)?
3. Which specific insight is missing or wrong?
4. What does the agent say (look for "insufficient data" or "low confidence" markers)?

## "I've been connected 48 hours, nothing on the dashboard"

| Cause | Fix |
|-------|-----|
| Backfill not complete | Live insights need some history; some agents wait for 7–30 days of data. See [backfill-stuck.md](./backfill-stuck.md). |
| Merchant has very low transaction volume | Some agents (basket_analysis, customer_ltv) need 30+ days at meaningful volume |
| Wrong vertical setting | If "vertical" is wrong, industry-benchmark fallback uses wrong reference |
| Dashboard filter set to wrong date range | Reset to "Last 30 days" |

## "Agent shows 'insufficient data' message"

Each agent has a path selector (minimal / partial / full) based on data quality. "Insufficient data" means we don't have enough to even run the minimal path with confidence.

Common per-agent triggers:

| Agent | Needs at minimum |
|-------|------------------|
| customer_ltv | 90+ days of transaction history + customer IDs |
| basket_analysis | 30+ days + multi-item transactions |
| forecaster | 60+ days for tight CIs; 14+ days for rough |
| seasonality | 12+ months ideally; 90 days for partial |
| employee_performance | Employee IDs on transactions + 30+ days |
| inventory_intel | SKU-level data + 30+ days |
| All cross-reference agents | Cameras connected + zones configured + 7+ days of joint POS+camera data |

If a merchant complains about a specific agent showing "insufficient data," check the requirement above. Often the answer is "you'll see this once you have [X] more days of data" — totally fine, set expectation.

## "The Money Left on Table number looks wrong"

`money_left_on_table` aggregates findings from all tier 1–4 agents (see `src/ai/agents/money_left.py`). It uses one of three calculation paths:

- **full** — most tier-1/2/3/4 agents returned complete results
- **partial** — most returned partial
- **minimal** — most returned minimal (low-confidence summary)

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Number is suspiciously low (e.g., CA$200 when you'd expect thousands) | Upstream agents on minimal path | Need more data — usually time |
| Number is huge and feels unrealistic | One upstream agent overestimating | Check individual agent outputs; if one looks off, that's the culprit |
| Number bounces day to day | New data shifting the agent outputs | Expected during first 2 weeks; stabilizes after |

The merchant should see, alongside the number, a "calculation_path" indicator. If they see "minimal," tell them the number will refine as more data accumulates.

## "An agent's recommendation seems crazy"

Some agents give counter-intuitive recommendations. Common ones:

| Recommendation | Why it makes sense |
|----------------|--------------------|
| "Raise prices on item X" (low elasticity item) | Pricing-power agent finds items where volume won't drop with price |
| "Stop a promo that 'works'" | Discount analyzer caught it cannibalizing full-price sales |
| "Kill a popular item" | Menu engineering found it's high revenue but low margin (a "puzzle") |
| "Hire fewer staff at peak" | Staffing agent found over-staffing at certain hours |

If the merchant disagrees, that's a conversation, not a bug. Show them the underlying data the agent used. Usually the merchant has context the agent doesn't (e.g., "that staff member I 'should' fire is my owner's nephew") — that's fine, they can ignore the recommendation.

## "Insights stopped appearing after a few days"

| Cause | Fix |
|-------|-----|
| POS connection failed silently | Check Settings → POS Connections; look for warning |
| Background worker stopped | Engineering escalation |
| Token expiry (esp. Clover — see [pos-connection-failures.md](./pos-connection-failures.md)) | Reconnect |

## "Camera insights / cross-reference insights aren't appearing"

| Cause | Fix |
|-------|-----|
| Camera offline | See [camera-offline.md](./camera-offline.md) |
| Zones not configured | Camera add-on feature — merchant must draw zone polygons in dashboard |
| Less than 7 days of joint camera + POS data | Cross-reference agents need joint data; wait |
| Camera connected after POS (or vice versa); no joint window yet | Same — needs joint window |

## Escalation

| Pattern | Action |
|---------|--------|
| Specific agent shows "insufficient data" for >2 weeks despite adequate data | Medium ticket — possible bug |
| Money Left on Table number is wildly wrong | High ticket — check upstream agents |
| All insights gone after they were appearing | High ticket — likely connection/worker issue |

---

_Last updated: 2026-06-29_
_Sourced from: src/ai/agents/money_left.py (path selection logic) + src/ai/agents/base.py + src/errors.py (DataError) + general per-agent data requirements_
