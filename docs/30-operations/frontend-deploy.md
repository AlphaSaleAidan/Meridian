# Frontend Deploy Runbook — meridian.tips

`meridian.tips` is **static files served by nginx from `/root/Meridian/frontend/dist` on the Contabo box**. There is no CI deploy, no Vercel, no Railway. Every deploy is a manual build + dist swap. This procedure exists because the portal was clobbered three times (2026-06-08, 2026-06-12 ×2) by builds from the wrong source.

> Canada-surface feature truth lives in `docs/CANADA_PORTAL_TRUTH.md` — read it before changing anything under `frontend/src/pages/canada/`.

## The iron rules

1. **Build only from `main`.** Since PR #96 merged (2026-06-12), main is the single canonical source — the old `canada-portal-canonical` tag lineage is retired and STALE (it predates the SR-portal work). Reviewed-good states are tagged `canada-portal-YYYYMMDD` as restore points.
2. **Never build in or deploy from the `/root/Meridian` working tree.** Use a fresh worktree.
3. **`.env.local` is mandatory.** Copy `/root/Meridian/frontend/.env.local` into the build dir before `npm run build`, or Vite silently ships demo-mode with broken Supabase auth.
4. **Bump `CACHE_NAME` in `frontend/public/sw.js` to a dated value on every deploy** (e.g. `meridian-v4-20260612`). An unchanged name leaves stale shells stranded in browsers, making good deploys look like regressions.
5. **Backup before swap. Verify after swap. Trust nginx logs, not file mtimes.**

## Procedure

```bash
# 1. Clean worktree at main
cd /root/Meridian
git worktree add /tmp/frontend-deploy origin/main

# 2. Build with real env
cd /tmp/frontend-deploy/frontend
ln -s /root/Meridian/frontend/node_modules node_modules
cp /root/Meridian/frontend/.env.local .
# bump CACHE_NAME in public/sw.js to today's date before building
npm run build

# 3. Verify the build BEFORE deploying
grep -o 'index-[A-Za-z0-9_-]*\.js' dist/index.html
grep -c 'kbuzufjxwflrutowwnfl' dist/assets/index-*.js        # must be ≥1 (Supabase embedded, not demo-mode)

# 4. Swap with backup
LIVE=/root/Meridian/frontend; TS=$(date +%Y%m%d-%H%M%S)
cp -a /tmp/frontend-deploy/frontend/dist "$LIVE/dist.new"
mv "$LIVE/dist" "$LIVE/dist.bak-$TS"
mv "$LIVE/dist.new" "$LIVE/dist"

# 5. Verify what is actually being served
curl -s https://meridian.tips/ | grep -o 'index-[A-Za-z0-9_-]*\.js'   # must match step 3
tail -50 /var/log/nginx/access.log | grep -o 'index-[A-Za-z0-9_-]*\.js' | sort -u

# 6. Clean up the worktree
cd /root/Meridian && git worktree remove /tmp/frontend-deploy --force
```

## Known facts and traps

- **Concurrent sessions are the repeat offender.** If another terminal/agent "rebuilds the frontend to test something," it deploys whatever its tree holds over canonical. One writer at a time; check `git worktree list` and `ps aux | grep vite` before portal work.
- **Stale review surfaces** caused phantom regressions: old cloudflared tunnels / preview proxies serve frozen snapshots forever. Review on https://meridian.tips only, and compare the served bundle hash (step 5) against `docs/CANADA_PORTAL_TRUTH.md` before concluding anything regressed.
- **Service worker:** dated `CACHE_NAME` (rule 4) makes browser caches self-healing; users may still need one hard refresh immediately after a deploy.
- **Rollback** = the same swap with the newest `dist.bak-*`.
- US and Canada portals are intentionally different; "fixing" one to look like the other is a regression, not a cleanup.
