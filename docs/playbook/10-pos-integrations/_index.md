# POS Integrations — Index

Quick lookup. Before promising anything to a merchant, **check the status column**. Don't sell what's not live.

## Status definitions

| Badge | What it means for you |
|-------|----------------------|
| **LIVE** | Working in production. Promise it. |
| **WAVE 1 BUILDING** | Active engineering, expected within ~30 days. Pre-sell with caveat. |
| **WAVE 1.5 BUILDING** | Phase 2 gap-research adds; registry config landed, build in progress alongside Wave 1. Pre-sell with caveat. |
| **WAVE 2 PARTNER-PENDING** | Partner application filed, waiting on vendor. Don't promise dates. |
| **CSV-ONLY** | No live API; merchant exports CSV from their POS and uploads. Works, but slower (daily, not real-time). |
| **NOT SUPPORTED** | Vendor has no usable API and CSV path is broken/deprecated. Route to alternative. |

## Wave 1 — Sell now (12)

| POS | Status | Category | Doc |
|-----|--------|----------|-----|
| Square | **LIVE** | multi-vertical | [square.md](./square.md) |
| Clover | **LIVE** (token-refresh bug pending fix) | multi-vertical | [clover.md](./clover.md) |
| Toast | **LIVE** (webhooks shipping) | restaurant | [toast.md](./toast.md) |
| Lightspeed Retail | WAVE 1 BUILDING | retail | [lightspeed-retail.md](./lightspeed-retail.md) |
| Korona POS | WAVE 1 BUILDING | retail | [korona-pos.md](./korona-pos.md) |
| Shopify POS | WAVE 1 BUILDING (API bump) | retail | [shopify-pos.md](./shopify-pos.md) |
| CAKE | WAVE 1 BUILDING (CSV path now, API later) | restaurant | [cake.md](./cake.md) |
| Lavu | WAVE 1 BUILDING (registry rewrite) | restaurant | [lavu.md](./lavu.md) |
| talech | WAVE 1 BUILDING (token-auth rewrite) | multi-vertical | [talech.md](./talech.md) |
| Lightspeed Restaurant | WAVE 1 BUILDING + partner app filed | restaurant | [lightspeed-restaurant.md](./lightspeed-restaurant.md) |
| SkyTab | WAVE 1 BUILDING + Shift4 partner app filed | restaurant | [skytab.md](./skytab.md) |
| Cova | WAVE 1 BUILDING + partner intake | cannabis | [cova-pos.md](./cova-pos.md) |

## Wave 1.5 — Retail / Restaurant adds (Phase 2 gap research)

Registry config landed; rep-facing playbooks live. Build is in progress alongside Wave 1.

| POS | Status | Category | Doc |
|-----|--------|----------|-----|
| Heartland Retail | WAVE 1.5 BUILDING (self-serve token — fastest win) | retail | [heartland-retail.md](./heartland-retail.md) |
| Heartland Restaurant | WAVE 1.5 BUILDING (partner program filed) | restaurant | [heartland-restaurant.md](./heartland-restaurant.md) |

**Note:** the existing compound `heartland` registry entry tried to cover Restaurant + Retail + Portico in one config and failed. Wave 1.5 splits these out as distinct connectors. Qualify which Heartland a prospect is on before promising a timeline — Portico is payments-only with no analytics surface.

## Salon / Wellness vertical — Wave 1.5 (new vertical wedge)

Salons are in rep training (lesson 4.3) but had **zero integrations** before Wave 1.5. These two are the wedge.

| POS | Status | Category | Doc |
|-----|--------|----------|-----|
| Boulevard | WAVE 1.5 BUILDING (modern salon/spa, GraphQL) | salon | [boulevard.md](./boulevard.md) |
| Mindbody | WAVE 1.5 BUILDING (wellness anchor — salon/spa/fitness) | salon / wellness | [mindbody.md](./mindbody.md) |

**Vertical notes:** Mindbody is the whole-vertical anchor (salons + spas + fitness studios). Boulevard is the wedge for salons that explicitly chose a modern POS over Mindbody. Booker (Mindbody-owned) and Vagaro are fast-follow connectors after these land. Glofox is NOT a full POS — qualify out.

## Cannabis vertical — Greenlit (9)

