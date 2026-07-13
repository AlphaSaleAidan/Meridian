# Evidence — A1-BACKUP — backups & restore

**v0.1 — 2026-06-28.** Policies: `/policies/backup.md`, `/policies/business-continuity-dr.md`.

## Type I evidence (real)
| Tier | Mechanism | Location |
|---|---|---|
| HOT | Supabase managed PITR (7-day) | Supabase |
| WARM | nightly zstd archive | `src/workers/cold_storage.py`, Contabo `data/archives/` (12 mo) |
| COLD | nightly upload to Cloudflare R2 (SHA-256 manifest) | `cold_storage.py:351`, 04:00 UTC (`celery_app.py:121`) |
| DVC | data versioning to Backblaze B2 | `.dvc/config` (manual `dvc push`) |
| App config | tar+sha256 pre-change | `backups/auth.py.20260617-052614.*` |

## CRITICAL gap — untested restore
**An untested backup is not a control.** No restore has ever been performed/timed. The HOT→archive job does
**not delete** from Supabase (so HOT grows unbounded); R2 objects are **never purged**; the 60-day termination
deletion is unimplemented; `dvc push` is manual (not in Beat).

## Restore-test template (run quarterly; file results here)
```
restore-tests/restore_YYYYMMDD.md
- Source: [Supabase PITR @ timestamp | WARM pg_dump | R2 object]
- Target: throwaway DB
- Steps run / commands
- Rows verified (count vs source) / integrity check
- RTO observed (start→usable): ____   RPO observed (data loss window): ____
- Pass/Fail + follow-ups
```
Proposed targets (DECISION): RPO 24h, RTO 8h — **note:** 8h RTO conflicts with the 99.5% SLA's ~3.6h/mo
allowance; reconcile via DR Phase 2 (see BC/DR policy).

## Status 🔴 backups exist, restore untested → cannot claim A1 recovery until a restore test passes.
