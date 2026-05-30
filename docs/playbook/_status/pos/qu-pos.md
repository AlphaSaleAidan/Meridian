# Qu POS (Qu Beyond)

**Registry key:** `qu-pos` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP — and current registry config likely has wrong `base_url` + wrong auth type.

## What it is
Enterprise "Intelligent Commerce Platform" (POS + kitchen + omnichannel) for multi-unit QSR and fast-casual restaurant chains. Marketed as "beyond traditional POS."

## Vertical & market
- **Primary vertical:** restaurant (QSR / fast-casual, enterprise tier)
- **Estimated NA market presence:** Medium in enterprise QSR, near-zero in SMB
- **Typical merchant profile:** multi-unit chain / franchise (named customers include Jack in the Box, Shake Shack, Dave's Hot Chicken, Blaze Pizza, Taco John's, GoTo Foods)
- **Geographic concentration:** US-centric

## How to spot the merchant uses it
- Operator talks about "Qu" or "Qu Beyond" by name (it's a CTO/IT-led purchase, not a counter-staff brand)
- Chain with 20+ units, especially QSR with drive-thru and digital ordering tightly integrated
- Mentions "single menu management" across channels
- Almost never on a single independent restaurant — if a rep hears "Qu" from a one-off owner, double-check; they probably mean something else

## Auth method
API key in header (`APIKey: <string>`) per public Data Access API docs — **not** bearer as currently configured in the registry.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | ? | `/orders` (config) | Public docs describe order *ingestion* (3rd-party → Qu), not pull; needs partner validation |
| Catalog / items | ? | `/menu/items` (config) | Real path style is `/api/v3/customers/{id}/locations/{id}/...` |
| Customers | ? | `/customers` (config) | "Customer" in Qu = the enterprise account, not the diner |
| Employees | ? | `/employees` (config) | Unverified against live docs |
| Inventory | ✗ | — | Not configured |
| Refunds | ✗ | — | Not configured |

## Partner program / access requirements
- **Partner program required:** Yes
- **Sign-up URL:** https://www.qubeyond.com/partner-ecosystem/ (contact form — no self-service)
- **Approval timeline:** Enterprise sales cycle — partner approval gated through Qu BD, no public timeline
- **Cost / revenue share:** Unknown / not published

## Sandbox / test environment
- **Available:** Yes (referenced as `dev-data-access-api.azurewebsites.net` in public docs)
- **URL:** issued post-partnership; not self-serve
- **Notes:** API keys provisioned per integration partner

## Rate limits
Unknown — not publicly documented.

## Webhook / sync model
Pull-based ingestion for 3rd-party orders (vendor posts orders → in-store POS pulls them). No public webhook catalog. Treat as poll/push-in until partner docs confirm.

## Connect flow (what the merchant does)
1. Merchant's corporate IT/CTO approves integration (not a store-level decision)
2. Qu BD issues integration agreement with Meridian
3. Qu provisions tenant API key scoped to the chain's `Customer` and `Location` IDs
4. Meridian stores key per merchant and queries `/api/v3/customers/{customerId}/locations/{locationId}/...`

## Estimated effort to go LIVE (config → production-ready)
XL — custom partnership required. Plus M-level config fix (base URL, auth header, path template with customer/location IDs) before any wire-up.

## What blocks LIVE status today
- No partnership with Qu Beyond
- Registry `base_url` (`https://api.qupos.com/v2`) does not match the documented host (`qu-api.qubeyond.com` / Data Access API on `/api/v3`) — needs verification with Qu before any build
- Registry `auth_type: bearer` conflicts with documented `APIKey` header scheme
- Endpoint paths in registry are flat (`/orders`, `/menu/items`) but real API is nested under customer + location IDs
- No customer-facing OAuth/connect UI (and there won't be one — this is B2B key provisioning)

## Common failure modes (for troubleshooting playbook)
- **Symptom:** 404 from `api.qupos.com` → **Likely cause:** stale/wrong host in registry → **Fix:** confirm correct host with Qu partner team before debugging further
- **Symptom:** 401 with bearer token → **Likely cause:** API expects `APIKey` header, not `Authorization: Bearer` → **Fix:** update connector auth
- **Symptom:** rep insists a single-location restaurant "has Qu" → **Likely cause:** brand confusion → **Fix:** ask for corporate parent / chain name

## Strategic notes
Qu is a top-down enterprise sell. The decision-maker is a chain CTO or VP of Digital, not a store owner — completely outside Meridian's current SMB rep motion. Any Qu deal is one-off, contract-led, and would unlock 20–500+ locations at once if won. Pursue only if (a) a specific Qu chain shows interest in Meridian analytics, or (b) Meridian moves into enterprise sales.

## Recommendation
DEFER

**Reasoning:** Wrong fit for SMB rep playbook — no self-service path, no public sandbox, and current registry config can't actually connect. Revisit only when an enterprise prospect or partner intro materializes; until then, do not pitch.

## Sources consulted
- https://www.qubeyond.com/
- https://www.qubeyond.com/partner-ecosystem/
- https://www.qubeyond.com/restaurant-apis-architecture-notall-are-created-equal/
- https://qu-api.qubeyond.com/ (referenced; cert/host issues fetching directly)
- https://status.qubeyond.com/
- Live API docs accessed: Partial — public summaries only; full docs partner-gated
