# Meridian — Controls Register

> One row per control: stable ID → objective → implementation (with file:line) → owner → evidence pointer →
> status. The auditor/automation platform traces **criterion → control → evidence** in one hop:
> evidence lives in `/compliance/evidence/<ID>/`. v0.1 — 2026-06-28. Owner: Aidan Pierce unless noted.
>
> Status: 🟢 designed+evidenced · 🟡 partial · 🔴 critical gap · 🚩 org/human control.

## CC6 — Logical & Physical Access (the heavy block)

| ID | Objective | Implementation (file:line) | Evidence | Status |
|---|---|---|---|---|
| **CC6.1-TENANT** | A tenant cannot act on another tenant's data via the API | `require_org_access` + `_org_id_from_body` (`src/api/auth.py:142-225`); `enforce_service_member` (`auth.py:313`) | `/evidence/CC6.1-TENANT/` + `tests/api/test_tenant_isolation_bola.py` | 🔴 partial (C1 BOLA rollout incomplete) |
| **CC6.1-RLS** | DB enforces least-privilege row access independent of the API | Supabase RLS per table (`supabase/migrations/`) | `/evidence/CC6.1-RLS/` (policy inventory + negative tests + fix migration) | 🔴 `USING(true)` on vision/phone/schedule/sms tables |
| **CC6.6-AUTH** | Only verified principals reach privileged ops | Supabase JWT verify (`auth.py:42-62`); `require_admin`/`require_admin_auth` (fail-closed) | `/evidence/CC6.6-AUTH/` | 🟡 `ADMIN_EMAILS` hardcoded (`auth.py:25-31`) |
| **CC6.6-MFA** | MFA on all admin access to subservice consoles | Supabase/Railway/GitHub/Cloudflare MFA settings (org-level) | screenshots/policy (to collect) | 🚩 no technical enforcement — R6 |
| **CC6.6-SECRETS** | No secrets in code; scanned; governed; rotated | gitleaks pre-commit + CI (`.gitleaks.toml`, `.github/workflows/gitleaks.yml`); `.env` gitignored; AES-256-GCM token vault | `/evidence/CC6.6-AUTH/` secrets section | 🟡 Contabo file-secrets ungoverned; env vars undocumented |
| **CC6.7-ENCRYPTION** | Confidentiality in transit & at rest | TLS+HSTS (`security_headers.py:13`); POS tokens AES-256-GCM (`src/security/encryption.py`); Supabase AES-256 | `/evidence/CC6.7-ENCRYPTION/` | 🟡 RTSP edge unencrypted; CSP `unsafe-inline`; doc says wrong algo |

## CC1–CC5, CC7–CC9 — Common Criteria

| ID | Objective | Implementation | Evidence | Status |
|---|---|---|---|---|
| **CC1-GOV** | Defined control environment despite solo-founder reality | Roles documented; quarterly security review ritual | `/policies/hr-personnel-security.md`, `/policies/risk-assessment-management.md` | 🚩 oversight ritual to operate |
| **CC2-COMMITMENTS** | External commitments backed by controls | Signed SLA (`generate-sla-pdf.ts`) mapped to controls in `gap-analysis.md` | `/evidence/` SLA + mapping | 🟡 |
| **CC3-RISK** | Risks identified, assessed, treated | `/risk/register.md` + threat models | `/risk/` | 🟢 authored |
| **CC4-MONITOR** | Continuous monitoring + periodic evaluation | CI scans, log review cadence, pen-test cadence | `/policies/logging-monitoring.md`, `/policies/vulnerability-management.md` | 🟡 scans non-blocking; pen test unbooked |
| **CC5-SOD-COMPENSATING** | Compensate for impossible segregation of duties | Immutable git history, mandatory PR review, CI gate, tamper-evident logs | `CC5-SOD-COMPENSATING.md` | 🟢 authored |
| **CC7-INCIDENT** | Detect → respond → recover → review | Sentry, `security_events`, healthchecks; IRP | `/policies/incident-response-plan.md`; `/evidence/CC7-INCIDENT/` (Toast/Clover precedents) | 🟢 IRP authored; alerting gap |
| **CC7-VULNMGMT** | Find & fix vulnerabilities on an SLA | bandit/safety/npm-audit/gitleaks CI; SECURITY_SWEEP tracker | `/policies/vulnerability-management.md` | 🟡 non-blocking; no pen test |
| **CC8-CHANGE** | All change is controlled & authorized | branch→PR→CI→human merge→deploy; tar+sha256 rollback | `/policies/change-management.md`; `/evidence/CC8-CHANGE/` (PR/CI history) | 🟢 strongest area; branch-protection evidence to add |
| **CC9-VENDOR** | Subservice risk managed (carve-out) | `/vendors/` register + review cadence | `/vendors/` | 🟡 7 of ~25 registered |

## Additional categories

| ID | Objective | Implementation | Evidence | Status |
|---|---|---|---|---|
| **A1-BACKUP** | Recoverable backups, tested | 3-tier archive (`cold_storage.py`) + Supabase PITR | `/evidence/A1-BACKUP/`; quarterly restore test | 🔴 untested restore |
| **A1-AVAILABILITY** | Meet 99.5% SLA; capacity; redundancy | healthchecks; PM2 restart; Railway | `/policies/business-continuity-dr.md` | 🟡 Contabo SPOF; no uptime monitor |
| **C1-CLASSIFICATION** | Classify, handle, retain, dispose confidential data | classification scheme; retention/disposal | `/policies/data-classification.md`, `/policies/data-retention-disposal.md` | 🔴 deletion unscheduled |
| **PI1-RECONCILE** | Computed financials reconcile to source | `reconcile.py` (Square ±$1, post-sync) | `/evidence/PI1-RECONCILE/` | 🔴 Square-only; log-only |
| **P-PRIVACY** | Lawful basis, consent, rights, retention | CASL guard, acceptance gate, DSAR intake, consent banner | `/evidence/P-PRIVACY/` | 🔴 resale disclosure + deletion automation + biometric PIA |

## Naming convention
`<criterion>-<short-name>`, e.g. `CC6.1-RLS`. Evidence folders mirror the ID. New controls get a register row
**and** an evidence folder before they count toward readiness.
