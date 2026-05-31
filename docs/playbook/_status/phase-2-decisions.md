# Phase 2 Decisions

Aidan's calls on the Phase 1 prioritization checkpoint, 2026-05-31. Drives Phase 3 (content rebuild) and Phase 5 (integration buildout waves).

---

## Wave 1 — BUILD NOW (12 + cannabis additions)

Confirmed:

1. **Square** — LIVE, harden UX
2. **Clover** — LIVE, fix token refresh (silent 401 bug — see Production Issues)
3. **Toast** — LIVE, ship webhooks + deep-link "Add Now"
4. **Lightspeed Retail** — READY config, build OAuth UI
5. **Korona POS** — READY, build connect UI
6. **Shopify POS** — bump API version off legacy `2024-01`, plan GraphQL migration
7. **CAKE** — ship CSV path now (Sysco channel ~5k restaurants); API stays WAIT
8. **Lavu** — rewrite registry to `reqserv` POST-table shape, ship
9. **talech** — token-auth REST rewrite (no Elavon partner gate)
10. **Lightspeed Restaurant** — fix registry + start partner app this week
11. **SkyTab** — start Shift4 partner app this week (Revel migration tailwind)
12. **Cova** — fix registry + start partner intake this week (Canada cannabis #1 wedge)

---

## Cannabis vertical — GREENLIT

**Decision: GO.** Accept the banking/compliance/marketing overhead.

Build order:

1. **Cova** (Canada — already in Wave 1)
2. **Dutchie** — US dispensary #1; partner intake this week
3. **Treez** — US #2 (CA-heavy); needs RSA JWT signer (30s TTL); partner intake this week
4. **Flowhub** — US #3 (CO/MI/MA/OK); partner intake
5. **Meadow** — CA boutique/delivery niche
6. **Blaze** — CA mid-tier
7. **BioTrack** — state regulatory layer (complementary, not competing)
8. **Indica Online** — CA boutique long-tail

Hard prerequisites:
- Separate banking + insurance posture (federal Schedule I)
- PII handling per state HIPAA-adjacent rules
- Direct/event/WOM outbound only (Google/Facebook/LinkedIn restrict cannabis ads)

---

## Wave 2 — Partner applications to file THIS WEEK

| POS | Vendor contact | Notes |
|-----|---------------|-------|
| Lightspeed Restaurant | K-Series partner portal | Wave 1 dependency |
| SkyTab | Shift4 partner program | Wave 1 dependency; Revel migration ~18k locations |
| Cova | Cova partner intake | Wave 1 dependency; Canada cannabis #1 |
| TouchBistro | `integratedpartners@touchbistro.com` | Canada wedge; lead with analytics-only/read-only framing |
| Dutchie | Certified Partner Program (launched Aug 2025) | Cannabis #1 |
| Treez | Treez partner program | Cannabis #2 |

**Holding for now:**
- **SpotOn** — public reports show 26+ days just to receive their partner form. File on first qualified prospect, not speculatively.
- **NCR/Aloha, MICROS/Simphony, Brink, Xenial, Qu, Agilysys, Olo** — enterprise gates, wrong fit for SMB rep motion. Do not pursue.
- **Epos Now, Erply, Rezku, Squirrel, Shop-Ware** — file on prospect signal, not speculatively.

---

## Deprecate from training (strip these — we'd be lying if we said we support them)

| Item | Why | Action |
|------|-----|--------|
| iZettle (registry duplicate) | Same product as `paypal-zettle`, two registry keys | Add alias map (`izettle` → `paypal-zettle`) in loader; remove standalone after one release |
| Upserve | `api.upserve.com` returns no HTTP response; ownership changed 2026 | Mark connector as CSV-import-only stub; full deprecate if no Skyview signal in 90 days |
| Harbortouch | Shift4 rebranded to SkyTab; dev URL redirects to SkyTab | Strip from outbound; inbound routes to SkyTab connect flow |
| Leaf Logix | Acquired by Dutchie Mar 2021; URL says "no longer available" | Keep CSV for legacy tenants only; strip from active training |
| POS Nation category (`cannabis` in registry — WRONG) | POS Nation has no cannabis product; it's multi-vertical retail | Fix registry `category` to `retail` immediately — prevents compliance logic firing on wrong merchants |
| Gloria Food mis-categorization | It's an online-ordering widget on top of real POS, not a POS itself | Reclassify; route inbound to underlying POS (Square/Clover/Toast) |
| Aldelo/Lavu/Rain POS "owned by Roller Holdings/Cygnet" claims | Unverifiable — flagged by Phase 1 source review | Strip ownership claims from training |
| Protractor "acquired into Solera" | Unverified | Caveat any quoting |

---

## Cameras — official support list (expanded after gap research)

**OFFICIALLY SUPPORTED (10):**

| Brand | Why | Critical gotcha |
|-------|-----|-----------------|
| Hikvision | Dominant SMB; one URL pattern covers OEMs (LaView/ANNKE/older Honeywell) | NDAA 889 — qualify federal/critical-infra customers OUT |
| Dahua | One URL pattern covers OEMs (Amcrest/EmpireTech/older Lorex) | Same NDAA 889 caveat |
| Reolink | Huge SMB footprint (cheap PoE bullets) | PoE/wired ONLY — battery SKUs (standalone Argus) NOT SUPPORTED |
| UniFi | Common in modern/tech-savvy SMBs | RTSPS (TLS) on **port 7441**, not plain RTSP — handler must support TLS-wrapped RTSP |
| Axis | NDAA/TAA + federal CAGE 3DJU8 — unlocks federal customers no other brand serves cleanly | Premium tier; low SMB volume but uniquely required for fed |
| **Amcrest** | Dahua OEM | Link to dahua.md — same URL pattern |
| **Bosch** | Inteox/Flexidome professional tier | Defaults to H.265 — URL must include `&h26x=4` to force H.264 for analytics pipeline |
| **Avigilon** (Unity-line) | Premium retail/enterprise | RTSP URL only generates AFTER a compression profile is configured — empty field is not a bug |
| **Verkada** (LAN) | Cloud-native vendor that surprisingly ships standard RTSP on every current camera — multi-site retail unlock | LAN-only (RFC1918); must enable per-camera in Command admin |
| **Lorex** (N-series + wired PoE) | Still effectively Dahua under the hood | Same NDAA blocker as Dahua; Skywatch moving to Vivotek on new lines — re-check 2027 |

**BEST EFFORT (3):** Eufy wired-only (SoloCam wired/Indoor/Floodlight wired), Swann wired DVR/NVR only, Avigilon Alta cloud-line.

**NOT SUPPORTED (5):**

| Brand | Why | Rep response |
|-------|-----|--------------|
| Wyze | Stock firmware has no RTSP; current SKUs (v4/OG/v3 Pro/Floodlight/Battery) have NO RTSP at all | Recommend $60 PoE replacement (Reolink RLC-510A or Hikvision DS-2CD2043G2-I) alongside |
| Nest | Current-gen all WebRTC-only; SDM RTSP single-client + 5-min sessions + $5/merchant Device Access fee | Same — keep Nest for mobile alerts |
| Arlo | Cloud-only encrypted streams, no RTSP/ONVIF/local | Same |
| **Ring** | "ONVIF support" article is misleading — Ring Edge ingests 3rd-party ONVIF; Ring's own cameras don't speak ONVIF or RTSP | Treat exactly like Arlo |
| **Camect** | NOT a camera vendor — AI gateway that ingests other cameras; no RTSP rebroadcast | Bypass Camect; integrate with the cameras underneath it |

**Field warnings (add to troubleshooting):**
- Swann has 3 different OEM URL families (Raysharp current / Hikvision pre-2020 / Dahua 2014–2018) — identify by model number
- Swann kits sometimes remap RTSP off port 554 to **1025 or 1085** — silent failure mode
- Eufy is per-SKU fragmented within product families — verify exact model, not family name

Full research at `/root/Meridian/docs/playbook/_status/_how-to-connect-any-camera.md` and the 17 brand files at `/root/Meridian/docs/playbook/_status/cameras/`.

---

## POSes we CAN'T connect to — vendor has no API at all (informational, no action)

For rep training: if a merchant uses any of these, the answer is "CSV upload only" (where a CSV exists) or "we can't ingest from this POS." Don't promise an API timeline.

**Restaurant on-prem:** Aldelo, Digital Dining, Focus POS, Future POS, PixelPoint, NorthStar (vendor unverified)

**Retail / Pharmacy:** Cashier Live, Rain POS, Retail Edge

**Automotive (full vertical):** Mitchell1, ALLDATA Manage, NAPA TRACS, TireMaster, R.O. Writer, Protractor, Bolt On, AutoVitals, AutoFluent, Omnique

**Restaurant sunset/dead:** Upserve (DEAD API), Harbortouch (brand sunset → SkyTab)

**Cameras:** Arlo, Wyze (current SKUs), Nest (current-gen)

---

## POS registry expansion (Wave 1.5 — adds from gap research)

Phase 1 missed the salon/wellness vertical entirely + a clean bank-channel consolidation. Adding these to Wave 1:

### High-priority adds (build alongside Wave 1)

| POS | Vertical | Why | Auth | Docs |
|-----|----------|-----|------|------|
| **Boulevard** | Salon (modern) | Salon vertical is in training already; zero coverage today; GraphQL Admin API, self-serve | OAuth | developers.joinblvd.com |
| **Mindbody** | Wellness anchor (salon/spa/fitness) | Whole-vertical wedge — anchor connector for all wellness merchants | OAuth + OIDC | developers.mindbodyonline.com |
| **Heartland Retail** | Multi-vertical retail | Self-serve bearer tokens — only tractable Heartland branch; S-effort, fastest win on the entire add list | API token | dev.retail.heartland.us |
| **Heartland Restaurant** (Genius) | Restaurant | ~35k venues; distinct from the compound `heartland` registry entry; 7shifts and others integrate directly | API key | heartland.us/partners/developers |
| **Greenline POS** | Cannabis (Canada) | BLAZE-owned Canadian cannabis POS; AGCO/BCLDB compliant; open REST + webhooks. Fits cannabis greenlight + Canada portal directly | API key + webhooks | getgreenline.co |

### Lower-priority adds (build on demand)

| POS | Why |
|-----|-----|
| **Booker** (Mindbody-owned) | Salon vertical fast-follow after Mindbody lands |
| **Vagaro** | Salon vertical mid-tier — public dev docs |
| **Ecwid** (Lightspeed-owned) | Online-retail micro-merchants; REST API |
| **Foodics** | MENA restaurant chain — opportunistic |
| **Mariana Tek** | Fitness boutique (Xponential brands) |
| **GoTab** | Modern QR-order restaurant |
| **Linga** | Restaurant chain, public partner program |

### Clover aliases (no new connectors needed — add `aliases` field)

Bank-channel "POS" products are all rebranded Clover. Single config change in `registry.py` to support all of them via the existing `clover` connector:

- PNC POS, Wells Fargo Merchant Services, Worldpay POS, TSYS POS, Global Payments Genius, Fiserv (non-Clover-branded) — all route to Clover OAuth

### Parent-product aliases (no new connectors)

- Toast Now POS → Toast
- Square for Restaurants → Square
- Shopify Lite / Starter / POS Pro → Shopify POS

### Skipped (with reasons)

22 candidates qualified out: 7shifts (labor, not POS), Restaurant365 (back-office), MarketMan (inventory layer), Punchh (loyalty), ChowNow / Lunchbox / Olo-adjacent (ordering, not POS), Veeqo / Brightpearl / Cin7 (ERP), Glofox (membership), DAVO / Avalara (tax), and the off-ICP enterprise/international remainder.

### Already covered (false alarms)

11 candidates were confirmed as already in registry under different names (Posist = Restroworks metadata-only update, Vend = Lightspeed Retail X-Series, Revel Express = Revel, Lavu Lite = Lavu, etc.).

### Source

Full research at `/root/Meridian/docs/playbook/_status/pos-expansion-candidates.md` — 50 candidates evaluated, primary-source docs cited per entry.

---

## Production issues surfaced during Phase 1 (separate from training)

1. **Clover OAuth token expiry** — `src/clover/oauth.py` has a comment claiming tokens don't expire. Clover docs now say they DO. Long-lived merchants will silently 401. **Severity: high.** Needs fix as separate PR.
2. **22+ registry config bugs** — wrong base URLs, wrong auth schemes, wrong endpoint paths across the 80 POS entries. Documented in each playbook entry's "What blocks LIVE status today" section. Address as part of Phase 5 buildout.

---

## What unblocks now

- **Phase 3 content swarm fires immediately** using these decisions as input
- **Phase 5 Wave 1 engineering** can begin in parallel (3 POSes/week cadence)
- **Camera expansion swarm** runs in parallel; outcomes update cameras matrix before Phase 4 portal rewrite
