# Known Issues — tracked for post-Wave-1 follow-up

Items surfaced during the swarm upgrade that are out of scope for the
current run. Do not fix in-flight; pick up after Wave 1 lands.

---

## 1. DeepSeek rejects LiteLLM JSON-mode (`response_format`)

**Discovered:** 2026-06-02, during Wave 1 go-live Phase A seed.
**Owner:** TBD (router / `llm_layer.enhance_insights` surface).
**Severity:** Blocks Step 3 (tier-resolver) baseline; live structured-output
failure on the primary provider.

### What

`src/ai/llm_layer.enhance_insights(...)` asks LiteLLM for JSON output via
`response_format={"type": "json_object"}` (OpenAI-compatible JSON mode).
DeepSeek's API responds:

```
litellm.BadRequestError: DeepseekException -
  {"error":{"message":"This response_format type is unavailable now",
   "type":"invalid_request_error", ...}}
```

The router then falls back to OpenAI per the latency chain. On this VPS
the OpenAI key is quota-exhausted, so:

```
litellm.RateLimitError: RateLimitError: OpenAIException -
  You exceeded your current quota, please check your plan and billing
  details.
```

Net effect: every `enhance_insights` call during the Phase A baseline seed
failed (`success=0` in `swarm_traces`), even though both keys are present
and reachable.

### Reproduction

```
MERIDIAN_BASELINE_CONFIRMED_DEMO=1 \
DEMO_ORG_ID=00000000-0000-0000-0000-000000000000 \
PYTHONPATH=/root/Meridian \
python3 scripts/run_baseline_seed.py
```

Watch `data/swarm_traces.sqlite` — `enhance_insights` rows arrive with
`success=0` and the messages above in `error`.

### Possible fixes (evaluate later — do NOT do in this run)

1. **Drop OpenAI JSON-mode for DeepSeek.** Replace the `response_format`
   ask with explicit JSON-schema prompting + tool/function-calling for
   models that don't support OpenAI JSON mode. LiteLLM supports
   `tools=[…]` cross-provider; DeepSeek-V3 understands function-calling.
2. **Provider routing on JSON-mode.** Have the router send JSON-mode
   calls only to providers that support it (Groq's Llama-3.3-70B does;
   SambaNova varies by model; Cerebras does), and fall back to a plain-
   prompt JSON parser elsewhere.
3. **Top up OpenAI quota** for the meantime. Tactical only — doesn't
   address (1).

### Why this matters for the swarm upgrade

Step 3 of the masterplan (LiteLLM tier resolver + confidence escalation)
needs a populated SQLite baseline of real LLM calls to validate
acceptance. Currently we can produce trace rows but they're all
`success=0` — useless for the latency/cost-by-tier comparisons the
acceptance gate wants. Fixing the JSON-mode call also unblocks the
baseline seed.

---
