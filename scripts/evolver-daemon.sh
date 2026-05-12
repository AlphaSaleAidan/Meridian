#!/bin/bash
# Evolver Daemon — runs continuous evolution cycles every 4 hours
# Falls back to prompt-only mode if Ollama isn't available

cd /root/Meridian/services/evolver

LOG_DIR="/root/Meridian/logs"
mkdir -p "$LOG_DIR"

echo "[Evolver] Starting autonomous evolution daemon (4h cycle)"
echo "[Evolver] Strategy: balanced | Mode: loop"

while true; do
    echo "═══════════════════════════════════════════════════"
    echo "[Evolver] Cycle start: $(date)"

    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "[Evolver] Ollama detected — full evolution mode"
        timeout 1800 node index.js --review 2>&1 | tail -20
    else
        echo "[Evolver] No Ollama — running repair-only mode"
        timeout 900 node index.js 2>&1 | tail -20
    fi

    echo "[Evolver] Cycle complete: $(date)"
    echo "[Evolver] Next cycle in 4 hours"
    echo "═══════════════════════════════════════════════════"

    sleep 14400  # 4 hours
done
