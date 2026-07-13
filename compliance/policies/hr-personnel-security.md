# HR & Personnel Security Policy
**Document ID:** POL-007
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder, US signing authority)
**Review Cadence:** Annual, or within 30 days of any personnel change

---

## Purpose

Ensure that every individual with access to Meridian production systems, customer data, or cryptographic secrets is properly vetted before access is granted, operates under documented responsibilities, and has all access revoked completely and same-day on separation. This policy also documents the segregation-of-duties (SoD) reality for a solo-founder operation and the compensating controls in place.

---

## Scope

This policy applies to all Meridian personnel with access to any of the following:

| System | Access type |
|---|---|
| Supabase project `kbuzufjxwflrutowwnfl` (AWS us-east-1) | DB read/write, Auth admin |
| Railway team (project `miraculous-curiosity` / Meridian) | Env vars, deployments, logs |
| GitHub org / repositories | Source code, CI, secrets |
| Contabo VPS `209.126.80.45` | SSH, PM2 processes, `/root/.secrets/` |
| Cloudflare account | DNS, Stream, R2, WAF rules |
| Stripe Connect platform | Payment intents, webhook signing secrets |
| Square merchant OAuth credentials | POS order writes |
| Resend / Postal | Transactional email content |

**Current personnel in scope:**

| Individual | Role | Jurisdiction |
|---|---|---|
| Aidan Pierce | Sole US Admin, Policy Signing Authority | US |
| Aidan Nguyen | Canada Administrative Co-Authority | CA |
| Enoch Cheung | Canada Administrative Co-Authority | CA |
| Active contractors | Scoped dev access under NDA / non-compete | Various |

---

## Procedure

### 1. Onboarding — Before Any Access Is Granted

All steps below must be completed and documented in `compliance/evidence/POL-007/access-grants.md` before a new individual receives any production credentials.

**Step 1.1 — Legal agreements**

- Contractor (non-employee) must execute a written NDA and non-compete before receiving any access.
- Signed copies stored in `compliance/evidence/POL-007/contracts/<name>-<date>/`. Electronic signatures (DocuSign or equivalent) are acceptable.
- CA admins (employees or quasi-employees): confirm employment agreement or equivalent engagement letter is on file.

**Step 1.2 — Background check**

