# Password & Authentication Policy
**Document ID:** POL-003
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce
**Review Cadence:** Annual, or on any change to the authentication stack
**Related Policies:** [POL-001 Information Security](./information-security-policy.md), [POL-002 Access Control](./access-control.md), [POL-004 Encryption](./encryption-cryptography.md)
**TSC Controls:** CC6.6-AUTH, CC6.1 (logical access), CC6.7 (transmission)

---

## Purpose

Establish Meridian's requirements for credential security, session token handling, multi-factor authentication on privileged consoles, and service-key rotation.

---

## Scope

All human and service authentication to Meridian systems: tenant user accounts, admin console access (Supabase dashboard, Railway, GitHub, Cloudflare, Stripe, Square), and API service keys.

---

## Procedure

### 1. Tenant User Authentication (Supabase Auth)

Meridian delegates all tenant password management to **Supabase Auth**. This means:

- **Password hashing:** Supabase Auth uses bcrypt with a work factor of 10 (Supabase managed default). Meridian never stores or handles raw passwords.
- **Password storage:** All password hashes reside exclusively in Supabase's managed Postgres (`auth.users` table, project `kbuzufjxwflrutowwnfl`, AWS us-east-1).
- **Password reset:** Handled via Supabase Auth email flows using the Supabase Auth SMTP configuration (separate from Meridian's transactional email Resend path — see `compliance/evidence/POL-003/supabase-smtp-config.md`).
- **Minimum password requirements:** Enforced by Supabase Auth project settings. Current configuration must be verified and documented in `compliance/evidence/POL-003/supabase-auth-settings.md`. Recommended minimum: 12 characters, no dictionary-word-only passwords.

### 2. Session Tokens (JWT)

Supabase Auth issues JWTs to authenticated sessions. Meridian's API validates these server-side in `src/api/auth.py:42-62` by calling Supabase `/auth/v1/user` on each request. This means:

- JWT validation is live (not purely signature-based), so revoked sessions cannot outlive their Supabase Auth invalidation.
- **JWT expiry:** Controlled by Supabase Auth project settings. Must be documented in `compliance/evidence/POL-003/supabase-auth-settings.md`. Recommended: access token 1 hour, refresh token 7 days.
- JWTs are transmitted only over TLS (HSTS enforced, see [POL-004 Encryption](./encryption-cryptography.md)). They are never logged or stored in plaintext by Meridian application code.

### 3. Admin API Key (`MERIDIAN_ADMIN_KEY`)

The `MERIDIAN_ADMIN_KEY` environment variable is the credential for admin-only FastAPI endpoints (`require_admin` dependency, `src/api/auth.py`):

- Must be a cryptographically random string, minimum 32 characters.
- Stored as a Railway encrypted environment variable in production.
- Fail-closed: `require_admin` returns HTTP 503 if `MERIDIAN_ADMIN_KEY` is unset. This prevents accidental exposure of admin routes if the key is inadvertently removed from Railway.
- Must be rotated: (a) on any suspected exposure, (b) on any personnel departure, (c) at least annually.
- Rotation procedure: generate new value (`openssl rand -hex 32`), set in Railway environment, redeploy API, confirm `/health` and one admin endpoint respond correctly, update `compliance/evidence/POL-003/key-rotation-log.md`.

### 4. Multi-Factor Authentication on Privileged Consoles

## DECISION (Aidan)

**Requirement stated in this policy:** MFA is REQUIRED for all human access to the following consoles: Supabase dashboard, Railway, GitHub (`AlphaSaleAidan`), Cloudflare, Stripe, Square. No exceptions.

**Current state:** MFA enablement has not been technically verified or documented. There is no automated enforcement evidence on file.

**Recommended default:** Enable TOTP MFA on all five consoles using an authenticator app (e.g., 1Password TOTP, Authy). GitHub also offers hardware key (FIDO2); preferred for Aidan's account given signing authority.

**Tradeoff:** A team of three with no MFA is a significant control gap. A single compromised password on any of these consoles would allow production data access, secret extraction, or service disruption. The implementation effort is low (< 30 minutes across all consoles). The cost of not doing it is potentially audit-blocking.

**Action required:** Aidan to enable MFA on all five consoles, then produce `compliance/evidence/POL-003/mfa-enrollment.md` with screenshots (or API evidence) of MFA enrollment for each admin account on each console. This evidence must exist before any SOC 2 readiness interview.

### 5. OAuth State Secret (`OAUTH_STATE_SECRET`)

POS provider OAuth flows use `OAUTH_STATE_SECRET` to sign state parameters, preventing CSRF during the OAuth handshake:

- Stored as a Railway environment variable (encrypted at rest).
- Must be a minimum 32-byte random value (`openssl rand -hex 32`).
- Rotation triggers and procedure: same as `MERIDIAN_ADMIN_KEY` (§3 above).
- An unset `OAUTH_STATE_SECRET` causes the OAuth endpoints to return 403. This is fail-closed behavior.

### 6. Supabase Service Role Key

`SUPABASE_SERVICE_ROLE_KEY` bypasses RLS and must be treated as a root credential:

- Used only in backend API worker processes and the Garry self-healing agent on Contabo.
- Must never appear in frontend code, browser-accessible assets, or logs.
- Access is restricted to Railway environment and `/root/.secrets/supabase.env` on Contabo (chmod 700).
- Rotation triggers: suspected exposure, Supabase key rotation feature, or annual cycle. After rotation, all Railway services and Contabo workers referencing the key must be updated and restarted.

### 7. Third-Party Integration Keys (Telnyx, Square, Stripe, Resend)

All third-party API keys follow the same handling rules:

- Stored in Railway env vars (production) and `/root/.secrets/*.env` (Contabo workers).
- Never committed to `AlphaSaleAidan/Meridian` (gitleaks blocking).
- Rotated immediately on any paste into a channel, doc, or log file (see `MEMORY.md` notes on past exposure events).
- Rotation is logged in `compliance/evidence/POL-003/key-rotation-log.md`.

### 8. SSH Access to Contabo VPS

- Access via SSH key authentication only. Password authentication must be disabled in `/etc/ssh/sshd_config` (`PasswordAuthentication no`).
- Root SSH key is held by Aidan Pierce only.
- `~/.ssh/authorized_keys` on the Contabo VPS must match the expected set (auditable via `compliance/evidence/POL-002/quarterly-review-<YYYY-QN>.md`).

## DECISION (Aidan)

**Choice:** The `deploy-frontend.yml` workflow currently uses the root SSH password to push the static frontend build to Contabo. This is a control weakness: the root password is stored in GitHub Actions secrets, which widens its exposure surface.

**Recommended default:** Replace root-password SSH with a dedicated deploy SSH key pair: generate a key with no passphrase, add the public key to Contabo `authorized_keys` with a `command=` restriction limiting it to rsync/scp of the dist directory only, store the private key in GitHub Actions secret `DEPLOY_SSH_KEY`. Remove `DEPLOY_SSH_PASSWORD` secret.

**Tradeoff:** Minimizes blast radius if the GitHub Actions secret is exposed — an attacker would get rsync of one directory, not full root shell.

**Action required:** Aidan to approve this change and track implementation in `compliance/evidence/POL-003/decisions.md`.

---

## Roles & Responsibilities

| Role | Responsibility |
|---|---|
| Aidan Pierce | Enable and maintain MFA on all admin consoles; rotate `MERIDIAN_ADMIN_KEY`, `OAUTH_STATE_SECRET`, Supabase service role key per schedule; maintain key rotation log |
| CA Admins | Enable MFA on their GitHub and Supabase accounts before receiving production access |
| Any engineer | Never log, commit, or transmit credentials in plaintext; report suspected credential exposure immediately |

---

## Evidence that this Policy Operates

1. **`compliance/evidence/POL-003/mfa-enrollment.md`** — screenshots or API responses confirming MFA enrollment for each admin on Supabase, Railway, GitHub, Cloudflare, and Stripe dashboards.
2. **`compliance/evidence/POL-003/supabase-auth-settings.md`** — export of Supabase Auth project settings showing JWT expiry, minimum password requirements, and bcrypt work factor.
3. **`compliance/evidence/POL-003/key-rotation-log.md`** — timestamped log of all `MERIDIAN_ADMIN_KEY`, `OAUTH_STATE_SECRET`, and third-party key rotations, with reason and who performed the rotation.
4. **Railway environment variable list** — demonstrates keys are set (values masked); auditors may request a dated Railway console screenshot.
5. **`git log --all -- src/api/auth.py`** — confirms fail-closed behavior for `require_admin` has not been removed or bypassed in any merged commit.
6. **`compliance/evidence/POL-003/decisions.md`** — Aidan's recorded decisions on MFA and deploy-key items above.
