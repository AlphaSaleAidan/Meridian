#!/usr/bin/env bash
# Run the Meridian phone-agent streaming sidecar (pipecat 1.4 + Nemotron).
#
# This is the host the backend /voice TwiML points provider calls at:
#     <Stream url="wss://${MEDIA_STREAM_HOST}/twilio/media-stream/{merchant_id}">
# so it must run on a box with the heavy voice deps (NOT Railway — pipecat/torch
# OOM there). It serves plain ws://127.0.0.1:$PORT; put a TLS reverse proxy
# (nginx) in front so providers can reach it over wss://, and set the backend's
# MEDIA_STREAM_HOST to that public hostname.
#
# Usage:   ./run_sidecar.sh            # foreground
#          ./run_sidecar.sh --daemon   # detached (setsid nohup), logs to $LOG
#
# Env (read from ./.env if present — gitignored; never commit it):
#   DEEPSEEK_API_KEY   required (the brain)
#   NVIDIA_API_KEY     enables Nemotron ASR + Magpie TTS (else local Moonshine/Kokoro)
#   SUPABASE_URL / SUPABASE_ANON_KEY   to load real merchant configs (omit → demo config)
#   PHONE_PROVIDER     twilio | telnyx   (default twilio; must match the live provider)
#   TELNYX_API_KEY     or TWILIO_ACCOUNT_SID+TWILIO_AUTH_TOKEN   for auto-hangup at call end
#   PHONE_AGENT_PORT   default 8095
#   DEEPGRAM_API_KEY + CARTESIA_API_KEY   enable the premium voice lane
#   VOICE_AB=1         alternate premium/nemotron lanes per call (A/B on the test line)
#   VOICE_VENDOR       pin one lane: premium | nemotron
#   WORKERS            uvicorn workers (default 1). Each worker handles many
#                      concurrent calls (cloud STT/TTS ≈ audio proxying); scale
#                      workers ~= CPU cores for max simultaneous lines.
set -euo pipefail
cd "$(dirname "$0")"

VENV="${VENV:-.venv}"
PORT="${PHONE_AGENT_PORT:-8095}"
LOG="${LOG:-/tmp/meridian-voice-sidecar.log}"

[ -d "$VENV" ] || { echo "ERROR: venv '$VENV' not found — create it and pip install requirements.txt"; exit 1; }
if [ -f .env ]; then set -a; . ./.env; set +a; fi
[ -n "${DEEPSEEK_API_KEY:-}" ] || { echo "ERROR: DEEPSEEK_API_KEY not set (the brain needs it)"; exit 1; }
export PHONE_PROVIDER="${PHONE_PROVIDER:-twilio}"
export PHONE_AGENT_PORT="$PORT"

WORKERS="${WORKERS:-1}"
CMD=("$VENV/bin/python" -m uvicorn main:app --host 127.0.0.1 --port "$PORT" --workers "$WORKERS")
PREMIUM=$([ -n "${DEEPGRAM_API_KEY:-}" ] && [ -n "${CARTESIA_API_KEY:-}" ] && echo on || echo off)
echo "phone-agent sidecar → 127.0.0.1:$PORT  (provider=$PHONE_PROVIDER, nemotron=$([ -n "${NVIDIA_API_KEY:-}" ] && echo on || echo off), premium=$PREMIUM, ab=${VOICE_AB:-0}, workers=$WORKERS)"

if [ "${1:-}" = "--daemon" ]; then
  pkill -f "uvicorn main:app" 2>/dev/null || true; sleep 1
  setsid nohup "${CMD[@]}" >"$LOG" 2>&1 < /dev/null & disown
  # uvicorn + the pipecat import can take ~8s to bind — poll, don't single-shot.
  for _ in $(seq 1 20); do
    sleep 1
    curl -sf --max-time 3 "http://127.0.0.1:$PORT/health" >/dev/null && { echo "started; /health OK; logs: $LOG"; exit 0; }
  done
  echo "FAILED to come up within 20s — see $LOG"; tail -20 "$LOG"; exit 1
else
  exec "${CMD[@]}"
fi
