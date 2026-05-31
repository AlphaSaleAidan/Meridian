# Greenline POS

> Status: **WAVE 1.5 BUILDING — Canada cannabis #2 (after Cova)**
> Category: cannabis (Canadian dispensary; BLAZE-owned; AGCO/BCLDB compliant)
> Auth: X-Api-Key header per tenant (partner program — getgreenline.co)

## What you tell the merchant

"Greenline is our #2 Canadian cannabis integration, right behind Cova. BLAZE-owned, AGCO and BCLDB compliant out of the box. Partner intake is filed alongside Cova; expected live within 30–45 days. We've built the cannabis workflow with PII handling and provincial compliance baked in — same as Cova."

## How the merchant connects (when live)

1. Cannabis vertical compliance review (one-time per Meridian) → Greenline partner intake
2. Greenline issues per-tenant API key
3. Merchant pastes key into Meridian's **Settings → POS Connections → Connect Greenline**
4. We hit `/locations` to verify and start the backfill
5. Real-time webhooks subscribe automatically once the key validates

Typical time to connect (projected): **4 minutes** post-partner-approval.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Orders | real-time (webhooks) + hourly poll | 18 months |
| Products (catalog) | daily | full history |
| Customers | daily | full history (PII-protected) |
| Employees | daily | full history |
| Locations | daily | full history |

Endpoint reference: `https://api.getgreenline.co/v1`

## What features they get (when live)

Cannabis-tuned suite (same shape as Cova):

- Money Left on Table
- Product Velocity (especially valuable — fast cannabis inventory turn)
- Inventory Intelligence (reorder timing, batch tracking)
- Customer LTV (patient/member retention is the cannabis margin lever)
- Revenue trend + forecasting
- Promo/discount ROI
- Day-of-week / time-of-day patterns (cannabis traffic is heavily time-skewed)
- Real-time webhook ingestion — fresher data than poll-only POSes

## What features they DON'T get

- Order creation (`supports_orders: False`) — analytics-only
- Cross-border or US compliance — Greenline is Canada-focused (AGCO/BCLDB)
- Provincial regulator submission — we surface compliance-relevant fields but don't file on the merchant's behalf

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Auth rejected | Wrong scope on Greenline tenant key | Greenline partner intake clarifies scopes during approval |
| Missing batch IDs | Greenline batch tracking not enabled per location | Falls back to SKU-level (still useful for velocity/margin) |
| Webhook drops | Greenline-side network blip | Hourly poll backstops; missing window auto-fills on next poll |
| Provincial compliance scope mismatch | Per-province PII rules vary | We honor Greenline's per-province PII flags; some fields may be redacted by province |

## Sales angle

**Opener (Canada):** "You're on Greenline — BLAZE-owned, AGCO and BCLDB compliant. We're your #2 cannabis priority right after Cova. Provincial regulators want clean data; your members want product consistency. We give you both, plus the margin insights nobody else surfaces. And Greenline pushes real-time webhooks — your data is fresher than Cova's, actually."

**Why Greenline is the wedge:**
- Canadian cannabis #2 footprint (Cova is #1) — together they cover most of the market
- AGCO/BCLDB compliance is baked into the product — fewer rep objections about regulatory risk
- Real-time webhooks support — fresher data than the poll-only cannabis POSes
- BLAZE ownership means the same engineering team that runs `blaze-pos` (US) runs this — proven dev maturity

**Competitive notes:** If a prospect is on Cova, that's playbook #1 — both are valid. If they're on Indica Online, that's CSV-only legacy. If they're on a US cannabis POS in Canada (rare), qualify carefully — US connectors don't carry Canadian compliance posture.

---

## Cannabis-specific compliance you MUST mention

(Same as Cova — repeat verbatim on every cannabis sales call.)

- **Separate banking + insurance posture** — federal Schedule I in US contexts; Canadian banking is permissive but insurance varies by province
- **PII handling per provincial rules** — Ontario, BC, Quebec each have different consumer-data rules; we honor Greenline's per-province flags
- **Marketing channels: direct / event / WOM only** — Google, Facebook, LinkedIn restrict cannabis ads; no paid social or paid search

---

## What blocks live status today

- Greenline partner intake filed this week — waiting on approval
- Cannabis vertical compliance review (already in flight for Cova — covers Greenline once landed)
- Webhook receiver build (we have the poll path; webhook-receive endpoint is in progress)

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (greenline-pos config) + docs/playbook/_status/phase-2-decisions.md (Wave 1.5 adds, Cannabis vertical greenlit, Wave 2 partner table) + docs/playbook/_status/pos-expansion-candidates.md (greenline-pos high-priority entry)_
