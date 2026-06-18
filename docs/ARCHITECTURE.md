# Meridian — Architecture & Coding Principles

The conventions every change to this repo should follow. Short, enforced where
possible by CI (`.github/workflows/`). When a rule has a reusable primitive, use
the primitive — don't re-implement the rule inline.

## 1. Layering (Domain-Driven, bounded contexts)

```
src/api/routes/      HTTP boundary — auth, validation, no business logic
src/<provider>/      POS adapters (square/, clover/) — client, mappers, sync_engine
src/workers/         background jobs (backfill, incremental sync, token refresh)
src/db/              persistence + canonical queries (the ONLY place SQL/PostgREST lives)
frontend/src/        React (pages, hooks, components, lib)
```

- Keep files under ~500 lines; split by responsibility, not by size.
- Public functions have typed signatures. No `any` in new TS; no untyped dicts crossing module boundaries where a TypedDict/model fits.
- Routes validate input at the boundary and delegate; they do not embed business rules or raw SQL.

## 2. Tenancy — every org-scoped action proves membership

The #1 security class in the audit was endpoints trusting a client-supplied
`org_id`/`merchant_id`. Three guards exist; pick the right one:

| Guard | Proves | Use when |
|-------|--------|----------|
| `require_jwt` | a valid session exists | never sufficient alone for org data |
| `require_service_auth` | session **or** service token | internal/service-to-service only |
| `require_org_access` (dependency) | caller is a member of `org_id` | `org_id` is in the **query/path** |
| `require_org_member(user, org_id)` | caller is a member of `org_id` | `org_id` is in the **body** or another param |

**Rule:** any endpoint that reads or mutates org-scoped data and takes the org id
in the request **body** MUST call `await require_org_member(user, body.org_id)`
after `require_jwt`. `require_org_access` only sees query/path params — it is a
no-op for body params. (The DB client uses the service-role key and bypasses RLS,
so the application is the only tenancy boundary on those paths.)

## 3. Money — one source of truth

All money is **integer cents**, never floats. Never sum `total_cents` directly for
a displayed figure — voids inflate it and refunds aren't netted. Use
`src/db/revenue.py`:

```python
from src.db.revenue import net_revenue_cents, is_revenue_txn
revenue = net_revenue_cents(transactions)   # excludes voids, nets refunds
```

Currency/locale is path-derived (`/canada` → CAD/en-CA) via `frontend/src/lib/format.ts`
(`formatCents`, `formatCad`, `formatCentsCompact`). Never hardcode `$`/`US$`/`USD`/`en-US`
on a shared page — Canadian merchants see it. Don't hardcode FX rates.

## 4. POS data — per-provider tables, unified read view

Each POS system writes to its **own** canonical table so ingestion paths can never
overwrite each other:

```
square_transactions  ┐
clover_transactions  ├─►  VIEW transactions   (read-only; app reads this)
toast_transactions   ┘
```

- Ingestion (backfill / incremental / webhook) writes the **provider** table only.
- The app reads the `transactions` **view** (and the equivalent per-domain views) — never a provider table directly.
- Per-provider tables are write-restricted by RLS to the ingestion service role; everyone else is read-only.
- Dedup key is `(org_id, external_id)` **within a provider table** — provider isolation removes cross-POS collisions. Re-syncs must be idempotent (stable `external_id`, not a fresh uuid, in the on-conflict key).

## 5. Error handling — never swallow, never fake success

- No empty `catch {}` / `except: pass` / `.catch(()=>{})` that hides a failure from the user.
- Frontend mutations check `res.ok`; a 4xx/5xx surfaces an error (reuse the existing toast/`ErrorState`) and never advances a wizard or marks an action done.
- Background tasks that fail must record the failure on the row they touch (e.g. `pos_connections.status='error' + last_error`) so the state is recoverable — not a silent "connected, no data".
- Webhooks verify their signature before processing; dedupe must survive process restart.

## 6. CI gates (`.github/workflows/`)

A PR to `main` must pass: **ruff** (`ci.yml`), **tsc** + Python syntax (`syntax-check.yml`),
the **POS ingestion harness** (`ci.yml`), **gitleaks** (`gitleaks.yml`), and **security** checks.
Don't merge red. Don't `--no-verify` around a real failure — fix the cause.

## 7. Deploy reality

`main` → Railway (production backend, `api.meridian.tips`). The Canada frontend is a
**manually-built** Contabo static `dist` — source edits there have no live effect until
a rebuild. Backend changes take effect on Railway deploy (merge to `main`). Migrations
run against the **shared production Supabase** — author them as reviewable files; apply
to prod deliberately, never as a side effect.
