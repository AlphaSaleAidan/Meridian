# Meridian — SOC 2 Gap Analysis (source of truth for readiness %)

> **This file is the single source of truth for SOC 2 readiness.** Update it after every phase.
> Readiness ≠ compliance. Meridian is not SOC 2 compliant/certified; an independent CPA firm issues the
> attestation. This tracks how ready the controls are for that examination.
>
> **As of:** 2026-06-28 · **HEAD:** `77bbf327` (origin/main) · **Phase:** 0 (scope + gap) complete; Phase 1
> technical remediation authored-not-applied.

## How readiness is scored

Each criterion is scored 0–100% on control **design** (Type I lens): is the control defined, implemented, and
evidenced *at a point in time*? Type II (operated-over-window) readiness is lower across the board because the
observation window has not started. A criterion is **not** counted as "ready" until its evidence pointer in
`/compliance/evidence/<ID>/` resolves to a real artifact.

> **Caveat that caps confidence:** several RLS findings are read from migration **files**. The live Supabase
> `pg_policies` state must be queried before these scores are final. Where live state is unconfirmed, the
> score reflects the *worst-case* (the migration as written). Confirming live state is remediation task **R0**.

---

## Overall readiness

| Scope | Type I design readiness | Notes |
|---|---|---|
| **Security (CC1–CC9)** | **~46%** | Strong change-mgmt & auth foundations; RLS + BOLA + MFA are the holes. |
| **Availability (A1)** | **~50%** | Backups/archive exist; no tested restore, no DR plan, Contabo SPOF. |
| **Confidentiality (C1)** | **~45%** | Encryption strong; classification informal; secure-disposal-on-termination unimplemented. |
| **Processing Integrity (PI1)** | **~40%** | Square reconciliation exists; Clover/Toast none; mismatches log-only. |
| **Privacy (P1–P8)** | **~48%** | Rich CASL/consent/DSAR intake; deletion automation + resale disclosure are the gaps. |
| **WEIGHTED OVERALL** | **≈ 46%** | Honest mid-point: good bones, several critical access + privacy gaps before Type I is credible. |

**Headline:** Meridian is roughly **halfway** to Type-I readiness. Two CRITICAL access-control gaps
(RLS `USING(true)`, C1 BOLA) and the PCI/Twilio finding must close before any auditor accepts the system for
examination. None require new architecture — the patterns to fix them already exist in the codebase.

---

## Common Criteria (Security)

### CC1 — Control Environment — **40%**
| Item | State | Gap | Remediation | Owner | Status |
|---|---|---|---|---|---|
| Org chart / roles | Implicit (Aidan sole US admin; Nguyen+Cheung CA admins) | Not documented as a control | Org-chart + roles doc; HR/Personnel policy | Aidan | ⬜ authored in `/policies/hr-personnel-security.md` |
| Code of conduct | Absent | Required | Acceptable Use + code-of-conduct acknowledgment | Aidan | ⬜ |
| Background checks | Absent (solo + contractors) | Org control | Policy + per-contractor record | Aidan (human) | 🚩 flagged — cannot be coded |
| Board/management oversight | Absent | Required even solo | Lightweight quarterly security review Aidan signs | Aidan (human) | 🚩 ritual proposed in `/policies/risk-assessment.md` |

### CC2 — Communication & Information — **55%**
| Item | State | Gap | Remediation | Owner | Status |
|---|---|---|---|---|---|
| External commitments (SLA) | Strong — signed SLA with 99.5% uptime, 60-min data freshness, IR times, 60-day deletion (`generate-sla-pdf.ts`) | Controls must back each promise | Map SLA promises → controls (done in this file) | Aidan | 🟡 |
| Internal security comms | Ad hoc | Document responsibilities | Info-Security Policy distribution + ack | Aidan | ⬜ |

