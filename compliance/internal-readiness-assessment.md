# Meridian — Internal Readiness Assessment (mock audit)

> Phase 4. I walked the in-scope criteria **adversarially, as the auditor would**, and tried to break each
> control. Every finding is listed with a disposition. This is not the auditor's opinion — it is an internal
> dry run to drive readiness up before engaging a CPA firm. v0.1 — 2026-06-28. Overall design readiness ≈ 46%
> (see `gap-analysis.md`). Target before Phase 5: ≥ 85%.

## Method
For each criterion: (1) what would the auditor ask for? (2) does real evidence exist? (3) can I break it?
(4) finding + disposition. Findings graded **F-Crit / F-High / F-Med / F-Low / Pass**.

## Findings ledger

### Security — CC6 (Access) — the make-or-break block
| # | Auditor question | Finding | Grade |
|---|---|---|---|
| 1 | Show RLS denies cross-tenant reads on every sensitive table | **R0-confirmed live:** `phone_*` + `schedule_*` are `USING(true)` + `anon`/`authenticated` SELECT grant → **anonymous** read of `pos_access_token` + customer PII. (`vision_*` org-scoped in prod = config-drift only.) | **F-Crit** (R-01) |
| 2 | Prove the denied path with a test | API BOLA test exists (`test_tenant_isolation_bola.py`); **RLS** denial test was deleted from main; new one authored, not yet run in CI | **F-High** |
| 3 | Is tenant isolation enforced on all service endpoints? | Merchant routes covered; **rep-portal `billing/*`+`onboarding/*` authorize "any logged-in user"** (BOLA) — fix needs rep-auth model, not member-check (`evidence/CC6.1-TENANT/bola_triage.md`) | **F-High** (R-02) |
| 4 | MFA on all admin/privileged access? | none in code; subservice-console MFA unverified | **F-High** (R-09) |
| 5 | How is admin access granted/revoked + reviewed? | `ADMIN_EMAILS` hardcoded; no quarterly access review | **F-Med** (R-10) |
| 6 | Encryption in transit & at rest? | TLS+HSTS, AES-256-GCM tokens, Supabase AES-256 — strong | **Pass** (RTSP/CSP = F-Low) |
| 7 | Secrets not in code, scanned, rotated? | gitleaks blocking, no committed secrets; Contabo file-secrets ungoverned; rotation undocumented | **F-Low** |

### Security — CC1–CC5, CC7–CC9
| # | Question | Finding | Grade |
|---|---|---|---|
| 8 | Governance/oversight (even solo)? | roles documented; quarterly security-review ritual proposed, not yet operating | **F-Med** |
| 9 | Risk assessment with register + threat models? | authored this session (`/risk/`) | **Pass** (needs Aidan sign-off) |
| 10 | Segregation of duties / compensating controls? | named + independent (`CC5-SOD-COMPENSATING`); CI scans non-blocking weakens it | **F-Low** |
| 11 | Incident response plan + worked incidents? | IRP authored; real Toast/Clover/CA-1 precedents | **Pass** (alerting gap = F-Med) |
| 12 | Vulnerability management with SLAs + pen test? | **external pen test passed 2026-06-27** (need report artifact); CI scans still non-blocking | **Pass** (pen test) · **F-Med** (R-11, blocking scans) |
| 13 | Change management controlled & authorized? | branch→PR→CI→human merge — strong; branch-protection evidence + root-SSH deploy gaps | **Pass** (gaps = F-Med) |
| 14 | Vendor/subservice management? | register authored; 7→~25 vendors, DPAs/Law25 TRAs incomplete | **F-Med** (R-17) |

### Availability — A1
| # | Question | Finding | Grade |
|---|---|---|---|
| 15 | Backups exist **and restores are tested**? | backups real; **no tested restore** | **F-High** (R-08) |
| 16 | DR plan with RPO/RTO? | authored; Contabo SPOF, Redis no HA; RTO conflicts with SLA | **F-Med** (R-07) |
| 17 | Uptime monitored against the 99.5% SLA? | no uptime monitoring/SLA tracking | **F-Med** |

### Confidentiality — C1
| # | Question | Finding | Grade |
|---|---|---|---|
| 18 | Data classification + handling rules? | scheme authored; was informal; retention numbers inconsistent (90 vs 30d) | **F-Med** |
| 19 | Retention + secure disposal operating? | deletion fn unscheduled; R2 never purged; 60-day termination delete unimplemented | **F-High** (R-06) |

### Processing Integrity — PI1
| # | Question | Finding | Grade |
|---|---|---|---|
| 20 | Input validation on ingested data? | Pydantic + tolerant normalizer; no negative/dupe guard | **F-Med** (R-13) |
| 21 | Output reconciles to source? | Square only, log-only | **F-High** (R-14) |

### Privacy — P1–P8
| # | Question | Finding | Grade |
|---|---|---|---|
| 22 | Notice published? | no public privacy page found | **F-Med** |
| 23 | Consent captured + revocable? | CASL/acceptance/cookie strong; acceptance IP missing | **Pass** (F-Low) |
| 24 | Purpose disclosed (no undisclosed resale)? | Data *labeled* `resale_tier:"premium"` w/ resale intent in docstring, but **no active sale mechanism in code**; SLA permits only anonymized+aggregated. Latent governance gap, not an active violation. | **F-Med** (R-04) |
| 25 | Subject rights fulfilled (incl. deletion)? | intake yes; deletion not automated; export incomplete | **F-High** |
| 26 | Biometric lawful basis + PIA? | none; VIP/demographics ready but off | **F-High** latent (R-05) |

## Tally (after R0 live verification + corrections)
**F-Crit ×1** (the phone_/schedule_ anon RLS exposure — `pos_access_token` + customer PII readable with the
public anon key) · F-High ×8 · F-Med ×10 · F-Low ×4 · Pass ×6. R0 retired the other criticals: vision_* and the
financial/PII tables are isolated in prod; the resale finding is latent (no active sale mechanism), not active.

## The critical path to ≥85% (in order)
1. **R0** confirm live `pg_policies` (turns finding #1 from worst-case to actual).
2. **R1+R3** fix RLS wide-open + restore camera P0 + run the RLS denial test in CI → clears #1, #2.
3. **R2** finish `enforce_service_member` rollout → clears #3.
4. **R4** Twilio signature + remove raw PAN/CVV → clears the PCI/H2 finding.
5. **R6** MFA enablement + evidence → clears #4.
6. **R7** schedule retention deletion + implement disposal → clears #19, helps #25.
7. **R8** quarterly restore test → clears #15.
8. **R5** blocking CI scans + dep pinning → clears #12 (partial), strengthens #10.
9. **R8 (legal)** resale-purpose disclosure decision → clears #24 (the privacy F-Crit).
10. Book pen test; finish vendor register dates + DPAs; publish privacy notice.

## Honest verdict
Meridian has **good bones** — real auth, strong change management, genuine privacy/CASL machinery, encrypted
tokens, org-scoped RLS on the core financial/PII/biometric data (R0-confirmed), and a documented history of
handling incidents correctly. After live verification the picture is **better than the file-based scan
suggested**: the single live CRITICAL is the `phone_*`/`schedule_*` tables being readable with the public anon
key (`pos_access_token` + customer PII) — a contained, well-understood fix (R3). The next tier is the PCI/Twilio
finding (R4) and the rep-authorization model for the billing/onboarding BOLA (R2, needs a product decision).
None require new architecture. Realistic path: close R3/R4 + decide R2's model (mostly code Aidan merges) →
re-score (expect ≥70%) → Type I → operate controls over a 3–6 month window → Type II.
