# Vendor: Railway
**Document ID:** VEN-002
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce

---

## Role

Managed application hosting platform for Meridian's FastAPI backend (`api.meridian.tips`). Railway manages containerized deployments, environment variable storage, build pipelines, and deployment logs. Railway is the API layer through which all customer-facing requests flow.

**Project:** `miraculous-curiosity` / Meridian / production environment

**Integration path:** `railway.toml` (deployment config), `.github/workflows/` (CI triggers Railway deploy on merge to main)

---

## Data Touched

| Data category | Details |
|---|---|
| Environment variables / secrets | ALL production secrets: Supabase URL + service role key, Stripe secret key, Square OAuth client secret, Telnyx API key, JWT signing secret, MERIDIAN_ADMIN_KEY, Postal SMTP credentials, and all other env vars defined in `.env.example` |
| API request/response logs | May contain PII in request bodies (customer names, phone numbers) and response bodies if logging is verbose. Sentry integration (`src/api/app.py:23`) should be the primary exception sink with PII scrubbed. |
| Build artifacts | Compiled application code (no customer data in build artifacts) |
| Process memory | During request handling, all in-flight customer data (PII, order payloads, LLM responses) passes through Railway process memory |

Railway holds ALL production secrets. A Railway account compromise is equivalent to a full key rotation emergency across all integrated services.

---

## Attestation Status

| Attestation | Status | Source |
|---|---|---|
| SOC 2 Type II | Public — verify at [railway.app/legal](https://railway.app/legal) or Railway's trust center | Download annually |
| ISO 27001 | Verify — Railway's underlying infrastructure is AWS; check whether Railway's own SOC 2 scope covers this | TBD |

**Annual evidence action:** Download Railway SOC 2 report → `compliance/evidence/POL-008/vendor-attestations/railway-soc2-<year>.pdf`.

---

## DPA Status

Railway provides a Data Processing Agreement. Verify at railway.app/legal and confirm whether it has been executed for the Meridian account. Record in `compliance/evidence/POL-008/vendor-attestations/railway-dpa-status.md`.

---

## What Breaks if Railway Fails

**Impact: CRITICAL**

- `api.meridian.tips` goes offline immediately — all merchant portal, rep portal, and phone agent API calls fail.
- New POS orders cannot be written.
- Phone agent cannot retrieve merchant context or submit orders.
- Static Canada frontend continues to load (served from Contabo), but all dynamic API calls fail.
- All async workers on Contabo continue to run but cannot receive new tasks from the API.

**Recovery:** Railway provides automatic multi-AZ deployment within its AWS region. Meridian has no second-region failover. RTO is Railway-dependent. Meridian's target is to receive Railway's status updates via status.railway.app monitoring (document monitoring setup in availability evidence).

---

## Specific Risks & Controls

| Risk | Control | Status |
|---|---|---|
| Railway env var leaked (e.g., via build log) | Railway env vars are encrypted at rest; Meridian gitleaks prevents committing to git | Enforced |
| Unauthorized Railway deploy from compromised GitHub | GitHub branch protection requires PR review before merge to main; Railway deploys only on merge to main | Enforced |
| Railway account takeover | Railway account secured via GitHub SSO; GitHub account secured by MFA (verify hardware key — see POL-007 DECISION) | Partial — MFA verify |
| Railway log retention exposes PII | Application-level log filtering in `src/api/app.py` (Sentry integration PII scrub) | Verify log verbosity in Railway default logs |

---

## Review Date

TBD — next annual review cycle. Next attestation download: January 2027.
