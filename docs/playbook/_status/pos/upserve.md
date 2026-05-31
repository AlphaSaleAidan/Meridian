# Upserve (formerly Lightspeed U-Series)

**Registry key:** `upserve` — see `src/services/pos_connectors/registry.py`

## Status
DEAD API / OUTDATED CONFIG — `api.upserve.com` no longer responds (DNS CNAMEs to `upserve.com`, which 301-redirects to a Lightspeed marketing page). No live developer portal at `developer.upserve.com`. Ownership change in 2026 (Skyview Equity acquired Upserve from Lightspeed) adds further uncertainty.

## What it is
Cloud restaurant POS for US full-service and casual-dining merchants — was Lightspeed's "U-Series" heritage restaurant product (acquired by Lightspeed 2020, divested to Skyview Equity 2026).

## Vertical & market
- **Primary vertical:** restaurant (full-service, casual dining, bars)
- **Estimated NA market presence:** Small-Medium and shrinking — Lightspeed has been steering new and existing US restaurant merchants to K-Series (Lightspeed Restaurant); Skyview now owns the product but post-divestiture roadmap is unclear
- **Typical merchant profile:** US independent full-service restaurants, single- and small-multi-unit operators
- **Geographic concentration:** US-only

## How to spot the merchant uses it
- Login URL `*.upserve.com` (back-office) or `app.upserve.com`
- Help center URL `help.upserve.com` (titled "Upserve by Lightspeed Knowledge Center")
- Receipt footer / hardware branded "Upserve"; legacy iPad terminals
- Conversational tells: "Upserve", "Breadcrumb" (Upserve's predecessor brand), "U-Series"

## Auth method
Bearer token per registry — UNVERIFIABLE today. Historical Upserve API used OAuth-issued bearer tokens granted to approved partners; no current public docs to confirm.

## Data we can pull (per current config — UNVERIFIED, API host is unreachable)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | ? | `/checks` | API host does not resolve to a live service |
| Catalog / items | ? | `/menu-items` | Same |
| Customers | ? | `/guests` | Same |
| Employees | ? | `/employees` | Same |
| Inventory | ✗ | — | Not configured |
| Refunds | ? | — | Not configured |
| Order create | ✗ | — | `supports_orders: False` in registry |

## Partner program / access requirements
- **Partner program required:** Yes (historically) — UNCERTAIN today
- **Sign-up URL:** None found. Legacy `developer.upserve.com` does not resolve. No partner portal linked from `lightspeedhq.com/upserve/` or `help.upserve.com`
- **Approval timeline:** UNKNOWN — no published process post-divestiture
- **Cost / revenue share:** UNKNOWN

## Sandbox / test environment
- **Available:** No public sandbox found
- **URL:** N/A

## Rate limits
UNKNOWN — no live docs.

## Webhook / sync model
UNKNOWN. Historical Upserve API was poll-based REST.

## Connect flow (what the merchant does)
Not possible to build today — no live API endpoint, no partner-onboarding path, no documented OAuth client provisioning.

## Estimated effort to go LIVE
**XL (custom partnership required)** — must first establish contact with Skyview Equity's Upserve team to confirm whether the API still exists for new integrations, obtain credentials, and get current docs. Engineering work is small once that gate clears, but the gate itself is the blocker.

## What blocks LIVE status today
- `api.upserve.com` returns no HTTP response (DNS resolves to redirect host; no API service listening)
- `developer.upserve.com` and `upserve.com/restaurants/api/` both redirect to `lightspeedhq.com/upserve/`
- No public-facing developer documentation or partner sign-up flow
- Ownership in flux: Lightspeed sold Upserve to Skyview Equity in 2026 — partnership intake process post-divestiture unknown
- Lightspeed's K-Series API (`api.lsk.lightspeed.app`) does NOT cover U-Series merchants per K-Series API docs reviewed
- Registry config (`base_url`, endpoints, `auth_type: bearer`) cannot be validated against any live surface

## Common failure modes (for troubleshooting playbook)
- **Symptom:** Merchant says "I use Upserve" → **Likely cause:** legacy US restaurant POS → **Fix:** confirm dashboard URL (`*.upserve.com` vs `*.lightspeed.app`); if true Upserve, currently no integration path — offer CSV import or route to K-Series migration if they're considering it
- **Symptom:** Connection test to `api.upserve.com/v2/restaurants` times out / DNS fails → **Likely cause:** API host is no longer published → **Fix:** disable connector in UI until partnership re-established
- **Symptom:** Merchant says "we're migrating off Upserve" → **Likely cause:** Lightspeed's push to K-Series, or Skyview transition → **Fix:** identify destination POS and route to that connector

## Strategic notes
Triple-jeopardy account: (1) product is a heritage brand consolidated then divested, (2) public API surface is offline, (3) US-only and shrinking. Lightspeed marketing copy says "all former Upserve integrations will remain operational" — this refers to existing third-party integrations (e.g. payroll, accounting) that Upserve already had, NOT new API onboarding. Reps should not promise an Upserve integration; if a prospect insists on Upserve, the realistic options are CSV import (manual export from Upserve back-office) or wait for the merchant to migrate to a supported POS.

## Recommendation
**DEFER** — and consider **DEPRECATE** if no partnership signal from Skyview Equity within 90 days.

**Reasoning:** No live API host, no developer portal, no partner intake, and ownership just changed hands. Engineering effort would be wasted until Skyview clarifies API availability. Keep registry entry as a stub for CSV-import fallback only.

## Sources consulted
- Live HTTP probe: `https://api.upserve.com/v2/restaurants` → HTTP 000 (no response)
- Live HTTP probe: `https://developer.upserve.com/` → HTTP 000 (no response)
- Live HTTP probe: `https://upserve.com/` → 301 → `https://www.lightspeedhq.com/upserve/` (HTTP 200)
- DNS: `api.upserve.com` and `developer.upserve.com` both CNAME to `upserve.com` (34.117.157.200)
- https://www.lightspeedhq.com/upserve/ — confirms 2026 Skyview Equity acquisition and "former Upserve integrations will remain operational" language
- https://help.upserve.com/ — live Salesforce-hosted "Upserve by Lightspeed Knowledge Center" (no developer/API section linked)
- https://api-docs.lsk.lightspeed.app/ — K-Series API docs make no mention of U-Series coverage
- Cross-reference: `lightspeed-restaurant.md` (sister playbook entry, K-Series)
- Live API docs accessed: No (none exist publicly)
