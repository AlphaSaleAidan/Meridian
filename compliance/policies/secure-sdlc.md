# Secure Software Development Lifecycle (SDLC) Policy
**Document ID:** POL-005
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce
**Review Cadence:** Annual, or on any change to CI/CD tooling or testing stack
**Related Policies:** [POL-001 Information Security](./information-security-policy.md), [POL-006 Change Management](./change-management.md)
**TSC Controls:** CC8.1 (change management), CC7.1 (detection and monitoring), CC6.8 (change authorization)

---

## Purpose

Codify how security is built into Meridian's development process — from the first commit to production deployment — so that security controls are not an afterthought but a gate on every change.

---

## Scope

All code merged to `AlphaSaleAidan/Meridian` `main` branch and deployed to `api.meridian.tips`, the React frontend on Railway, and the Canada portal static build on Contabo VPS.

---

## Procedure

### 1. Development Environment Setup

All engineers must configure their local environment with the pre-commit hooks defined in `.pre-commit-config.yaml` before writing or pushing any code:

```bash
pip install pre-commit
pre-commit install
```

The pre-commit suite runs **before every local commit** and includes:
- **gitleaks** — secret scanning against `.gitleaks.toml` patterns. **Blocking.** A commit containing a detected secret is rejected locally before it ever reaches GitHub.

Any engineer who disables or bypasses pre-commit hooks must disclose this to Aidan Pierce immediately.

### 2. Branch Policy

- All work occurs on feature branches. No direct commits to `main`.
- Branch naming convention: `feat/<description>`, `fix/<description>`, `audit/<description>`, `conductor/<description>`.
- The live Canada deploy branch `session-2-canada-prep` must never be pushed to directly — only via PR.
- See [POL-006 Change Management](./change-management.md) for the full branch and merge protocol.

### 3. CI Pipeline Security Gates

Every PR to `main` triggers the GitHub Actions CI pipeline. The following checks are defined and their blocking status is documented here for audit traceability:

| Check | Workflow File | Tool | Blocking? | Notes |
|---|---|---|---|---|
| Secret scanning | `.github/workflows/gitleaks.yml` | gitleaks + `.gitleaks.toml` | **YES** | PR cannot merge if secrets detected |
| Python lint | CI workflow | ruff | **YES** | PR cannot merge on lint failure |
| Python syntax | CI workflow | `python -m py_compile` | **YES** | Catches import/syntax errors |
| TypeScript type-check | CI workflow | `tsc --noEmit` | **YES** | Catches TS type errors in frontend |
| Python security scan | CI workflow | bandit | **NO** (`\|\| true`) | Results surfaced but do not block merge |
| Python dependency audit | CI workflow | safety | **NO** (`\|\| true`) | CVE check; results surfaced but do not block |
| JS dependency audit | CI workflow | npm audit | **NO** (`\|\| true`) | CVE check; results surfaced but do not block |

## DECISION (Aidan)

**Gap:** `bandit`, `safety`, and `npm audit` are non-blocking (`|| true`). A PR introducing a known CVE or a high-severity security issue (e.g., SQL injection, use of `subprocess.shell=True`) can currently merge without any human review of these findings.

**Recommended default:** Promote `bandit` to blocking at `HIGH` severity level (`bandit -ll` flag), and `safety` to blocking for CVEs with a CVSS score ≥ 7.0. For `npm audit`, block on `critical` severity. Accept a 30-day grace period for any CVE where no patched version exists, documented as a tracked exception in `compliance/evidence/POL-005/vuln-exceptions.md`.

**Tradeoff:** Will require triage of existing findings before enabling. Recommend a one-time baseline run (`bandit -r src/ -ll`, `safety check`, `npm audit`) to enumerate current findings and either patch or document-as-accepted before flipping the flag.

**Action required:** Aidan to approve promotion of security scans to blocking, or document a counter-decision, in `compliance/evidence/POL-005/decisions.md`.

### 4. Code Review Requirements

Every PR must receive at least one human review and approval before merge. Self-merge (author merging their own PR without a second reviewer) is permitted only for:
- Hotfixes to a P0 production incident (must be documented in `compliance/evidence/POL-006/emergency-changes.md`).
- Documentation-only changes with no code impact.

Code reviewers must verify, at minimum:
- All new API routes handling tenant data include `require_org_access` (see [POL-002 Access Control §2](./access-control.md)).
- No new route relies solely on `require_service_auth` without `enforce_service_member` on every handler.
- No hardcoded secrets, URLs, or credentials.
- Cryptographic choices comply with [POL-004 Encryption](./encryption-cryptography.md).
- Any new Supabase migration follows the manual migration discipline in [POL-006 §4](./change-management.md).

### 5. Dependency Management

**Python dependencies (`requirements.txt` or `pyproject.toml`):**
- Pin major versions for security-sensitive libraries (`cryptography`, `fastapi`, `supabase`).
- `safety check` runs on every CI build (currently non-blocking; see §3 DECISION above).
- Dependency updates are treated as code changes: PR required, CI must pass, human review must approve.

