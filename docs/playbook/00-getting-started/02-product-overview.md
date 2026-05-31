# Product Overview

## What Meridian is

A platform that connects to a merchant's POS, ingests their transaction history and live feed, and runs a fleet of AI agents on the data. Every insight comes with (1) what's happening, (2) what to do about it, (3) what it's worth in dollars.

## What we connect to

**POS systems** (full live list in `10-pos-integrations/_index.md`):

- **Live today:** Square, Clover, Toast
- **Wave 1 building now (12):** Square, Clover, Toast, Lightspeed Retail, Korona, Shopify POS, CAKE (CSV), Lavu, talech, Lightspeed Restaurant, SkyTab, Cova
- **Cannabis vertical (8):** Cova, Dutchie, Treez, Flowhub, Meadow, Blaze, BioTrack, Indica Online
- **80 total POS systems** in registry; many are CSV-import-only because the vendor has no usable API

**Cameras** (full list in `20-camera-integrations/_index.md`):

- **Officially supported (5):** Hikvision, Dahua, Reolink, UniFi, Axis
- **Not supported (3):** Wyze (current SKUs have no RTSP), Nest (WebRTC-only, $5/merchant fee), Arlo (cloud-only encrypted)
- Hikvision/Dahua handlers also cover their OEM rebrands: LaView, ANNKE, Amcrest, EmpireTech, older Lorex/Honeywell

## What we run on the data

Four tiers of AI agents (full inventory in `30-features/`):

1. **POS Analytics** (~31 agents) — revenue, peak hours, customer LTV, inventory, pricing power, money-left-on-table, basket analysis, employee performance, etc. Tiered 1–5 by data dependency.
2. **Vision** (camera pipeline) — foot traffic counts, queue length, dwell time, zone heatmaps. Anonymous counts only. No facial recognition.
3. **Cross-Reference** (10 agents) — fuses POS + camera. Things like "customers who spent >3 min in display zone had 40% higher tickets," "lost sales from queue abandonment," "path-to-purchase by store layout."
4. **Coordination** — orchestrator + swarm trainer. Schedules the agent fleet, fuses outputs, ranks actions.

## The hook merchants actually care about

The **Money Left on Table** score. One dollar amount, top of dashboard. Roll-up of every individual opportunity the agents found. Click in → see exactly where it's coming from (pricing gaps, peak-hour understaffing, churning regulars, dead inventory). Each line has a dollar amount and a specific action.

That's the demo. Everything else is supporting evidence.

## How it differs from what's already in their POS

| Their POS dashboard | Meridian |
|---------------------|----------|
| What happened (charts) | What to do (actions + dollar amounts) |
| One POS only | Works across Square / Clover / Toast / Lightspeed / 80 others |
| No cross-store comparison | Multi-location rollups |
| Manual reading | AI agents proactively surface findings + alert |
| No camera intelligence | Foot traffic + queue + dwell time analytics |

## What we are not

- Not an inventory tool (we cover it, but we're not MarketMan)
- Not a generic BI tool (no SQL, no dashboards to build, no data team needed)
- Not POS replacement — we sit alongside their existing POS

---

_Last updated: 2026-05-31_
_Sourced from: services/training_video_pipeline/lesson_content.json (lessons 1.2, 2.4) + docs/playbook/_status/phase-2-decisions.md + src/services/pos_connectors/registry.py + src/ai/agents/_
