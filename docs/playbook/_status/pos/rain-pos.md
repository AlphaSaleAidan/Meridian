# Rain POS

**Registry key:** `rain-pos` — see `src/services/pos_connectors/registry.py`

## Status
CSV ONLY — confirmed against vendor public surface. Registry config carries no `base_url` and `auth_type: csv_only`; no public REST API, OAuth, or developer portal was found.

## What it is
Rain Retail Software — cloud POS + integrated website for niche specialty retail. The vendor ships vertical-branded variants (e.g., music shops, sewing/quilting/fabric, jewelry, bike/outdoor/ski/dive). Web-based back office; receipt printer + drawer at the counter.

## Vertical & market
- **Primary vertical:** specialty retail (music, fabric/quilt/sewing, sporting goods, jewelry, outdoor)
- **NA presence:** Small–Medium; deep in the vertical niches it targets, not broad SMB retail
- **Merchant:** independent single-location or small multi-location specialty shop, often owner-operated, doing parallel e-commerce on the bundled Rain website
- **Geography:** US-heavy

## How to spot the merchant uses it
- Owner says "Rain," "MusicShop360," "Like Sew," or "Jewel360" (Rain vertical brands)
- Storefront website and POS are obviously the same product (shared catalog, Rain footer/admin)
- Login URL on `rainpos.com` or a vertical-brand subdomain

## Auth method
CSV upload only. No partner-issuable API key, OAuth, or webhook surface found on `rainpos.com` or `knowledge.rainpos.com`. Public integrations advertised (Shopify, QuickBooks Online, Notions Marketing, Clientbook) are vendor-built, not an open partner API.

## Data we can pull (per current config)
| Type | Available | Notes |
|------|-----------|-------|
| Orders / transactions | CSV only | Cols: `Transaction #`, `Date`, `Total`, `Item Description`, `Payment Type` |
| Catalog / items | ✗ | Not mapped — manual export from Products if needed |
| Customers | ✗ | Not mapped |
| Employees | ✗ | Not in CSV columns |
| Inventory | ✗ | Manual export only |
| Refunds | ✗ | Not mapped |

`supports_orders: False`, `sms_fallback: True` — no order push; SMS receipt capture is the real-time fallback.

## Partner program / access requirements
None publicly documented. Any integration work would require a direct vendor conversation.

## Sandbox / test environment
None. Validate against a sample CSV export.

## Rate limits
N/A — file upload.

## Webhook / sync model
None. Manual or scheduled CSV; SMS fallback for near-real-time receipts if shop opts in.

## Connect flow (what the merchant does)
1. Rain admin → **Reports** → Sales → choose date range → Export CSV
2. (Optional) Products → Inventory → Export for catalog
3. Shop uploads CSV in Meridian; column mapping uses registry defaults

## Estimated effort to go LIVE
S (1–3 days) — CSV importer wiring only. No API path to build against today.

## What blocks LIVE status today
No public first-party API — vendor constraint, not a Meridian gap. Real-time data requires SMS fallback or vendor partnership conversation.

## Common failure modes
- Columns don't match → re-map; confirm `Transaction #`, `Date`, `Total` present
- Totals off → export filtered by tender type → re-run with all payment types
- Missing item detail → exported summary instead of line-item report → re-run line-item view

## Strategic notes
Off-ICP for Meridian's Square/Clover/Toast F&B + retail focus. Footprint is real inside specialty niches (quilt, music, bike) but small in aggregate, and the vendor's bundled e-commerce reduces demand for third-party data tooling. Note: user-provided claim that Cygnet (formerly Cygnet International) owns Rain POS could **not be verified** from public sources during this pass — treat ownership as unconfirmed until a primary source is found.

## Recommendation
DEFER. Off-ICP, no API, and small aggregate footprint. Keep the CSV importer for inbound leads already on Rain; do not prospect. Revisit only if a vertical partnership (e.g., quilt or music shop channel) creates concentrated demand.

## Sources consulted
- https://www.rainpos.com — public site; integrations listed, no developer portal
- https://knowledge.rainpos.com — knowledge base; no API docs surfaced
- `src/services/pos_connectors/registry.py` — `rain-pos` entry (csv_only)
- `frontend/src/data/pos-systems.ts` — `apiAvailable: false`, `oauthSupported: false`, `webhooksSupported: false`
- Live first-party API access: No — none found
