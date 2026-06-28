# Backup and Recovery Policy

**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder / Engineering Lead)
**Review cadence:** Quarterly; restore test results must be appended within 7 days of each quarterly test

---

## Purpose

Define how Meridian AI Business Solutions backs up its data, where backups are stored, what the recovery objectives are, and — critically — how recovery is tested. An untested backup is not a control.

Meridian does not claim SOC 2 certification.

---

## Scope

All persistent data produced or processed by Meridian:

- Supabase PostgreSQL (tenant data, `security_events`, merchant configs, POS connections, order history)
- Agent / LLM training data managed by DVC
- Frontend build artifacts (not primary data; regenerable from source)
- Configuration state (Railway env vars, Supabase edge function config)

---

## 3-Tier Backup Architecture

Meridian operates a 3-tier data archiving system implemented in `src/workers/cold_storage.py`. The Celery Beat scheduler triggers the nightly archive at **04:00 UTC** (`src/workers/celery_app.py:121`).

| Tier | Label | Storage | Retention | Compression | Contents |
|------|-------|---------|-----------|-------------|----------|
| HOT | Live | Supabase PostgreSQL (managed) | 90 days rolling | None (live DB) | All tables; queryable in real time |
| WARM | Archive | Contabo VPS local disk (`/var/meridian/archive/`) | 12 months | `zstd` compressed dumps | Nightly `pg_dump` snapshots |
| COLD | Historical | Cloudflare R2 (`meridian-cold-archive` bucket) | Indefinite (all history) | `zstd` | Promoted from WARM monthly |

**Note:** The HOT tier does NOT automatically purge data after 90 days — HOT→WARM is a copy, not a move. Supabase's live database accumulates all records until a manual purge is run. This is by design for audit trail purposes but should be reviewed annually for storage cost.

**Note:** R2 objects are never deleted. All history is retained in COLD storage indefinitely. If a data deletion obligation arises (merchant termination, Law 25 erasure request), R2 objects must be deleted manually via `wrangler r2 object delete`.

---

## Supabase Managed Backups (Point-in-Time Recovery)

Supabase provides managed PITR (Point-in-Time Recovery) on the Pro plan. PITR allows restoring the database to any second within the retention window.

- **PITR retention:** 7 days (Supabase Pro default; upgradeable to 30 days at additional cost).
- **Trigger:** Supabase handles WAL-based PITR automatically; no Meridian action required.
- **Recovery:** Via Supabase dashboard → Backups → Point in Time → select timestamp → restore to new project.

PITR is Meridian's **primary recovery mechanism** for data corruption or accidental deletion events. The nightly `pg_dump` pipeline is the secondary / offline copy.

---

## DVC Remote (Backblaze B2)

Machine learning training data, evaluation sets, and vector index snapshots are versioned via DVC with a Backblaze B2 remote (configured in `.dvc/config`).

- **What's covered:** Files tracked by DVC (`dvc push` includes `.dvc` pointer files pushed to B2).
- **Cadence:** `dvc push` is run manually before any training run; no automated schedule exists yet.
- **Gap:** DVC push is not part of the nightly Celery Beat job. If training data is updated without a `dvc push`, B2 will not have the latest version.

### DECISION (Aidan): Add DVC Push to Nightly Job

**Recommended default:** Add a `dvc push` step to the nightly Celery Beat task in `src/workers/celery_app.py` so B2 backup of training data is automatic. Requires the Backblaze B2 credentials to be present on Contabo as env vars.

**Tradeoff:** Adds ~30 seconds to nightly run; eliminates the risk of losing training data between manual pushes.

---

## Recovery Objectives

### DECISION (Aidan): RPO and RTO Targets

**Recommended defaults:**

| Metric | Proposed Target | Rationale |
|--------|----------------|-----------|
| RPO (Recovery Point Objective) | **24 hours** | Nightly `pg_dump` at 04:00 UTC means maximum data loss is ~24h of new records. Supabase PITR narrows this to seconds for the live DB. |
| RTO (Recovery Time Objective) | **8 hours** | Time to restore Supabase from PITR + redeploy Railway backend + verify `/health` = approximately 2–4 hours technical work; 8 hours is a conservative SLA buffer. |

**Tradeoff:** The 99.5% monthly uptime SLA in `frontend/src/lib/generate-sla-pdf.ts` allows ~3.6 hours downtime/month. An 8-hour RTO would breach this SLA if the outage exceeds 3.6 hours. If the target is to always meet the SLA, RTO should be reduced to ≤3 hours, which requires more automated recovery tooling.

**Aidan's action:** Confirm RPO 24h / RTO 8h or set tighter targets. Document in this file under "Confirmed Targets" once decided.

---

## What Is NOT Automatically Backed Up

