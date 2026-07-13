# Business Continuity and Disaster Recovery Policy

**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder / Engineering Lead)
**Review cadence:** Quarterly; scenario procedures reviewed within 30 days of any DR event or infrastructure change

---

## Purpose

Define how Meridian AI Business Solutions maintains or restores service following significant infrastructure failures. This policy ties Meridian's contractual 99.5% monthly uptime commitment (`frontend/src/lib/generate-sla-pdf.ts`) to concrete recovery scenarios, documents known single points of failure (SPOFs), and establishes recovery time targets.

Meridian does not claim SOC 2 certification.

---

## Scope

All production infrastructure components:

- **Contabo VPS** (`209.126.80.45`): Celery workers, Redis (task queue), local LLM inference, Garry agent, Canada frontend static files
- **Railway**: Python Flask backend API (auto-deploys from `main`)
- **Supabase**: Primary PostgreSQL database, auth, RLS, Edge Functions
- **Cloudflare**: DNS, CDN, R2 cold storage
- **Third-party integrations**: Square, Clover, Telnyx, Vapi, Resend, Sentry

---

## SLA Tie-In

| Commitment | Source | Implication for DR |
|-----------|--------|-------------------|
| 99.5% monthly uptime | `frontend/src/lib/generate-sla-pdf.ts` | Maximum allowed downtime: ~3.6 hours/month |
| Maintenance windows: 2–6 AM ET, ≤4h/month, 48h notice | Same | Planned downtime must be pre-announced |
| POS data reflected within 60 min | Same | Celery/Redis failure directly breaches this SLA |
| Critical incident response: 1 hour | Same | Detection + initial response within 60 min of outage start |

**Gap:** No uptime monitoring or SLA-tracking tooling exists. Meridian currently has no automated way to measure whether 99.5% is achieved in a given month. This is a compliance gap and a customer-trust gap.

### DECISION (Aidan): Uptime Monitoring

**Recommended default:** Add a free-tier external uptime monitor (UptimeRobot or Better Uptime free tier) polling `https://api.meridian.tips/health` every 60 seconds. Configure email + Telegram notification on failure. This provides:
- Real-time outage detection (closes the paging gap documented in [`incident-response-plan.md`](incident-response-plan.md))
- Monthly uptime reports to validate SLA compliance
- Documented evidence for SOC 2 auditors

**Tradeoff:** Free tiers poll every 5 minutes; 60-second polling requires a paid plan (~$7/month). Either is better than the current zero-monitoring state.

---

## Single Point of Failure Analysis

| Component | SPOF? | Consequence of failure |
|-----------|-------|----------------------|
| Contabo VPS | **YES** | Celery task queue stalls; POS sync stops; local LLM offline; Canada frontend returns 502; Agent logs lost |
| Redis (on Contabo) | **YES** | Celery cannot queue or dequeue tasks; POS data sync halts immediately |
| Railway backend | Partial | Railway is multi-region but single-service; a crash loop causes full API outage |
| Supabase | Partial | Supabase is managed HA with automatic failover; risk is low but not zero |
| Cloudflare DNS | Low | Cloudflare has 100% SLA history; risk negligible |

---

## Failure Scenarios and Recovery Procedures

### Scenario 1: Contabo VPS Loss (Highest Risk)

**Trigger:** VPS becomes unreachable — hardware failure, IP block, or account suspension.

**Impact:**
- Celery workers down → POS sync stopped → 60-min SLA breach begins immediately
- Redis down → task queue gone; in-flight tasks lost
- Canada frontend returns 502 (nginx upstream gone)
- Local LLM / Garry agent offline
- Agent logs inaccessible until new node provisioned

**Recovery procedure:**

1. **Detect** (target: <5 min): UptimeRobot alerts on `https://api.meridian.tips/health` (Railway — still up) AND Canada frontend 502 (Contabo down).
2. **Triage** (target: <15 min): SSH to `209.126.80.45`; if unreachable, log into Contabo portal to check node status.
3. **Temporary mitigation** (target: <30 min for customer-facing impact): Update Cloudflare DNS for Canada frontend to point to a temporary static "maintenance" page hosted on Cloudflare Pages (can be deployed in <10 min from `nova-labs` static dist as a placeholder).
4. **Provision replacement** (target: <4 hours): Spin up new Contabo VPS (Ubuntu 24.04). Run the provisioning playbook in `docs/runbook-contabo-provision.md` (this document must be created — see DECISION below).
5. **Restore services on new node:**
   - Install PM2, Redis, Python venv, Node
   - Restore `/var/meridian/archive/` from latest WARM-tier dump or pull from R2 COLD (see [`backup.md`](backup.md))
   - Copy env files from `/root/.secrets/` backup
   - Start PM2 processes: `pm2 start ecosystem.config.js`
   - Verify Celery workers reconnect to Supabase: check `/health` on Railway
