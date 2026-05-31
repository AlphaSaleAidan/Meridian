# Treez

> Status: **WAVE 2 PARTNER-PENDING** — partner intake this week; requires RSA JWT signer (30s TTL)
> Category: cannabis (US dispensary #2 — California-heavy)
> Auth: Bearer (with RSA JWT signing, short TTL)

## What you tell the merchant

"Treez is our #2 US cannabis priority — partner intake filed this week. The auth is more involved (RSA-signed tokens with 30-second TTL), which is why partner cycle matters. Once we're approved, you'll be live in days."

## How the merchant connects (when live)

1. Treez admin → **Settings → API → Generate keypair** (RSA)
2. Provide public key to Meridian; we use the private key (issued by Treez via partner program) to sign requests
3. We pull from `https://api.treez.io/v2.0/dispensary/{dispensary_id}/...`

The merchant doesn't see the JWT signing — it's hidden behind the connect flow.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Tickets (orders) | hourly poll | 18 months |
| Products | daily | full history |
| Budtenders (employees) | daily | full history |
| Customers | daily | PII-protected |

Endpoint reference: `https://api.treez.io/v2.0/dispensary/{dispensary_id}/`

## What features they get (when live)

Cannabis suite + budtender-specific:

- Money Left on Table
- Budtender performance (Treez has rich employee data — strong feature here)
- Product velocity + batch turn
- Customer LTV
- Revenue forecasting
- Promo ROI

## What features they DON'T get

- Order creation (`supports_orders: False`) — analytics-only
- Real-time push (hourly poll due to RSA JWT 30s TTL — we batch)

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Auth signature rejected | Clock skew (JWT TTL is 30s) | Sync time on our end (NTP) — should be invisible to merchant |
| Dispensary ID wrong | Treez dispensary ID is internal, not the public store ID | Treez partner provides it during onboarding |

## Sales angle

**Opener (California focus):** "You're on Treez — heavy California presence. Budtender-level data is rich on Treez and we use it: who sells what, who upsells, who undersells. That's a margin lever you can't see in Treez's standard reports."

**Why Treez merchants close:**
- California cannabis is hyper-competitive on margin — analytics ROI is obvious
- Budtender performance is a wedge (Treez exposes it well, others don't)

## What blocks live status today

- Treez partner intake filed this week — waiting on approval (Treez partner program acceptance varies by state)
- RSA JWT signer implementation on our side (engineering knows the spec)

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (treez config) + docs/playbook/_status/phase-2-decisions.md (Cannabis #3, Wave 2 partner table)_
