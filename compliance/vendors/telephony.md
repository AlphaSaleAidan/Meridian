# Vendor: Telephony (Telnyx / Twilio / Vapi / Deepgram / AWS Polly)
**Document ID:** VEN-008
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce

---

## Role

Meridian's phone agent system uses multiple telephony vendors across the call lifecycle: Telnyx for primary inbound/outbound SIP and SMS, Twilio as fallback and DTMF card capture, Vapi for the AI phone demo, Deepgram for real-time speech-to-text, and AWS Polly for text-to-speech responses.

**Integration paths:**
- Telnyx: `src/sms/client.py`, phone routing config, Canadian DID `+17823585534`
- Twilio: `src/api/routes/phone.py` (DTMF card capture path)
- Vapi: `src/api/routes/vapi_webhook.py`
- Deepgram: `src/api/routes/phone.py` (STT streaming)
- AWS Polly: `src/api/routes/phone.py` (TTS response generation)

---

## Telnyx (Primary Telephony)

### Role
Primary SIP provider, SMS transport, and DID management. All live inbound calls to Meridian's Canada test line (`+17823585534`, CA DID) route through Telnyx. TeXML app "Meridian Phone Calls" (App ID `2975326560921322657`) is the active Telnyx voice application.

### Data Touched
- Phone numbers (caller DID, Meridian DID)
- SMS message content (order confirmations, after-hours messages)
- Call audio recordings (if Telnyx call recording is enabled — verify whether Meridian has enabled Telnyx-side recording)
- Call metadata (duration, timestamp, call legs)
- TeXML webhook payloads (include caller phone number and call state)

