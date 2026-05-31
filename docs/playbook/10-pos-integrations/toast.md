# Toast

> Status: **LIVE** (webhooks + "Add Now" deep link shipping)
> Category: restaurant (full-service, QSR, multi-location)
> Auth: OAuth client credentials

## What you tell the merchant

"Toast connection takes 3 minutes. We use Toast's standard API integration — you generate an API key from your Toast Web admin, paste it into Meridian, and we start backfilling. First insights in 24 hours."

## How the merchant connects

1. Toast admin → **Integrations → API Access → Create new credential**
2. Scopes needed: `orders:read`, `menus:read`, `labor:read`, `customers:read`
3. They copy the client ID + client secret + restaurant external ID
4. Paste into Meridian's **Settings → POS Connections → Connect Toast**
5. We authenticate, register webhooks (when shipped), start backfill

Typical time to connect: **3–5 minutes** (slightly more steps than Square because Toast requires manual credential creation).

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
- Multi-location rollups (Command tier)

## What features they DON'T get

- Inventory intelligence at SKU level requires Toast Inventory module — many merchants don't have it. We fall back to menu-item velocity.

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Credential rejected | Wrong restaurant external ID | Toast Web → Settings → shows the GUID |
| Missing menu items in analytics | Item was deleted from menu (not archived) | We can backfill from order history if the merchant re-enables historical access |
| Labor data empty | Toast Payroll not on, just basic labor | Expected — staffing recs become "low confidence" |

## Sales angle

**Opener:** "Are you on Toast? Most Toast restaurant owners know their revenue but can't tell which menu items actually make them money vs. just sell well. Our Menu Engineering Matrix shows you the stars and the dogs — usually finds 4–6 items costing you margin."

**Why Toast is high-value:**
- Restaurant owners spend more than retail (CA$685 Premium tier is normal)
- Cameras + Toast = killer combo: queue length + table dwell + revenue cross-reference
- Multi-location restaurants → Command tier ($959/mo commission to you)

**Decision maker:** owner or GM (single location), franchisee (chains — not corporate).

## What blocks live status today

- Webhooks shipping this week (currently 1-hour poll)
- "Add Now" deep link UX from Toast admin → Meridian connect screen — in dev

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (toast config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #3)_
