# Square

**Registry key:** `square` — see `src/services/pos_connectors/registry.py`

## Status
LIVE

## What it is
Square is a multi-vertical POS used by SMBs across food and beverage, retail, beauty/personal services, and home/auto services, running on Square Terminal, Register, Stand, and mobile readers.

## Vertical & market
- **Primary vertical:** multi-vertical (restaurant + retail are the bulk of Meridian's TAM here)
- **Estimated NA market presence:** Dominant for sub-$5M-revenue SMBs in the US
- **Typical merchant profile:** Single-location or 2–10 location independents — coffee shops, salons, boutiques, food trucks
- **Geographic concentration:** US-heavy (also CA, UK, AU, JP, IE, FR, ES)

## How to spot the merchant uses it
- White Square Terminal, Register, or iPad in a white Square Stand with a chip-and-tap reader
- Receipt footer reads "Powered by Square" or shows `squareup.com/receipt/...`
- Merchant logs in at `squareup.com/dashboard`
- Conversational tells: "Square fees," "my Square dashboard," "Cash App tap to pay"

## Auth method
OAuth 2.0 (authorization code flow). Merchant approves at `https://connect.squareup.com/oauth2/authorize`. Access tokens last 30 days; refresh tokens from the code flow do not expire. We auto-refresh when tokens are within 5 days of expiry (`src/square/oauth.py`).

## Data we can pull (per current config)
| Type | Available | Endpoint | Notes |
|------|-----------|----------|-------|
| Orders / transactions | Yes | `POST /v2/orders/search` | 18-month backfill, chunked monthly; filters `COMPLETED`+`CANCELED` |
| Catalog / items | Yes | `GET /v2/catalog/list` | Categories, items, variations |
| Customers | Yes (configured) | `GET /v2/customers` | Not currently pulled by sync engine |
| Employees / team | Yes | `POST /v2/team-members/search` | Active members per location |
| Inventory | Yes | `POST /v2/inventory/batch-retrieve-counts` | Current snapshots, batched 100/call |
| Payments (card details) | Yes | `GET /v2/payments/{id}` | Enriched via webhook on `payment.created/updated` |
| Refunds | UNCERTAIN | not wired | Refund-state changes come in via `order.updated` |

## Partner program / access requirements
- **Partner program required:** No (any developer can ship an OAuth app)
- **Sign-up URL:** https://developer.squareup.com/apps
- **Approval timeline:** Self-service; production app needs Square's standard production checklist
- **Cost / revenue share:** Free

## Sandbox / test environment
- **Available:** Yes
- **URL:** `https://connect.squareupsandbox.com` (auth at `https://connect.squareupsandbox.com/oauth2/authorize`)
- **Notes:** Sandbox merchants and seeded test data available from the Developer Dashboard. Client toggles base URL via `environment` arg in `SquareClient`.

## Rate limits
Square does not publish exact numbers; observed safe ceiling is ~10 req/sec per app on standard endpoints and ~5 req/sec on batch + `SearchOrders`. We run conservatively at **8 req/sec standard (capacity 10)** and **4 req/sec batch (capacity 5)** via token bucket (`src/square/rate_limiter.py`). On HTTP 429 we honor the `Retry-After` header and back off automatically.

## Webhook / sync model
Hybrid. Initial 18-month backfill, then real-time webhooks (`order.created`, `order.updated`, `payment.created`, `payment.updated`, `catalog.version.updated`, `inventory.count.updated`, `oauth.authorization.revoked`) plus a 15-min incremental poll as a safety net. Signature verified via HMAC-SHA256 over `notification_url + raw_body`, base64-encoded.

## Connect flow (what the merchant does)
1. In Meridian: **Settings → Integrations → Connect Square**
2. Merchant is redirected to Square, signs into their Square account
3. Reviews requested scopes on Square's consent screen → clicks **Allow**
4. Redirected back to Meridian; backfill kicks off automatically (locations → team → catalog → 18 mo orders → inventory)
5. Sync progress bar updates live; first dashboards usable within minutes (orders phase is the long pole)

## Estimated effort to go LIVE
N/A — already LIVE.

## What blocks LIVE status today
None — OAuth, sync engine, webhooks, and token refresh are all in production (`src/square/`).

## Common failure modes (for troubleshooting playbook)
- **Symptom:** "Sync stuck at orders phase" → **Likely cause:** Large merchant + rate limiting on `SearchOrders` → **Fix:** Confirm 429s in logs; backfill resumes month-by-month, no action needed. ETA ~1–30 min for 18 months.
- **Symptom:** "Square disconnected unexpectedly" → **Likely cause:** Merchant revoked from Square Dashboard, or refresh token never used for >30 days → **Fix:** `oauth.authorization.revoked` webhook auto-marks disconnected; merchant must re-run connect flow.
- **Symptom:** "Card brand / last-4 missing on transactions" → **Likely cause:** `payment.created` webhook hadn't fired yet at order import → **Fix:** Wait for payment webhook; values backfill on `_enrich_payment`.
- **Symptom:** "401 Unauthorized after a few weeks" → **Likely cause:** Access token expired and refresh cron failed → **Fix:** Check `refresh_token()` logs; manual refresh via OAuthManager.

## Strategic notes
Square is our highest-volume integration target — easy self-serve OAuth, no partner gate, and the merchant base maps perfectly to Meridian's SMB ICP. Lead with Square in demos. If a merchant uses Square Appointments or Square for Restaurants, same OAuth covers both.

## Recommendation
BUILD NOW — already shipped; keep prioritizing UX polish on the connect flow and surfacing Square-specific insights (Cash App tender mix, tip rates, item velocity).

**Reasoning:** Highest install base in our ICP, no partnership friction, and our integration is feature-complete (OAuth + backfill + webhooks + payment enrichment).

## Sources consulted
- https://developer.squareup.com/docs/oauth-api/overview
- https://developer.squareup.com/docs/oauth-api/create-urls-for-square-authorization
- https://developer.squareup.com/docs/webhooks/overview
- https://developer.squareup.com/apps
- `src/square/oauth.py`, `client.py`, `sync_engine.py`, `webhook_handlers.py`, `rate_limiter.py`
- Live API docs accessed: Yes
