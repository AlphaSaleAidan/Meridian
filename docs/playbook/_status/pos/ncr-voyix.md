# NCR Voyix Commerce Platform

**Registry key:** `ncr-voyix` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP

## What it is
The NCR Voyix Commerce Platform (also called NEP — NCR Enterprise Platform) is the unified cloud API gateway that NCR Voyix spun off from NCR Corporation in October 2023. It sits in front of NCR's restaurant, retail, and convenience/fuel POS estates and is the API umbrella under which Aloha and the rest of NCR's commerce products are exposed.

## Vertical & market
- **Primary vertical:** multi-vertical (restaurant chains, grocery / drug / mass-merch retail, convenience & fuel)
- **Estimated NA market presence:** Large — NCR Voyix publicly cites ~110B API calls/year across its platform
- **Typical merchant profile:** enterprise and upper mid-market chains (rarely independent SMB)
- **Geographic concentration:** US-led, global footprint

## How to spot the merchant uses it
- Merchant is on Aloha, NCR Counterpoint, NCR Silver, or NCR convenience/fuel back-office (any of these route through Voyix gateways)
- Back-office logins on `*.ncrcloud.com` or `*.ncrvoyix.com`
- IT/ops team references an "NEP Organization ID" or "Org ID"
- Conversational tells: "we're on the NCR platform," "our NEP org"

## Auth method
OAuth 2.0 **client_credentials** against `https://gateway.ncrcloud.com/security/authentication/login`, plus a per-tenant `nep-organization` header on every API call. Client credentials are issued only after partner onboarding — not self-service.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | configured | `/transaction-document/transaction-documents/find-by-criteria` | `supports_orders: False` — read only |
| Catalog / items | configured | `/catalog/items/find-by-criteria` | |
| Customers | not configured | — | available on platform, not wired |
| Employees | not configured | — | |
| Inventory | not configured | — | available on platform, not wired |
| Refunds | not configured | — | inside transaction-document payload |

Base URL: `https://gateway.ncrcloud.com`. Response envelope keyed under `pageContent`.

## Partner program / access requirements
- **Partner program required:** Yes (NCR Voyix Developer / Partner Program)
- **Sign-up URL:** https://developer.ncrvoyix.com/
- **Approval timeline:** Enterprise sales cycle (weeks to months); signed partner agreement required before production credentials
- **Cost / revenue share:** Not publicly disclosed — negotiated per partner

## Sandbox / test environment
- **Available:** Yes, via NCR Voyix Developer Portal API Explorer
- **URL:** https://developer.ncrvoyix.com/portals/dev-portal/api-explorer
- **Notes:** Sandbox creds are scoped to demo orgs; per-merchant production access requires that merchant's own NEP Org ID and explicit grant

## Rate limits
Not publicly documented. NCR positions the platform for enterprise throughput; expect per-org throttling validated during onboarding.

## Webhook / sync model
Poll-only for the endpoints we use (`find-by-criteria` pattern). Event streaming exists elsewhere on the platform but is not wired into our connector.

## Connect flow (what the merchant does)
1. Merchant confirms their **NEP Organization ID** with their NCR account rep
2. NCR rep grants Meridian's partner app access to that org
3. NCR issues OAuth client credentials scoped to the org
4. Rep enters client ID + secret + NEP Org ID into Meridian's connector settings
5. Meridian POSTs to `/security/authentication/login`, then calls `/site/sites/find-by-criteria` to validate, then begins polling transactions and catalog

## Estimated effort to go LIVE (config → production-ready)
XL — partner agreement + per-merchant onboarding gate every install

## What blocks LIVE status today
- No signed NCR Voyix partner agreement on file
- No customer-facing UI to capture client_id / secret / NEP Org ID
- Connector unvalidated against a live production org
- Overlap with the `aloha` entry needs a routing decision: Voyix gateway can serve Aloha tenants too, but the existing `aloha` config targets a different base URL (`api.ncr.com/asr/v2`)

## Common failure modes (for troubleshooting playbook)
- **Symptom:** 401 on every call → **Likely cause:** missing or mismatched `nep-organization` header → **Fix:** confirm Org ID with NCR rep, header value must match exactly
- **Symptom:** Token endpoint returns 403 → **Likely cause:** client credentials not yet provisioned for that org → **Fix:** open ticket with NCR partner manager
- **Symptom:** 404 on `find-by-criteria` paths → **Likely cause:** merchant is on a product not exposed through NEP gateway (e.g., legacy on-prem Aloha) → **Fix:** confirm the merchant's product is NEP-enabled before promising integration

## Strategic notes
Voyix is the platform; Aloha, Counterpoint, Silver, and the convenience/fuel POSes are products on it. The separate `aloha` entry in our registry hits an older Aloha-specific API family (`api.ncr.com/asr/v2`); this `ncr-voyix` entry is the modern gateway path and is the right target for any new enterprise integration work. Do not pitch both in parallel to the same prospect — pick one based on which API family their NCR rep enables. Single-location prospects who say "NCR" almost always mean Aloha Cloud or NCR Silver and should be routed accordingly, not to the enterprise Voyix path.

## Recommendation
DEFER

**Reasoning:** Enterprise-only, partner-gated, and our connector is unvalidated against a live org. Pursue only when a named enterprise chain prospect will sponsor the partner agreement, or when we hire a dedicated mid-market/enterprise rep. Until then, route Voyix-platform inbound to a waitlist alongside Aloha.

## Sources consulted
- https://www.ncrvoyix.com/ (verticals, product lines, scale)
- https://developer.ncrvoyix.com/ (developer portal, partner program landing)
- https://docs.ncrvoyix.com/ (product documentation index)
- `src/services/pos_connectors/registry.py` (verified base_url, token_url, headers, endpoints)
- Existing `aloha.md` entry (cross-reference for partner program mechanics)
- Live API docs accessed: Partial (gateway hostname + auth path + nep-organization header verified from registry; full OAuth spec gated behind partner portal)
