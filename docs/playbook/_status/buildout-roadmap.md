# Phase 2 Buildout Roadmap

Actionable prioritization plan derived from the 79 POS and 8 camera playbook entries under `/root/Meridian/docs/playbook/_status/`. Use this to scope Phase 2 engineering and partnership work.

---

## Wave 1 — BUILD NOW (ship in next 4–6 weeks)

Twelve POS systems where the integration is either already LIVE and needs hardening, or has a clean self-service auth path with no partner gate, or has a partner gate that we must start TODAY in parallel with engineering.

### Already LIVE — harden, do not regress

- **[square.md](./pos/square.md)** — Highest-volume SMB integration; keep prioritizing UX polish on the connect flow and Square-specific insights (Cash App mix, tip rates, item velocity).
- **[clover.md](./pos/clover.md)** — Highest-leverage SMB unlock via Fiserv bank/ISO channel. Why now: token refresh isn't yet implemented and long-lived connections will silently 401 — fix before that bites a paying merchant.
- **[toast.md](./pos/toast.md)** — Largest US restaurant POS. Why now: code path is LIVE; the wins to ship are webhook ingestion and a deep-link "Add Now" button in the connect UI to compress the 2–4 week merchant-side onboarding gate.

### READY config — self-service auth, just needs UI

- **[lightspeed-retail.md](./pos/lightspeed-retail.md)** — Why now: config valid, OAuth credentials self-service (no partner approval blocking), large analytics-friendly retail base. ~1 week of work for OAuth UI + `/Account.json` discovery.
- **[korona-pos.md](./pos/korona-pos.md)** — Why now: self-serve basic-auth + tenant-owned credentials = zero partnership risk, S–M lift; perfect overlap with Meridian's smoke-shop/convenience ICP.
- **[shopify-pos.md](./pos/shopify-pos.md)** — Why now: huge retail TAM and growing F&B; self-serve OAuth via custom apps. Bump API version off legacy `2024-01` and plan GraphQL migration as follow-up.

### OUTDATED CONFIG — fix the registry, ship the connector

- **[cake.md](./pos/cake.md)** — Why now: build the one-click CSV mapping for the Sysco-channel base (~5k restaurants); zero partnership cost. API path stays WAIT.
- **[lavu.md](./pos/lavu.md)** — Why now: self-service credentials + high-fit pizzeria/bar/QSR ICP. Cheapest "real" integration on the board after the `reqserv` POST-table rewrite (no TouchBistro-style partner moat to wait on).
- **[talech.md](./pos/talech.md)** — Why now: self-service merchant tokens remove the partnership barrier that blocks most bank-distributed POS; wedge into the much larger Elavon merchant book.

### Start partner application NOW even though build is weeks out

- **[lightspeed-restaurant.md](./pos/lightspeed-restaurant.md)** — Why now: K-Series partner approval is the long pole. Submit the partner application this week; in parallel, fix registry config + extend connector for OAuth authorization-code flow + build OAuth UI (~1–2 weeks of eng).
- **[skytab.md](./pos/skytab.md)** — Why now: Shift4 is migrating ~18,000 Revel locations onto SkyTab. File partner application this week, fix the registry to match Shift4's actual auth (HTTP Basic on payments API; partner-only for POS data), treat POS endpoint mapping as blocked on partner SDK.
- **[cova-pos.md](./pos/cova-pos.md)** — Why now: ~70% of Canadian dispensaries + Canada portal already live = highest-leverage cannabis integration we can pursue. Start partner intake immediately; in parallel, fix the registry config and prototype against the public Postman collection. Do not promise a customer-facing LIVE date until OAuth credentials land.

---

## Wave 2 — Partner application kickoff THIS WEEK, build in 8–12 weeks

Systems that are NEEDS PARTNERSHIP with a real long-pole partner cycle (2–8 weeks) where filing the intake NOW means engineering can land alongside credentials.

- **[touchbistro.md](./pos/touchbistro.md)** — Toronto HQ + TD Bank channel = highest-priority Canada restaurant target. Email `integratedpartners@touchbistro.com` this week. Lead with analytics-only, read-only, no-order-push framing — historically clears partner review faster.
- **[spoton.md](./pos/spoton.md)** — Top-5 US restaurant POS, gaining share vs Toast. Submit intake form now — public reports show 26+ days just to receive the form after first contact. Fix `auth_type` from bearer to `x-api-key` in parallel.
- **[rezku.md](./pos/rezku.md)** — Fast credibility win for US independent-bar deals. Send `support@rezku.com` API enablement email opportunistically — first Rezku-using prospect triggers it and a registry upgrade from `csv_only` to `oauth_client_credentials`.
- **[epos-now.md](./pos/epos-now.md)** — UK expansion lever, useful US checkbox. File AppStore developer signup only if (a) UK expansion is committed or (b) a US multi-location Epos Now merchant lands.
- **[erply.md](./pos/erply.md)** — Build on demand: defer behind larger NA verticals; revisit on first multi-location chain inbound. Formalize partnership at that trigger.

