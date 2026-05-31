# POS Registry Expansion Candidates

Meridian is a POS analytics platform targeting US/Canadian SMB restaurants, retail, cannabis, and salons. The current registry (`src/services/pos_connectors/registry.py`, 80 systems) leaves visible gaps in (a) the **salon/spa/wellness vertical** — explicitly part of Meridian's training but covered by zero connectors today — (b) the **Canadian cannabis** vertical beyond Cova/Treez, (c) several **distinct SKUs that hide under compound entries** (Heartland Restaurant, Heartland Retail, Booker), and (d) modern **brewery/beverage-tech-adjacent** POS systems. The candidates below let reps quote integration possibility for ~30 additional SMB systems they're likely to encounter without expanding scope outside Meridian's ICP. Bank-channel POS rebrands (PNC, Wells Fargo) are confirmed as resold Clover and need no new connector — only a marketing-side alias.

## ADD TO REGISTRY (high priority)

| POS | Vertical | Why add | Auth method | Effort to add config |
|-----|----------|---------|-------------|----------------------|
| boulevard | Salon/Spa | Modern GraphQL Admin API; salon vertical is in rep training and currently has zero coverage. Self-serve via dev portal. [Docs](https://developers.joinblvd.com/) | OAuth 2.0 (GraphQL) | M |
| mindbody | Wellness/Salon/Fitness | Public API v6 with OAuth Identity Service; thousands of salons, spas, gyms — anchor connector for the entire wellness vertical. Self-serve dev account + sandbox. [Docs](https://developers.mindbodyonline.com/PublicDocumentation) | OAuth2 + OpenID Connect | M |
| booker | Salon/Spa | Separate Booker API (developers.booker.com), distinct endpoints from parent Mindbody despite same owner; spa/salon ICP overlap with Meridian. [Docs](https://developers.mindbodyonline.com/ui/documentation/booker-api) | API key (per Mindbody article 203267383) | M |
| vagaro | Salon/Spa/Fitness | Public APIs + Webhooks (Settings → Developers → APIs & Webhooks) covering Appointments, Customers, Transactions, Employees; large indie-salon footprint. Access form-gated, ~7-day approval. [Docs](https://docs.vagaro.com/) | API key + webhook subs | M |
| heartland-retail | Retail | Distinct product from `heartland` (which is Restaurant/Dinerware/Portico compound); self-serve API tokens — the tractable Heartland branch the matrix already flagged. [Docs](https://dev.retail.heartland.us/) | Bearer (account-scoped API token) | S |
| heartland-restaurant | Restaurant | Distinct from the compound `heartland` entry; this is the Genius-branded cloud restaurant SKU 7shifts and others integrate to directly. ~35k venues on Dinerware/Heartland Restaurant. [Docs](https://www.heartland.us/partners/developers) | Open API (key/cert via dev portal) | M |
| greenline-pos | Cannabis (Canada) | BLAZE-owned Canadian cannabis POS with open REST API + real-time webhooks; AGCO/BCLDB-compliant. Direct fit for Meridian Canada portal (meridian.tips) cannabis pipeline. [Docs](https://getgreenline.co/) | API key + webhooks | M |
| lightspeed-ecom | Retail (e-commerce + POS) | Formerly Ecwid, now Lightspeed Ecom (E-Series); bundled into Retail POS Core/Plus plans. Distinct REST API with OAuth2, 600 req/min, public+private tokens. Hybrid online/in-person shops in the ICP need this. [Docs](https://api-docs.ecwid.com/reference/rest-api) | OAuth 2.0 | S |
| lightspeed-golf | Retail (Golf) | Vertical SKU (formerly Chronogolf) with its own Partner API (REST + OAuth2) distinct from lightspeed-retail; tee-sheet + pro-shop POS in one. [Docs](https://partner-api.docs.chronogolf.com/) | OAuth 2.0 | M |
| foodics | Restaurant (MENA + LATAM + growing) | REST + JSON, OAuth2 authorization code, 30k+ outlets in 35+ countries; documented dev portal with Postman collection. Useful when Meridian Canada gets MENA-diaspora restaurant inbound. [Docs](https://dash.foodics.com/api-docs) | OAuth 2.0 | M |
| mariana-tek | Fitness Studio | Full suite of REST APIs (Admin, Customer, Studio, Stripe, Documents); boutique fitness POS with real transaction surface, not just billing — distinct from Glofox/Mindbody. [Docs](https://guides.marianatek.com/api-overview) | API key (per docs portal) | M |
| gotab | Restaurant/Brewery/Entertainment | REST + GraphQL public API with full developer portal; modern entertainment-commerce POS gaining share in breweries, pickleball, food halls. [Docs](https://docs.gotab.io/) | API key (dev portal sign-up) | M |
| ncr-counterpoint | Retail (specialty) | Distinct from `ncr-voyix` (enterprise) — Counterpoint is the SMB/mid-market specialty retail SKU with self-serve REST API, multi-company support, free API key + paid merchant registration. Vape/cigar/specialty shops use this. [Docs](https://github.com/NCRCounterpointAPI/APIGuide) | API key (Auth header) + Counterpoint creds | M |
| ecwid | Retail (online + light POS) | Pre-Lightspeed-rebrand Ecwid is still widely searched by name; alias mapping to `lightspeed-ecom` lets reps quote without confusing merchants who haven't seen the rebrand. Same REST/OAuth2 API. [Docs](https://api-docs.ecwid.com/reference/rest-api) | OAuth 2.0 (alias) | S (alias entry) |

## ADD TO REGISTRY (lower priority, opportunistic)

| POS | Vertical | Why add | Auth method | Effort to add config |
|-----|----------|---------|-------------|----------------------|
| sapaad | Restaurant (MENA + APAC, growing US) | Open REST API + event webhooks ("instant updates without polling") covering sales, orders, inventory, customer. Cloud restaurant POS w/ growing US presence. [Docs](https://www.sapaad.com/kw/custom-apis-developer-tools/) | API key (per developer-tools page) | M |
| linga-pos | Restaurant | Open API for menu, online ordering, device sync, user roles; 17+ years in restaurant; developer partner program. Useful for fast-casual/QSR inbounds. [Docs](https://lingapos.com/partners/become-a-developer-partner) | Partner program (form-gated) | M |
| gofrugal | Retail/Restaurant (India + MENA) | Documented Open APIs for sales orders, inventory, items; Postman collection in community KB. Relevant only for Canadian-Indian-diaspora multi-location retailers. [Docs](https://community.gofrugal.com/portal/en/kb/articles/api-integration) | API key | M |
| ezyvet | Veterinary | OAuth2 + bearer tokens, 60 req/min endpoint cap; clear commercial-partner vs private-integration tiers. Vet vertical is off Meridian's primary ICP but ezyVet is the modern leader if vet ever opens up. [Docs](https://developers.ezyvet.com/) | OAuth 2.0 (bearer) | M |
| untappd-business | Restaurant/Brewery (menu+POS write-back) | Backend UTFB API supports write tokens for menu sync to POS (Toast/Square/GoTab integrations live). Not a primary POS but the canonical beverage-menu layer brewery prospects ask about. [Docs](https://docs.business.untappd.com/) | API token (read/write) | S |
| beerboard | Restaurant/Brewery (draft analytics, POS-adjacent) | Web-services API connecting flow sensors + POS DB; beer-program reconciliation layer that bar/brewery prospects routinely ask about. POS-adjacent, not primary POS. [Docs](https://www.beerboard.com/pos-integrations/) | API key (per integration partner) | S |
| paymentsense-connect | Retail/Restaurant (UK-tilted, expanding) | Cloud-hosted REST API (`*.connect.paymentsense.cloud`) bridging EPoS and card-machine; documented endpoints for transactions, table data, EOD reports. UK/EU prospects on Epos Now/AccentPOS often pair with this. [Docs](https://docs.connect.paymentsense.cloud/rest/api) | Per-merchant host + key | M |
| arryved | Restaurant/Brewery | Purpose-built craft-beverage POS (taproom + production + payments + reporting); 7shifts already syncs sales data from it. No public dev portal yet — partner-gated, contact required. [Site](https://arryved.com/platform/arryved-overview/) | Partner-gated (no public docs) | L |

## SKIP

| POS | Why skip |
|-----|----------|
| mangomint | No public API documented (only Zapier + named partner integrations like Square/Stripe/QuickBooks). |
| glossgenius | Explicit "no API" per SaaSworthy; integrations are Stripe/Square/QuickBooks/Google only. |
| slice-register | Vendor confirms "Slice Register does not have an API available." Pizza-only, ~15k venues, but no programmatic surface. |
| glofox | Per multiple 2026 reviews "basic payment collection but NOT full POS"; off-ICP for Meridian's POS-analytics positioning. |
| quickvee | No developer documentation surfaced; smoke-shop POS already well-covered by KORONA in registry. |
| blackbox-solutions (vape) | No vape/smoke POS named "BlackBox" with documented API surfaced; KORONA already covers the vertical. |
| brewlogix | No public-facing product/API surfaced under this name in 2026; brewery vertical is better covered via Arryved/BeerBoard/GoTab. |
| 7shifts | Labor-management, not POS — pulls FROM POS (Toast/Heartland-Restaurant/Simphony). Adjacent, not in scope. |
| restaurant365 | Back-office accounting/inventory layer ("connects to POS providers"), not a POS. Snowflake share + R365 API exist but they consume POS data, not produce it. |
| marketman | Inventory layer ("paid add-on on Growth plans" to MarketMan's own API); pulls from POS. April 2026 "Square Restaurant Inventory by MarketMan" confirms direction is into-Square, not standalone POS. |
| punchh (PAR Engagement) | Loyalty engine inside PAR Engagement Cloud; not a POS. Sits alongside Brink/PixelPoint (already in registry). |
| olo / chownow / lunchbox / gloria-food / bbot | Ordering layers on top of POS — already classified correctly (olo, gloria-food in registry as DEFER). Same bucket for ChowNow/Lunchbox/Bbot. |
| veeqo / brightpearl / cin7 | Inventory / order-management systems; consume POS data, not POS systems themselves. |
| davo / avalara | Tax-compliance integrations (per task brief). Not POS. |
| posist (rebrand to Restroworks) | Already in registry as `posist`; the rebrand is a metadata cleanup task in the existing file's `notes`, not a new connector. |
| tabit | MobileFirst restaurant POS, but no public developer portal surfaced — partner-gated, no docs URL, off-ICP geography (Israel/MENA HQ, US footprint thin). Revisit on inbound. |
| netsuite-suitecommerce-pos | Oracle enterprise-only; SuiteScript/SuiteCommerce InStore (SCIS) is per-tenant Aconcagua-release-plus customization, not a connector pattern. Off-ICP at $150–225/hr dev rates. |
| genius-pos (Global Payments standalone) | Genius is Global Payments' unified POS umbrella launched May 2025; underlying SKUs (Heartland Restaurant, Heartland Retail, Xenial) already covered separately. Add as alias only if reps repeatedly hear "Genius" without an underlying product. |
| toast-now | Not a separate POS — Toast Now is a digital-ordering/marketing add-on SKU on top of Toast POS (already covered). |
| square-for-restaurants | Confirmed by Square docs: no distinct API — uses Square Orders/Catalog/Payments APIs already covered under `square`. |
| shopify-lite / shopify-starter / shopify-pos-pro | All three use the same Shopify POS API surface (`shopify-pos` in registry). POS Lite vs POS Pro is a billing distinction, not an API distinction. |
| lavu-lite | No evidence of a distinct "Lavu Lite" SKU with separate API surface in 2026; falls under the existing `lavu` rewrite already on the BUILD NOW list. |
| revel-express | No distinct "Revel Express" product surfaced in 2026; covered under existing `revel` entry (which is itself DEFER per Shift4/SkyTab migration). |
| cashmere (cannabis) | No product surfaced by that name in 2026 Canadian cannabis listings (TechPOS, Cova, BLAZE, Greenline, Dutchie dominate). |

## ALREADY COVERED (false alarms)

| Suggested name | Already at | Note |
|----------------|------------|------|
| PNC POS | `clover` | PNC distributes Clover via Fiserv merchant channel; same API. Add `aliases: ["pnc-merchant-services"]` on clover entry. |
| Wells Fargo Merchant Services POS | `clover` | Confirmed: wellsfargo.com/biz/merchant lists Clover Station Solo/Duo/Mini/Compact/Flex. Same Clover API. Add alias. |
| Worldpay POS | `clover` / `genius-pos` | Global Payments closed Worldpay acquisition Jan 2026; combined company cross-sells Global Payments' Genius POS to Worldpay SMB base. No distinct API surface. |
| Fiserv POS (generic) | `clover` | Clover is the Fiserv POS product. |
| TSYS POS | `clover` | TSYS is now Global Payments (post-2019 merger); their SMB POS push goes through Genius/Heartland — both covered as separate adds above. |
| Harbortouch | `harbortouch` (already in registry) | Sunset into SkyTab/Shift4 Dine per existing matrix; no action needed. |
| Bindo (replacement product) | `bindo-pos` (already) + `aldelo` | Bindo has reached end-of-life; replacement is Aldelo Touch for iPad — Aldelo is already in registry. |
| iZettle / PayPal Zettle | `paypal-zettle` + `izettle` | Already in registry as duplicates; matrix already flags collapse-to-one cleanup. |
| Upserve | `upserve` | Already in registry; DEAD API per matrix. |
| Restroworks | `posist` | Already in registry under pre-rebrand name; needs notes-field update, not new connector. |
| Connected Restaurant (Punchh) | n/a | "Connected Restaurant" is not a product — it's PAR's positioning phrase for the Punchh+Brink suite. Brink is in registry. |

## NOT A POS (qualify out)

| Suggested name | What it actually is | Where it fits if anywhere |
|----------------|---------------------|---------------------------|
| 7shifts | Labor management / scheduling SaaS | Adjacent — pulls sales data FROM POS. Skip as connector. |
| Restaurant365 | Back-office accounting + inventory + payroll | Adjacent — consumes POS data via integrations. Skip. |
| MarketMan | Restaurant inventory / purchasing layer | Adjacent — pulls from POS; April 2026 Square integration confirms direction. Skip. |
| Punchh (PAR Engagement) | Loyalty + engagement engine | Adjacent — sits on top of POS (Brink, etc.). Skip. |
| Olo | Enterprise digital-ordering aggregator | Already in registry as DEFER (correctly flagged as not-a-POS). |
| ChowNow / Lunchbox / Bbot | Online-ordering layers + connectivity middleware | Same bucket as Olo. Skip. |
| GloriaFood | Online-ordering widget | Already in registry as DEFER (correctly flagged). |
| Veeqo / Brightpearl / Cin7 Omni | Multichannel inventory / order management | Adjacent — consume POS data. Skip. |
| DAVO / Avalara | Sales-tax automation | Tax integration, not POS. Skip. |
| BeerBoard / Untappd for Business | Beverage analytics + menu sync layer | POS-adjacent — listed as opportunistic ADD above because they DO write to POS (menu sync), but they are not primary transactional POS. |
| OpenTable / Resy / Tock | Reservation platforms | Adjacent — Resy+Toast partnership shows direction but reservation is not POS. Skip. |
| Glofox | Fitness studio management (basic payment, not full POS) | Reviewers in 2026 explicitly state "not a full POS." Skip — Mariana Tek covers the fitness vertical when it opens up. |
| Mindbody (consumer side) | Consumer-facing booking app | The Public API v6 is the POS-relevant surface; that's what gets added. |
| Altametrics / Hubworks | Enterprise restaurant back-office | Adjacent — integrates with Brink POS via Any Connector. Skip. |
