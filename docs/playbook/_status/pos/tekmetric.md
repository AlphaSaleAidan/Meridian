# Tekmetric

**Registry key:** `tekmetric` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP — and config base_url currently points at SANDBOX, not production.

## What it is
Cloud-native auto repair shop management software (functions as the shop's POS + digital vehicle inspection + repair order system). One of the modern leaders for independent auto shops, replacing legacy Mitchell1 / AllData / ShopWare installs.

## Vertical & market
- **Primary vertical:** automotive — independent auto repair shops, tire stores, oil change centers, small multi-bay service chains
- **Estimated NA market presence:** Large within modern cloud auto-shop SaaS; Tekmetric advertises 70+ integration partners
- **Typical merchant profile:** 2–8 bay independent repair shop, $500K–$5M annual revenue, owner-operator
- **Geographic concentration:** US-heavy

## How to spot the merchant uses it
- Service writer working off a desktop browser at `shop.tekmetric.com`
- Digital vehicle inspection sent to the customer's phone with photos + recommendations
- Estimates / repair orders branded "Powered by Tekmetric" on the customer-facing portal
- Conversational tells: "we run on Tekmetric," "our DVI tool," "send the estimate through Tek"

## Auth method
OAuth 2.0 (client credentials) — `Client ID` + `Client Secret` issued by Tekmetric after partnership approval. Token sent as `Authorization` header. The config's `auth_type: header` matches, but the credential issuance flow is gated, not self-service.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes (per config) | `/repair-orders` | Paginated `page`/`size`, `content` envelope; filters on `updatedDateStart`/`updatedDateEnd` |
| Catalog / items | Yes (per config) | `/services` | Shop service catalog |
| Customers | Yes (per config) | `/customers` | |
| Employees | Yes (per config) | `/employees` | |
| Inventory | Not configured | — | Parts inventory exists in the API; not wired |
| Refunds | Unknown | — | Likely embedded in repair-order payload — needs live validation |

`supports_orders: True` in config, but order-push is unverified against partner docs.

## Partner program / access requirements
- **Partner program required:** Yes
- **Sign-up URL:** https://api.tekmetric.com (request form — no self-service)
- **Approval timeline:** ~2–3 weeks per community integrators; "approval at Tekmetric's discretion" — third-party (non-shop-operator) integrations are not guaranteed
- **Cost / revenue share:** Not publicly documented

## Sandbox / test environment
- **Available:** Yes — `https://sandbox.tekmetric.com/api/v1` (what the registry currently uses)
- **Production URL:** `https://shop.tekmetric.com/api/v1` (per community MCP implementations; needs first-party confirmation when credentials land)
- **Notes:** Sandbox credentials issued during the partner onboarding.

## Rate limits
Not publicly documented. Run conservatively until partner docs land.

## Webhook / sync model
Webhooks documented as available on the partner portal; current registry config is poll-only (`updatedDateStart`/`updatedDateEnd` window). Treat as poll-first, add webhooks post-partnership.

## Connect flow (what the merchant does)
1. Shop owner must already be a Tekmetric customer
2. Meridian needs Tekmetric-issued Client ID / Secret (partnership prerequisite — not merchant-issuable)
3. In Meridian: **Settings → Integrations → Connect Tekmetric** (UI not yet built)
4. Shop ID entered or selected → backfill kicks off against `/repair-orders`

## Estimated effort to go LIVE
L (1+ months) — gated almost entirely by Tekmetric partnership approval; engineering work itself is S–M once creds + production URL are in hand.

## What blocks LIVE status today
- **Base URL is sandbox.** `https://sandbox.tekmetric.com/api/v1` will not return real shop data; production is `https://shop.tekmetric.com/api/v1`. Swap before any LIVE merchant connect.
- **No partnership.** OAuth client credentials require Tekmetric approval (2–3 wk).
- **No customer-facing connect UI.** Same gap as other gated integrations.
- **Endpoint paths unvalidated** against current partner docs (config was built without live API access).

## Common failure modes (for troubleshooting playbook)
- **Symptom:** "Auth works in dev, no data in prod" → **Likely cause:** still hitting `sandbox.tekmetric.com` → **Fix:** flip `base_url` to `shop.tekmetric.com/api/v1`.
- **Symptom:** "401 on every call" → **Likely cause:** missing `Bearer ` prefix or expired client-credentials token → **Fix:** refresh token; confirm `Authorization` header format with partner docs.
- **Symptom:** "Empty `content` array" → **Likely cause:** date window too narrow or wrong `shopId` scoping → **Fix:** widen `updatedDateStart`; verify shop assignment.

## Strategic notes
Different vertical from Meridian's core ICP (food and beverage + retail SMBs on Square/Clover/Toast). **Reps should not actively prospect auto repair shops today** — we have no production integration, no partnership, no auto-shop-tuned dashboards, and the buyer persona (service manager / shop owner) is different from a restaurant GM. If an inbound auto shop appears and already uses Tekmetric, log the lead and flag for product — do not promise a timeline. The registry config is scaffolding for a future automotive expansion, not a sellable integration today.

## Recommendation
DEFER.

**Reasoning:** Gated partner program + sandbox-only config + off-ICP vertical. Revisit only if Meridian commits to an automotive expansion or an enterprise auto-shop lead justifies the 2–3 week partnership ask.

## Sources consulted
- https://www.tekmetric.com/integrations
- https://api.tekmetric.com
- https://apitracker.io/a/tekmetric
- https://github.com/beetlebugorg/tekmetric-mcp
- https://beetlebugorg.github.io/tekmetric-mcp/installation/
- `src/services/pos_connectors/registry.py` (lines 217–237)
- Live first-party API docs accessed: No (gated behind partner approval)
