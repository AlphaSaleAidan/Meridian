# Evidence — P-PRIVACY — privacy (P1–P8)

**v0.1 — 2026-06-28.** Policies: `/policies/data-classification.md`, `/policies/data-retention-disposal.md`,
`/policies/vendor-third-party-management.md`. Threat model: `/risk/threat-model-camera.md`.

## Type I evidence (real — substantial existing work)
| Control | Location | Maps to |
|---|---|---|
| CASL consent guard (express/implied, instant unsubscribe) | `src/compliance/casl_guard.py` | P2/P3 (choice/consent) |
| SMS CASL (STOP/HELP/START, sender id) | `services/phone_agent/casl_compliance.py` | P2/P3 |
| Document acceptance gate (SHA-256 proof) | `src/compliance/acceptance_gate.py`; `src/api/routes/compliance.py:102` | P3 |
| DSAR intake (6 rights) | `src/api/routes/compliance.py:207` | P5/P6 (access/portability) |
| Quebec-aware cookie banner | `frontend/.../CookieConsentBanner.tsx` | P2 |
| Breach pipeline (72h CAI) | `src/api/routes/compliance.py:363`; `breach_log` | P8 (monitoring/enforcement) |
| Camera retention schema | `vision_visitors.expires_at = now()+90d`; `cleanup_expired_visitors()` | P4 (retention) |
| Defaults-off sensitive analytics | `src/api/routes/vision.py:46-50` | P4 (collection limitation) |

## CRITICAL gaps
- **P2/P4 — undisclosed secondary purpose:** `cold_storage.py` tags camera/journey/transaction data
  `resale_tier:"premium"`, but the signed SLA discloses only "anonymized and aggregated…to improve the
  Services." Resale is not disclosed → PIPEDA Identifying Purposes / Law 25 violation risk (R-04). **Legal
  decision required before any resale.**
- **P4 — retention not enforced:** `cleanup_expired_visitors()` is **unscheduled** (no pg_cron/Celery); R2
  objects never purged; 60-day termination deletion unimplemented (R-06). Posture doc says 30d, schema says
  90d — reconcile.
- **P5/P6 — incomplete rights:** DSAR `deletion` not automated; export omits transactions/vision/journeys.
- **Biometric (P-all):** VIP face-match (CompreFace) + minor-age buckets without PIA or biometric consent flow
  (R-05). Features default off and VIP not wired to prod loop — but a PIA + jurisdiction/cannabis consent flow
  is mandatory **before** enabling.
- **P1 — notice:** no public privacy page found in frontend routes.
- `data_inventory` table referenced (`compliance.py:348`) but **no migration creates it**.

## Status 🔴 strong consent/CASL bones; disclosure + retention-enforcement + biometric PIA are the blockers.
Privacy is defensible to defer to the next cycle under the minimum-viable scope (see scope DECISION).
