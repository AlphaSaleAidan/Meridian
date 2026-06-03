# Per-session worktree workflow

## Why this exists

Multiple concurrent sessions (Claude Code, other agents, manual SSH) sharing one `git checkout` of `/root/Meridian` cause real, reproducible problems:

1. **Branch-state race.** Session A switches to `swarm-upgrade`. Session B (in the same `/root/Meridian` shell) runs `git commit` thinking it's on `main`. The commit lands on `swarm-upgrade`. This happened on 2026-06-03 — two fold-in commits intended for `review/canada-auth-revert` landed on `pos-beta-wiring` because another session had switched HEAD in between bash invocations.
2. **Dirty-tree contamination.** Session A leaves uncommitted edits to a file. Session B's `git stash pop` (after switching branches) pulls Session A's work into Session B's branch. Or rsyncs/copies see Session A's WIP and treat it as their own scope.
3. **Pre-commit hooks race.** The frontend `tsc` hook runs against the working tree. If Session A has WIP for file X and Session B is trying to commit unrelated file Y, the hook sees the combined state — Session B's commit blocks on Session A's type errors.

Symptoms: commits on the wrong branch, dirty files appearing in surprising PRs, hooks failing on code you didn't write. Root cause: shared mutable state.

## The rule

**Every session that's going to make commits MUST work in its own dedicated `git worktree`, never in `/root/Meridian` directly.**

`/root/Meridian` is reserved for:

- Long-running pinned branches (e.g. `swarm-upgrade` for the live POS development)
- Read-only inspection (`git log`, `git diff`, `git show`)
- Operations that explicitly need the canonical tree (e.g. running pm2-managed services)

It is **not** for new feature work, refactors, or commit production.

## Workflow

### Create a session worktree

```bash
cd /root/Meridian
scripts/session-worktree.sh new my-feature
# or pick a non-main base:
scripts/session-worktree.sh new pos-fix swarm-upgrade
```

This:

1. Fetches the base branch from origin.
2. Creates a new branch `session/my-feature` off that base.
3. Creates a worktree at `/tmp/meridian-my-feature/`.
4. Symlinks `frontend/node_modules` from `/root/Meridian` so the pre-commit `tsc` hook works without running `npm install` again.
5. Prints the next steps.

### Work in the worktree

```bash
cd /tmp/meridian-my-feature
# edit files, run tests, etc.
git add <paths> && git commit -m "..."
git push -u origin session/my-feature
gh pr create --base main --head session/my-feature
```

The worktree has its own `HEAD`, its own dirty file scope, its own staging area. Other sessions on `/root/Meridian` cannot see your in-flight work, and you cannot see theirs.

### Tear down

```bash
cd /root/Meridian
scripts/session-worktree.sh rm my-feature
```

This refuses to remove a worktree with uncommitted changes — push or stash first. Then:

1. Removes the symlinked `node_modules`.
2. Removes the worktree at `/tmp/meridian-my-feature/`.
3. Deletes the local branch `session/my-feature` if it has zero commits beyond `origin/main` (it was never used). Otherwise prints a manual cleanup command — you probably opened a PR from it.

### List active worktrees

```bash
scripts/session-worktree.sh list
```

Shows all worktrees in this repo, including `/root/Meridian` itself.

## Caveats

- **Modifying `frontend/node_modules`** (e.g. running `npm install` in the worktree to add a dep) writes through the symlink to `/root/Meridian/frontend/node_modules`. That's usually what you want, but it means concurrent sessions can race on `npm install` if multiple sessions install at once. If you're changing deps, do it in `/root/Meridian` directly (briefly) or quiesce other sessions first.
- **The pre-commit hook** runs against the worktree's working tree. If you haven't symlinked `node_modules`, the hook errors with "This is not the tsc command you are looking for." The script symlinks for you, but if you delete the symlink, restore it before committing.
- **Branch names** are forced to `session/<safe-name>`. If you need an unprefixed branch (e.g. `feature/foo` for naming convention), create the worktree manually:
  ```bash
  git worktree add -b feature/foo /tmp/meridian-foo origin/main
  ```
  The script's automation (symlink, refuse-to-rm-if-dirty) is convenience — `git worktree` directly is always available.

## What this does NOT do

- It does NOT migrate existing dirty work out of `/root/Meridian`. If `/root/Meridian` is currently full of WIP, that work stays there until somebody explicitly moves it (e.g. by rsyncing into a fresh worktree and reverting `/root/Meridian` to a clean state).
- It does NOT enforce the rule. A session can still `cd /root/Meridian && git commit`. The rule is a discipline; this script is the path of least resistance for following it.
- It does NOT replace `git worktree` as the underlying primitive — it's a thin convenience wrapper around it.

## Related

- `git worktree` man page: https://git-scm.com/docs/git-worktree
- Internal feedback memory: `branch-verify-before-commit` (origin: 2026-06-03 cross-session race where commits landed on the wrong branch).
