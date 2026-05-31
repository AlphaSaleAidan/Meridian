# Lavu

> Status: **WAVE 1 BUILDING** — registry being rewritten to `reqserv` POST-table shape
> Category: restaurant (iPad-based POS, often used by independent restaurants + bars)
> Auth: API key (X-Api-Key header)

## What you tell the merchant

"Lavu support is shipping this month. We connect with an API key you generate from Lavu's control panel. Backfill takes a few hours, first insights inside 24 hours of connect."

## How the merchant connects (when live)

1. Lavu Control Panel → **Settings → Integrations → API Keys → Create**
2. They paste the key into Meridian's **Settings → POS Connections → Connect Lavu**
3. We test against the Lavu API and start backfill

Typical time to connect (projected): **3 minutes**.

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Orders | hourly poll | 18 months |
| Menu items | daily | full history |
| Employees | daily | full history |
| (Customers — limited) | daily | varies |

Endpoint reference: `https://api.lavu.com/v1` (rewrite in progress to `reqserv` POST-table shape — engineering call)

## What features they get (when live)

Restaurant-focused suite:

- Money Left on Table
- Menu engineering
- Peak hours
- Revenue forecasting
- Discount/promo ROI
- Employee performance
- Order creation supported (`supports_orders: True`) — phone agent can push back orders

## What features they DON'T get

- Customer LTV is limited — Lavu's customer module is optional and not universally enabled
- No camera-side reservation data (Lavu doesn't have reservations natively)

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| API returns malformed JSON | Lavu's older `reqserv` endpoint returns POST-table shape | Engineering rewriting registry handler to match |
| Auth header rejected | Wrong header name (`X-Api-Key` vs `apikey`) | Use exact header per Lavu docs |
| Missing orders | Order saved offline on iPad, not synced | Lavu-side sync issue — outside our control |

## Sales angle

**Opener:** "Are you on Lavu? You've got iPad-level data most POSes don't expose — table turn times, server performance, void patterns. Our agents pull all of that and tell you exactly where you're leaking margin."

**Best fit:** independent restaurants, bars/pubs, small chains (2–5 locations) that picked Lavu specifically for the iPad form factor.

**Watch out:** Lavu has had ownership changes over the years (don't repeat unverified claims about Cygnet/Roller Holdings — flagged unverifiable in Phase 1 source review).

## What blocks live status today

- Registry rewrite to match Lavu's actual `reqserv` POST-table response shape (current implementation expects standard JSON envelope; real shape is different)

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (lavu config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #8, ownership-claim caveat)_
