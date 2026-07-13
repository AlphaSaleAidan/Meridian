# Data Classification Policy
**Document ID:** POL-007
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder, US signing authority)
**Review Cadence:** Annual, or on any material change to data schema or secondary-use commitments
**Parent Policy:** [information-security-policy.md](./information-security-policy.md)

---

## Purpose

Define the four classification tiers that apply to all data created, collected, or processed by Meridian AI Business Solutions, map every known Meridian data class into those tiers, and specify the minimum handling controls required at each tier. This policy also surfaces two critical gaps — a retention-period inconsistency between the schema and the posture document, and an undisclosed secondary data-use purpose — that require legal decision before the next merchant onboarding.

Meridian is not SOC 2 certified. This policy is part of an internal control framework authored to support readiness for a future Type II examination.

---

## Scope

Applies to all data created, collected, stored, processed, or transmitted by any Meridian system or sub-processor, including:
- Data stored in Supabase project `kbuzufjxwflrutowwnfl` (AWS us-east-1)
- Data archived to Cloudflare R2 bucket `meridian-archives` via `src/workers/cold_storage.py`
- Data processed in-memory by Railway (FastAPI) or Contabo (Celery/Beat, Redis)
- Data processed on merchant-premises Jetson edge devices (`edge/`, `src/ai/reid/`)

---

## Procedure

### 3.1 Classification Tiers

#### Tier 0 — Public
Data intentionally published or suitable for unrestricted disclosure. No controls beyond basic integrity.

**Examples:** marketing copy, public API documentation, the Meridian sales training HTML (`docs/meridian-sales-training.html`), publicly accessible product descriptions.

**Handling:** No labelling required. May be shared freely. No encryption at rest required (though TLS in transit still applies to all web-served content).

---

#### Tier 1 — Internal
Data that is not intended for public release but whose accidental exposure causes no direct harm to merchants, end-customers, or Meridian's legal obligations.

**Examples:** internal playbooks (`docs/playbook/`), aggregated and fully-anonymised foot-traffic counts with no `person_id` (once de-identified), anonymised benchmark data, internal meeting notes, non-sensitive configuration values that do not include credentials.

**Handling:**
- Stored in version-controlled repositories (private GitHub) or Supabase with standard RLS
- Shared freely within Meridian; not sent to third parties without business justification
- Transmitted over TLS 1.2+

---

#### Tier 2 — Confidential
Business-sensitive data whose accidental exposure could damage merchant relationships, trigger regulatory inquiry, or cause material harm to Meridian. Includes most merchant business data.

**Examples:**
- POS transaction data: `transactions`, `daily_revenue`, `daily_product_performance`, `weekly_revenue` tables (Supabase) — sales totals, item mix, revenue aggregates
- Merchant and rep identity/PII: `business_users`, phone numbers in `phone_orders`, `phone_call_logs.caller_phone`
- CASL consent records: `casl_consent_records` — commercial email consent status, timestamps, implied-consent basis
- Compliance acceptances: `compliance_acceptances` (SHA-256 document hashes), `privacy_requests`
- Breach log: `breach_log` (24-month minimum retention per posture doc; Supabase `compliance.py:336`)
- Standard camera analytics (anonymous only): foot-traffic counts, dwell times, heatmaps, zone occupancy — **only when VIP face-match and demographics inference are both disabled**; once VIP or demographics are active the data escalates to Tier 3

**Handling:**
- AES-256 encryption at rest (Supabase managed)
- Access via service-role key only from authenticated Railway processes; no direct DB access for contractors without Aidan's written approval
- RLS policies enforced on all merchant-scoped tables
- TLS 1.2+ in transit; no unencrypted transmission
- Exported only in anonymised or aggregated form except to satisfy a privacy rights request; exports must be logged
- Retention per [data-retention-disposal.md](./data-retention-disposal.md) POL-008

---

#### Tier 3 — Restricted
Highest-sensitivity data whose exposure creates significant legal, regulatory, or reputational risk. Biometric data, cross-profile data, and financial credentials fall here.

**Sub-categories and sources:**

