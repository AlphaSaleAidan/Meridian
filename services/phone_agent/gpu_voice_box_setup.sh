#!/usr/bin/env bash
# Meridian GPU voice box — one-shot setup for the office RTX 3080 machine.
#
# Stands up two OpenAI-compatible model servers (both fit together in 10GB):
#   STT  :8790  NVIDIA Parakeet TDT 0.6B (whisper-compatible API, ~3GB VRAM)
#   TTS  :4123  Chatterbox (OpenAI /v1/audio/speech, ~3-4GB VRAM)
# then connects the box to the VPS over Tailscale so the sidecar can reach it.
#
# Prereqs on the box: Ubuntu/Debian-ish Linux, NVIDIA driver, docker + nvidia-
# container-toolkit (script checks and tells you what's missing; it does not
# install drivers for you).
#
# Run:  bash gpu_voice_box_setup.sh
# Then on the VPS sidecar .env:
#   GPU_STT_BASE_URL=http://<tailscale-ip>:8790/v1
#   GPU_TTS_BASE_URL=http://<tailscale-ip>:4123/v1
set -euo pipefail

say() { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }
die() { printf '\033[1;31mERROR: %s\033[0m\n' "$*"; exit 1; }

say "checks"
command -v docker >/dev/null || die "docker missing — https://docs.docker.com/engine/install/"
docker info 2>/dev/null | grep -qi nvidia || nvidia-smi >/dev/null 2>&1 || die "NVIDIA driver/toolkit missing — install driver + nvidia-container-toolkit"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

WORK="${WORK:-$HOME/meridian-voice-box}"
mkdir -p "$WORK" && cd "$WORK"

say "STT — Parakeet (whisper-compatible server)"
if [ ! -d parakeet ]; then git clone --depth 1 https://github.com/achetronic/parakeet.git; fi
# Serves POST /v1/audio/transcriptions on :8790 (see repo README; ONNX, CUDA)
(cd parakeet && docker compose up -d 2>/dev/null) || \
  echo "NOTE: check parakeet/README.md for its current compose/run command; expose port 8790"

say "TTS — Chatterbox (OpenAI-compatible /v1/audio/speech)"
if [ ! -d chatterbox-tts-api ]; then git clone --depth 1 https://github.com/travisvn/chatterbox-tts-api.git; fi
cd chatterbox-tts-api
cp -n .env.example.docker .env 2>/dev/null || true
docker compose -f docker/docker-compose.gpu.yml up -d 2>/dev/null || docker compose up -d
cd "$WORK"

say "smoke test"
sleep 20
curl -sf -o /tmp/tts-test.wav -X POST http://127.0.0.1:4123/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","voice":"alloy","input":"Thanks for calling, what can I get started for you?"}' \
  && echo "TTS OK → /tmp/tts-test.wav (play it!)" || echo "TTS not up yet — docker logs chatterbox-tts-api"

say "network — Tailscale (stable private address, no open ports)"
if ! command -v tailscale >/dev/null; then curl -fsSL https://tailscale.com/install.sh | sh; fi
sudo tailscale up || true
echo "This box's tailscale IP: $(tailscale ip -4 2>/dev/null | head -1)"

say "done — next steps"
cat <<'EOF'
1. Install tailscale on the VPS too (same account):  curl -fsSL https://tailscale.com/install.sh | sh && tailscale up
2. On the VPS, add to /root/meridian-voice-sidecar/services/phone_agent/.env:
     GPU_STT_BASE_URL=http://<this-box-tailscale-ip>:8790/v1
     GPU_TTS_BASE_URL=http://<this-box-tailscale-ip>:4123/v1
3. pm2 restart meridian-voice-sidecar — the A/B now rotates premium/gpu/nemotron.
EOF