6. **Update DNS:** Point Canada frontend to new VPS IP in Cloudflare DNS.
7. **Verify:** `curl https://api.meridian.tips/health` returns all components green; manually trigger a POS sync test for one merchant.
8. **Post-incident review:** document in `docs/incidents/` per [`incident-response-plan.md`](incident-response-plan.md).

**Estimated RTO:** 4–8 hours (manual provisioning; see DECISION on RTO target in [`backup.md`](backup.md)).

### DECISION (Aidan): Contabo SPOF Reduction

**Current state:** Everything on one VPS. No snapshots, no standby, no automation.

**Recommended default (Phase 1, low cost):**
- Take a Contabo VPS snapshot weekly (available in Contabo portal; ~€1.50/month for a 50GB snapshot).
- Export `pm2 ecosystem.config.js` and a `provision.sh` bootstrap script to the repo (gitignored secrets section) so a new node can be provisioned from scratch in <1 hour.

**Recommended default (Phase 2, medium cost):**
- Migrate Celery/Redis to a managed service: Railway Redis add-on (~$5/month) or Upstash (~$0.20/100K commands). This eliminates the Celery/Redis SPOF entirely.
- Move Canada frontend to Cloudflare Pages or Vercel (static, no VPS dependency).

**Tradeoff:** Phase 1 is ~€1.50/month and ~2 hours of work; closes the "total Contabo loss" gap. Phase 2 requires migration work (~8–16 hours) but would reduce Contabo to hosting only local LLM inference, which is not customer-critical.

---

### Scenario 2: Supabase Outage

**Trigger:** Supabase platform incident affecting the `kbuzufjxwflrutowwnfl` project.

**Impact:**
- All API endpoints requiring DB queries return 503
- Auth token validation fails → all authenticated sessions rejected
- `security_events` writes fail (silent — no alert unless Sentry catches the exception)

**Recovery procedure:**

1. **Detect:** Sentry captures DB connection errors; Railway `/health` returns non-200 on DB component.
2. **Triage:** Check `https://status.supabase.com` — if platform incident, no Meridian action is possible.
3. **Mitigation during outage:** No read-only fallback is currently implemented. Merchants see errors.
4. **If data corruption (not platform outage):** Initiate PITR restore (see [`backup.md`](backup.md)).
5. **Post-restore verification:** Run the same queries as the quarterly restore test; verify `security_events`, `merchants`, and `pos_connections` tables are intact.

**Estimated RTO:** 2–4 hours for PITR restore; depends on Supabase's platform recovery time for a platform incident (typically <1 hour per Supabase SLA).

**Gap:** No read-replica or read-only fallback mode exists. For future resilience, a Supabase read replica or a cached response layer (Redis on Railway) would reduce impact during read-heavy outages.

---

### Scenario 3: Railway Backend Outage

**Trigger:** Railway platform incident, failed deploy causing crash loop, or resource limit hit.

**Impact:**
- All API requests fail (Railway is the only API surface)
- POS sync stalls; merchant portals return errors

**Recovery procedure:**

1. **Detect:** Sentry error spike; `/health` non-200 in uptime monitor.
2. **Triage:** Check `https://status.railway.app` and `railway logs`.
3. **Rollback (if caused by a bad deploy):**
   ```bash
   railway rollback   # reverts to the previous successful deployment
   ```
4. **If crash loop:** Check Railway logs for OOM or startup error; fix in code and redeploy from `main`.
5. **If Railway platform incident:** No action possible; monitor `status.railway.app`.

**Estimated RTO:** <30 minutes for a bad-deploy rollback; up to 4 hours for a Railway platform incident.

**Note:** Railway auto-deploys on merge to `main`. Any merge during an incident investigation must be deliberate — do not push exploratory commits to `main` during a P1.

---

### Scenario 4: Redis Loss on Contabo

**Trigger:** Redis process crashes and PM2 restart loop fails, or Contabo disk full causes Redis RDB corruption.