### CC3 — Risk Assessment — **45%**
| Item | State | Gap | Remediation | Owner | Status |
|---|---|---|---|---|---|
| Risk register | Now authored | Was absent | `/risk/register.md` (incl. fraud + tenancy isolation) | Aidan | 🟢 authored |
| Threat models | Now authored (POS, camera) | Was absent | `/risk/threat-model-pos.md`, `/risk/threat-model-camera.md` | Aidan | 🟢 authored |

### CC4 — Monitoring Activities — **35%**
| Item | State | Gap | Remediation | Owner | Status |
|---|---|---|---|---|---|
| Vuln scanning | Bandit/Safety/npm-audit in CI **but `\|\| true` (non-blocking)** (`.github/workflows/security.yml`) | Advisory only | Make scans blocking (or triage-gated) | Aidan | ⬜ R5 |
| Dependency audit | Present, non-blocking; deps mostly unpinned upper bounds | Pin + enforce | Lockfile enforcement + Dependabot/Renovate | Aidan | ⬜ |
| Pen test | None | Annual external pen test is the Type II norm | **Book third-party pen test** | Aidan (human) | 🚩 paid engagement |
| Log review cadence | Logs exist (Sentry, `security_events`) | No documented review cadence | Logging & Monitoring policy defines cadence | Aidan | 🟡 |

### CC5 — Control Activities — **50%**
| Item | State | Gap | Remediation | Owner | Status |
|---|---|---|---|---|---|
| Segregation of duties | Impossible solo | Must document compensating controls | Named in `/controls/CC5-SOD-COMPENSATING.md`: immutable git, mandatory PR review, CI gate, tamper-evident logs | Aidan | 🟢 authored |

### CC6 — Logical & Physical Access — **40%** *(the heavy block)*
| Item | State | Gap | Remediation | Owner | Status |
|---|---|---|---|---|---|
| **RLS least-privilege** | **`USING(true)` on `vision_*`, `phone_agent_config`, `phone_call_logs`, `phone_orders`, `sms_optout_tracking`, `schedule_*`** (`supabase/migrations/20260516_*`, `20260507_*`, `20260604_*`, `20260522_*`) — named "service role" but no `TO service_role` → public | **CRITICAL** | Drop wide-open policies; add `TO service_role` + org-scoped authenticated policies; **confirm live `pg_policies`** | Aidan | 🔴 migration authored in `/evidence/CC6.1-RLS/`, **not applied** |
| Camera P0 fix | Migration `20260624_camera_streaming_phase1.sql` + denial test exist in git history, **absent from main** | CRITICAL — fix may never run via `db push` | Restore migration to main; re-add CI denial test | Aidan | 🔴 R1 |
| **Tenant isolation (API)** | Body-`org_id` bypass remediated (`auth.py:142-225`); BOLA layer `enforce_service_member` **partial** | **CRITICAL (C1)** | Thread `enforce_service_member` into every `require_service_auth` tenant handler (`phone_dashboard`, `schedule`, `website`, `intelligence`, `stripe_connect`, `pos`) | Aidan | 🔴 R2 |
| `get_user_org_id()` | Called in `benchmark_snapshots` RLS (`20260501_006:30`) but **never defined** | HIGH — policy errors/denies | Define the function or rewrite policy | Aidan | ⬜ |
| `cline_*`/`merchant_health` RLS | `business_id = auth.uid()` never matches | MEDIUM — silent deny | Correct to membership lookup | Aidan | ⬜ |
| MFA | **No technical enforcement** anywhere | HIGH (CC6.1) | Enable + evidence MFA on Supabase/Railway/GitHub/Cloudflare consoles | Aidan (human) | 🚩 org control |
| Admin allowlist | `ADMIN_EMAILS` **hardcoded** in `auth.py:25-31` | MEDIUM — no audit trail, deploy-to-change | Move to DB-managed roles w/ RLS | Aidan | ⬜ |
| Encryption (transit) | Railway/Cloudflare TLS + HSTS (`security_headers.py:13`) | RTSP edge unencrypted; CSP `unsafe-inline/eval` | RTSPS/VPN decision; CSP hardening | Aidan | 🟡 |
| Encryption (at rest) | Supabase AES-256; POS tokens **AES-256-GCM** fail-closed (`encryption.py`) | Compliance doc wrongly says "Fernet/AES-128" | Correct doc; document key rotation | Aidan | 🟡 |
| Secrets mgmt | gitleaks pre-commit + CI; no committed secrets; `.env` gitignored | Contabo file-secrets (`/root/.secrets/*`) ungoverned; security env vars undocumented | Secrets inventory + rotation policy | Aidan | 🟡 |
| Provisioning/deprovisioning | Ad hoc | Quarterly access review absent | Access Control policy + signed quarterly review | Aidan (human) | 🚩 |
| Physical | Carved out to Contabo/Supabase/Railway/Cloudflare | Document reliance | Vendor register notes carve-out | Aidan | 🟢 |

