# Evidence — CC7-INCIDENT — incident response & monitoring

**v0.1 — 2026-06-28.** Policy: `/policies/incident-response-plan.md`.

## Worked precedents (real detect→fix→verify cycles — strong IR evidence)
1. **Toast webhook HMAC** — detect: events accepted without signature even when secret set
   (`docs/SECURITY_SWEEP_2026-06-27.md`); fix: `Toast-Signature` HMAC-SHA256 verified
   (`src/api/routes/webhooks.py:432-438`, PR #176); verify: live, fails-closed (503) while Toast not live.
2. **Clover/Square OAuth state-secret** — detect: ~75% callbacks 403 (4 workers, ephemeral state)
   (`docs/POS_CONNECT_SESSION_2026-06-16.md`); fix: shared `OAUTH_STATE_SECRET`, fail-closed in prod
   (`src/api/routes/oauth.py`); verify: probe 6/12 → 12/12. Commit `0247568b`.
3. **CA-1/CA-2 cross-tenant bypass** — see `CC6.1-TENANT`.

## Detection sources (real)
Sentry (`src/api/app.py:23-32`, `send_default_pii=False`); `security_events` table taxonomy
(`src/api/security/audit_log.py`: login_success, invalid_token, rls_violation_attempt, pos_credential_access,
admin_action, brute_force, prompt_injection); `/health` (`app.py:269`); Docker + Railway healthchecks; PM2.

## Living vuln tracker
`docs/SECURITY_SWEEP_2026-06-27.md` — 2 Critical / 2 High / 6 Medium / 7 Low with per-finding fixes. This is a
real control-improvement loop; keep it updated as findings close.

## Gaps
No on-call paging for core API (Telegram only on SEO engine) → R-18. No ticketing system. Author IRP now sets
severity tiers (mapped to SLA times) + notification path.

## Status 🟢 precedents + detection real; 🟡 formal IRP authored, alerting gap open.
