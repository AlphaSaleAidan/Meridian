# Meridian — Evidence Pipeline

> Evidence is organized by **control ID** so the auditor / automation platform traces
> criterion → control → evidence in one hop. v0.1 — 2026-06-28.
>
> **Type I evidence** = the control exists and is designed right *at a point in time* (config, policy, RLS
> definitions, test results). **Type II evidence** = the control *operated across the window* (dated access
> reviews, merged-PR change logs, incident tickets, backup-restore tests, log samples, training records).
>
> **Never fabricate evidence.** If a control is not operating, the gap tracker says so. A fake artifact is
> worse than a gap. Nothing in this tree is a screenshot of a passing control that did not pass.

## Automate-for-free Type II sources (already emitting)
| Source | Evidence type | Where |
|---|---|---|
| Git history | Change management (CC8) | GitHub commits/PRs — immutable, attributed |
| CI runs | Integrity gate (CC5/CC8) | GitHub Actions: `ci.yml`, `syntax-check.yml`, `gitleaks.yml`, `security.yml` |
| `security_events` table | Access/audit (CC6/CC7) | Supabase — `src/api/security/audit_log.py` |
| Sentry | Incident detection (CC7) | external, tamper-resistant |
| Nightly cold-storage archive | Backup (A1) | R2/B2 — `src/workers/cold_storage.py` manifests (SHA-256) |
| `sla_signatures` table | Customer commitments (CC2) | Supabase |

Set these to be exportable + timestamped; they become recurring Type II evidence with no extra work.

## Folder map
| Folder | Control | Contents (this session) | Type I status |
|---|---|---|---|
| `CC6.1-RLS/` | DB row security | `policy_inventory.md`, `fix_rls_wideopen.sql` (authored, not applied), `test_rls_cross_tenant.py` (negative test) | 🔴 gap documented + remediation authored |
| `CC6.1-TENANT/` | API tenant isolation | `evidence-log.md` → existing `tests/api/test_tenant_isolation_bola.py`, guard code refs | 🟡 partial (C1) |
| `CC6.6-AUTH/` | Auth + secrets | `evidence-log.md` → auth model, gitleaks config, ADMIN_EMAILS gap | 🟡 |
| `CC6.7-ENCRYPTION/` | Encryption | `evidence-log.md` → AES-256-GCM impl, HSTS, TLS | 🟢 design good |
| `CC7-INCIDENT/` | Incident response | `evidence-log.md` → Toast/Clover detect→fix→verify precedents | 🟢 precedents real |
| `CC8-CHANGE/` | Change mgmt | `evidence-log.md` → PR/CI history, tar+sha256 rollback artifact | 🟢 strongest |
| `A1-BACKUP/` | Backups | `evidence-log.md` → archive schedule + restore-test template (untested) | 🔴 restore untested |
| `PI1-RECONCILE/` | Processing integrity | `evidence-log.md` → Square reconciliation, gaps | 🔴 Square-only |
| `P-PRIVACY/` | Privacy | `evidence-log.md` → CASL/consent/DSAR + resale disclosure gap | 🔴 disclosure gap |

## Policy ↔ control ID note
The policy set under `/policies/` was authored with its own `POL-00N` document IDs and references
`evidence/POL-00N/` folders. Those map onto the control IDs here as follows (the auditor can use either index):
POL-001 InfoSec→all · POL-002 Access→CC6.1-TENANT/CC6.6-AUTH · POL-003 Password→CC6.6-MFA/AUTH ·
POL-004 Encryption→CC6.7-ENCRYPTION · POL-005 SDLC→CC8-CHANGE · POL-006 Change→CC8-CHANGE.
Evidence is filed under the **control ID** folders here; policy "evidence that this policy operates" sections
point to the same artifacts.

## Backfill status
Type I pointers are backfilled in each `evidence-log.md` (links to real source files/configs). Type II
collection **starts when the observation window opens** (Phase 6). The recurring collectors above already
emit; they need to be exported on a schedule and retained.
