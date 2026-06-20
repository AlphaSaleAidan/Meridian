#!/usr/bin/env bash
# Prerender every public route into dist/ after a build.
# Assumes `vite build` already ran. Starts a local preview, prerenders, stops it.
set -e
cd "$(dirname "$0")/.."

PORT="${PRERENDER_PORT:-4188}"
npx vite preview --port "$PORT" --host 127.0.0.1 > /tmp/prerender-preview.log 2>&1 &
PREVIEW_PID=$!
trap 'kill $PREVIEW_PID 2>/dev/null || true' EXIT
sleep 6

PRERENDER_BASE="http://127.0.0.1:$PORT" node scripts/prerender.mjs "$@"
echo "prerender-all complete"
