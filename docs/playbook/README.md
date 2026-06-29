# Meridian Rep Playbook

The full rep-facing knowledge base. Everything you need to find a prospect, run a discovery call, demo the product, close the deal, onboard the merchant, troubleshoot what breaks, and protect the recurring commission.

**Print this nav. Live in it. The cheat sheets in `50-cheatsheets/` are the most-used pages.**

---

## Start here (if you're new)

1. [00-getting-started/01-welcome.md](./00-getting-started/01-welcome.md) — what we sell and why it works
2. [00-getting-started/02-product-overview.md](./00-getting-started/02-product-overview.md) — the product in one page
3. [00-getting-started/03-pricing-commission.md](./00-getting-started/03-pricing-commission.md) — plans + your 70% commission math
4. [00-getting-started/04-pipeline-setup.md](./00-getting-started/04-pipeline-setup.md) — how the portal Leads pipeline works
5. [00-getting-started/05-first-week.md](./00-getting-started/05-first-week.md) — day-by-day plan for your first 5 days

## Cheat sheets (use every day)

| Sheet | When to use |
|-------|-------------|
| [50-cheatsheets/pos-by-vertical.md](./50-cheatsheets/pos-by-vertical.md) | Discovery — what POS × vertical means for pitch + tier |
| [50-cheatsheets/discovery-questions.md](./50-cheatsheets/discovery-questions.md) | Every discovery call — the core 5 + vertical deep-dives |
| [50-cheatsheets/objection-handlers.md](./50-cheatsheets/objection-handlers.md) | When prospect pushes back — exact lines that work |
| [50-cheatsheets/tier-feature-comparison.md](./50-cheatsheets/tier-feature-comparison.md) | At the close — which plan to recommend |
| [50-cheatsheets/one-pager-printable.md](./50-cheatsheets/one-pager-printable.md) | Print + leave behind after the demo |

## POS integrations (10-pos-integrations/)

**ALWAYS check status before promising integration.** [10-pos-integrations/_index.md](./10-pos-integrations/_index.md) is the master matrix.

### Live today
- [square.md](./10-pos-integrations/square.md)
- [clover.md](./10-pos-integrations/clover.md)
- [toast.md](./10-pos-integrations/toast.md)

### Wave 1 — building this month
- [lightspeed-retail.md](./10-pos-integrations/lightspeed-retail.md)
- [korona-pos.md](./10-pos-integrations/korona-pos.md)
- [shopify-pos.md](./10-pos-integrations/shopify-pos.md)
- [cake.md](./10-pos-integrations/cake.md)
- [lavu.md](./10-pos-integrations/lavu.md)
- [talech.md](./10-pos-integrations/talech.md)
- [lightspeed-restaurant.md](./10-pos-integrations/lightspeed-restaurant.md)
- [skytab.md](./10-pos-integrations/skytab.md)
- [cova-pos.md](./10-pos-integrations/cova-pos.md) — Canada cannabis #1
- [meadow.md](./10-pos-integrations/meadow.md) — California cannabis boutique
- [blaze.md](./10-pos-integrations/blaze.md) — California cannabis mid-tier

### Cannabis (greenlit vertical)
- [cova-pos.md](./10-pos-integrations/cova-pos.md) — Canada (Wave 1)
- [dutchie.md](./10-pos-integrations/dutchie.md) — US #1 (Wave 2 partner-pending)
- [treez.md](./10-pos-integrations/treez.md) — US #2 (Wave 2 partner-pending)
- [flowhub.md](./10-pos-integrations/flowhub.md) — US #3 (Wave 2)
- [meadow.md](./10-pos-integrations/meadow.md), [blaze.md](./10-pos-integrations/blaze.md) — California (Wave 1)
- [biotrack.md](./10-pos-integrations/biotrack.md) — state regulatory (CSV)
- [indica-online.md](./10-pos-integrations/indica-online.md) — California boutique (CSV)

### Wave 2 — partner-pending
- [touchbistro.md](./10-pos-integrations/touchbistro.md) — Canada
- [spoton.md](./10-pos-integrations/spoton.md) — slow partner cycle
- [rezku.md](./10-pos-integrations/rezku.md)
- [epos-now.md](./10-pos-integrations/epos-now.md)
- [erply.md](./10-pos-integrations/erply.md)

### CSV-only legacy
- [_csv-only-systems.md](./10-pos-integrations/_csv-only-systems.md) — one doc covers all 28 CSV-only POSes (automotive vertical, legacy restaurant on-prem, etc.)

### Deprecated / not supported (do NOT pitch)
- Upserve (dead API), Harbortouch (sunset → SkyTab), Leaf Logix (acquired by Dutchie), iZettle (duplicate of paypal-zettle), Gloria Food (not a POS), POS Nation (registry mis-tag)
- Enterprise wrong-fit: NCR/Aloha, MICROS/Simphony, Brink, Xenial, Qu, Agilysys, Olo
- See [_index.md](./10-pos-integrations/_index.md) for full deprecate list

## Camera integrations (20-camera-integrations/)

[20-camera-integrations/_index.md](./20-camera-integrations/_index.md) is the master.

Cameras require the **camera intelligence add-on** (see `20-camera-integrations/_index.md` for pricing guidance).