### Attestation Status
| Attestation | Status |
|---|---|
| SOC 2 | Telnyx SOC 2 — verify at [telnyx.com/company/security](https://telnyx.com/company/security) |
| STIR/SHAKEN compliance | Required for legitimate CNAM + caller ID; verify Telnyx compliance |

### DPA Status
Telnyx provides a DPA. Verify it has been accepted for the Meridian Telnyx account. Document in `compliance/evidence/POL-008/vendor-attestations/telnyx-dpa-status.md`.

### What Breaks if Telnyx Fails
All inbound phone calls to Meridian's Canada DID fail. SMS sending fails. Voice agent is unreachable. Twilio fallback may partially compensate (verify routing fallback logic).

---

## Twilio (Fallback + DTMF Card Capture)

### Role
Telephony fallback and — critically — the path used for DTMF-based card number capture (raw PAN/CVV via keypad tones during phone calls).

### Data Touched

**HIGH RISK — PAN/CVV in call audio:**
- **Raw Payment Account Numbers (PAN) and CVV** may be present in Twilio call audio streams during DTMF card capture flows (`src/api/routes/phone.py`).
- Caller phone numbers
- Call audio recordings (if recording is enabled)
- Transcription content (if Twilio transcription is used — would include spoken card numbers)
- DTMF tone sequences (which ARE the card digits if DTMF capture is active)

**This is Meridian's highest PCI-scope risk.** Any path where Twilio records call audio that includes DTMF card entry makes Twilio a PCI DSS in-scope component for those calls. Meridian's PCI scope could escalate from SAQ A to SAQ D if Twilio records or retains audio containing card data.

### Attestation Status
| Attestation | Status |
|---|---|
| PCI DSS Level 1 | Twilio is a PCI DSS Level 1 Service Provider — verify at [twilio.com/en-us/security](https://www.twilio.com/en-us/security) |
| SOC 2 Type II | Twilio SOC 2 Type II (public) | verify |
| GDPR / HIPAA | Twilio offers BAA (HIPAA) and DPA (GDPR) — GDPR DPA available |

### DPA Status
Twilio provides a DPA at twilio.com/legal/data-protection-addendum. Confirm it is accepted/executed for the Meridian Twilio account. **This is HIGH PRIORITY given PCI-scope implications.**

### What Breaks if Twilio Fails
Fallback telephony is unavailable. DTMF card capture path fails (which may be acceptable if that feature is gated). SMS fallback via Telnyx should remain functional.

### Critical Action Required — PCI Scope

## ## DECISION (Aidan) — Twilio DTMF Call Recording and PCI Scope

**Context:** If Twilio records call audio that includes DTMF card digits, those recordings contain raw PANs. This is a PCI DSS violation if Twilio's recording retention is not a compliant cardholder data environment. Twilio IS PCI DSS Level 1, but Meridian must confirm:
1. Is Twilio call recording enabled for the DTMF card capture path? If yes, what is the retention period?
2. Are DTMF tones (card digits) included in the recorded audio or are they suppressed (DTMF masking)?
3. Has Meridian completed PCI SAQ A-EP or SAQ D to account for the Twilio path?

**Options:**
1. Confirm Twilio DTMF masking is enabled (Twilio supports `<Pay>` verb with built-in PCI-compliant card capture that keeps PAN out of recordings). Migrate DTMF card capture to Twilio `<Pay>` verb.
2. Disable call recording entirely on the DTMF card capture path.
3. Accept the risk with documented rationale and Twilio PCI DSS carve-out.

**Decision required from Aidan.** This is a HIGH finding in the risk register.

---

## Vapi (AI Phone Demo)

### Role
AI-powered phone agent platform used for the live demo line. Vapi provides voice activity detection, LLM orchestration, and call flow management. Not in Meridian's prior 7-vendor list — **this is a gap now resolved here.**

**Phone number:** `+13802409535` (Vapi assistant `13e00df9`)
**Webhook:** `/api/vapi/webhook`
**Integration:** `src/api/routes/vapi_webhook.py`

### Data Touched
- Call audio (streamed through Vapi's infrastructure)
- Call transcripts (Vapi transcribes calls and sends transcripts via webhook)
- Conversation data (full agent-customer dialog)
- Caller phone numbers

### Attestation Status
Vapi is a relatively early-stage AI company. SOC 2 attestation: **verify at vapi.ai/security**. As of authoring this document, Vapi's SOC 2 status is unconfirmed — treat as a gap until verified.

### DPA Status
Verify at vapi.ai/privacy or legal pages. **Action required:** Confirm DPA availability and execute for Meridian account. Document in `compliance/evidence/POL-008/vendor-attestations/vapi-dpa-status.md`.

### What Breaks if Vapi Fails
The live demo phone line (`+13802409535`) becomes unreachable. Demo calls cannot be completed. Live production Telnyx-based phone agent is unaffected (separate infrastructure).

---

## Deepgram (Speech-to-Text)

### Role
Real-time speech-to-text streaming for the Meridian phone agent. Caller audio is streamed to Deepgram for transcription; transcripts are passed to the LLM for response generation.

**Integration:** `src/api/routes/phone.py`

### Data Touched
- Caller speech audio (streamed, ephemeral — Deepgram processes in-stream and does not store audio after transcription per their privacy policy; **verify current Deepgram data retention policy**)
- Transcribed text (returned to Meridian; Deepgram may retain transcripts for model training unless opted out)

### Attestation Status
Deepgram SOC 2: verify at [deepgram.com/trust](https://deepgram.com/trust). Status: TBD.

### DPA Status
Deepgram provides a DPA. Verify whether Meridian has opted out of data-for-training retention. Document in `compliance/evidence/POL-008/vendor-attestations/deepgram-dpa-status.md`.

**Action required:** Confirm Deepgram's data retention settings for Meridian's API key. Opt out of data retention for training if Meridian has not already done so.

---

## AWS Polly (Text-to-Speech)

### Role
Text-to-speech synthesis for phone agent responses. Meridian's backend constructs response text, sends to AWS Polly, receives audio, and plays back to caller.

### Data Touched
- Response text (generated by LLM; contains order confirmations, menu information — no raw PII stored by Polly)
- No persistent data: AWS Polly processes the TTS request and returns audio; it does not store text or audio after synthesis

### Attestation Status
AWS SOC 2 Type II + ISO 27001 (underlying AWS infrastructure). Polly is in scope for AWS's standard compliance framework.

### DPA Status
Covered by the AWS Customer Agreement. No separate DPA required beyond AWS's standard terms.

---

## Consolidated Evidence Actions for Telephony

1. Download Telnyx SOC 2 → `compliance/evidence/POL-008/vendor-attestations/telnyx-soc2-<year>.pdf`
2. Confirm Telnyx DPA executed → `telnyx-dpa-status.md`
3. Download Twilio PCI DSS / SOC 2 → `twilio-soc2-<year>.pdf` + `twilio-pci-<year>.pdf`
4. Confirm Twilio DPA executed → `twilio-dpa-status.md`
5. Verify Vapi SOC 2 status → `vapi-attestation-status.md`
6. Confirm Vapi DPA → `vapi-dpa-status.md`
7. Verify Deepgram SOC 2 + confirm data retention opt-out → `deepgram-dpa-status.md`
8. Resolve DECISION on Twilio DTMF card recording PCI scope

## Review Date

TBD — prioritize Twilio PCI-scope DECISION within 30 days. Full attestation review: January 2027.
