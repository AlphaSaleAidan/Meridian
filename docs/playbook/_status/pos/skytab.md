# SkyTab POS (Shift4)

**Registry key:** `skytab` — see `src/services/pos_connectors/registry.py`

## Status
NEEDS PARTNERSHIP — registry compiles, but `https://api.shift4.com/v1` is Shift4's **payments** API (HTTP Basic auth, Charges/Customers/Refunds), not a SkyTab restaurant-data API. POS-level access (orders, menu, employees) requires Shift4's partner program via `dine.shift4.com`.

## What it is
Restaurant POS (handheld + counter) from Shift4 — pay-at-the-table, online ordering, KDS, reservations, loyalty. Shift4's flagship hospitality product post-Revel.

## Vertical & market
- **Primary:** restaurant (QSR, full-service, bars, fast-casual); stadiums/venues via Appetize
- **NA presence:** Large and accelerating — Shift4 (NYSE: FOUR) migrating ~18,000 Revel locations onto SkyTab
- **Typical merchant:** independents through mid-market multi-unit; US-dominant, expanding internationally

## How to spot it
- Black handheld branded "SkyTab" at table-side; receipts say "Powered by SkyTab" / "Shift4 Payments"
- Back-office at `https://lighthouse.shift4.com/`; staff say "the SkyTab" or "the handheld"

## Auth method
- **Payments API (in registry):** HTTP Basic — secret as username, blank password. **NOT** Bearer. Config is wrong.
- **SkyTab POS data API:** not publicly documented; partner-gated via Lighthouse.

## Data we can pull (per current config — UNVERIFIED)
| Type | Config claim | Reality |
|------|--------------|---------|
| Transactions | `/merchants/{id}/transactions` | Not on payments API; likely 404 |
| Catalog | `/merchants/{id}/items` | Same — needs partner API |
| Employees | `/merchants/{id}/employees` | Same |
| Refunds | none mapped | Payments API has `/refunds` |

## Partner program / access
- **Required:** Yes — POS data is not on the public payments API
- **Sign-up:** `dine.shift4.com/integrations`; payments docs at `dev.shift4.com`
- **Timeline:** Enterprise — assume 4–8 weeks
- **Cost / rev share:** Not publicly disclosed

## Sandbox / limits / webhooks
Payments API: test keys (`sk_test_*`), webhooks supported, rate limits undocumented (429 backoff). SkyTab POS sandbox and sync model are partner-only.

## Connect flow — TBD
Cannot define until partner access granted. Expect: merchant logs into Lighthouse → grants access → Meridian receives merchant_id + token.

## Effort to go LIVE
XL — partner approval + API discovery + auth refactor + connect UI.

## What blocks LIVE today
1. No Shift4 partner agreement
2. Registry `base_url`, auth, and endpoint paths are unverified — **do not ship as-is**
3. No customer-facing connect UI
4. SkyTab POS endpoints not publicly documented

## Common failure modes (predicted)
- **401 on every call** → Bearer against Basic-auth API → swap to HTTP Basic, secret as username
- **404 on `/merchants/{id}/transactions`** → path doesn't exist on payments API → escalate to partner
- **Test-only data** → using `sk_test_*` → swap for live secret

## Strategic notes
**Highest-leverage restaurant integration on our roadmap.** Shift4 is consolidating Revel (~18,000 locations, $250M deal closed July 2024) into SkyTab — CEO Isaacman said "you don't need two restaurant products." Every Revel prospect today is a SkyTab prospect in 12–24 months. Shift4 is also rolling up Focus POS and Appetize.

Rep angle: Revel prospects fear forced migration. Pitch Meridian as the analytics layer that **survives the platform switch** — we follow them Revel → SkyTab without losing historical data.

## Recommendation
BUILD NOW (partnership track) — file partner application this week, fix the registry to match Shift4's actual auth, treat POS endpoint mapping as blocked on partner SDK.

**Reasoning:** SkyTab is where the restaurant base is moving; the current registry entry is cosmetic and will fail on the first real call.

## Sources
- `dev.shift4.com/docs/api` — base URL + HTTP Basic auth confirmed
- `paymentsdive.com/news/shift4-point-of-sale-revel-pos-merger-acquisition-payment/715958/` — $250M Revel deal, July 2024 close, 18k locations
- `dine.shift4.com/` — SkyTab product home (redirect from skytab.com)
- `src/services/pos_connectors/registry.py` lines 286–296
- Live partner docs accessed: No (partner-gated)
