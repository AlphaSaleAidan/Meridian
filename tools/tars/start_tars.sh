#!/usr/bin/env bash
# Launch Agent TARS CLI with Meridian context.
# Usage: ./tools/tars/start_tars.sh [playbook-name]
#
# Examples:
#   ./tools/tars/start_tars.sh                          # Interactive mode
#   ./tools/tars/start_tars.sh add_railway_env_vars     # Load specific playbook

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MERIDIAN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLAYBOOK_DIR="$SCRIPT_DIR/playbooks"
CONTEXT_FILE="$SCRIPT_DIR/meridian_context.yaml"

# Agent TARS requires Node >= 22.15.0
NODE_MAJOR=$(node -v 2>/dev/null | sed 's/v\([0-9]*\).*/\1/')
if [ "${NODE_MAJOR:-0}" -lt 22 ]; then
    echo "ERROR: Agent TARS requires Node >= 22.15.0 (you have $(node -v 2>/dev/null || echo 'none'))"
    echo ""
    echo "Upgrade with nvm:"
    echo "  nvm install 22"
    echo "  nvm use 22"
    echo "  npm install -g @agent-tars/cli@latest"
    echo ""
    echo "Or install Node 22 directly:"
    echo "  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -"
    echo "  apt-get install -y nodejs"
    echo "  npm install -g @agent-tars/cli@latest"
    exit 1
fi

# Verify Agent TARS is installed
if ! command -v agent-tars &>/dev/null; then
    echo "Agent TARS CLI not found. Installing..."
    npm install -g @agent-tars/cli@latest
fi

# Build system prompt with Meridian context
SYSTEM_PROMPT="You are helping Aidan Pierce automate Meridian infrastructure tasks.

Project: Meridian — AI-powered POS analytics platform
Domain: meridian.tips
Backend: Railway (FastAPI)
Frontend: Vercel (Vite+React)
Database: Supabase (PostgreSQL 15 + TimescaleDB)
Email: Postal (self-hosted)
DNS: Namecheap

SECURITY: Never type, paste, or screenshot credentials. Reference env vars by name only.
SECURITY: Never run destructive DB operations without explicit confirmation.
SECURITY: Only interact with allowed domains listed in SECURITY.md.

Context file: $CONTEXT_FILE"

# If a playbook name was passed, load it
if [ "${1:-}" != "" ]; then
    PLAYBOOK_FILE="$PLAYBOOK_DIR/${1%.md}.md"
    if [ -f "$PLAYBOOK_FILE" ]; then
        echo "Loading playbook: $1"
        PLAYBOOK_CONTENT=$(cat "$PLAYBOOK_FILE")
        SYSTEM_PROMPT="$SYSTEM_PROMPT

--- PLAYBOOK ---
$PLAYBOOK_CONTENT
--- END PLAYBOOK ---

Follow the playbook steps above. Ask for confirmation before any write operation."
    else
        echo "Playbook not found: $PLAYBOOK_FILE"
        echo "Available playbooks:"
        ls "$PLAYBOOK_DIR"/*.md 2>/dev/null | xargs -I{} basename {} .md
        exit 1
    fi
fi

echo "Starting Agent TARS for Meridian..."
echo "Context: $CONTEXT_FILE"
echo ""

# Launch TARS with Meridian context
agent-tars --system-prompt "$SYSTEM_PROMPT"
