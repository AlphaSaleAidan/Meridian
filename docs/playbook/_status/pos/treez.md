# Treez

**Registry key:** `treez` — see `src/services/pos_connectors/registry.py`

## Status
**NEEDS PARTNERSHIP** — config seeded (base URL, endpoints, auth class) but Treez gates production keys behind partner application + integration certification. No customer-facing connect flow built.

## What it is
Cloud cannabis dispensary POS for state-regulated retail: POS, inventory, metrc compliance, TreezPay (PIN debit/ACH), ecommerce, loyalty.

## Vertical & market
- **Primary vertical:** cannabis dispensary (state-regulated retail)
- **NA market presence:** Large — Treez cites ~30% of California cannabis sales running through its platform; widely cited as #2 US dispensary POS after Dutchie
- **Typical merchant profile:** single and multi-location dispensaries; MSOs
- **Geographic concentration:** US-only (federally illegal — no Canada/intl); California-heavy, expanding to AZ, CO, IL, MA, MI, MN, MS, MO, NV, NJ, ME

## How to spot the merchant uses it
- Budtender terminals branded Treez; checkout shows metrc compliance fields inline
- "Powered by Treez" on dispensary ecommerce / order-ahead menus
- TreezPay pinpads at checkout
- Operator says "Treez" or "SWIFTER" (their checkout UI)

## Auth method
**Signed JWT bearer (RSA).** Integrator generates an RSA key pair, Treez registers the public key, every call must include a freshly signed JWT in `Authorization: Bearer <jwt>` with a **30-second TTL**. One integrator credential scopes to many `{dispensary_id}` tenants — no per-store key. Registry's `auth_type: "bearer"` is directionally correct but `rest_connector.py` needs a JWT-signer before this works in prod.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Config only | `/tickets` | No live sync wired |
| Catalog | Config only | `/products` | |
| Customers | Config only | `/customers` | Patient/member PII — regulated |
| Employees | Config only | `/budtenders` | Budtender-level analytics |
| Inventory | Not configured | `/stock/getStock` per docs | Add if compliance is on roadmap |
| Refunds | Not configured | Inside tickets (assumed) | Validate post-partnership |

`supports_orders: False` — pull-only.

## Partner program / access requirements
- **Required:** Yes, mandatory. Prod keys only after Treez certifies the integration.
- **Sign-up:** https://treez.io/partner-application (program: https://www.treez.io/partners, docs: https://code.treez.io/)
- **Timeline:** Not published. Plan 6+ weeks (application → review → certification → prod keys).
- **Cost:** No partner fee disclosed. $1,500/converted-lead referral fee; no integrator rev-share published.

## Sandbox / test environment
Yes — issued during certification per Getting Started docs; URL not public, provisioned by Treez partner team. Public-key registration happens here before prod cutover.

## Rate limits
**Not publicly documented.** Confirm during onboarding; plan exponential backoff.

## Webhook / sync model
**Poll-only assumed.** No public generic-event webhooks. Cadence comparable to Toast: 30-min incremental, multi-month backfill.

## Connect flow (what the merchant does)
*Hypothetical until certified:*
1. Meridian completes partner app + certification, receives prod credentials
2. Dispensary owner asks Treez to enable Meridian for their `dispensary_id` (Treez-side admin, not self-serve)
3. Treez confirms; integrator JWT starts working for that tenant
4. Merchant returns to Meridian, confirms dispensary, backfill begins

## Estimated effort to go LIVE
**L (1+ months calendar).** Engineering ~1 week (JWT signer, key storage, sync_engine wiring, mappers). Blocker is the 6+ week partner cycle.

## What blocks LIVE status today
- No Treez partner application submitted
- `rest_connector.py` assumes static bearer — no RSA JWT signer
- No `treez/` module (client, mappers, sync_engine) — registry stub only
- No connect UI for cannabis vertical; no compliance review of pulling patient PII

## Common failure modes
- **401 on every call** → JWT expired (30s TTL) or clock skew → sign per-request, verify NTP
- **403 on a specific dispensary** → integrator key not scoped to that `dispensary_id` → ask Treez partner support to add the tenant
- **Empty `/tickets` despite live sales** → wrong dispensary UUID (org vs location) → validate against Treez admin

## Strategic notes
Treez + Dutchie cover ~70%+ of US dispensaries — if Meridian commits to cannabis, this is integration #2, not optional. But cannabis is a deliberate vertical decision: federal banking restrictions mean dispensaries can't use Stripe; customer data is regulated patient/member PII; SaaS vendors serving cannabis often need separate banking and insurance. Pursue as part of a "Meridian for Cannabis" GTM with Dutchie alongside, not a one-off.

## Recommendation
**WAIT** — keep the registry stub, don't file the partner app until leadership greenlights cannabis as a target vertical.

**Reasoning:** Config is seeded so we can move fast if approved, but JWT auth work + partner app burns weeks that only pay off if we also pursue Dutchie and accept the cannabis compliance overhead.

## Sources consulted
- https://code.treez.io/ (API docs landing)
- https://code.treez.io/reference/authentication (RSA JWT, 30s TTL — via search excerpt; site 403s WebFetch)
- https://code.treez.io/docs/getting-started (partner + certification gate — via search excerpt)
- https://www.treez.io/partners, https://treez.io/partner-application (program, referral fee)
- https://www.treez.io/about-treez (CA volume, state footprint)
- `/root/Meridian/src/services/pos_connectors/registry.py` (`treez` entry, lines 811–822)
- Live API docs accessed: Partial — landing pages fetched; reference pages 403 to WebFetch, content from search excerpts
