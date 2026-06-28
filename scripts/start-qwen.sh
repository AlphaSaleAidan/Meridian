#!/usr/bin/bash
# qwen-server launcher — bound to localhost only (F1 pen-test fix 2026-06-28).
# Only the local litellm gateway consumes this (via 127.0.0.1:8002); never expose publicly.
exec python3 -m llama_cpp.server \
  --model /root/Meridian/data/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf \
  --host 127.0.0.1 \
  --port 8002 \
  --n_ctx 4096 \
  --n_threads 4 \
  --chat_format chatml
