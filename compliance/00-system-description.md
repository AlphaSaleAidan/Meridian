# Meridian — System Description (SOC 2 seed)

> **Status:** Draft v0.1 — 2026-06-28. Authored as the seed for the formal SOC 2 System Description the
> auditor will require. Grounded in the codebase at `origin/main` (HEAD `77bbf327`) of the
> `AlphaSaleAidan/Meridian` repository. Every claim here is traceable to source; see
> `/compliance/controls/` and `/compliance/evidence/` for the control + evidence mapping.

> **Readiness, not certification.** Meridian is **not** "SOC 2 compliant" or "SOC 2 certified." SOC 2 is an
> attestation issued by a licensed independent CPA firm. This document and the rest of `/compliance/`
> establish *readiness*. Current readiness is tracked in `gap-analysis.md`.

---

## DECISION BLOCK — Trust Services Criteria scope (Aidan to confirm)

The Charter (`CLAUDE.md §1.1`) sets the in-scope TSC. These are sensible defaults for Meridian's real risk
profile, but **TSC scope is Aidan's decision** and changes audit cost. Recorded here so the choice is explicit.

| Category | Charter default | Recommendation | Rationale |
|---|---|---|---|
| Security (CC1–CC9) | In scope | **Keep** (mandatory) | Always required. |
| Availability (A1) | In scope | **Keep** | SLA commits to **99.5% uptime** + 60-min data-freshness (signed SLA, `frontend/src/lib/generate-sla-pdf.ts:215-220`). Uptime is contractual. |
| Confidentiality (C1) | In scope | **Keep** | Financial + PII + video; confidentiality survives termination 3 yrs per SLA. |
| Processing Integrity (PI1) | In scope | **Defensible to defer** | Meridian computes financial figures from POS feeds — core to the product. But PI1 expands audit effort and reconciliation today covers **Square only** (`src/services/reconcile.py`). |
| Privacy (P1–P8) | In scope | **Defensible to defer** | Heavy existing PIPEDA/Law 25/CASL work maps onto P-series, but the camera↔POS↔identity overlay (`src/ai/reid/journey_tracker.py`) is the highest-sensitivity flow and carries open gaps (undisclosed resale purpose, unscheduled retention deletion). |

**Minimum-viable first report (faster / cheaper):** Security + Availability + Confidentiality. Add Privacy +
Processing Integrity in the next cycle. This still produces a usable Type I for enterprise diligence while
the two heavier criteria are remediated.

**Full-scope first report (recommended if seed/enterprise deals demand it):** all five. Higher effort; the
gap analysis below is written for the full five so either path is supported.

**→ SCOPE SELECTED (2026-06-28): all five criteria (full scope).** Confirmed via the scope-decision prompt.
Items unique to PI1/Privacy remain tagged so they can still be re-sequenced to a later cycle if priorities change.

---

## 1. Company & service overview

**Meridian AI Business Solutions** provides AI-driven business intelligence for retail/hospitality merchants
(including cannabis dispensaries). The platform ingests Point-of-Sale (POS) transaction data and, optionally,
in-store camera analytics, and computes revenue/operational analytics, forecasts, and an AI phone-ordering
agent. It is sold to US and Canadian merchants under signed SLAs.

Tenancy is **multi-tenant**, scoped by `org_id` (a business UUID). Multi-tenant isolation is the single most
important control objective and the locus of a prior, remediated cross-tenant write vulnerability (see §6 and
control `CC6.1-TENANT`).

## 2. System boundary (what the audit covers)

| Layer | Technology | Where it runs | Source of truth |
|---|---|---|---|
| Frontend | React / Vite SPA | Railway (primary) + a **manually built static `dist/`** for the Canada portal on the Contabo VPS | `frontend/`, `CONTEXT.md:12-13`, `docs/ARCHITECTURE.md:87-88` |
| Backend API | Python **FastAPI** (uvicorn, 4 workers) | Railway — `api.meridian.tips` | `src/api/app.py`, `Procfile`, `railway.toml` |
| Async compute | Celery (8 workers) + Celery Beat, DeerFlow, scraper, local Qwen LLM, Garry self-healing agent | **Contabo VPS** (209.126.80.45, St. Louis), managed by PM2 | `ecosystem.config.js` |
| Broker / cache | Redis (single node) | Contabo VPS | `src/workers/celery_app.py`, `CONTEXT.md:48` |
| Database | **Supabase** managed PostgreSQL (RLS), project `kbuzufjxwflrutowwnfl` | AWS us-east-1 (Supabase) | `supabase/migrations/`, `src/db/` |
| Camera edge | Docker Compose (YOLO + ByteTrack + ReID + CompreFace) | **Merchant-premises** GPU device (Jetson) | `edge/`, `src/ai/reid/`, `src/camera/` |
| Live video relay | Cloudflare Stream (WHIP/WHEP) | Cloudflare | `src/services/cloudflare_stream.py` |
| Cold archive | Cloudflare R2 + Backblaze B2 | Cloudflare / B2 | `src/workers/cold_storage.py`, `.dvc/config` |
| Integrations | POS (Square live; Clover/Toast built/gated), Telephony (Telnyx primary, Twilio fallback, Vapi demo), Email (Postal self-hosted + Resend), Payments (Stripe Connect + Square) | Subservice orgs | see `/compliance/vendors/` |