| Item | Current state | Risk |
|------|-------------|------|
| Railway environment variables | Not backed up; set manually in Railway dashboard | Loss of Railway project = re-entering all secrets manually |
| Supabase Edge Function config | Not backed up | Function code is in `supabase/functions/` in the repo (source control is the backup) |
| Contabo VPS system state | No snapshot / image | Full Contabo loss requires reprovisioning from scratch (see `business-continuity-dr.md`) |
| Redis state (Celery task queue) | No HA, no RDB/AOF backup | Queue loss on Redis crash = tasks must be re-queued manually; no data loss if tasks are idempotent |

**Highest risk:** Railway env vars. If the Railway project is deleted or inaccessible, all secrets must be re-entered. Recommend exporting a `.env.railway` file to `/root/.secrets/meridian-railway.env` (gitignored, chmod 600) as a manual offline backup.

---

## Backup Encryption

| Tier | Encryption at rest | Encryption in transit |
|------|-------------------|----------------------|
| HOT (Supabase) | AES-256 (Supabase managed) | TLS 1.2+ |
| WARM (Contabo local) | Not encrypted (host disk encryption status unknown) | N/A (local disk) |
| COLD (Cloudflare R2) | AES-256 (R2 managed) | TLS |
| DVC / B2 | AES-256 (B2 server-side) | TLS |

**Gap:** WARM-tier dumps on Contabo are stored as cleartext zstd files on the VPS. If the VPS is compromised, these dumps are readable. Recommend encrypting WARM-tier dumps with `gpg --symmetric` using a passphrase stored in `/root/.secrets/meridian-backup-passphrase.txt` (chmod 600, never committed).

---

## Mandatory Quarterly Restore Test

**An untested backup is not a control.** Evidence that backups exist is insufficient for SOC 2. Evidence that restores succeed is required.

**Procedure (quarterly, approximately 2 hours):**

1. **Supabase PITR test:**
   - Select a timestamp 24 hours prior.
   - Restore to a new Supabase project (not production).
   - Verify: connect with `psql`, run `SELECT COUNT(*) FROM merchants` and one other business-critical table.
   - Document row count and compare to expected production count at that timestamp.
   - Destroy the test project immediately after verification.

2. **WARM-tier `pg_dump` test:**
   - Copy the most recent dump from `/var/meridian/archive/` to a local dev environment.
   - Restore: `zstd -d [file] | psql -U postgres -d meridian_test`.
   - Verify: check at least 3 tables for expected row counts.

3. **Record results** in `compliance/restore-tests/YYYY-QN-restore-test.md` (format: date, tier tested, tables verified, pass/fail, tester name).

---

## Merchant Data Deletion on Termination

Per the contractual SLA (`frontend/src/lib/generate-sla-pdf.ts`): data is returned within 30 days and deleted within 60 days of termination.

**Procedure:**
1. Export merchant data: `pg_dump --table=merchants --where="org_id='[uuid]'"` + all foreign-keyed tables.
2. Deliver export to merchant via secure S3/R2 pre-signed URL.
3. Delete from Supabase: cascade delete from `merchants` (RLS and FK constraints handle child rows).
4. Delete from WARM tier: locate and delete dump files containing the org's data.
5. Delete from COLD tier: `wrangler r2 object delete meridian-cold-archive/[prefix]` for all objects tagged with the org_id.
6. Log deletion in `breach_log` with `event_type = 'merchant_data_deletion'` and timestamp.

---

## Roles

| Role | Responsibilities |
|------|-----------------|
| Owner (Aidan) | Authorizes restore tests; reviews restore test records quarterly; signs off on any deletion |
| Celery Beat (automated) | Runs nightly 04:00 UTC archive task |
| Supabase (managed) | PITR snapshot management |
| Cloudflare R2 | COLD tier object storage; lifecycle rules (none configured — Aidan decision needed) |

---

## Related Policies

- [`business-continuity-dr.md`](business-continuity-dr.md) — uses backup restore as the primary DR mechanism
- [`incident-response-plan.md`](incident-response-plan.md) — Phase 4 recovery references backup restore
- [`logging-monitoring.md`](logging-monitoring.md) — `security_events` table is part of the backed-up dataset

---

## Evidence that this policy operates

1. `src/workers/cold_storage.py` — 3-tier archive code exists and is deployed.
2. `src/workers/celery_app.py:121` — Celery Beat schedule shows 04:00 UTC trigger for archive task.
3. `.dvc/config` — DVC remote configured to Backblaze B2.
4. Contabo VPS: `/var/meridian/archive/` contains at least one dump file timestamped within the past 25 hours (run `ls -lh /var/meridian/archive/ | tail -5` to verify).
5. Cloudflare R2 dashboard shows objects in `meridian-cold-archive` bucket.
6. `compliance/restore-tests/` directory contains at least one `YYYY-QN-restore-test.md` showing a successful restore (due by the first quarterly review after this policy is adopted).
