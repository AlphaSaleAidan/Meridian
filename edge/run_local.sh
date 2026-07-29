#!/usr/bin/env bash
# Meridian Vision Edge Agent — no-Docker quickstart for the merchant's own
# computer (Linux/macOS, CPU-only). Creates a local venv, installs CPU
# wheels, and starts the agent against config/cameras.json.
#
#   MERIDIAN_API_URL=https://api.meridian.tips \
#   MERIDIAN_API_KEY=... MERIDIAN_ORG_ID=... ./run_local.sh
set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv-edge"
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip
  "$VENV/bin/pip" install torch torchvision --index-url https://download.pytorch.org/whl/cpu
  "$VENV/bin/pip" install -r requirements-cpu.txt
fi

# Counting only by default on customer hardware.
export ENABLE_DEMOGRAPHICS="${ENABLE_DEMOGRAPHICS:-0}"
export ENABLE_DEPTH="${ENABLE_DEPTH:-0}"

exec "$VENV/bin/python" edge_agent.py
