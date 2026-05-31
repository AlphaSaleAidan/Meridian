# Tyro

**Registry key:** `tyro` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP / UNCERTAIN — config carries a plausible API key shape (`X-Api-Key` header against `https://api.tyro.com/connect/v1`), but the public host/path has not been validated against live Tyro developer docs and there is no Meridian partnership in place.

## What it is
Australian payments + EFTPOS + iPad-era POS provider — Tyro is AU's largest non-bank merchant acquirer, dominant in hospitality/restaurants and growing in retail and health.

## Vertical & market
- **Primary vertical:** restaurant / hospitality (primary), retail and health (secondary)
- **Estimated NA market presence:** None material — Australia-only acquirer
- **Typical merchant profile:** single- to multi-location AU restaurant, cafe, pub, or specialty retailer running Tyro EFTPOS terminals integrated with a third-party POS
- **Geographic concentration:** Australia (with NZ exposure via partner POS stacks)

## How to spot the merchant uses it
- Tyro-branded EFTPOS countertop or mobile terminal on the bar/counter
- AU street address; merchant talks in AUD, mentions "EFTPOS" rather than "card terminal"
- POS UI shows a "Tyro" payment integration tile (Lightspeed, Kounta/Lightspeed Restaurant, Impos, Bepoz, etc.)
- Conversational tells: "Tyro terminal," "Tyro integrated EFTPOS," "Tyro Portal"

## Auth method
API key in `X-Api-Key` header (per registry). Real-world Tyro integrations historically also involve a paired terminal / merchant-ID handshake; the customer-facing key issuance flow has not been verified against current Tyro docs.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Partial | `/merchants/{merchant_id}/transactions` | Payment-side transactions only; not POS line items |
| Catalog / items | ✗ | — | Tyro is acquirer/terminal, not menu/inventory source |
| Customers | ✗ | — | Not in scope |
| Employees | ✗ | — | Not in scope |
| Inventory | ✗ | — | Not in scope |
| Refunds | ✗ | — | Not configured (likely surfaces inside transactions feed) |

`supports_orders: False`. Frontend `pos-systems.ts` flags `sales: true`, everything else false, historical 365 days, real-time true — UNVERIFIED against live API.

## Partner program / access requirements
- **Partner program required:** Effectively yes — Tyro integrations are partner-gated; merchants do not typically self-issue API keys for third-party data pulls
- **Sign-up URL:** Not confirmed; Tyro Partners / Developer access is sales-led
- **Approval timeline:** UNCERTAIN — enterprise sales cycle (multi-week+)
- **Cost / revenue share:** Unknown

## Sandbox / test environment
- **Available:** UNCERTAIN — not validated
- **URL:** N/A confirmed
- **Notes:** No Meridian-side sandbox credentials on file

## Rate limits
Not documented in registry; not independently verified.

## Webhook / sync model
Frontend metadata claims webhooks supported; registry does not configure any webhook receiver. Treat as poll-only until validated.

## Connect flow (what the merchant does)
1. Merchant logs into Tyro Portal
2. Settings → API Access → generate integration key (per registry `stepByStepInstructions`; UNVERIFIED that this self-serve path exists today)
3. Merchant pastes Merchant ID + API key into Meridian
4. Meridian calls `/merchants/{merchant_id}` to validate, then polls `/transactions`

## Estimated effort to go LIVE
XL — partnership-gated, off-region, requires AU entity considerations and a customer-facing connect UI that does not exist.

## What blocks LIVE status today
- No Tyro partnership; key-issuance path is not confirmed to be self-serve
- Endpoint shape (`api.tyro.com/connect/v1`) not validated against current Tyro developer documentation in this pass
- No NA merchant demand — zero ICP overlap
- Payment-only data surface; does not give Meridian menu/inventory/employee coverage even if it worked

## Common failure modes
- **Symptom:** 401 on `/merchants/{merchant_id}` → **Likely cause:** key not issued for that merchant, or wrong header name → **Fix:** confirm with Tyro support; verify `X-Api-Key` is current contract
- **Symptom:** 404 on base path → **Likely cause:** `/connect/v1` path drifted or never existed publicly → **Fix:** re-validate against live Tyro developer docs before any further work

## Strategic notes
Tyro matters in Australia and only in Australia. For Meridian's NA (US + Canada) ICP, an AU acquirer adds zero pipeline value and meaningful maintenance surface. The right posture is to leave the config in place as a future-optionality stub and not invest engineering or partnership cycles until Meridian has an explicit AU expansion thesis with named accounts.

## Recommendation
DEFER (geography).

**Reasoning:** Tyro is AU-only and partnership-gated; off-ICP for Meridian's NA motion and no merchant demand to justify validating endpoints or pursuing a partner agreement.

## Sources consulted
- `src/services/pos_connectors/registry.py` (key: `tyro`)
- `frontend/src/data/pos-systems.ts` (key: `tyro`)
- Live API docs accessed: No