| POS | Status | Region | Doc |
|-----|--------|--------|-----|
| Cova | WAVE 1 BUILDING | Canada (#1 wedge) | [cova-pos.md](./cova-pos.md) |
| Greenline POS | WAVE 1.5 BUILDING (BLAZE-owned, AGCO/BCLDB) | Canada (#2) | [greenline-pos.md](./greenline-pos.md) |
| Dutchie | WAVE 2 PARTNER-PENDING (Certified Partner Program) | US (#1) | [dutchie.md](./dutchie.md) |
| Treez | WAVE 2 PARTNER-PENDING (RSA JWT) | US (#2, CA-heavy) | [treez.md](./treez.md) |
| Flowhub | WAVE 2 PARTNER-PENDING | US (CO/MI/MA/OK) | [flowhub.md](./flowhub.md) |
| Meadow | WAVE 1 BUILDING | California boutique/delivery | [meadow.md](./meadow.md) |
| Blaze | WAVE 1 BUILDING | California mid-tier | [blaze.md](./blaze.md) |
| BioTrack | CSV-ONLY (regulatory layer) | state-level | [biotrack.md](./biotrack.md) |
| Indica Online | CSV-ONLY | California boutique | [indica-online.md](./indica-online.md) |

**Cannabis compliance notes:** separate banking/insurance posture (federal Schedule I), PII per state/provincial HIPAA-adjacent rules, no Google/Facebook/LinkedIn ads (direct/event/WOM outbound only).

## Wave 2 — Partner-pending (file on first qualified prospect)

| POS | Status | Notes | Doc |
|-----|--------|-------|-----|
| TouchBistro | WAVE 2 PARTNER-PENDING | Canada wedge; lead with analytics-only framing | [touchbistro.md](./touchbistro.md) |
| SpotOn | WAVE 2 PARTNER-PENDING (slow) | 26+ day partner form wait — file on prospect signal | [spoton.md](./spoton.md) |
| Rezku | WAVE 2 (CSV in meantime) | File on prospect signal | [rezku.md](./rezku.md) |
| Epos Now | WAVE 2 PARTNER-PENDING | File on prospect signal | [epos-now.md](./epos-now.md) |
| Erply | WAVE 2 PARTNER-PENDING | File on prospect signal | [erply.md](./erply.md) |

## CSV-only legacy / niche systems

If a merchant uses one of these, they can upload a CSV. No live API integration. See [_csv-only-systems.md](./_csv-only-systems.md) for the full list with column mappings.

Covers: accu-pos, Aldelo, Cashier Live, Digital Dining, Focus POS, Future POS, NorthStar, PixelPoint, Rain POS, Retail Edge, plus all automotive vertical POSes (Mitchell1, ALLDATA, NAPA TRACS, TireMaster, R.O. Writer, Protractor, Bolt On, AutoVitals, AutoFluent, Omnique) and CSV-only cannabis (BioTrack, Indica Online, Leaf Logix legacy tenants).

## Deprecated — DO NOT pitch as supported

| POS | Why | What to do instead |
|-----|-----|--------------------|
| Upserve | API is dead (`api.upserve.com` returns nothing); ownership flux | If merchant is on Upserve, they likely need to migrate — route to Toast or Square |
| Harbortouch | Sunset → rebranded to SkyTab | Route to SkyTab connect flow |
| Leaf Logix | Acquired by Dutchie 2021; URL says "no longer available" | CSV-only for legacy tenants; recommend Dutchie migration |
| iZettle (standalone) | Duplicate of paypal-zettle | Use paypal-zettle alias |
| Gloria Food | It's an online-ordering widget, not a POS | Find the underlying POS (usually Square/Clover/Toast) and integrate that |
| POS Nation (cannabis tag) | Registry mis-tagged as cannabis; it's actually multi-vertical retail | Use the retail flow if a merchant is on it |

## Enterprise / wrong-fit POSes (don't pursue)

NCR/Aloha, MICROS/Simphony, Brink, Xenial, Qu, Agilysys, Olo — enterprise gates, multi-month partner cycles, wrong fit for SMB rep motion. If a prospect is on one of these and it's a single location, polite decline + route to a smaller competitor.

## Can't-connect list (informational — for rep awareness)

Vendor has no API at all. If a merchant uses these, the answer is "CSV upload only" (where a CSV path exists) or "we can't ingest from this POS."

- **Restaurant on-prem:** Aldelo, Digital Dining, Focus POS, Future POS, PixelPoint, NorthStar
- **Retail/Pharmacy:** Cashier Live, Rain POS, Retail Edge
- **Automotive (entire vertical):** Mitchell1, ALLDATA Manage, NAPA TRACS, TireMaster, R.O. Writer, Protractor, Bolt On, AutoVitals, AutoFluent, Omnique
- **Restaurant sunset/dead:** Upserve, Harbortouch
- **Cameras:** Wyze (current SKUs), Nest (current-gen), Arlo

---

_Last updated: 2026-05-31_
_Sourced from: docs/playbook/_status/phase-2-decisions.md (Wave 1 + Wave 1.5 + Cannabis greenlight) + src/services/pos_connectors/registry.py (85 entries — 80 baseline + 5 Wave 1.5 adds) + docs/playbook/_status/pos-expansion-candidates.md (gap research)_
