# Mindbody

> Status: **WAVE 1.5 BUILDING — wellness anchor (salon/spa/fitness)**
> Category: salon / wellness (the whole-vertical anchor connector)
> Auth: Public API v6 — API Key + SiteId headers; OAuth + OIDC for user-scoped queries

## What you tell the merchant

"Mindbody is our wellness anchor connector — once we have Mindbody live, we cover salons, spas, and fitness studios in one integration. You'll request an API key from Mindbody's developer portal, grab your SiteId from your Mindbody admin, and paste both into Meridian. First insights inside 24 hours of connect."

## How the merchant connects (when live)

1. **developers.mindbodyonline.com** → request **Public API key** (free tier supports analytics-only use)
2. In Mindbody admin → **Settings → Business Information** → copy the **SiteId** (numeric)
3. Paste both into Meridian's **Settings → POS Connections → Connect Mindbody**
4. We hit `/site/sites` to verify and start the backfill
5. Multi-location merchants paste one SiteId per location

Typical time to connect (projected): **5 minutes** (API key approval is usually same-day; longer for first-time developer accounts).

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Sales | hourly poll | 18 months |
| Services (catalog) | daily | full history |
| Clients (customers) | daily | full history (PII-protected) |
| Staff (employees / instructors) | daily | full history |

Endpoint reference: `https://api.mindbodyonline.com/public/v6`

## What features they get (when live)

Wellness-tuned suite:

- Money Left on Table (no-shows, late cancels, unfilled class slots)
- Customer LTV + churn (retention is the wellness margin lever)
- Class/service utilization (fill rate by time slot)
- Pricing power per service tier (membership vs drop-in)
- Employee / instructor performance (revenue per instructor, class fill, rebook)
- Discount/promo ROI (intro offers, package deals)

## What features they DON'T get

- Order creation (`supports_orders: False`) — analytics-only
- Booker merchants need the separate Booker connector (same Mindbody parent, but different API surface — see [_index.md](./_index.md) for Booker status)
- Consumer-facing booking app data — we read the business-side Public API only

## Common failure modes (projected)

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 on every call | Wrong SiteId for the location | Multi-location merchants need per-location SiteIds (one credential set per location) |
| Session expired mid-backfill | Mindbody session tokens shorter than typical POS | Connector handles re-auth automatically; user shouldn't see this |
| Staff schema doesn't match expected employees | Mindbody splits staff vs instructors differently than typical POS employee model | Connector layer normalizes; reps may see "instructor" labels in staff reports |
| Missing client PII | Wellness client privacy rules (region-specific) | We honor Mindbody's PII flags |

## Sales angle

**Opener (any wellness vertical):** "If you're on Mindbody — and you probably are, it's the wellness default — we pull your sales, your clients, your no-shows, and your instructor performance into one view that tells you exactly which class slots are losing money and which clients are about to lapse."

**Why Mindbody is the wellness wedge:**
- Mindbody is THE wellness anchor — owning this connector unlocks salons, spas, and fitness studios in one build
- Booker (also Mindbody-owned) uses a similar API surface — fast-follow connector after Mindbody lands
- Wellness operators care about retention and utilization above all else — we surface both natively
- Self-serve dev portal — no partner gate (unlike Cova/Dutchie cannabis)

**Competitive notes:** Boulevard is the wedge for salons that chose a modern POS over Mindbody. Mariana Tek is the wedge for boutique fitness (Xponential brands) when that opens up. Glofox is NOT a full POS — qualify those out.

## What blocks live status today

- Per-site SiteId provisioning UX (multi-location merchants need a clean way to add multiple locations)
- Staff/instructor schema normalization (Mindbody's model differs from typical POS employee shape)
- First Mindbody merchant for beta validation

---

_Last updated: 2026-05-31_
_Sourced from: src/services/pos_connectors/registry.py (mindbody config) + docs/playbook/_status/phase-2-decisions.md (Wave 1.5 adds, wellness anchor framing) + docs/playbook/_status/pos-expansion-candidates.md (mindbody high-priority entry)_
