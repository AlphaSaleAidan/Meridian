# Risk Assessment & Management Policy
**Document ID:** POL-009
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder, US signing authority)
**Review Cadence:** Annual; triggered on major architecture change, security incident, or new sub-processor onboarding

---

## Purpose

Define how Meridian identifies, rates, treats, and monitors information security risks across its systems and supply chain. Establish the quarterly management oversight ritual — a concrete, documented review that serves as the CC1.2 / CC1.4 compensating control for the absence of a formal board of directors.

---

## Scope

All Meridian production systems, personnel, sub-processors, and customer data flows as defined in [information-security-policy.md](./information-security-policy.md) (POL-001). Threat models for specific subsystems (POS integration, camera vision) are authored separately and referenced from this policy.

---

## Procedure

### 1. Risk Assessment Methodology

Meridian uses a qualitative likelihood × impact scoring model:

| Axis | Scale | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| **Likelihood** | How probable in 12 months | Very unlikely (<5%) | Unlikely (5–20%) | Possible (20–50%) | Likely (50–80%) | Near-certain (>80%) |
| **Impact** | Consequence if realized | Negligible (no customer effect) | Minor (< 10 customers, recoverable) | Moderate (< 100 customers or service degradation) | Major (> 100 customers, regulatory notice possible) | Catastrophic (breach, regulatory action, existential to business) |

**Risk score = Likelihood × Impact (range: 1 – 25)**

**Criticality thresholds and required response:**

| Score range | Label | Required response | Escalation |
|---|---|---|---|
| 1–5 | **Low** | Accept or monitor; document rationale in register | None |
| 6–11 | **Medium** | Mitigate within 90 days; document treatment plan | Aidan Pierce awareness |
| 12–19 | **High** | Mitigate within 30 days; Aidan Pierce written sign-off required | Aidan Pierce sign-off |
| 20–25 | **Critical** | Immediate action; consider suspending affected service until mitigated | Aidan Pierce escalates; consider legal counsel |

**Residual risk:** After controls are applied, re-score (residual likelihood × impact). The residual score must be documented alongside the inherent score in the register.

---

### 2. Risk Register

**Location:** `compliance/risk/register.md` — this is the single source of truth for all identified risks.

Each risk entry contains the following fields:

| Field | Description |
|---|---|
| **Risk ID** | Sequential (RISK-001, RISK-002, …) |
| **Title** | Short, specific label |
| **Affected system(s)** | E.g., "Supabase RLS", "Contabo VPS", "Twilio DTMF path" |
| **Category** | Access Control / Availability / Confidentiality / Fraud / Vendor / Privacy |
| **Inherent likelihood** | 1–5 |
| **Inherent impact** | 1–5 |
| **Inherent score** | L × I |
| **Treatment** | Accept / Mitigate / Transfer / Avoid |
| **Control(s) / Compensating control** | What is in place or planned |
| **Owner** | Almost always Aidan Pierce at current scale |
| **Residual likelihood** | 1–5 post-control |
| **Residual impact** | 1–5 post-control |
| **Residual score** | Residual L × I |
| **Target completion date** | For open mitigations |
| **Actual completion date** | When confirmed closed |
| **Last reviewed date** | Date of most recent assessment |

**Known top risks (documented in register — do not duplicate detail here):**

| Risk | Category | Notes |
|---|---|---|
| Multi-tenant cross-tenant write (historical) | Access Control | Remediated (per-tenant RLS policies shipped); documented as strength — the incident and fix are evidence of a responsive control environment |
| Contabo single-point-of-failure | Availability | No HA, no SOC 2; async workers and Canada frontend go dark on Contabo failure |
| Camera edge biometric/embedding exposure | Privacy / Confidentiality | On-device embeddings; merchant-premises physical security out of Meridian's control |
| Twilio raw PAN/CVV exposure in DTMF path | Confidentiality / PCI | Twilio records call audio including DTMF tones; raw card data in audio stream; PCI DSS implication |
| Fraud via unauthorized POS OAuth token | Fraud / Access Control | Tokens encrypted at rest; cross-tenant use blocked; risk mitigated but not eliminated |
| LLM prompt injection in analytics pipeline | Processing Integrity | Anonymized prompts sent to OpenRouter/DeepSeek etc.; prompt injection could affect analytics output |
| Solo-founder key-person dependency | Availability | All signing authority and admin access in one person; no documented succession |
| Undisclosed data-resale purpose | Privacy | If Meridian were to sell customer data, it would require disclosure not yet in policy or terms |

