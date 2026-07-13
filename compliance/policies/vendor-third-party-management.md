# Vendor and Third-Party Management Policy
**Document ID:** POL-009
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder, US signing authority)
**Review Cadence:** Annual, plus triggered review on any new sub-processor onboarding or material change in an existing sub-processor's service scope
**Parent Policy:** [information-security-policy.md](./information-security-policy.md)
**Control Reference:** CC9 (Risk Management — Vendor and Business Partner Risk)

---

## Purpose

Define how Meridian selects, onboards, monitors, and offboards third-party vendors and sub-processors that handle, store, or transmit Meridian customer data. Establish the carve-out method as the primary assurance strategy, maintain the sub-processor register, and identify the outstanding Quebec Law 25 Transfer Risk Assessment obligation for US-based sub-processors.

Meridian is not SOC 2 certified. This policy is part of an internal control framework authored to support readiness for a future Type II examination.

---

## Scope

Applies to all third-party organisations that:
- Process, store, or transmit Meridian customer data on Meridian's behalf (sub-processors), or
- Provide infrastructure or tooling material to the security, availability, or confidentiality of Meridian systems

Does not apply to: public open-source libraries with no data-processing role; marketing vendors that receive only pseudonymous analytics with no personal data.

The full sub-processor register is maintained at **`compliance/vendors/`**. This policy governs how that register is populated and kept current.

---

## Procedure

### 3.1 Sub-Processor Assurance Method (Carve-Out)

Meridian relies on the **carve-out method** for sub-processor assurance: rather than auditing sub-processors directly, Meridian relies on each sub-processor's own independently certified security posture. Each material sub-processor must hold at least one of:

- SOC 2 Type II report (publicly listed or provided under NDA)
- ISO 27001 certificate in scope for the services used
- PCI DSS Level 1 or Level 2 Service Provider certification (for payment processors)

Where a sub-processor holds none of these (currently: Contabo VPS, 209.126.80.45), Meridian documents compensating controls in lieu of independent certification. See `compliance/vendors/contabo.md`.

The carve-out method means Meridian's own SOC 2 boundary explicitly excludes the sub-processors' internal controls — the auditor will note a "carve-out" for each. This is standard practice and does not imply sub-processor risk is unmanaged.

---

### 3.2 Current Sub-Processor Summary

| Sub-Processor | Data Handled | Certification Basis | Data Location | DPA Executed |
|---|---|---|---|---|
| **Supabase** (AWS us-east-1) | All customer PII, POS data, camera analytics, compliance records | Supabase SOC 2 Type II (public); underlying AWS SOC 2 Type II | US — AWS us-east-1 | See `compliance/vendors/supabase.md` |
| **Railway** | FastAPI process memory, env vars, deployment pipelines | Railway SOC 2 Type II (public) | US | See `compliance/vendors/railway.md` |
| **Cloudflare** (R2 + CDN) | Cold archive objects in `meridian-archives`; TLS termination | Cloudflare SOC 2 Type II (public) | US (R2 automatic region) | See `compliance/vendors/cloudflare.md` |
| **Telnyx** | Phone call audio streams, DTMF digits (including phone-pay path), caller phone numbers | Telnyx SOC 2 (public) | US | See `compliance/vendors/telnyx.md` |
| **Square** | POS OAuth tokens (used by Meridian backend); order writes via Square API | Square PCI DSS Level 1; Square API ToS | US | See `compliance/vendors/square.md` |
| **Stripe** | Payment method tokens for platform billing | Stripe PCI DSS Level 1; Stripe DPA | US | See `compliance/vendors/stripe.md` |
| **Resend** | Transactional email content (merchant notifications, CASL consent emails) | Resend SOC 2 (public) | US | See `compliance/vendors/resend.md` |
| **Contabo** (VPS 209.126.80.45) | Celery/Beat workers, Redis, DeerFlow, Garry agent, async compute | **No SOC 2 / ISO 27001.** Compensating controls: SSH key-only auth, secrets in `/root/.secrets/` (chmod 700), gitleaks excluded on-box | Germany (Contabo DC) | See `compliance/vendors/contabo.md` |

