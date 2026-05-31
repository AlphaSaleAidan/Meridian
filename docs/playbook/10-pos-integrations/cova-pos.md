# Cova

> Status: **WAVE 1 BUILDING** + partner intake this week — **Canada cannabis #1 wedge**
> Category: cannabis (dispensary)
> Auth: Header-based auth (Authorization header)

## What you tell the merchant

"Cova is our #1 Canadian cannabis integration — partner intake filed this week, building now. You'll connect with API credentials from your Cova admin. Expected live within 30–45 days. We've designed the cannabis workflow with PII handling and provincial compliance baked in."

## How the merchant connects (when live)

1. Meridian rep initiates connection from the merchant's Cova-enabled account
2. Merchant authorizes Meridian's OAuth client in the Cova back-office
3. iQmetrix's accounts service (`https://accounts.iqmetrix.net/v1/oauth2/token`) redirects with `code` → Meridian exchanges for access + refresh tokens
4. Meridian calls **CompanyTree** to enumerate the merchant's locations, stores location IDs
5. Backfill begins per location against `SalesInvoice` (`https://api.covasoft.net/pointofsale/...`)

Typical time to connect (projected): **3 minutes** once partnered.

**Partner program required:** apply via `https://www.covasoftware.com/partner-inquiry` (inquiry form, no self-service). Production OAuth credentials are gated; "Featured" and "Bundled" partner tiers exist. Expect **4–8 weeks** relationship build. Cova publishes a Postman collection (`COVA_API_Collection_for_Integrators.json`) on the documentation portal — use for shape validation before partnership lands.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Sales invoices | hourly poll | 18 months |
| Catalog products | daily | full history |
| Employees | daily | full history |
| Customers (patients) | daily | full history (PII-protected) |

Endpoint reference: `https://api.covasoftware.com/v1`

## What features they get (when live)

Cannabis-tuned suite:

- Money Left on Table
- Product Velocity (especially valuable — fast inventory turn in cannabis)
- Inventory Intelligence (reorder timing, batch tracking)
- Customer LTV (patient retention is the cannabis margin lever)
- Revenue trend + forecasting
- Promo/discount ROI
- Day-of-week / time-of-day patterns (cannabis traffic is heavily time-skewed)

## What features they DON'T get

- Order creation (`supports_orders: False`) — analytics-only
- Cross-border or US compliance — Cova is Canada-focused

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 on all calls | Using static API key against Cova's OAuth endpoint | Mint Bearer token from the iQmetrix accounts service (`accounts.iqmetrix.net/v1/oauth2/token`); static API keys don't work |
| 404 on `/sales/invoices` | Stale registry path | Target `https://api.covasoft.net/pointofsale/...` (Cova splits services across subpaths: `pointofsale`, `productlibrary`, CRM, CompanyTree) |
| Merchant on Cova but no Canadian provincial board data flowing | Cova reports to AGLC/OCS/BCLDB internally; not all of that is exposed via API | Scope analytics promises to in-Cova data only |
| Auth rejected | Wrong scope on Cova credential | Cova partner intake clarifies scopes during approval |
| Missing batch IDs | Cova batch tracking module not on | Falls back to SKU-level (still useful) |

## Sales angle

**Opener (Canada):** "You're on Cova in Canada — you're our #1 priority cannabis integration. Provincial regulators want clean data; your patients want consistent product availability. We give you both, plus the margin insights nobody else surfaces."

**Why Cova is the wedge:**
- **~70% of Canadian legal brick-and-mortar dispensaries** run on Cova; 52% of Alberta stores, 50%+ of BC stores
- Handles provincial compliance reporting (AGLC Alberta, OCS Ontario, BCLDB British Columbia, SQDC adjacency in Quebec) — owning Cova effectively unlocks the entire Canadian cannabis vertical for Meridian
- Cannabis margins are tight → analytics ROI is obvious
- Founded in Regina SK; HQ Vancouver BC + Denver CO. Also serves NY, NJ, MI, IL, NM, MN, MS in the US — but US-side, Dutchie + Flowhub matter more

**Frame Cova as the Canada wedge, Dutchie as the US-cannabis wedge.** Pair this with the Canada portal's province-aware compliance positioning.

**Operator tells:** iPad or Windows till, back-office login at `*.covasoft.net` or "Cova Cloud", "Cova Pay" branded payment terminals, "Cova handles our AGLC/OCS/BCLDB reporting," "our budtenders use Cova."

**Cannabis-specific compliance you must mention:**
- Separate banking + insurance posture (federal Schedule I in US contexts)
- PII handling per provincial rules
- Marketing channels: direct, event, WOM only (Google/Facebook/LinkedIn restrict cannabis ads)

## What blocks live status today

- **No partner program approval / production OAuth client** (intake filed; 4–8 week build expected)
- **Registry `base_url` and `auth_type` are wrong** — point to non-Cova host `api.covasoftware.com/v1` with static header auth; real host is `https://api.covasoft.net/<service>` with OAuth tokens minted from `accounts.iqmetrix.net/v1/oauth2/token`
- **No CompanyTree location-discovery step** in connector
- **No OAuth refresh handling** in connector base
- **`data_key: "data"` likely wrong** — iQmetrix responses vary per service
- **Cannabis vertical compliance review** (separate banking/insurance, PII storage) — coordinating with ops
- Estimated effort to LIVE: **1+ month** (partner approval is the long pole, plus registry rewrite + multi-service base-URL handling)

## Reference docs

- Live Cova API portal: https://api.covasoft.net/Documentation
- Partner inquiry form: https://www.covasoftware.com/partner-inquiry
- Partners page: https://www.covasoftware.com/partners
- Canada retail suite: https://www.covasoftware.com/cannabis-retail-suite-canada
- Alberta market share (52%): https://www.covasoftware.com/pos/alberta
- BC market share (50%+): https://www.covasoftware.com/pos/bc
- BetaKit on ~70% Canadian share + Regina founding: https://betakit.com/saskatchewan-startup-beats-out-shopify-as-pos-behind-cannabis-retailers/

---

_Last updated: 2026-05-31 (enhanced with Phase 1 research)_
_Sourced from: src/services/pos_connectors/registry.py (cova-pos config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #12, Cannabis vertical greenlit, Wave 2 partner table) + docs/playbook/_status/pos/cova-pos.md (Phase 1)_
