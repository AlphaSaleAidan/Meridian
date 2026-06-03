#!/usr/bin/env bash
# Per-session git worktree helper for /root/Meridian.
#
# Why this exists:
#   Multiple concurrent Claude Code (and other) sessions all sharing
#   /root/Meridian's working tree race each other — uncommitted edits
#   from one session show up in another, branch switches in one session
#   shuffle dirty files in another, and pre-commit hooks fire against
#   whoever happens to be there. This script gives each session its
#   own isolated worktree with its own HEAD and dirty-file scope.
#
# Usage:
#   scripts/session-worktree.sh new <session-name> [base-branch]   # create
#   scripts/session-worktree.sh list                                # list
#   scripts/session-worktree.sh rm <session-name>                   # remove
#   scripts/session-worktree.sh path <session-name>                 # print path
#   scripts/session-worktree.sh check                               # is THIS worktree safe to npm-install?
#
# Examples:
#   scripts/session-worktree.sh new my-feature              # off origin/main
#   scripts/session-worktree.sh new pos-fix swarm-upgrade   # off local swarm-upgrade
#   scripts/session-worktree.sh list
#   scripts/session-worktree.sh rm my-feature
#   cd /tmp/meridian-my-feature && scripts/session-worktree.sh check

set -e

REPO_ROOT="${REPO_ROOT:-/root/Meridian}"
WORKTREE_BASE="${WORKTREE_BASE:-/tmp}"

usage() {
    cat <<'EOF'
Usage:
  session-worktree.sh new <session-name> [base-branch]
  session-worktree.sh list
  session-worktree.sh rm <session-name>
  session-worktree.sh path <session-name>
  session-worktree.sh check       # run inside a worktree: is npm-install safe here?

Env vars:
  REPO_ROOT     (default: /root/Meridian)
  WORKTREE_BASE (default: /tmp)

Worktree path: $WORKTREE_BASE/meridian-<name>
Branch name:   session/<name>

See docs/SESSION-WORKTREE.md for the full workflow + rationale.
EOF
}

sanitize() {
    # Lowercase, replace anything outside [a-z0-9._-] with '-'
    echo "$1" | tr 'A-Z' 'a-z' | sed 's/[^a-z0-9._-]/-/g'
}

