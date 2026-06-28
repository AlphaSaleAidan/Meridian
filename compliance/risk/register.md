# Meridian — Risk Register (CC3)

> Living risk register for SOC 2 Risk Assessment (CC3). Likelihood/Impact on 1–5; Score = L×I. Treatment:
> Mitigate / Accept / Transfer / Avoid. Owner: Aidan Pierce unless noted. **v0.1 — 2026-06-28.**
> Review cadence: quarterly + on any major change. The remediated cross-tenant write history is recorded
> honestly — a handled-correctly risk is a readiness *strength*, not a liability.

## Scoring key
L/I 1=rare/negligible · 2=unlikely/minor · 3=possible/moderate · 4=likely/major · 5=almost-certain/severe.
Score ≥15 = critical (treat now); 8–14 = high; 4–7 = medium; ≤3 = low.

## Register

| ID | Risk | Category | L | I | Score | Treatment | Control / Evidence | Status |
|---|---|---|---|---|---|---|---|---|
| R-01 | **ANONYMOUS read exposure (R0-confirmed live):** `phone_agent_config` (`pos_access_token`), `phone_orders` (customer PII), `phone_call_logs`, `schedule_*` are `USING(true)` + `SELECT` granted to `anon`/`authenticated` → readable with the public anon key. (`vision_*` is org-scoped in prod = config-drift only.) | Tenant isolation | 4 | 5 | **20** | Mitigate | `CC6.1-RLS`; `evidence/CC6.1-RLS/pg_policies_live_20260628.md`; fix migration authored (drop+`TO service_role`+REVOKE), **not applied**; R3 | 🔴 OPEN |
| R-02 | **BOLA on `require_service_auth` endpoints (C1)** — any signed-up merchant session reaches tenant-scoped handlers lacking `enforce_service_member` | Tenant isolation | 4 | 5 | **20** | Mitigate | `CC6.1-TENANT`; `docs/SECURITY_SWEEP_2026-06-27.md`; **R2** | 🔴 OPEN (partial) |
| R-03 | **PCI exposure** — raw PAN/CVV held in app memory in Twilio DTMF pay path; no Twilio webhook signature validation | Payment/PCI | 3 | 5 | **15** | Mitigate/Avoid | `CC6.7`; **R4** move to Twilio `<Pay>`, add signature check | 🔴 OPEN |
| R-04 | **Secondary-use governance gap (latent)** — archive tiers are *labeled* `resale_tier:"premium"` and the `cold_storage.py` docstring states resale intent ("resale packaging", "resale-ready"), surfaced via `archives.py`. **No active data-sale mechanism found in code.** SLA 5.3 permits only *anonymized + aggregated* use that "cannot identify…any individual" — but `customer_journeys` (person_id+txn) + camera data are identity-linked. So resale of those tiers, if ever activated, would exceed the SLA. | Privacy/Legal | 2 | 5 | **10** | Mitigate (legal) | `P-PRIVACY`; **R8** legal review before any resale; do not activate resale of identity-linked tiers without disclosure | 🟡 latent |
| R-05 | **Biometric over-collection** — VIP face-match (CompreFace) + demographics (incl. `age_0-17` minors) without PIA or biometric consent flow; cannabis clients raise stakes | Privacy/Biometric | 3 | 5 | **15** | Mitigate/Avoid | `P-PRIVACY`; features default OFF; VIP not yet wired to prod loop; **PIA required before enabling** | 🟡 latent |
| R-06 | **Retention non-enforcement** — 90-day `cleanup_expired_visitors()` unscheduled; HOT→archive never deletes; R2 objects never purged; 60-day termination delete unimplemented | Privacy/Confidentiality | 4 | 3 | **12** | Mitigate | `C1-CLASSIFICATION`; **R7** schedule deletion | 🔴 OPEN |
| R-07 | **Contabo single point of failure** — Celery, Redis, local LLM, Garry, Canada frontend all on one node; Redis no HA | Availability | 3 | 4 | **12** | Mitigate/Accept | `A1`; DR plan authored; reduce SPOF / Redis HA | 🟡 |
| R-08 | **Untested backups** — nightly archive to R2/B2 + Supabase PITR but no restore ever tested | Availability | 3 | 4 | **12** | Mitigate | `A1-BACKUP`; quarterly restore test | 🔴 OPEN |
| R-09 | **No MFA enforcement** on admin access to Supabase/Railway/GitHub/Cloudflare consoles | Access | 3 | 4 | **12** | Mitigate | `CC6.6-MFA`; **R6** enable + evidence | 🚩 org |
| R-10 | **Hardcoded `ADMIN_EMAILS`** in source — access changes need a deploy; no audit trail; no runtime revoke | Access | 3 | 3 | **9** | Mitigate | `CC6.6-AUTH`; move to DB roles | ⬜ |
| R-11 | **Non-blocking CI security scans** — bandit/safety/npm-audit `\|\| true`; a known-vuln dep can merge | Vuln mgmt | 3 | 3 | **9** | Mitigate | `CC7-VULNMGMT`; **R5** make blocking | ⬜ |
| R-12 | **Prod deploy via root SSH password** (`deploy-frontend.yml`) to Contabo | Access/Change | 2 | 4 | **8** | Mitigate | `CC8-CHANGE`; key-based non-root deploy user | ⬜ |
| R-13 | **Fraud — manipulated POS feed** drives wrong financial analytics (negative/duplicate txns pass the normalizer) | Processing integrity/Fraud | 3 | 3 | **9** | Mitigate | `PI1-RECONCILE`; reconciliation Square-only; add guards + extend | ⬜ |
| R-14 | **Reconciliation blind spots** — Clover/Toast unreconciled; mismatches log-only, never surfaced | Processing integrity | 3 | 3 | **9** | Mitigate | `PI1-RECONCILE` | ⬜ |
| R-15 | **Ungoverned file-secrets on Contabo** (`/root/.secrets/*.env`) — no rotation, no access logging | Secrets | 2 | 4 | **8** | Mitigate | `CC6.6-SECRETS`; secrets inventory + rotation | 🟡 |
| R-16 | **`get_user_org_id()` undefined** — `benchmark_snapshots` RLS errors or silently denies | Access/Reliability | 3 | 2 | **6** | Mitigate | define fn or rewrite policy | ⬜ |
| R-17 | **Sub-processor sprawl** — ~25 vendors, only 7 registered; DPAs/Law 25 TRAs incomplete | Vendor | 3 | 3 | **9** | Mitigate | `CC9-VENDOR`; `/vendors/` register | 🟡 |
| R-18 | **No on-call alerting** for core API — incidents detected late | Operations | 3 | 3 | **9** | Mitigate | `CC7-INCIDENT`; wire paging | ⬜ |
| R-19 | **No cyber/E&O insurance** | Business/Transfer | 2 | 4 | **8** | Transfer | flag to Aidan | 🚩 |
| R-20 | **Single-operator key-person risk** (Aidan sole US admin/signing authority) | Org/BC | 2 | 4 | **8** | Mitigate/Accept | document succession in BC/DR; CA admins as partial redundancy | 🚩 |

## Documented, remediated risks (readiness strengths — write up honestly)
- **CA-1/CA-2 cross-tenant body-`org_id` bypass** — detected (live 200 on cross-tenant POST), fixed
  (`src/api/auth.py:142-225`), verified (`tests/api/test_tenant_isolation_bola.py`). Canonical example for CC6.
- **Toast webhook HMAC** + **Clover/Square OAuth state-secret** — full detect→fix→verify cycles
  (`docs/SECURITY_SWEEP_2026-06-27.md`, `docs/POS_CONNECT_SESSION_2026-06-16.md`). IR evidence.

## Treatment owner & cadence
All open items owned by Aidan Pierce. The risk register is reviewed at the **quarterly documented security
review** (see `/policies/risk-assessment-management.md`), which also serves the CC1 management-oversight ritual.
