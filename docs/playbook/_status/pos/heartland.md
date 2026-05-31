# Heartland POS (Heartland Payment Systems / Global Payments)

**Registry key:** `heartland` — see `src/services/pos_connectors/registry.py`

## Status
UNCERTAIN — registry `base_url` (`api.heartlandpos.com/v1`) is not a documented public Heartland endpoint. Heartland's real API surface is split across three brands (Restaurant, Retail, Portico/payments), each with different auth, base URL, and access models. Config needs validation against whichever product line we target.

## What it is
Multi-vertical payments + POS suite from Global Payments (acquired Heartland in 2016): **Heartland Restaurant** (FOH/BOH for full- and quick-service), **Heartland Retail** (cloud retail POS, formerly Springboard), and **Heartland Payment+ / Beauty** (terminals + salon).

## Vertical & market
- **Primary vertical:** Multi-vertical — restaurant, retail, beauty/salon
- **Estimated NA market presence:** Large (Global Payments processes >$200B annually; Heartland brand is a major mid-market POS player)
- **Typical merchant profile:** 1–10 location independent or small-chain restaurant, apparel/specialty retail, salon
- **Geographic concentration:** US-focused (some Canada)

## How to spot the merchant uses it
- Terminal hardware branded "Heartland" or "Genius" (Genius is Heartland's countertop terminal line)
- Receipt footer "Powered by Heartland" / "Heartland Restaurant"
- Manager logs into `*.retail.heartland.us` (Retail) or the Heartland Restaurant iPad app
- Merchant says "we use Heartland" or "Genius terminal" — clarify which product (Restaurant vs Retail vs payments-only)

## Auth method
**Varies by product** — registry's `bearer` is partially correct:
- **Heartland Retail:** Bearer token, merchant-generated in dashboard under API section
- **Heartland Restaurant:** API key issued by Heartland rep (per-merchant), not self-service
- **Portico (payments):** SiteID / DeviceID / LicenseID / username / password header set (SOAP-era), or newer Global Payments OAuth

## Data we can pull (per current config)
Registry endpoints (`/merchants/{merchant_id}/transactions`, `/items`, `/employees`, `/customers`, `/orders`) follow a plausible REST shape but **do not match any documented Heartland product**. Heartland Retail uses `https://{subdomain}.retail.heartland.us/api/` with resources like `orders`, `tickets`, `items`, `customers`, `users`. Treat the table below as aspirational until reconciled.

| Type | Available | Endpoint (registry) | Notes |
|------|-----------|---------------------|-------|
| Orders / transactions | Likely | `/merchants/{id}/transactions` | Real path differs per product |
| Catalog / items | Likely | `/merchants/{id}/items` | Retail has `items`; Restaurant exposes menus |
| Customers | Likely | `/merchants/{id}/customers` | Confirmed in Retail |
| Employees | Likely | `/merchants/{id}/employees` | Retail calls them `users` |
| Inventory | Unknown | — | Retail supports inventory; Restaurant limited |
| Refunds | Unknown | — | Via payments API (Portico/Global Payments) |

## Partner program / access requirements
- **Partner program required:** Yes for Restaurant (rep-issued API key) and for production payments; Retail tokens are merchant-self-serve from dashboard
- **Sign-up URL:** https://www.heartland.us/partners/developers and https://developer.globalpayments.com/heartland/getting-started/overview
- **Approval timeline:** Self-service sandbox account is offered; production integration typically requires a rep conversation + certification (Portico cert list includes retail, restaurant, EMV, gift, etc.)
- **Cost / revenue share:** Not publicly disclosed

## Sandbox / test environment
- **Available:** Yes — "Get sandbox account" on developer portal; Portico has cert URL `cert.api2.heartlandportico.com`
- **URL:** https://developer.globalpayments.com/heartland (umbrella); `dev.retail.heartland.us` (Retail)
- **Notes:** MFA required for developer accounts since Feb 1 2025

## Rate limits
Not publicly documented for any of the three product APIs.

## Webhook / sync model
Poll-only is safest assumption — webhooks not documented in public-facing Retail or Restaurant API references.

## Connect flow (what the merchant does)
**Retail (self-serve):** Dashboard → Settings → API → Generate token → paste into Meridian (include their subdomain).
**Restaurant (rep-mediated):** Merchant emails Heartland rep → rep provisions API key → merchant pastes into Meridian.

## Estimated effort to go LIVE
**L (1+ months)** — three different auth flows, the registry config likely needs to be split into `heartland_retail` / `heartland_restaurant` (and possibly `heartland_payments`) before a customer-facing UI is built.

## What blocks LIVE status today
- Registry `base_url` does not resolve to a documented Heartland API — needs validation or replacement
- Single `heartland` config can't represent three distinct products with different auth + URL patterns
- Restaurant API key is rep-gated — no self-serve onboarding possible without a partnership
- No customer-facing connect UI

## Common failure modes
- **Symptom:** 404 on `api.heartlandpos.com` → **Cause:** host not the real API → **Fix:** route to Retail subdomain or Global Payments base
- **Symptom:** 401 with valid-looking key → **Cause:** wrong product (Retail token used against Restaurant endpoint) → **Fix:** confirm product line during onboarding

## Strategic notes
Heartland's mid-market footprint (especially Restaurant in independents) is attractive but the fractured API surface and rep-gated Restaurant access make this an enterprise BD play, not a self-serve integration. Retail is the only branch with clean self-serve tokens.

## Recommendation
**DEFER** for Restaurant/payments; **consider BUILD** for Heartland Retail only as a scoped pilot.

**Reasoning:** Retail has documented REST + self-serve bearer tokens — tractable. Restaurant requires a partner relationship we don't have, and current config doesn't reflect any of the three real product APIs.

## Sources consulted
- https://developer.globalpayments.com/heartland/getting-started/overview
- https://dev.retail.heartland.us/
- https://developer.heartlandpaymentsystems.com/documentation
- https://www.heartland.us/partners/developers (403)
- https://help.yellowdogsoftware.com/heartlandrestaurant
- Live API docs accessed: Partial (Retail yes; Restaurant/Portico landing pages only)
