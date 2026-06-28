# Access Control Policy
**Document ID:** POL-002
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce
**Review Cadence:** Annual + within 5 business days of any personnel change
**Related Policies:** [POL-001 Information Security](./information-security-policy.md), [POL-003 Password & Authentication](./password-authentication.md)
**TSC Controls:** CC6.1-TENANT, CC6.6-AUTH, CC6.2 (logical access provisioning)

---

## Purpose

Define how access to Meridian production systems is granted, scoped, reviewed, and revoked — and how tenant isolation is enforced at both the application and database layers.

---

## Scope

All systems in scope per POL-001: Railway (API + frontend), Supabase, Cloudflare, GitHub (`AlphaSaleAidan/Meridian`), Contabo VPS, Stripe/Square console access.

---

## Procedure

### 1. Authentication Architecture (Current State)

Meridian's API enforces access through a layered dependency chain in `src/api/auth.py`. The following guards exist and their behaviors are documented here for audit traceability:

| FastAPI Dependency | Location | Behavior |
|---|---|---|
| `require_jwt` | `src/api/auth.py:42-62` | Validates Supabase JWT by calling `/auth/v1/user`; rejects invalid/expired tokens with 401 |
| `require_admin` | `src/api/auth.py` | Compares `X-Admin-Key` header to `MERIDIAN_ADMIN_KEY` env var; returns 503 (fail-closed) if `MERIDIAN_ADMIN_KEY` is unset |
| `require_admin_jwt` | `src/api/auth.py` | Requires valid JWT AND email on hardcoded allowlist (lines 25-31) |
| `require_org_access` | Router-level dependency | Confirms caller's JWT user belongs to the org being accessed |
| `require_service_auth` | Per-handler | Accepts any valid user session for cross-service calls — **see BOLA Gap below** |
| `enforce_service_member` | Per-handler | Checks membership at handler level; must be present on every handler under `require_service_auth` |

**TSC CC6.6-AUTH:** All API endpoints exposed to tenants require at minimum `require_jwt`. Admin-only endpoints additionally require `require_admin` or `require_admin_jwt`. Unauthenticated endpoints are limited to health checks (`/health`).

### 2. Tenant Isolation (CC6.1-TENANT)

Tenant isolation is a named objective. Meridian is a multi-tenant SaaS; a user from Org A must never read or write Org B's data.

Two enforcement layers exist:

**Layer 1 — Database (Supabase RLS):** Row Level Security policies are enabled on all tables containing tenant-scoped data. RLS was audited and gaps in `authenticated` role GRANTs were discovered and remediated (Tier 1 + Tier 2 tables fixed 2026-06-07; Tier 3 status must be verified before next production change).

**Layer 2 — API (require_org_access):** The `require_org_access` dependency is applied at the router level for all org-scoped resource routes. Any new router that exposes org-scoped data MUST include this dependency. Code reviewers are expected to verify this during PR review (see [POL-005 Secure SDLC](./secure-sdlc.md)).

### 3. Known Gap: BOLA Risk on require_service_auth

`require_service_auth` accepts any valid user session for cross-service calls. Without `enforce_service_member` on every handler beneath it, a valid session from Org A could access Org B's resources. This is documented in `docs/MERIDIAN_COMPLIANCE_POSTURE.md` as a P0 risk.

**Remediation target:** All handlers under `require_service_auth` must be audited for the presence of `enforce_service_member`. This audit must be completed before the next Type II examination period opens. Track in `compliance/evidence/POL-002/bola-remediation.md`.

### 4. Known Gap: Hardcoded Admin Email Allowlist

Admin emails are hardcoded at `src/api/auth.py:25-31`. This creates friction when the admin team changes and requires a code deploy to add or remove an admin.

## DECISION (Aidan)

**Choice:** Migrate admin email allowlist from hardcode to a database-backed role table.

**Recommended default:** Create a `platform_admins` table in Supabase with `email` (unique), `role` (enum: `super_admin`, `ca_admin`), `granted_by`, `granted_at`, `revoked_at`. `require_admin_jwt` queries this table at request time (with a short TTL cache). Revocation takes effect at next request without a deploy.

