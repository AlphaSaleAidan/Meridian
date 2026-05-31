# Lightspeed Restaurant (K-Series)

> Status: **WAVE 1 BUILDING** + partner application filed this week
> Category: restaurant (full-service, hospitality, multi-location)
> Auth: OAuth (bearer)

## What you tell the merchant

"Lightspeed Restaurant support is in active build — partner application filed this week with Lightspeed's K-Series team. Expected live within 30–45 days. I can put you on the priority list and we can preview your data via CSV in the meantime."

**Do not promise a specific date** — vendor approval is variable.

## How the merchant connects (when live)

1. From the Meridian portal → **Settings → POS Connections → Connect Lightspeed Restaurant**
2. OAuth 2.0 authorization-code redirect to Lightspeed → business owner approves scopes (`orders-api`, `financial-api`, `items`, `staff-api`)
3. Lightspeed redirects back with `code` → we exchange for access + refresh tokens at `/oauth/token`
4. We store refresh token (encrypted) and pull from `https://api.lsk.lightspeed.app` (NOT the old `api.lightspeedrestaurant.com` host — that doesn't resolve)

Typical time to connect (projected): **3 minutes**. Refresh tokens valid 14 days — we proactively rotate.

**Partner program required:** apply via the Partner Application form at `api-portal.lsk.lightspeed.app` (select "Restaurant" when asked which product). Approval timeline is variable — community evidence suggests weeks, not days. Explicit approval by Lightspeed Partnerships or Hospitality Product team. Merchants can also request access directly via their Account Manager (faster path for single-merchant POCs).

## What data we pull

| Data | Frequency | Backfill |
|------|-----------|----------|
| Transactions | hourly poll | 18 months |
| Items | daily | full history |
| Employees | daily | full history |
| Customers | daily | full history |

Endpoint reference: `https://api.lightspeedrestaurant.com/v1`

## What features they get (when live)

Restaurant suite + hospitality extras:

- Money Left on Table
- Menu engineering matrix
- Revenue forecasting (with reservation overlay where Lightspeed reservations are on)
- Peak hours
- Customer LTV
- Employee performance
- Multi-location rollups (Command tier)
- Order creation supported (`supports_orders: True`)

## What features they DON'T get

- Lightspeed-specific table management telemetry (table turn time) requires module add-on the merchant may not have

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Cannot resolve host api.lightspeedrestaurant.com" | Stale registry base URL — that host doesn't resolve to any current Lightspeed product | Use `https://api.lsk.lightspeed.app` (K-Series) or the O-Series host if merchant is on legacy O-Series |
| Merchant says "I use Upserve / Kounta / iKentoo" | Legacy brand on K-Series or U-Series (Lightspeed Restaurant consolidated 4 heritage brands: Kounta AU, iKentoo EU, Upserve US, Breadcrumb) | Ask which dashboard URL they log into; route U-Series merchants to the existing `upserve` connector |
| 401 after 14 days | Refresh token expired | Proactive refresh-token rotation; one-click reconnect as fallback |
| Endpoint returns 404 | Registry path is wrong — real K-Series paths are `/financial/v1/...`, `/items/v1/...`, `/staff/v1/businessLocations/{id}/userTypes/POS` | Consult K-Series OpenAPI at `api-docs.lsk.lightspeed.app` |

### Edge cases we expect but haven't seen yet
- Wrong region — Lightspeed has US/EU/AU instances. Confirm region during onboarding.

## Sales angle

**Opener:** "Are you on Lightspeed Restaurant? Hospitality-grade data we can do a lot with — table turn analysis, server-level revenue, menu engineering. Once we're live (this month), most operators find CA$3K+/mo in repeatable wins."

**Best fit:** full-service restaurants, hotels with F&B, multi-location restaurant groups (Command tier — CA$1,370/mo, $959 commission).

**Why this is the wedge:** Lightspeed Restaurant is the consolidated brand for what used to be **four separate POS products** — Kounta (AU), iKentoo (EU), Upserve (US), Breadcrumb. Combined footprint is easily top-10 restaurant POS by merchant count when counting heritage brands. Strong AU + EU presence; US base via Upserve (covered by our existing `upserve` connector). K-Series API is modern and well-documented — the friction is the partner-approval gate, not the tech. **Never promise "instant connect"** — OAuth + partner-gated, expect a 2–4 week stand-up per new merchant until we have partner-level credentials.

## What blocks live status today

- **Lightspeed K-Series partner application filed** — waiting on approval (no published SLA; community evidence: weeks)
- **Registry `base_url` `https://api.lightspeedrestaurant.com/v1` does not resolve** — must be replaced with `https://api.lsk.lightspeed.app`
- **Registry `auth_type: bearer` is wrong** — real flow is OAuth 2.0 authorization-code (not `oauth_client_credentials`)
- **Endpoint paths** (`/transactions`, `/items`, `/employees`, `/customers`, `/orders`) **do not match K-Series API structure** — see real paths under Common Failure Modes
- **`GenericRESTConnector` likely lacks authorization-code flow** — needs extension
- **No customer-facing OAuth connect UI** built
- **Sandbox is gated by partner approval** (`https://api.trial.lsk.lightspeed.app`)
- Estimated effort to LIVE: **1+ month** (driven primarily by partner-approval wait)

## Reference docs

- K-Series API reference: https://api-docs.lsk.lightspeed.app/
- Developer portal intro: https://api-portal.lsk.lightspeed.app/quick-start/intro
- OAuth2 authentication guide: https://api-docs.lsk.lightspeed.app/authentication
- Partner access tutorial: https://api-portal.lsk.lightspeed.app/guides/tutorials/developer-portal
- O-Series OAuth (for disambiguation): https://o-series-support.lightspeedhq.com/hc/en-us/articles/31329293014427-OAuth-2-0-Process
- Legacy resto-api docs (for disambiguation): https://developers.lightspeedhq.com/resto-api/introduction/gettingstarted/

---

_Last updated: 2026-05-31 (enhanced with Phase 1 research)_
_Sourced from: src/services/pos_connectors/registry.py (lightspeed-restaurant config) + docs/playbook/_status/phase-2-decisions.md (Wave 1 #10, Wave 2 partner table) + docs/playbook/_status/pos/lightspeed-restaurant.md (Phase 1)_
