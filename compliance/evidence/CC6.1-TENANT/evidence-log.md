# Evidence — CC6.1-TENANT — API tenant isolation

**v0.1 — 2026-06-28.** Control: `/compliance/controls/CC6.1-TENANT.md`.

## Type I evidence (point-in-time, real)
| Artifact | Location | Proves |
|---|---|---|
| Server-side JWT verification | `src/api/auth.py:42-62` | identity comes from verified token, not client input |
| Body-`org_id` resolution + membership check | `src/api/auth.py:142-225` | client-supplied `org_id` cannot override authenticated tenant |
| Membership lookup | `src/api/auth.py:87-139` | owner/member check against `business_users` |
| Second BOLA layer | `src/api/auth.py:313` (`enforce_service_member`) | service-auth endpoints re-check membership |
| **Negative test (existing, real)** | `tests/api/test_tenant_isolation_bola.py` | non-member → 403 **and side effect does not run** (`assert db.updates == []`) |

## Remediated incident (write-up for auditor)
CA-1/CA-2 body-`org_id` bypass — detect (live 200 on cross-tenant POST) → fix (`auth.py:142-225`, commit
`dfd864e9`) → verify (`test_tenant_isolation_bola.py`). Canonical CC6 remediation story.

## Open gap (C1, R-02)
`enforce_service_member` not yet in every tenant-scoped `require_service_auth` handler
(`phone_dashboard.py`, `schedule.py`, `website.py`, `intelligence.py`, `stripe_connect.py`, `pos.py`) —
`docs/SECURITY_SWEEP_2026-06-27.md:33-46`. Also confirm `TENANCY_ENFORCEMENT_DISABLED` is unset/false in prod.

## Type II (collect over window)
Per-route denial matrix (extend the BOLA test to every tenant-scoped route); CI run records over time.

## Status 🟡 partial — foundation strong, C1 rollout incomplete.