**Impact:**
- Celery cannot publish or consume tasks
- POS sync halts (60-min SLA breach begins)
- Nightly archive task does not run
- In-flight tasks (e.g., mid-archive) are lost

**Recovery procedure:**

1. **Detect:** PM2 shows Redis process in `errored` state; Celery workers log `ConnectionRefusedError`.
2. **Restart Redis:** `pm2 restart redis-server` (or `sudo systemctl restart redis-server` depending on PM2 config).
3. **If RDB corrupt:** Delete corrupted dump, restart Redis (starts empty), then manually re-queue any known missed tasks:
   ```bash
   redis-cli FLUSHALL  # clear corrupted state
   pm2 restart redis-server
   # Manually trigger nightly archive if it missed the 04:00 UTC run:
   celery -A src.workers.celery_app call src.workers.cold_storage.run_archive
   ```
4. **Verify:** `redis-cli ping` returns `PONG`; `pm2 status` shows Redis and Celery workers as `online`.

**Estimated RTO:** <30 minutes if Redis process failure; up to 2 hours if disk issue requires cleanup.

**Longer-term fix:** See DECISION above — migrate to Railway Redis or Upstash to eliminate this SPOF.

---

## Recovery Objectives (Confirmed Targets Pending Aidan Decision)

See [`backup.md`](backup.md) DECISION block. Proposed targets:

| Metric | Proposed | Confirmed |
|--------|----------|-----------|
| RPO | 24 hours | [ ] TBD |
| RTO | 8 hours | [ ] TBD |

**Note:** An 8-hour RTO is inconsistent with the 99.5% monthly uptime SLA (which allows only ~3.6 hours downtime/month). If Meridian is to reliably meet its SLA during a Contabo failure, RTO must be ≤3 hours. This requires automation (Contabo snapshot restore script or migrating services off Contabo).

---

## No DR Plan for Local LLM / Garry Agent

Meridian's local LLM inference and the Garry agent run exclusively on Contabo. There is no DR path for these services — they go offline with the VPS and do not have a cloud fallback. If these are customer-facing features, this is a material SLA gap.

**Recommended mitigation:** If Garry's LLM inference is customer-facing, add a fallback in the API to route to a Railway-hosted Anthropic API call when the local endpoint is unreachable (environment: `LOCAL_LLM_ENDPOINT` absent → fall back to `ANTHROPIC_API_KEY`).

---

## DR Test Cadence

**Annual tabletop exercise (minimum):** Aidan and any team members walk through Scenario 1 (Contabo loss) verbally, identifying steps that have changed since last review and any gaps in the runbook.

**Biannual recovery drill (target):** Execute Scenario 1 or 2 in a staging environment — spin up a new Contabo node from scratch or restore Supabase to a test project — and time the actual RTO. Document results in `compliance/dr-tests/YYYY-HN-dr-test.md`.

---

## Roles

| Role | Responsibilities |
|------|-----------------|
| Incident Commander (Aidan) | Declares BC/DR event; coordinates recovery; external communications |
| Technical Responder (Aidan) | Executes recovery procedures; updates DNS; verifies service restoration |
| Supabase (managed) | PITR restore tooling; platform incident management |
| Railway (managed) | Rollback tooling; platform incident management |
| Cloudflare (managed) | DNS failover; R2 cold storage access |

---

## Related Policies

- [`backup.md`](backup.md) — provides the data recovery layer for all DR scenarios
- [`incident-response-plan.md`](incident-response-plan.md) — DR events are P1/P2 incidents; IRP governs comms and review
- [`logging-monitoring.md`](logging-monitoring.md) — uptime monitoring gap documented there; same gap drives DR detection delay

---

## Evidence that this policy operates

1. `frontend/src/lib/generate-sla-pdf.ts` — contractual 99.5% uptime and response time commitments that this policy is designed to support.
2. `src/workers/cold_storage.py` and `src/workers/celery_app.py:121` — automated nightly archive that enables Contabo recovery.
3. `compliance/restore-tests/` — quarterly restore test records (see [`backup.md`](backup.md)); a passed restore test is evidence of DR capability.
4. `compliance/dr-tests/` — annual tabletop or drill records.
5. Uptime monitor (once configured per DECISION above) — monthly uptime reports demonstrating SLA measurement capability.
6. `docs/runbook-contabo-provision.md` (to be created) — bootstrap script demonstrating the Contabo recovery path is documented and executable.
