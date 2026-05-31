# Data Requirements Matrix

Which features need which data, from which POS systems. Use this to set expectations during discovery — if a merchant is on a POS that doesn't expose customer IDs, you can't promise customer LTV; if they have no camera, no cross-reference agents.

## Data fields × Features

| Feature | Transactions | Line items | Customer ID | Employee ID | Camera | Multi-loc |
|---------|--------------|------------|-------------|-------------|--------|-----------|
| revenue_trend | required | — | — | — | — | — |
| cash_flow | required | — | — | — | — | — |
| pricing_power | required | required | — | — | — | — |
| discount_analyzer | required | — | — | — | — | — |
| foot_traffic | required | — | — | — | boost | — |
| queue_monitor | required | — | — | — | boost | — |
| basket_analysis | required | required | — | — | — | — |
| product_velocity | required | required (SKU) | — | — | — | — |
| inventory_intel | required | required (SKU) | — | — | — | — |
| category_mix | required | required (category) | — | — | — | — |
| customer_recognizer | required | — | helpful | — | — | — |
| dwell_time | required | — | — | — | **required** | — |
| peak_hours | required | — | — | — | — | — |
| day_of_week | required | — | — | — | — | — |
| seasonality | required | — | — | — | — | — |
| location_analyst | required | — | — | — | — | **required (Command)** |
| loyalty_architect | required | — | helpful | — | — | — |
| demographic_profiler | — | — | — | — | **required** | — |
| employee_performance | required | — | — | **required** | helpful | — |
| staffing | required | — | — | helpful | helpful | — |
| payment_optimizer | required | — | — | — | — | — |
| waste_shrinkage | required | — | — | — | — | — |
| forecaster | required | — | — | — | — | — |
| growth_score | required | required | helpful | helpful | helpful | helpful |
| customer_ltv | required | — | **required** | — | helpful (re-id) | — |
| cashflow_forecast | required | — | — | — | — | — |
| promo_roi | required | — | — | — | — | — |
| benchmark | required | helpful | — | — | — | — |
| action_prioritizer | (aggregates other agents) |
| money_left_on_table | (aggregates other agents) |
| **All cross-reference agents** | required | helpful | — | — | **required** | — |

## POS systems × Data field coverage

What you can rely on from each major POS:

| POS | Transactions | Line items | Customer ID | Employee ID | Real-time |
|-----|--------------|------------|-------------|-------------|-----------|
| Square | yes | yes | yes | yes | yes (webhooks + 5min poll) |
| Clover | yes | yes | yes (if captured) | yes | hourly (webhooks pending) |
| Toast | yes | yes (rich) | yes | yes | yes (webhooks shipping) |
| Lightspeed Retail | yes | yes | yes | yes | hourly |
| Lightspeed Restaurant | yes | yes | yes | yes | hourly |
| Korona | yes | yes | yes | yes (cashiers) | hourly |
| Shopify POS | yes | yes | yes | yes (users) | hourly |
| CAKE (CSV) | yes | yes | **no** | **no** | daily |
| Lavu | yes | yes | partial | yes | hourly |
| talech (CSV today) | yes | yes | **no** | **no** | daily |
| SkyTab | yes | yes | **no** | yes | hourly |
| TouchBistro | yes | yes | partial | yes | hourly |
| SpotOn | yes | yes | yes | yes | hourly |
| Epos Now | yes | yes | yes | yes (staff) | hourly |
| Erply | yes | yes | yes | yes | hourly |
| **Cannabis** |
| Cova | yes | yes | yes | yes | hourly |
| Dutchie | yes | yes | yes | yes | hourly |
| Treez | yes | yes (tickets) | yes | yes (budtenders) | hourly |
| Flowhub | yes | yes | yes (members) | yes | hourly |
| Meadow | yes | yes | yes (patients) | **no** | hourly |
| Blaze | yes | yes | yes (members) | **no** | hourly |
| BioTrack (CSV) | yes | yes | **no** | **no** | daily |
| Indica Online (CSV) | yes | yes | **no** | **no** | daily |
| **CSV-only legacy** |
| All automotive | yes | partial | **no** | **no** | daily |
| Rezku (CSV) | yes | partial | **no** | **no** | daily |
| Most other CSV | yes | partial | **no** | **no** | daily |

## What this means for your discovery

When prospect says **"I'm on [POS]"**, you can immediately answer:

1. **Will customer LTV work?** Check the Customer ID column. If "no" → tell them upfront, suggest loyalty program collection upgrade.
2. **Will employee performance work?** Check the Employee ID column. If "no" → don't pitch that feature.
3. **Real-time alerts vs daily?** Check the Real-time column. If "daily" (CSV path), set expectations accordingly.
4. **Will any cross-reference / vision feature work?** Requires a connected supported camera (regardless of POS).

## What "helpful" means in the matrix

"Helpful" = the feature works without it, but is meaningfully better with it. Example:

- `growth_score` works on transactions alone (basic score) but is much richer with line items + customer IDs + employee data
- `customer_ltv` "helpful: cameras (re-id)" — the LTV agent works on POS customer IDs alone; adding cameras with person re-ID catches walk-in regulars who don't show in POS customer data

## Cameras × Cross-reference features

All 10 cross-reference agents need cameras. Specifically:

| Cross-ref agent | Camera requirement |
|-----------------|---------------------|
| influence_zone | Cameras covering target zones + zone polygons configured |
| lost_sale | Camera at entrance |
| path_to_purchase | Cameras across multiple zones |
| peak_basket | Camera with wide coverage |
| posture_purchase | Cameras + skeletal tracking module (Command) |
| product_placement | Cameras covering product zones |
| queue_basket | Camera at checkout |
| return_customer | Cameras + person re-ID service |
| staff_effect | Cameras detecting staff (uniform/badge) |
| zone_conversion | Cameras + zone polygons |

If a merchant has only one camera (at the entrance), they get: foot_traffic, queue_monitor (if entrance-facing), lost_sale, basic dwell_time. They do NOT get path_to_purchase, product_placement, staff_effect.

**Sales takeaway:** for cross-reference features, recommend 2–3 cameras minimum (entrance, main floor zones, checkout). At $60 each (Reolink), that's $120–$180 in hardware for $239/mo recurring commission to you.

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ class-level metadata + src/services/pos_connectors/registry.py (per-POS data field coverage) + src/camera/ pipeline modules_
