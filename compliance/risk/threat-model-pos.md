# Threat Model — POS Connectors (Square / Clover / Toast)

> STRIDE-lite threat model for the POS ingestion path. v0.1 — 2026-06-28. Feeds the risk register (R-03,
> R-13, R-14) and controls `CC6.7-ENCRYPTION`, `PI1-RECONCILE`. Scope = OAuth connect → token storage →
> webhook/poll ingestion → normalization → financial computation.

## Data flow
```
Merchant authorizes (OAuth)  →  oauth.py (state HMAC, OAUTH_STATE_SECRET)
   → access/refresh tokens  →  AES-256-GCM encrypt (src/security/encryption.py)
   → pos_connections (Supabase, encrypted columns)
Ingestion: webhook (src/api/routes/webhooks.py) OR 15-min poll (celery_app.py:71)
   → normalizer.py  →  batch_upsert("transactions")
   → daily_revenue / hourly_revenue views  →  AI analytics  →  merchant dashboard
Verification: reconcile.py (Square only) compares ours vs Square truth (±$1)
```

## Trust boundaries
1. Merchant browser ↔ Meridian (OAuth redirect) — CSRF-protected by signed `state`.
2. Meridian ↔ POS vendor APIs (Square/Clover/Toast) — TLS; bearer tokens.
3. POS vendor ↔ Meridian webhooks — **inbound, attacker-reachable**.
4. Meridian app ↔ Supabase — service-role writes; RLS on reads.

## Threats

| # | STRIDE | Threat | Current control | Gap / Risk | Action |
|---|---|---|---|---|---|
| P1 | Spoofing | Forged webhook posts fake transactions | **Toast** HMAC verified (`webhooks.py:432`, PR #176). | **Twilio** path has no signature check (R-03); confirm Square/Clover webhook signature verification | Verify all POS webhook signatures; reject unsigned |
| P2 | Tampering | Malicious/garbage POS feed (negative totals, duplicate source IDs) corrupts analytics | Normalizer tolerant parsing (`normalizer.py`) | No negative-amount guard, no dedup (R-13) | Add value/sign validation + idempotent upsert on source ID |
| P3 | Repudiation | Dispute over computed figures | Square reconciliation logs mismatch (`reconcile.py:91`) | Log-only, never surfaced; Clover/Toast unreconciled (R-14) | Persist reconciliation results; alert on mismatch; dashboard |
| P4 | Info disclosure | POS OAuth token theft → full merchant POS access | AES-256-GCM at rest, fail-closed; `pos_connections` RLS | Key (`ENCRYPTION_KEY`) handling/rotation undocumented; Contabo file-secrets (R-15) | Document key mgmt + rotation; govern Contabo secrets |
| P5 | Info disclosure | Cross-tenant read of another merchant's transactions | RLS intended; service-role writes | `transactions`/`square_transactions` RLS unconfirmed; `USING(true)` pattern elsewhere (R-01) | Confirm txn-table RLS is org-scoped (R0) |
| P6 | Elevation | Body-`org_id` overrides authenticated tenant on connect/disconnect | **Remediated** — body org resolved + membership checked (`auth.py:142-225`); negative test exists | C1 BOLA still partial on some service-auth routes (R-02) | Thread `enforce_service_member` everywhere (R2) |
| P7 | DoS | OAuth callback storm / webhook flood | Rate limiter (`rate_limiter.py`), `/api/pos/connect` 10/hr | In-memory per-worker limiter (limit×workers); resets on restart | Redis-backed shared limiter |
| P8 | Spoofing | OAuth state forgery → connect attacker's POS to victim org | Signed `state` (HMAC, `OAUTH_STATE_SECRET`); fail-closed in prod if unset | Was a real incident (state-secret unset → 75% 403s), now fixed | Keep `OAUTH_STATE_SECRET` set; monitor |

## Residual risk
With R0–R5 closed, the POS path is strong: encrypted tokens, signed webhooks, org-scoped RLS, reconciliation
surfaced. Until then, **R-01/R-02 (cross-tenant) and R-03 (PCI) are the live exposures.**
