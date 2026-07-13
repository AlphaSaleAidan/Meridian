# Acceptable Use Policy
**Document ID:** POL-010
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder, US signing authority)
**Review Cadence:** Annual, or on any change to personnel roster or production system architecture
**Parent Policy:** [information-security-policy.md](./information-security-policy.md)

---

## Purpose

Define the acceptable and prohibited uses of Meridian production systems, data, developer tooling, and credentials by Meridian personnel and contractors. Establish the minimum conduct expectations that protect merchant data, preserve Meridian's legal obligations under CASL, PIPEDA, and Quebec Law 25, and uphold the trust that merchants place in Meridian's platform.

This policy is not an exhaustive list of all possible misuse. Any action that a reasonable person would consider harmful to merchants, to Meridian, or to end-customers is prohibited regardless of whether it is named here.

Meridian is not SOC 2 certified. This policy is part of an internal control framework authored to support readiness for a future Type II examination.

---

## Scope

Applies to all individuals who have been granted access to any Meridian production system, repository, or Tier 2/3 data:

- **Aidan Pierce** (Founder, US — full production authority)
- **Aidan Nguyen** (Canada Administrative Co-Authority — Canada portal operations)
- **Enoch Cheung** (Canada Administrative Co-Authority — Canada portal operations)
- Any future engineer, contractor, or consultant granted temporary or permanent access

"Production systems" means: Railway FastAPI deployment (`api.meridian.tips`), Supabase project `kbuzufjxwflrutowwnfl`, Contabo VPS (209.126.80.45), Cloudflare R2 bucket `meridian-archives`, the private GitHub repository `AlphaSaleAidan/Meridian`, and any merchant-premises Jetson edge device connected to the Meridian platform.

---

## Procedure

### 3.1 Acceptable Uses

The following uses of Meridian systems and data are explicitly permitted:

| Use | Scope / Constraint |
|---|---|
| Accessing production systems to investigate, diagnose, and resolve incidents | Minimum access necessary; actions must be logged; no modification to data without written approval from Aidan Pierce |
| Running database queries against Supabase for support, debugging, or compliance requests | Query must be scoped to the relevant `org_id`; results must not be exported outside Meridian tooling without approval |
| Deploying to Railway via a merged pull request on `main` | Automated via Railway CI; no manual Railway CLI deploys without approval |
| Accessing merchant data to fulfill a privacy rights request | Must follow the privacy request workflow at `compliance.py:208`; log access in `privacy_requests` |
| Using Meridian tooling (GitHub, Railway dashboard, Supabase Studio) for legitimate development and operations | Business purpose only; personal projects must not be run on Meridian infrastructure |
| Reading this and all subordinate compliance policies as required annually | Acknowledgement required in `compliance/evidence/POL-001/acknowledgements.md` |

---

### 3.2 Prohibited Actions

The following actions are strictly prohibited regardless of role, unless a written exception is approved by Aidan Pierce and logged in `compliance/evidence/POL-001/exceptions.md`:

#### 3.2.1 Data Misuse

- **Cross-merchant data access** — querying, exporting, or processing any merchant's data in a context scoped to a different merchant. All queries must include a filtering predicate on `org_id` or equivalent.
- **Unauthorized data export** — extracting Tier 2 or Tier 3 data (PII, POS data, camera analytics, `customer_journeys`) to personal devices, personal cloud storage, or any system outside the Meridian boundary without explicit written approval.
- **Using merchant data for personal purposes** — merchant sales data, customer phone numbers, and camera analytics may not be used for personal analysis, personal enrichment, or any purpose not directly serving the merchant's account.
- **Sharing credentials or data** with parties not listed in this policy's scope section.

#### 3.2.2 Credentials and Secrets

- **Hardcoding secrets in source code** — API keys, database connection strings, OAuth tokens, and passwords must never appear in any file committed to version control. All secrets are stored in `/root/.secrets/` (Contabo, chmod 700), Railway environment variables, or Supabase environment configuration. Gitleaks is enforced in CI.
- **Sharing environment variables** in Slack, email, or any unencrypted channel. Use Railway's env-var interface or Aidan's 1Password vault for transmission.
- **Using personal AWS, Cloudflare, or Supabase accounts** for any Meridian data processing.
- **Rotating production secrets without notifying Aidan Pierce** — secret rotation is a planned, coordinated event. Unilateral rotation can break Railway deployments and Celery workers simultaneously.

#### 3.2.3 System Integrity