---

### 3. Assessment Cadence

**3.1 Annual comprehensive review**

- Full re-rating of all risks in `compliance/risk/register.md`.
- Threat models reviewed: `compliance/risk/threat-model-pos.md`, `compliance/risk/threat-model-camera.md`.
- Aidan Pierce signs off in `compliance/evidence/POL-009/quarterly-reviews.md` under the Q4 / annual entry.
- Any new risks identified are added to the register before sign-off.
- Target: complete within the first 30 days of each calendar year (January annual review) or within 30 days of the policy's anniversary.

**3.2 Triggered reviews**

A new risk assessment must be initiated within 14 days of any of the following events:

| Trigger | Example |
|---|---|
| New production system deployed | New POS integration (Clover, Toast) goes live |
| New sub-processor onboarded | New LLM provider added to `src/ai/routing/tiered_router.py` |
| Security incident | Any event logged in `compliance/evidence/CC7-INCIDENT/` |
| Major architecture change | Phone agent launch, camera subsystem expansion to new merchant |
| Regulatory inquiry | Government or legal inquiry about data practices |

The triggered review is documented as a new entry in `compliance/evidence/POL-009/quarterly-reviews.md` with type = `triggered`.

---

### 4. Risk Treatment Options

| Treatment | When to use | Documentation required |
|---|---|---|
| **Accept** | Risk score ≤ 5, or cost of mitigation exceeds risk cost | Written rationale in register; Aidan Pierce acknowledgement for scores ≥ 4 |
| **Mitigate** | Risk score > 5 and a cost-effective control exists | Control description, owner, target date, and residual score in register |
| **Transfer** | Risk is substantially borne by a sub-processor with adequate attestation (e.g., Supabase physical security) | Reference to sub-processor's attestation in `compliance/vendors/<vendor>.md` |
| **Avoid** | Activity creating the risk is discontinued | Document decision and date; confirm discontinuation in evidence |

**Appetite statement:** Meridian's risk appetite is LOW for risks affecting confidentiality of customer PII, processing integrity of financial transactions (POS orders, Stripe payments), and multi-tenant data isolation. Medium appetite for availability risks given current scale (acceptable degraded-mode during Contabo failures). Low appetite for privacy violations involving camera-adjacent data (biometric-adjacent embeddings).

---

### 5. Quarterly Lightweight Security Review (CC1 Management Oversight Ritual)

Because Meridian has no board of directors and no audit committee, this quarterly review is the primary management-oversight ritual. It satisfies CC1.1 (Commitment to Integrity and Ethical Values) and CC1.4 (Board/Management Oversight) for a solo-founder organization by creating a signed, tamper-evident record that the control environment was actively reviewed.

**Cadence:** Q1 (complete by January 31), Q2 (complete by April 30), Q3 (complete by July 31), Q4 (complete by October 31).

**Who conducts it:** Aidan Pierce. When CA admins Nguyen or Cheung have visible operational findings (e.g., onboarded a new rep that triggered an access question), they contribute input to Aidan's review via email or Slack thread (preserved in evidence).

**What is reviewed each quarter:**

