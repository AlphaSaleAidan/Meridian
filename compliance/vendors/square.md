# Vendor: Square (+ Clover / Toast references)
**Document ID:** VEN-006
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce

---

## Role

Square is Meridian's primary POS integration for restaurant and retail merchants. Meridian acts as a Square OAuth application: merchants authorize Meridian to write orders on their behalf via the Square API. Clover (feature-gated, not yet live in production) and Toast (integration pending) follow the same OAuth pattern and are referenced here.

**Integration paths:**
- Square: `src/square/` (OAuth flow, order write, Square client)
- Clover: `src/clover/` (feature-gated, `CLOVER_ENABLED` flag)
- Toast: `src/toast/` (integration pending)

---

## Data Touched

| Data category | Details |
|---|---|
| Square OAuth tokens | Per-merchant access tokens (`SQUARE_ACCESS_TOKEN` per merchant, stored in Supabase, encrypted at rest via `src/security/encryption.py`) |
| Square merchant IDs | Merchant and location IDs used to route orders |
| Order write payloads | Customer order details (items, modifiers, prices) written to Square `/v2/orders`; Meridian constructs and submits the order |
| Transaction references | Square order IDs returned from the API, stored in Supabase for reconciliation |
| Square webhook events | Order status updates received via webhooks (if configured) |
| Clover OAuth tokens | Same pattern as Square; stored encrypted in Supabase; not yet live |
| Toast OAuth tokens | Same pattern; integration not yet live |

**What Meridian does NOT store:** Raw Square/Clover/Toast payment card data. POS payments are processed by the merchant's Square reader directly; Meridian only writes orders (not payments) to the Square API.

---

## Attestation Status

| Vendor | Attestation | Status |
|---|---|---|
| **Square** | PCI DSS Level 1 Service Provider | Public — verify at [squareup.com/us/en/security](https://squareup.com/us/en/security) |
| **Square** | SOC 2 | Verify at Square's security page — status TBD |
| **Clover / Fiserv** | PCI DSS Level 1 | Clover is a Fiserv company; PCI DSS Level 1 (verify at clover.com) |
| **Toast** | PCI DSS Level 1 | Verify at pos.toasttab.com/security |

**Annual evidence action:** Download Square PCI DSS certificate of compliance → `compliance/evidence/POL-008/vendor-attestations/square-pci-<year>.pdf`. Do the same for Clover and Toast when those integrations go live.

---

## DPA Status

Square's Terms of Service govern data processing. Verify whether Square offers a DPA for Meridian's use case as an OAuth application writing orders on behalf of merchants.

For Clover and Toast: verify DPA availability when those integrations go live. Do not go live with a new POS integration without confirming DPA status.

**Action required:** Document DPA status for Square in `compliance/evidence/POL-008/vendor-attestations/square-dpa-status.md`.

---

## What Breaks if Square Fails

**Impact: HIGH (POS order submission fails for Square merchants)**

- Phone agent cannot submit orders to Square (`src/api/routes/phone.py` → `submit_order` → `/v2/orders`).
- Order history in merchant portal may become stale if Square API is the source of truth for order status.
- Clover/Toast are independent — Square failure does not affect those integrations.

**Recovery:** Meridian has no POS failover. If Square is down, voice orders cannot be submitted. Consider logging failed order attempts for manual re-submission (verify this retry mechanism exists).

---

## Specific Risks & Controls

| Risk | Control | Status |
|---|---|---|
| Square OAuth token leaked | Tokens stored encrypted in Supabase (AES-256-GCM, `src/security/encryption.py`); never stored in Railway env vars or logs in plaintext | Enforced |
| Cross-tenant POS token access | Per-merchant RLS on token table; `require_org_access` dependency enforces org scoping | Enforced — verify in migration + API dependency |
| Square webhook spoofing | Verify Square webhook signature header on all incoming events (confirm implementation) | Verify in `src/square/` |
| Excessive OAuth scope | Square OAuth scope should be minimum required (`ORDERS_WRITE`, `ITEMS_READ`) — verify scope requested in OAuth flow | Verify in OAuth initiation code |
| Clover / Toast go live without DPA | DPA must be verified before enabling feature flags in production | Procedural gate — enforce |

---

## Clover-Specific Notes

Clover is feature-gated behind `CLOVER_ENABLED` flag (per `src/clover/`). It has NOT been applied to production as of 2026-06-28. Before enabling:
- Confirm DPA with Clover/Fiserv
- Download Clover PCI DSS certificate
- Add Clover to the active sub-processor list in this register
- Update `compliance/vendors/README.md` to reflect Clover as active (not gated)

## Toast-Specific Notes

Toast integration is pending (not started). Same pre-live requirements apply as for Clover.

---

## Review Date

TBD — next annual review cycle. Clover and Toast entries to be updated when those integrations go live.
