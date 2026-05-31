# GloriaFood

**Registry key:** `gloria-food` — see `src/services/pos_connectors/registry.py` (lines 652–666)

## Status
**CSV ONLY / mis-categorized** — registry has it as `category: "restaurant"` with `auth_type: "csv_only"`, but GloriaFood is **not a POS**. It's an online ordering/delivery widget that sits alongside the merchant's actual POS.

## What it is
A free online ordering and reservation system for restaurants — embeds a "See Menu & Order" button on the restaurant's website/Facebook page and routes incoming digital orders to the operator via tablet, email, or SMS.

## Vertical & market
- **Primary vertical:** restaurant — independents, small chains, ghost kitchens
- **Estimated NA market presence:** Medium within the free-tier indie segment; not visible in enterprise/multi-unit
- **Typical merchant profile:** single-location pizzeria, café, or takeout-heavy ethnic restaurant; the operator who wants online ordering without paying Toast / Square / Olo for it
- **Geographic concentration:** global; significant presence in US, Canada, UK, EU

## How to spot the merchant uses it
- "See MENU & Order" button on their website or Facebook page
- Order confirmation emails / SMS from `noreply@gloriafood.com`
- Operator says "I get the orders on a tablet" but names a separate POS (Square, Clover, Toast) for in-store
- They mention it's free / they don't pay for online ordering

## Auth method
**CSV upload only** (`auth_type: "csv_only"`). No live API integration in the current registry. `sms_fallback: True` is set.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes (CSV) | — | Digital orders only; columns: `Order ID`, `Date`, `Total`, `Items Ordered`, `Payment`, `Customer Name` |
| Catalog / items | No | — | Not wired |
| Customers | Partial (CSV) | — | Customer Name only, no contact fields |
| Employees | No | — | GloriaFood has no labor data |
| Inventory | No | — | Lives in the actual POS |
| Refunds | No | — | Not in CSV schema |
| Order create (push) | No | — | `supports_orders: False` |

## Partner program / access requirements
- **Partner program required:** No for CSV; unknown for any future API (public API not documented for third-party data extraction)
- **Sign-up URL:** https://www.gloriafood.com/
- **Approval timeline:** N/A (CSV is operator-driven export)
- **Cost / revenue share:** Free tier exists; paid add-ons (promo, marketing, branded app) — none of which gate data export

## Sandbox / test environment
- **Available:** N/A — CSV only
- **URL:** N/A
- **Notes:** Operator exports order history from their GloriaFood admin and uploads to Meridian

## Rate limits
N/A — no live API.

## Webhook / sync model
N/A — CSV upload, one-shot.

## Connect flow (what the merchant does)
1. Log into GloriaFood admin
2. Export order history to CSV
3. Upload CSV to Meridian via the CSV importer

## Estimated effort to go LIVE (config → production-ready)
**XL** — would require either (a) a partnership/API GloriaFood does not publicly offer, or (b) confirming the unverified `sms_fallback` path actually delivers structured order data. Neither is justified by ICP fit.

## What blocks LIVE status today
- No public API for third-party order extraction
- Mis-categorized as `restaurant` POS — it's an ordering channel, not the POS-of-record
- Even with full data, output is online orders only — same fundamental gap as Olo

## Common failure modes (for troubleshooting playbook)
- **Symptom:** Operator says "this is way less than my real sales" → **Cause:** GloriaFood = digital channel only → **Fix:** ask which POS they ring in-store orders on and connect that
- **Symptom:** CSV `Items Ordered` field is a free-text blob → **Cause:** GloriaFood exports items as a string, not normalized line items → **Fix:** treat as opaque; do not attempt SKU-level analytics

## Strategic notes
GloriaFood occupies the same scope-mismatch slot as Olo (digital-only channel feeding a different POS-of-record), but at the opposite end of the market: free-tier indies instead of enterprise chains. For Meridian's ICP, the value would be **combining** GloriaFood digital with the operator's real POS (Square, Clover, Toast) — and at that point the real POS connection is what matters; GloriaFood is at best a secondary channel feed.

## Recommendation
**DEFER** — leave the CSV-only config in place, do not invest in API discovery or live integration.

**Reasoning:** Not a POS, no public ingestion API, free-tier merchants are low-LTV, and digital-only data is intrinsically partial. Pursue the underlying POS instead.

## Sources consulted
- `/root/Meridian/src/services/pos_connectors/registry.py` (`gloria-food` entry, lines 652–666)
- https://www.gloriafood.com/ (product scope, free-tier confirmation)
- Live API docs accessed: No (no public third-party data-export API found)
