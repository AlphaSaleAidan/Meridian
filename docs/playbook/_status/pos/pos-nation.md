# POS Nation

**Registry key:** `pos-nation` — see `src/services/pos_connectors/registry.py` (currently `auth_type: csv_only`, `category: cannabis`)

## Status
**OUTDATED CONFIG** — registry says `cannabis`, but POS Nation has no cannabis product. They are **multi-vertical small-business retail** (liquor, grocery, tobacco, c-store, phone repair, general retail). CSV-only is operationally correct; the category label is wrong.

## What it is
Charlotte, NC small-business POS company selling hardware bundles paired with software. Historically a pure reseller; **September 2020** they acquired **CAP Retail** and now run hybrid — in-house CAP Retail for general retail, plus vertical brands (Bottle POS, Market POS, Cigars POS, C-Store POS, CellSmart POS).

## Vertical & market
- **Primary vertical:** Multi-vertical small-business retail. **Not cannabis. Not restaurant.**
- **NA presence:** Medium — "10,000+ customers" per their site, mostly independent single-location
- **Merchant profile:** Independent liquor store, neighborhood grocer, cigar shop, single-location c-store
- **Geography:** US-focused

## How to spot the merchant uses it
- Mentions "Bottle POS", "Cigars POS", "C-Store POS", "Market POS", "CellSmart POS", or "CAP Retail"
- Receipt or back office shows "CAP Retail" or "Powered by POS Nation"
- Calls **1-877-727-3548** for support
- POS Nation–branded all-in-one touchscreen bundle

## Auth method
**CSV upload only.** No API wired. CAP Retail / Modern Retail does expose an "Integration API" (`api.modernretail.com`) for e-commerce sync with Shopify/BigCommerce/WooCommerce/Magento — auth scheme, endpoints, and rate limits not publicly documented.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders | CSV only | — | Columns: `Sale ID`, `Date`, `Total`, `Item Name`, `Tender Type` |
| Catalog | ✗ | — | |
| Customers | ✗ | — | |
| Employees | ✗ | — | |
| Inventory | ✗ | — | |
| Refunds | ✗ | — | |

Registry: `supports_orders: False`, `sms_fallback: True`.

## Partner program / access requirements
Not publicly advertised. Entry point is contact form on posnation.com or Modern Retail. Timeline, cost, rev share unknown.

## Sandbox / test environment
Not publicly documented.

## Rate limits
Unknown.

## Webhook / sync model
**Poll / batch.** No webhook surface in public docs.

## Connect flow
**CSV today:** operator exports a sales report from CAP Retail or their vertical product, uploads to Meridian.

## Estimated effort to go LIVE
**L (1+ months)** — partner conversation, API doc access, auth reverse-engineering, plus per-product-line validation.

## What blocks LIVE status today
- Registry `category: cannabis` is wrong — change to `retail`
- No public API documentation
- Long tail of older bundled platforms at customer sites may not share one API
- No committed Meridian go-to-market for independent liquor / c-store / tobacco

## Common failure modes
- **CSV column drift** between Bottle POS vs. CAP Retail exports → confirm headers per product line
- **`Total` with currency symbol** → strip `$` and commas before integer-cents
- **Brand ambiguity** → operator may say "POS Nation" but actually run a pre-2020 bundled third-party platform → confirm the back-office software name

## Strategic notes
The `cannabis` label is copy-paste drift — neighboring registry entries (`cova-pos`, `treez`) also carry `category: cannabis`. Wrong classification matters: cannabis decisions (compliance, METRC/BioTrack handling) should not trigger for a POS Nation merchant. The 2020 pivot also means calling them strictly a "reseller" is outdated — general retail is now in-house CAP Retail with vertical brands layered on top.

## Recommendation
**DEFER**

**Reasoning:** Real footprint, but no committed Meridian retail play, no public API, and the registry classification is wrong. Fix the `category` label, keep CSV-only as the honest answer for reps, revisit if multi-vertical retail is funded.

## Sources consulted
- https://posnation.com/ (verticals, brand list, customer count)
- https://www.prnewswire.com/news-releases/pos-nation-becomes-all-in-one-retail-provider-with-in-house-software-301121766.html (CAP Retail acquisition, Sept 2020)
- https://koronapos.com/blog/pos-nation-review/ (vertical coverage)
- https://modernretail.com/pos-erp-systems/pos-nation-cap-software-website-integration (Modern Retail middleware)
- `/root/Meridian/src/services/pos_connectors/registry.py` (`pos-nation`, lines 784–797)
- Live API docs accessed: No (none public)
