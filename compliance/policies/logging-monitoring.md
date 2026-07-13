# Logging and Monitoring Policy

**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder / Engineering Lead)
**Review cadence:** Quarterly; updated within 7 days of any new log source added or removed

---

## Purpose

Define what Meridian AI Business Solutions logs, where those logs are stored, how long they are retained, who can access them, and how they are reviewed. This policy also documents current monitoring gaps and the alerting roadmap.

Meridian does not claim SOC 2 certification.

---

## Scope

- Backend API: Railway-hosted Python Flask app (`src/api/app.py`)
- Audit events: Supabase `security_events` table (`src/api/security/audit_log.py`)
- Celery workers and agent processes on Contabo VPS
- Sentry application monitoring
- Optional/env-gated: PostHog, Highlight.io

---

## What Is Logged

### 1. Security Audit Events — `security_events` Table

Source: `src/api/security/audit_log.py`. Every call to `log_security_event()` writes a row to this table. Row-Level Security restricts reads to the `admin` and `canada_manager` roles only — no merchant or anonymous session can query this table.

| `event_type` value | When it fires | Risk signal |
|-------------------|---------------|-------------|
| `login_success` | Successful Supabase auth token validation | Baseline; abnormal volume = credential stuffing |
| `invalid_token` | JWT signature invalid or expired | Reconnaissance or replay attempt |
| `rls_violation_attempt` | Supabase RLS policy blocks a query that reached the DB | Cross-tenant probe |
| `pos_credential_access` | Square/Clover OAuth token retrieved from `pos_connections` | Legitimate ops or lateral movement |
| `admin_action` | Any request authenticated with `X-Admin-Key` header | All admin ops must be traceable |
| `brute_force` | >5 failed auth attempts from a single IP in 60 seconds | Active attack |
| `prompt_injection` | LLM agent input flagged by injection classifier | Adversarial merchant or end-user input |

**Schema (relevant columns):**

```sql
security_events (
  id            uuid primary key default gen_random_uuid(),
  event_type    text not null,              -- one of the values above
  user_id       uuid references auth.users, -- null for unauthenticated events
  org_id        uuid,                       -- merchant org scope
  ip_address    inet,
  details       jsonb,                      -- structured context (endpoint, payload excerpt)
  severity      text,                       -- 'critical' | 'warning' | 'info'
  created_at    timestamptz default now()
)
```

### 2. Application Error Logs — Sentry

Source: `src/api/app.py:23-32`.

```python
sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    send_default_pii=False,       # PII is never sent to Sentry
    traces_sample_rate=0.2,       # 20% of transactions traced
)
```

`send_default_pii=False` is enforced in code. This means request bodies, user IP addresses, and session tokens are stripped before transmission to Sentry's cloud. Trace sampling at 20% provides performance insight without full-volume data egress.

What Sentry captures: unhandled exceptions, slow transactions (>threshold), error groups with stack traces, release-correlated regression detection.

### 3. Structured Agent Logs — Contabo VPS

Source: `logs/agents/*.log`. Meridian's LLM agent workers (Garry, Canada pipeline) write structured JSON lines to per-agent log files on the Contabo node.

Contents: agent session ID, merchant org_id, tool calls made (not inputs), token counts, completion status. Prompt content is **not** logged in cleartext (guard: agent log formatter strips message content after the first 50 characters and replaces with `[TRUNCATED]`).

### 4. Process Health — PM2 and Railway

- Railway: container restart counts, CPU/memory metrics, deploy logs — accessible via Railway dashboard and `railway logs`.
- PM2 (Contabo): `pm2 logs` captures stdout/stderr from Celery, Redis-adjacent processes, and the Canada frontend static server.
- Docker HEALTHCHECK (`Dockerfile:35`) writes liveness state to Docker daemon log.
- `/health` endpoint (`src/api/app.py:269-279`) returns JSON with component status (DB, Redis, Celery queue depth). Railway's `railway.toml` healthcheck polls this endpoint.

### 5. Optional/Env-Gated Sources

| Source | Env var gate | What it adds |
|--------|-------------|-------------|
| PostHog | `POSTHOG_API_KEY` | Frontend user behaviour, page views |
| Highlight.io | `HIGHLIGHT_PROJECT_ID` | Full session replay (no PII fields — must be verified per deployment) |

These are disabled unless the env var is set. Their data handling must be reviewed before enabling in production with Canadian merchant PII.

---

## Log Retention

| Log store | Retention | Deletion mechanism |
|-----------|-----------|-------------------|
| `security_events` (Supabase) | **1 year minimum** | Manual purge via `DELETE WHERE created_at < now() - interval '1 year'`; no automatic TTL configured yet |
| Sentry events | 90 days (Sentry default on Team plan) | Sentry auto-purge |
| Railway deploy/runtime logs | 7 days (Railway default) | Railway auto-purge |
| PM2 / agent logs (Contabo) | 90 days | `logrotate` configured: 90-day `maxage` for `logs/agents/*.log`; verify `/etc/logrotate.d/meridian-agents` exists |
| Celery task logs | 30 days | Celery Beat purge task in `src/workers/celery_app.py` |

