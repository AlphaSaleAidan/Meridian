# Evidence — CC8-CHANGE — change management (strongest area)

**v0.1 — 2026-06-28.** Policy: `/policies/change-management.md`. Control: `CC5-SOD-COMPENSATING`.

## Type I evidence (real, mostly free Type II too)
| Control | Location | Evidence type |
|---|---|---|
| Feature branch → PR → human-gated merge | GitHub PR history | Type II (accumulates) |
| CI blocking gates | `.github/workflows/ci.yml` (ruff), `syntax-check.yml` (`py_compile`, `tsc --noEmit`), `gitleaks.yml` | Type II run records |
| Secret scan (pre-commit + CI) | `.pre-commit-config.yaml`, `gitleaks.yml`, `.gitleaks.toml` | blocking |
| Rollback ritual (tar + sha256) | `backups/auth.py.20260617-052614.tar.gz` + `.sha256` | real artifact |
| Deliberate manual prod migrations | `docs/ARCHITECTURE.md:88-89` | procedure |

## Gaps (remediation tracked)
- Branch protection rules live at GitHub API level, **not in-repo** → export evidence that required reviews +
  force-push protection are on (strengthens immutable-history + mandatory-review compensating controls).
- Security scans (bandit/safety/npm-audit) **non-blocking** (`|| true`, `security.yml`) → R5 make blocking.
- Prod frontend deploy uses **root SSH password** (`deploy-frontend.yml`) → key-based non-root deploy user (R-12).
- Playwright e2e exists but not wired to CI.

## Type II (collect over window)
Merged-PR log with reviewer + CI status per change; this is the cleanest auto-collected change-mgmt evidence
Meridian has. Export monthly.

## Status 🟢 strongest area; gaps are hardening, not foundational.
