# Vendor: Contabo VPS
**Document ID:** VEN-003
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce

---

## Role

Unmanaged virtual private server hosting Meridian's async processing tier and supplementary services. Not in Meridian's prior 7-vendor sub-processor list — **this is a gap now resolved by registration here.**

**Server:** `209.126.80.45` · **Location:** St. Louis, MO data center · **OS:** Ubuntu 24.04

**What runs on Contabo (PM2 `ecosystem.config.js`):**
- Celery workers and Celery Beat scheduler (async task processing)
- Redis (task queue broker, ephemeral session cache)
- DeerFlow (research agent)
- Garry (self-healing agent)
- Kimi K2.6 LiteLLM gateway (`:4000`) — LLM proxy
- Canada frontend static files (nginx-served, git-built manually)
- Postal email MTA (self-hosted email transport — see [email.md](./email.md))
- SEO engine cron processes (`seo-engine/`)
- Backblaze B2 DVC remote access

**Integration path:** `ecosystem.config.js` (PM2 config), `src/workers/` (Celery tasks), nginx config (Canada frontend)

---

## Data Touched

| Data category | Details |
|---|---|
| Async task payloads | All data processed by Celery workers passes through Contabo memory; includes customer names, order data, LLM prompts, POS sync payloads |
| Redis cache | Ephemeral session data, Celery task queues; Redis runs unauthenticated on localhost (bound to 127.0.0.1 only — verify) |
| `/root/.secrets/` | Long-lived API keys and credentials (Supabase, Stripe, Square, Telnyx, etc.) stored in files with `chmod 700`. This is the most sensitive artifact on the box. |
| Email content | Postal MTA handles all outbound email content (see [email.md](./email.md)) |
| SEO monitoring data | Domain metrics, ranking data — no customer PII expected but verify |
| LiteLLM gateway logs | Prompts and completions flowing through Kimi gateway are logged at `:4000` level — verify log content and retention |

---

## Attestation Status

| Attestation | Status |
|---|---|
| SOC 2 | **None.** Contabo is a commodity VPS provider with no independent SOC 2 or ISO 27001 certification as of 2026-06-28. Check annually at contabo.com whether this changes. |
| ISO 27001 | **Not confirmed.** Contabo's website references physical security measures but provides no attestation. |
| PCI DSS | **Not applicable** — no raw card data should transit Contabo (Stripe and Square handle PCI scope; Twilio is the PCI-scoped risk, not Contabo). Verify. |

**This is a known attestation gap.** Contabo is a single-point-of-failure AND lacks independent security attestation. Both findings are documented in `compliance/risk/register.md`.

---

## Compensating Controls (in lieu of SOC 2)

| Control | Detail | Verification |
|---|---|---|
| Canonical data in Supabase | Supabase (SOC 2 attested) holds all persistent customer data. Contabo processes transient workloads only; a Contabo failure does not result in data loss (data is in Supabase). | Architecture review |
| SSH key-only authentication | `PasswordAuthentication no` in `/etc/ssh/sshd_config`; only Aidan Pierce's SSH public key is authorized | `sshd -T | grep passwordauth` |
| Secrets file permissions | `/root/.secrets/` is `chmod 700`, accessible only by root | `ls -la /root/.secrets/` |
| TLS in transit | All external connections to/from Contabo are TLS 1.2+; Redis bound to 127.0.0.1 (no external exposure) | Network scan / `ss -tlnp` |
| Gitleaks | Secret scanning on all PRs prevents hardcoding keys in source | GitHub Actions run history |
| Process inventory | Aidan Pierce reviews PM2 process list (`pm2 list`) during quarterly security reviews for unexpected processes | Quarterly review log |
| No direct DB access from Contabo | Celery workers connect to Supabase via the Supabase API + service role key (not direct Postgres); reduces blast radius | Code review: `src/workers/` |

---

## DPA Status

**No formal DPA.** Contabo is a compute provider; Meridian is the data controller and Contabo is a data processor (infrastructure). Contabo's standard Terms of Service govern the relationship. For GDPR/PIPEDA purposes, Contabo's data center in St. Louis (US) means data is processed in the US, which may require documentation for Canadian customers.

**Action required:** Review Contabo's ToS for data processing provisions. For Canadian customer data passing through Contabo workers, document the US processing basis (PIPEDA permits this with adequate safeguards). Record in `compliance/evidence/POL-008/vendor-attestations/contabo-dpa-status.md`.

---

## What Breaks if Contabo Fails

**Impact: HIGH (non-catastrophic due to canonical data in Supabase)**

- All async task processing stops (Celery/Beat): no background LLM calls, no DeerFlow research, no SEO cron, no cold-archive sync.
- Canada frontend goes offline (nginx-served static files on Contabo).
- Postal email MTA stops — transactional emails queue or fail (Resend is the fallback for critical emails, verify).
- LiteLLM Kimi gateway goes offline — any services routing through `:4000` fall back to direct provider APIs.
- Redis cache goes offline — session caching degrades but Railway API continues serving from Supabase.
- **Railway API (`api.meridian.tips`) continues operating** — Railway and Supabase are independent of Contabo.

**Recovery:** Manual SSH to Contabo, `pm2 resurrect`, or complete re-provision from `ecosystem.config.js`. No automated recovery. This is a known High risk in the register.

---

## Review Date

TBD — check annually whether Contabo has obtained SOC 2 certification. If not obtained by the time Meridian pursues a Type II examination, consider migrating async workers to an attested provider (Railway, Render, Fly.io) or narrowing Contabo's scope to minimize data exposure.
