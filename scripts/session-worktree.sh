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
#
# Examples:
#   scripts/session-worktree.sh new my-feature              # off origin/main
#   scripts/session-worktree.sh new pos-fix swarm-upgrade   # off local swarm-upgrade
#   scripts/session-worktree.sh list
#   scripts/session-worktree.sh rm my-feature

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
    if [ -d "$REPO_ROOT/frontend/node_modules" ]; then
        echo "→ symlinking frontend/node_modules → $REPO_ROOT/frontend/node_modules"
        rm -rf "$path/frontend/node_modules" 2>/dev/null
        ln -s "$REPO_ROOT/frontend/node_modules" "$path/frontend/node_modules"
    else
        echo "⚠ no $REPO_ROOT/frontend/node_modules to symlink — run 'cd frontend && npm install' in the worktree if you need tsc/lint."
    fi

    cat <<EOF

✓ Session worktree ready.

  cd $path
  # work here — your HEAD, your dirty files, isolated from other sessions
  # the pre-commit tsc hook will work because node_modules is symlinked
  # if you change frontend deps, run 'cd frontend && npm install' in THIS worktree
  # (it'll resolve against the symlink — installing inside a symlinked node_modules
  # is unusual; safer is 'cd frontend && rm node_modules && npm install' locally)

  git add <paths> && git commit -m "..."
  git push -u origin $branch
  gh pr create --base main --head $branch

  # When done:
  $0 rm $safe
EOF
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
    new)  shift; cmd_new "$@" ;;
    list) cmd_list ;;
    rm)   shift; cmd_rm "$@" ;;
    path) shift; cmd_path "$@" ;;
    -h|--help|help|"") usage; exit 0 ;;
    *) echo "unknown command: $1" >&2; usage; exit 2 ;;
esac