| Data Class | Table / Source | Sensitivity Basis |
|---|---|---|
| POS OAuth tokens (access + refresh) | `pos_connections` | AES-256-GCM encrypted at rest (`src/security/encryption.py`); compromise = full POS access for merchant |
| Camera↔POS cross-reference journeys | `customer_journeys` (`src/ai/reid/journey_tracker.py:145`) | Links `person_id` + `transaction_id` + `total_cents`; behavioural profile of individual end-customers |
| VIP face embeddings | On-edge (Jetson, `edge/`) + optional cloud sync | **Biometric data** under Quebec Law 25 and PIPEDA; requires explicit separate consent; never stored in Supabase without explicit scope |
| Camera analytics with demographics inference | `vision_visitors` (when demographics bucket populated) | Inferred sensitive characteristics; escalates from Tier 2 when active |
| Re-identification `person_id` across sessions | `vision_visitors`, `vision_events` | Persistent pseudonymous identifier linking sightings across time |
| Raw PAN, expiry, CVV (phone-pay path) | In-memory only, `card_on_phone.CardCapture` object, `src/api/routes/phone.py` | PCI DSS in-scope card data; **see open finding §3.3** |

**Handling:**
- Tier 3 access requires explicit per-request justification; access is logged
- No Tier 3 data exported to R2 or any cold store without written approval from Aidan Pierce
- Biometric data (VIP face embeddings) must not leave the merchant-premises Jetson without a signed biometric-data agreement with the merchant and explicit end-customer consent
- `customer_journeys` — accessible only to the owning merchant's service-role context; no cross-merchant queries permitted; RLS must be verified on each migration
- PCI data (phone-pay path) — handled per [encryption-cryptography.md](./encryption-cryptography.md) POL-004 and the open PCI finding in §3.3

---

### 3.2 Data Class → Tier Mapping (Summary)

| Data Class | Tier | Primary Store | Notes |
|---|---|---|---|
| Marketing / public docs | 0 — Public | GitHub (public) | — |
| Internal playbooks, de-ID aggregates | 1 — Internal | GitHub (private) | — |
| POS transaction data | 2 — Confidential | Supabase `transactions`, `daily_revenue` | — |
| Merchant PII (name, email, phone) | 2 — Confidential | Supabase `business_users` | — |
| Phone-order PII (caller phone, order detail) | 2 — Confidential | Supabase `phone_orders`, `phone_call_logs` | — |
| CASL consent records | 2 — Confidential | Supabase `casl_consent_records` | 3-year CASL retention |
| Compliance acceptances / breach log | 2 — Confidential | Supabase `compliance_acceptances`, `breach_log` | — |
| Anonymous camera counts (VIP/demo OFF) | 2 — Confidential | Supabase `vision_visitors` | See DECISION §3.4 on retention period |
| Camera re-ID `person_id` (no demographics) | 3 — Restricted | Supabase `vision_visitors`, `vision_events` | Persistent pseudonymous ID |
| Camera analytics with demographics | 3 — Restricted | Supabase `vision_visitors` | Sensitive inferences |
| Camera↔POS cross-reference journeys | 3 — Restricted | Supabase `customer_journeys` | Highest sensitivity |
| VIP face embeddings | 3 — Restricted Biometric | Jetson edge; no cloud by default | Biometric; see §3.3 |
| POS OAuth tokens | 3 — Restricted | Supabase `pos_connections` | AES-256-GCM at rest |
| Raw PAN / CVV (phone-pay) | 3 — Restricted / PCI | In-memory only (`card_on_phone`) | Open finding; see §3.3 |

---

### 3.3 Open Findings

**PCI — Raw PAN/CVV in phone-pay path (HIGH)**

`src/api/routes/phone.py` (routes `/twilio/pay/number`, `/twilio/pay/expiry`, `/twilio/pay/cvv`) temporarily holds raw card numbers, expiry dates, and CVV values in a `CardCapture` object in process memory (`cap.pan`, `cap.expiry`, `cap.cvv`). This makes the Railway FastAPI process PCI DSS in-scope. Controls required but not yet verified: end-to-end TLS (Twilio→Railway), no persistent logging of PAN/CVV, memory cleared immediately after charge via `clear_capture(call_sid)`, Railway process memory encrypted at rest (Railway SOC 2 guarantees). This is an open remediation item tracked in the risk register at `compliance/risk/risk-register.md`.

---

### 3.4 Retention-Period Inconsistency

## DECISION (Aidan + legal counsel required)

The Meridian Compliance Posture document (`docs/MERIDIAN_COMPLIANCE_POSTURE.md:76`) states camera analytics retention as **"30 days raw / 1 year aggregated."**

The actual Supabase schema (`supabase/migrations/20260501_004_vision_intelligence.sql:35`) sets:
```sql
expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '90 days')
```

