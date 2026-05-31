# PAR Brink POS

**Registry key:** `brink` — see `src/services/pos_connectors/registry.py`

## Status
**NEEDS PARTNERSHIP / OUTDATED CONFIG** — registry says REST at `api.brinkpos.net/v1` with `X-API-Key`; PAR's live portal documents **SOAP/XML** at `api2.brinkpos.net/[Service].svc` (sandbox `api-apiint.brinkpos.net`) using **AccessToken + LocationToken**. Not onboardable today.

## What it is
Cloud SOAP-API restaurant POS owned by PAR Technology, used by enterprise QSR / fast-casual chains (Five Guys, Dairy Queen, Papa Murphy's, large BK franchisees).

## Vertical & market
- **Vertical:** restaurant — enterprise QSR / fast-casual
- **NA presence:** Large in enterprise QSR; negligible in independents
- **Typical merchant:** multi-unit operator, **50+ locations**, franchisee group or corporate parent
- **Geography:** US-primary, some international franchise

## How to spot it
- Operator self-identifies as "on Brink" or "on PAR"
- "Brink" on receipts, PAR-branded back-office, PAR EverServ / Pixel terminals
- Tell: references "Location Tokens" or an internal PAR rep

## Auth method
**AccessToken + LocationToken**, in headers or SOAP body depending on service. Issued only by PAR support after certification. No public OAuth, no X-API-Key.

## Data we can pull (per current config)
Nothing — registry endpoints (`/orders`, `/menus`, `/locations`) don't exist on Brink's real API. The actual surface is SOAP: `Sales2.svc` GetOrders, `Settings.svc` / `Settings2.svc` for menus, `HouseAccounts.svc` for customers, `Labor2.svc` for employees. Refunds are inside Sales2; inventory not wired. `supports_orders: False` already set.

## Partner program / access
- **Required:** Yes — certification REQUIRED per PAR portal
- **Contact:** `api.support@partech.com` / `(800) 403-9027`; tokens via `BrinkAPITokenRequest@partech.com`. No self-service. Portal: https://developers.partech.com/
- **Timeline:** Enterprise B2B — assume **4–8+ weeks** certification, plus per-merchant tokens
- **Cost / rev share:** Not publicly disclosed; enterprise-negotiated

## Sandbox
APIINT (`api-apiint.brinkpos.net`), WSDLs on sandbox CDN. Credentials issued by PAR support, same channel as production.

## Rate limits
Multi-tenant: **5 concurrent, 2–3 min sleep between calls.** Single-tenant: 10 concurrent, 1 min sleep. Batch ops 5 req/min. Delta-poll on `ModifiedTime`. TLS 1.2/1.3, HTTPS only.

## Webhook / sync model
**Poll-only.** No webhooks; `ModifiedTime` deltas are the documented best practice.

## Connect flow
1. Meridian (certified partner) emails `BrinkAPITokenRequest@partech.com` with merchant's PAR account + location IDs
2. PAR issues AccessToken + LocationToken (per location); merchant's PAR rep confirms enablement
3. Meridian stores tokens, begins polling

PAR-rep-driven, not self-serve.

## Estimated effort to go LIVE
**XL (custom partnership).** PAR certification, SOAP/XML client rewrite, per-service mappers for Sales2 / Settings2 / Labor2, rate-limit-aware poller.

## What blocks LIVE today
- No PAR partnership / production tokens
- Registry config (REST + X-API-Key + `/v1`) doesn't match the real SOAP API
- No SOAP/XML client — `rest_connector.py` cannot drive WSDL services
- No enterprise QSR prospect to justify the build

## Common failure modes
- **`/v1/locations` 404 / HTML** → registry host doesn't serve REST → don't attempt
- **401 with real creds** → AccessToken in wrong field (header vs body varies) → check the `.svc` WSDL
- **Throttling** → ignored 2–3 min sleep → sequence, never exceed 5 concurrent

## Strategic notes
Enterprise motion, not SMB. A real Brink lead = multi-unit franchisee group, multi-month procurement, security review, often a paid pilot. **Qualify out** anyone single-unit ("how many locations on Brink?"). <20 units = probably on Toast/Square instead. Only worth chasing with executive sponsorship and funding for the SOAP build.

## Recommendation
**DEFER** until a qualified enterprise QSR prospect commits to a paid pilot.

**Reasoning:** Config is non-functional, going live requires certification plus a SOAP rewrite, and the 50+ unit ICP sits outside Meridian's current SMB-restaurant motion.

## Sources consulted
- https://brinkapiportal.parpos.com/ (and `/bestpracticeandfaqs`)
- https://developers.partech.com/
- https://apitracker.io/a/partech-brink-pos
- `src/services/pos_connectors/registry.py` (`brink` — flagged outdated)
- Live API docs accessed: Yes
