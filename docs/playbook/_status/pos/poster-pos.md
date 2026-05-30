# Poster POS

**Registry key:** `poster-pos` — see `src/services/pos_connectors/registry.py`

## Status
READY (off-ICP) — real API host, documented auth, no NA connect UI, merchant base outside NA ICP.

## What it is
Cloud cafe/restaurant POS for the Ukrainian/CIS small-business market; tablet front-of-house, web back office at `joinposter.com`.

## Vertical & market
- **Primary vertical:** restaurant — independent cafes, coffee shops, bakeries, bars, food trucks, small franchises
- **NA presence:** Small — Poster lists 27,000 active businesses across "110 countries"; no material NA base surfaced
- **Typical merchant:** 1–3 location independent cafe/restaurant in Ukraine/CIS or emerging markets
- **Geography:** International — dominant Ukraine/CIS small F&B; HQ Hong Kong

## How to spot the merchant uses it
- Back office at `joinposter.com` (Cyrillic UI common); tablet app branded "Poster"
- Receipt or QR-menu footer references `joinposter.com`
- Ukrainian or Russian-speaking operator; tells: "Poster," "joinposter," "Постер"

## Auth method
API key as query param (`token=`) on every call — per registry (`auth_type: "query"`, base `https://joinposter.com/api`). Self-service token issuance from the merchant's account; separate OAuth flow exists for marketplace apps, not used here.

## Data we can pull (per current config)
| Type | Available | Endpoint |
|------|-----------|----------|
| Orders / transactions | ✓ (read) | `/dash.getTransactions` |
| Catalog / items | ✓ | `/menu.getProducts` |
| Customers | ✓ | `/clients.getClients` |
| Employees | ✓ | `/access.getEmployees` |
| Inventory | ✗ | — |
| Refunds | ✗ | — |

Envelope keyed `response`. Test: `/settings.getSettings`. `supports_orders: False`.

## Partner program / access requirements
- **Required:** No for per-account tokens; Yes for marketplace apps
- **Sign-up URL:** `https://dev.joinposter.com/`; merchant tokens generated in their account
- **Timeline:** Self-service per-account; marketplace not published
- **Cost:** Per-account API free; marketplace economics not published

## Sandbox / test environment
- **Available:** UNCERTAIN — no public sandbox host; spin up a free trial and test against production
- **URL:** N/A publicly

## Rate limits
Not publicly documented. Treat as conservative until measured.

## Webhook / sync model
Poll-only as configured. Marketplace-app webhooks exist; not wired.

## Connect flow (what the merchant does)
1. Log into back office at `joinposter.com`
2. Open account/integrations, generate API token
3. Paste into Meridian's connect screen
4. Meridian verifies via `/settings.getSettings?token=…` then polls transactions/menu/clients/employees

## Estimated effort to go LIVE
M (1–2 weeks) — config and auth correct; missing connect UI, per-merchant sanctions review, pagination/date-window validation on `/dash.getTransactions`.

## What blocks LIVE status today
- No paste-token UI
- Read-only (`supports_orders: False`)
- No webhook wired
- No legal review of merchant geography

## Common failure modes
- **Auth error every call** → whitespace in token or revoked → trim, re-issue
- **Empty `/dash.getTransactions`** → date window outside data, or plan gates dashboard → widen, confirm plan
- **Intermittent 5xx** → undocumented rate limit → back off poll frequency

## Strategic notes
Real platform — center of gravity Ukrainian/CIS small F&B, not NA pipeline. Two compliance flags: (1) **Russia sanctions** — US/UK/EU sanctions since 2022 restrict IT/cloud/software services to Russia-resident entities; a Russia-resident merchant triggers OFAC review regardless of API cleanliness. Non-RU tenants (Ukraine, EU, MENA) still need standard KYB. (2) **Data residency** — HQ Hong Kong, cloud-region story unpublished.

## Recommendation
DEFER (geography).

**Reasoning:** Off-ICP for NA; connector and auth are fine, but merchant base concentrates in Ukraine/CIS with unresolved Russia-sanctions exposure on RU-resident tenants — no UI work until a non-RU deal forces it.

## Sources consulted
- Registry: `src/services/pos_connectors/registry.py` (`poster-pos`)
- https://joinposter.com/en/about (HQ, 27K merchants, 110 countries)
- https://dev.joinposter.com/ (dev portal; inner pages JS-rendered, specifics flagged UNCERTAIN)
- Sanctions: https://www.clearytradewatch.com/2024/10/u-s-uk-and-eu-sanctions-alignment-u-s-it-and-software-sector-service-bans-and-export-controls-take-effect-as-russia-sanctions-continue-to-expand/
- Live API docs: Partial
