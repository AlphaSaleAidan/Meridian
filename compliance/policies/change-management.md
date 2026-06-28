# Change Management Policy
**Document ID:** POL-006
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce
**Review Cadence:** Annual, or on any change to CI/CD infrastructure
**Related Policies:** [POL-001 Information Security](./information-security-policy.md), [POL-005 Secure SDLC](./secure-sdlc.md)
**TSC Controls:** CC8.1 (change management), CC6.8 (change authorization), CC7.2 (monitoring for change)

---

## Purpose

Codify the actual change control workflow that governs every modification to Meridian production systems — from feature development through automated deployment to database migrations and emergency rollback. Identify gaps in the current workflow and define remediation targets.

---

## Scope

All changes to code running in production (`api.meridian.tips`, Railway-hosted frontend, Contabo VPS workers), all Supabase database migrations, all Railway environment variable changes, and all changes to CI/CD pipeline configuration.

---

## Procedure

### 1. Normal Change Workflow

The following is the authoritative change pipeline for all non-emergency changes:

```
Developer creates feature branch
        ↓
Local development + pre-commit hooks (gitleaks blocking)
        ↓
Pull Request opened against main
        ↓
CI Pipeline (ruff, py_compile, tsc --noEmit, gitleaks — all blocking)
        ↓
Human review (≥ 1 approver; Aidan Pierce for security-sensitive paths)
        ↓
Aidan Pierce merges PR to main
        ↓
Railway auto-deploys backend API on merge to main
        ↓
Frontend: manual build + deploy to Contabo (see §5)
```

**Key principles:**
- No direct push to `main`. All changes enter via PR.
- The live Canada deploy branch (`session-2-canada-prep`) must not be pushed to directly. PRs only. Aidan merges.
- CI must pass before any merge. Human approval must precede any merge.
- Railway backend deployment is automatic and immediate on merge to `main`. There is no separate "promote to production" step for the backend API.

### 2. Development/Production Separation

| Environment | Backend | Frontend | Database |
|---|---|---|---|
| **Development** | Local `uvicorn` process | Local `npm run dev` (Vite) | Developer's own Supabase project or local emulator |
| **Production** | Railway (auto-deploy from `main`) | Railway (frontend) + Contabo VPS static dist/ (Canada portal) | Supabase project `kbuzufjxwflrutowwnfl` (AWS us-east-1) |

There is currently no staging environment between development and production. All code that passes CI and human review goes directly to production on merge.

## DECISION (Aidan)

**Gap:** The absence of a staging environment means that integration bugs not caught by CI or code review reach production users immediately.

**Recommended default:** Use Railway's preview environments (Railway creates an isolated environment per PR branch, with its own URL) as a lightweight staging layer. Require that any PR touching: (a) authentication logic, (b) database migrations, (c) POS/payment flows, or (d) new API routes be verified against the Railway preview environment before merge. The verifying engineer records their findings in the PR description.

**Tradeoff:** Railway preview environments use production Supabase by default unless a separate test project is configured. Mixing preview traffic with the production database is a risk. Short-term: accept this risk for read-only verifications. Medium-term: provision a Supabase test project for preview environments.

**Action required:** Aidan to document the staging decision in `compliance/evidence/POL-006/decisions.md`.

### 3. Branch Protection (Gap — Remediation Required)

Branch protection rules on `main` are not confirmed in-repository. This means:

- Currently, CI pass and human review are enforced by convention, not by GitHub's branch protection enforcement.
- A contributor with push access could theoretically bypass the PR flow.

**Required controls (to be implemented):**
- GitHub branch protection on `main`: require PR, require CI checks to pass, require at least 1 approving review, dismiss stale reviews on new push.
- `CODEOWNERS` file designating Aidan Pierce as required reviewer for security-sensitive paths (listed in [POL-005 §8](./secure-sdlc.md)).

Track completion in `compliance/evidence/POL-006/branch-protection.md`.

### 4. Database Migration Discipline

Supabase database migrations are **applied manually and deliberately to production**. This is intentional — schema changes are not automatically applied on code deploy.

**Standard migration procedure:**

1. Migration file authored in `migrations/` directory with sequential naming (e.g., `028_add_feature.sql`).
2. Migration reviewed in PR alongside the code change that depends on it.
3. After PR is merged and API is deployed, Aidan Pierce applies the migration to Supabase production via the Supabase dashboard or `psql` connection.
4. Migration application is logged in `compliance/evidence/POL-006/migration-log.md` with: migration filename, date applied, who applied it, and a confirmation query showing the schema change is live.
5. The API is verified post-migration by testing the affected endpoint or running the relevant `pytest` suite against production.

**Why manual:** Automatic migrations tied to deploy carry the risk of a failed migration leaving the schema in an inconsistent state while the new API code is already running. Manual application with a deliberate apply step allows the operator to verify the migration succeeded before the new code is live (or to roll back the deploy if the migration fails).

**Never apply migrations without a corresponding merged PR.** Ad-hoc schema changes to production must be treated as emergency changes (see §6).

### 5. Frontend Deployment (Contabo Canada Portal)

The Canada portal static frontend (React/Vite) is deployed manually to the Contabo VPS. It is **not** automatically deployed on merge to `main`. The deploy procedure is:

1. Build locally or via CI: `npm run build` from `frontend/`.
2. The build requires `frontend/.env.local` (gitignored) with the correct Supabase URL and keys. Without this file, the build will silently ship a demo-mode build with broken auth.
3. Transfer `dist/` to Contabo VPS via the deploy script (currently using SSH — see [POL-003 §8 DECISION](./password-authentication.md) for the root-password-SSH gap and recommended remediation).
4. Nginx serves the new `dist/` immediately (no process restart required).
5. Post-deploy verification: confirm Supabase URL in the deployed `dist/index.html` matches production, test login flow in a browser (service worker caches may require hard-refresh).

