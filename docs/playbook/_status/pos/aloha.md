# Aloha POS (NCR Voyix)

**Registry key:** `aloha` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP

## What it is
Aloha is NCR Voyix's flagship enterprise restaurant POS, dominant in mid-market and large chain table-service and quick-service restaurants. (NCR spun off the Voyix retail/restaurant business in October 2023; "NCR Voyix" now owns Aloha.)

## Vertical & market
- **Primary vertical:** restaurant (table service + QSR)
- **Estimated NA market presence:** Dominant in chains/franchises (100k+ restaurant locations globally)
- **Typical merchant profile:** multi-unit franchises and enterprise chains (5+ locations), rarely independent SMB
- **Geographic concentration:** US-led, global footprint

## How to spot the merchant uses it
- Radiant/NCR-branded terminals with the "Aloha" boot screen or back-office shortcut
- Back-office tools labeled "Aloha Manager," "Aloha Configuration Center (CFC)," or "Aloha Web Admin"
- Receipt footers / KDS branding referencing "Aloha" or "NCR"
- Conversational tells: "we're on Aloha," "our CFC," "the BOH"

## Auth method
API key in `X-Api-Key` header **plus** `nep-organization` header carrying the merchant's NEP Organization ID. Issued by NCR Voyix after partner onboarding — not self-service.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | configured | `/orders` | `supports_orders: False` — read only |
| Catalog / items | configured | `/items` | |
| Customers | not configured | — | |
| Employees | configured | `/employees` | |
| Inventory | not configured | — | |
| Refunds | not configured | — | inside orders payload |

Base URL: `https://api.ncr.com/asr/v2` (ASR = Aloha Sales & Reporting family).

## Partner program / access requirements
- **Partner program required:** Yes (NCR Voyix Developer / Partner Program)
- **Sign-up URL:** https://developer.ncrvoyix.com/
- **Approval timeline:** Enterprise sales cycle (weeks to months); requires signed partner agreement before production keys are issued
- **Cost / revenue share:** Not publicly disclosed — negotiated per partner; expect paid add-ons and possible per-location fees

## Sandbox / test environment
- **Available:** Yes, via the NCR Voyix Developer Portal API Explorer
- **URL:** https://developer.ncrvoyix.com/portals/dev-portal/api-explorer
- **Notes:** Sandbox keys are scoped to demo orgs; merchant-specific production access requires the merchant's own NEP Organization ID

## Rate limits
Not publicly documented. NCR positions the platform as "tuned for enterprise throughput" — assume per-org throttling, validate during partner onboarding.

## Webhook / sync model
Poll-only for the endpoints we use (`/sites`, `/orders`, `/items`, `/employees`). Event streaming exists elsewhere in the Voyix platform but is not in our current connector.

## Connect flow (what the merchant does)
1. Merchant confirms their **NEP Organization ID** in Aloha Web Admin (same org name they use to log in to the NCR portal)
2. Merchant's NCR account rep grants Meridian's partner app access to that organization
3. NCR issues an `X-Api-Key` scoped to that org
4. Rep enters the API key + NEP Org ID into Meridian's connector settings
5. Meridian calls `/sites` to validate, then begins polling orders/items/employees

## Estimated effort to go LIVE (config → production-ready)
XL — partner agreement + per-merchant onboarding gate every install

## What blocks LIVE status today
- No signed NCR Voyix partner agreement on file
- No customer-facing UI to capture `X-Api-Key` + `nep-organization` pair
- Connector is poll-only; no validation against a real production org yet
- `data_key: "items"` is generic and likely wrong for `/orders` and `/employees` — needs per-endpoint shape mapping after live API testing

## Common failure modes (for troubleshooting playbook)
- **Symptom:** 401 / 403 on `/sites` → **Likely cause:** missing or mismatched `nep-organization` header → **Fix:** confirm merchant's NEP Org ID in Web Admin matches the header value exactly
- **Symptom:** 404 on every endpoint → **Likely cause:** wrong API family (Aloha has ASR, Aloha Cloud, and Digital Ordering APIs on different base URLs) → **Fix:** confirm merchant is on Aloha Enterprise (ASR) vs. Aloha Cloud
- **Symptom:** Key works in sandbox, fails in prod → **Likely cause:** prod key not yet provisioned for that org → **Fix:** open ticket with NCR partner manager

## Strategic notes
Aloha is the highest-value restaurant POS for Meridian by revenue-per-merchant (chains run 5–500 locations each), but the lowest-velocity by deal cycle. Going after Aloha means hiring or contracting an enterprise rep motion: RFPs, security reviews, MSAs, paid integration fees. Indie restaurants on Aloha are rare — if a single-location prospect says "Aloha," double-check; they may be on Aloha Cloud (a different SKU) or Toast.

## Recommendation
DEFER

**Reasoning:** Partnership is gated by NCR Voyix enterprise sales, not self-service, and our config is unvalidated against a live org. Pursue only when (a) we have a named enterprise-chain prospect willing to sponsor the partner agreement, or (b) we hire a dedicated mid-market/enterprise rep. Until then, route Aloha inbound to a waitlist and focus on Toast/Square/Clover where deals close in days.

## Sources consulted
- https://docs.ncrvoyix.com/restaurant/aloha-pos/about/overview
- https://docs.ncrvoyix.com/restaurant/digital-ordering/integrating/digital_ordering_and_cm/associating_bsp_organization_name
- https://developer.ncrvoyix.com/portals/dev-portal/api-explorer
- https://apitracker.io/a/ncr-aloha
- Live API docs accessed: Partial (overview + NEP org confirmed; full auth spec gated behind partner portal)