### CC7 — System Operations — **45%**
| Item | State | Gap | Remediation | Owner | Status |
|---|---|---|---|---|---|
| Incident response | Worked examples (Toast/Clover detect→fix→verify); no formal IRP | Author IRP w/ severity tiers + paths | `/policies/incident-response-plan.md` | Aidan | 🟢 authored |
| Monitoring/alerting | Sentry + `/health` + PM2 + Docker healthcheck | No on-call paging; Telegram only on SEO engine | Wire core-API alerting | Aidan | ⬜ |
| Vuln management | Scans non-blocking; no SLA-to-fix by severity | Author Vuln Mgmt policy w/ SLAs | `/policies/vulnerability-management.md` | Aidan | 🟢 authored |

### CC8 — Change Management — **65%** *(strongest area)*
| Item | State | Gap | Remediation | Owner | Status |
|---|---|---|---|---|---|
| Branch→PR→merge | Real, enforced workflow; CI lint/typecheck/secret-scan blocking | Branch protection not in-repo; security scans non-blocking; prod deploy via **root SSH password** (`deploy-frontend.yml`) | Document the control; add branch protection evidence; key-based deploy user | Aidan | 🟢 policy authored; 🚩 SSH finding |
| Rollback | tar+sha256 backups (`backups/auth.py.*`) | Make it a documented procedure | Change Mgmt policy codifies it | Aidan | 🟢 |

### CC9 — Risk Mitigation — **40%**
| Item | State | Gap | Remediation | Owner | Status |
|---|---|---|---|---|---|
| Vendor mgmt | 7 of ~25 vendors registered | Register + cadence | `/vendors/` full register (authored) + review dates | Aidan | 🟢 authored, dates TBD |
| BC/insurance | None | Cyber/E&O insurance is a business decision | Flag for Aidan | Aidan (human) | 🚩 |

---

## Availability (A1) — **50%**
| Item | State | Gap | Remediation | Owner | Status |
|---|---|---|---|---|---|
| Backups | Nightly cold-storage archive to R2/B2 (`cold_storage.py`); Supabase PITR | **No tested restore** (untested backup ≠ control); HOT→archive does not delete | Quarterly restore test; document RPO/RTO | Aidan | ⬜ |
| DR / redundancy | Railway managed; **Contabo single node**, Redis no HA | DR plan absent; SPOF | `/policies/business-continuity-dr.md` (authored) + reduce SPOF | Aidan | 🟢 policy; ⬜ infra |
| Uptime vs SLA | 99.5% committed; **no uptime monitoring** | Add external uptime monitor + SLA tracking | Aidan | ⬜ |

