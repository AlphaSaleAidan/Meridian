# Vendor: LLM Providers (OpenRouter / DeepSeek / SambaNova / Groq / Cerebras / OpenAI)
**Document ID:** VEN-007
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce

---

## Role

Meridian's tiered LLM routing system (`src/ai/routing/tiered_router.py`) dispatches analytics and AI inference calls to multiple LLM providers depending on task complexity, cost, and availability. Additionally, the Kimi K2.6 LiteLLM gateway on Contabo (`:4000`) proxies some calls through a DeepSeek-compatible API.

None of these providers are in Meridian's prior 7-vendor list — **this is a gap now resolved by registration here.**

**Integration path:** `src/ai/routing/tiered_router.py`, `src/api/app.py` (prompt dispatch), Contabo LiteLLM gateway at `:4000`

---

## Providers and Tier Assignment

| Provider | API endpoint | Primary use in Meridian | Tier |
|---|---|---|---|
| **OpenRouter** | api.openrouter.ai | Routing layer aggregating multiple models | 1/2/3 |
| **DeepSeek** | api.deepseek.com (and via Kimi gateway at :4000) | Low-cost text completions for analytics | 1/2 |
| **SambaNova** | api.sambanova.ai | Fast inference for structured extraction tasks | 2 |
| **Groq** | api.groq.com | High-speed inference (Llama models) for latency-sensitive paths | 2 |
| **Cerebras** | api.cerebras.ai | Ultra-fast inference (Llama 3.1 70B) | 2 |
| **OpenAI** | api.openai.com | GPT-4 class tasks; camera vision analytics (`gpt-4o-vision`) | 3 |

---

## Data Touched

| Data category | Details |
|---|---|
| Analytics prompts | Restaurant performance analytics, menu analysis, trend summaries. **Prompts are anonymized: no customer names, phone numbers, or direct PII should be included.** Verify this in `tiered_router.py` — check that prompt construction strips PII before dispatch. |
| Camera vision input (OpenAI) | If `gpt-4o-vision` receives camera frames or descriptions, this may include images of merchant premises and indirectly of customers. Verify what is sent to OpenAI Vision endpoints. |
| Agent reasoning traces | DeerFlow and Garry agents on Contabo may send reasoning steps to LLM providers. Confirm what context is included. |
| LiteLLM gateway logs on Contabo | The Kimi K2.6 gateway at `:4000` logs requests and responses locally on the VPS. Review log retention and content — PII in prompts would be stored in Contabo logs. |

**Critical assumption to verify:** The claim that prompts are anonymized must be confirmed by code review of `tiered_router.py` and all call sites. If PII is flowing to LLM providers, this materially changes the risk profile and DPA requirements.

---

## Attestation Status

| Provider | SOC 2 / Attestation | Status |
|---|---|---|
| OpenRouter | SOC 2: **verify** at openrouter.ai/privacy | TBD |
| DeepSeek | SOC 2: **verify**; DeepSeek is a Chinese company — data residency implications for Canadian customer data | TBD — HIGH PRIORITY to verify |
| SambaNova | SOC 2: **verify** at sambanova.ai/security | TBD |
| Groq | SOC 2: **verify** at groq.com/security | TBD |
| Cerebras | SOC 2: **verify** at cerebras.ai | TBD |
| OpenAI | SOC 2 Type II + ISO 27001 (public) | openai.com/security |

**DeepSeek jurisdiction note:** DeepSeek is operated by a Chinese company (High-Flyer). Data sent to DeepSeek's API may be subject to the Chinese National Intelligence Law. For Canadian customers, this creates a cross-border data transfer risk if any PII (even indirect) is included in prompts. **Action required:** Verify (a) no PII in DeepSeek prompts, and (b) whether OpenRouter anonymizes provider routing. If DeepSeek cannot be confirmed PII-free, consider routing away from DeepSeek for analytics involving Canadian merchant data.

---

## DPA Status

| Provider | DPA available | Notes |
|---|---|---|
| OpenRouter | Verify at openrouter.ai | TBD |
| DeepSeek | Verify | High-priority given jurisdiction concern |
| SambaNova | Verify | TBD |
| Groq | Verify at groq.com | TBD |
| Cerebras | Verify | TBD |
| OpenAI | OpenAI DPA available (covers GDPR) | Confirm PIPEDA alignment |

**Action required for each provider:** Check privacy page and legal terms. If a DPA or acceptable data processing terms are available, accept/execute them. Document outcomes in `compliance/evidence/POL-008/vendor-attestations/llm-<provider>-dpa-status.md`.

---

## What Breaks if LLM Providers Fail

**Impact: MEDIUM (analytics and AI features degrade; core POS and auth unaffected)**

- Analytics summaries (restaurant performance, menu insights) fail or fall back to simpler logic.
- Camera vision analytics (if OpenAI Vision is used) stop updating.
- DeerFlow and Garry agent reasoning stops; agents may fall back to rule-based behavior.
- Phone agent's natural language understanding degrades if LLM backend is unavailable; turn-based fallback remains operational.
- Core API (`api.meridian.tips`), POS order submission, authentication, and Supabase data are unaffected.

**Failover:** `tiered_router.py` implements tiered routing — if one provider fails, it falls back to the next tier. Verify that Circuit Breaker logic is implemented and tested.

---

## Specific Risks & Controls

| Risk | Control | Status |
|---|---|---|
| PII in LLM prompts | Prompt construction in `tiered_router.py` strips PII before dispatch (design intent) | **Verify by code review — not confirmed** |
| LLM API key leaked | Keys stored in Railway env vars and `/root/.secrets/`; gitleaks on all PRs | Enforced |
| LiteLLM gateway logs storing PII on Contabo | Review log level and retention of `:4000` gateway; set appropriate log retention | Verify + configure |
| DeepSeek cross-border data transfer | Anonymize prompts OR route away from DeepSeek for Canadian-context queries | Unresolved — requires DECISION |
| Prompt injection affecting analytics output | Input validation on analytics query construction; LLM output treated as untrusted data | Verify in code |

---

## ## DECISION (Aidan) — DeepSeek Jurisdiction Risk

**Context:** DeepSeek is subject to Chinese law, which includes broad intelligence-access provisions. If Meridian sends any Canadian merchant business data (even anonymized analytics prompts that could identify a merchant) to DeepSeek, this is a PIPEDA cross-border transfer risk.

**Options:**
1. Confirm prompts are fully anonymized (no merchant identifiers) and accept the residual risk.
2. Route away from DeepSeek for all Canadian-context queries; use OpenAI/Groq/SambaNova instead.
3. Use DeepSeek only via a US-proxied OpenRouter that strips routing metadata.

**Decision required from Aidan.** Document outcome here and in the risk register.

---

## Review Date

TBD — verify all provider SOC 2 / DPA statuses by next annual review (January 2027). Reassess DeepSeek routing decision within 30 days.
