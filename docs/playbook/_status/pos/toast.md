# Toast

**Registry key:** `toast` — see `src/services/pos_connectors/registry.py`

## Status
**LIVE** — direct API integration (one of 3). **CRITICAL CAVEAT:** new merchants only connect after Toast Partner Program approval and a merchant-side "Add Now" install. Do not promise same-day onboarding.

## What it is
Cloud restaurant POS on Android-based Toast hardware (Flex, Go, Tap) used by full-service, quick-service, cafes, and bars across the US.

## Vertical & market
- **Primary vertical:** restaurant (FSR, QSR, cafe, bar — no retail, no salons, no automotive)
- **Estimated NA market presence:** Dominant — largest US restaurant POS by new installs
- **Typical merchant profile:** single-location independent restaurants up to multi-unit groups
- **Geographic concentration:** US-primary, expanding to Canada/UK/Ireland

## How to spot the merchant uses it
- Green/black Toast-branded handheld and counter terminals (Toast Flex)
- Server-handed handhelds for tableside ordering
- "Powered by Toast" footer on guest receipts and online ordering pages
- Operator says "Toast" by name — they almost always know what they're on

## Auth method
OAuth 2.0 **client_credentials** grant via `POST /authentication/v1/authentication/login` with `{clientId, clientSecret, userAccessType: "TOAST_MACHINE_CLIENT"}`. Returns short-lived bearer token (`expiresIn` seconds). Every API call also requires `Toast-Restaurant-External-ID: <restaurant_guid>` header to scope to the specific restaurant.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes | `/orders/v2/orders` | Paginated, businessDate range |
| Catalog / items | Yes | `/menus/v2/menus` | Flattened from menu > group > item |
| Customers | Config only | `/customers/v1/customers` | Not pulled by sync_engine today |
| Employees | Yes | `/labor/v1/employees` | Cached for server attribution |
| Inventory | No | — | Not wired |
| Refunds | Partial | Inside orders | Surfaced via check/payment state, not separate endpoint |

## Partner program / access requirements
- **Partner program required:** **Yes — mandatory**
- **Sign-up URL:** https://pos.toasttab.com/integrations/integration-partner-program (apply via Toast; developer portal at https://doc.toasttab.com/)
- **Approval timeline:** **2–4 weeks typical** for Standard API Access; longer for custom scopes. Meridian is already an approved partner — the wait is for the merchant to enable us, not for us to be approved.
- **Cost / revenue share:** Free for Standard API Access tier; some scopes require Toast review

## Sandbox / test environment
- **Available:** Yes — Toast issues sandbox `clientId`/`clientSecret` and test restaurant GUIDs after partner approval
- **URL:** Same hosts as production (`ws-api.toasttab.com`) with sandbox credentials
- **Notes:** Request via Toast developer support after partner sign-off

## Rate limits
Per-endpoint limits documented in Toast portal; auth endpoint has a separate quota. Client retries on 401 with a fresh token (see `client.py`). Treat as bursty-tolerant but not unlimited.

## Webhook / sync model
**Poll-only in our integration.** Initial backfill = 18 months of orders in 7-day windows; incremental = every 30 min from last sync. Toast does offer webhooks for some events but we are not wired for them.

## Connect flow (what the merchant does)
1. Restaurant owner signs into Toast Web
2. **Integrations > Integration management > Browse & purchase integrations**
3. Search "Meridian" > click **Add Now**
4. Pick restaurant locations to enable
5. Confirm on Add Partner page — Meridian receives the restaurant GUID and credentials propagate (immediate for partner; up to 15 min for some downstream APIs)
6. Merchant returns to Meridian, paste/confirm restaurant GUID if prompted, sync starts

## Estimated effort to go LIVE (config → production-ready)
**Already LIVE.** Per-merchant onboarding: M (1–2 weeks calendar time driven by Toast-side enablement, not engineering).

## What blocks LIVE status today
- Nothing on Meridian's side — code path is production
- Per-merchant blocker: merchant must complete in-Toast "Add Now" step; we cannot self-serve them
- Customer sync wired in registry but not invoked in `sync_engine.py` — leave for v2

## Common failure modes (for troubleshooting playbook)
- **Symptom:** "Toast authentication failed (401)" on first sync → **Likely cause:** merchant skipped Add Now or removed Meridian in Toast Web → **Fix:** have them re-add in Integrations panel
- **Symptom:** Backfill empty despite real sales → **Likely cause:** wrong `restaurant_guid` (they pasted location GUID vs restaurant GUID) → **Fix:** call `GET /restaurants/v1/restaurants/{guid}` to validate
- **Symptom:** Token works then fails mid-sync → **Likely cause:** access token expired (`expiresIn` elapsed) → **Fix:** already handled — client auto-retries auth on 401

## Strategic notes
Toast is our highest-intent inbound channel because restaurant operators on Toast are sophisticated and analytics-hungry — but it is also the integration where reps over-promise most often. The Toast Partner Program gate is real: even though we are an approved partner, the **merchant** still has to install us from their Toast Web admin, and that is the 2–4 week reality (driven by GM availability, not red tape). Never say "instant" or "tomorrow" for Toast. Frame it as: "We're a Toast-approved partner, so the integration itself is live and proven — onboarding is a 10-minute click in your Toast admin, but we typically schedule it within 1–2 weeks so we can walk your GM through it."

## Recommendation
**BUILD NOW** — keep, polish, prioritize. This is a top-3 distribution channel; the only adds worth doing are webhook ingestion and surfacing the Add Now deep-link directly in our connect UI to compress the 2–4 week onboarding.

**Reasoning:** Largest restaurant POS in our ICP, integration is already shipped and stable, and the only friction is merchant-side which is fixable with better connect UX.

## Sources consulted
- https://doc.toasttab.com/
- https://doc.toasttab.com/doc/devguide/authentication.html
- https://doc.toasttab.com/doc/platformguide/adminRestaurantServiceIntegrationsAndToastPartnerIntegrations.html
- `/root/Meridian/src/toast/client.py`, `mappers.py`, `sync_engine.py`
- `/root/Meridian/src/services/pos_connectors/registry.py` (`toast` entry)
- Live API docs accessed: Yes
