# Incident Response Plan

**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder / Engineering Lead)
**Review cadence:** Quarterly, or within 30 days of any P1/P2 incident

---

## Purpose

Define how Meridian AI Business Solutions detects, classifies, contains, and recovers from security incidents and service disruptions. This plan ties Meridian's customer-facing SLA commitments (documented in `frontend/src/lib/generate-sla-pdf.ts`) to concrete internal procedures, and establishes a documented capability to notify Quebec's Commission d'accès à l'information (CAI) within 72 hours of a confirmed personal-information breach.

Meridian does not claim SOC 2 certification. This policy is part of the compliance program being built toward that goal.

---

## Scope

All production systems operated by Meridian AI Business Solutions:

- Railway-hosted backend API (`src/api/app.py`)
- Supabase tenant database (including `security_events` audit table, per `src/api/security/audit_log.py`)
- Contabo VPS (Celery workers, Redis, local LLM inference, Garry agent, Canada frontend dist)
- Canadian merchant-facing portal (`meridian.tips`)
- POS integrations: Square, Clover
- SMS/voice channels: Telnyx, Vapi

---

## Severity Tiers and SLA Response Times

These tiers map directly to the contractual response targets in `frontend/src/lib/generate-sla-pdf.ts` and `docs/customer-sop.md:191`.

| Tier | Label | Definition | Initial Response Target | Resolution Target |
|------|-------|------------|------------------------|-------------------|
| P1 | Critical | Data breach / unauthorized PII access; full service outage affecting all merchants; POS ordering down; confirmed ransomware or account takeover | **1 hour** | Best effort, no SLA cap |
| P2 | High | Single-merchant outage; authentication failures for >10% of sessions; cross-tenant data leak (scoped); Celery/Redis failure causing stale POS data | **4 hours** | 12 hours |
| P3 | Medium | Non-critical feature degraded; POS sync delay >60 min threshold; intermittent 5xx on single endpoint | **1 business day** | 3 business days |
| P4 | Low | Cosmetic bugs; minor latency increase; documentation gap; single failed cron run | **3 business days** | Next sprint |

---

## Detection Sources

Meridian currently has the following detection surfaces (all must be checked for each incident):

| Source | What it surfaces | Location |
|--------|-----------------|----------|
| Sentry | Unhandled exceptions, slow transactions, error groups | `src/api/app.py:23-32`; dashboard sentry.io |
| `security_events` table | `login_success`, `invalid_token`, `rls_violation_attempt`, `pos_credential_access`, `admin_action`, `brute_force`, `prompt_injection` — see `src/api/security/audit_log.py` | Supabase; readable only by `admin` / `canada_manager` roles via RLS |
| Railway health check | `GET /health` 200/non-200 + container restarts | `railway.toml`; Railway dashboard |
| Docker HEALTHCHECK | Container-level liveness | `Dockerfile:35` |
| `/health` endpoint | Component-level: DB connectivity, Redis, Celery | `src/api/app.py:269-279` |
| PM2 process health | Celery worker crash loops on Contabo | `pm2 status` on VPS |
| Structured agent logs | LLM agent anomalies, prompt injection attempts | `logs/agents/*.log` on Contabo |
| Customer report | Merchant emails / phone calls | Aidan directly |

### DECISION (Aidan): On-Call Paging

**Current state:** No PagerDuty or OpsGenie is configured. Telegram alerting exists only for the SEO cron engine — the core API has no automated paging.

**Gap:** P1 incidents can go undetected until business hours unless Aidan or a team member notices Sentry email digests.

**Recommended default:** Add a single free-tier PagerDuty account wired to Sentry's alert rules for P1/P2 conditions (e.g., error rate >5% in 5 min, `/health` non-200 for >3 min). Sentry→PagerDuty webhook takes ~30 minutes to set up.

**Tradeoff:** Free tier limits policy routing; paid tier is ~$19/user/month. Alternatively, a Telegram webhook on Railway's built-in health alerts is a zero-cost interim.

---

## Incident Response Procedure

### Phase 1 — Detection & Classification (Target: within 15 min of alert)

1. Responder (Aidan or designated) receives alert via Sentry email / manual discovery / customer report.
2. Validate by checking `GET https://api.meridian.tips/health` and `security_events` table:
   ```sql
   SELECT event_type, details, created_at
   FROM security_events
   WHERE created_at > now() - interval '1 hour'
   ORDER BY created_at DESC;
   ```
3. Assign severity tier (P1–P4) using the table above.
4. Open an entry in `breach_log` table (for any P1 or P2 involving PII):
   ```sql
   INSERT INTO breach_log (discovered_at, severity, description, affected_rows_estimate, responder)
   VALUES (now(), 'P1', '[description]', NULL, 'aidan');
   ```
5. If P1/P2: immediately post in the Telegram ops channel noting time discovered, tier, and initial symptoms.

### Phase 2 — Containment

**For auth / cross-tenant leaks (see worked precedent CA-1/CA-2 below):**
- Revoke suspect JWTs via Supabase Auth admin API.
- If cross-org body-bypass: set `REQUIRE_ORG_SCOPE=true` kill-switch env var on Railway (takes effect on next request, no redeploy needed if the guard at `src/api/auth.py:142-225` reads from env).
- Block IP ranges in Cloudflare if brute-force confirmed.

**For POS credential exposure:**
- Rotate Square/Clover OAuth tokens immediately via the respective partner portal.
- Disable affected merchant's integration row in Supabase (`pos_connections` table) — set `active = false`.

**For Contabo VPS compromise:**
- Isolate node: remove from Cloudflare DNS / nginx upstream immediately.
- Do not power off — preserve evidence for forensics.