**Gap:** No automated purge is configured for `security_events`. This means the table grows unbounded. A Celery Beat task to archive rows older than 1 year to `COLD` tier (Cloudflare R2) and delete from Supabase should be added — tracked as a Medium finding in `docs/SECURITY_SWEEP_2026-06-27.md`.

---

## Log Access Controls

| Log store | Who can read | Mechanism |
|-----------|-------------|-----------|
| `security_events` | `admin`, `canada_manager` roles only | Supabase RLS policy |
| Sentry | Aidan (account owner) | Sentry org membership |
| Railway logs | Aidan (Railway account owner) | Railway team membership |
| PM2 / agent logs on Contabo | Aidan (SSH key auth only, no password login) | Linux file permissions (`640`, owned by `meridian` user) |

### Tamper-Evidence and Separation of Duties

Meridian is a single-founder company. This creates an inherent separation-of-duties limitation: Aidan can both write code and access logs. The following compensating controls are in place:

1. **`security_events` is append-only for application service accounts.** The Railway backend connects to Supabase as the `authenticated` or `anon` role, which has `INSERT` but not `DELETE` or `UPDATE` on `security_events`. Only `service_role` (held by Aidan, not embedded in application code) can delete rows.
2. **Sentry is a third-party SaaS.** Event history in Sentry cannot be silently altered from the codebase — any deletion requires Sentry dashboard access and leaves an audit trail in Sentry's own logs.
3. **Agent logs on Contabo are written by PM2 child processes under a service user**, not the interactive SSH session. Modification requires SSH access and leaves `mtime` changes detectable by a future integrity baseline.

### DECISION (Aidan): Weekly Log Review

**Recommended default:** Schedule a 15-minute weekly review of `security_events` filtered to `severity IN ('critical', 'warning')` in the past 7 days. This is the minimum viable human review loop.

**Tradeoff:** Without a formal review schedule, logs exist but no one reads them — they provide no security value and no audit evidence. A calendar reminder and a saved Supabase query is sufficient to operationalize this.

**Proposed query to bookmark in Supabase Studio:**
```sql
SELECT event_type, count(*), max(created_at) as latest
FROM security_events
WHERE severity IN ('critical', 'warning')
  AND created_at > now() - interval '7 days'
GROUP BY event_type
ORDER BY count(*) DESC;
```

---

## Alerting — Current State and Gaps

| Condition | Current alerting | Gap |
|-----------|-----------------|-----|
| Unhandled exception (P1 code path) | Sentry email digest (batch, not real-time) | No instant page; see IRP DECISION on PagerDuty |
| `/health` non-200 | Railway dashboard; no proactive notification | No uptime monitor; 99.5% SLA has no enforcement tooling |
| `brute_force` event in `security_events` | None — rows written but no alert fired | Need a Supabase Edge Function or Celery task polling for bursts |
| `prompt_injection` event | None | Same as above |
| Redis / Celery crash on Contabo | PM2 restart loop; no external notification | Telegram hook on PM2 event or a cron health probe would close this |
| SEO cron failures | Telegram (SEO engine only) | Telegram alerting not connected to core API |

**Recommended short-term actions (all low effort):**

1. Add a Supabase Edge Function that queries `security_events` for `brute_force` or `prompt_injection` events in the past 5 minutes and fires a Telegram message to the ops channel. (~2 hours implementation.)
2. Add a free external uptime monitor (UptimeRobot, Better Uptime free tier) polling `https://api.meridian.tips/health` every 60 seconds with email + Telegram notification on failure. (~30 minutes.)

---

## Roles

| Role | Responsibilities |
|------|-----------------|
| Owner (Aidan) | Weekly log review; maintains log access list; approves log retention changes |
| Railway system | Auto-purges runtime logs after 7 days |
| Supabase | RLS enforcement on `security_events`; PITR of all tables |
| Developer (Aidan) | Adds `log_security_event()` calls for new sensitive operations; reviews Sentry error groups weekly |

---

## Related Policies

- [`incident-response-plan.md`](incident-response-plan.md) — log sources used during incident detection
- [`vulnerability-management.md`](vulnerability-management.md) — logging of exploit attempts confirms vuln status
- [`backup.md`](backup.md) — `security_events` table is included in Supabase PITR backup

---

## Evidence that this policy operates

1. `security_events` table exists in Supabase with non-zero rows from production traffic — screenshot or `COUNT(*)` query result from production.
2. `src/api/security/audit_log.py` — source code shows `log_security_event()` called for each event type above.
3. `src/api/app.py:23-32` — `send_default_pii=False` visible in Sentry init.
4. Sentry project shows active error reporting: at least one error group from production in the past 30 days.
5. Railway dashboard shows health check polling active (`railway.toml`).
6. Weekly log review: a recurring calendar entry or `compliance/review-log.md` entry showing the last review date and `security_events` query result (row count by event type).
