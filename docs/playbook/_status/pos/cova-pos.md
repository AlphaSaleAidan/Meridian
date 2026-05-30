# Cova POS

**Registry key:** `cova-pos` — see `src/services/pos_connectors/registry.py` (line 798)

> Config disambiguation: the registry currently lists `base_url: https://api.covasoftware.com/v1` with header auth. Live Cova docs at `api.covasoft.net/Documentation` show the actual host is `https://api.covasoft.net/<service>` (e.g. `/pointofsale`, `/productlibrary`) with OAuth 2.0 tokens minted from iQmetrix (`https://accounts.iqmetrix.net/v1/oauth2/token`). Registry config needs validation before LIVE.

## Status
NEEDS PARTNERSHIP (config endpoint + auth flow are stale; production OAuth credentials require Cova partner program approval)

## What it is
Cannabis-vertical retail POS + inventory + compliance suite for licensed dispensaries; cloud back-office with iPad/Windows till hardware, built on the iQmetrix retail platform.

## Vertical & market
- **Primary vertical:** cannabis (retail dispensary only — not cultivation/wholesale)
- **Estimated NA market presence:** Dominant in Canada; mid-tier in US (Dutchie + Flowhub larger US-side)
- **Typical merchant profile:** licensed single-store or 2–20 location dispensary chain
- **Geographic concentration:** Canada-first (HQ Vancouver BC + Denver CO; originally founded in Regina, SK). ~70% of Canadian legal brick-and-mortar dispensaries, 52% of Alberta stores, 50%+ of BC stores. Also serves NY, NJ, MI, IL, NM, MN, MS in the US.

## How to spot the merchant uses it
- iPad or Windows till; back-office login at `*.covasoft.net` or "Cova Cloud"
- "Cova Pay" branded payment terminals
- Receipt or e-commerce footer references Cova; product catalog UX is iQmetrix-style
- Tells: "we're on Cova," "Cova handles our AGLC/OCS/BCLDB reporting," "our budtenders use Cova"

## Auth method
OAuth 2.0 (token endpoint hosted by iQmetrix at `accounts.iqmetrix.net/v1/oauth2/token`). Bearer token in `Authorization` header on all subsequent Cova service calls. Static API key flow in current registry config is incorrect.

## Data we can pull (per live API surface)
| Type | Available | Endpoint family | Notes |
|------|-----------|-----------------|-------|
| Orders / transactions | yes | `pointofsale` / `SalesInvoice` / `SalesOrder` | Per-location |
| Catalog / items | yes | `productlibrary` / `DataPlatform` / `Catalog` | Master + per-store pricing |
| Customers | yes | CRM service | Loyalty + member data |
| Employees | yes | CompanyTree | Org hierarchy |
| Inventory | yes | `productlibrary` | Stock + price |
| Refunds | yes | via SalesInvoice negatives | Confirm during smoke test |

## Partner program / access requirements
- **Partner program required:** Yes — production OAuth client credentials are gated
- **Sign-up URL:** `https://www.covasoftware.com/partner-inquiry` (inquiry form, no self-service)
- **Approval timeline:** Not published; categories include "Featured" and "Bundled" partner tiers — expect 4–8 week relationship build
- **Cost / revenue share:** Not disclosed publicly

## Sandbox / test environment
- **Available:** Not publicly documented
- **URL:** N/A — must request via partner intake
- **Notes:** Cova publishes a Postman collection (`COVA_API_Collection_for_Integrators.json`) on the documentation portal; use for shape validation before partnership lands

## Rate limits
Not published on the public docs page (referenced from a "Getting Started" section gated behind partner access). Assume conservative throttling until confirmed.

## Webhook / sync model
No webhook support documented publicly. Plan for poll-only sync (invoices by updated-date window).

## Connect flow (what the merchant does)
1. Meridian rep initiates connection from merchant's Cova-enabled account
2. Merchant authorizes Meridian's OAuth client in Cova back-office
3. iQmetrix accounts service redirects with `code` → Meridian exchanges for access + refresh token
4. Meridian calls CompanyTree to enumerate the merchant's locations, stores location IDs
5. Backfill begins against `SalesInvoice` per location

## Estimated effort to go LIVE (config → production-ready)
L (1+ months). Drivers: partner approval cycle, registry config rewrite (host + OAuth), CompanyTree location discovery, multi-service base-URL handling (Cova splits services across subpaths).

## What blocks LIVE status today
- No partner program approval / production OAuth client
- Registry `base_url` and `auth_type` are wrong (point to non-Cova host `api.covasoftware.com/v1` with static header auth)
- No CompanyTree location-discovery step in connector
- No OAuth refresh handling in connector base
- `data_key: "data"` likely wrong — iQmetrix responses vary per service

## Common failure modes (for troubleshooting playbook)
- **Symptom:** 401 on all calls → **Cause:** using static API key against OAuth endpoint → **Fix:** mint Bearer token from iQmetrix accounts service
- **Symptom:** 404 on `/sales/invoices` → **Cause:** stale registry path → **Fix:** target `https://api.covasoft.net/pointofsale/...` instead
- **Symptom:** Merchant on Cova but no Canadian provincial board data flowing → **Cause:** Cova reports to AGLC/OCS/BCLDB internally; not all of that is exposed via API → **Fix:** scope analytics promises to in-Cova data only

## Strategic notes
**This is the single highest-value cannabis integration for the Meridian Canada portal (meridian.tips).** Cannabis is fully legal nationwide in Canada and regulated province-by-province — Cova powers ~70% of Canadian dispensaries and handles provincial compliance reporting (AGLC Alberta, OCS Ontario, BCLDB British Columbia, SQDC adjacency in Quebec). Owning the Cova integration effectively unlocks the Canadian cannabis vertical for Meridian.

US-side, Cova is mid-tier; Dutchie + Flowhub matter more. Frame Cova as the **Canada wedge**, Dutchie as the US-cannabis wedge. Pair this with the Canada portal's province-aware compliance positioning.

## Recommendation
**BUILD NOW** — but as a partnership track, not a sprint.

**Reasoning:** Dominant Canadian cannabis POS share + Canada portal already live = highest-leverage cannabis integration we can pursue. Start partner intake immediately; in parallel, fix the registry config and prototype against the Postman collection. Do not promise a customer-facing LIVE date until OAuth credentials are in hand.

## Sources consulted
- https://api.covasoft.net/Documentation (live API portal, accessed)
- https://www.covasoftware.com/partners
- https://www.covasoftware.com/partner-inquiry
- https://www.covasoftware.com/cannabis-retail-suite-canada
- https://www.covasoftware.com/pos/alberta (52% AB share claim)
- https://www.covasoftware.com/pos/bc (50%+ BC share claim)
- https://betakit.com/saskatchewan-startup-beats-out-shopify-as-pos-behind-cannabis-retailers/ (~70% Canadian share, Regina founding)
- https://www.newswire.ca/news-releases/52-of-alberta-cannabis-stores-use-cova-pos-to-make-big-strides-despite-strict-rules-885984203.html
- Registry config: `src/services/pos_connectors/registry.py` (line 798)
- Live API docs accessed: Yes
