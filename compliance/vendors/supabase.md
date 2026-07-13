# Vendor: Supabase
**Document ID:** VEN-001
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce

---

## Role

Primary managed Postgres database, Row-Level Security (RLS) enforcement, Supabase Auth (JWT issuance and session management), and Supabase Storage. Supabase is Meridian's most critical sub-processor: it is the authoritative store for all tenant, customer, and operational data.

**Project ref:** `kbuzufjxwflrutowwnfl` · **Region:** AWS us-east-1 (N. Virginia)

**Integration path:** `src/db/` (Supabase client), `src/api/dependencies/auth.py` (JWT validation), `src/api/dependencies/tenant.py` (RLS context), all migration files under `migrations/`

---

## Data Touched

| Data category | Examples | RLS policy |
|---|---|---|
| Tenant / org data | org records, rep accounts, merchant profiles | Per-org RLS on all tenant tables |
| Customer PII | Customer names, contact details, order history | Scoped to org-level access |
| Auth tokens / sessions | Supabase Auth JWT, refresh tokens | Auth schema; access by Supabase Auth service only |
| POS OAuth credentials | Encrypted Square / Clover / Toast OAuth tokens | Stored encrypted (`src/security/encryption.py`); RLS-protected |
| Phone call metadata | Call records, agent session logs | Org-scoped RLS |
| Camera vision data | Merchant device records, session analytics | Org-scoped RLS; embeddings not stored in Supabase (on-device) |
| Financial data | Order amounts, payment references (not raw card data) | Org-scoped RLS |

Supabase holds ALL of Meridian's customer PII and operational data. A Supabase compromise is Meridian's highest-impact availability and confidentiality risk.

---

## Attestation Status

| Attestation | Status | Source |
|---|---|---|
| SOC 2 Type II | Public — verify at [supabase.com/security](https://supabase.com/security) | Download annually |
| AWS underlying infrastructure | AWS SOC 1/2/3, ISO 27001 (Supabase runs on AWS us-east-1) | AWS compliance pages |
| GDPR | Supabase DPA available online | supabase.com/gdpr |

**Annual evidence action:** Download current Supabase SOC 2 Type II report PDF → store at `compliance/evidence/POL-008/vendor-attestations/supabase-soc2-<year>.pdf`.

---

## DPA Status

Supabase provides a Data Processing Addendum (DPA) available at supabase.com/legal/dpa.

**Action required:** Confirm whether a signed DPA is on file. Given Meridian's Canadian customers, PIPEDA obligations apply. Supabase's GDPR DPA likely covers PIPEDA alignment but this should be confirmed. Record status in `compliance/evidence/POL-008/vendor-attestations/supabase-dpa-status.md`.

---

## What Breaks if Supabase Fails

**Impact: CRITICAL**

- All authenticated API endpoints fail immediately (JWT validation depends on Supabase Auth).
- All tenant data reads/writes fail (Meridian backend has no local data cache).
- The Canada frontend (static HTML, Railway-served) loads but all data-dependent features (rep portal, order history, analytics) show empty or error states.
- Async workers (Celery/Beat on Contabo) that write to Supabase begin queuing or failing.
- Phone agent cannot look up merchant context — orders cannot be submitted.
- Camera vision sessions cannot be persisted.

**Recovery:** Supabase provides daily automated backups. Meridian has no independent Postgres dump schedule as of v0.1 (this is a gap in the availability risk register — `compliance/risk/register.md`). RTO/RPO are Supabase-dependent until Meridian implements independent backup exports.

---

## Specific Risks & Controls

| Risk | Control | Status |
|---|---|---|
| Cross-tenant data leak via RLS misconfiguration | Per-org RLS on all tenant tables; `require_org_access` dependency on all API routes | Historical incident (remediated); documented as compensating-control strength |
| Supabase project key exposed in codebase | gitleaks scans on all PRs; service role key stored only in Railway env vars and `/root/.secrets/` | Enforced |
| Supabase Auth JWT forged | HMAC-SHA256 JWT validation; `supabase_jwt_secret` stored in Railway and `/root/.secrets/` | Enforced |
| Supabase `authenticated` role losing table GRANTs | Historical incident (2026-06-07, Tier 1+2 fixed); Tier 3 fix status must be verified | Open — verify |

---

## Review Date

TBD — schedule for next annual review cycle. Next attestation download: January 2027 (or at next annual review).
