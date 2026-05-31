# SumUp

**Registry key:** `sumup` — see `src/services/pos_connectors/registry.py`

## Status
UNCERTAIN — config exists with a current base URL, but NA market presence is thin and we have not built or tested the OAuth connect flow.

## What it is
SumUp is a European-founded mobile card reader + lightweight POS used by micro-merchants, mobile vendors, market traders, and small cafés/retail — competitor to PayPal Zettle and Square's mobile reader tier.

## Vertical & market
- **Primary vertical:** retail / food & beverage micro-SMB and mobile vendors (taxis, market stalls, salons, pop-ups)
- **Estimated NA market presence:** Small (US/Canada available, but SumUp's center of gravity is Europe)
- **Typical merchant profile:** Solo operator or 1–3 person business using SumUp Air, Solo, or Solo Lite reader paired with a phone — under ~$500k revenue
- **Geographic concentration:** Europe + UK dominant; SumUp lists 40+ countries including US, CA, BR, MX, CL, CO, PE, AU

## How to spot the merchant uses it
- Small black/white chip-and-tap reader branded **SumUp Air** or **SumUp Solo** (Solo has a built-in screen)
- Receipts and payment links on `sumup.link` / `pay.sumup.com`
- Merchant logs in at `me.sumup.com`
- Conversational tells: "my SumUp reader," "the SumUp app," "I just tap it to my phone"

## Auth method
OAuth 2.0 authorization code flow, plus API keys (`sk_test_*` / `sk_live_*`) for server-to-server use. Bearer token in `Authorization` header. Our current registry config assumes a bearer token has already been obtained — no OAuth client wired.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes | `GET /v0.1/me/transactions/history` (data key: `items`) | Paginated transaction history for the authenticated merchant |
| Test / identity | Yes | `GET /v0.1/me` | Used as health check |
| Catalog / items | No | not configured | SumUp's "Items" catalog is limited; not in our config |
| Customers | No | n/a | SumUp does not expose a rich customer object |
| Employees | No | n/a | Out of scope for SumUp's micro-merchant model |
| Inventory | No | n/a | Not a SumUp strength |
| Refunds | Yes (API supports) | `POST /v0.1/me/refund/{txn_id}` | Not wired in our connector |
| Orders (write) | No | `supports_orders: False` | Read-only integration |

## Partner program / access requirements
- **Partner program required:** No — self-service developer signup at the SumUp Developer Portal
- **Sign-up URL:** https://developer.sumup.com
- **Approval timeline:** Self-service (sandbox merchant + API keys immediately)
- **Cost / revenue share:** Free for API access; SumUp earns on the merchant's payment processing

## Sandbox / test environment
- **Available:** Yes — sandbox merchant account from the SumUp Dashboard
- **URL:** Same base URL; keys prefixed `sk_test_*` route to test mode
- **Notes:** OAuth client and redirect URI must be registered in the developer dashboard before live use

## Rate limits
Not publicly documented. Treat as low — recommend ≤5 req/sec per merchant and honor `429` with backoff until we measure in production.

## Webhook / sync model
Poll-only in current config (no webhook handler wired). SumUp does publish webhooks for checkouts/transactions, but we have not implemented them.

## Connect flow (what the merchant does)
1. In Meridian (future UI): **Settings → Integrations → Connect SumUp**
2. Redirected to SumUp consent screen; merchant signs into their SumUp account (`me.sumup.com`)
3. Reviews requested scopes (transactions read, profile) → **Allow**
4. Redirected back to Meridian with auth code → we exchange for access + refresh tokens
5. Backfill `/me/transactions/history` from earliest available; ongoing via poll

> Today this flow does not exist in the product — only the REST config is in place.

## Estimated effort to go LIVE
**M (1–2 weeks)** — OAuth client wiring, token storage/refresh, customer-facing connect UI, transaction normalization to Meridian's schema, and basic poll scheduler. No partnership cycle.

## What blocks LIVE status today
- No OAuth client implementation; registry assumes a bearer token already exists
- No customer-facing connect UI
- No webhook receiver; sync is poll-only by default
- No production validation against a real SumUp merchant

## Common failure modes (for troubleshooting playbook)
- **Symptom:** `401 Unauthorized` on `/me` → **Likely cause:** Expired access token or wrong key mode (`sk_test_` vs `sk_live_`) → **Fix:** Refresh token; verify environment.
- **Symptom:** Empty `items` array on `/me/transactions/history` → **Likely cause:** New merchant with no settled transactions yet, or wrong merchant context on the token → **Fix:** Confirm `/me` returns the expected merchant code.

## Strategic notes
SumUp is likely **off-ICP for Meridian today**. Our pipeline is North America-heavy; SumUp's NA footprint is small and the merchant is typically too micro to need analytics. Keep the config warm so we can flip it on opportunistically (EU expansion, a specific NA prospect, or a market-vendor vertical), but do not invest ahead of demand.

## Recommendation
**DEFER** — keep the registry entry, do not build the connect UI until we have a paying NA prospect on SumUp or commit to EU expansion.

**Reasoning:** Low NA market presence and micro-merchant ARPU don't justify the OAuth + UI build right now; config is correct and ready when demand appears.

## Sources consulted
- https://developer.sumup.com (API overview, OAuth 2.0, API keys)
- https://sumup.com (country availability — 40+ markets incl. US/CA)
- `src/services/pos_connectors/registry.py` (key: `sumup`, lines 379–387)
- Live API docs accessed: Yes (landing pages; deeper OAuth reference pages returned 404 via fetch and were not re-verified)