**Tradeoff:** Current hardcode is simple and has zero DB latency. The DB-backed approach adds a query per admin request (mitigated by 60s TTL cache) but enables clean audit trail and immediate revocation — required for SOC 2 CC6.2 (access reviews must be executable without a code change).

**Action required:** Aidan to approve or document a counter-decision in `compliance/evidence/POL-002/decisions.md` before the examination period.

### 5. Provisioning and Deprovisioning

**Provisioning:** Access to production systems (Railway, Supabase dashboard, GitHub, Cloudflare, Stripe, Square) is granted only by Aidan Pierce. Access is scoped to the minimum required for the role. New personnel must not receive production database credentials; they receive JWT-scoped access to the API only, bounded by RLS.

**Deprovisioning:** On personnel departure or role change, Aidan Pierce must revoke access within 24 hours across: Supabase dashboard, Railway team membership, GitHub organization, Cloudflare team membership, any shared credentials in 1Password. Deprovisioning is logged in `compliance/evidence/POL-002/access-log.md`.

**Current personnel and access:**

| Individual | Systems | Access Level |
|---|---|---|
| Aidan Pierce | All | Full admin |
| Aidan Nguyen | Canada portal, Supabase (org-scoped data), GitHub (contributor) | Scoped contributor |
| Enoch Cheung | Canada portal, Supabase (org-scoped data), GitHub (contributor) | Scoped contributor |

### 6. Quarterly Access Review

## DECISION (Aidan)

**Choice:** Implement a formal quarterly access review ritual.

**Recommended default:** On the first Monday of each quarter, Aidan Pierce reviews the access log and confirms each person's access remains appropriate. Review is documented in `compliance/evidence/POL-002/quarterly-review-<YYYY-QN>.md` with a checklist: (a) confirm active personnel list, (b) confirm no orphaned Supabase service keys, (c) confirm no orphaned Railway tokens, (d) confirm no departed personnel retain GitHub org membership, (e) confirm Contabo SSH authorized_keys matches expected set.

**Tradeoff:** This is manual overhead for a small team. The alternative (automated access review via a script) is recommended for Q3 2026 when team size justifies it.

**Action required:** Aidan to confirm cadence (quarterly vs. semi-annual) and complete the first review, producing `compliance/evidence/POL-002/quarterly-review-2026-Q3.md`.

### 7. Service Accounts and API Keys

Service-to-service credentials (Railway env vars: `ENCRYPTION_KEY`, `MERIDIAN_ADMIN_KEY`, `OAUTH_STATE_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`, Telnyx/Square/Stripe keys) are:
- Stored as Railway encrypted environment variables for API production.
- Stored in `/root/.secrets/*.env` on Contabo for async workers (chmod 700, gitignored).
- Documented as a gap: Contabo file-based secrets are not governed by a secrets manager with audit logs. See [POL-004 Encryption](./encryption-cryptography.md) for the key handling policy and remediation path.

No service account credentials are committed to `AlphaSaleAidan/Meridian` (enforced by gitleaks; see [POL-005 Secure SDLC](./secure-sdlc.md)).

---

## Roles & Responsibilities

| Role | Responsibility |
|---|---|
| Aidan Pierce | Sole provisioner of production access; owns quarterly review; approves all exceptions |
| CA Admins | Operate within granted scope; report unauthorized access immediately |
| Any engineer on a PR | Verify that new routes include `require_org_access` for org-scoped data |

---

## Evidence that this Policy Operates

1. **`compliance/evidence/POL-002/access-log.md`** — dated log of all access grants and revocations, with approver.
2. **`compliance/evidence/POL-002/quarterly-review-<YYYY-QN>.md`** — completed quarterly access reviews.
3. **`compliance/evidence/POL-002/bola-remediation.md`** — progress tracker for `require_service_auth` handler audit.
4. **Supabase dashboard → Authentication → Users** — current active user list; auditors may request a screenshot dated within the examination window.
5. **Railway team → Members** — current team membership; auditors may request a dated export.
6. **GitHub → `AlphaSaleAidan/Meridian` → Settings → Collaborators** — auditors may request a dated screenshot.
7. **`src/api/auth.py` git history** — shows when admin email list last changed and who authored the commit.
