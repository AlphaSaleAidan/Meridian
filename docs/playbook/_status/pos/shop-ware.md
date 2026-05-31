# Shop-Ware

**Registry key:** `shop-ware` — see `src/services/pos_connectors/registry.py` (lines 238–256)

## Status
NEEDS PARTNERSHIP — public API exists and is documented, but credentials are gated on an API Partner relationship. Config bearer-auth assumption is plausible but unverified against live partner docs.

## What it is
Cloud-based auto repair shop management software — runs the service writer's day end-to-end (estimates, digital vehicle inspections, repair orders, invoicing, parts ordering). Competes head-to-head with Tekmetric and Shopmonkey for the modern independent-shop segment.

## Vertical & market
- **Primary vertical:** automotive — independent auto repair shops, multi-bay service centers, tire stores
- **Estimated NA market presence:** Medium-Large within modern cloud SMS; 40+ named integration partners on their partner page (360 Payments, AutoOps, Worldpac, Mitchell1, Carfax, Kukui, PartsTech, Zapier, Podium, et al.)
- **Typical merchant profile:** 3–10 bay independent shop, $750K–$5M annual revenue, often a "high-performance" shop that has already left Mitchell1/AllData
- **Geographic concentration:** US-heavy

## How to spot the merchant uses it
- Service writer working in `app.shop-ware.com` from a desktop or large tablet
- Estimates / DVIs sent to customer phones branded Shop-Ware
- Shop owner mentions "the Workflow board," "Tech Worksheet," or "our SMS is Shop-Ware"
- Integration stack tells: 360 Payments, AutoOps scheduling, Worldpac parts

## Auth method
Bearer token per registry config (`auth_type: bearer`, `base_url: https://app.shop-ware.com/api/v1`). Shop-Ware's public API uses an **API Partner ID** model with tenant-scoped access; partner credentials are issued after approval. Exact header format (raw bearer vs. partner-id header) is **not first-party verified** — confirm against partner docs at credential issuance.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes (per config) | `/repair_orders` | Paginated `page`/`per_page`, `results` envelope; window via `updated_after`/`updated_before` (YYYY-MM-DD) |
| Catalog / items | Yes (per config) | `/services` | Shop service catalog |
| Customers | Yes (per config) | `/customers` | |
| Employees (techs) | Yes (per config) | `/technicians` | |
| Inventory | Not configured | — | Parts/inventory entities exist in Public API per Stoplight; not wired |
| Refunds | Unknown | — | Likely embedded in repair-order payload — needs live validation |

`supports_orders: True` in config (`order_create_endpoint: /repair_orders`, `order_id_field: id`), but order-creation has not been tested against live credentials.

## Partner program / access requirements
- **Partner program required:** Yes — Shop-Ware's Public API is gated; no self-service developer signup is publicly documented
- **Sign-up URL:** No public developer portal; entry points are `support.shop-ware.com` and the contact line on `shop-ware.com/partners/` (415-890-0906)
- **Approval timeline:** Not publicly documented
- **Cost / revenue share:** Not publicly documented

## Sandbox / test environment
- **Available:** Not publicly documented
- **URL:** N/A (production base in registry is `https://app.shop-ware.com/api/v1`)
- **Notes:** Tenants are fully isolated per Public API docs; expect a sandbox tenant to be issued during onboarding.

## Rate limits
Windowed per IP and per API Partner ID; current status returned in response headers per Shop-Ware's rate-limiting doc. Exact thresholds not published — run conservative concurrency and respect returned headers.

## Webhook / sync model
Not publicly confirmed. Current registry config is poll-only via `updated_after` / `updated_before`. Treat as poll-first; ask about webhooks during partner intake.

## Connect flow (what the merchant does)
1. Shop must already be a Shop-Ware tenant
2. Meridian must hold an approved API Partner credential (prerequisite — not merchant-issuable)
3. Shop owner enables the Meridian integration in **API Integrations** settings within Shop-Ware
4. In Meridian (UI not yet built): **Settings → Integrations → Connect Shop-Ware** → tenant selected → backfill against `/repair_orders`

## Estimated effort to go LIVE
L (1+ months) — bottlenecked on partner approval and on building a customer-facing connect UI. Engineering is S–M once credentials land and the auth header format is confirmed.

## What blocks LIVE status today
- No API Partner relationship with Shop-Ware
- Auth header format unverified — config assumes raw `Authorization: Bearer <token>`; Public API may require an API-Partner-ID header pair
- No customer-facing connect UI (same gap as Tekmetric)
- Endpoint paths copied from convention, not validated against live Stoplight schema

## Common failure modes (for troubleshooting playbook)
- **Symptom:** "401 on every call" → **Likely cause:** wrong auth header shape or expired partner token → **Fix:** confirm header format against partner docs; refresh credential.
- **Symptom:** "429 with retry-after" → **Likely cause:** windowed rate limit hit on the partner ID → **Fix:** back off using returned headers; lower concurrency.
- **Symptom:** "Empty `results` array" → **Likely cause:** date window too narrow or wrong tenant scoping → **Fix:** widen `updated_after`; verify tenant assignment.

## Strategic notes
Off-ICP for Meridian today. Reps should **not** prospect auto repair shops — no live integration, no partnership, no automotive-tuned dashboards, and the buyer (shop owner / service manager) is a different sale than a restaurant GM. If an inbound shop already runs Shop-Ware, log the lead and flag for product. Shop-Ware sits alongside Tekmetric and Shopmonkey as the three modern cloud SMS leaders — any future automotive expansion needs all three, not just one.

## Recommendation
DEFER.

**Reasoning:** Gated partner program, unverified auth specifics, and off-ICP vertical. Revisit only if Meridian commits to an automotive expansion or a large multi-shop lead justifies the partnership and UI work.

## Sources consulted
- https://shop-ware.com/partners/
- https://support.shop-ware.com/s/article/API-Partner-Integration (page failed to render via WebFetch — JS-only)
- https://shop-ware.stoplight.io/docs/public-api/b287rk0o3bkrz-rate-limiting
- https://shop-ware.stoplight.io/docs/public-api/u7tg4dbg59g8q-entities
- https://shop-ware.stoplight.io/docs/public-api/n1zw0ockkvv8m-common-parameters
- `src/services/pos_connectors/registry.py` (lines 238–256)
- Live first-party API call: No (gated behind partner credentials)