### Officially supported (5)
- [hikvision.md](./20-camera-integrations/hikvision.md) — covers LaView/ANNKE/EmpireTech/older Lorex/older Honeywell
- [dahua.md](./20-camera-integrations/dahua.md) — covers Amcrest, newer Lorex
- [reolink.md](./20-camera-integrations/reolink.md) — also our recommended budget pick (~$60 RLC-510A)
- [unifi.md](./20-camera-integrations/unifi.md) — RTSPS on port 7441
- [axis.md](./20-camera-integrations/axis.md) — only federal-eligible brand (NDAA/TAA + CAGE 3DJU8)

### Not supported (3)
- [wyze.md](./20-camera-integrations/wyze.md), [nest.md](./20-camera-integrations/nest.md), [arlo.md](./20-camera-integrations/arlo.md) — all recommend $60 Reolink alongside

### Universal diagnostic
- [_how-to-connect-any-camera.md](./20-camera-integrations/_how-to-connect-any-camera.md) — if a merchant's camera isn't on either list

## Features (30-features/)

[30-features/_index.md](./30-features/_index.md) is the master.

**47 total features documented:**
- **30 POS analytics agents** (`pos-analytics/`) — all included in base product (data complexity tiers 1–5, internal classification)
- **10 cross-reference agents** (`cross-reference/`) — camera intelligence add-on required; fuses POS × camera
- **5 vision modules** (`vision/`) — internal pipeline (rtsp_handler, detector, people_counter, line_counter, pipeline)
- **2 coordination components** (`coordination/`) — cross_reference_orchestrator, swarm_trainer

[30-features/_data-requirements-matrix.md](./30-features/_data-requirements-matrix.md) — which features need which data from which POSes. **Use this before every discovery to set realistic expectations.**

## Troubleshooting (40-troubleshooting/)

When something breaks. Start at [40-troubleshooting/_index.md](./40-troubleshooting/_index.md) or [40-troubleshooting/_decision-tree.md](./40-troubleshooting/_decision-tree.md).

| Symptom | Doc |
|---------|-----|
| Connection won't work / 401 errors | [pos-connection-failures.md](./40-troubleshooting/pos-connection-failures.md) |
| Camera offline | [camera-offline.md](./40-troubleshooting/camera-offline.md) |
| Numbers don't match the POS | [data-mismatch.md](./40-troubleshooting/data-mismatch.md) |
| Backfill stuck | [backfill-stuck.md](./40-troubleshooting/backfill-stuck.md) |
| Insights missing / wrong | [insights-not-appearing.md](./40-troubleshooting/insights-not-appearing.md) |
| Billing dispute | [billing-issues.md](./40-troubleshooting/billing-issues.md) |

---

## Search hints

If you can't remember which file something's in, ctrl-F the playbook root for these terms:

| Looking for | Try searching |
|-------------|---------------|
| A specific POS | The POS name in `10-pos-integrations/` |
| Camera compatibility | Brand name in `20-camera-integrations/` |
| What does agent X do | Agent name in `30-features/pos-analytics/` or `30-features/cross-reference/` |
| Why is this thing not working | Symptom keyword in `40-troubleshooting/` |
| Pricing in CAD | "CA$" in `00-getting-started/03-pricing-commission.md` or `50-cheatsheets/tier-feature-comparison.md` |
| The 60-second pitch | `50-cheatsheets/objection-handlers.md` (top) |
| 5 discovery questions | `50-cheatsheets/discovery-questions.md` (top) |
| Federal / NDAA / CAGE / Section 889 | `20-camera-integrations/axis.md` |
| Cannabis compliance | `10-pos-integrations/cova-pos.md` or any cannabis POS doc |
| "Money Left on Table" definition | `30-features/pos-analytics/money_left_on_table.md` |
| Token refresh / Clover 401 | `40-troubleshooting/pos-connection-failures.md` |
| CSV upload + automotive | `10-pos-integrations/_csv-only-systems.md` |

## Source-of-truth reference

The `_status/` directory holds upstream reference material — NOT rep-facing. Don't link merchants to these. Maintainers can find:

- `_status/phase-2-decisions.md` — Aidan's prioritization calls (Wave 1/2, deprecate, cannabis greenlight)
- `_status/cameras/` — research-swarm output on brands not in the official supported list (Eufy, Ring, Verkada, Avigilon, Bosch, Swann, Camect, Lorex, Amcrest)
- `_status/cameras-matrix.md` — master camera status
- `_status/pos-expansion-candidates.md` — POSes being evaluated for the registry

## Open questions

Items flagged during Phase 3 that need confirmation: [_open-questions.md](./_open-questions.md).

## Anti-goals (what NOT to do)

- Don't pitch deprecated POSes (Upserve, Harbortouch, Leaf Logix, iZettle standalone) as supported
- Don't promise features that aren't in `src/ai/agents/` — if it's not documented in `30-features/`, it doesn't exist
- Don't oversell camera intelligence to merchants with unsupported cameras — sell base product, upsell camera add-on later when they have a supported camera
- Don't free-form discount — only annual prepay (2 months free) or referral discount (50% off for 3 active referrals)
- Don't guarantee specific dollar outcomes — use averages and ranges only (see `50-cheatsheets/objection-handlers.md` for compliance-safe phrasing)
- Don't ship videos or video scripts from this playbook — it's markdown for the rep portal

---

_Last updated: 2026-06-29_
_Maintainer: Phase 3 rebuild — see [_open-questions.md](./_open-questions.md) for items that still need Aidan's input._
_Sourced from: docs/playbook/_status/phase-2-decisions.md + src/services/pos_connectors/registry.py (80 POSes) + src/ai/agents/ (47 features) + src/camera/ + src/errors.py + services/training_video_pipeline/lesson_content.json + docs/customer-sop.md_
