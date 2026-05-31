# WooCommerce (WC REST API)

**Registry key:** `woo-pos` — see `src/services/pos_connectors/registry.py`

## Status
READY — config matches the documented `wp-json/wc/v3` surface with HTTP Basic Auth (consumer key/secret). No partner gate, no OAuth UI required to pilot. Needs a customer-facing "paste your key" connect screen and a clear position on the online-vs-in-store framing before we list it as LIVE.

## What it is
WooCommerce is the dominant WordPress ecommerce plugin — primarily an **online store** platform. A separate "WooCommerce POS" add-on plugin exists for in-store checkout, but the vast majority of merchants run WooCommerce as a web storefront; the same REST API serves both surfaces.

## Vertical & market
- **Primary vertical:** retail (online), with long-tail use in services, digital goods, subscriptions
- **Estimated NA market presence:** Dominant in WordPress-based ecommerce; one of the largest ecommerce platforms globally by site count
- **Typical merchant profile:** SMB online retailer running a self-hosted WordPress site, often DTC / niche brands, agencies-built stores, hobbyist-to-professional sellers
- **Geographic concentration:** Global (US, EU, IN heaviest)

## How to spot the merchant uses it
- Store URL is a WordPress site; admin at `<domain>/wp-admin`
- Checkout pages styled with default WooCommerce blocks; "Powered by WooCommerce" sometimes in footer
- Conversational tells: "my WordPress store," "I use Woo," "Woo subscriptions," "my web guy set up WooCommerce"
- In-store POS hardware is uncommon — most WooCommerce merchants do not have a physical till

## Auth method
HTTP **Basic Auth** over HTTPS: REST API Consumer Key as username, Consumer Secret as password. Generated self-service by the merchant in their WordPress admin.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes | `GET /wp-json/wc/v3/orders` | Paginate `page`/`per_page`; filter `after`/`before` |
| Catalog / items | Yes | `GET /wp-json/wc/v3/products` | |
| Customers | Yes | `GET /wp-json/wc/v3/customers` | |
| Employees | Not in config | — | WordPress users exist; not a Woo-native concept |
| Inventory | Not in config | — | Available on product payload (`stock_quantity`); needs adding |
| Refunds | Not in config | — | Available via `orders/{id}/refunds`; needs adding |
| Order creation | Yes | `POST /wp-json/wc/v3/orders` | `supports_orders: true` in config |

## Partner program / access requirements
- **Partner program required:** No
- **Sign-up URL:** N/A — credentials issued from the merchant's own WordPress admin
- **Approval timeline:** Self-service, instant
- **Cost / revenue share:** Free

## Sandbox / test environment
- **Available:** Yes — any local WordPress install (LocalWP, Studio by WordPress.com, Docker) with the WooCommerce plugin activated
- **Notes:** Plugin is free; demo data is one click in the WooCommerce setup wizard

## Rate limits
Not documented in the WC REST API reference. Practical limit is the merchant's WordPress host — many shared-hosting plans throttle aggressively. Plan for conservative paging (≤100/page is already our config) and backoff on HTTP 429 / 5xx.

## Webhook / sync model
Hybrid. WooCommerce supports native webhooks (orders create/update, products, customers) configurable in **WooCommerce → Settings → Advanced → Webhooks**. We are poll-only today.

## Connect flow (what the merchant does)
1. In their WordPress admin: **WooCommerce → Settings → Advanced → REST API → Add key**
2. Set permissions to **Read** (or **Read/Write** if we want order creation), generate
3. Copy the Consumer Key and Consumer Secret (shown once)
4. In Meridian: **Settings → Integrations → Connect WooCommerce**, paste store URL + key + secret

## Estimated effort to go LIVE
**S (1–3 days)** — pure "paste your key" UI plus a test-connection call against `/system_status`.

## What blocks LIVE status today
- No customer-facing connect UI built
- No webhook subscription helper
- Strategic call on whether Meridian wants the online-retail vertical (see below)

## Common failure modes (for troubleshooting playbook)
- **Symptom:** `401 woocommerce_rest_authentication_error` → **Cause:** key sent over HTTP, not HTTPS → **Fix:** require HTTPS; suggest OAuth 1.0a fallback for non-SSL stores
- **Symptom:** `404 rest_no_route` → **Cause:** WooCommerce plugin disabled, pretty permalinks off, or security plugin blocking `/wp-json/` → **Fix:** verify plugin active and permalinks set to anything but "Plain"
- **Symptom:** timeouts on large stores → **Cause:** shared host throttling → **Fix:** reduce `per_page`, add retry/backoff
- **Symptom:** missing in-store sales → **Cause:** merchant is not running the WC POS add-on → **Fix:** confirm with merchant; Woo is primarily an online channel

## Strategic notes
This integration is materially different from every other entry in our registry: WooCommerce is overwhelmingly an **online store**, not an in-store POS. Roughly all the data we'd pull is ecommerce orders. That's still valuable — Meridian's analytics work just as well on web orders — but the rep pitch must reframe ("unify your online + in-store sales analytics") rather than imply we're powering a register. The in-store WC POS add-on exists and uses the same API, so a merchant who has it will Just Work, but those are rare.

Pairs naturally with Shopify POS (same omnichannel story) and Square (many Woo merchants also run a Square Reader for occasional in-person sales).

## Recommendation
**BUILD** if Meridian wants the online-retail vertical; **DEFER** if we are staying focused on brick-and-mortar POS analytics.

**Reasoning:** Self-service, free, simple Basic Auth — engineering cost is among the lowest in the registry. The only real question is product/positioning: do we want to serve online-only sellers? If yes, this is a fast win against a massive TAM. If no, defer until the strategy says otherwise.

## Sources consulted
- https://woocommerce.github.io/woocommerce-rest-api-docs/
- `src/services/pos_connectors/registry.py` (key: `woo-pos`)
- Live API docs accessed: Yes
