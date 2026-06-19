# Clover REST API — Read-Only Endpoint Coverage

What the Meridian Clover client (`src/clover/client.py`) consumes, why, and what we
deliberately skip. All endpoints are under `/v3/merchants/{mId}` and are **read-only**
(the digest never writes back to Clover). Money is in cents; timestamps are epoch
milliseconds; lists use offset/limit pagination and Clover silently caps time-filtered
queries to the most recent **90 days** (we window wider ranges — see
`_list_time_filtered`).

## Implemented

| Method | Path | Used by | Notes |
|---|---|---|---|
| `get_merchant()` | `/` | backfill phase 1 → location | name, address, timezone, currency, `isBillable` |
| `get_merchant_properties()` | `/properties` | available | extra merchant settings; not currently mapped |
| `list_devices()` | `/devices` | available | Clover treats devices as "locations" |
| `list_employees()` | `/employees` | backfill phase 2 | builds id→name cache for `employee_name` |
| `list_categories()` | `/categories` | backfill phase 3 | id→category lookup |
| `list_items()` | `/items?expand=categories,modifierGroups,tags` | backfill phase 4 | products + id→product lookup |
| `list_order_types()` | `/order_types` | both syncs → `_fetch_config_lookups` | id→label; surfaces `metadata.order_type` (Dine In/Take Out/Delivery) |
| `list_tenders()` | `/tenders` | both syncs → `_fetch_config_lookups` | id→{label,labelKey}; authoritative `payment_method` mapping |
| `list_orders()` | `/orders?expand=lineItems.taxRates,payments,discounts,serviceCharges,device` | backfill phase 5 + incremental | transactions + line items; 5-expansion budget (tax, tips, discounts, service charges, device) |
| `get_order()` | `/orders/{id}` (same expand) | order webhook | single-order refetch |
| `list_refunds()` | `/refunds` | `_apply_refunds` (both syncs) | appended as discrete `type='refund'` rows |
| `list_payments()` | `/payments` | available | payments incl. tender + tip; orders already carry payments via expand |
| `list_item_stocks()` | `/item_stocks` | backfill phase 6 + inventory webhook | inventory snapshots |
| `list_tax_rates()` | `/tax_rates` | reconcile validation | id/name/rate; not a write path |
| `list_customers()` | `/customers` | available | customer list |

## Deliberately not implemented

| Path | Why skipped |
|---|---|
| `/cash_events` | Cash-drawer audit trail — not part of the revenue/inventory digest. |
| `/modifier_groups` (standalone) | Modifiers arrive via `list_items(expand=modifierGroups)`; no separate fetch needed. |
| `/credits` | Manual merchant credits — refunds (`/refunds`) cover the money-out path we surface. |
| Ecommerce/hosted-checkout endpoints | Different product surface (HMAC-signed); Meridian integrates the merchant POS API, not Clover Ecommerce. |

## How tender & order-type mapping works

`/order_types` and `/tenders` are small, merchant-level config sets fetched once per sync by
`CloverSyncEngine._fetch_config_lookups` (best-effort — a fetch failure falls back to whatever
the order/payment objects carry inline). The mapper:

- **order_type:** prefers `order.orderType.label` if present, else resolves `order.orderType.id`
  against the lookup → `transaction.metadata.order_type`.
- **payment_method:** resolves `payment.tender.id` against the lookup, then maps Clover's canonical
  `labelKey` (`com.clover.tender.cash` / `…check`) before falling back to fuzzy label matching.
  Specific tenders (gift, debit) are matched before the generic "card" check so e.g. "Gift Card"
  isn't misclassified as a credit card.

## Verifying it end to end

`scripts/reconcile_clover.py <org_id> --token … --merchant … [--sandbox] --days 30` pulls
Clover's own sale/refund totals for the window and diffs them against Meridian's stored
`transactions`, applying the same sale/void classification on both sides. A clean PASS proves the
OAuth/token → list → map → upsert path is faithful. Get a real (free) credential via a Clover
sandbox developer merchant + a merchant-specific API token (Developer Dashboard → Test Merchants →
Merchant Dashboard → Settings → API tokens → Create Token).
