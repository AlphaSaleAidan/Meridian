# Control CC5-SOD-COMPENSATING — Compensating Controls for Segregation of Duties

**Criterion:** CC5.1/CC5.2 (Control Activities). **Owner:** Aidan Pierce. **v0.1 — 2026-06-28.**

## The reality
Meridian is operated primarily by one person (Aidan, sole US admin/signing authority), with two Canadian
admins (Aidan Nguyen, Enoch Cheung) and occasional contractors under NDA/non-compete. **True segregation of
duties is impossible** — one person authors, reviews, and deploys. SOC 2 accepts this *if* compensating
controls are named, real, and operating. Do not pretend SoD exists; document the compensations.

## Compensating controls (named, each independently evidenced)

| # | Compensating control | Why it compensates | Evidence |
|---|---|---|---|
| 1 | **Immutable, attributable git history** | Every change is permanently attributed and tamper-evident; rewrites are detectable | GitHub commit history; force-push protection (to confirm in branch protection) |
| 2 | **Mandatory PR review before merge** | No change reaches `main`/`session-2-canada-prep` without an explicit human merge decision; agent-authored PRs are reviewed by Aidan | PR merge records; `/policies/change-management.md` |
| 3 | **Automated CI as an independent gate** | ruff, `py_compile`, `tsc --noEmit`, gitleaks **block** merges regardless of author — a non-human reviewer | `.github/workflows/ci.yml`, `syntax-check.yml`, `gitleaks.yml` |
| 4 | **Tamper-evident logging Aidan cannot silently alter** | Security events persisted to Supabase `security_events` + Sentry (external) — an operator cannot quietly erase their own actions | `src/api/security/audit_log.py`; Sentry retention |
| 5 | **Backup-before-change ritual (tar + sha256)** | Independent rollback path; the checksum detects post-hoc tampering | `backups/auth.py.20260617-052614.{tar.gz,sha256}` |
| 6 | **Deliberate, separate production migration step** | DB schema changes are not a side effect of merge; applied manually with a snapshot first | `docs/ARCHITECTURE.md:88-89` |

## Independence requirement (do not fake depth)
These controls must **fail independently**. CI (3) does not depend on the reviewer (2); external logging (4)
does not depend on the operator; the checksum (5) is independent of git (1). A stack of controls that all rely
on the same honest-operator assumption is one control with decoration — that is explicitly avoided here.

## Known weakening factors (remediation tracked in gap-analysis)
- CI security scans (bandit/safety/npm-audit) are **non-blocking** (`|| true`) — control (3) is weaker than it
  should be → R5 makes them blocking.
- Branch protection rules live at the GitHub API level, not in-repo → add exported evidence that required
  reviews + force-push protection are enabled (strengthens controls 1 & 2).
- Production frontend deploy uses **root SSH password** (`deploy-frontend.yml`) → replace with key-based
  non-root deploy user.

## Evidence pointer
`/compliance/evidence/CC8-CHANGE/` (PR + CI history) and `/compliance/evidence/CC7-INCIDENT/` (tamper-evident
log samples). Operating evidence accumulates automatically as PRs merge over the observation window — this is
free Type II evidence.
