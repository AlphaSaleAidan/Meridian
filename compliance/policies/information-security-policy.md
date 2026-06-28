# Information Security Policy
**Document ID:** POL-001
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder, US signing authority)
**Review Cadence:** Annual, or on any material architectural change

---

## Purpose

This document is the master information security policy for Meridian AI Business Solutions. It defines the security principles, control environment, authority structure, and commitment to the Trust Services Criteria (TSC) that govern all Meridian systems, personnel, and service providers. All subordinate policies listed in §6 derive their authority from this document.

Meridian is not SOC 2 certified. This policy represents Meridian's internal control framework, authored to support readiness for future Type II examination.

---

## Scope

This policy applies to:
- All production systems operated by or on behalf of Meridian: the FastAPI backend on Railway (`api.meridian.tips`), the React/Vite frontend served from Railway and the Contabo VPS (209.126.80.45), Supabase managed Postgres (project `kbuzufjxwflrutowwnfl`, AWS us-east-1), Redis (Contabo), all async workers (Celery/Beat, DeerFlow, scraper, Garry self-healing agent managed via PM2 `ecosystem.config.js`).
- All personnel with access to production systems, secrets, or customer data. Currently: Aidan Pierce (US), Aidan Nguyen (CA), Enoch Cheung (CA).
- All third-party sub-processors handling Meridian customer data (see §5).

---

## Control Environment

### Authority Structure

| Role | Individual | Scope |
|------|-----------|-------|
| Sole US Administrative Authority / Policy Signing | Aidan Pierce | All production systems, Railway, GitHub, Cloudflare, Supabase, Stripe |
| Canada Administrative Co-Authority | Aidan Nguyen | Canada portal operations, onboarding, rep management |
| Canada Administrative Co-Authority | Enoch Cheung | Canada portal operations, onboarding, rep management |

Aidan Pierce is the single approval authority for: exceptions to this policy, emergency access grants, new sub-processor onboarding, and any change to Railway environment variables in production.

### Commitment to the Five Trust Services Criteria

| TSC Category | Meridian Commitment |
|---|---|
| **CC — Security** | Protect customer data from unauthorized access through defense-in-depth: Supabase RLS, JWT-gated APIs, AES-256-GCM token encryption, gitleaks secret scanning, TLS 1.2+ on all endpoints. |
| **A — Availability** | Railway managed hosting (Railway SLA) for the API; Contabo VPS for async workers. Incident response targets: P0 customer-data exposure < 2hr triage, P1 service outage < 4hr restore attempt. |
| **PI — Processing Integrity** | Tenant data isolation enforced at the database row level (RLS) and API layer (require_org_access dependency). Orders and POS submissions processed only once via idempotent Square API calls. |
| **C — Confidentiality** | POS OAuth tokens encrypted at rest (AES-256-GCM, `src/security/encryption.py`). Supabase AES-256 at rest. Secrets never stored in version control (gitleaks enforced). |
| **P — Privacy** | Not in scope for current examination period. Meridian does not sell customer PII. Data retention decisions deferred to the Data Retention policy (not yet authored). |

---

## Procedure

### 5.1 Risk Management Cycle

Risks to customer data, system availability, and processing integrity are identified, documented, and tracked in `compliance/risk/`. Risks are rated by likelihood × impact (1–5 each). Any risk rated ≥ 12 requires a written remediation plan within 30 days. The risk register is reviewed at each annual policy review and after any security incident.

### 5.2 Exception Process

Any deviation from a subordinate policy requires a written exception request submitted to Aidan Pierce. The request must state: the specific policy clause being excepted, the business justification, the compensating control in place during the exception period, and the planned resolution date. Approved exceptions are logged in `compliance/evidence/POL-001/exceptions.md` and expire after 90 days unless renewed.

### 5.3 Third-Party / Sub-Processor Oversight

Current sub-processors material to customer data:

| Sub-Processor | Data Handled | Security Basis |
|---|---|---|
| Supabase (AWS us-east-1) | All customer & tenant PII, orders, sessions | Supabase SOC 2 Type II (public); AES-256 at rest; TLS in transit |
| Railway | API process memory, env vars | Railway SOC 2 Type II (public); env vars encrypted at rest |
| Cloudflare | TLS termination, CDN | Cloudflare SOC 2 Type II (public) |
| Telnyx | Phone call audio, phone numbers | Telnyx SOC 2 (public) |
| Square | POS order data | Square PCI DSS Level 1; Square API for order writes |
| Stripe | Payment method tokens | Stripe PCI DSS Level 1; Meridian stores no raw card data |
| Resend | Transactional email content | Resend SOC 2 (public) |
| Contabo (VPS 209.126.80.45) | Async worker processes, Redis, file-based secrets in `/root/.secrets/` | **No independent SOC 2.** Compensating controls: SSH key auth, root password stored in 1Password (Aidan only), gitleaks on box excluded, secrets file permissions chmod 700. |

### 5.4 Incident Response (Summary)

A dedicated Incident Response policy is forthcoming. Current minimum procedure: any suspected data exposure is reported immediately to Aidan Pierce, who has sole authority to issue customer notifications and engage legal counsel. The incident is logged in `compliance/evidence/POL-001/incidents.md` with timeline, scope, and remediation steps.

### 5.5 Security Awareness

All personnel with production access must read this policy and each subordinate policy at least annually, acknowledged in `compliance/evidence/POL-001/acknowledgements.md`.

---

## Subordinate Policies (Cross-References)

| Policy | Document ID | File |
|---|---|---|
| Access Control | POL-002 | [access-control.md](./access-control.md) |
| Password & Authentication | POL-003 | [password-authentication.md](./password-authentication.md) |
| Encryption & Cryptography | POL-004 | [encryption-cryptography.md](./encryption-cryptography.md) |
| Secure SDLC | POL-005 | [secure-sdlc.md](./secure-sdlc.md) |
| Change Management | POL-006 | [change-management.md](./change-management.md) |

---

## Roles & Responsibilities

| Role | Responsibility |
|---|---|
| Aidan Pierce (Policy Owner) | Maintain and sign this policy; approve exceptions; sign off on sub-processor additions; lead incident response |
| CA Admins (Nguyen, Cheung) | Operate within scope defined by access grants; report suspected incidents immediately |
| Any future engineer | Must read subordinate policies before receiving production access |

---

## Evidence that this Policy Operates

Auditors should verify:
1. **`compliance/evidence/POL-001/acknowledgements.md`** — signed acknowledgements from all personnel with production access, dated within the last 12 months.
2. **`compliance/risk/risk-register.md`** — current risk register with ratings and owners.
3. **`compliance/evidence/POL-001/exceptions.md`** — log of any active or expired policy exceptions (empty = no exceptions granted).
4. **`compliance/evidence/POL-001/sub-processors.md`** — current sub-processor list with last-reviewed date and link to their public compliance certificates.
5. **This file's git history** — confirms authorship date and any subsequent revisions (`git log --follow compliance/policies/information-security-policy.md`).
