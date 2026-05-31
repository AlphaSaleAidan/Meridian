# Oracle Simphony

**Registry key:** `simphony` — see `src/services/pos_connectors/registry.py` (line 875). Sibling entry `micros.md` covers both Oracle products jointly (shared `base_url` / `token_url`); this entry focuses on Simphony-specific details. Read `micros.md` first for partnership, auth, and ROI context.

## Status
NEEDS PARTNERSHIP + OUTDATED CONFIG.

Registry lists `auth_type: oauth_client_credentials`, but live Simphony Transaction Services Gen2 docs describe OAuth 2.0 **Authorization Code + PKCE**. Config also distinct from `micros` in transactions endpoint: Simphony uses `/checks`, MICROS uses `/transactions`.

## What it is
Oracle's modern cloud restaurant POS — the strategic successor to legacy on-prem MICROS, delivered as Simphony Cloud (Essentials, Standard, Premium, Enterprise tiers). Runs on Oracle-branded workstations and tablets with a central Enterprise Management Console.

## Vertical & market
- **Primary vertical:** restaurant / hospitality / gaming / stadium concessions
- **Estimated NA market presence:** Dominant in enterprise hospitality; growing in upper-mid-market chains migrating off MICROS RES 3700
- **Typical merchant profile:** hotel F&B operator, casino, theme park, 25+ unit chain that has already cloud-migrated
- **Geographic concentration:** Global

## How to spot the merchant uses it
- Login URL contains `simphony` subdomain or `oracleindustry.com`
- Manager mentions "Reporting and Analytics" (R&A) — the Simphony back-office portal
- Oracle Workstation 6 / 625 / Express Station hardware running cloud-tier UI (vs. MICROS RES on legacy WS5)
- Conversational tell: "we're on Simphony Cloud" / "we migrated off RES" / references to "EMC" (Enterprise Management Console)
- Receipt footer may show property/enterprise name configured in R&A

## Auth method
OAuth 2.0 **Authorization Code + PKCE** via Simphony Transaction Services Gen2. Signin requires `orgname` (organization short name). Registry's `oauth_client_credentials` flow is incorrect for this product and must be rewritten.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | YES | `/organizations/{org_id}/checks` | Simphony uses "checks" (vs. MICROS "transactions") |
| Catalog / items | YES | `/organizations/{org_id}/menu-items` | |
| Employees | YES | `/organizations/{org_id}/employees` | |
| Customers | NO | — | Not in current config |
| Inventory | NO | — | Separate Oracle Inventory Management module |
| Refunds | UNKNOWN | — | Not validated against live API |
| Order creation | NO | — | `supports_orders: False` in registry |

## Partner program / access requirements
See `micros.md`. Same Oracle PartnerNetwork (OPN) + Simphony Integrations Program gate applies. Simphony Lab sandbox is the cloud-tier test environment provisioned post-approval.

## Sandbox / test environment
- **Available:** Yes — Simphony Lab (free to approved ISV partners)
- **URL:** Provisioned post-approval, not public
- **Notes:** Cloud-only, no on-prem variant needed (unlike MICROS RES)

## Rate limits
Not publicly documented.

## Webhook / sync model
Poll-only per current registry config. Gen2 cloud APIs offer event streaming capabilities not yet wired up here.

## Connect flow (what the merchant does)
Not applicable until partnership exists. Post-approval, a Simphony admin would: (1) log in to Reporting and Analytics, (2) add a Transaction Services Gen2 API account, (3) select Client Scope (BOTH/LOCAL/CLOUD — Simphony Cloud merchants typically choose CLOUD), (4) select Authorization Scope, (5) share Client ID with Meridian, (6) complete PKCE signin with `orgname`.

## Estimated effort to go LIVE
XL — same partnership gate as MICROS, plus connector rewrite (PKCE flow, refresh-token rotation, correct `/checks` pagination).

## What blocks LIVE status today
- No Oracle PartnerNetwork enrollment
- No Simphony Integrations Program acceptance
- Registry `auth_type` is `oauth_client_credentials` — wrong flow for Simphony Gen2
- No customer-facing OAuth UI for PKCE
- No Simphony Lab credentials to validate `/checks` endpoint shape

## Common failure modes
- **Symptom:** 401 on token endpoint → **Likely cause:** registry uses client_credentials grant → **Fix:** rebuild connector for Authorization Code + PKCE
- **Symptom:** Empty result from `/checks` → **Likely cause:** Client Scope set to LOCAL but querying cloud tenant → **Fix:** confirm CLOUD or BOTH scope on API account
- **Symptom:** 404 on `/organizations/{org_id}/...` → **Likely cause:** `org_id` vs. `orgname` mismatch → **Fix:** use organization short name from signin context

## Strategic notes
Simphony is the forward-looking Oracle product — every new Oracle hospitality deal lands here, not on legacy MICROS RES. If Meridian ever pursues hospitality enterprise, Simphony is the right target (cleaner Gen2 APIs, cloud-native, more predictable schema than MICROS RES exports). But the partnership economics are identical to MICROS: 3–9 month sales cycle, OPN gating, Marketplace listing required. SMB rep motion does not encounter Simphony customers.

## Recommendation
DEFER.

**Reasoning:** Same Oracle partnership economics as MICROS make this wrong-ICP for current rep motion. Prioritize Simphony over MICROS only when revisiting — it is the strategic Oracle product and has the cleaner API surface, so any future enterprise pipeline investment should target Simphony first.

## Sources consulted
- `src/services/pos_connectors/registry.py` (line 875)
- `docs/playbook/_status/pos/micros.md` (joint coverage of partnership, auth, sandbox)
- Live API docs accessed: No (relying on sibling entry's validation)