- **Bypassing Row-Level Security** — executing queries with the Supabase `service_role` key in a context where an `anon` or user-JWT key is appropriate, in order to circumvent merchant-scoped access control.
- **Disabling or weakening security controls without approval** — including but not limited to: disabling gitleaks pre-commit hooks, removing RLS policies, widening CORS origins, or removing the SHA-256 acceptance gate (`src/compliance/acceptance_gate.py`).
- **Pushing directly to `main`** — all changes must flow through a pull request with at least one review by Aidan Pierce. Direct pushes to `main` or `session-2-canada-prep` are blocked.
- **Deploying migrations to Supabase production without a dry-run review** — all migrations must be reviewed in the staging environment (or against a Supabase branch) before being applied to `kbuzufjxwflrutowwnfl`.

#### 3.2.4 Safety Controls — Independent Control Planes Principle

Meridian's safety architecture requires that independent safety controls fail independently, with different inputs and different control planes, so that a single failure does not disable multiple guards simultaneously.

**Prohibited:**
- Wiring two distinct safety guards to the same switch, environment variable, or configuration key so that one change disables both
- Adding a "master disable" for safety features (camera consent gate, CASL guard, PCI card-clear path) that can be triggered from a single API call or environment flag without a separate out-of-band confirmation
- Testing safety controls only in the "happy path" direction — each control must be verified to be `assert_not_called` (i.e., the side effect does not fire) when the control is legitimately denied; a control that always passes is not a control

When implementing any new security or compliance gate, the reviewer must verify: (a) the guard fires correctly on the denied input, and (b) the guard does not fire on the permitted input, using separate test cases.

#### 3.2.5 Contractor-Specific Obligations

Contractors and consultants must, before receiving any production access:
1. Sign Meridian's NDA (template at `compliance/templates/nda.md` — to be authored)
2. Acknowledge this policy in writing (email to `aidanpierce72@gmail.com` or `compliance/evidence/POL-001/acknowledgements.md` entry)
3. Receive access only to the minimum systems required for their engagement (least privilege)
4. Return or destroy any copies of Meridian data within 5 business days of engagement end

Contractors may not subcontract any Meridian work without explicit written approval from Aidan Pierce.

---

### 3.3 Least Privilege

Access to production systems is granted at the minimum level required to perform the assigned function:

| Role | Default Access Grant |
|---|---|
| Aidan Pierce | Full — all systems, all data tiers |
| Aidan Nguyen | Canada portal operations scope: `business_users` (CA orgs), `rep_profiles`, `compliance_acceptances`; no direct Supabase service-role key; no Railway deploy authority |
| Enoch Cheung | Same as Nguyen |
| Future contractor (development) | GitHub repository (feature branch only); Railway read-only logs (if needed); no Supabase direct access without per-task approval |
| Future contractor (support) | Supabase Studio read-only on specified tables, scoped to `org_id` of the merchant being supported; time-limited grant |

Access grants are documented in `compliance/evidence/POL-002/access-grants.md` (maintained by the Access Control policy, POL-002).

---

### 3.4 Incident Reporting

Any individual who suspects a violation of this policy, observes an anomalous data access, discovers a secret committed to version control, or identifies a potential data breach must report immediately to Aidan Pierce. Reports must include: what was observed, when, and what system or data was involved.

Deliberate violation of §3.2 by a contractor is grounds for immediate termination of the engagement and may result in civil or criminal referral depending on the nature of the violation.

---

## Roles

| Role | Responsibility |
|---|---|
| Aidan Pierce (Policy Owner) | Enforce this policy; approve exceptions; terminate access on violation; maintain access grant log |
| All personnel in scope | Read and acknowledge annually; report suspected violations immediately; operate within their minimum-privilege grant |

---

## Owner

Aidan Pierce

---

## Review Cadence

Annual. Triggered review on: new personnel onboarding, departure of any individual with production access, or material change to the production system boundary.

---

## Evidence that this Policy Operates

Auditors should verify:
1. **`compliance/evidence/POL-001/acknowledgements.md`** — signed acknowledgements from all personnel currently in scope, dated within the last 12 months.
2. **`compliance/evidence/POL-002/access-grants.md`** — current access grant log confirming least-privilege assignments.
3. **`compliance/evidence/POL-001/exceptions.md`** — log of any approved exceptions to §3.2; auditors should confirm no unapproved bypasses exist (e.g., direct pushes to `main` in git log).
4. **GitHub branch protection settings** for `main` — confirm direct push is blocked and PR review is required.
5. **`src/compliance/acceptance_gate.py`** and **`src/compliance/casl_guard.py`** — confirm safety controls are present and have dual-direction test coverage.
6. **This file's git history** — `git log --follow compliance/policies/acceptable-use.md`.

---

## Related Policies

- [information-security-policy.md](./information-security-policy.md) — POL-001 master policy; exception process at §5.2
- [access-control.md](./access-control.md) — POL-002 access grant details, provisioning, and deprovisioning
- [data-classification.md](./data-classification.md) — POL-007 defines Tier 2/3 data referenced in §3.2.1
- [secure-sdlc.md](./secure-sdlc.md) — POL-005 development workflow controls (PR reviews, branch protection)
