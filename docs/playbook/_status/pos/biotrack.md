# BioTrack

**Registry key:** `biotrack` — see `src/services/pos_connectors/registry.py` (currently `auth_type: csv_only`)

## Status
**OUTDATED CONFIG** — registry says `csv_only`, but BioTrack actually exposes a per-state JSON/XML state-traceability API (e.g. `https://mcmonitoring.agr.illinois.gov/serverjson.asp`). Treat as CSV-only operationally until partner access is sorted.

## What it is
A cannabis seed-to-sale platform with two surfaces: a state-government traceability system licensees must report into, and a commercial dispensary POS. They share branding, not the same API.

## Vertical & market
- **Vertical:** Cannabis (regulated cultivation, processing, dispensary)
- **NA presence:** Dominant as a state traceability system; smaller commercial POS share (trails Dutchie/Flowhub/Treez/Cova)
- **Merchant profile:** Licensed operator in a BioTrack state, required to report regardless of checkout POS
- **Geography:** US-only. Traceability states per OpenTHC wiki: AR, CT, DE, FL, HI, IL, NH, NM, NY, ND, VA. **WA dropped BioTrack in 2017** (user's WA claim is wrong). **NY migrating to Metrc Q1 2026.**

## How to spot the merchant uses it
- Operator in any state above — files state reports through BioTrack even if checkout is Dutchie/Flowhub/Cova
- Manifests reference "BioTrackTHC" or "BioTrack Trace"; package IDs use BioTrack format (not METRC)
- Operator mentions "the state system," "UBI number," or "serverjson"

## Auth method
**Per-state username + password + UBI/license** → returns `sessionid` used as `x-api-key` on follow-up calls. Optional MFA. v2/v3 endpoints JSON-only; v1 XML or JSON. No OAuth, no public app registration. Credentials belong to the licensee, not the integrator.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders | CSV only | — | Sales endpoints exist on state API |
| Catalog | CSV only | — | Inventory endpoints exist |
| Customers | ✗ | — | API is product/plant-centric |
| Employees | ✗ | — | Exists on state API, not exposed |
| Inventory | CSV only | — | Plant lifecycle, adjust, transfer all available |
| Refunds | ✗ | — | |

Registry CSV columns: `Transaction ID`, `Date`, `Total`, `Product Name`, `METRC Tag`, `License Number`. `supports_orders: False`, `sms_fallback: True`.

## Partner program / access requirements
- **Required:** Yes for commercial POS sync; no for state-API access if licensee shares own credentials
- **URL:** `https://biotrack.com/resources/partners/` (returned 403 unauthenticated — verify in browser)
- **Timeline / cost:** Not published

## Sandbox / test environment
Yes — include `<training>1</training>` (XML) or equivalent JSON flag for training mode. Confirmed for Illinois.

## Rate limits
Not documented. State APIs serve regulators in real time — assume tight quotas, plan backoff.

## Webhook / sync model
**Poll-only.** No webhook surface in public docs.

## Connect flow (what the merchant does)
**CSV today:** Operator exports BioTrack sales report, uploads to Meridian.
**API future:** Merchant supplies username + password + UBI; Meridian POSTs login, stores `sessionid`, polls per-state endpoints.

## Estimated effort to go LIVE
**L (1+ months)** — per-state base URL routing, credential storage for username+password+UBI, session refresh, training toggle, cannabis compliance review. CSV path today is **S** but caps value.

## What blocks LIVE status today
- Registry `csv_only` masks real API — needs a `biotrack_state_session` auth variant
- No per-state base URL table (IL, FL, NM, NY, etc. all differ)
- Storing licensee credentials needs a different security review than holding an API key
- No cannabis vertical commitment from Meridian
- NY operators leave BioTrack Q1 2026 — NY-only investment shrinks fast

## Common failure modes
- **CSV $0 totals** → `Total` has currency symbol → strip `$` before parse
- **METRC Tag empty** → operator in BioTrack-only state (no METRC) → fall back to BioTrack package IDs
- **Future 401** → sent creds as Basic instead of POSTing to login → fix login flow, capture `sessionid`
- **Future wrong endpoint** → used IL URL for NM licensee → add state routing table

## Strategic notes
BioTrack is a **regulatory rail**, not just a POS. Highest near-term value is using it as compliance source-of-truth in BioTrack states, not as a checkout system. A merchant on Dutchie in a BioTrack state still touches BioTrack for state reporting — so this integration can complement, not just compete with, Dutchie. Two cliffs: NY migrating to Metrc Q1 2026, and any cannabis play inherits federal Schedule I, banking, and marketing constraints.

## Recommendation
**WAIT** — pending cannabis vertical commitment.

**Reasoning:** Real API exists, so the `csv_only` label is wrong and should be flagged. But going live needs per-state plumbing, licensee-credential handling, and a cannabis go-to-market. Reps should not promise a live BioTrack connection today; CSV upload is the only honest answer until cannabis is a named vertical.

## Sources consulted
- https://biotrack.com/biotrack-features/integrations/
- https://wiki.openthc.org/BioTrack (state list, WA removal Oct 2017)
- http://server.biotrackthc.net/API_documentation/Illinois/ (live — confirms username/password/UBI, sessionid, `serverjson.asp`/`serverxml.asp`, training mode, v4.0)
- https://docs.api.nm.biotrackthc.net/ (NM Trace 2.0)
- https://api.licensee.fl.biotr.ac/ (FL licensee Swagger)
- https://cannabis.ny.gov/biotrack-faq
- https://www.cannabisregulations.ai/cannabis-and-hemp-regulations-compliance-ai-blog/new-york-metrc-2026-biotrack-migration-readiness (NY → Metrc Q1 2026)
- https://www.flowhub.com/press-release/flowhub-launches-advanced-biotrack-state-traceability-integration
- `/root/Meridian/src/services/pos_connectors/registry.py` (`biotrack` entry)
- Live API docs accessed: Yes (Illinois)
