# BLAZE POS

**Registry key:** `blaze-pos` — see `src/services/pos_connectors/registry.py` (line 847)

> Config disambiguation: registry has `base_url: https://api.blaze.me/api/v1` with a single `Authorization` header. Live BLAZE Partner API docs at `apidocs.blaze.me/intro` show the actual host is `https://api.partners.blaze.me` and auth requires **two** headers: `x-api-key` (Partner Key) **plus** `Authorization` (Developer Key). Registry config will 404 / 401 until rewritten.

## Status
NEEDS PARTNERSHIP — production keys are gated behind the BLAZE Partner Network (BPN) Third-Party Integration intake, and the current connector config has the wrong host and a single-header auth scheme.

## What it is
Cloud cannabis dispensary POS + inventory + ecommerce suite for licensed retailers — covers in-store checkout, METRC/state compliance, online menus, loyalty, and delivery.

## Vertical & market
- **Primary vertical:** Cannabis dispensary (also markets to vape, CBD, and liquor)
- **Estimated NA market presence:** Mid-tier; strong California footprint with expansion into other regulated US states
- **Typical merchant profile:** Single-state operator or small MSO, often California-rooted, frequently bundled with BLAZE's online menu and delivery tooling
- **Geographic concentration:** US (California-heavy) with growth into other state-legal markets

## How to spot the merchant uses it
- Budtender ringing up sales on iPad with the "BLAZE Retail" app, label printer for METRC tags
- Online menu / order-ahead branded or footer-credited to BLAZE
- Back-office login at `*.blaze.me` / "BLAZE Cloud"
- Conversational tells: "we're on BLAZE," "our BLAZE rep set up the online menu"

## Auth method
API key — **two headers required** on every request: `x-api-key: <Partner Key>` + `Authorization: <Developer Key>`. The Partner Key is issued to Meridian as a vendor; each merchant connection additionally combines that key with the retailer's dispensary key to unlock data for that store.

## Data we can pull (per live Partner API surface)
| Type | Available | Endpoint family | Notes |
|------|-----------|-----------------|-------|
| Orders / transactions | yes | Orders & Payments (Transactions, Payments, ACH) | Registry path `/partner/transactions` unverified vs live spec |
| Catalog / items | yes | Catalog (Brands, Categories, Products) | Registry path `/partner/products` unverified |
| Customers | yes | Memberships | Registry path `/partner/members` unverified |
| Employees | not configured | Store & Operations (Employees) | Available on Partner API; add to registry |
| Inventory | not configured | Inventory (Batches, Order Quantity, Store Inventory) | Cannabis-critical — must add |
| Refunds | not configured | Via Transactions | Confirm during smoke test |
| Webhooks | yes (per docs) | Webhooks resource | Real-time event stream available |

## Partner program / access requirements
- **Partner program required:** Yes — BLAZE Partner Network (BPN), Third-Party Integration tier
- **Sign-up URL:** `https://www.blaze.me/bpn/` (Partner API Request Form, ~4 min to submit)
- **Approval timeline:** Not published; expect vendor review + document signing before any key is issued (assume multi-week)
- **Cost / revenue share:** Fee disclosed as "associated cost" but amount not public; referral commissions available on a separate tier

## Sandbox / test environment
- **Available:** Yes — approved partners receive a Partner Key plus a staging account to develop against before touching production
- **URL:** Issued post-approval, not public
- **Notes:** No public Postman / OpenAPI bundle linked from the intro page; rely on the docs portal once partner credentials land

## Rate limits
Not documented on the public intro page. Assume conservative throttling until confirmed with the BPN team.

## Webhook / sync model
Hybrid — Partner API documents a Webhooks resource for real-time events; pair with polled backfill for history and reconciliation.

## Connect flow (what the merchant does)
1. Meridian must already be an approved BPN Third-Party Integration partner (Partner Key in hand)
2. Merchant generates / shares their dispensary key from BLAZE back-office
3. Merchant pastes dispensary key into Meridian connect screen
4. Meridian calls `/partner/store` (or live equivalent) with both headers to verify the key pair
5. Backfill begins against Transactions; webhooks subscribed for ongoing sync

## Estimated effort to go LIVE
L (1+ months). Drivers: BPN approval cycle, registry rewrite (host + dual-header auth + endpoint validation), webhook handler, cannabis compliance posture on Meridian side.

## What blocks LIVE status today
- Not an approved BPN partner; no Partner Key
- Registry `base_url` (`api.blaze.me/api/v1`) is wrong — should be `api.partners.blaze.me`
- Registry auth model assumes a single `Authorization` header; live API requires `x-api-key` + `Authorization` together (connector base does not currently support dual-header schemes)
- Endpoint paths (`/partner/store`, `/partner/transactions`, `/partner/products`, `/partner/members`) and `data_key: "values"` are unvalidated against the live spec
- Inventory + employees endpoints not in registry — both are needed for cannabis vertical

## Common failure modes (for troubleshooting playbook)
- **Symptom:** 401 on every call → **Cause:** sending only one of the two required headers → **Fix:** send `x-api-key` (Partner Key) AND `Authorization` (Developer Key) on every request
- **Symptom:** DNS / 404 on all calls → **Cause:** stale `api.blaze.me/api/v1` host → **Fix:** repoint base to `https://api.partners.blaze.me`
- **Symptom:** Auth works but no data returned → **Cause:** Partner Key not paired with that merchant's dispensary key → **Fix:** confirm merchant has authorized Meridian's partner key for their store

## Strategic notes
BLAZE is a **California-first mid-tier cannabis play** — meaningful share in the largest US legal market, but smaller national footprint than Dutchie and less Canadian relevance than Cova. Treat as a complementary win once the cannabis vertical is committed: Cova for Canada, Dutchie for US national, BLAZE for California depth and merchants who want BLAZE's online-menu / delivery stack as well as analytics. BPN explicitly states "integrations requiring more than API access face lower approval odds" — keep the Meridian pitch read-only and analytics-focused to maximize approval probability.

## Recommendation
DEFER — unless cannabis is committed as a named Meridian vertical; then pursue **after** Cova (Canada) and Dutchie (US) partner intakes are in motion.

**Reasoning:** Cannabis-only POS with a real partner gate, real config debt (wrong host, wrong auth model, unvalidated paths), and a market position that ranks behind Dutchie/Cova for share. Worth the BPN form when the cannabis go-to-market is funded; not worth the rewrite as a one-off.

## Sources consulted
- https://apidocs.blaze.me/intro (Partner API base URL + dual-header auth, accessed)
- https://www.blaze.me/bpn/ (BPN intake, partnership tiers, accessed)
- https://www.blaze.me/partners/ (partner program landing)
- https://www.blaze.me/products/retail/open-api-docs/ (retail product Open API marketing page)
- https://www.blaze.me/dispensary-pos-software/ (vertical positioning)
- Registry config: `src/services/pos_connectors/registry.py` (line 847)
- Live API docs accessed: Yes (intro page); deeper endpoint spec gated behind partner login
