# Audits

Durable archive for one-off investigations that produced findings worth keeping
but don't belong in a feature branch. Each audit is read-only at authoring
time — capturing state, not changing it.

## Index

| File | Date | Scope |
|---|---|---|
| [`2026-06-03-eval-track-audit.md`](2026-06-03-eval-track-audit.md) | 2026-06-03 | Issue #37 — `model-eval-harness` swarm + eval tracks. Verified: zero overlap with PR #34, no prod-schema drift, no latently-broken-against-prod code. Identified one signal blocker (DeepSeek JSON-mode → eval harness `success=0`) — tracked as task #27. |
| [`2026-06-03-contabo-prod-state-snapshot.tar.gz`](2026-06-03-contabo-prod-state-snapshot.tar.gz) | 2026-06-03 | Forensic snapshot of the Contabo box's `/root/Meridian` working tree captured BEFORE the PR #34 cherry-pick chain ran. Contents: `3eeeeca5` commit + diff, `git status --porcelain`, diff stat, full tracked-file diff (.patch), untracked-file inventory, canada-portal correlation. Used to verify the source of the 9-commit off-main P-series chain. |

## Recovery

Reproduce the snapshot:

```bash
tar xzf docs/audits/2026-06-03-contabo-prod-state-snapshot.tar.gz -C /tmp/
ls /tmp/contabo-prod-state-snapshot-20260603-073945/
```

## When to add an audit here

A read-only investigation that:

- Took non-trivial effort
- Produced findings someone will want to re-read in 3+ months
- Doesn't belong on any feature branch (no code change, just analysis)
- Otherwise would live in `/tmp` and get lost

Don't add ephemeral investigation notes — those stay in agent context.