---

## Wave 3 — WAIT (revisit Q3 or on prospect signal)

Systems where the playbook explicitly says WAIT. Hold position; revisit when leadership greenlights the vertical or a qualified inbound triggers it.

- **[squirrel.md](./pos/squirrel.md)** — Canadian-HQ (BC) hospitality. Open a partnership conversation before investing build; trigger build on first BC/AB/ON hospitality opportunity.
- **[biotrack.md](./pos/biotrack.md)** — Regulatory rail in BioTrack states. Wait until cannabis is named. Note NY migrating to Metrc Q1 2026 — NY-only investment shrinks fast.
- **[leaf-logix.md](./pos/leaf-logix.md)** — Product sunset by Dutchie. Keep CSV mapping live; no engineering investment in a Leaf Logix API path.
- **[shop-ware.md](./pos/shop-ware.md)** — Listed under WAIT per matrix but the file's stated recommendation is DEFER. Revisit only if Meridian commits to automotive expansion.

---

## Cannabis vertical — all-or-nothing decision

Cannabis is intrinsically a vertical commitment, not a per-vendor integration call. Per the Dutchie / Treez / Flowhub / Blaze playbook analysis:

> "Cannabis is all-or-nothing: Dutchie (~dominant), Treez (~#2), Flowhub (~#3) cover the vast majority of US licensed dispensaries. Owning only one is a half-measure — operators switch vendors and MSOs run mixed stacks."

### Hard prerequisites if cannabis vertical is greenlit

1. **Compliance posture:** federal Schedule I status → no Stripe / standard banking. Need separate banking + insurance posture.
2. **PII handling:** patient/member data is regulated (state-by-state HIPAA-adjacent rules).
3. **Marketing constraints:** Google Ads, Facebook, LinkedIn restrict cannabis. Outbound channel = direct/event/word-of-mouth.

### Recommended build order IF cannabis is committed

| Order | POS | Region | Status | Reason |
|------:|-----|--------|--------|--------|
| 1 | [cova-pos.md](./pos/cova-pos.md) | Canada | NEEDS PARTNERSHIP | ~70% Canadian share. Pair with Canada portal compliance positioning. **Already in Wave 1 BUILD NOW track.** |
| 2 | [dutchie-pos.md](./pos/dutchie-pos.md) | US | NEEDS PARTNERSHIP | Dominant US dispensary POS. Certified Partner Program (launched Aug 2025); registry has wrong base_url (ecommerce, not POS). |
| 3 | [treez.md](./pos/treez.md) | US (CA-heavy) | NEEDS PARTNERSHIP | #2 US, ~30% CA volume. Need RSA JWT signer (30s TTL) before going live. |
| 4 | [flowhub.md](./pos/flowhub.md) | US (CO/MI/MA/OK) | NEEDS PARTNERSHIP | #3 US. Bundle with Dutchie+Treez or skip — going alone doesn't justify the cannabis lift. |
| 5 | [meadow.md](./pos/meadow.md) | US (CA) | NEEDS PARTNERSHIP (soft) | Captures CA boutique/delivery segment top-3 underserve. Lighter partner gate. |
| 6 | [blaze-pos.md](./pos/blaze-pos.md) | US (CA-first) | NEEDS PARTNERSHIP | After Cova (CA-canada) + Dutchie (US) are in motion. |
| 7 | [biotrack.md](./pos/biotrack.md) | US (state traceability) | OUTDATED CONFIG | Complementary regulatory layer — even Dutchie merchants in BioTrack states touch this for state reporting. |
| 8 | [indica-online.md](./pos/indica-online.md) | US (CA) | OUTDATED CONFIG | Fast-follow for CA boutique long-tail. |
| — | [leaf-logix.md](./pos/leaf-logix.md) | — | DEPRECATED (Dutchie acquired Mar 2021) | CSV-only courtesy bridge. No engineering. |

**If cannabis is NOT greenlit:** keep `cova-pos.md` in Wave 1 (Canada wedge stands alone), defer the rest. Do not file partner intakes for Dutchie/Treez/Flowhub/Meadow/Blaze until vertical is committed.

---

## DEPRECATE / strip from training

Items to remove from sales training content so reps stop pitching them or pitching them incorrectly.

