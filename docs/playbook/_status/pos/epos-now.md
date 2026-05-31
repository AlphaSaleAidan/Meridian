# Epos Now

**Registry key:** `epos-now` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP — config base URL and shape look right, but Epos Now requires an approved AppStore developer app before production access is usable.

## What it is
Epos Now is a UK-founded cloud POS used across both hospitality (pubs, cafes, restaurants, takeaways) and retail (convenience, vape, salon, pharmacy, gift), typically on iPad or touchscreen all-in-one terminals sold direct or via the Epos Now reseller channel.

## Vertical & market
- **Primary vertical:** multi-vertical (hospitality + retail, with strong salon/beauty and convenience presence)
- **Estimated NA market presence:** Small-to-Medium — Epos Now lists US/CA storefronts, but the installed base skews UK
- **Typical merchant profile:** Independent single-site or small multi-site SMB; price-sensitive, often sold a hardware bundle on a multi-year deal
- **Geographic concentration:** UK primary; also US, Canada, Australia, NZ, Ireland, Spain, Germany, Mexico, UAE

## How to spot the merchant uses it
- Branded Epos Now touchscreen terminal or iPad with Epos Now app
- Merchant logs in to `eposnowhq.com` Back Office
- Receipts/back-office reference "Epos Now"
- Conversational tells: "Epos Now," British spelling of "Epos," mentions of a UK head office or a multi-year hardware lease

## Auth method
Bearer token per registry config (`auth_type: bearer` against `https://api.eposnowhq.com/api/v4`). The exact header format (Bearer vs HTTP Basic with driver/secret) and per-merchant access-token issuance flow are gated behind the developer portal and were not directly verifiable in this pass — validate against the live `developer.eposnowhq.com` docs after sign-up before shipping a connect flow.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes | `GET /api/v4/transaction` | `data_key: None` — response shape needs validation |
| Catalog / items | Yes | `GET /api/v4/product` | Brand, Category, ProductImage resources also exist per docs index |
| Customers | Yes | `GET /api/v4/customer` | CustomerAddress and CustomerPoints exist as separate resources |
| Employees | Yes | `GET /api/v4/staff` | Clocking and Role resources also exist |
| Inventory | Not configured | — | `ProductStock`, `Location`, `PurchaseOrder` exist in v4 — not wired today |
| Refunds | Not configured | — | Likely embedded in `/transaction`; needs schema validation |
| Order creation | No | — | `supports_orders: False`; phone agent cannot push orders |

## Partner program / access requirements
- **Partner program required:** Yes — Epos Now operates an AppStore with a documented Sign Up → Build → Submit → Approval → Launch workflow
- **Sign-up URL:** https://developer.eposnowhq.com/Home/DeveloperSignUp
- **Approval timeline:** Not published; treat as 2–6 weeks per typical POS AppStore review cadence
- **Cost / revenue share:** Not disclosed publicly on the signup or developer landing pages

## Sandbox / test environment
- **Available:** Not verified in this pass
- **URL:** N/A — registry points at production `https://api.eposnowhq.com/api/v4`
- **Notes:** Plan to provision a sandbox or test merchant during the developer-program application

## Rate limits
Not verified in this pass — implement defensive throttling and honor HTTP 429 `Retry-After`.

## Webhook / sync model
Poll-only as wired today. Epos Now's integration docs reference webhook setup and a dedicated webhook IP, so a webhook-driven sync is feasible after partnership is approved.

## Connect flow (what the merchant does)
1. Meridian must first be an approved Epos Now AppStore app (one-time partner workstream)
2. In Meridian: **Settings → Integrations → Connect Epos Now**
3. Merchant authenticates against their Epos Now account and grants Meridian access
4. Redirected back to Meridian; backfill begins against `/transaction`
5. Per-merchant access token persisted for ongoing poll/sync

## Estimated effort to go LIVE (config → production-ready)
L (1+ months) — engineering itself is modest (bearer auth, REST), but the partner gate, app submission, and review cycle dominate the timeline.

## What blocks LIVE status today
- No Epos Now AppStore developer registration submitted
- No customer-facing connect UI for Epos Now in Meridian
- Auth header exact format (Bearer vs Basic) and per-merchant token flow not validated against live docs
- Pagination, date filters, and `data_key` shape (`None`) in the registry not yet schema-validated against a live response

## Common failure modes (for troubleshooting playbook)
- **Symptom:** "401 Unauthorized on first call" → **Likely cause:** Wrong auth scheme (Bearer vs Basic) or app not yet approved → **Fix:** Confirm scheme with developer portal; verify app status in AppStore.
- **Symptom:** "Empty `data` array but 200 OK" → **Likely cause:** Response wrapping differs from `data_key: None` assumption → **Fix:** Inspect raw payload; adjust `data_key` in registry.
- **Symptom:** "Transactions missing for date range" → **Likely cause:** No `start_date_param`/`end_date_param` wired in registry → **Fix:** Add date-filter params after confirming Epos Now's filter syntax.

## Strategic notes
Epos Now is a real lever for UK expansion and a useful checkbox for US merchants who happen to be on it, but it is not a North America growth driver. The partner-program gate means we should only invest if (a) Meridian is actively pursuing UK distribution, or (b) a US rep surfaces a multi-location Epos Now merchant whose ARR justifies the 1–2 month integration runway. Reps in the US should treat Epos Now sightings as "qualify hard, then escalate" — not "promise integration this quarter."

## Recommendation
WAIT — defer the partner submission until either UK expansion is committed or a qualified US opportunity lands.

**Reasoning:** Integration is straightforward once approved, but the AppStore review gate makes speculative work expensive. Build on demand, not speculation.

## Sources consulted
- https://developer.eposnowhq.com (developer portal landing)
- https://developer.eposnowhq.com/Docs/Global (V2/V4 docs index — resource list confirmed)
- https://developer.eposnowhq.com/Home/DeveloperSignUp (developer registration form)
- https://www.eposnow.com/uk/integrations/ (AppStore + verticals + geography)
- `src/services/pos_connectors/registry.py` (key: `epos-now`)
- Live API docs accessed: Partial (resource index and signup confirmed; auth-detail and full V4 reference behind 403/404 or sign-in)
