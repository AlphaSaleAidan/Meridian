# Toast

> Status: **LIVE** (webhooks + "Add Now" deep link shipping)
> Category: restaurant (full-service, QSR, multi-location)
> Auth: OAuth client credentials

## What you tell the merchant

"Toast connection takes 3 minutes. We use Toast's standard API integration — you generate an API key from your Toast Web admin, paste it into Meridian, and we start backfilling. First insights in 24 hours."

## How the merchant connects

The recommended flow is the Toast Partner install — Meridian is already an approved Toast partner:

1. Restaurant owner signs into Toast Web → **Integrations → Integration management → Browse & purchase integrations**
2. Search "Meridian" → click **Add Now**
3. Pick the restaurant locations to enable
4. Confirm on the Add Partner page — Meridian receives the restaurant GUID and credentials propagate (immediate for partner; up to 15 min for some downstream APIs)
5. Merchant returns to Meridian, confirms restaurant GUID if prompted, sync starts

Typical time to connect: **10 minutes of clicks**, but **calendar time 1–2 weeks** because we schedule with the GM. **Never promise same-day onboarding.** The partner program (https://pos.toasttab.com/integrations/integration-partner-program) gate is real even though we're approved — the merchant-side install can lag 2–4 weeks depending on GM availability.

Alternate path (legacy): API Access → Create new credential, paste client ID + client secret + restaurant external ID into Meridian. Same OAuth client_credentials flow underneath.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Orders | webhooks (shipping) + hourly poll fallback | 18 months |
| Menus | daily | full history |
| Labor / employees | hourly | full history |
| Customers | daily | full history |

Endpoint reference: `https://ws-api.toasttab.com`

## What features they get

Full restaurant-focused suite — Toast has the deepest restaurant-specific data of any POS:

- Money Left on Table
- Revenue trend + forecasting (restaurant-tuned models)
- Peak hours by 15-min window (critical for staffing)
- Menu engineering matrix (stars / plowhorses / puzzles / dogs)
- Food cost analysis (when item costs are entered)
- Discount/promo ROI
- Employee performance + tip-out fairness
- Customer LTV
- Reservation no-show analysis (if Toast Tables is on)
- Multi-location rollups (multi-location add-on)

## What features they DON'T get

- Inventory intelligence at SKU level requires Toast Inventory module — many merchants don't have it. We fall back to menu-item velocity.

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Toast authentication failed (401)" on first sync | Merchant skipped Add Now in Toast Web, or removed Meridian from Integrations panel | Have them re-add Meridian via Integrations → Integration management |
| Backfill empty despite real sales | Wrong `restaurant_guid` — merchant pasted location GUID vs restaurant GUID | Validate via `GET /restaurants/v1/restaurants/{guid}`; Toast Web → Settings shows the correct GUID |
| Token works then fails mid-sync | Short-lived access token (`expiresIn` elapsed) | Already handled — client auto-retries auth on 401 |
| Missing menu items in analytics | Item was deleted from menu (not archived) | We can backfill from order history if the merchant re-enables historical access |
| Labor data empty | Toast Payroll not on, just basic labor | Expected — staffing recs become "low confidence" |

## Sales angle

**Opener:** "Are you on Toast? Most Toast restaurant owners know their revenue but can't tell which menu items actually make them money vs. just sell well. Our Menu Engineering Matrix shows you the stars and the dogs — usually finds 4–6 items costing you margin."

**Why Toast is high-value:**
- Restaurant owners with cameras are prime camera intelligence add-on candidates
- Cameras + Toast = killer combo: queue length + table dwell + revenue cross-reference
- Multi-location restaurants → multi-location add-on (commission at custom price)

**Why this is the wedge:** Toast is the largest US restaurant POS by new installs, and restaurant operators on Toast are sophisticated and analytics-hungry — our highest-intent inbound channel. But it's also the integration where reps over-promise most often. Frame onboarding as: "We're a Toast-approved partner, so the integration itself is live and proven — onboarding is a 10-minute click in your Toast admin, but we typically schedule it within 1–2 weeks so we can walk your GM through it."

**Decision maker:** owner or GM (single location), franchisee (chains — not corporate).

## What blocks live status today

- Nothing on Meridian's side — code path is production (`/root/Meridian/src/toast/`)
- **Per-merchant blocker:** merchant must complete the Toast Web "Add Now" step; we cannot self-serve them
- Webhooks shipping this week (currently 30-min poll fallback)
- "Add Now" deep link UX from Toast admin → Meridian connect screen — in dev (compresses the 2–4 week onboarding)
- Customer sync wired in registry but not invoked in `sync_engine.py` — v2

## Reference docs

- Toast developer docs: https://doc.toasttab.com/
- Authentication guide: https://doc.toasttab.com/doc/devguide/authentication.html
- Integration partner platform guide: https://doc.toasttab.com/doc/platformguide/adminRestaurantServiceIntegrationsAndToastPartnerIntegrations.html
- Partner program application: https://pos.toasttab.com/integrations/integration-partner-program

---

_Last updated: 2026-05-31 (enhanced with Phase 1 research)_
_Sourced from: src/services/pos_connectors/registry.py (toast config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #3) + docs/playbook/_status/pos/toast.md (Phase 1)_
