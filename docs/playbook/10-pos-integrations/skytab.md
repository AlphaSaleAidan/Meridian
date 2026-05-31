# SkyTab (Shift4)

> Status: **WAVE 1 BUILDING** + Shift4 partner application filed this week
> Category: restaurant (Shift4's restaurant POS — major Revel migration tailwind)
> Auth: OAuth (bearer)

## What you tell the merchant

"SkyTab support is in active build — Shift4 partner application filed this week. Expected live within 30–45 days. If you migrated from Revel recently, you're a priority — there are ~18,000 of you moving to SkyTab right now and we're building specifically for that wave."

## How the merchant connects (when live)

1. From the Meridian portal → **Settings → POS Connections → Connect SkyTab**
2. Merchant logs into Shift4 Lighthouse (`https://lighthouse.shift4.com/`) → grants Meridian access
3. Meridian receives `merchant_id` + access token from the Lighthouse partner flow
4. Backfill begins against the partner-only SkyTab POS data API (NOT `api.shift4.com/v1` — that's the payments API, HTTP Basic auth, only good for charges/customers/refunds)

Typical time to connect (projected): **3 minutes** once partnered.

**Partner program required:** apply via `dine.shift4.com/integrations`. Approval timeline is enterprise — assume **4–8 weeks**. POS-level access (orders, menu, employees) is not on the public payments API; SkyTab POS endpoints and sync model are partner-only.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Transactions | hourly poll | 18 months |
| Items | daily | full history |
| Employees | daily | full history |

Endpoint reference: `https://api.shift4.com/v1`

## What features they get (when live)

Restaurant suite:

- Money Left on Table
- Menu engineering
- Revenue forecasting
- Peak hours
- Employee performance
- Discount/promo ROI

## What features they DON'T get

- Order creation (`supports_orders: False`) — analytics-only
- Customer LTV — SkyTab customer data is not exposed in their current API surface

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 on every call | Sending Bearer against the payments API which expects HTTP Basic (secret as username, blank password). Or pointing at the payments API at all when we need the partner POS API | Use Lighthouse partner credentials, not the public payments API |
| 404 on `/merchants/{id}/transactions` | Path doesn't exist on the payments API | Escalate via partner SDK — POS endpoints are partner-only |
| Test-only data appearing | Using `sk_test_*` test secret | Swap for live secret |
| Merchant ID wrong | SkyTab merchant ID differs from Shift4 payment merchant ID | Use the SkyTab admin → Settings to get the right one |
| Old Harbortouch credentials | Merchant migrated from Harbortouch but kept old creds | They need new SkyTab creds from Shift4 |

## Sales angle

**Opener for Revel-migrating merchants:** "I know you just moved to SkyTab from Revel. That migration is brutal and you've probably lost your analytics in the process. We rebuild it on SkyTab data — same insights, better than what Revel ever gave you."

**Opener for net-new SkyTab:** "Are you on SkyTab? Shift4's restaurant POS — we're partner-pending right now and you can be in the first cohort of live merchants. CA$2,800/mo in money-left-on-table is the average we find in week 1."

**Why this matters:** the Revel → SkyTab migration is a forced event for ~18,000 restaurants. Most are looking for replacements for their old analytics stack. Time-bounded opportunity.

**Why this is THE wedge:** SkyTab is the **highest-leverage restaurant integration on the roadmap**. Shift4 (NYSE: FOUR) closed the $250M Revel acquisition in July 2024 and is consolidating Revel's ~18,000 locations into SkyTab — CEO Isaacman publicly said "you don't need two restaurant products." Shift4 is also rolling up Focus POS and Appetize. **Every Revel prospect today is a SkyTab prospect in 12–24 months.** Rep angle: Revel prospects fear forced migration. Pitch Meridian as the analytics layer that **survives the platform switch** — we follow them Revel → SkyTab without losing historical data.

**Operator tells:** black handheld branded "SkyTab" at table-side, receipts say "Powered by SkyTab" / "Shift4 Payments", back-office at `https://lighthouse.shift4.com/`, staff say "the SkyTab" or "the handheld."

## What blocks live status today

- **No Shift4 partner agreement yet** — application filed; assume 4–8 weeks
- **Registry `base_url`, auth, and endpoint paths are unverified — do not ship as-is.** `https://api.shift4.com/v1` is Shift4's **payments** API (HTTP Basic auth, Charges/Customers/Refunds), not a SkyTab restaurant-data API. POS data is partner-only.
- **No customer-facing connect UI**
- **SkyTab POS endpoints not publicly documented** — discovery blocked on partner SDK
- Estimated effort to LIVE: **XL** (partner approval + API discovery + auth refactor + connect UI)

## Routing note

**If a merchant says "we're on Harbortouch":** that brand is sunset. Shift4 is migrating everyone to SkyTab. Pitch them as SkyTab merchants and tee up the migration conversation.

## Reference docs

- Shift4 payments API docs (NOT the POS API): https://dev.shift4.com/docs/api
- SkyTab / partner integrations home: https://dine.shift4.com/integrations
- Revel acquisition ($250M, July 2024, 18k locations): https://www.paymentsdive.com/news/shift4-point-of-sale-revel-pos-merger-acquisition-payment/715958/

---

_Last updated: 2026-05-31 (enhanced with Phase 1 research)_
_Sourced from: src/services/pos_connectors/registry.py (skytab config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #11, Harbortouch deprecation, Wave 2 partner table) + docs/playbook/_status/pos/skytab.md (Phase 1)_
