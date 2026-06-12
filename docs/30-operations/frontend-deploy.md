# Frontend Deploy Runbook — meridian.tips

`meridian.tips` is **static files served by nginx from `/root/Meridian/frontend/dist` on the Contabo box**. There is no CI deploy, no Vercel, no Railway. Every deploy is a manual build + dist swap. This procedure exists because the portal has been clobbered twice (2026-06-08, 2026-06-12) by builds from the wrong source.

## The iron rules

1. **Build only from the canonical tag lineage.** Until PR #90 merges, that is tag `canada-portal-canonical`. `main` does NOT contain the canonical Canada portal — a main-built deploy reverts the portal (this is exactly what happened on 2026-06-12 at 03:43).
2. **Never build in or deploy from the `/root/Meridian` working tree.** Use a worktree of the tag.
3. **`.env.local` is mandatory.** Copy `/root/Meridian/frontend/.env.local` into the build dir before `npm run build`, or Vite silently ships demo-mode with broken Supabase auth.
4. **Backup before swap. Verify after swap. Trust nginx logs, not file mtimes.**

## Procedure

```bash
# 1. Clean worktree at the canonical tag
cd /root/Meridian
git worktree add /tmp/frontend-deploy canada-portal-canonical

# 2. Build with real env
cd /tmp/frontend-deploy/frontend
ln -s /root/Meridian/frontend/node_modules node_modules
cp /root/Meridian/frontend/.env.local .
npm run build

# 3. Verify the build BEFORE deploying
grep -o 'index-[A-Za-z0-9_-]*\.js' dist/index.html          # expected: index-vfdQE9ED.js for the current tag
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

- **Current canonical bundle: `index-vfdQE9ED.js`** — byte-reproducible from the tag + `.env.local` (verified hash-identical twice). If your build of the tag produces a different hash, your inputs differ — stop and figure out why before deploying.
- **Service worker:** `sw.js` CACHE_NAME (`meridian-v3`) does not change between builds, so browsers can serve a stale cached shell after a deploy or restore. Hard-refresh to verify; consider bumping CACHE_NAME on deploys (PR #93 introduces the dated-name convention).
- **Concurrent sessions are the repeat offender.** If another terminal/agent "rebuilds the frontend to test something," it will deploy main/WIP content over canonical. Check `ls -la /root/Meridian/frontend/dist/index.html` mtime and nginx logs if the portal looks wrong.
- **Rollback** = the same swap with the newest `dist.bak-*`. Backups also live in `/root/meridian-backups/quarantine-20260612/frontend/` (older recovery-era builds).
- After PR #90 merges to main, update this runbook: the canonical source becomes `main` and this tag pinning can be retired.
- US and Canada portals are intentionally different; "fixing" one to look like the other is a regression, not a cleanup.