| Item | Source | Question asked |
|---|---|---|
| Risk register | `compliance/risk/register.md` | Any new risks added since last review? Any open mitigations past their target date? |
| Access grant log | `compliance/evidence/POL-007/access-grants.md` | Are all current access grants authorized and current? Any departed personnel still listed? |
| Offboarding log | `compliance/evidence/POL-007/offboarding-log.md` | Are all recorded offboardings complete? |
| Incident log | `compliance/evidence/CC7-INCIDENT/` (or POL-001 incidents) | Any open incidents? Were all incidents closed within SLA? |
| Sub-processor register | `compliance/vendors/README.md` | Any new vendors added to the codebase not yet registered? Any vendors with overdue attestation refresh? |
| CI security scan trend | GitHub Actions → `.github/workflows/gitleaks.yml` + `security.yml` | Any scan failures in the past 90 days? Were failures addressed before the PR merged? |
| Policy review status | This file and sibling policies | Which policies are overdue for annual review (>12 months since last update)? |
| Contabo-specific check | SSH authorized_keys, PM2 process list | Is the process list consistent with expected workloads? Any unexpected processes? |

**Sign-off record format (in `compliance/evidence/POL-009/quarterly-reviews.md`):**

```markdown
## [Q1/Q2/Q3/Q4] [Year] Review — [date conducted]

**Type:** Scheduled / Triggered
**Conducted by:** Aidan Pierce
**Reviewed items:**
- Risk register: [summary — e.g., "2 new risks added: RISK-023 (Clover token scope), RISK-024 (PostHog EU data residency). No overdue mitigations."]
- Access grants: [summary — e.g., "3 active grants (Nguyen, Cheung, Contractor X). All current."]
- Offboarding log: [summary — e.g., "Contractor X offboarded 2026-05-15. Checklist complete."]
- Incident log: [summary — e.g., "0 incidents in Q2 2026."]
- Sub-processor register: [summary — e.g., "PostHog and Sentry added as per gap-analysis. DPA pending for both."]
- CI scan trend: [summary — e.g., "0 gitleaks failures in Q2. 1 security.yml flag (resolved in same PR)."]
- Policy review status: [summary — e.g., "POL-002 due for annual review by 2026-08-01."]
- Contabo check: [summary — e.g., "PM2 process list consistent. No unexpected processes."]

**Actions created:**
- [ ] RISK-023 mitigation plan authored by 2026-07-15 (Aidan)
- [ ] POL-002 annual review: schedule for July (Aidan)

**Findings requiring escalation:** [None / describe]

**Sign-off:** Aidan Pierce | [date]
```

This file is committed to git after each review. The git commit timestamp is the tamper-evident record that the review occurred on the stated date.

---

## Roles & Responsibilities

| Role | Responsibility |
|---|---|
| **Aidan Pierce (Policy Owner)** | Conduct quarterly reviews; maintain risk register; sign off on all High and Critical risk treatments; author triggered reviews within 14 days; own this policy. |
| **CA Admins (Nguyen, Cheung)** | Report new risks observed in Canada operations to Aidan Pierce. Review risk register entries relevant to their operational area at annual review. |
| **All personnel** | Report suspected new risks (security weaknesses, near-misses, suspicious activity) to Aidan Pierce immediately; do not self-assess or self-treat. |

---

## Owner

Aidan Pierce. Policy exceptions require written approval from Aidan Pierce logged in `compliance/evidence/POL-001/exceptions.md`.

---

## Review Cadence

Annual. Triggered review within 14 days of any event in §3.2.

---

## Evidence that this Policy Operates

Auditors should verify:

1. **`compliance/risk/register.md`** — current risk register with inherent scores, treatment status, residual scores, and review dates.
2. **`compliance/evidence/POL-009/quarterly-reviews.md`** — signed quarterly review log; git history confirms each review occurred on its stated date.
3. **`compliance/risk/threat-model-pos.md`** and **`compliance/risk/threat-model-camera.md`** — subsystem threat models referenced by the register.
4. **GitHub Actions run history** — `.github/workflows/gitleaks.yml` and `security.yml` pass/fail trend for the examination period.
5. **`compliance/evidence/POL-009/risk-treatments/`** — written treatment plans for any High (≥12) risks, with Aidan Pierce sign-off.
6. **This file's git history** — `git log --follow compliance/policies/risk-assessment-management.md`
