# talech (by Elavon / U.S. Bank)

**Registry key:** `talech` — see `src/services/pos_connectors/registry.py`

## Status
CSV ONLY in registry — but a real **REST API with self-serve merchant-issued tokens** is documented by talech and is the right path. Registry config needs to be upgraded from `csv_only` to a token-auth REST connector.

## What it is
iPad-first cloud POS for small independents — single-location restaurants, specialty retail, and service businesses (salons, professional services). Acquired by U.S. Bancorp in 2019 and distributed primarily as the in-house POS bundled with Elavon merchant processing.

## Vertical & market
- **Primary vertical:** Multi-vertical — restaurant, retail, service
- **Estimated NA market presence:** Medium (8,000+ merchants and $2.3B annual processing volume reported at time of 2019 acquisition; meaningful footprint inside the Elavon / U.S. Bank merchant book since then)
- **Typical merchant profile:** Single-location independent restaurant, boutique retailer, or salon that took the iPad POS as part of a U.S. Bank / Elavon merchant services bundle
- **Geographic concentration:** US-focused, also UK/IE via Elavon Europe (separate `api-eu.talech.com` host)

## How to spot the merchant uses it
- iPad on a stand at the counter running the talech app (often paired with an Elavon-branded card reader)
- Manager logs in at `app.talech.com`
- Receipts / web ordering page reference talech or Elavon
- Merchant says "we use talech" or "the iPad POS from our bank / Elavon"
- Pricing tiers Mobile (free) / Starter ($29) / Standard ($69) / Premium ($99) — Premium tier is where most API-eligible accounts sit

## Auth method
**Merchant-generated API token (bearer-style)** — self-serve from the talech dashboard. No Elavon partnership required for the merchant-data API: the merchant owns their data and authorizes a third-party developer directly. (talech explicitly warns that the API provides full account access, so tokens should only be shared with trusted developers.)

## Data we can pull (per documented API)
Registry today is CSV-only and only maps `Receipt #`, `Date`, `Total`, `Item`, `Payment Method`. The documented API surface is broader; exact endpoint paths need to be re-confirmed against the live OpenAPI/Swagger spec (referenced on apitracker.io but not publicly browsable) or the `Talech-API-for-Merchants.pdf` developer guide.

| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | ✓ (API) | TBD | Currently CSV `Receipt #` / `Date` / `Total` |
| Catalog / items | ✓ (API) | TBD | CSV exposes `Item` only |
| Customers | ✓ (API) | TBD | Not in CSV today |
| Employees | ✓ (API) | TBD | Not in CSV today |
| Inventory | Likely | TBD | Retail tier feature |
| Refunds | Likely | TBD | Surface via orders / payments |

## Partner program / access requirements
- **Partner program required:** No for merchant-data API (self-serve token). Yes if we ever wanted to be listed on talech's marketplace or co-sell through Elavon.
- **Sign-up URL:** No public developer portal — merchant generates the token from `app.talech.com` → name in top-right → **Account Settings** → **Generate New Token**. Developer name + email are entered; credentials are emailed to that developer address. Revocable from the same screen.
- **Approval timeline:** Self-service (minutes) for merchant token. Elavon co-sell / marketplace listing would be an enterprise BD cycle.
- **Cost / revenue share:** None disclosed for direct API use.

## Sandbox / test environment
- **Available:** Not publicly documented. `api-eu.talech.com` returns 403 to anonymous requests; `api.talech.com` exists but is gated.
- **URL:** N/A publicly — would need to request via Elavon developer relations or a friendly pilot merchant.
- **Notes:** Easiest path is to onboard one cooperative merchant on the Premium tier and use their generated token against production with small date ranges.

## Rate limits
Not publicly documented. Assume conservative polling (≤1 req/sec, exponential backoff on 429) until validated against a live merchant token.

## Webhook / sync model
**Poll-only** — no public webhook documentation. Plan for date-windowed polling on orders.

## Connect flow (what the merchant does)
1. Log in at `app.talech.com`
2. Click their name (top right) → **Account Settings**
3. Click **Generate New Token**
4. Enter developer name = "Meridian" and developer email = the Meridian-monitored inbox
5. Click **Generate API Token** — talech emails the credentials to that inbox
6. Meridian ingests the token automatically from the email; merchant does nothing further

## Estimated effort to go LIVE
**M (1–2 weeks)** — once we have one merchant token to probe against, swapping `csv_only` for a token-auth REST connector is mechanical; the unknown is endpoint path confirmation.

## What blocks LIVE status today
- Registry entry is `csv_only` with no `base_url`, endpoints, or auth — needs rewrite
- API host (`api.talech.com` vs `api-eu.talech.com`), exact resource paths, pagination, and date params are not openly published — need a live token to introspect
- No webhook channel — pure poll model has to be designed
- Email-delivered token onboarding flow needs a Meridian-side inbox handler

## Common failure modes
- **Symptom:** Merchant on Mobile/Starter tier can't find "Generate New Token" → **Cause:** API access is tier-gated → **Fix:** upgrade prompt to Standard/Premium
- **Symptom:** 403 on `api-eu.talech.com` for a US merchant → **Cause:** wrong region host → **Fix:** route US to `api.talech.com`
- **Symptom:** Token works then suddenly 401 → **Cause:** merchant clicked **Revoke** in Account Settings → **Fix:** re-issue from same screen

## Strategic notes
talech sits inside the U.S. Bank / Elavon distribution machine, so every talech merchant is also an Elavon processing customer — winning the talech integration doubles as a wedge into the much larger Elavon merchant book. The self-serve merchant token is the unlock: we don't need bank-grade partner approval to start, which makes talech materially easier than Heartland or Clover-on-Fiserv. Long term, an Elavon ISV / marketplace relationship would let us co-sell at the point of merchant onboarding.

## Recommendation
**BUILD NOW** — upgrade registry from CSV-only to token-auth REST as soon as one pilot merchant generates a token.

**Reasoning:** Self-serve merchant tokens remove the partnership barrier that blocks most bank-distributed POS systems, and talech's footprint inside Elavon makes a working connector a strategic foothold, not just a one-vendor integration.

## Sources consulted
- https://help.talech.com/hc/en-us/articles/115004761986-How-do-I-give-Developers-access-to-my-talech-account-
- https://help.talech.com/hc/en-us/articles/218019803-Requesting-API-Access (Zendesk returns 401 to anon fetchers; content visible via search snippet)
- https://apitracker.io/a/talech (confirms OpenAPI/Swagger spec exists)
- http://ppsusa.com/wp-content/uploads/2020/04/Talech-API-for-Merchants.pdf (PDF developer guide — binary, not parsed inline)
- https://www.elavon.com/solutions/accept-payments-in-person/point-of-sale-software-solutions/talech-retail.html
- https://en.wikipedia.org/wiki/Talech (acquisition + 8,000-merchant / $2.3B scale)
- https://bankautomationnews.com/allposts/payments/us-bank-acquires-startup-talech-to-enhance-point-of-sale-tools-for-smes/
- https://www.merchantmaverick.com/reviews/talech-review/ (verticals + pricing tiers)
- Live API docs accessed: Partial — help-center articles via search; API hosts (`api.talech.com`, `api-eu.talech.com`) return 403/401 to anon; OpenAPI spec not browsed
