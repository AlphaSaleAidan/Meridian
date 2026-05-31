# POS Matrix — All 79 Systems

Single-page scan of every POS playbook entry. Sorted by (1) Recommendation priority (BUILD NOW → WAIT → DEFER → DEPRECATE) then (2) Status tier within each group.

**Status legend:** LIVE / READY / NEEDS PARTNERSHIP / CSV ONLY / OUTDATED CONFIG / DEAD API / UNCERTAIN / DEPRECATED.

**Effort legend:** S (1–3 days) / M (1–2 weeks) / L (1+ months) / XL (custom partnership).

---

## BUILD NOW

| POS | Vertical | Status | Effort | Recommendation | Key blocker | Strategic note |
|-----|----------|--------|--------|----------------|-------------|----------------|
| [square.md](./pos/square.md) | Multi-vertical | LIVE | N/A | BUILD NOW | None — production | Highest-volume SMB integration; self-serve OAuth, no partner gate. |
| [clover.md](./pos/clover.md) | Multi-vertical | LIVE | N/A | BUILD NOW | Token refresh not yet implemented (silent 401 risk) | Largest US SMB POS via Fiserv bank/ISO channel; "we speak Clover natively" wedge. |
| [toast.md](./pos/toast.md) | Restaurant | LIVE | M per merchant | BUILD NOW | Per-merchant Toast Partner Program "Add Now" gate (2–4 wks) | Dominant US restaurant POS; we are an approved partner but merchant must click install. |
| [lightspeed-retail.md](./pos/lightspeed-retail.md) | Retail | READY | M | BUILD NOW | No customer-facing OAuth UI; missing `/Account.json` discovery step | Large specialty-retail base, analytics-friendly buyers; self-serve OAuth, no partner approval. |
| [korona-pos.md](./pos/korona-pos.md) | Retail | READY | S–M | BUILD NOW | No connect UI; base_url hardcoded vs. merchant's numbered host shard | Self-serve basic auth, zero partner gate; strong fit for smoke-shop/convenience ICP. |
| [shopify-pos.md](./pos/shopify-pos.md) | Retail | UNCERTAIN | M | BUILD NOW | REST `2024-01` past Shopify support window; needs version bump or GraphQL migration | Huge retail TAM, growing F&B; self-serve OAuth via custom apps. |
| [cova-pos.md](./pos/cova-pos.md) | Cannabis | NEEDS PARTNERSHIP | L | BUILD NOW | Wrong base_url + auth_type in registry; no partner approval | ~70% of Canadian dispensaries; THE Canada-cannabis wedge for meridian.tips. |
| [cake.md](./pos/cake.md) | Restaurant | OUTDATED CONFIG | S CSV / L API | BUILD NOW (CSV) | API path needs Mad Mobile partner intro; CSV columns unvalidated | Sysco-channel distribution = ~5k restaurants absorbable via one-click CSV mapping. |
| [lavu.md](./pos/lavu.md) | Restaurant | OUTDATED CONFIG | M | BUILD NOW | Registry config (host, auth, paths) doesn't match `reqserv` POST-table shape | Self-serve credentials + high-fit pizzeria/bar/QSR ICP; fastest win after registry rewrite. |
| [talech.md](./pos/talech.md) | Multi-vertical | CSV ONLY (real API exists) | M | BUILD NOW | Registry stuck on `csv_only`; needs token-auth REST rewrite | Self-serve merchant tokens = no Elavon partner gate; wedge into Elavon/US Bank book. |
| [skytab.md](./pos/skytab.md) | Restaurant | NEEDS PARTNERSHIP | XL | BUILD NOW (partnership track) | No Shift4 partner agreement; registry has wrong API (payments, not POS) | Shift4 migrating ~18k Revel locations onto SkyTab — every Revel prospect is a SkyTab prospect in 12–24 months. |
| [lightspeed-restaurant.md](./pos/lightspeed-restaurant.md) | Restaurant | OUTDATED CONFIG | L | BUILD NOW (start partner app now) | base_url dead; auth_type wrong (needs OAuth auth-code, not bearer); endpoint paths wrong | Consolidated rollup of Kounta/iKentoo/Upserve/Breadcrumb — top-10 by combined merchant count globally. |

