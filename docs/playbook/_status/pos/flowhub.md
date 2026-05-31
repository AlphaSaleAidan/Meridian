# Flowhub

**Registry key:** `flowhub` — see `src/services/pos_connectors/registry.py` (lines 823-834)

## Status
**NEEDS PARTNERSHIP** — config seeded with plausible base URL + endpoints, but Flowhub gates production credentials behind a manual partner intake (email `api@flowhub.com`). No public developer portal, no public Swagger, no sandbox docs surfaced. Endpoint paths in registry are unverified against the live API.

## What it is
Denver-based cloud cannabis dispensary POS + Greenlight handheld terminals + Maui ecommerce + Metrc compliance + payments, sold to single- and multi-location licensed dispensaries.

## Vertical & market
- **Primary vertical:** Cannabis dispensary (state-regulated retail)
- **NA market presence:** Medium-Large — widely cited as #3 US dispensary POS after Dutchie and Treez
- **Typical merchant profile:** Independent and small-MSO dispensaries; strong with operators that value Metrc integration depth (Flowhub wrote the first Metrc integration in 2015)
- **Geographic concentration:** US-only (federal Schedule I — no Canada/intl). Strong in CO, MI, MA, OK; expanding NY

## How to spot the merchant uses it
- Budtenders ringing sales on Flowhub-branded iPads or "Greenlight" handheld scanners at the display case
- Online menu / order-ahead branded "Powered by Flowhub" or on Maui (`maui.flowhub.com` subdomain)
- Receipts/compliance labels reference Metrc package tags pulled via Flowhub
- Conversational tell: "we're on Flowhub" or "Greenlight" (handheld) or "Maui" (ecom menu)

## Auth method
**Bearer token (Client Id + API Key issued by Flowhub)** — per partner intake documentation surfaced through third-party integrators (DailyStory), Flowhub provisions a `Client Id` + `API Key` pair that the integrator stores in account settings. Registry's `auth_type: "bearer"` is directionally correct, but exact header shape (single bearer vs. paired headers) is UNCERTAIN until live credentials are issued.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Config only | `/transactions` | Unverified path |
| Catalog / inventory | Config only | `/inventory` | Cannabis SKUs are Metrc-tagged — expect package-level granularity |
| Customers (members) | Config only | `/members` | Patient/member PII, regulated |
| Employees | Config only | `/employees` | Budtender-level attribution |
| Inventory | Same as catalog | `/inventory` | Combined |
| Refunds | Not configured | — | Validate post-credential |

`supports_orders: False` — pull-only. No phone-agent order push.

## Partner program / access requirements
- **Required:** Yes. No self-service developer signup discovered.
- **Sign-up:** Email `api@flowhub.com` (per ProgrammableWeb 2016 + current Flowhub partners site). No public application form.
- **Approval timeline:** UNCERTAIN — not published. Plan 2-6 weeks based on comparable cannabis POS vendors.
- **Cost / revenue share:** Not publicly disclosed.

## Sandbox / test environment
- **Available:** UNCERTAIN — not documented publicly. Likely issued during partner onboarding.

## Rate limits
**Not publicly documented.** Plan exponential backoff; confirm at credentialing.

## Webhook / sync model
**Poll-only assumed.** No public webhook documentation found.

## Connect flow (what the merchant does)
*Hypothetical until credentialed:*
1. Meridian completes Flowhub partner intake (`api@flowhub.com`), receives `Client Id` + `API Key`
2. Dispensary operator authorizes Meridian (mechanism TBD — likely Flowhub-side enablement per-account)
3. Merchant pastes/confirms in Meridian connect screen; we test against `/locations` before unlocking dashboard

## Estimated effort to go LIVE
**L (1+ months calendar).** Engineering ~3-5 days (validate endpoint paths against live API, build connect UI, mappers for Metrc-tagged inventory). Blocker is partner intake cycle + endpoint validation.

## What blocks LIVE status today
- No Flowhub partner intake submitted; no `Client Id`/`API Key` issued
- Endpoint paths (`/transactions`, `/inventory`, `/members`, `/employees`) unvalidated against live API — no public Swagger to cross-check
- `base_url` `https://api.flowhub.co/v1` returned 405 on probe (method-not-allowed, not a 404 — suggests host exists but root path doesn't accept GET; auth-gated)
- No cannabis vertical commitment on Meridian side (banking, compliance, marketing constraints same as Dutchie/Treez)

## Common failure modes
- **401 on every call** → wrong auth header shape (bearer vs. paired Client-Id + Api-Key) → re-check intake docs once issued
- **404 on `/transactions`** → endpoint name drift (might be `/sales`, `/orders`, `/receipts` in current API) → validate against live docs once credentialed
- **Empty `/inventory` despite live SKUs** → wrong location/store scoping param → confirm tenant model with Flowhub support

## Strategic notes
Cannabis is all-or-nothing: Dutchie (~dominant), Treez (~#2), Flowhub (~#3) cover the vast majority of US licensed dispensaries. Owning only one is a half-measure — operators switch vendors and MSOs run mixed stacks. Federal Schedule I status means no Stripe/standard banking, regulated patient PII, restricted ad channels. Flowhub's CO/MI/MA/OK strength complements Dutchie's national footprint and Treez's CA dominance — together the three give Meridian credible cannabis vertical coverage.

## Recommendation
**WAIT** — keep registry stub seeded; do not pitch Flowhub merchants and do not file partner intake until leadership greenlights cannabis as a named vertical alongside Dutchie + Treez.

**Reasoning:** Flowhub is the right #3 if Meridian commits to cannabis, but unilaterally pursuing Flowhub without Dutchie + Treez wastes the partner cycle on a vertical Meridian can't credibly sell into. Bundle the three or skip all three.

## Sources consulted
- https://www.flowhub.com/partners (partner ecosystem landing)
- https://www.flowhub.com/ (product overview, open API positioning)
- https://help.flowhub.com/en/articles/8796540-api-sales-reporting-in-vermont (state compliance reporting; confirms API surface exists)
- https://docs.dailystory.com/article/eju41pn77i-integrations-flowhub (third-party integrator confirms Client Id + API Key model)
- https://www.programmableweb.com/news/flowhub-api-seeds-growth-high-stakes-marijuana-industry/analysis/2016/11/14 (historical: `api@flowhub.com` as intake)
- https://www.flowhub.com/partners/metrc-integration (Feb 2025 Metrc Connect reaffirmation)
- `/root/Meridian/src/services/pos_connectors/registry.py` (`flowhub` entry, lines 823-834)
- Live API docs accessed: **No** — no public developer portal; `api.flowhub.co/v1` returned 405 (auth-gated). Authoritative auth shape, endpoint paths, rate limits, and webhook model remain UNCERTAIN until partner credentials are issued.