**For Celery / Redis failure:**
- Railway backend is stateless; Celery workers on Contabo are the SPOF. If Redis is down, Celery task queue stalls — POS sync will exceed the 60-min SLA.
- Manually drain queued tasks: `redis-cli FLUSHDB` only after confirming tasks are safe to discard or will auto-retry.

### Phase 3 — Eradication

1. Root-cause via `security_events` query and Sentry trace.
2. Patch deployed via Railway (auto-deploys on merge to `main`) or manual `rsync` to Contabo frontend.
3. Verify fix: re-run the specific failing request pattern in staging or via `curl` against prod `/health`.
4. Remove any attacker artifacts (unauthorized SSH keys, cron entries on Contabo — check `crontab -l` and `/etc/cron.d/`).

### Phase 4 — Recovery

1. Confirm `/health` returns 200 and all components healthy.
2. Restore POS sync by checking the nightly archive job in Celery Beat (`src/workers/celery_app.py:121`) did not stall mid-run.
3. Notify affected merchants: use the Resend email transport (via Railway env, not direct paste). Draft uses template in `src/api/notifications/`.
4. Update `breach_log` with resolution timestamp and final scope assessment.

### Phase 5 — Post-Incident Review

- P1/P2: Written review within 5 business days. Covers timeline, root cause, what Meridian's monitoring did/didn't catch, and at least one concrete prevention action.
- P3/P4: Brief note in the incident ticket; no formal review required unless a pattern emerges.
- Review document stored in `docs/incidents/YYYY-MM-DD-[slug].md`.

---

## Breach Notification — Quebec CAI (72-Hour Requirement)

Quebec's Act respecting the protection of personal information in the private sector (Law 25) requires notification to the CAI within **72 hours** of a confirmed breach involving personal information. Meridian processes Canadian merchant and consumer PII.

**Trigger:** Any P1 or P2 incident where `affected_rows_estimate > 0` on PII fields (name, email, phone, SIN, payment reference).

**Steps:**
1. Confirm breach scope: query `breach_log` + affected Supabase tables.
2. Complete CAI online declaration form at `https://www.cai.gouv.qc.ca` within 72 hours of discovery.
3. Notify affected individuals "in the most expedient time possible" per Law 25, using Resend (transactional email) or Telnyx SMS.
4. Retain `breach_log` record for minimum 5 years.

### DECISION (Aidan): Breach Notification Template

**Recommended default:** Draft a short bilingual (EN/FR) breach notification email template and store it in `src/api/notifications/breach_notification.html`. This avoids writing one under pressure during a P1.

**Tradeoff:** A few hours of drafting now vs. scrambled comms during a real incident. Low effort, high value.

---

## Roles

| Role | Responsibilities |
|------|-----------------|
| Incident Commander (Aidan) | Declares severity, owns external communications, signs breach notifications, signs off on recovery |
| Technical Responder (Aidan or future hire) | Executes containment/eradication steps, updates `breach_log` |
| Customer Contact (Aidan) | Merchant-facing communications via Resend / Telnyx |

---

## Appendix A: Worked Precedent — Toast Webhook HMAC Fix (P2)

**Date:** 2026-06-27 (see `docs/SECURITY_SWEEP_2026-06-27.md`, PR #176)

**Detection:** Code review during security sweep identified missing HMAC signature validation on inbound Toast webhook endpoint. Unauthenticated POST requests could inject arbitrary order data.

**Containment:** Endpoint protected with HMAC middleware before any further orders processed.

**Eradication:** PR #176 merged; Railway auto-deployed to production. Verified by sending a test webhook with an invalid signature — rejected 401.

**Lesson:** Webhook receivers must validate `X-Toast-HMAC-SHA256` header on every request. Added to `src/api/security/audit_log.py` as `pos_credential_access` event type. No PII was confirmed exfiltrated; no CAI notification triggered.

---

## Appendix B: Worked Precedent — Clover/Square OAuth State Secret Fix (P2)

**Date:** 2026-06-16 (see `docs/POS_CONNECT_SESSION_2026-06-16.md`)

**Detection:** Monitoring of OAuth callback success rate showed ~75% completion; 25% of Clover OAuth flows failed with CSRF state mismatch.

**Containment:** Identified `OAUTH_STATE_SECRET` env var unset in Railway production environment.

**Eradication:** Set `OAUTH_STATE_SECRET` in Railway; verified callback success rate rose to 100% in subsequent merchant connections.

**Lesson:** OAuth state secrets must be present before any merchant goes live. Added to Railway environment checklist in `docs/runbook-deploy.md`.

---

## Related Policies

- [`logging-monitoring.md`](logging-monitoring.md) — `security_events` taxonomy, log retention
- [`vulnerability-management.md`](vulnerability-management.md) — vulnerability intake and patching SLAs
- [`backup.md`](backup.md) — data recovery during incident eradication
- [`business-continuity-dr.md`](business-continuity-dr.md) — scenarios where incident = sustained outage

---

## Evidence that this policy operates

The following artifacts demonstrate this IRP is active (not just written):

1. `breach_log` Supabase table exists and is writable by `service_role` only.
2. `security_events` table populated with real events from `src/api/security/audit_log.py` — query shows non-zero rows from production.
3. `docs/SECURITY_SWEEP_2026-06-27.md` — written post-incident review for PR #176 (Toast HMAC).
4. `docs/POS_CONNECT_SESSION_2026-06-16.md` — written post-incident review for OAuth state fix.
5. `src/api/auth.py:142-225` — cross-tenant bypass guards (CA-1/CA-2) merged and active.
6. Quarterly review date logged in `compliance/review-log.md` (to be created at first review).
