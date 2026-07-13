# Vendor: Email Transport (Postal self-hosted + Resend)
**Document ID:** VEN-009
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce

---

## Role

Meridian uses TWO separate email transport paths that must be distinguished:

1. **Postal (self-hosted MTA on Contabo):** Primary transactional email transport for application emails (order confirmations, rep notifications, merchant alerts). Meridian IS the processor — Postal runs on Contabo `209.126.80.45`.
2. **Resend:** Cloud-based email API used as fallback or for specific high-delivery email flows (verify which flows use Resend vs. Postal in `src/email/postal_client.py`).

**Important:** These email paths are separate from the **Supabase Auth SMTP transport** used for login/password-reset emails. Fixing one transport does NOT fix the other.

**Integration path:** `src/email/postal_client.py` (both Postal and Resend are implemented here based on routing logic)

---

## Postal (Self-Hosted)

### Role

Postal is an open-source mail delivery platform (postal.atech.media) self-hosted on Contabo. It provides SMTP relay, delivery tracking, bounce handling, and email queuing. Because it is self-hosted, **Meridian is the data controller AND data processor** for Postal — there is no third-party sub-processor to carve out to.

### Data Touched

- Recipient email addresses (merchants, reps, customers who receive transactional emails)
- Email content (order confirmations, agent reports, rep alerts, diagnostic summaries)
- Delivery status and bounce logs (stored in Postal's database on Contabo)
- SMTP credentials for outbound sending (stored in `/root/.secrets/` or Postal's own credential store)

All email data processed by Postal resides on Contabo `209.126.80.45`. The Contabo security posture (no SOC 2) therefore applies to Postal email data. See [contabo.md](./contabo.md).

### Security Controls

| Control | Detail | Status |
|---|---|---|
| TLS for outbound SMTP | Postal enforces STARTTLS for outbound email delivery | Verify in Postal dashboard → TLS settings |
| DKIM signing | Postal must be configured to DKIM-sign all outbound email from `meridian.tips` | Verify DKIM record in Cloudflare DNS and Postal signing key |
| SPF record | `v=spf1 include:postal-server-ip ... -all` must be set in Cloudflare DNS | Verify |
| DMARC policy | DMARC record should be present for `meridian.tips` and aligned | Verify |
| Access to Postal web UI | Postal web dashboard must be secured (non-default credentials, not publicly exposed without auth) | Verify Postal admin credentials are in 1Password; not using default password |
| Log retention | Postal logs email content and delivery attempts; define and enforce a retention period | Set retention period in Postal settings — recommend 90 days |
| Resend API key rotation | Resend API key (`re_*`) stored in Railway env vars and `/root/.secrets/`; must be rotated if exposed | Rotate cadence: annually or on suspected exposure |

### Attestation Status

No third-party attestation applicable — Postal is self-hosted software. Meridian is responsible for securing the Postal instance on Contabo. The Contabo physical security gap (documented in [contabo.md](./contabo.md)) applies here.

**Annual action:** Review Postal version for security updates. Check postal.atech.media for security advisories. Update Postal if vulnerabilities are published.

### DPA Status

Not applicable — Postal is self-hosted software.

---

## Resend

### Role

Cloud email delivery API used as primary (for some flows) or fallback transport. Resend provides deliverability optimization, email logs, and send-event webhooks.

**Verified domain:** `poachrr.io` (Resend); verify whether `meridian.tips` is also verified in Resend.

### Data Touched

- Recipient email addresses
- Email content (whatever Meridian's code sends via the Resend API)
- Send logs and delivery events (Resend retains these for a vendor-defined period)
- Resend API key (`re_*`) — stored in Railway env vars and `/root/.secrets/`

### Attestation Status

| Attestation | Status |
|---|---|
| SOC 2 | Resend SOC 2 — verify at [resend.com/security](https://resend.com/security) |

**Annual evidence action:** Download Resend SOC 2 → `compliance/evidence/POL-008/vendor-attestations/resend-soc2-<year>.pdf`.

### DPA Status

Resend provides a DPA. Verify at resend.com/legal and confirm it is accepted. Relevant for Canadian and EU recipient email data under PIPEDA/GDPR. Document in `compliance/evidence/POL-008/vendor-attestations/resend-dpa-status.md`.

### What Breaks if Resend Fails

Flows routed through Resend stop delivering. Postal on Contabo is the fallback (or primary, depending on routing). Audit `src/email/postal_client.py` to confirm which flows use which transport and whether the fallback is automatic.

---

## Email Path Disambiguation (Action Required)

Audit `src/email/postal_client.py` and all call sites to produce a table of:

| Email type | Which transport | Notes |
|---|---|---|
| Order confirmation to merchant | ? | Identify |
| Rep daily report | ? | Identify |
| After-hours order alert | ? | Identify |
| Supabase Auth (login, password reset) | **Supabase Auth SMTP** (separate — NOT Postal/Resend) | This is independent |
| CA portal onboarding | ? | Identify |
| SEO alert | ? | Identify |

Document in `compliance/evidence/POL-009/email-transport-map.md`. This disambiguation is required before an auditor can assess whether email delivery controls are adequate.

---

## Consolidated Evidence Actions for Email

1. Download Resend SOC 2 → `compliance/evidence/POL-008/vendor-attestations/resend-soc2-<year>.pdf`
2. Confirm Resend DPA executed → `resend-dpa-status.md`
3. Verify Postal DKIM, SPF, DMARC configuration for `meridian.tips`
4. Confirm Postal admin credentials are rotated from defaults and stored in 1Password
5. Set Postal log retention policy (recommend 90 days)
6. Complete email transport disambiguation table

## Review Date

TBD — next annual review cycle. Verify Resend SOC 2 and DKIM/SPF/DMARC configuration by next quarterly review.
