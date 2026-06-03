#!/usr/bin/env bash
# Meridian LiteLLM gateway launcher (called by PM2 entry "litellm-gateway").
# Sources /root/Meridian/.env.litellm + pulls DEEPSEEK_API_KEY from main .env,
# refuses to start if the master key is missing or placeholder.

set -euo pipefail

ENV_FILE="/root/Meridian/.env.litellm"
MAIN_ENV="/root/Meridian/.env"
CONFIG="/root/Meridian/litellm.config.yaml"
LITELLM_BIN="/root/Meridian/.venv/bin/litellm"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
else
  echo "FATAL: $ENV_FILE not found" >&2
  exit 1
fi

# Pull DEEPSEEK_API_KEY from main .env (don't re-source whole file — it has
# unrelated secrets and is owned by the wider app).
if [ -f "$MAIN_ENV" ]; then
  _ds_line="$(grep -E '^DEEPSEEK_API_KEY=' "$MAIN_ENV" | head -1 || true)"
  if [ -n "$_ds_line" ]; then
    DEEPSEEK_API_KEY="$(printf '%s' "$_ds_line" | sed -E 's/^DEEPSEEK_API_KEY=//; s/^"//; s/"$//; s/^'\''//; s/'\''$//')"
    export DEEPSEEK_API_KEY
  fi
fi

# Sanity: master key must be set and not a placeholder.
if [ -z "${LITELLM_MASTER_KEY:-}" ] || [[ "${LITELLM_MASTER_KEY:-}" == *"<<FILL"* ]]; then
  echo "FATAL: LITELLM_MASTER_KEY missing or placeholder — edit $ENV_FILE" >&2
  exit 1
fi

# Warn (don't fail) when no upstream key is filled — the local fallback still
# answers, which keeps the gateway up for the fixer to operate offline.
_have_any_upstream=0
for k in OPENROUTER_API_KEY GROQ_API_KEY CEREBRAS_API_KEY SAMBANOVA_API_KEY DEEPSEEK_API_KEY; do
  v="${!k:-}"
  if [ -n "$v" ] && [[ "$v" != *"<<FILL"* ]]; then
    _have_any_upstream=1
    break
  fi
done
if [ "$_have_any_upstream" -eq 0 ]; then
  echo "WARN: no upstream provider keys set — only meridian-local will answer" >&2
fi

# Render the effective config with the budget cap injected from env. We do
# this in shell because LiteLLM's `os.environ/X` resolver returns a string
# and the spend>cap compare is numeric — see the comment on max_budget in
# litellm.config.yaml.
EFFECTIVE_CONFIG="/run/meridian-fixer/litellm.config.effective.yaml"
# Fall back to /tmp if the meridian-fixer runtime dir isn't writable (e.g.,
# very first boot before tmpfiles.d has run).
if ! { [ -w "$(dirname "$EFFECTIVE_CONFIG")" ] 2>/dev/null; }; then
  EFFECTIVE_CONFIG="/tmp/litellm.config.effective.yaml"
fi
_budget="${LITELLM_MAX_BUDGET:-9.0}"
# Validate it's a positive number; otherwise the proxy will throw the same
# misleading 401 the env-var path used to.
if ! printf '%s' "$_budget" | grep -qE '^[0-9]+(\.[0-9]+)?$'; then
  echo "FATAL: LITELLM_MAX_BUDGET ($_budget) is not numeric" >&2
  exit 1
fi
sed "s/__LITELLM_MAX_BUDGET__/$_budget/" "$CONFIG" > "$EFFECTIVE_CONFIG"

# LiteLLM also reads LITELLM_MAX_BUDGET directly from the process environment
# as a string, which then fails the spend>cap numeric compare. Drop it so the
# YAML's numeric value is the only source.
unset LITELLM_MAX_BUDGET

exec "$LITELLM_BIN" \
  --config "$EFFECTIVE_CONFIG" \
  --port 4000 \
  --host 127.0.0.1 \
  --num_workers 1
