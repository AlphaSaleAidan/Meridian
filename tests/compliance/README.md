# SOC 2 prebuilt control tests

Automated checks that *prove* controls instead of describing them. Offline
(no live services), run on every PR by `.github/workflows/compliance.yml`,
plus a weekly scheduled run that adds read-only live collectors and uploads
an evidence bundle (400-day retention — covers a Type II window).

Companion docs (system description, policies, gap analysis) live in the
`/compliance` package (PR #196). This suite is the enforcement layer.

## Control map

| Control | File | What it proves |
|---|---|---|
| CC6.1 | `test_cc6_1_rls_migrations.py` | Migrations can't (re)introduce `USING(true)`-to-anon policies or RLS-less tables (the PR #198 incident shape). Known migration↔live drift is baselined and may only shrink. |
| CC6.1 live | `scripts/compliance/collect_rls_evidence.py` | Prod `pg_policies` + grants posture, timestamped; fails on anon exposure. |
| CC6.6 | `test_cc6_6_route_auth_matrix.py` | Every route is authenticated or in the reviewed public baseline (`public_endpoint_baseline.yaml`, a ratchet: new public routes fail CI, stale entries fail CI, the `unreviewed` bucket may only shrink). Money-path webhooks (Vapi / Stripe / Square) fail closed without signatures. |
| CC6.7 / CC6.8 | `test_cc6_7_cc6_8_data_protection.py` | No plaintext `http://` calls to external services; no PAN/CVV persistence (last-4 only). |
| CC8.1 | `test_cc8_change_management.py` | Secret scanning, static security analysis, syntax gate, and this suite stay wired into CI with the right triggers. |
| P / CC7 | `test_p_a1_pi1_platform_controls.py` | DSAR intake public, data export admin-gated, unsubscribe live, CASL guard intact, breach register gated. |
| A1 | same + `scripts/compliance/collect_backup_evidence.py` | Archive tooling present; live backup/PITR freshness (≤48h) with violations failing the run. |
| PI1 | same | Payment reconciliation module present. |

## The ratchet idea

Where the platform isn't clean yet, the current state is frozen in an
explicit, reviewed baseline (public endpoints, RLS migration drift) and CI
fails on ANY regression — while every remediation forces the baseline to
shrink (stale entries fail too). Readiness can only move one direction.

Burn-down lists:
- `public_endpoint_baseline.yaml` → `unreviewed:` (34 endpoints at freeze)
- `test_cc6_1_rls_migrations.py` → `KNOWN_RLS_MIGRATION_DRIFT` (6 tables)

## Reports

`scripts/compliance/readiness_report.py` renders the latest run into a
per-control markdown snapshot with a **test-backed readiness %** — stricter
than the design-readiness % in `compliance/gap-analysis.md` because only
running checks count.
