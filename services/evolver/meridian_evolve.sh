#!/bin/bash
# ═══════════════════════════════════════════════════
# MERIDIAN EVOLVER — Run an evolution cycle
# Usage:
#   ./meridian_evolve.sh              → review mode (safe default)
#   ./meridian_evolve.sh harden       → harden strategy
#   ./meridian_evolve.sh repair-only  → emergency repairs
#   ./meridian_evolve.sh loop         → continuous evolution
# ═══════════════════════════════════════════════════

cd "$(dirname "$0")"

STRATEGY=${1:-balanced}
MODE=${2:-review}

echo "═══════════════════════════════════════════════════"
echo "  MERIDIAN EVOLVER"
echo "  Strategy: $STRATEGY | Mode: $MODE"
echo "  $(date)"
echo "═══════════════════════════════════════════════════"

if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
  echo "✓ Ollama is running"
else
  echo "⚠ Ollama not detected — Evolver will run in prompt-only mode"
fi

export EVOLVE_STRATEGY=$STRATEGY

if [ "$MODE" = "loop" ]; then
  node index.js --loop
elif [ "$MODE" = "review" ]; then
  node index.js --review
else
  node index.js
fi

echo "═══════════════════════════════════════════════════"
echo "  Evolution cycle complete"
echo "  Check assets/gep/events.jsonl for the audit log"
echo "═══════════════════════════════════════════════════"
