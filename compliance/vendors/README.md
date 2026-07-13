# Meridian Sub-Processor & Vendor Register
**Document ID:** VEN-000 (Master Register)
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder, US signing authority)
**Review Cadence:** Annual; updated within 14 days of any new vendor onboarding

---

## Carve-Out Method

Meridian relies on third-party subservice organizations for infrastructure, payments, communications, and data processing. Under SOC 2, Meridian applies the **carve-out method**: risks relating to physical data center security, cloud-infrastructure resilience, and PCI-scoped payment handling are carved out to those subservice organizations. Meridian's responsibility is to:

1. Select sub-processors with adequate independent attestations (SOC 2 Type II, ISO 27001, or PCI DSS Level 1 as appropriate).
2. Obtain and retain annual attestation evidence in `compliance/evidence/POL-008/vendor-attestations/`.
3. Maintain Data Processing Agreements (DPAs) where required by applicable law.
4. Confirm carve-out scope boundaries before any auditor examination.

Where a vendor lacks a SOC 2 / ISO 27001 certification, Meridian documents compensating controls in the relevant per-vendor file.

---

## Registry Gap Notice

The seven vendors in Meridian's previous informal sub-processor list (referenced in `compliance/policies/information-security-policy.md` §5.3) did not include the following vendors that touch production data. These are **gaps that must be resolved** by obtaining attestations, executing DPAs, and completing the per-vendor files below:

**Newly registered in this document (not in prior list):**
Contabo, OpenRouter/DeepSeek/SambaNova/Groq/Cerebras/OpenAI (LLM providers), Vapi, Backblaze B2, PostHog, Sentry, Highlight.io, Convex, Telegram, Clover, Toast, Stripe.

---

## Master Sub-Processor Table

