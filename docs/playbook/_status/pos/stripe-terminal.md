# Stripe Terminal

**Registry key:** `stripe-terminal` — see `src/services/pos_connectors/registry.py`

> Important caveat: Stripe Terminal is an **in-person payment product**, not a full POS. Stripe's own docs frame it as something you integrate *into* a custom or third-party POS. Treat any "Stripe Terminal merchant" as a Stripe-payments merchant who almost certainly uses another POS for menu, employees, and inventory.

## Status
READY (config valid, self-service auth) — but flagged: analytics value is limited vs full-POS connectors.

## What it is
Stripe's in-person payment stack: certified card readers (BBPOS WisePOS E, Stripe Reader S700, Tap to Pay on iPhone/Android) plus PaymentIntents API, used by businesses already on Stripe online who want to accept cards in person.

## Vertical & market
- **Primary vertical:** multi-vertical, but skewed to developer-built / custom-POS deployments (fitness studios, pop-ups, service businesses, online brands with retail counters)
- **Estimated NA market presence:** Large in payment volume; small as a *standalone* POS install base
- **Typical merchant profile:** Stripe-online merchant who added in-person; or a custom-built POS using Stripe as the payments layer
- **Geographic concentration:** US/CA/EU/UK/AU/SG/NZ/JP

## How to spot the merchant uses it
- WisePOS E (black handheld touchscreen, "stripe" wordmark on chin) or white Stripe Reader S700 at the counter
- Receipt or email from `stripe.com` / dashboard at `dashboard.stripe.com`
- Tap to Pay on iPhone with no separate POS hardware
- Tells: "we use Stripe," "everything's in our Stripe dashboard," "our developer set it up"

## Auth method
HTTP Basic Auth with the secret API key as username, empty password. Self-service — any Stripe account holder can generate `sk_live_…` / `sk_test_…` keys at `dashboard.stripe.com/apikeys`. Restricted keys can scope read-only access to PaymentIntents, Products, Customers. Stripe Connect OAuth is available if we want a hosted connect flow later.

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Partial | `GET /v1/payment_intents` | Amount, currency, status, customer, payment method, created — but **no item-level lines on the PaymentIntent itself** |
| Catalog / items | Partial | `GET /v1/products` | Only populated if merchant manages a catalog in Stripe (most Terminal merchants don't) |
| Customers | Yes | `GET /v1/customers` | Often sparse — many in-person sales are guest checkouts |
| Employees | No | — | Stripe has no employee/cashier concept |
| Inventory | No | — | Out of scope for Stripe |
| Refunds | Yes | `GET /v1/refunds` (not in config) | Easy add |
| Line items | Limited | `GET /v1/payment_intents/{id}/amount_details_line_items` | Separate call per PI; only present when the integrator pushed cart details to the reader |

Pagination is cursor-based (`starting_after` + `limit`, max 100). Date filtering via `created[gte]/[lte]` as Unix timestamps. The `/balance` endpoint is the cheap connection test.

## Partner program / access requirements
- **Partner program required:** No
- **Sign-up URL:** `https://dashboard.stripe.com/register` then `…/apikeys`
- **Approval timeline:** Self-service, instant
- **Cost / revenue share:** Free for API access

## Sandbox / test environment
- **Available:** Yes
- **URL:** Same host (`api.stripe.com`) with `sk_test_…` keys; Stripe also ships a Reader Simulator
- **Notes:** Test mode is fully featured; no separate base URL.

## Rate limits
Stripe publishes 100 read / 100 write requests per second in live mode (25/25 in test), with burst tolerance. We're well under this with poll-only sync.

## Webhook / sync model
Hybrid-capable. Stripe has rich webhooks (`payment_intent.succeeded`, `charge.refunded`, etc.) signed with `Stripe-Signature` (HMAC-SHA256). Current config is poll-only; webhooks are a follow-up.

## Connect flow (what the merchant does)
1. In Meridian: **Settings → Integrations → Connect Stripe**
2. Merchant opens `dashboard.stripe.com/apikeys`, creates a **restricted key** (read access to PaymentIntents, Customers, Products, Balance)
3. Pastes the `rk_live_…` key into Meridian
4. Meridian hits `/balance` to validate, then backfills PaymentIntents in date-range chunks

## Estimated effort to go LIVE
S (1–3 days) for paste-a-key flow. M (1–2 weeks) if we add Stripe Connect OAuth.

## What blocks LIVE status today
- No customer-facing "paste API key" UI
- No webhook handler
- No per-PI line-item enrichment (the `amount_details_line_items` call is N+1 — only worth it if merchant uses cart display)
- Strategic: **most Stripe Terminal merchants are not "pure POS" customers**, so the analytics surface is thin

## Common failure modes (for troubleshooting playbook)
- **Symptom:** Dashboard shows totals but no items → **Cause:** PaymentIntents don't carry line items by default → **Fix:** expected; either enrich via `amount_details_line_items` or accept transaction-level only
- **Symptom:** `401 Unauthorized` → **Cause:** restricted key missing required resource scope → **Fix:** regenerate with read access to PaymentIntents, Customers, Products, Balance
- **Symptom:** Customers list nearly empty → **Cause:** in-person sales were guest checkouts → **Fix:** expected behavior, not a bug

## Strategic notes
Stripe Terminal is a **complementary** integration, not a primary one. Two real use-cases for Meridian:
1. Merchant uses Stripe Terminal *as* their POS (custom-built, low-volume) — analytics value is real but the segment is small.
2. Merchant uses Stripe alongside another POS (Square, Toast, Shopify) — pull Stripe for the payments-truth layer and dedupe against the POS connector. This is the more interesting unlock.

Do not lead a sales conversation with Stripe Terminal. If a prospect says "we use Stripe," ask what POS sits on top.

## Recommendation
**DEFER** — build as an add-on after the top-10 full-POS connectors are LIVE.

**Reasoning:** Self-service auth and a clean API make this technically cheap, but Stripe alone gives transaction totals, not items/employees/inventory — the inputs Meridian's analytics rely on. Better positioned as a payments-reconciliation add-on than a primary POS.

## Sources consulted
- https://docs.stripe.com/terminal
- https://docs.stripe.com/api
- https://docs.stripe.com/api/authentication
- https://docs.stripe.com/api/payment_intents
- Registry config: `src/services/pos_connectors/registry.py` (line 349, `stripe-terminal`)
- Live API docs accessed: Yes