## WAIT (revisit Q3 or on prospect signal)

| POS | Vertical | Status | Effort | Recommendation | Key blocker | Strategic note |
|-----|----------|--------|--------|----------------|-------------|----------------|
| [erply.md](./pos/erply.md) | Retail | READY | M | WAIT | No connect UI; missing session-refresh + regional endpoint discovery | Correct config but 1000/hr cap + 1-hr session refresh; build on first multi-location chain inbound. |
| [shop-ware.md](./pos/shop-ware.md) | Automotive | NEEDS PARTNERSHIP | L | WAIT (DEFER per source) | No API Partner relationship; auth header format unverified | One of 3 modern cloud SMS leaders; only worth pursuing in committed automotive expansion. |
| [touchbistro.md](./pos/touchbistro.md) | Restaurant | NEEDS PARTNERSHIP | XL | WAIT | No signed integration partner agreement; gatekeeper protects competitive migration | Toronto HQ + TD Bank channel = highest-priority Canada restaurant target; relationship game. |
| [spoton.md](./pos/spoton.md) | Restaurant | NEEDS PARTNERSHIP | XL | WAIT (start intake now) | No partner agreement; auth_type wrong (needs `x-api-key`, not bearer); paths unvalidated | Top-5 US restaurant POS, gaining share vs Toast; intake form alone takes 26+ days. |
| [epos-now.md](./pos/epos-now.md) | Multi-vertical | NEEDS PARTNERSHIP | L | WAIT | No AppStore developer registration; UK-tilted base | UK expansion lever; build on demand from US multi-location merchant or UK push. |
| [rezku.md](./pos/rezku.md) | Restaurant | NEEDS PARTNERSHIP | M | WAIT | Registry is `csv_only`; needs partner email + connector upgrade | Punches above weight in independent bars; cheap to wire once a merchant deal triggers email to support. |
| [biotrack.md](./pos/biotrack.md) | Cannabis | OUTDATED CONFIG | L | WAIT | Registry says `csv_only` but real per-state JSON/XML API exists; needs per-state routing + licensee-credential storage | Regulatory rail in BioTrack states; complements rather than competes with Dutchie. NY migrating to Metrc Q1 2026. |
| [meadow.md](./pos/meadow.md) | Cannabis | NEEDS PARTNERSHIP (soft) | M | WAIT (if cannabis greenlit) | No partner intro; CA-only footprint; endpoints unvalidated | Captures CA boutique/delivery segment Dutchie/Treez underserve; lighter partner gate than peers. |
| [treez.md](./pos/treez.md) | Cannabis | NEEDS PARTNERSHIP | L | WAIT (if cannabis greenlit) | No partner app filed; need RSA JWT signer (30s TTL); no `treez/` module | ~30% of CA cannabis; #2 US dispensary POS after Dutchie. |
| [flowhub.md](./pos/flowhub.md) | Cannabis | NEEDS PARTNERSHIP | L | WAIT (if cannabis greenlit) | No partner intake submitted; no Swagger; endpoints unvalidated | #3 US dispensary POS (CO/MI/MA/OK); bundle with Dutchie+Treez or skip all three. |
| [indica-online.md](./pos/indica-online.md) | Cannabis | OUTDATED CONFIG | M–L | WAIT (if cannabis greenlit) | Registry CSV stub contradicts real Open API; docs portal gated | Mid-tier CA cannabis; fast-follow after Dutchie/Cova/Treez to cover boutique long tail. |
| [squirrel.md](./pos/squirrel.md) | Restaurant/Hospitality | NEEDS PARTNERSHIP | XL | WAIT | No partner relationship; no public dev portal; registry unvalidated | Canadian-HQ (BC); real footprint in CA full-service + hotel F&B for the Meridian Canada portal. |
| [leaf-logix.md](./pos/leaf-logix.md) | Cannabis | CSV ONLY / sunset | S CSV / XL API | WAIT | Product sunset; tenants migrating to Dutchie | Legacy MSO footprint inside Dutchie; CSV mapping is courtesy bridge only. |