## Confidentiality (C1) — **45%**
| Item | State | Gap | Remediation | Owner | Status |
|---|---|---|---|---|---|
| Classification | Informal (cold-storage tiers, posture doc) — inconsistent retention numbers (90 vs 30 days) | Formal scheme | `/policies/data-classification.md` (authored) | Aidan | 🟢 |
| Retention/disposal | `cleanup_expired_visitors()` exists **unscheduled**; R2 objects never deleted; 60-day termination delete unimplemented | HIGH | Schedule deletion (pg_cron/Celery); implement disposal | Aidan | ⬜ |

## Processing Integrity (PI1) — **40%**
| Item | State | Gap | Remediation | Owner | Status |
|---|---|---|---|---|---|
| Input validation | Pydantic at API; normalizer tolerant (`normalizer.py`) | No negative/duplicate guard | Add guards + dedup | Aidan | ⬜ |
| Reconciliation | **Square only** (`reconcile.py`, $1 tol, post-sync, log-only) | Clover/Toast none; mismatches not surfaced | Extend reconciliation; alert on mismatch; dashboard | Aidan | ⬜ |

## Privacy (P1–P8) — **48%**
| Item | State | Gap | Remediation | Owner | Status |
|---|---|---|---|---|---|
| Notice (P1) | No public privacy page found in routes | Publish privacy notice | Page + link | Aidan | ⬜ |
| Consent (P2/P3) | Strong: CASL guard, SHA-256 acceptance gate, Quebec cookie banner | IP not captured on acceptance; cookie consent localStorage-only | Capture IP; server-side cookie record | Aidan | 🟡 |
| Collection/use (P4) | **`resale_tier:"premium"` on camera/journey/txn data** (`cold_storage.py`) not disclosed; SLA says only "improve the Services" | **CRITICAL disclosure gap** | Disclose secondary purpose or stop resale classification | Aidan (legal) | 🔴 |
| Retention (P4) | 90-day `expires_at` + delete fn, **unscheduled** | HIGH | Schedule it | Aidan | ⬜ |
| Access/portability (P5/P6) | DSAR intake covers 6 rights; export omits txn/vision/journeys; deletion not automated | Complete export; automate deletion | Aidan | ⬜ |
| Camera↔identity (P-all) | VIP face-match (CompreFace) ready but not wired to prod loop; demographics buckets minors (`age_0-17`) | Biometric PIA + consent absent | PIA; jurisdiction/cannabis consent flow before enabling | Aidan (legal) | 🚩🔴 |

---

## Remediation priority queue (the critical path)

| ID | Priority | Item | Type | Owner |
|---|---|---|---|---|
| **R0** | P0 | Query live Supabase `pg_policies` to confirm which `USING(true)` policies are actually live | verify | Aidan/agent |
| **R1** | P0 | Restore camera P0 RLS-fix migration + denial test to main; fix `vision_*` RLS | code (PR) | Aidan |
| **R2** | P0 | Thread `enforce_service_member` into all tenant-scoped `require_service_auth` handlers (close C1 BOLA) | code (PR) | Aidan |
| **R3** | P0 | Fix `phone_*`, `schedule_*`, `sms_optout_tracking` RLS (`TO service_role` + org-scoped) | code (PR) | Aidan |
| **R4** | P1 | Twilio webhook signature validation; remove raw PAN/CVV from memory (Twilio `<Pay>`) | code (PR) | Aidan |
| **R5** | P1 | Make CI security scans blocking; pin deps | CI | Aidan |
| **R6** | P1 | Enable + evidence MFA on all subservice consoles | org | Aidan (human) |
| **R7** | P1 | Schedule retention deletion; implement 60-day termination disposal | code | Aidan |
| **R8** | P1 | Resolve camera/journey resale-purpose disclosure (legal) | legal | Aidan |
| **R9** | P2 | Book external pen test; decide cyber/E&O insurance; choose compliance-automation platform | business | Aidan (human) |

🚩 = human/organizational, cannot be coded. 🔴 = critical, open. 🟡 = partial. 🟢 = authored this session. ⬜ = not started.

*Update this file after every phase. It drives the readiness roadmap.*