**Gap:** The `deploy-frontend.yml` GitHub Actions workflow uses the Contabo root SSH password stored in GitHub Actions secrets. This is documented as a remediation item in [POL-003 §8](./password-authentication.md).

### 6. Emergency Change Procedure

An emergency change is any change that bypasses the standard PR + CI + review flow due to an active P0 or P1 incident (customer data exposure, complete service outage, active security breach).

**Emergency change rules:**

1. Aidan Pierce must be notified and must authorize the emergency change verbally or in writing before it is applied.
2. The minimum viable change is applied (not a batch of unrelated fixes).
3. If a code change is required, it is pushed to a hotfix branch and deployed via Railway (even without full CI passing, if CI is broken) — but gitleaks must still pass.
4. The change is documented within 24 hours in `compliance/evidence/POL-006/emergency-changes.md` with: date/time, nature of incident, change applied, who applied it, authorization record.
5. A follow-up PR is opened within 48 hours to formalize the change through the standard review process (or to revert it if the emergency change was temporary).

**Emergency environment variable changes** (e.g., rotating a compromised key) do not require a code deploy but must be logged in `compliance/evidence/POL-006/emergency-changes.md` within 24 hours.

### 7. Rollback Procedure

**Backend API rollback:** Railway supports instant rollback to any previous successful deployment. In Railway dashboard: Deployments → select previous successful deployment → Redeploy. Document the rollback in `compliance/evidence/POL-006/incident-log.md`.

**Database rollback:** Tar + sha256 backups are taken before significant schema changes. Current evidence: `backups/auth.py.20260617-052614.tar.gz` and its corresponding `.sha256` file. Procedure:
1. Before any migration that drops columns or tables, export the affected table: `pg_dump -t <tablename> > backups/<tablename>-<timestamp>.sql`.
2. Compute sha256: `sha256sum backups/<tablename>-<timestamp>.sql > backups/<tablename>-<timestamp>.sql.sha256`.
3. If migration must be reversed, restore from the dump file.
4. Log the rollback in `compliance/evidence/POL-006/migration-log.md`.

**Supabase automated backups:** Supabase Pro plan provides daily automated backups with point-in-time recovery (PITR). Confirm the current Supabase plan includes PITR in `compliance/evidence/POL-006/supabase-backup-config.md`.

### 8. Railway Environment Variable Changes

Changes to Railway production environment variables (secrets, feature flags, service URLs) are considered production changes and must be:

1. Authorized by Aidan Pierce.
2. Logged in `compliance/evidence/POL-006/env-var-change-log.md` with: variable name (not value), date, reason, who made the change.
3. Followed by an API health check (`/health` endpoint) confirming the service restarted successfully with the new configuration.

Never log the value of a secret in the change log — only the variable name and the reason for change.

### 9. Gap Summary and Remediation Tracker

| Gap | Risk | Remediation | Owner | Target |
|---|---|---|---|---|
| No GitHub branch protection rules on `main` | High — convention not enforced | Configure GitHub branch protection + CODEOWNERS | Aidan | Before examination period |
| Frontend deploy uses root SSH password | Medium — broad blast radius if secret exposed | Replace with restricted deploy SSH key ([POL-003 §8](./password-authentication.md)) | Aidan | Q3 2026 |
| No staging environment | Medium — integration bugs reach prod | Railway preview environments as staging gate ([§2 DECISION](#)) | Aidan | Q3 2026 |
| `bandit`/`safety`/`npm audit` non-blocking | Medium — known CVEs can merge | Promote to blocking at HIGH/CRITICAL ([POL-005 §3](./secure-sdlc.md)) | Aidan | Q3 2026 |
| Playwright e2e not wired to CI | Low-Medium — UI regressions undetected | Wire Playwright to CI on Railway preview URL ([POL-005 §7](./secure-sdlc.md)) | Aidan | Q4 2026 |

---

## Roles & Responsibilities

| Role | Responsibility |
|---|---|
| Aidan Pierce | Sole merge authority on `main`; authorize all environment variable changes; execute and log database migrations; authorize and document emergency changes; own rollback decisions |
| CA Admins / Contributors | Open PRs; never push directly to `main` or `session-2-canada-prep`; notify Aidan of any incident requiring emergency change |
| Any engineer | Verify CI passes before requesting review; include migration files in the same PR as dependent code |

---

## Evidence that this Policy Operates

1. **GitHub PR history for `main`** — all merged PRs during the examination period; confirms each had CI pass + at least one approving review before merge. Generate with: `gh pr list --state merged --base main --json number,title,mergedAt,author,reviews --limit 200`.
2. **Railway deployment history** — confirms each production deployment corresponds to a merged PR, not a direct push. Auditors may request a dated Railway console export.
3. **`compliance/evidence/POL-006/migration-log.md`** — dated log of every Supabase migration applied to production, with who applied it and a confirmation query result.
4. **`compliance/evidence/POL-006/emergency-changes.md`** — log of any emergency changes during the examination period (empty = no emergency changes required, which is also valid evidence).
5. **`compliance/evidence/POL-006/env-var-change-log.md`** — log of Railway environment variable changes.
6. **`backups/` directory in repo** — tar + sha256 files confirm backup artifacts exist (e.g., `backups/auth.py.20260617-052614.tar.gz` and `.sha256`).
7. **`compliance/evidence/POL-006/branch-protection.md`** — screenshot of GitHub branch protection rules once implemented.
8. **`compliance/evidence/POL-006/supabase-backup-config.md`** — confirms Supabase plan includes automated backups and PITR.