## DEFER (do not pursue)

| POS | Vertical | Status | Effort | Recommendation | Key blocker | Strategic note |
|-----|----------|--------|--------|----------------|-------------|----------------|
| [loyverse.md](./pos/loyverse.md) | Multi-vertical (micro) | READY | S | DEFER | No connect UI; ICP/pricing concern | Cheap to build but Loyverse merchants typically can't justify $343/mo. |
| [shopmonkey.md](./pos/shopmonkey.md) | Automotive | READY | M | DEFER | Off-ICP; no auto-shop dashboards | Self-serve keys + matching config = fast build whenever automotive is committed. |
| [poster-pos.md](./pos/poster-pos.md) | Restaurant | READY (off-ICP) | M | DEFER (geography) | No NA pipeline; Russia-sanctions exposure on RU tenants | Ukrainian/CIS small F&B; no UI work until a non-RU deal forces it. |
| [php-pos.md](./pos/php-pos.md) | Retail | READY | M | DEFER | High per-merchant support burden (self-hosted snowflakes) | Each install is a custom integration in support terms; flip on if 3+ inbound asks. |
| [aloha.md](./pos/aloha.md) | Restaurant | NEEDS PARTNERSHIP | XL | DEFER | No NCR Voyix partner agreement; merchant base is multi-unit chains | Highest revenue-per-merchant restaurant POS; needs hired enterprise rep motion. |
| [ncr-voyix.md](./pos/ncr-voyix.md) | Multi-vertical | NEEDS PARTNERSHIP | XL | DEFER | No signed Voyix partner agreement; enterprise gate every install | Modern Voyix gateway; route to this (not Aloha) for new enterprise NCR builds. |
| [dutchie-pos.md](./pos/dutchie-pos.md) | Cannabis | NEEDS PARTNERSHIP | XL | DEFER (unless cannabis greenlit) | Not an approved Dutchie partner; base_url points at ecommerce not POS; auth shape wrong | Dominant US dispensary POS; gatekeeps aggressively, requires deliberate cannabis GTM. |
| [blaze-pos.md](./pos/blaze-pos.md) | Cannabis | NEEDS PARTNERSHIP | L | DEFER (unless cannabis greenlit) | Not BPN partner; registry has wrong host + single-header auth (needs dual-header) | CA-first mid-tier; only after Cova (CA-CA) and Dutchie (US) are in motion. |
| [tekmetric.md](./pos/tekmetric.md) | Automotive | NEEDS PARTNERSHIP | L | DEFER | Off-ICP; partner-gated; base_url is SANDBOX not prod | Modern cloud auto-shop SaaS leader; only worth pursuing as part of automotive expansion. |
| [petpooja.md](./pos/petpooja.md) | Restaurant | NEEDS PARTNERSHIP / UNCERTAIN | L | DEFER | Off-ICP (India-dominant); no partnership; base_url unvalidated | 150k+ businesses but off Meridian's NA ICP; revisit only on qualified multi-outlet Canadian Indian-cuisine group. |
| [qu-pos.md](./pos/qu-pos.md) | Restaurant (enterprise QSR) | NEEDS PARTNERSHIP | XL | DEFER | Wrong host + wrong auth scheme in registry; no partnership | Enterprise CTO-led sale; wrong fit for SMB rep playbook. |
| [agilysys.md](./pos/agilysys.md) | Hospitality | NEEDS PARTNERSHIP | XL | DEFER | No Agilysys partner relationship; registry config unverified | Hotels/casinos/resorts only; competes with MICROS at enterprise tier. |
| [olo.md](./pos/olo.md) | Restaurant (enterprise) | UNCERTAIN | L | DEFER | Not a POS — sits on top of one; auth header format unconfirmable | Enterprise digital-ordering layer; data alone = online channel only. |
| [tyro.md](./pos/tyro.md) | Restaurant/Retail (AU) | NEEDS PARTNERSHIP / UNCERTAIN | XL | DEFER (geography) | AU-only; partner-gated; endpoint shape unvalidated | Australia's largest non-bank acquirer; zero NA pipeline value. |
| [iiko.md](./pos/iiko.md) | Restaurant | UNCERTAIN (off-ICP) | L | DEFER | base_url is Russia-region endpoint (OFAC review); off-ICP for NA | Dominant Russia/CIS, real MENA; revisit only on qualified non-RU intl deal. |
| [openbravo.md](./pos/openbravo.md) | Retail | UNCERTAIN (off-ICP) | L | DEFER | `supports_orders: False`; payments-only data shape; per-tenant Basic auth | EU mid-tier; integration is per-tenant ERP-style. |
| [posist.md](./pos/posist.md) | Restaurant | NEEDS PARTNERSHIP / UNCERTAIN | L | DEFER | Rebrand to Restroworks; host + paths unvalidated post-rebrand | India-dominant chain SaaS; off-ICP for NA. |
| [aldelo.md](./pos/aldelo.md) | Restaurant | UNCERTAIN | L | DEFER | base_url returns 403 (wrong host); Pro/Express split bifurcates strategy | Small independents below SLA threshold; defer unless EVO channel materializes. |
| [bindo-pos.md](./pos/bindo-pos.md) | Multi-vertical | UNCERTAIN | L | DEFER | bfriendo.com host not confirmed as Bindo; APAC pivot post-2021 | Center of gravity moved to Hong Kong; minimal NA pipeline. |
| [revel.md](./pos/revel.md) | Restaurant | OUTDATED CONFIG | XL | DEFER | No Partner account; needs OAuth refactor; Shift4 sunset risk | Skip Partner + auth refactor — base migrating to SkyTab. |
| [brink.md](./pos/brink.md) | Restaurant (enterprise QSR) | NEEDS PARTNERSHIP / OUTDATED CONFIG | XL | DEFER | Registry has REST + X-API-Key; real API is SOAP + AccessToken/LocationToken | Enterprise QSR only (50+ unit); SOAP build only worth chasing with executive sponsorship. |
| [pixelpoint.md](./pos/pixelpoint.md) | Restaurant | CSV ONLY | S CSV / XL API | DEFER (bundle w/ Brink) | No PAR partnership; no public API surface | Sibling to Brink — bundle if Brink partnership opens. |
| [micros.md](./pos/micros.md) | Restaurant (enterprise) | NEEDS PARTNERSHIP + OUTDATED CONFIG | XL | DEFER | No OPN enrollment; auth flow wrong (needs PKCE not client_credentials) | Enterprise-only; revisit only with signed LOI from multi-unit hotel/casino/chain. |
| [simphony.md](./pos/simphony.md) | Restaurant (enterprise) | NEEDS PARTNERSHIP + OUTDATED CONFIG | XL | DEFER | Same Oracle OPN gate as MICROS; PKCE rewrite required | Strategic Oracle product (cleaner Gen2 API); prioritize over MICROS if/when enterprise pipeline funded. |
| [xenial.md](./pos/xenial.md) | Restaurant (enterprise) | NEEDS PARTNERSHIP | XL | DEFER | No Global Payments partnership; no verified dev docs; brand-IT gatekeeper | Corporate-controlled enterprise QSR; franchisee can't self-authorize. |
| [heartland.md](./pos/heartland.md) | Multi-vertical | UNCERTAIN | L | DEFER (Retail = consider) | Single config can't represent three distinct products (Restaurant/Retail/Portico) | Heartland Retail has self-serve tokens — only branch with tractable path. |
| [stripe-terminal.md](./pos/stripe-terminal.md) | Multi-vertical | READY | S | DEFER | Not a full POS — payments only; thin analytics surface | Useful as payments-reconciliation add-on after top-10 POS land. |
| [paypal-zettle.md](./pos/paypal-zettle.md) | Retail/F&B (micro) | UNCERTAIN | L | DEFER | Off-ICP geography; deprecated public docs; active rebrand to "PayPal POS" | European micro-merchant tool; minimal NA pipeline. |
| [sumup.md](./pos/sumup.md) | Retail/F&B (micro) | UNCERTAIN | M | DEFER | No OAuth client; thin NA footprint; micro-merchant ARPU | European-tilted; build on signal not speculation. |
| [hike-pos.md](./pos/hike-pos.md) | Retail | UNCERTAIN | M | DEFER | Auth mismatch (bearer vs documented OAuth); small NA footprint | AU/NZ-tilted apparel/specialty; tie-breaker integration only. |
| [accu-pos.md](./pos/accu-pos.md) | Multi-vertical | CSV ONLY | S | DEFER | No third-party transactional API (vendor constraint) | Off-ICP; accountant-led selection; small installed base caps LTV. |
| [alldata-manage.md](./pos/alldata-manage.md) | Automotive | CSV ONLY | S CSV / XL API | DEFER | No public API; path runs through AutoZone | Off-ICP automotive; brand dominance is in Repair (info), not Manage. |
| [autofluent.md](./pos/autofluent.md) | Automotive | CSV ONLY | S CSV / XL API | DEFER | No public API; small base vs Tekmetric/Shopmonkey | Off-ICP; vendor-direct (TABS Software) integration path only. |
| [autovitals.md](./pos/autovitals.md) | Automotive | CSV ONLY | N/A | DEFER | No public API; DVI overlay not the system of record | Off-ICP; underlying SMS (Mitchell1/ALLDATA) owns RO data. |
| [bolt-on.md](./pos/bolt-on.md) | Automotive | CSV ONLY | N/A | DEFER | No public API; texting/DVI add-on, not POS | Off-ICP; transactions originate in underlying SMS. |
| [cashier-live.md](./pos/cashier-live.md) | Retail (pharmacy) | CSV ONLY | S | DEFER | No public API surfaced | Off-ICP independent pharmacy niche; Rx value lives in PMS. |
| [digital-dining.md](./pos/digital-dining.md) | Restaurant | CSV ONLY | S CSV / XL API | DEFER | No first-party API wired; Heartland/Global Payments partnership unverified | Heartland portfolio SKU shrinking as Toast/SpotOn displace. |
| [focus-pos.md](./pos/focus-pos.md) | Restaurant (mid-market) | CSV ONLY | S CSV / XL API | DEFER | No real CSV export validated; no API researched | On-premise enterprise; reseller-channel scale required. |
| [future-pos.md](./pos/future-pos.md) | Restaurant | CSV ONLY | S | DEFER | No public API, no partner program identified | Niche on-prem Windows POS; small addressable base. |
| [gloria-food.md](./pos/gloria-food.md) | Restaurant | CSV ONLY (mis-categorized) | XL | DEFER | Not a POS — online ordering widget on top of real POS | Pursue underlying POS (Square/Clover/Toast) instead. |
| [harbortouch.md](./pos/harbortouch.md) | Multi-vertical | CSV ONLY | S | DEFER (route to SkyTab) | Brand sunset into SkyTab/Shift4 Dine; no first-party API | Route any inbound to SkyTab connect flow. |
| [mitchell1.md](./pos/mitchell1.md) | Automotive | CSV ONLY | S | DEFER | No Manager SE API; vendor constraint | Off-ICP; legacy incumbent with structurally limited CSV LTV. |
| [napa-tracs.md](./pos/napa-tracs.md) | Automotive | CSV ONLY | S CSV / XL API | DEFER | No public API; path runs through Genuine Parts Company | Off-ICP; NAPA dealer channel relationship required. |
| [northstar.md](./pos/northstar.md) | Restaurant (enterprise) | CSV ONLY | S CSV / XL API | DEFER | Vendor identity unresolved (CBS vs Fourth); no API path | Confirm vendor before any outbound; CSV only realistic path. |
| [omnique.md](./pos/omnique.md) | Automotive (tire) | CSV ONLY | S CSV / XL API | DEFER | No public API; smaller than Tekmetric/Shopmonkey/Shop-Ware | Off-ICP tire-leaning niche. |
| [pos-nation.md](./pos/pos-nation.md) | Retail (multi-vertical) | OUTDATED CONFIG (wrong category) | L | DEFER | Registry says `cannabis` (wrong); should be `retail`; no public API | Fix category label first; 10k+ liquor/grocery/cigar/c-store base if multi-vertical retail is ever funded. |
| [protractor.md](./pos/protractor.md) | Automotive | CSV ONLY | N/A | DEFER | No public API; off-ICP | Canadian footprint — keep warm for Meridian Canada inbound only. |
| [rain-pos.md](./pos/rain-pos.md) | Retail (specialty) | CSV ONLY | S | DEFER | No public API; bundled e-commerce reduces 3rd-party demand | Off-ICP specialty niches (music/quilt/bike). |
| [retail-edge.md](./pos/retail-edge.md) | Retail (specialty) | CSV ONLY | XL | DEFER | No public API; local Windows architecture; RECAP undocumented | One-time license, local data — low-priority by design. |
| [ro-writer.md](./pos/ro-writer.md) | Automotive | CSV ONLY | N/A | DEFER | No public API; Windows desktop architecture | Off-ICP; only makes sense as part of broader automotive lift. |
| [shop-boss.md](./pos/shop-boss.md) | Automotive | NEEDS PARTNERSHIP / UNCERTAIN | L | DEFER | No verified API docs; smaller than auto-shop leaders | Off-ICP; unverified scaffold. |
| [tire-master.md](./pos/tire-master.md) | Automotive (tire) | CSV ONLY | N/A | DEFER | No public API; partnership through ASA Automotive | Off-ICP tire-shop niche. |
| [woo-pos.md](./pos/woo-pos.md) | Retail (online) | READY | S | DEFER (BUILD if online-retail vertical greenlit) | Strategic positioning question (online-only data) | Self-serve, free, easy; the question is product/positioning, not engineering. |