- **[izettle.md](./pos/izettle.md)** — Duplicate registry key for `paypal-zettle`. Add alias map (`izettle` → `paypal-zettle`) in the registry loader; remove the standalone `izettle` dict after one release cycle. Do not surface `izettle` to merchants in any UI.
- **[upserve.md](./pos/upserve.md)** — `api.upserve.com` returns no HTTP response; `developer.upserve.com` redirects to Lightspeed marketing. Ownership changed 2026 (Skyview Equity). Mark connector as stub for CSV-import fallback only; deprecate fully if no Skyview signal within 90 days.
- **[harbortouch.md](./pos/harbortouch.md)** — Shift4 has rebranded Harbortouch to SkyTab; `harbortouch.com/developers` redirects to SkyTab. No first-party Harbortouch API will ever ship. Strip from outbound; route inbound to `skytab.md` connect flow.
- **[leaf-logix.md](./pos/leaf-logix.md)** — Acquired by Dutchie Mar 2021; `leaflogix.com` 301-redirects to `business.dutchie.com/leaflogix` with explicit "no longer available" language. Keep CSV for legacy tenants only; strip from active training.
- **[pos-nation.md](./pos/pos-nation.md)** — Registry `category: cannabis` is WRONG (POS Nation has no cannabis product — multi-vertical retail). Fix category to `retail` immediately to prevent compliance decisions firing on POS Nation merchants.
- **[gloria-food.md](./pos/gloria-food.md)** — Mis-categorized as `restaurant` POS — it's an online ordering widget, not a POS. Reclassify in registry.
- **Aldelo "owned by Roller Holdings"** false claim — playbook flags this could not be verified. Strip from any training content that asserts ownership.
- **Lavu "owned by Roller Holdings"** similar — playbook flags as unverifiable. Strip.
- **Rain POS "owned by Cygnet" claim** — playbook flags as unverified. Strip from training.
- **Protractor "acquired into Solera"** — playbook flags as unverified. Caveat before quoting.

---

## DEFER (do not pursue) — explicit qualify-out list

These are off-ICP for the SMB rep motion. If a rep encounters one, log the inbound, accept CSV as a stopgap if relevant, flag for product. **Do not promise API timelines.**

### Automotive (all off-ICP unless Meridian commits to auto vertical)

[alldata-manage](./pos/alldata-manage.md), [autofluent](./pos/autofluent.md), [autovitals](./pos/autovitals.md), [bolt-on](./pos/bolt-on.md), [mitchell1](./pos/mitchell1.md), [napa-tracs](./pos/napa-tracs.md), [omnique](./pos/omnique.md), [protractor](./pos/protractor.md) (flag for Canada portal inbound), [ro-writer](./pos/ro-writer.md), [shop-boss](./pos/shop-boss.md), [shopmonkey](./pos/shopmonkey.md), [tekmetric](./pos/tekmetric.md) (registry on SANDBOX URL), [shop-ware](./pos/shop-ware.md), [tire-master](./pos/tire-master.md).

### Enterprise (wrong fit for SMB rep playbook)

[aloha](./pos/aloha.md), [ncr-voyix](./pos/ncr-voyix.md), [micros](./pos/micros.md), [simphony](./pos/simphony.md), [agilysys](./pos/agilysys.md), [brink](./pos/brink.md), [pixelpoint](./pos/pixelpoint.md), [xenial](./pos/xenial.md), [qu-pos](./pos/qu-pos.md), [olo](./pos/olo.md).

### Off-geography (no NA pipeline)

[iiko](./pos/iiko.md) (Russia/CIS — OFAC review on `api-ru.iiko.services` host), [poster-pos](./pos/poster-pos.md) (Ukrainian/CIS — same sanctions caveat for RU tenants), [petpooja](./pos/petpooja.md) (India), [posist.md](./pos/posist.md) (India/GCC — rebranded Restroworks), [hike-pos](./pos/hike-pos.md) (AU/NZ apparel), [tyro](./pos/tyro.md) (Australia-only acquirer), [openbravo](./pos/openbravo.md) (EU mid-tier retail), [paypal-zettle](./pos/paypal-zettle.md) (European micro-merchant), [sumup](./pos/sumup.md) (European micro-merchant), [bindo-pos](./pos/bindo-pos.md) (post-2021 APAC pivot).

### Off-ICP micro / niche

[loyverse](./pos/loyverse.md) (merchants below $343/mo threshold), [stripe-terminal](./pos/stripe-terminal.md) (not a full POS — payments only), [accu-pos](./pos/accu-pos.md), [cashier-live](./pos/cashier-live.md) (pharmacy niche), [php-pos](./pos/php-pos.md) (self-hosted snowflakes — high support burden), [rain-pos](./pos/rain-pos.md), [retail-edge](./pos/retail-edge.md), [aldelo](./pos/aldelo.md) (below SLA threshold), [revel](./pos/revel.md) (Shift4 sunset — route to SkyTab).

