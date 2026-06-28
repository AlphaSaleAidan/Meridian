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
| 1 | Show RLS denies cross-tenant reads on every sensitive table | `vision_*`, `phone_*`, `schedule_*`, `sms_optout_tracking` carry `USING(true)` public policies; camera P0 fix absent from main | **F-Crit** (R-01) |
| 2 | Prove the denied path with a test | API BOLA test exists (`test_tenant_isolation_bola.py`); **RLS** denial test was deleted from main; new one authored, not yet run in CI | **F-High** |
| 3 | Is tenant isolation enforced on all service endpoints? | `enforce_service_member` partial (C1) | **F-Crit** (R-02) |
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
| 12 | Vulnerability management with SLAs + pen test? | scans non-blocking; no pen test booked | **F-Med** (R-11) + **F-High** (pen test) |
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
| 24 | Purpose disclosed (no undisclosed resale)? | `resale_tier:"premium"` undisclosed in SLA | **F-Crit** (R-04) |
| 25 | Subject rights fulfilled (incl. deletion)? | intake yes; deletion not automated; export incomplete | **F-High** |
| 26 | Biometric lawful basis + PIA? | none; VIP/demographics ready but off | **F-High** latent (R-05) |

## Tally
F-Crit ×4 · F-High ×7 · F-Med ×9 · F-Low ×4 · Pass ×5 (some with sub-gaps).

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
tokens, and a documented history of handling incidents correctly. It is **not** ready for a CPA examination
today: four critical findings (two access-control, one PCI, one privacy-disclosure) must close first. None
require new architecture — the correct patterns already exist in the codebase. Realistic path: close R0–R4
(weeks, mostly code Aidan merges) → re-score → Type I. Then operate the controls over a 3–6 month window for
Type II.