**Boundary note (must be resolved in the auditor's System Description):** the frontend is split — Railway for
most surfaces, but the Canada portal is a hand-built static `dist/` on Contabo (`CLAUDE.md:20-21`). The audit
boundary must state both. The backend deploys to Railway automatically on merge to `main`; migrations are
applied to the shared production Supabase **manually and deliberately** (`docs/ARCHITECTURE.md:88-89`).

## 3. Data processed (classes)

| Class | Examples | Sensitivity | Primary store |
|---|---|---|---|
| Financial / transaction | POS sales, totals, items, daily/hourly revenue | Confidential | Supabase (`transactions`, `daily_revenue`) |
| POS credentials | OAuth access/refresh tokens | Restricted | Supabase `pos_connections`, AES-256-GCM encrypted (`src/security/encryption.py`) |
| Identity / PII | merchant users, caller phone numbers, customer names on phone orders | Confidential | Supabase (`business_users`, `phone_orders`, `phone_call_logs`) |
| Camera analytics | foot-traffic counts, re-ID `person_id`, demographics buckets, optional VIP face-match | Confidential → Restricted (biometric when VIP/demographics on) | Supabase `vision_*`; embeddings stay on merchant edge, 90-day expiry |
| Camera↔POS cross-reference | `customer_journeys` linking `person_id` + `transaction_id` + `total_cents` | **Restricted (highest sensitivity)** | Supabase `customer_journeys` (`src/ai/reid/journey_tracker.py:145`) |
| Consent / compliance | CASL consent, doc acceptances (SHA-256), privacy requests, breach log | Confidential | Supabase `casl_consent_records`, `compliance_acceptances`, `privacy_requests`, `breach_log` |
| Card data (phone pay path) | raw PAN/CVV captured in memory in the Twilio DTMF flow | **Restricted — PCI scope** | in-memory only (`src/api/routes/phone.py:1573,1593,1612`) — see open finding H2 |

## 4. Principal control objectives (named)

1. **Tenant isolation** — a tenant can never read or write another tenant's rows, at the API tier *and* the
   database (RLS) tier. (`CC6.1-TENANT`, `CC6.1-RLS`)
2. **Authentication & least privilege** — only verified, authorised principals reach privileged operations;
   MFA on all admin access to subservice consoles. (`CC6.6-AUTH`, `CC6.6-MFA`)
3. **Confidentiality of data in transit & at rest** — TLS everywhere; POS credentials and DB encrypted.
   (`CC6.7-ENCRYPTION`)
4. **Change is controlled** — branch → PR → CI gates → human-approved merge → deploy. (`CC8-CHANGE`)
5. **Operations are monitored and incidents are handled** — detection, response, post-incident review.
   (`CC7-INCIDENT`, `CC7-VULNMGMT`)
6. **Availability is met** — backups, restore tests, capacity, the 99.5% SLA. (`A1-*`)
7. **Processing integrity** — computed financials reconcile to source POS truth. (`PI1-RECONCILE`)
8. **Privacy** — lawful basis, consent, retention, subject rights — especially the camera↔identity overlay.
   (`P-*`)

## 5. Subservice organizations (carve-out method)

Meridian relies on subservice organizations and uses the **carve-out method**: it relies on their SOC 2 / ISO
attestations and governs them through its vendor-management program (`CC9-VENDOR`). Meridian does not audit
their internals (e.g., Contabo data-center physical security is carved out). The full register is in
`/compliance/vendors/`. ~25 distinct external services are in use; only 7 are currently in the formal
sub-processor registry — closing that gap is a named remediation item.

## 6. Notable security history (written up honestly — a readiness strength)

- **Cross-tenant body-`org_id` bypass (CA-1/CA-2)** — client-supplied `org_id` in a POST body could override
  the authenticated tenant on endpoints that read `org_id` only from the body. **Remediated**: server now
  resolves body `org_id` and verifies membership (`src/api/auth.py:142-225`), with a negative test
  (`tests/api/test_tenant_isolation_bola.py`). A second BOLA layer (`enforce_service_member`) was added for
  `require_service_auth` endpoints; per-route rollout is **partial** (open finding C1).
- **Toast / Clover webhook & OAuth hardening** — documented detect→fix→verify cycles
  (`docs/SECURITY_SWEEP_2026-06-27.md`, `docs/POS_CONNECT_SESSION_2026-06-16.md`). Good IR evidence.

These are documented remediated risks; honest write-ups of handled incidents strengthen the audit, not weaken it.

## 7. Known open items at time of writing (see gap-analysis.md for the full list)

- **CC6.1-RLS (CRITICAL, R0-confirmed live 2026-06-28):** `phone_agent_config` (holds `pos_access_token`),
  `phone_orders` (customer PII), `phone_call_logs`, `schedule_*` are `USING(true)` **and grant `SELECT` to
  `anon`+`authenticated`** → readable with the public anon key (anonymous exposure). `vision_*` is org-scoped
  in prod (config-drift only — fix not in `main`). See `evidence/CC6.1-RLS/pg_policies_live_20260628.md`.
- **C1 BOLA (CRITICAL):** `require_service_auth` accepts any signed-up merchant session; `enforce_service_member`
  not yet threaded into every tenant-scoped handler.
- **H2 (HIGH, verified):** phone webhooks have **no signature validation** (confirmed — spoofable). Raw PAN/CVV
  capture exists in code (`phone.py:1573+`) but is **gated** behind `CARD_PAYMENT_ENABLED` (default off) + `pay_now`
  mode → likely inactive (pay-at-pickup norm); confirm the env flag in prod. (R-03a/R-03b, R4)
- **MFA:** no technical enforcement; relies on subservice console settings (org control, evidence needed).
- **Privacy:** retention-deletion function unscheduled; DSAR deletion not automated; `resale_tier:"premium"`
  on camera/journey data not disclosed to merchants in the SLA.

---

*Document owner: Aidan Pierce (sole US admin / signing authority). Canadian admins: Aidan Nguyen, Enoch Cheung.
Review cadence: quarterly, or on any material change to the system boundary.*
