# Openbravo

**Registry key:** `openbravo` — see `src/services/pos_connectors/registry.py`

## Status
UNCERTAIN (off-ICP) — config targets the canonical Openbravo JSON REST surface (`org.openbravo.service.json.jsonrest`), but the merchant base is European mid-tier retail with no documented NA ICP footprint.

## What it is
Spanish-founded open-source retail/commerce platform (Openbravo Commerce Cloud, Openbravo POS, Mobile POS, Self-Checkout, WMS), now under Orisha Commerce. Mid-tier ("Tier 2") European retail focus.

## Vertical & market
- **Primary vertical:** retail (fashion, sporting goods, home/DIY, specialty; B2C/D2C/B2B)
- **Estimated NA market presence:** Small — no meaningful US/Canada footprint surfaced
- **Typical merchant profile:** multi-store mid-tier European retailer; reference logos include Adidas, Decathlon, Leroy Merlin, SMCP
- **Geographic concentration:** International — 55+ countries claimed, EU-centric (FR/ES/NL/EN content), minimal NA

## How to spot the merchant uses it
- Back-office on an Openbravo-branded subdomain serving `/openbravo/` paths
- "Openbravo POS" or "Openbravo Web POS" UI on terminals; Orisha Commerce branding on newer materials
- Conversational tells: "Openbravo Commerce Cloud," "Web POS," "Orisha"

## Auth method
HTTP Basic auth against the JSON REST web service, per registry config. Per-merchant Openbravo user with web-service role required.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Partial | `/FIN_Payment` | Payments table — not normalized POS orders |
| Catalog / items | ✓ | `/Product` | Standard Product entity |
| Customers | ✓ | `/BusinessPartner` | BP entity covers customers + vendors |
| Employees | ✓ | `/ADUser` | Application Dictionary user table |
| Inventory | ✗ | — | Not configured |
| Refunds | ✗ | — | Not configured |

`supports_orders: False`. Probe endpoint `/ADUser`; `data_key` is `response.data`.

## Partner program / access requirements
- **Partner program required:** Effectively yes — JSON REST surface is per-tenant on the merchant's Openbravo instance; access granted by merchant admin or implementation partner
- **Sign-up URL:** No NA-facing public developer portal surfaced; Orisha Commerce partner channel handles enterprise access
- **Approval timeline:** UNCERTAIN — depends on merchant IT and/or implementation partner
- **Cost / revenue share:** Unknown publicly

## Sandbox / test environment
- **Available:** UNCERTAIN — no public hosted sandbox confirmed
- **URL:** N/A publicly
- **Notes:** Realistic validation needs a merchant-provided dev tenant

## Rate limits
Not publicly documented.

## Webhook / sync model
Poll-only on the JSON REST surface per current config.

## Connect flow (what the merchant does)
1. Openbravo admin provisions a web-service user/role with read scope on Product, BusinessPartner, ADUser, FIN_Payment
2. Merchant supplies host domain plus Basic-auth username/password
3. Meridian probes `/ADUser`, then polls `/Product`, `/BusinessPartner`, `/FIN_Payment` via `response.data`

## Estimated effort to go LIVE
L (1+ months) — needs connect UI, normalization from `FIN_Payment` to Meridian's order model, partner/merchant credential path, per-tenant host handling.

## What blocks LIVE status today
- `supports_orders: False`; no real orders endpoint mapped — payments-only view
- No customer-facing Basic-auth connect UI built
- No relationship with Orisha Commerce or its implementation partners
- Per-tenant host (`{domain}` placeholder) means no central onboarding

## Common failure modes
- **Symptom:** `/ADUser` 401 → **Cause:** wrong credentials or missing web-service role → **Fix:** merchant grants web-service access on the user/role
- **Symptom:** empty `response.data` → **Cause:** role lacks read scope on the entity → **Fix:** widen role permissions
- **Symptom:** `404` on entity → **Cause:** entity casing or non-standard module mapping → **Fix:** confirm entity name with merchant's Openbravo admin

## Strategic notes
Legitimate mid-tier European retail platform with marquee references, but absent from Meridian's NA pipeline. Integration model is per-tenant against a customer-deployed JSON REST surface — closer to ERP integration than turnkey POS. Any motion would route through Orisha Commerce or an EU implementation partner, not self-serve.

## Recommendation
DEFER.

**Reasoning:** Off-ICP for the NA motion, payments-only data shape under current config, and per-tenant Basic auth against merchant-hosted instances — no engineering investment until a qualified EU mid-tier retail deal forces it.

## Sources consulted
- https://www.openbravo.com/ (redirects to https://commerce.orisha.com/)
- Registry config: `src/services/pos_connectors/registry.py` (`openbravo` entry)
- Live API docs accessed: No (vendor homepage references "API-first" but does not publish REST/JSON specs publicly)
