# CAKE POS (Mad Mobile)

**Registry key:** `cake` — see `src/services/pos_connectors/registry.py`

## Status
OUTDATED CONFIG — registry says `csv_only` but CAKE ships a real (partner-gated) REST API. Treat as CSV in production today; upgrade path exists.

## What it is
CAKE is a cloud, tablet-based restaurant POS used in full-service, quick-service, bars, cafes, pizzerias, and small multi-unit operators. Launched inside Sysco in 2011, divested to **Mad Mobile in August 2020**; Sysco kept it as a preferred POS partner with bundled offers but no longer owns it.

## Vertical & market
- **Primary vertical:** restaurant (full-service tilt; also QSR, bar, cafe, pizza)
- **Estimated NA market presence:** Medium — 5,000+ locations cited at acquisition; still distributed nationally via Sysco's foodservice channel
- **Typical merchant profile:** independent and small-chain restaurants (1–10 locations) where a Sysco rep introduced the POS alongside a food contract
- **Geographic concentration:** US

## How to spot the merchant uses it
- Orange "CAKE" logo on the terminal bezel, customer-facing screen, or printed receipt footer
- Square-ish all-in-one tablet terminal (often with branded "POS wrap" sleeves)
- Conversational tells: "we got the POS through our Sysco rep," "first station was free," reference to the **888-979-7225** support line
- They mention a "local CAKE expert" — that's the Sysco-channel rep, not corporate sales

## Auth method
Per current registry: **CSV upload only.** CAKE's documented API uses an `AUTH Login API v2` flow with Admin and Affiliate API tiers; older public docs at `developer.cake.net` referenced OAuth2 `client_credentials`, but that portal now redirects to marketing — access appears to have moved behind a partner-gated process. We have no signed integration agreement on file.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | CSV only | n/a | Columns: Order ID, Date, Total, Items, Payment Type |
| Catalog / items | not configured | — | API exists upstream; not wired |
| Customers | not configured | — | |
| Employees | not configured | — | Labor API exists upstream |
| Inventory | not configured | — | |
| Refunds | not configured | — | |

`supports_orders: False`, `sms_fallback: True` — same posture as other CSV-only restaurant connectors.

## Partner program / access requirements
- **Partner program required:** Yes (Mad Mobile / CAKE integration partner)
- **Sign-up URL:** No public self-service portal confirmed; intro path is through CAKE partnerships (and Sysco channel for warm intros)
- **Approval timeline:** Unknown — assume weeks; Mad Mobile is a private mid-market vendor without published partner SLAs
- **Cost / revenue share:** Not publicly disclosed

## Sandbox / test environment
- **Available:** Historically yes (OAuth2 sandbox keys via the old developer portal); current availability **unverified** post-portal redirect
- **URL:** Previously `developer.cake.net` — now redirects to `trycake.com`
- **Notes:** Request sandbox via partnerships contact; do not assume self-service

## Rate limits
Not publicly documented. Assume per-merchant throttling; validate during partner onboarding.

## Webhook / sync model
Unknown / not in our connector. Plan for poll-only against the Sales Summary API when we upgrade beyond CSV.

## Connect flow (what the merchant does)
1. Merchant exports a sales report from CAKE back-office (date range, all locations)
2. Merchant uploads the CSV in Meridian's connector UI
3. Meridian maps columns per registry (`Order ID`, `Date`, `Total`, `Items`, `Payment Type`)
4. If CSV fails, fall back to SMS daily-totals collection (`sms_fallback: True`)

## Estimated effort to go LIVE (config → production-ready)
**CSV path:** already live — S (test the importer against a real CAKE export).
**API path:** L — requires Mad Mobile partner intro, confirming current OAuth2 flow, and wiring the REST connector.

## What blocks LIVE status today
- Registry assumes CSV only; no API client implemented even though one exists
- Public developer portal redirected — current auth flow and sandbox process must be reconfirmed with Mad Mobile partnerships
- No validated CSV export from a real CAKE merchant on file to confirm column names match registry exactly

## Common failure modes (for troubleshooting playbook)
- **Symptom:** Merchant says "I use CAKE" but exports look different → **Likely cause:** they're on the older getCAKE admin export vs. the current trycake report → **Fix:** ask for a screenshot of the export screen, remap columns
- **Symptom:** Merchant routed by a Sysco rep is confused about logins → **Likely cause:** Sysco-bundled merchants often have their CAKE account provisioned by the rep and never set their own admin password → **Fix:** direct them to the 888-979-7225 Sysco-customer support line for credential reset

## Strategic notes
The user-supplied premise that "CAKE is owned by Sysco" is **out of date** — Sysco divested in 2020. The Sysco angle is still real, but as a **distribution channel** (free first station, 2-yr warranty, dedicated rep) rather than ownership. That makes CAKE a small/mid-market self-service-ish sale, not the NCR-style enterprise motion. The asymmetric lever: if Meridian builds a one-click CSV mapping for CAKE's default export, we can absorb the entire Sysco-channel base without ever signing a Mad Mobile partner agreement.

## Recommendation
**WAIT** on the API. **BUILD NOW** on the CSV path: validate the column mapping against a real export and ship a one-click "Sysco-CAKE merchant" onboarding template.

**Reasoning:** API access is partner-gated by a private mid-market vendor with no published self-service path, while ~5k Sysco-channel restaurants can be onboarded today via CSV with zero partnership cost.

## Sources consulted
- https://www.prnewswire.com/news-releases/mad-mobile-to-acquire-cake-a-sysco-company-301107901.html
- https://hospitalitytech.com/mad-mobile-acquire-cake-sysco-company
- https://www.solutions.sysco.com/cake
- https://trycake.com/pages/sysco-partners
- https://support.getcake.com/support/solutions/5000109264
- https://apitracker.io/a/trycake
- https://www.flipdish.com/us/what-we-do/integration/pos-partners/cake-by-sysco
- Live API docs accessed: No (developer.cake.net now redirects to marketing site; historic OAuth2 flow referenced in third-party writeups only)