| # | Vendor | Role | Data touched | Carve-out attestation | DPA status | Per-vendor file | In prior 7-vendor list | Review date |
|---|---|---|---|---|---|---|---|---|
| 1 | **Supabase** | Primary DB + Auth | ALL customer PII, tenant data, sessions, RLS-governed tables, auth tokens | SOC 2 Type II (verify: supabase.com/security) | Supabase DPA available | [supabase.md](./supabase.md) | Yes | TBD |
| 2 | **Railway** | Backend hosting | API process memory, logs, env vars, secrets (encrypted) | SOC 2 Type II (verify: railway.app/legal) | Railway DPA available | [railway.md](./railway.md) | Yes | TBD |
| 3 | **Contabo** | Compute / VPS | All async-processed data, Redis cache, `/root/.secrets/`, Canada frontend | **No SOC 2** — see compensating controls | No formal DPA | [contabo.md](./contabo.md) | **GAP — not in prior list** | TBD |
| 4 | **Cloudflare** | DNS / DDoS / CDN / Stream / R2 | IPs, live camera relay, cold archive, DNS queries | SOC 2 Type II + ISO 27001 (verify: cloudflare.com/trust-hub) | Cloudflare DPA available | [cloudflare.md](./cloudflare.md) | Yes | TBD |
| 5 | **Stripe** | Payments (Connect) | Payment intents, subscription data, webhook signing secrets, Stripe-Connect merchant tokens | PCI DSS Level 1 + SOC 2 Type II (verify: stripe.com/docs/security) | Stripe DPA via Stripe ToS | [stripe.md](./stripe.md) | **GAP — not in prior list** | TBD |
| 6 | **Square** | POS + billing | OAuth tokens, order write payloads, merchant credentials | PCI DSS Level 1 (verify: squareup.com/us/en/security) | Square DPA via Square ToS | [square.md](./square.md) | Yes | TBD |
| 7 | **Clover** | POS (feature-gated, not yet live) | OAuth tokens, transaction data (when enabled) | Clover/Fiserv PCI DSS Level 1 (verify: clover.com/security) | DPA: verify | [square.md](./square.md) — referenced | **GAP — not in prior list** | TBD |
| 8 | **Toast** | POS (integration pending) | OAuth tokens, transaction data (when enabled) | Toast PCI DSS Level 1 (verify: pos.toasttab.com/security) | DPA: verify | — referenced in square.md | **GAP — not in prior list** | TBD |
| 9 | **OpenRouter / DeepSeek / SambaNova / Groq / Cerebras / OpenAI** | LLM inference (analytics) | Anonymized analytics prompts; no raw PII by design (verify in code) | Varies by provider — see [llm-providers.md](./llm-providers.md) | DPA: verify per provider | [llm-providers.md](./llm-providers.md) | **GAP — not in prior list** | TBD |
| 10 | **Telnyx** | SMS + voice (primary) | Phone numbers, SMS content, call audio, call metadata | SOC 2 (verify: telnyx.com/company/security) | Telnyx DPA available | [telephony.md](./telephony.md) | Yes | TBD |
| 11 | **Twilio** | Telephony fallback + DTMF card capture | Phone numbers, call audio, **raw PAN/CVV in DTMF stream** (HIGH RISK) | PCI DSS Level 1 + SOC 2 (verify: twilio.com/en-us/security) | Twilio DPA available | [telephony.md](./telephony.md) | Yes | TBD |
| 12 | **Vapi** | AI phone demo | Call audio, call transcripts, conversation data | Vapi attestation: **verify** | DPA: verify | [telephony.md](./telephony.md) | **GAP — not in prior list** | TBD |
| 13 | **Deepgram** | Speech-to-text (phone agent) | Speech audio (ephemeral — streamed, not stored by Deepgram per their policy) | Deepgram SOC 2 (verify: deepgram.com/trust) | DPA: verify | [telephony.md](./telephony.md) | Yes | TBD |
| 14 | **AWS Polly** | Text-to-speech (phone agent) | No PII stored; TTS output only | AWS SOC 2 Type II + ISO 27001 | AWS DPA (AWS BAA equivalent) | [telephony.md](./telephony.md) | Yes | TBD |
| 15 | **Resend** | Transactional email | Email addresses, email content, send logs | Resend SOC 2 (verify: resend.com/security) | Resend DPA available | [email.md](./email.md) | Yes | TBD |
| 16 | **Postal (self-hosted)** | Email primary transport | Emails, content, routing logs; **self-hosted = Meridian IS the processor** | No third-party attestation needed (Meridian runs it on Contabo) | N/A (self-hosted) | [email.md](./email.md) | Yes | TBD |
| 17 | **Backblaze B2** | Cold archive | Historical merchant data (DVC-tracked) | Backblaze B2 SOC 2 (verify: backblaze.com/security) | DPA: verify | — | **GAP — not in prior list** | TBD |
| 18 | **PostHog** | Product analytics | Usage metadata, user session events (no raw PII by design) | PostHog SOC 2 Type II (verify: posthog.com/docs/privacy/gdpr) | PostHog DPA available | — | **GAP — not in prior list** | TBD |
| 19 | **Sentry** | Error monitoring | Exception payloads; PII scrubbing configured in `src/api/app.py:23` | Sentry SOC 2 Type II (verify: sentry.io/security/) | Sentry DPA available | — | **GAP — not in prior list** | TBD |
| 20 | **Highlight.io** | APM / tracing | Span data, request traces | Highlight.io attestation: **verify** | DPA: verify | — | **GAP — not in prior list** | TBD |
| 21 | **Convex** | Customer app sync | Dashboard data synced to customer-facing app | Convex SOC 2: **verify** | DPA: verify | — | **GAP — not in prior list** | TBD |
| 22 | **Telegram** | SEO alerting | SEO monitoring output (no customer PII expected; verify) | N/A (consumer app) | No DPA applicable | — | **GAP — not in prior list** | TBD |

---

## Annual Review Procedure

1. Aidan Pierce downloads updated attestation certificates for Supabase, Railway, Cloudflare, Stripe, Square, Telnyx, Twilio, Resend, Deepgram (where publicly available) and stores them in `compliance/evidence/POL-008/vendor-attestations/<vendor>-soc2-<year>.pdf`.
2. For each vendor marked "verify" in the attestation column, locate the current public compliance page and update the status in this table.
3. Check whether DPAs are signed or available online. Confirm GDPR/PIPEDA applicability given Meridian's Canadian customer base.
4. Check for any new third-party integrations added to the codebase since last review (grep `src/` for new API calls, new environment variables in `.env.example`). Add any new vendors to this table within 14 days.
5. Record the review date in the `Review date` column and note it in the quarterly security review (`compliance/evidence/POL-009/quarterly-reviews.md`).