## DEPRECATE / DEAD

| POS | Vertical | Status | Effort | Recommendation | Key blocker | Strategic note |
|-----|----------|--------|--------|----------------|-------------|----------------|
| [izettle.md](./pos/izettle.md) | Retail | OUTDATED CONFIG (duplicate) | N/A | DEPRECATE | Duplicate of `paypal-zettle`; missing date-window params | Collapse to one canonical key (`paypal-zettle`); add alias map. |
| [upserve.md](./pos/upserve.md) | Restaurant | DEAD API / OUTDATED CONFIG | XL | DEFER → DEPRECATE if no Skyview signal in 90 days | `api.upserve.com` has no DNS/HTTP response; ownership changed 2026 (Skyview Equity); no dev portal | Triple-jeopardy: consolidated heritage product, offline API, US-only shrinking base. |

---

## Distribution summary

### By status (n = 79)

| Status | Count |
|--------|------:|
| LIVE | 3 (square, clover, toast) |
| READY | 8 (lightspeed-retail, korona-pos, erply, loyverse, shopmonkey, php-pos, poster-pos, woo-pos) |
| NEEDS PARTNERSHIP | 17 |
| CSV ONLY | 25 |
| OUTDATED CONFIG | 9 |
| UNCERTAIN | 13 |
| DEAD API / OUTDATED CONFIG | 1 (upserve) |
| OUTDATED CONFIG (duplicate) | 1 (izettle) |
| READY (off-ICP) | 1 (poster-pos — counted above) |
| Mixed / hybrid status labels | 2 (biotrack OUTDATED→CSV; rezku NEEDS PARTNERSHIP w/ CSV fallback) |

