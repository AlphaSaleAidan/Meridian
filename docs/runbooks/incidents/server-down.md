# SEV-1 — Server / surface down

Fires as: edge-watchdog "DOWN" email, portals unreachable, API 5xx, or a
customer/merchant report. Three distinct surfaces — identify which FIRST.

## First 5 minutes — scope

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://meridian.tips           # frontend (Contabo)
curl -s -o /dev/null -w "%{http_code}\n" https://canada.meridian.tips    # frontend (Contabo)
curl -s -o /dev/null -w "%{http_code}\n" https://api.meridian.tips/health # backend (Railway)
```

| Result | Surface down | Go to |
|---|---|---|
| Frontends dead, API 200 | Contabo edge box | §A |
| API dead, frontends 200 | Railway backend | §B |
| Everything dead | DNS / Contabo (api.meridian.tips proxies via Contabo nginx for some paths — test Railway directly in §B) | §A then §B |
| All 200 but users report errors | Supabase or a partial outage | §C |

**Phone impact note:** the 10 pool DIDs' Vapi serverUrl points at
`api.meridian.tips` (direct to Railway since 2026-08-06) — a Contabo outage
does NOT kill the phone fleet; a Railway outage DOES (see
[phone-fleet-down.md](phone-fleet-down.md)).

## §A Contabo edge box (209.126.80.45 — static frontends + nginx)

1. SSH in. If SSH is dead too → Contabo control panel, hard reboot the VPS,
   then re-check the curls (nginx and pm2 are configured to come back on boot;
   `pm2 save` was last run 2026-07-31).
2. If SSH works: `systemctl status nginx` → `systemctl restart nginx`.
   Check disk first if nginx won't start: `df -h` (full disk is the classic).
3. Frontend dist corrupted/missing → restore newest backup:
   `ls -t /tmp/meridian-dist-backup-*.tgz | head -1`, extract into
   `/root/Meridian/frontend/` and re-test.
4. Verify: both portal curls 200, then load one page in a browser (SW cache can
   mask — hard-reload).

## §B Railway backend (project miraculous-curiosity, auto-deploys from main)

1. `cd /root/Meridian && railway deployment list --service Meridian --environment production --json | head`
   — a `FAILED`/`CRASHED` top entry after a merge = bad deploy.
2. **Mitigate: roll back** — Railway dashboard → Deployments → previous
   SUCCESS deployment → Redeploy. (Faster than debugging forward; do it first.)
3. If the deploy is SUCCESS but /health 5xx: `railway logs --service Meridian
   --environment production | tail -50` — look for startup refusals (e.g. the
   multi-worker guard raising) or a bad env var from a recent change; unset the
   offending var (`railway variables --set` / dashboard) → auto-redeploy.
4. Verify: `/health` 200, then one signed assistant-request probe (see
   phone-fleet-down.md §Probe) — the phone fleet rides this service.

## §C Supabase (project kbuzufjxwflrutowwnfl)

1. https://status.supabase.com first — platform incident = wait it out; the
   backend fails per-request, not fatally.
2. If Supabase is green but queries fail: check for an accidental RLS/grant
   change (the 42501 pattern) — recent merges touching `migrations/`, then
   `scripts/compliance/collect_rls_evidence.py` (read-only posture check).
3. NEVER hand-fix prod schema under pressure without writing the SQL into a
   numbered migration file in the same hour — drift here caused week-long bugs.

## Close-out

Watchdog sends its own recovery email when probes pass. Timeline → memory;
if the root cause was a deploy, the failing commit gets a test before the
incident closes.
