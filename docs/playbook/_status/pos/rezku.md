# Rezku

**Registry key:** `rezku` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP — registry currently marks `auth_type: csv_only`, but Rezku does expose a real REST API behind a support-mediated enablement process. Treat current CSV config as a fallback, not the ceiling.

## What it is
iPad-based restaurant POS from Guest Innovations (Sacramento, CA, founded 2014) bundling POS, reservations/waitlist, online ordering, gift cards and loyalty for independent bars, FSRs and small chains.

## Vertical & market
- **Primary vertical:** restaurant (bars, FSR, casual, cafes — independents)
- **Estimated NA market presence:** Small–Medium (US-concentrated independent operator base)
- **Typical merchant profile:** independent bar/restaurant, 1–3 locations, runs on iPads, payments processed via Vantiv/Worldpay through Guest Innovations
- **Geographic concentration:** US (Sacramento HQ, US-based 24/7 support)

## How to spot the merchant uses it
- iPad terminals with the "Rezku POS" app
- Reservations / waitlist tablet at host stand branded "Rezku"
- Receipt or online-ordering page references Rezku Online / Rezku Gift Cards / Rezku Loyalty
- Conversational tells: "we run Rezku", "our processor is Guest Innovations", merchant mentions integrations like 7shifts, MarginEdge, Yellow Dog, Chowly, or Flipdish

## Auth method
OAuth-style client credentials issued by Rezku support — Client ID + Client Secret + Restaurant ID(s) per location (per Yellow Dog integration docs). No public developer portal, no self-service keys. CSV export is the no-API fallback path the current registry encodes.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | ✓ (CSV today; API once enabled) | n/a — CSV columns `Order #`, `Date`, `Total`, `Item Name`, `Payment Type` | API pulls closed orders only |
| Catalog / items | ✓ (API) | undocumented publicly | "Unsold items" confirmed via Yellow Dog |
| Customers | ✗ | — | Not in registry; reservations module holds guest data |
| Employees | ✗ | — | 7shifts pulls timecards bidirectionally — likely exists |
| Inventory | Partial | — | Native Rezku Inventory module; third parties (Yellow Dog, MarginEdge, Craftable) consume via API |
| Refunds | Unknown | — | Likely inside closed-order payload |

`supports_orders: False`, `sms_fallback: True` — read-only analytics, SMS-receipt fallback supported.

## Partner program / access requirements
- **Partner program required:** Yes (informal — no public program page)
- **Sign-up URL:** None. Email `support@rezku.com` requesting "API enablement between Rezku and Meridian" (same phrasing MarginEdge and other partners use)
- **Approval timeline:** Unknown — partner-mediated, likely 1–4 weeks based on comparable mid-tier POS onboarding
- **Cost / revenue share:** Not publicly disclosed

## Sandbox / test environment
- **Available:** UNCERTAIN — not publicly documented
- **URL:** N/A publicly
- **Notes:** Request alongside API enablement email

## Rate limits
Unknown — not publicly documented. Yellow Dog runs hourly polls, suggesting limits are not aggressive.

## Webhook / sync model
Poll-only based on observed partner integrations (Yellow Dog: hourly). No public webhook documentation.

## Connect flow (what the merchant does)
1. Merchant emails `support@rezku.com` (or rep does it on their behalf, cc'd): "Please enable API access between our Rezku account and Meridian"
2. Rezku support issues Client ID + Client Secret + Restaurant ID(s) per location
3. Merchant pastes the three values into Meridian's connect screen
4. Meridian polls closed orders + items on schedule; CSV upload remains available as backup

## Estimated effort to go LIVE (config → production-ready)
M — engineering work is small (client_credentials + paginated orders/items endpoints) once credentials exist. Real cost is the email/relationship loop with Rezku support and validating endpoints against whatever they share.

## What blocks LIVE status today
- Registry config is `csv_only` — needs `base_url`, `auth_type: oauth_client_credentials`, and orders/items endpoint paths validated against Rezku's actual API
- No documented partner relationship with Rezku support yet
- No customer-facing connect UI for the Client ID / Secret / Restaurant ID triplet
- Sandbox availability unconfirmed

## Common failure modes (for troubleshooting playbook)
- **Symptom:** Merchant says "we use Rezku" but connector only offers CSV → **Likely cause:** registry not yet upgraded to API path → **Fix:** collect creds, fall back to CSV upload, queue API enablement request
- **Symptom:** 401 after pasting Client ID/Secret → **Likely cause:** credentials scoped to wrong Restaurant ID → **Fix:** ask Rezku support to confirm restaurant_id ↔ key binding
- **Symptom:** Missing recent transactions → **Likely cause:** API returns closed orders only; open tabs not yet finalized → **Fix:** wait for end-of-day close or document the gap to merchant

## Strategic notes
Rezku is small but punches above its weight in the independent-bar segment, and the partner ecosystem (7shifts, MarginEdge, Yellow Dog, Chowly, Flipdish, Craftable) proves the API is real and third parties get approved. Lead with the analytics-only, read-only framing — same posture that has worked for MarginEdge. Low strategic priority for the Canada portal specifically (US-concentrated), but a fast credibility win for US independent-operator deals when a merchant raises it unprompted.

## Recommendation
WAIT — keep CSV path live, send the API enablement email opportunistically.

**Reasoning:** Rezku's footprint doesn't justify proactive eng investment, but the API is cheap to wire up once a real merchant deal needs it. First Rezku-using prospect triggers the support email + a registry upgrade from `csv_only` to `oauth_client_credentials`.

## Sources consulted
- https://rezku.com/integrations
- https://rezku.com/about-us
- https://help.yellowdogsoftware.com/rezku
- https://www.7shifts.com/integrations/rezku/
- https://www.partnerbase.com/rezku-pos
- https://www.crunchbase.com/organization/guest-innovations-inc
- https://www.cardpaymentoptions.com/credit-card-processors/guest-innovations/
- Live API docs accessed: No (no public developer portal; access partner-gated via support@rezku.com)