(Categories above are inclusive of files whose Status field stacks multiple labels — see Cleanup Needed.)

### By recommendation (n = 79)

| Recommendation | Count |
|----------------|------:|
| BUILD NOW | 12 |
| WAIT | 13 |
| DEFER | 52 |
| DEPRECATE | 1 (izettle); +1 likely (upserve) |

### By vertical (rough cut)

| Vertical | Count |
|----------|------:|
| Restaurant | ~32 |
| Retail | ~13 |
| Multi-vertical | ~10 |
| Cannabis | 9 (biotrack, blaze-pos, cova-pos, dutchie-pos, flowhub, indica-online, leaf-logix, meadow, treez) |
| Automotive | 14 (alldata-manage, autofluent, autovitals, bolt-on, mitchell1, napa-tracs, omnique, protractor, ro-writer, shop-boss, shop-ware, shopmonkey, tekmetric, tire-master) |
| Hospitality (enterprise) | 1 (agilysys) |

---

## Cleanup needed (ambiguous / non-standard Status or Recommendation)

These entries deviate from the canonical 8 statuses or 4 recommendations and should be normalized in the next pass:

- **`biotrack.md`** — Status reads "OUTDATED CONFIG" but explains a hybrid CSV-only-operationally / real-API-exists state. Recommendation is WAIT (clear).
- **`brink.md`** — Status stacks "NEEDS PARTNERSHIP / OUTDATED CONFIG."
- **`cake.md`** — Status "OUTDATED CONFIG" but Recommendation splits **BUILD NOW** on CSV vs **WAIT** on API. Matrix lists as BUILD NOW (CSV).
- **`flowhub.md`** — Status "NEEDS PARTNERSHIP" with explicit `UNCERTAIN` callouts inline.
- **`gloria-food.md`** — Status "CSV ONLY / mis-categorized" (compound).
- **`heartland.md`** — Recommendation splits "DEFER for Restaurant/payments; consider BUILD for Heartland Retail." Listed under DEFER tier.
- **`hike-pos.md`** — Status "UNCERTAIN" with "treat as NEEDS PARTNERSHIP" — pick one.
- **`indica-online.md`** — Recommendation conditional: "WAIT if cannabis greenlit; DEFER if pursuing only top-3."
- **`leaf-logix.md`** — Status "CSV ONLY" but explicitly "effectively DEPRECATED."
- **`meadow.md`** — Recommendation conditional ("WAIT if cannabis greenlit; otherwise DEFER").
- **`olo.md`** — Status "UNCERTAIN" but should arguably be a new "NOT A POS" tag.
- **`paypal-zettle.md` / `izettle.md`** — Two registry keys for one product; izettle file recommends DEPRECATE (canonical), paypal-zettle DEFER (functional). Roll up.
- **`pos-nation.md`** — Status "OUTDATED CONFIG" relates to wrong `category` label, not the API surface.
- **`posist.md`** — Status "NEEDS PARTNERSHIP / UNCERTAIN" (compound).
- **`qu-pos.md`** — Status "NEEDS PARTNERSHIP" but body says config is likely wrong on host + auth (closer to OUTDATED CONFIG).
- **`rezku.md`** — Status "NEEDS PARTNERSHIP" but registry today is `csv_only` — needs explicit "CSV ONLY today, NEEDS PARTNERSHIP to upgrade."
- **`shop-boss.md`** — Status "NEEDS PARTNERSHIP / UNCERTAIN" (compound).
- **`shop-ware.md`** — Status "NEEDS PARTNERSHIP" but the Recommendation explicitly DEFERS — listed under WAIT tier per status spirit but DEFER per stated reco.
- **`talech.md`** — Status "CSV ONLY in registry — but a real REST API … exists" (compound). Recommendation BUILD NOW.
- **`tekmetric.md`** — Status "NEEDS PARTNERSHIP" but config currently points at SANDBOX (closer to OUTDATED CONFIG).
- **`tyro.md`** — Status "NEEDS PARTNERSHIP / UNCERTAIN" (compound).
- **`upserve.md`** — Status "DEAD API / OUTDATED CONFIG" + Recommendation "DEFER — consider DEPRECATE if no signal in 90 days" (conditional).
- **`woo-pos.md`** — Recommendation conditional ("BUILD if online-retail vertical; DEFER if staying focused on brick-and-mortar"). Listed under DEFER per default.

**Suggested normalization:** add a single primary Status + Recommendation per file (with secondary tags in the body if needed) before the next portal rewrite.