For the full register including ~18 additional tooling vendors, see **`compliance/vendors/`**. The information-security-policy (POL-001 §5.3) lists the 7 material sub-processors; this policy governs all 25+ in the full register.

---

### 3.3 Vendor Onboarding Due Diligence

Before any new vendor is granted access to Meridian customer data:

1. **Risk classification:** Aidan Pierce assigns the vendor to one of three risk tiers based on data access:
   - **Critical** — direct access to Tier 2 or Tier 3 data (PII, POS data, camera↔POS journeys)
   - **Standard** — access to Tier 1 data or anonymised aggregates only
   - **Tooling** — no customer data access (CI/CD tooling, developer tooling, monitoring with no PII)

2. **Assurance review (Critical tier only):**
   - Obtain current SOC 2 Type II report or equivalent certificate
   - Confirm scope covers the services Meridian will use
   - Review for exceptions or qualified opinions in the Type II report

3. **Data Processing Agreement (DPA):**
   - All Critical-tier vendors must sign a DPA before receiving data
   - DPA must include: purpose limitation, sub-processor obligations, breach notification (≤72 hours to Meridian), data deletion on termination, and cross-border transfer clauses
   - DPA stored in `compliance/vendors/<vendor>.md` with a link to the signed document

4. **Transfer Risk Assessment (Quebec Law 25):** See §3.5.

5. **Approval:** Aidan Pierce countersigns the vendor onboarding checklist in `compliance/vendors/<vendor>.md`.

---

### 3.4 Ongoing Monitoring and Annual Review

Meridian reviews all Critical-tier sub-processors annually against the following:

| Check | Frequency | Action on Failure |
|---|---|---|
| SOC 2 / ISO / PCI certificate still current | Annual | Escalate to Aidan Pierce; suspend data sharing pending renewal |
| DPA terms still match current data scope | Annual | Renegotiate DPA |
| Sub-processor's own sub-processors disclosed | Annual | Review new fourth-parties; update Transfer Risk Assessment if US→CA data flows added |
| Breach notification received from sub-processor | On event | Trigger Meridian incident response; notify affected merchants per SLA |
| Sub-processor material change of control (acquisition, insolvency) | On event | Review contract rights; assess data risk |

Annual review is documented in `compliance/evidence/POL-009/vendor-review-<year>.md` with a checklist entry for each Critical-tier vendor.

Changes that trigger an immediate out-of-cycle review:
- New sub-processor added to the data flow
- Existing sub-processor expands scope (e.g., Telnyx begins transcription storage)
- Sub-processor ceases SOC 2 certification
- Sub-processor's public breach disclosure

---

### 3.5 Quebec Law 25 — Privacy Impact Assessments for Cross-Border Transfers

## DECISION (Canadian privacy counsel required)

Quebec Law 25 (Act respecting the protection of personal information in the private sector, as amended) requires a **Privacy Impact Assessment (PIA)** before any personal information of a Quebec resident is communicated outside Quebec to a person or body in another jurisdiction. This applies to each US-based sub-processor that may receive data about Quebec-resident merchants or end-customers.

**Current status:** No Transfer Risk Assessments have been conducted. The following sub-processors receive data about Quebec-resident merchants and their end-customers (phone-order caller phone numbers, POS transaction data, camera analytics):

| Sub-Processor | Data Type Crossing Border | PIA Status |
|---|---|---|
| Supabase (AWS us-east-1) | All PII, all POS data, camera analytics | Not completed |
| Railway (US) | Process memory — PII in API requests | Not completed |
| Cloudflare R2 (US) | Cold archive — POS and camera data | Not completed |
| Telnyx (US) | Phone call audio, caller phone numbers | Not completed |
| Resend (US) | Merchant email addresses in email bodies | Not completed |

