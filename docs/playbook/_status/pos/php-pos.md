# PHP Point of Sale

**Registry key:** `php-pos` — see `src/services/pos_connectors/registry.py`

## Status
READY (config exists and matches live API; no customer-facing connect UI; self-hosted model makes onboarding non-standard)

## What it is
Self-hosted PHP-based retail POS that merchants install on their own web server or shared hosting; web-based UI with optional hardware peripherals.

## Vertical & market
- **Primary vertical:** general retail (multi-vertical: convenience, liquor, smoke shops, small grocery, gift shops)
- **Estimated NA market presence:** Small (niche; popular with technically inclined indie retailers and overseas operators)
- **Typical merchant profile:** single- to small-multi-location independent retailer running their own server or cheap shared hosting
- **Geographic concentration:** global, with notable adoption outside the US in cost-sensitive markets

## How to spot the merchant uses it
- Merchant mentions "we host our own POS" or "our IT person set it up"
- Browser URL bar shows `/index.php/...` on the back-office screen
- Cashier interface is plain web-based (no proprietary terminal hardware)
- They reference an annual license fee rather than a monthly SaaS subscription

## Auth method
API key (header) — `x-api-key`, per-merchant. Base URL is per-domain: `https://{domain}/index.php/api/v1`.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | ✓ | `/sales` | `supports_orders: False` in config — sales only |
| Catalog / items | ✓ | `/items` | Also `/item_kits`, `/categories` available |
| Customers | ✓ | `/customers` | Batch endpoint exists |
| Employees | ✓ | `/employees` | |
| Inventory | ~ | (via `/items`) | No dedicated inventory endpoint configured |
| Refunds | ~ | (via `/sales`) | Not separately configured |

Test endpoint: `/info`. `data_key: None` (responses are top-level arrays).

## Partner program / access requirements
- **Partner program required:** No
- **Sign-up URL:** N/A — merchant generates own key inside their installation
- **Approval timeline:** Self-service (per merchant)
- **Cost / revenue share:** Free for us; merchant pays own license + hosting

## Sandbox / test environment
- **Available:** Yes (vendor-hosted demo)
- **URL:** `https://demo.phppointofsale.com/index.php/api/v1/yaml` (OpenAPI spec)
- **Notes:** No shared sandbox keys; we'd need a real merchant install or self-hosted test install

## Rate limits
Unknown — not documented. Behavior depends entirely on merchant's own server.

## Webhook / sync model
Poll-only. No webhook support documented.

## Connect flow (what the merchant does)
1. Log into their own PHP POS install as admin
2. Navigate to Employees, edit the API user
3. Enable API access and copy the generated API key
4. Provide Meridian with their **domain** (e.g. `pos.theirstore.com`) and the **API key**
5. Meridian stores both; base URL is templated as `https://{domain}/index.php/api/v1`

## Estimated effort to go LIVE (config → production-ready)
M (1–2 weeks) — config is correct, but we need a two-field connect UI (domain + key), TLS/reachability validation, and per-merchant support docs.

## What blocks LIVE status today
- No customer-facing connect UI for the domain + API key pair
- No reachability/health check (self-hosted installs are often behind weak TLS, expired certs, basic auth, or non-public IPs)
- No version pinning — merchant installs vary in version; endpoints may drift per install
- Support burden: when sync breaks, root cause is usually the merchant's server, not us

## Common failure modes (for troubleshooting playbook)
- **Symptom:** "401 / invalid key" → **Likely cause:** key revoked or copied with whitespace → **Fix:** regenerate in their admin, repaste
- **Symptom:** "connection refused / TLS error" → **Likely cause:** self-signed cert, expired cert, or host firewalled → **Fix:** merchant fixes their cert/firewall
- **Symptom:** "404 on `/index.php/api/v1/*`" → **Likely cause:** API module not enabled or older install without v1 → **Fix:** merchant updates install / enables API
- **Symptom:** "endpoint returns HTML, not JSON" → **Likely cause:** request hit a login redirect (key missing or wrong header) → **Fix:** confirm `x-api-key` header, not `Authorization`

## Strategic notes
PHP POS is real and the API spec is current (v1, OpenAPI YAML publicly served from the demo). But the self-hosted model means every merchant is a snowflake: their own domain, their own TLS, their own version, their own uptime. Each connection is effectively a custom integration in production support terms. Volume per merchant won't justify the support cost unless we already have a cluster of PHP POS merchants asking for it.

## Recommendation
DEFER

**Reasoning:** Niche NA footprint and self-hosted architecture create a high per-merchant support burden that outweighs the per-account revenue. Keep the config as-is so we can flip on connection support reactively if 3+ merchants request it.

## Sources consulted
- https://phppointofsale.com/api.php
- https://demo.phppointofsale.com/index.php/api/v1/yaml
- https://support.phppointofsale.com/hc/en-us/articles/360000581643-API (403 to fetcher; referenced via vendor index)
- `src/services/pos_connectors/registry.py` (lines 757–769)
- Live API docs accessed: Yes (OpenAPI YAML confirmed)
