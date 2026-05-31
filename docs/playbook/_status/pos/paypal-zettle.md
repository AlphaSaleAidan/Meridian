# PayPal Zettle (formerly iZettle)

**Registry key:** `paypal-zettle` (also legacy `izettle`) — see `src/services/pos_connectors/registry.py`

## Status
UNCERTAIN — API endpoints respond, but the platform is off-ICP for North America and PayPal is mid-rebrand to "PayPal Point of Sale."

## What it is
A PayPal-owned mobile/tablet POS plus chip-and-tap card reader aimed at micro-merchants — food trucks, market stalls, pop-ups, small independent retail. PayPal acquired iZettle in 2018 and is now rebranding it as "PayPal Point of Sale."

## Vertical & market
- **Primary vertical:** retail + light food/beverage (multi-vertical micro-merchant)
- **Estimated NA market presence:** Minimal — Zettle is a European-first product
- **Typical merchant profile:** Solo operator or 1–3 person business; market vendor, pop-up retailer, food truck, small café
- **Geographic concentration:** UK, Sweden, Germany, Italy, France, Spain, Netherlands, Brazil, Mexico. US presence is unclear (Wikipedia lists US historically; current paypal.com/us/...zettle URL 404s)

## How to spot the merchant uses it
- Compact white card reader (PayPal Reader / Zettle Reader 2) tethered to a phone or tablet
- App icon labeled "Zettle" or "PayPal Zettle" on iOS/Android
- Receipt or merchant dashboard at `my.zettle.com`
- Conversational tells: "my Zettle reader," "PayPal Point of Sale," any UK/EU merchant saying "card reader" not "terminal"

## Auth method
OAuth 2.0. Token endpoint `https://oauth.izettle.com/token` (HTTP 405 on GET — confirmed live). Merchant authenticates with their PayPal/Zettle account; client credentials + assertion grant for partner apps.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes | `GET /purchases/v2` on `purchase.izettle.com` | Returns 401 unauthenticated — confirmed live |
| Catalog / items | Yes | `GET /organizations/{org_id}/products` | Per-org scoped |
| Customers | No | — | Not in config; Zettle has limited customer data |
| Employees | No | — | Not in config |
| Inventory | Partial | via products endpoint | Stock counts available but not wired |
| Refunds | No | — | `supports_orders: False` — read-only purchases only |

Date params: `startDate` / `endDate` in `%Y-%m-%dT%H:%M:%S.000Z`.

## Partner program / access requirements
- **Partner program required:** Yes — developer app registration at `developer.zettle.com` (portal returned HTTP 200)
- **Sign-up URL:** https://developer.zettle.com
- **Approval timeline:** Self-service for sandbox; production app review unverified
- **Cost / revenue share:** No published fee — unverified

## Sandbox / test environment
- **Available:** Yes (per developer portal) — specific sandbox URL not verified in this pass
- **Notes:** GitHub `iZettle/api-documentation` repo is marked **[Deprecated]**; mobile SDKs (`sdk-ios`, `sdk-android`) still public but low activity. Ecosystem is in maintenance mode.

## Rate limits
Unknown — not documented in our config or in the public portal pages reachable.

## Webhook / sync model
Poll-only per current config (no webhook fields). Zettle has historically offered limited webhook coverage; treat as polling integration with `startDate`/`endDate` windows.

## Connect flow (what the merchant does)
1. In Meridian: **Settings → Integrations → Connect PayPal Zettle**
2. Merchant redirected to PayPal/Zettle OAuth consent (signs in with PayPal account that owns the Zettle merchant)
3. Approves read scopes for purchases + products
4. Redirected back to Meridian; poll-based backfill begins on `/purchases/v2`

(UI not yet built — see blockers.)

## Estimated effort to go LIVE
L (1+ months) — needs partner app approval, OAuth UI, polling sync engine, and validation of the deprecated API docs against the live endpoints.

## What blocks LIVE status today
- No customer-facing OAuth UI built
- Official `api-documentation` repo is deprecated — endpoint paths need live re-validation
- Active PayPal rebrand to "PayPal Point of Sale" — API surface may shift
- North American merchant base is thin; ROI on the integration is low

## Common failure modes (for troubleshooting playbook)
- **Symptom:** "401 Unauthorized" → **Likely cause:** Expired bearer / OAuth assertion → **Fix:** Re-run OAuth flow.
- **Symptom:** "Merchant says they use PayPal but no Zettle data" → **Likely cause:** They use PayPal Checkout, not Zettle POS → **Fix:** Confirm they have a physical Zettle/PayPal Reader.
- **Symptom:** "Empty product catalog" → **Likely cause:** Wrong `org_id` in path → **Fix:** Resolve org via `/users/self` first.

## Strategic notes
Two names, one product — reps will hear "iZettle" (legacy), "Zettle by PayPal," and now "PayPal Point of Sale." All three map to `paypal-zettle` for us; the duplicate `izettle` registry key exists for back-compat only.

This is fundamentally a European SMB tool. For North American ICP it almost never comes up — if a US merchant mentions "PayPal," they more often mean PayPal Here (discontinued 2022, now migrated to Zettle) or generic PayPal Checkout, not the physical reader. Qualify hardware ("do you have a card reader from PayPal?") before promising an integration.

## Recommendation
DEFER — keep the config, do not build the UI until we have inbound demand from EU/UK merchants or PayPal completes the "PayPal Point of Sale" rebrand and republishes stable docs.

**Reasoning:** Off-ICP geography, deprecated public API documentation, and an active product rebrand make the engineering risk high while the addressable revenue in North America is low.

## Sources consulted
- https://developer.zettle.com (HTTP 200 — portal live)
- https://oauth.izettle.com/token (HTTP 405 — confirmed live)
- https://purchase.izettle.com/purchases/v2 (HTTP 401 — confirmed live)
- https://github.com/iZettle (api-documentation repo marked Deprecated)
- https://www.zettle.com/gb ("Zettle by PayPal becomes PayPal Point of Sale")
- https://en.wikipedia.org/wiki/IZettle (acquisition + country list)
- `src/services/pos_connectors/registry.py` (entries `paypal-zettle` and `izettle`)
- Live API docs accessed: Partial — official docs repo deprecated; endpoints probed directly