These two numbers are inconsistent. The `cleanup_expired_visitors()` function (migration line 97) would enforce 90 days if scheduled — not 30 days. Additionally, `cold_storage.py` archives camera data to R2 but does not delete it from R2 on expiry, so the "90-day" figure applies only to Supabase hot storage.

**Decision required:** Which retention period is authoritative? Options:
1. **Adopt 30 days** — update the schema default to `INTERVAL '30 days'`, schedule `cleanup_expired_visitors()` via pg_cron, update posture doc and this policy. More conservative; preferred if targeting Quebec Law 25.
2. **Adopt 90 days** — update posture doc to 90 days, ensure this is disclosed in merchant privacy disclosures, schedule deletion in Supabase, implement R2 deletion on expiry.

Until this decision is made, this policy records the **schema value (90 days)** as the operative figure for Supabase hot storage, and notes that R2 cold objects have **no current deletion schedule** (open remediation item POL-008).

---

### 3.5 Resale-Tier Classification and Secondary-Use Disclosure Gap

## DECISION (legal counsel required — CRITICAL)

`src/workers/cold_storage.py` classifies archived data into tiers with the `resale_tier` attribute:

```python
"tier_a_pos": {"resale_tier": "premium", ...}   # line 77
"tier_b_vision": {"resale_tier": "premium", ...} # line 88
"tier_c_crossref": {"resale_tier": "premium", ...} # line 98
```

This means POS transaction data, camera analytics, and camera↔POS cross-reference data are structurally tagged for potential resale or secondary commercial use.

The signed merchant SLA (generated by `generate-sla-pdf.ts`) discloses only:

> "anonymized and aggregated Client Data for improving the Services"

This language **does not disclose** a secondary commercial-resale purpose. Under PIPEDA Principle 1 (Identifying Purposes), purposes must be identified at or before the time of collection. Under Quebec Law 25 (Bill 64) Article 8, a new purpose requires a new privacy impact assessment and notice. This is a **P2 (PIPEDA) / P4 (Quebec Law 25) gap**.

**Required actions before any resale activity:**
1. Retain Canadian privacy counsel to advise on disclosure requirements
2. Draft a supplemental purpose clause for the merchant SLA
3. Conduct a Privacy Impact Assessment (PIA) on the resale use case
4. Obtain explicit consent (Quebec Law 25 requires explicit consent for new purposes)
5. Update merchant-facing privacy policy to name resale as a purpose

No data classified `resale_tier: "premium"` or `resale_tier: "high"` may be shared with, sold to, or licensed to any third party until steps 1–5 are complete and Aidan Pierce has countersigned a revised disclosure.

---

## Roles

| Role | Responsibility |
|---|---|
| Aidan Pierce (Policy Owner) | Approve tier assignments, sign off on any Tier 3 data access or export, resolve DECISION items |
| Engineers (current: Aidan Pierce only in production) | Label data at creation per this policy; escalate ambiguous cases |
| Canada Admins (Nguyen, Cheung) | Handle only Tier 2 data within their granted scopes; no Tier 3 access without explicit approval |

---

## Owner

Aidan Pierce

---

## Review Cadence

Annual. Also triggered by: any new data class added to schema, any change to secondary-use commitments, any Quebec Law 25 enforcement guidance update, or any new camera feature.

---

## Evidence that this Policy Operates

Auditors should verify:
1. **`compliance/evidence/POL-007/tier-assignments.md`** — signed log of each data class's assigned tier, with date and approver.
2. **`compliance/evidence/POL-007/decision-log.md`** — record of DECISION items resolved (§3.4 retention period, §3.5 resale disclosure), with date and legal counsel reference.
3. **`supabase/migrations/20260501_004_vision_intelligence.sql`** — confirms the `expires_at` default value in the live schema.
4. **`src/workers/cold_storage.py`** — confirms `resale_tier` assignments in `ARCHIVE_TIERS`; auditors should compare against current merchant SLA language.
5. **This file's git history** — `git log --follow compliance/policies/data-classification.md`.

---

## Related Policies

- [information-security-policy.md](./information-security-policy.md) — POL-001 master policy
- [data-retention-disposal.md](./data-retention-disposal.md) — POL-008 retention periods and disposal procedures
- [encryption-cryptography.md](./encryption-cryptography.md) — POL-004 encryption controls by tier
- [vendor-third-party-management.md](./vendor-third-party-management.md) — POL-009 sub-processor handling of Tier 2/3 data
