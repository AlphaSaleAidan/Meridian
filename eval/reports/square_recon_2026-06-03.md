# Square API recon — Stage A feasibility (2026-06-03)

- Environment (from `SQUARE_ENVIRONMENT`): **production**
- API base: `https://connect.squareup.com`
- Square-Version header: `2024-12-18`

All output is aggregate; no customer identifiers recorded.
Read-only across both Square (this script) and Meridian (untouched).

## A1 — Authentication + locations

- Token authenticates: **YES** (HTTP 200 on `/v2/locations`)
- Locations connected: **1**

| id | name | type | status | country | currency | created_at |
|----|------|------|--------|---------|----------|------------|
| LY1VJBWJ2J13J | Meridian | MOBILE | ACTIVE | US | USD | 2026-04-19T00:42:37.005Z |

## A2 — Customers directory sample

- Customers sampled: **20** (complete)
- With `email_address`: 100%
- With `phone_number`: 0%
- With `given_name` or `family_name`: 100%
- With `address`: 0%
- Earliest `created_at` in sample: 2026-05-18T18:22:22.301000+00:00
- Latest `created_at` in sample: 2026-05-19T20:45:41.853000+00:00
- Sample wall time: 0.3s

## A3 — Orders search (DESC by `created_at`)

- Orders sampled: **56** (complete)
- With `customer_id` populated: **0** (0.0%)
- Distinct `customer_id` values in sample: **0**
- Earliest `created_at` in sample: 2026-04-21T03:06:15.909000+00:00
- Latest `created_at` in sample: 2026-05-19T20:45:42.224000+00:00
- Sample wall time: 0.7s

Order state distribution (sample):

| state | count |
|-------|------:|
| CANCELED | 2 |
| COMPLETED | 1 |
| DRAFT | 47 |
| OPEN | 6 |

Monthly distribution (sample, oldest → newest):

| YYYY-MM | orders |
|---------|-------:|
| 2026-04 | 3 |
| 2026-05 | 53 |

## A4 — Repeat-customer signal

_(insufficient data — no customer-linked orders in sample)_

## Verdict — does Square have enough real data for a churn eval?

**THIN ON IDENTITY** — only 0.0% of sampled orders carry a `customer_id`. Churn-by-customer is not labelable from this data without a different identity strategy.