**Required actions:**
1. Retain a Quebec-licensed privacy lawyer (posture doc estimates $500–$800 for initial consultation)
2. Conduct a Transfer Risk Assessment for each sub-processor above, covering: the legal basis for transfer, the sub-processor's data protection regime (US = PIPEDA-equivalent or stronger?), contractual safeguards (DPA clauses), and residual risk
3. Document each PIA in `compliance/vendors/<vendor>-quebec-pia.md`
4. If any PIA concludes the transfer is not adequate, suspend data flows pending remediation (e.g., Supabase region selection, data residency options)

Until PIAs are completed, Meridian is operating under known compliance risk for Quebec residents. This risk is logged in `compliance/risk/risk-register.md`.

---

### 3.6 Sub-Processor Offboarding

When a sub-processor relationship ends:

1. Revoke all Meridian API keys, OAuth tokens, and credentials granted to the sub-processor
2. Request written confirmation from the sub-processor that all Meridian customer data has been deleted or returned, per DPA terms
3. Retain the deletion confirmation in `compliance/vendors/<vendor>.md`
4. Remove the sub-processor from the active register in `compliance/vendors/`

---

### 3.7 Contabo VPS — Non-Certified Compensating Controls

Contabo (VPS 209.126.80.45) holds no SOC 2 or ISO 27001. Compensating controls in lieu of certification:

| Control | Implementation |
|---|---|
| Authentication | SSH key-only (`/root/.ssh/authorized_keys`); password auth disabled |
| Secrets management | All secrets in `/root/.secrets/` with chmod 700; accessed at runtime only; never in version control |
| Access | Aidan Pierce only; no contractor SSH access without explicit per-session approval |
| Monitoring | PM2 process-level health checks (`ecosystem.config.js`) |
| Network | Cloudflare DNS proxy for all public endpoints; direct VPS port exposure limited to SSH (22) and necessary service ports |
| Data residency | Async workers process data in transit; Redis cache is ephemeral; no Tier 3 data stored permanently on Contabo |

These compensating controls are reviewed annually and documented in `compliance/vendors/contabo.md`.

---

## Roles

| Role | Responsibility |
|---|---|
| Aidan Pierce (Policy Owner) | Approve all new sub-processors; sign DPAs; conduct annual reviews; resolve Quebec Law 25 PIA obligation |
| CA Admins (Nguyen, Cheung) | Report any new tooling or service they intend to use that touches customer data; no authority to approve new sub-processors |
| Future engineer | Must raise a vendor onboarding request before integrating any new data-handling service |

---

## Owner

Aidan Pierce

---

## Review Cadence

Annual. Triggered review on: new sub-processor onboarding, sub-processor material change, Quebec Law 25 enforcement guidance update, or receipt of a sub-processor's breach notification.

---

## Evidence that this Policy Operates

Auditors should verify:
1. **`compliance/vendors/`** — directory of sub-processor files; each Critical-tier vendor file should include: current cert reference, DPA status, Quebec PIA status, last-reviewed date.
2. **`compliance/evidence/POL-009/vendor-review-<year>.md`** — annual review checklist with dates and sign-off.
3. **`compliance/evidence/POL-009/dpa-tracker.md`** — table mapping each Critical-tier vendor to DPA execution date and document location.
4. **`compliance/evidence/POL-009/quebec-pia-tracker.md`** — status of each required Transfer Risk Assessment (§3.5).
5. **This file's git history** — `git log --follow compliance/policies/vendor-third-party-management.md`.

---

## Related Policies

- [information-security-policy.md](./information-security-policy.md) — POL-001 master policy, §5.3 sub-processor list
- [data-classification.md](./data-classification.md) — POL-007 data tiers handled by sub-processors
- [data-retention-disposal.md](./data-retention-disposal.md) — POL-008 deletion obligations on sub-processor offboarding
- [asset-management.md](./asset-management.md) — POL-011 system boundary encompassing sub-processor infrastructure
