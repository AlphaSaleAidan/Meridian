# LiteLLM Grafana dashboard — future deployment sketch

The single-host LiteLLM gateway shipped 2026-06-04 deliberately trims the heavy `claude-flow/examples/litellm` stack (3x LiteLLM, Postgres, Prometheus, Loki, Grafana) down to one PM2 process. Per-call spend/latency is still captured by LiteLLM's built-in spend logs and is queryable via the proxy admin API.

Deploy the full observability layer when traffic justifies it:

## When to upgrade

- Sustained > 5 req/s through the gateway
- More than one human reviewing fixer activity (need shared dashboards)
- Multi-team budget enforcement (need per-key spend caps)
- > $50/day K2.6 spend (cost telemetry becomes ROI-critical)

## Drop-in stack

```bash
git clone https://github.com/ruvnet/claude-flow /tmp/cf-litellm
cp -r /tmp/cf-litellm/examples/litellm /root/Meridian/services/observability
cd /root/Meridian/services/observability
# Migrate /root/Meridian/litellm.config.yaml → config.yaml
# Point its Postgres at a managed DB or co-host with the existing mariadb
docker compose up -d prometheus loki grafana
```

Then route nginx `/litellm` → `127.0.0.1:4000` (already happens via the PM2 process; no change). Grafana dashboards land at `https://meridian.tips/grafana/` (proxied) or a separate subdomain — the per-model spend, latency, and fallback-rate panels are pre-built in the claude-flow example.

## Cheap interim alternative

Until then, the existing application-level trace recorder (`src/ai/trace_recorder.py`, table `swarm_traces`) captures every LLM call from `llm_layer.py` with `(agent_name, provider, model, latency_ms, prompt_tokens, completion_tokens, success)`. Add a Supabase view + a Metabase/Grafana panel against it for the same view at zero infra cost.
