# Evidence — CC6.6-AUTH — authentication, admin access, secrets

**v0.1 — 2026-06-28.** Policies: `/policies/access-control.md`, `/policies/password-authentication.md`.

## Type I evidence (real)
| Control | Location | Notes |
|---|---|---|
| Supabase JWT auth | `src/api/auth.py:42-62` | server-side token verification |
| Admin gate (fail-closed) | `src/api/auth.py` `require_admin` | 503 if `MERIDIAN_ADMIN_KEY` unset |
| No client admin key | `frontend/.../GarryWidget.tsx:73-75` | "never embed a static admin key"; frontend forwards JWT |
| Rate limiting | `src/api/middleware/rate_limiter.py` | admin 10/hr, connect 10/hr, signup 5/hr |
| Security headers | `src/api/middleware/security_headers.py` | nosniff, DENY, HSTS, Permissions-Policy |
| Secret scanning | `gitleaks.yml`, `.gitleaks.toml`, `.pre-commit-config.yaml` | no committed secrets verified |

## Gaps
- **Hardcoded `ADMIN_EMAILS`** (`auth.py:25-31`) — no audit trail / deploy-to-change → move to DB roles (R-10).
- **No MFA enforcement** anywhere in code → `CC6.6-MFA`, R6 (org control on subservice consoles).
- `require_service_auth` accepts any merchant session (C1 BOLA) → see `CC6.1-TENANT`.
- Security-critical env vars (`ENCRYPTION_KEY`, `OAUTH_STATE_SECRET`, `MERIDIAN_SERVICE_TOKEN`,
  `VAPI_SERVER_SECRET`, `TENANCY_ENFORCEMENT_DISABLED`) undocumented → secrets inventory.
- Legacy `src/auth/manager.py:24` weak default secret (dead code) → remove.

## Status 🟡 strong auth foundation; MFA + admin-allowlist + secrets-inventory are the gaps.