### CSV-only legacy restaurant on-prem (no API path possible)

[digital-dining](./pos/digital-dining.md), [focus-pos](./pos/focus-pos.md), [future-pos](./pos/future-pos.md), [northstar](./pos/northstar.md) (vendor ambiguity: CBS vs Fourth — confirm before any outbound).

### Strategic question marks

- **[woo-pos.md](./pos/woo-pos.md)** — DEFER per default. BUILD if Meridian wants the online-retail vertical (S effort, free, self-service). Decision point for Phase 2 product scope.
- **[heartland.md](./pos/heartland.md)** — DEFER for Restaurant/payments. **Consider scoped BUILD for Heartland Retail only** — it has documented REST + self-serve bearer tokens. Decision point if mid-market retail expansion is funded.

---

## Cameras — official support decision

Per [cameras-matrix.md](./cameras-matrix.md):

### OFFICIALLY SUPPORT (5 brands cover the SMB market)

| Brand | Why | Notes |
|-------|-----|-------|
| [hikvision](./cameras/hikvision.md) | Dominant SMB; one URL pattern (`/Streaming/Channels/101`/`102`) covers Hikvision + LaView + ANNKE + older Honeywell Performance | NDAA 889 caveat — qualify federal/critical-infra customers out |
| [dahua](./cameras/dahua.md) | One URL pattern (`/cam/realmonitor?channel=1&subtype=0`/`1`) covers Dahua + Amcrest + EmpireTech + older Lorex | Same NDAA 889 caveat |
| [reolink](./cameras/reolink.md) | Huge SMB footprint (cheap PoE bullets) | PoE/wired ONLY. Standalone battery (Argus without Home Hub) flagged NOT SUPPORTED |
| [unifi](./cameras/unifi.md) | Common in modern/tech-savvy SMBs | RTSPS (TLS) on port **7441**, not plain RTSP — handler must accept TLS-wrapped RTSP. Use Medium tier for analytics. Prefer official Protect API for remote deployments. |
| [axis](./cameras/axis.md) | NDAA/TAA + federal CAGE 3DJU8 — unlocks federal/critical-infra customers no other brand can serve cleanly | Premium tier; low SMB volume but uniquely required for fed deals |

### NOT SUPPORTED (3 brands — pitch replacement)

| Brand | Why blocked | Rep response |
|-------|-------------|--------------|
| [wyze](./cameras/wyze.md) | Stock firmware has no RTSP; flash procedure is a support nightmare; only legacy Cam v2/v3/Pan v2/Pan v3 work. Wyze actively sells v4/OG/v3 Pro/Floodlight/Battery — none have RTSP at all. | Recommend Reolink RLC-510A or Amcrest replacement. |
| [nest](./cameras/nest.md) | All current-gen Nest are WebRTC-only; SDM RTSP is single-client, 5-min sessions, requires $5 Device Access fee + Google Cloud project + OAuth per merchant | Recommend a $60 PoE camera (Reolink RLC-510A or Hikvision DS-2CD2043G2-I) alongside the Nest. Merchant keeps Nest for mobile alerts. |
| [arlo](./cameras/arlo.md) | No RTSP, no ONVIF, no local API. Cloud-only with proprietary encrypted streams. Even local microSD viewable only via Arlo app. | Same recommendation — add a cheap PoE camera for analytics; keep the Arlo for the mobile app alerts. |

---

## Phase 2 decision points for Aidan

1. **Cannabis vertical: GO or NO-GO?** If NO, hold Cova-only as the Canada wedge; defer everything else. If GO, commit to the 8-step build order above and accept the banking/compliance/marketing overhead.
2. **Automotive vertical: GO or NO-GO?** If NO, the 14 automotive entries stay DEFER permanently (SMS layer Tekmetric/Shopmonkey/Shop-Ware as the right first targets if GO).
3. **Online-retail (WooCommerce) vertical: GO or NO-GO?** Cheapest add on the board if GO; clarifies product positioning either way.
4. **Heartland Retail scoped pilot: GO or NO-GO?** Self-serve tokens make it the only tractable Heartland branch.
5. **Enterprise restaurant motion (Aloha, Voyix, MICROS/Simphony, Brink, Xenial, Qu, Olo, SkyTab/Shift4 Dine):** still off-ICP for current SMB rep motion. SkyTab is the one exception — Wave 1 BUILD NOW because of the forced-migration dynamic from Revel.
