// Read LITELLM_MASTER_KEY out of the 0600 .env.litellm at fork time so the
// secret never lands in this file (which is checked into git).
const _fs = require("fs");
function _readLitellmKey() {
  try {
    const raw = _fs.readFileSync("/root/Meridian/.env.litellm", "utf8");
    const m = raw.match(/^LITELLM_MASTER_KEY=["']?([^"'\n]+)["']?$/m);
    return m ? m[1] : "";
  } catch (_e) {
    return "";
  }
}
const LITELLM_MASTER_KEY = _readLitellmKey();
const GATEWAY_ENV = {
  // OpenAI-compatible bridge — anything speaking OpenAI clients hits :4000.
  OPENAI_BASE_URL: "http://127.0.0.1:4000/v1",
  OPENAI_API_KEY: LITELLM_MASTER_KEY,
  // Anthropic-compatible bridge — `claude -p` headless hits :4000 the same way.
  ANTHROPIC_BASE_URL: "http://127.0.0.1:4000",
  ANTHROPIC_AUTH_TOKEN: LITELLM_MASTER_KEY,
  // Convenience for app-side code that wants the canonical gateway URL.
  RUFLO_GATEWAY: "http://127.0.0.1:4000/v1",
};

module.exports = {
  apps: [
    {
      name: "meridian-api",
      script: "/usr/local/bin/uvicorn",
      args: "src.api.app:app --host 0.0.0.0 --port 8000 --workers 4",
      cwd: "/root/Meridian",
      interpreter: "none",
      exec_mode: "fork",
      instances: 1,
      max_memory_restart: "512M",
      env: {
        PYTHONPATH: "/root/Meridian",
        ENABLE_LLM_INSIGHTS: "1",
        MERIDIAN_REASONING: "1",
        ENABLE_SWARM_TRAINING: "1",
        ENABLE_CANADA_INTELLIGENCE: "1",
        ENABLE_FINANCIAL_INTELLIGENCE: "1",
        ...GATEWAY_ENV,
      },
    },
    {
      name: "celery-worker",
      script: "/usr/bin/bash",
      args: "-c 'celery -A src.workers.celery_app worker --loglevel=info -Q default,sync,analysis,reports --concurrency=8 --max-tasks-per-child=200'",
      cwd: "/root/Meridian",
      exec_mode: "fork",
      instances: 1,
      max_memory_restart: "400M",
      env: { ...GATEWAY_ENV },
    },
    {
      name: "celery-beat",
      script: "/usr/bin/bash",
      args: "-c 'celery -A src.workers.celery_app beat --loglevel=info'",
      cwd: "/root/Meridian",
      exec_mode: "fork",
      instances: 1,
      max_memory_restart: "200M",
      env: { ...GATEWAY_ENV },
    },
    {
      // Gateway env intentionally omitted: pm2 reload with --update-env breaks
      // `uv run` module discovery inside this entry (was working before, now
      // throws "Could not import module 'app.api'"). DeerFlow has its own LLM
      // config so it doesn't depend on the gateway. Reinstate the gateway env
      // once we've isolated whether it's a uv-cache or PATH issue.
      name: "deerflow",
      script: "/usr/bin/bash",
      args: "-c 'cd /root/Meridian/services/deerflow/backend && /root/.local/bin/uv run uvicorn app.api:app --host 0.0.0.0 --port 8004'",
      cwd: "/root/Meridian",
      exec_mode: "fork",
      instances: 1,
      max_memory_restart: "200M",
    },
    {
      name: "scraper",
      script: "/root/Meridian/scripts/scraper-daemon.py",
      cwd: "/root/Meridian",
      interpreter: "python3",
      exec_mode: "fork",
      instances: 1,
      max_memory_restart: "300M",
      env: { ...GATEWAY_ENV },
    },
    {
      name: "qwen-server",
      script: "/usr/bin/bash",
      args: "-c 'python3 -m llama_cpp.server --model /root/Meridian/data/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf --host 0.0.0.0 --port 8002 --n_ctx 4096 --n_threads 4 --chat_format chatml'",
      cwd: "/root/Meridian",
      exec_mode: "fork",
      instances: 1,
      max_memory_restart: "12G",
    },
    {
      name: "garry",
      script: "/root/garry/garry_main.py",
      cwd: "/root/garry",
      interpreter: "python3",
      exec_mode: "fork",
      instances: 1,
      max_memory_restart: "200M",
      env: {
        ...GATEWAY_ENV,
      },
    },
    {
      // Unified model gateway on 127.0.0.1:4000 — see /root/Meridian/litellm.config.yaml.
      // Aliases: meridian-architect | meridian-fixer | meridian-fast | meridian-local.
      name: "litellm-gateway",
      script: "/root/Meridian/scripts/start-litellm.sh",
      interpreter: "none",
      cwd: "/root/Meridian",
      exec_mode: "fork",
      instances: 1,
      max_memory_restart: "1G",
      restart_delay: 5000,
      max_restarts: 10,
    },
    {
      // Autonomous K2.6 fixer daemon — listens on /run/meridian-fixer/sock.
      // Runs as the non-root meridian-fixer user; escalates only via sudoers
      // to /opt/meridian-fixer/{worktree,apply}.sh. See /opt/meridian-fixer/.
      name: "meridian-fixer",
      script: "/opt/meridian-fixer/start.sh",
      interpreter: "none",
      cwd: "/opt/meridian-fixer",
      exec_mode: "fork",
      instances: 1,
      max_memory_restart: "512M",
      restart_delay: 5000,
      max_restarts: 10,
    },
    {
      // LiteLLM → Telegram alert bridge. Listens on 127.0.0.1:8005/alert and
      // forwards budget / exception alerts to AIDAN_TELEGRAM_ID via Garry's
      // bot token. Standalone process so the gateway never loses alerting if
      // Garry's main bot restarts. Audit log: /var/lib/garry/litellm-alerts.log.
      name: "garry-litellm-alerts",
      script: "/root/garry/services/start-litellm-alerts.sh",
      interpreter: "none",
      cwd: "/root/garry",
      exec_mode: "fork",
      instances: 1,
      max_memory_restart: "100M",
      restart_delay: 5000,
      max_restarts: 10,
    },
  ],
};