**JavaScript dependencies (`package.json`):**
- `npm audit` runs on every CI build (currently non-blocking; see §3 DECISION above).
- No `npm install` with `--ignore-scripts` disabled for packages with known malicious install scripts.

**Upgrade policy:** Any dependency with a published CVE rated ≥ HIGH (CVSS ≥ 7.0) must be patched or a documented exception filed within 14 days of Meridian becoming aware of the CVE (via `safety` output, `npm audit` output, or GitHub Dependabot alert).

### 6. Secret Scanning

Three layers of secret scanning protect the `AlphaSaleAidan/Meridian` repository:

1. **Pre-commit (local):** gitleaks runs before each commit on the developer's machine (`.pre-commit-config.yaml`).
2. **CI (PR gate):** gitleaks runs on every PR in `.github/workflows/gitleaks.yml`. **Blocking.** A PR containing detected secrets cannot pass CI.
3. **Custom rules:** `.gitleaks.toml` contains Meridian-specific patterns (Railway tokens, Supabase keys, Telnyx keys, Stripe keys). These patterns must be reviewed and updated when new secret types are added to the Meridian stack.

Secrets that escape these controls (e.g., pasted into a Slack message or docs file) must be rotated immediately per [POL-003 §7](./password-authentication.md).

### 7. Testing Requirements

- **Python:** `pytest tests/` must pass locally before a PR is opened. The CI pipeline runs `pytest` (verify this is wired — check `.github/workflows/*.yml` for pytest invocation).
- **Frontend end-to-end:** Playwright e2e tests exist in the frontend directory. These are **not currently wired to CI**. This is a documented gap.

## DECISION (Aidan)

**Gap:** Playwright e2e tests are not wired to CI. Frontend deployments can succeed even if core user flows (login, order submission, menu display) are broken.

**Recommended default:** Add a `playwright test` step to CI targeting the Railway preview URL. Gate the merge on at least the smoke test suite (login, navigate to a location, view menu) passing. This requires the CI pipeline to receive the Railway preview URL as an environment variable (Railway provides this on PR environments).

**Action required:** Aidan to approve wiring Playwright to CI in `compliance/evidence/POL-005/decisions.md` and assign to the next sprint.

### 8. Security-Sensitive Code Areas

The following files and directories are designated security-sensitive. Any PR touching them requires Aidan Pierce as an explicit reviewer:

- `src/api/auth.py` — authentication logic
- `src/security/encryption.py` — AES-256-GCM token encryption
- `src/api/middleware/security_headers.py` — HSTS and security headers
- `.github/workflows/gitleaks.yml` — secret scanning CI
- `.pre-commit-config.yaml` — pre-commit hook configuration
- `.gitleaks.toml` — secret patterns
- Any new Supabase migration file (`migrations/`)

## DECISION (Aidan)

**Recommended default:** Implement GitHub branch protection rules on `main` requiring: (a) at least 1 approving review, (b) CI checks must pass, (c) `CODEOWNERS` file designating Aidan Pierce as required reviewer for the security-sensitive paths above. This enforces the review requirement at the GitHub layer rather than relying on convention.

**Current state:** Branch protection rules are not confirmed to be in-repo (not verified in `.github/` configuration). This is a gap that must be closed before Type II examination.

**Action required:** Aidan to configure branch protection on `main` and add a `CODEOWNERS` file; document in `compliance/evidence/POL-005/branch-protection.md`.

---

## Roles & Responsibilities

| Role | Responsibility |
|---|---|
| Aidan Pierce | Own CI pipeline configuration; approve changes to security gates; review all security-sensitive PRs; approve exceptions to testing requirements |
| CA Admins / Contributors | Install pre-commit hooks before first commit; run tests locally before opening PRs; flag security concerns in PR description |
| Any code reviewer | Verify access control dependencies on new routes; flag cryptographic choices; ensure no secrets in diff |

---

## Evidence that this Policy Operates

1. **`.github/workflows/gitleaks.yml`** — confirms gitleaks runs on PRs and blocks on detection.
2. **`.pre-commit-config.yaml`** — confirms pre-commit hook configuration.
3. **`.gitleaks.toml`** — confirms Meridian-specific secret patterns.
4. **GitHub Actions run history for `main`** — shows CI results for every merged PR, including which checks passed/failed. Auditors may request an export for the examination period.
5. **`compliance/evidence/POL-005/pr-review-log.md`** — list of all PRs merged during the examination period with reviewer names and CI pass/fail status (can be generated from GitHub API: `gh pr list --state merged --json number,title,mergedAt,reviews`).
6. **`compliance/evidence/POL-005/branch-protection.md`** — screenshot of GitHub branch protection rules on `main`.
7. **`compliance/evidence/POL-005/vuln-exceptions.md`** — log of any CVEs accepted as exceptions with justification and expiry date.
8. **`compliance/evidence/POL-005/decisions.md`** — Aidan's recorded decisions on blocking security scans and Playwright CI wiring.
