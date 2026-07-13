# Vendor: Cloudflare
**Document ID:** VEN-004
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce

---

## Role

Global CDN, DNS, DDoS mitigation, TLS termination for all Meridian public endpoints, plus two Meridian-specific integrations:

- **Cloudflare Stream:** Live camera relay from merchant-premises Jetson devices → cloud; camera session archives.
- **Cloudflare R2:** Cold archive storage for historical merchant data (`src/workers/cold_storage.py`).

**Integration paths:** DNS (all Meridian domains), `src/services/cloudflare_stream.py` (camera relay), `src/workers/cold_storage.py` (R2 archive), Cloudflare Pages (if used for static hosting — verify).

---

## Data Touched

| Data category | Details |
|---|---|
| IP addresses and TLS metadata | All client IPs accessing `api.meridian.tips`, `meridian.tips`, and `canada.meridian.tips` pass through Cloudflare |
| Live camera relay (Stream) | Raw video frames streamed from Jetson devices through Cloudflare Stream; Meridian controls retention settings |
| Camera session archives (R2) | Historical video clips or analytics data stored in R2 for cold retrieval; content defined by `src/workers/cold_storage.py` |
| DNS queries | All DNS lookups for Meridian domains processed by Cloudflare DNS |
| WAF logs | HTTP request logs with headers, paths, and partial bodies (PII exposure depends on WAF log level configuration) |

**High-sensitivity data point:** Cloudflare Stream relay contains live video of merchant premises, which may include images of customers and staff. This is biometric-adjacent data. Retention policy for Stream archives must be explicitly defined and enforced.

---

## Attestation Status

| Attestation | Status | Source |
|---|---|---|
| SOC 2 Type II | Public — verify at [cloudflare.com/trust-hub](https://www.cloudflare.com/trust-hub/) | Download annually |
| ISO 27001 | Cloudflare holds ISO 27001 certification | Same trust hub |
| GDPR | Cloudflare offers a DPA covering GDPR | cloudflare.com/gdpr/introduction |

**Annual evidence action:** Download Cloudflare SOC 2 Type II report → `compliance/evidence/POL-008/vendor-attestations/cloudflare-soc2-<year>.pdf`.

---

## DPA Status

Cloudflare provides a Data Processing Addendum available at cloudflare.com/gdpr. Confirm whether it has been executed for the Meridian Cloudflare account. Given Canadian customer data (PIPEDA) and potential EU merchant data, confirm DPA coverage.

**Action required:** Locate Cloudflare account → confirm DPA is accepted/executed. Record in `compliance/evidence/POL-008/vendor-attestations/cloudflare-dpa-status.md`.

---

## What Breaks if Cloudflare Fails

**Impact: HIGH (all external traffic disrupted)**

- All public Meridian endpoints go offline immediately (Cloudflare is the DNS resolver and TLS terminator for all domains).
- Even if Railway and Supabase are operational, clients cannot reach `api.meridian.tips` without Cloudflare.
- Live camera relay (Stream) stops — merchants lose real-time camera analytics.
- R2 cold archive writes queue or fail — no immediate data loss (cold archive is archival, not operational).

**Recovery:** If Cloudflare experiences a regional or global outage, there is no immediate failover option since DNS is also Cloudflare-managed. Recovery is dependent on Cloudflare's own resilience. Cloudflare's 300+ PoP architecture makes global outages extremely rare but not impossible.

---

## Specific Risks & Controls

| Risk | Control | Status |
|---|---|---|
| Cloudflare Stream archive data retained indefinitely | Define and enforce stream retention period in Cloudflare Stream settings; document policy | Verify retention settings |
| WAF logs capture PII from request bodies | Set WAF logging to capture headers/paths only, not request bodies, or configure PII masking | Verify WAF log config |
| Cloudflare account takeover | Cloudflare account secured by Aidan Pierce's Google SSO + hardware key (confirm — see POL-007 DECISION) | Partial — verify |
| DNS hijack via Cloudflare account compromise | All DNS is Cloudflare-managed; account takeover = DNS hijack of all Meridian domains | Enforce 2FA + access logging |
| R2 bucket policy too permissive | R2 bucket should be private (no public access); accessible only via signed URLs or internal workers | Verify R2 bucket ACL |

---

## Review Date

TBD — next annual review cycle. Next attestation download: January 2027.
