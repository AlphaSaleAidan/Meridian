# Olo

**Registry key:** `olo` — see `src/services/pos_connectors/registry.py`

## Status
**UNCERTAIN** — config exists, but Olo is **not a POS**. It sits on top of a merchant's actual POS (Toast, Aloha, Micros). Anything we pull is online-channel orders only.

## What it is
Enterprise restaurant digital ordering, delivery, payments, and guest-engagement platform used by 750+ multi-unit brands.

## Vertical & market
- **Primary vertical:** restaurant — almost exclusively enterprise/multi-unit chains and franchisors
- **Estimated NA market presence:** Large within its niche; near-zero among single-location indies
- **Typical merchant profile:** 50+ unit chain or franchise (Five Guys, P.F. Chang's, Portillo's, Denny's, Panda Express, Cold Stone, First Watch, Freddy's, Nando's per olo.com)
- **Geographic concentration:** US-primary

## How to spot the merchant uses it
- Their branded ordering web/app is white-labeled but powered by Olo (often visible in page source)
- Operator says "Olo Dispatch," "Olo Pay," or "Rails"
- They name an underlying POS separately ("we're on Aloha, Olo is online ordering")
- Enterprise org chart with Director of Digital / VP of Off-Premise — not a single-store GM

## Auth method
API key in `Authorization` header (registry: `auth_type: header`). Exact token format (raw vs. `Bearer …`) **not verifiable** — `developer.olo.com` is fully gated; confirm during partner onboarding.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes (digital only) | `/orders` | Does NOT include in-store/POS sales |
| Catalog / items | Yes | `/restaurants/{restaurant_id}/menu` | Olo-configured menu, not POS-of-record |
| Customers | Unknown | — | Not wired |
| Employees | No | — | Olo doesn't own labor data |
| Inventory | No | — | Lives in POS |
| Refunds | Unknown | — | Not wired |
| Order create (push) | Yes | `/restaurants/{restaurant_id}/orders` | `supports_orders: True` |

## Partner program / access requirements
- **Partner program required:** Yes — Developer Portal gated
- **Sign-up URL:** https://developer.olo.com/ (login wall; inquiry via olo.com)
- **Approval timeline:** Enterprise — assume **4–8+ weeks** plus per-brand enablement via corporate IT
- **Cost / revenue share:** Not publicly disclosed

## Sandbox / test environment
- **Available:** Presumed yes (standard for enterprise APIs) — not verified
- **URL:** N/A until partner credentials issued
- **Notes:** Cannot self-serve

## Rate limits
**Unknown — not documented publicly.**

## Webhook / sync model
**Unknown from public sources.** Current registry config is poll-shaped against `/orders`.

## Connect flow (what the merchant does)
1. Brand's corporate Digital/IT opens a ticket with Olo to enable a new partner
2. Olo issues API credentials scoped to the brand (and sometimes specific locations)
3. Credentials handed to Meridian out-of-band — no self-serve OAuth
4. We paste them in and sync the online ordering stream

## Estimated effort to go LIVE (config → production-ready)
**L (1+ months)** after a brand commits. Partnership + per-brand enablement dominate; engineering is minor.

## What blocks LIVE status today
- No verified partner credentials — portal behind login wall
- Auth header format not confirmable from public docs
- No customer-facing connect UI (would be enterprise-bespoke per brand anyway)
- **Fundamental gap:** Olo data alone = digital-channel revenue only

## Common failure modes (for troubleshooting playbook)
- **Symptom:** Numbers way lower than operator says → **Cause:** Olo is online only (often 15–40% of total) → **Fix:** explain scope, ask for actual POS connection
- **Symptom:** Catalog items don't match in-store menu → **Cause:** Olo menu is a curated subset → **Fix:** treat as channel-specific, not source-of-truth

## Strategic notes
Olo's presence in the registry reads as speculative scaffolding — it doesn't fit Meridian's ICP (single-location to small multi-unit on a real POS). For an enterprise chain on Olo we'd want Olo **plus** their underlying POS. Real future play: Meridian as the analytics layer unifying Olo digital + Toast/Aloha in-store for mid-market chains — 2026+ enterprise motion, not today's SMB cycle.

## Recommendation
**DEFER** — leave the config; do not invest in connect UX or partnership pursuit until we have an enterprise-chain ICP and an inbound lead.

**Reasoning:** Off-ICP today, data intrinsically incomplete without the underlying POS, partnership cost high relative to current pipeline.

## Sources consulted
- `/root/Meridian/src/services/pos_connectors/registry.py` (`olo` entry, lines 995–1007)
- https://www.olo.com/ (customer brand list, product scope)
- https://investors.olo.com/ (public company, 750+ brands)
- https://developer.olo.com/ (login wall — API specifics not accessible)
- Live API docs accessed: No (gated)