See [§ DECISION — Background Checks](#decision--background-checks) below.

**Step 1.3 — Security awareness reading**

Before credentials are issued, the new person must read and acknowledge:
- [information-security-policy.md](./information-security-policy.md) (POL-001)
- [access-control.md](./access-control.md) (POL-002)
- This policy (POL-007)

Acknowledgement is recorded in `compliance/evidence/POL-007/security-awareness-ack.md`. Format:

```
| Name | Date read | Policies acked | Aidan sign-off |
| Aidan Nguyen | 2026-06-28 | POL-001, POL-002, POL-007 | Aidan Pierce |
```

**Step 1.4 — Access grant (principle of least privilege)**

Access is granted by Aidan Pierce only, using the minimum permissions required for the role:

| System | How to grant | Minimum role |
|---|---|---|
| Supabase | Project Settings → Members → Invite | `developer` (not `owner`) |
| Railway | Team → Members → Invite | `viewer` or `member` (not `admin`) |
| GitHub | Repo Collaborator or Org Member → specific repos only | `write` (not `admin`) |
| Contabo VPS | Append SSH public key to `/root/.secrets/authorized_keys` or system `authorized_keys`; confirm password auth is DISABLED (`PasswordAuthentication no` in sshd_config) | SSH access to named directories only where feasible |
| Cloudflare | Account → Members → Invite | `Read` unless deployment role required |

Every grant is logged in `compliance/evidence/POL-007/access-grants.md` with: date, grantor (always Aidan Pierce), system, role assigned, and access expiry (if time-limited contractor).

**Step 1.5 — Acceptable-use acknowledgement**

The new person signs an Acceptable Use statement confirming:
- No use of Meridian credentials for personal projects
- No sharing of credentials with third parties
- Obligation to report suspected security incidents immediately to Aidan Pierce
- Understanding that all activity on Meridian systems is logged

Template stored at `compliance/evidence/POL-007/acceptable-use-template.md`.

---

### 2. Offboarding — Same-Day Access Revocation

Trigger: resignation, contract end, termination for cause, or role change eliminating access need.

**Aidan Pierce must complete all of the following within the same business day.** For termination-for-cause, target is 2 hours.

**Offboarding checklist (record in `compliance/evidence/POL-007/offboarding-log.md`):**

```
Individual: [name]
Separation date: [date]
Separation type: [resignation / contract end / termination]
Aidan Pierce initiating: [date + time]

[ ] Supabase: removed from project kbuzufjxwflrutowwnfl member list
[ ] Railway: removed from team members list
[ ] GitHub: removed as collaborator/org member; any personal tokens they generated are unknown — rotate any shared secrets (Railway env vars, Cloudflare API keys) as a precaution
[ ] Contabo VPS: SSH public key removed from authorized_keys on 209.126.80.45
[ ] Cloudflare: access invite revoked
[ ] Stripe / Square: confirm individual had no personal API keys; if uncertain, rotate signing secrets
[ ] Any shared secrets (DB passwords, SMTP credentials) known to the individual: rotated
[ ] /root/.secrets/ reviewed: no files referencing individual's tokens remaining

Completion confirmed by: Aidan Pierce | [date + time]
```

**API key and token rotation:** Any shared long-lived secret that the departing individual had access to must be assumed compromised and rotated within 24 hours of separation, even if access was revoked. Document rotations in the offboarding log.

---

### 3. Roles & Responsibilities

| Role | Responsibility |
|---|---|
| **Aidan Pierce (Policy Owner)** | Sole authority to grant and revoke production access. Execute onboarding / offboarding checklists. Own this policy. Conduct annual policy review. |
| **CA Admins (Nguyen, Cheung)** | Operate strictly within granted access scope. May NOT grant access to others. Report anomalies or suspected incidents to Aidan immediately. Read and ack this policy annually. |
| **Contractors** | Operate within NDA / non-compete and within specific project scope. No access beyond the systems and repos explicitly granted. Report security concerns to Aidan Pierce. |
| **No one** | May self-grant elevated permissions, share credentials, or access systems outside their defined role. |

---

### 4. Segregation of Duties — Solo-Founder Reality & Compensating Controls

Meridian is a solo-founder + small-team operation. True segregation of duties (where no single person can initiate AND approve a sensitive action) is not achievable at current headcount. This is an acknowledged risk documented in `compliance/risk/register.md`.

**Compensating controls in place:**

| Control | Mechanism | Verification |
|---|---|---|
| Immutable git history | All production code changes committed to GitHub; branch protection on `main` and `session-2-canada-prep` prevents force-push. No history rewriting. | `git log --oneline origin/main` |
| Mandatory PR review | PRs to `main` must receive at least one review before merge. When Aidan Pierce is the only available reviewer, the PR is at minimum delayed 24h and self-reviewed against the checklist in `compliance/evidence/CC8-CHANGE/`. | GitHub branch protection settings screenshot |
| CI security gate | Every PR runs `.github/workflows/gitleaks.yml` (secret scanning), `.github/workflows/security.yml`, and `.github/workflows/syntax-check.yml`. Merge is blocked on failure. | GitHub Actions run history |
| Railway env var audit log | Railway logs all environment variable modifications with actor, timestamp, and value hash. Aidan reviews this log in quarterly security reviews. | Railway dashboard audit trail |
| Supabase audit log | Supabase project audit log is enabled; records Auth admin events, DB schema changes, and member invite/removal events. | Supabase dashboard → Logs → Audit |
| Quarterly management review | Aidan Pierce reviews access grant log, incident log, and sub-processor list each quarter and signs off in `compliance/evidence/POL-009/quarterly-reviews.md`. Described fully in POL-009. | `compliance/evidence/POL-009/quarterly-reviews.md` |

**Acknowledged residual risk:** A motivated malicious insider with Aidan Pierce's credentials could bypass all above controls. Mitigations: 1Password as sole credential vault (no credential reuse), phishing-resistant auth for Google/GitHub (hardware key recommended — see DECISION below), and personal liability under applicable law.

---

## ## DECISION (Aidan) — Background Checks

**Context:** SOC 2 CC1.1 expects the entity to demonstrate commitment to integrity and ethical values, which typically includes pre-employment background checks. For a solo-founder with contractors, a formal background check vendor (e.g., Checkr, Sterling) is the standard approach.

**Options for Meridian's scale:**

1. **Lightweight self-attestation (minimum viable):** Require each contractor to sign a declaration confirming no felony convictions related to fraud, data theft, or computer crimes in the past 7 years. Store in `compliance/evidence/POL-007/contracts/<name>/background-self-attestation.md`. Auditors may flag this as insufficient.
2. **Basic criminal check via Checkr (~$30/contractor):** Checkr offers a "Basic Criminal" package. Run on all contractors before access is granted. Sufficient for SOC 2 at Meridian's stage.
3. **Full background check (Checkr "Pro" or equivalent):** Adds employment verification, education verification. Overkill for contract devs.

**Recommendation:** Option 2 (Checkr Basic Criminal, ~$30/contractor) before access is granted. Record the check ID and result (clear / consider) in `compliance/evidence/POL-007/background-checks.md`.

**Decision required from Aidan:** Choose option 1, 2, or 3. Once decided, update this section with the chosen approach and the vendor/process to use.

---

## ## DECISION (Aidan) — Hardware Security Keys for Admin Accounts

**Context:** GitHub, Railway, Cloudflare, and Supabase all support FIDO2/WebAuthn hardware keys. A phishing attack against Aidan Pierce's personal Google or GitHub account would compromise all Meridian systems. Hardware keys (YubiKey 5, $50) are the highest-ROI single security investment for a solo founder.

**Decision required from Aidan:** Confirm whether FIDO2 keys are enrolled on GitHub + Cloudflare + Railway accounts. If not, document a target date to enroll. Record outcome in `compliance/evidence/POL-007/mfa-enrollment.md`.

---

## Owner

Aidan Pierce. Policy exceptions require written approval from Aidan Pierce and are logged in `compliance/evidence/POL-001/exceptions.md`.

---

## Review Cadence

Annual review by Aidan Pierce. Triggered review within 30 days of: any personnel change, security incident involving personnel, or new contractor onboarding.

---

## Evidence that this Policy Operates

Auditors should verify:

1. **`compliance/evidence/POL-007/access-grants.md`** — current log of all access grants, dates, roles, and granting authority (Aidan Pierce).
2. **`compliance/evidence/POL-007/offboarding-log.md`** — completed offboarding checklists with same-day timestamps.
3. **`compliance/evidence/POL-007/contracts/`** — signed NDA and non-compete documents for each contractor.
4. **`compliance/evidence/POL-007/security-awareness-ack.md`** — signed policy acknowledgements from all personnel, dated within the last 12 months.
5. **`compliance/evidence/POL-007/background-checks.md`** — background check records per contractor (once DECISION above is resolved).
6. **GitHub branch protection settings** — confirm `main` has required-reviewer rule enabled.
7. **GitHub Actions run history** — gitleaks and security scan pass on all merged PRs.
8. **This file's git history** — `git log --follow compliance/policies/hr-personnel-security.md`
