# Adding a 1-click POS provider

Meridian's "1-click connect" = merchant clicks **Connect** → provider's OAuth
consent screen → redirect back → Meridian stores tokens and (eventually) syncs
their orders. Today **Square** and **Clover** do this end-to-end (dedicated
routes + full data sync). This doc covers adding more via the generic framework
in `src/pos_connect/`.

## The real bottleneck is credentials, not code

Every provider needs a **registered developer app** (a `client_id` /
`client_secret`) and a registered **redirect URI**. For some providers that's a
self-serve signup; for others it's a **partner application with legal/security
review**. No code can skip this — it's the critical path, and most steps only
the account owner (Aidan) can do.

| Provider | Auth model | Self-serve? | Reality |
|---|---|---|---|
| Square | OAuth2 | ✅ (done) | Live, full sync |
| Clover | OAuth2 | ✅ (done) | Live, full sync |
| **Lightspeed X-Series** | OAuth2 | ✅ | **Best net-new target** — real US restaurant + retail share. Register at the Lightspeed developer portal. Confirm the X-Series OAuth host (differs from R-Series `cloud.lightspeedapp.com`). |
| SumUp | OAuth2 | ✅ | Simple; low US restaurant share. Register at developer.sumup.com. |
| PayPal Zettle | OAuth2 (PKCE) | ✅ | EU-leaning; low US share. Needs a PKCE verifier store before enabling (see below). |
| **Toast** | Partner API | ❌ | #1 US restaurant POS (~30% / 155k locations) and highest demand — but **partner-gated**: API license agreement, compliance/privacy/security/legal review, signed agreement, assigned rep. Full API access reportedly **12–36 months**. **Apply now**: pos.toasttab.com/partners/integration-partner-application. Ask specifically about read-only / beta timelines. `src/toast/` already has client/mappers/sync plumbing. |
| SpotOn / TouchBistro / Revel / Aloha | Partner / API-key | ❌ | Partner-gated or API-key paste (not true 1-click). Track as demand appears. |

**Aggregator shortcut** (evaluate commercially): a unified POS API (Rutter,
Codat, Merge, Apideck) can cover many POS through one integration. Trade-off:
per-connection cost + a middleman vs. building each provider direct. Worth a
pricing/coverage call if breadth matters more than margin — confirm they carry
restaurant **order** data (not just accounting) for Toast/Lightspeed/etc.

## Turning on a framework provider (once you have an app)

A provider is offered to merchants only when it is **both** `verified=True` in
`src/pos_connect/registry.py` **and** its credential env vars are set. Steps:

1. **Register the app** with the provider. Set the redirect URI to
   `https://<api-host>/api/pos/<provider_key>/callback`
   (e.g. `https://api.meridian.tips/api/pos/lightspeed_xseries/callback`).
2. **Set env vars** on the API (Railway): the provider's `*_CLIENT_ID` and
   `*_CLIENT_SECRET` (names are in the registry entry). `OAUTH_STATE_SECRET`
   and `API_PUBLIC_URL` must already be set.
3. **Validate the round-trip** against the real app in a scratch/dev merchant:
   authorize → consent → callback stores a row in `pos_connections`. Confirm the
   authorize host, token host, scopes, and `merchant_id_strategy` are correct
   (docs are a starting point, not proof — see the registry warning).
4. **Flip `verified=True`** for that provider in the registry. It now appears in
   `GET /api/pos/providers` and the US onboarding wizard renders its Connect
   button automatically (no frontend deploy needed).
5. **Build the data sync.** `run_backfill` is Square-specific. Connecting stores
   tokens but ingests no data until a per-provider sync engine maps that
   provider's orders/catalog into Meridian's schema (model on `src/square/` or
   `src/clover/`). Do this against the same test merchant.

### Zettle / PKCE note
Zettle uses PKCE. The generic authorize builder emits a `code_challenge` when
one is supplied, but the framework does not yet persist the `code_verifier`
across the redirect (needs a short-lived shared store keyed by state nonce —
in-memory won't survive multiple workers). Add that before enabling any PKCE
provider.

## Why nothing is pre-enabled
Registry providers ship `verified=False` on purpose — a test in
`tests/api/test_pos_connect.py` enforces it. This prevents shipping an untested,
doc-transcribed OAuth config as if it were a working integration. A provider
becomes real only after step 3 above.