cmd_new() {
    local name="$1"
    local base="${2:-origin/main}"
    [ -z "$name" ] && { echo "session-name required" >&2; usage; exit 2; }

    local safe; safe=$(sanitize "$name")
    local branch="session/$safe"
    local path="$WORKTREE_BASE/meridian-$safe"

    if [ -d "$path" ]; then
        echo "⚠ worktree path already exists: $path" >&2
        echo "  use a different name, or run: $0 rm $safe" >&2
        exit 3
    fi

    cd "$REPO_ROOT"

    # If base is on origin/*, refresh it first.
    if [[ "$base" == origin/* ]]; then
        local upstream_branch="${base#origin/}"
        echo "→ fetching $upstream_branch from origin..."
        git fetch origin "$upstream_branch" >/dev/null 2>&1
    fi

    echo "→ creating worktree at $path on branch $branch off $base"
    git worktree add -b "$branch" "$path" "$base"

    # Symlink node_modules so the pre-commit tsc hook can resolve the TypeScript
    # compiler without running `npm install` (which would race or duplicate).
    #
    # IMPORTANT: the symlink is a soft symlink, so any WRITE through
    # $path/frontend/node_modules/... lands in $REPO_ROOT/frontend/node_modules/...
    # That's fine for `npm ci` (which removes node_modules first, then creates a
    # fresh real dir), but UNSAFE for `npm install`, `npm uninstall`, `npm update`
    # — they mutate the shared store in place.
    #
    # Drift-at-birth check: if the base branch's frontend/package-lock.json
    # doesn't match /root/Meridian's, an `npm install` here would silently
    # propagate THIS worktree's lock state into the shared store, breaking
    # every other worktree. In that case we refuse to symlink and tell the
    # user to either `npm ci` here (isolated install) or rebase to a base
    # whose lockfile matches.
    local symlink_ok=1
    if [ -d "$REPO_ROOT/frontend/node_modules" ]; then
        local shared_lock="$REPO_ROOT/frontend/package-lock.json"
        local new_lock="$path/frontend/package-lock.json"
        if [ -f "$shared_lock" ] && [ -f "$new_lock" ]; then
            local shared_hash new_hash
            shared_hash=$(sha256sum "$shared_lock" | cut -d' ' -f1)
            new_hash=$(sha256sum "$new_lock" | cut -d' ' -f1)
            if [ "$shared_hash" != "$new_hash" ]; then
                symlink_ok=0
                cat >&2 <<EOF
⚠ DRIFT-AT-BIRTH: '$base' has a different frontend/package-lock.json than $REPO_ROOT.
  NOT symlinking node_modules — a symlink here would corrupt the shared store
  the moment anything runs 'npm install'.

  Choose one before running anything that touches node_modules:
    (a) isolated install (slow, ~500MB, safe):
          cd $path/frontend && npm ci
    (b) rebase this branch onto a base whose lockfile matches $REPO_ROOT/frontend/package-lock.json

  To re-check drift at any point from inside this worktree:
    cd $path && $0 check
EOF
            fi
        fi

        if [ "$symlink_ok" = "1" ]; then
            echo "→ symlinking frontend/node_modules → $REPO_ROOT/frontend/node_modules"
            rm -rf "$path/frontend/node_modules" 2>/dev/null
            ln -s "$REPO_ROOT/frontend/node_modules" "$path/frontend/node_modules"
        fi
    else
        echo "⚠ no $REPO_ROOT/frontend/node_modules to symlink — run 'cd frontend && npm install' in the worktree if you need tsc/lint."
    fi

    cat <<EOF

✓ Session worktree ready at $path

⚠ DEP-MUTATION RULE — load-bearing, read every time:
  frontend/node_modules is (or was) symlinked to $REPO_ROOT's store.
  READING it is safe (tsc, vite build, eslint).
  WRITING through it via 'npm install' / 'npm install <pkg>' / 'npm uninstall' /
  'npm update' corrupts the shared store for every other session.

  Safe options when you need to change deps in this worktree:
    ✓ cd frontend && npm ci          # removes symlink, installs fresh (~500MB, slow, isolated)
    ✗ npm install / npm install <pkg>  — DO NOT run; corrupts shared store
    ✗ npm uninstall / npm update       — same

  Verify safety before any npm command:
    cd $path && $0 check
  Prints '✓ safe' or '✗ DRIFT' with the recovery command.

Workflow:
  cd $path
  # work — your HEAD, your dirty files, isolated from other sessions
  # tsc pre-commit hook works because node_modules is symlinked

  git add <paths> && git commit -m "..."
  git push -u origin $branch
  gh pr create --base main --head $branch

When done:
  $0 rm $safe
EOF
}

cmd_check() {
    # Run from inside a worktree. Compares this worktree's frontend/package-lock.json
    # to $REPO_ROOT's; tells you whether 'npm install' / 'npm update' / 'npm uninstall'
    # would corrupt the shared store.
    local shared_lock="$REPO_ROOT/frontend/package-lock.json"
    local here_lock="frontend/package-lock.json"

    if [ ! -f "$here_lock" ]; then
        echo "⚠ no $here_lock in CWD — run this from a worktree's repo root (the dir that contains frontend/)." >&2
        return 2
    fi
    if [ ! -f "$shared_lock" ]; then
        echo "⚠ no $shared_lock — is REPO_ROOT correct? (current: $REPO_ROOT)" >&2
        return 2
    fi

    local shared_hash here_hash
    shared_hash=$(sha256sum "$shared_lock" | cut -d' ' -f1)
    here_hash=$(sha256sum "$here_lock"   | cut -d' ' -f1)

    # Also check whether node_modules is actually still a symlink (it could have
    # been replaced by a real directory if someone already ran `npm ci` here).
    local nm_state="(no node_modules)"
    if [ -L "frontend/node_modules" ]; then
        nm_state="symlink → $(readlink frontend/node_modules)"
    elif [ -d "frontend/node_modules" ]; then
        nm_state="real directory (isolated — npm install safe here)"
    fi

    if [ "$shared_hash" = "$here_hash" ]; then
        cat <<EOF
✓ SAFE — frontend/package-lock.json matches $REPO_ROOT.
  node_modules: $nm_state
  npm install / uninstall / update would mutate the shared store, but lock state
  is identical so the shared store stays internally consistent. Still: prefer
  'npm ci' if you're about to change deps (it converts node_modules from symlink
  to real dir, isolating any further mutations).
EOF
        return 0
    else
        cat <<EOF
✗ DRIFT — frontend/package-lock.json differs from $REPO_ROOT.
  node_modules: $nm_state
  this worktree:    $here_hash
  $REPO_ROOT: $shared_hash
  Running 'npm install' / 'npm update' here would silently propagate THIS
  worktree's lock state into the shared store. Do NOT run them.

  Safe options:
    (a) cd frontend && rm node_modules && npm ci   # isolated install (~500MB, slow)
    (b) rebase this branch onto a base whose lockfile matches $REPO_ROOT
EOF
        return 1
    fi
}

cmd_list() {
    cd "$REPO_ROOT"
    git worktree list
}

cmd_rm() {
    local name="$1"
    [ -z "$name" ] && { echo "session-name required" >&2; usage; exit 2; }
    local safe; safe=$(sanitize "$name")
    local path="$WORKTREE_BASE/meridian-$safe"
    local branch="session/$safe"

    cd "$REPO_ROOT"

    if [ ! -d "$path" ]; then
        echo "⚠ no worktree at $path" >&2
        # Still try to remove the branch if it exists and is unused.
    fi

    # Remove the symlinked node_modules so worktree remove doesn't complain.
    if [ -L "$path/frontend/node_modules" ]; then
        rm "$path/frontend/node_modules"
    fi

    # Refuse to remove a worktree with uncommitted changes (unless --force).
    if [ -d "$path" ] && git worktree list --porcelain | grep -q "^worktree $path$"; then
        local dirty
        dirty=$(cd "$path" && git status --porcelain 2>/dev/null | wc -l)
        if [ "$dirty" -gt 0 ]; then
            echo "⚠ worktree has $dirty uncommitted entries. Refusing to remove." >&2
            echo "  Commit/push them, or run: git worktree remove --force $path" >&2
            exit 3
        fi
    fi

    if [ -d "$path" ]; then
        echo "→ removing worktree $path"
        git worktree remove "$path" 2>/dev/null || git worktree remove --force "$path"
    fi

    # Delete the local branch if it has zero commits beyond origin/main and has no PR open.
    if git rev-parse --verify "$branch" >/dev/null 2>&1; then
        local ahead
        ahead=$(git rev-list --count "origin/main..$branch" 2>/dev/null || echo "?")
        if [ "$ahead" = "0" ]; then
            echo "→ deleting empty branch $branch"
            git branch -D "$branch"
        else
            echo "  branch $branch still exists ($ahead commits ahead of origin/main) — delete manually if no longer needed:"
            echo "    git branch -D $branch"
        fi
    fi
}

cmd_path() {
    local name="$1"
    [ -z "$name" ] && { echo "session-name required" >&2; usage; exit 2; }
    local safe; safe=$(sanitize "$name")
    echo "$WORKTREE_BASE/meridian-$safe"
}

case "${1:-}" in
    new)   shift; cmd_new "$@" ;;
    list)  cmd_list ;;
    rm)    shift; cmd_rm "$@" ;;
    path)  shift; cmd_path "$@" ;;
    check) cmd_check ;;
    -h|--help|help|"") usage; exit 0 ;;
    *) echo "unknown command: $1" >&2; usage; exit 2 ;;
esac
