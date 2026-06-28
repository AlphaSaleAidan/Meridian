# Data Retention and Disposal Policy
**Document ID:** POL-008
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder, US signing authority)
**Review Cadence:** Annual, or on any schema change affecting retention defaults or deletion logic
**Parent Policy:** [information-security-policy.md](./information-security-policy.md)

---

## Purpose

Define how long Meridian retains each class of data, how data is securely disposed of at end-of-life, and who is responsible for each deletion action. This policy also identifies the current gap between stated retention periods and implemented deletion mechanisms — specifically the unscheduled `cleanup_expired_visitors()` function and the absence of R2 cold-object deletion — as the highest-priority remediation item in the current control environment.

Meridian is not SOC 2 certified. This policy is part of an internal control framework authored to support readiness for a future Type II examination.

---

## Scope

Covers all data stores within the Meridian system boundary:
- **Supabase** managed PostgreSQL, project `kbuzufjxwflrutowwnfl` (AWS us-east-1): all tables under the `public` schema including `transactions`, `daily_revenue`, `pos_connections`, `business_users`, `phone_orders`, `phone_call_logs`, `vision_visitors`, `vision_events`, `customer_journeys`, `casl_consent_records`, `compliance_acceptances`, `privacy_requests`, `breach_log`
- **Cloudflare R2** bucket `meridian-archives` — cold archive written by `src/workers/cold_storage.py`
- **Redis** on Contabo VPS (209.126.80.45) — session cache, Celery queues
- **Merchant-premises Jetson edge devices** (`edge/`) — local camera buffers, embeddings, detection frames
- **Railway process memory** — ephemeral; relevant only for the phone-pay PAN/CVV path (see §3.5)

---

## Procedure

### 3.1 Retention Schedule

| Data Class | Table / Store | Retention Period | Legal Basis | Notes |
|---|---|---|---|---|
| POS transaction data | Supabase `transactions`, `daily_revenue`, `daily_product_performance` | 3 years from collection | Business records, merchant contract term + 1 year | Aggregates retained; line-item detail may be archived to R2 after 12 months |
| POS OAuth tokens | Supabase `pos_connections` | Deleted within 30 days of merchant POS disconnect or account termination | Minimum necessary | Encrypted AES-256-GCM at rest; delete via `DELETE WHERE org_id = ?` on disconnect event |
| Merchant PII (name, email) | Supabase `business_users` | Duration of active account + 60 days post-termination | SLA §7 deletion commitment | See §3.4 — 60-day termination delete is currently unimplemented |
| Phone-order records | Supabase `phone_orders` | 3 years from order date | Business records | Does not include raw PAN/CVV (never persisted) |
| Phone call logs with caller number | Supabase `phone_call_logs` | 3 years from call date | CASL / business records; caller number = PII | Caller phone visible in `caller_phone` column; confirm RLS blocks cross-org queries |
| Camera visitor records (re-ID) | Supabase `vision_visitors` | 90 days from `expires_at` (schema default `now() + INTERVAL '90 days'`) | Minimum necessary for analytics window | **See DECISION §3.6 — 90-day schema conflicts with 30-day posture doc claim** |
| Camera events | Supabase `vision_events` | 90 days (same `expires_at` cascade as `vision_visitors`) | Minimum necessary | Cascade-delete on parent `vision_visitors` deletion |
| Camera↔POS journeys | Supabase `customer_journeys` | 90 days (align with `vision_visitors`) | Minimum necessary; highest-sensitivity Tier 3 data | Explicitly delete on `vision_visitors` expiry; confirm FK cascade or manual delete job |
| VIP face embeddings | Merchant Jetson edge only | Until merchant disables VIP feature or account termination | Biometric: minimum necessary | Must not be synced to Supabase or R2; deletion on Jetson must be verified at offboarding |
| CASL consent records | Supabase `casl_consent_records` | 3 years from consent action | CASL enforcement requirement | Applies to both express and implied consent records |
| Compliance acceptances | Supabase `compliance_acceptances` | 3 years from acceptance date | Audit trail for SHA-256 doc hashes | — |
| Privacy rights requests | Supabase `privacy_requests` | 3 years from request completion | PIPEDA / Quebec Law 25 audit trail | Includes deadline tracking (30-day deadline per `compliance.py:215`) |
| Breach log | Supabase `breach_log` | 24 months minimum from discovery date | Regulatory notification audit trail | Per posture doc `MERIDIAN_COMPLIANCE_POSTURE.md:318` |
| Cold archive (R2) | Cloudflare R2 `meridian-archives` | **No current deletion schedule (open finding — see §3.3)** | Undefined | `cold_storage.py` writes; nothing reads or deletes |
| Redis cache / Celery queues | Contabo Redis | TTL-governed per queue; no persistent data | Ephemeral | Ensure no PII in queue payloads; verify Celery task serialisation |
| Raw PAN/CVV | Railway process memory (`card_on_phone.CardCapture`) | **Never persisted**; cleared immediately after `charge()` via `clear_capture(call_sid)` | PCI DSS — no storage of full track data or CVV post-authorisation | See §3.5 — verify `clear_capture` is called on all code paths including error paths |

---

### 3.2 Deletion Trigger Events

| Trigger | Action Required | Responsible Party |
|---|---|---|
| `vision_visitors.expires_at < now()` | Delete row; cascade to `vision_events`; also delete matching `customer_journeys` | Scheduled job (pg_cron or Celery Beat) — **currently unscheduled; see §3.3** |
| Merchant account termination | Delete `business_users`, `pos_connections` (within 60 days); delete all `vision_*` and `customer_journeys` for org; revoke POS OAuth tokens; remove from R2 cold archive | Aidan Pierce (manual) — **currently unimplemented; see §3.4** |
| Privacy deletion request (POST /api/privacy/request, type=deletion) | Delete all Tier 2/3 data for `user_id`; export omission of `transactions`/`vision`/`journeys` is an open gap (see §3.5) | Aidan Pierce (manual + `compliance.py` scaffolding) |
| CASL unsubscribe | Update `casl_consent_records.consent_status`; suppress future sends; retain record 3 years | `src/compliance/casl_guard.py` (automated instant unsubscribe) |
| Employee / contractor offboarding | Revoke GitHub access, Railway access, Supabase MFA device; delete any temporary credentials | Aidan Pierce within 24 hours of departure |

---

### 3.3 Open Finding: `cleanup_expired_visitors()` is Unscheduled (HIGH PRIORITY)

The function `cleanup_expired_visitors()` is defined in `supabase/migrations/20260501_004_vision_intelligence.sql:97` and correctly deletes `vision_visitors` rows where `expires_at < now()`. However, **this function has no scheduler** — no `pg_cron` job in any migration, and no Celery Beat task in `ecosystem.config.js`.

**Consequence:** The 90-day deletion promise is theoretical. In production, `vision_visitors` rows (including `person_id` re-ID data and demographics) accumulate indefinitely.

## DECISION (Aidan — implementation required)

Choose one scheduling path and implement it:

**Option A — pg_cron (preferred for Supabase):**
Add to a new migration:
```sql
SELECT cron.schedule(
    'cleanup-expired-visitors',
    '0 3 * * *',   -- 03:00 UTC daily
    $$SELECT cleanup_expired_visitors()$$
);
```
Requires `pg_cron` extension enabled on Supabase project `kbuzufjxwflrutowwnfl`.

**Option B — Celery Beat task:**
Add a periodic task in `ecosystem.config.js` / `src/workers/` that calls a `supabase.rpc('cleanup_expired_visitors')` daily. Runs on Contabo. More complex but avoids a Supabase extension dependency.

**Evidence of resolution:** `compliance/evidence/POL-008/cleanup-scheduler-evidence.md` — screenshot or log of the first scheduled run, with timestamp and row count deleted.

---

### 3.4 Open Finding: 60-Day Termination Deletion is Unimplemented (HIGH PRIORITY)

The merchant SLA commits to secure deletion of customer data within 60 days of account termination. The gap analysis (`compliance/gap-analysis.md:123`) confirms this is unimplemented. There is no offboarding workflow, no deletion script, and no tracking table for terminated accounts awaiting data disposal.

**Minimum required implementation:**
1. A `terminated_orgs` table (or flag on `businesses`) recording the termination date
2. A manual or scheduled procedure (Celery Beat, Supabase function, or CLI script) that deletes all rows scoped to `org_id` across: `pos_connections`, `vision_visitors`, `vision_events`, `customer_journeys`, `phone_orders`, `phone_call_logs`, `transactions` (or anonymise), and `business_users`
3. R2 deletion of all objects prefixed with `{org_id}/` in `meridian-archives`
4. Jetson offboarding: physical or remote wipe of face embeddings and local cache
5. A signed deletion confirmation document sent to the merchant within 5 business days of deletion

**Evidence of resolution:** `compliance/evidence/POL-008/termination-deletion-log.md` — log entry per terminated org, with date range (termination date → deletion date), confirming ≤60-day window.

---

### 3.5 Open Finding: Privacy Deletion Request Does Not Cover All Data Classes

The `/api/privacy/request` endpoint (`src/api/routes/compliance.py:208`) accepts deletion requests and records them in `privacy_requests`. The data-export path (`compliance.py:262`) includes `casl_consent_records` and `privacy_requests` themselves, but **does not export or delete** `transactions`, `vision_visitors`, `vision_events`, or `customer_journeys`.

Under PIPEDA and Quebec Law 25, an individual's right to access their personal information includes all personal information held, regardless of storage location. The deletion right requires erasure of all personal information, not a subset.

**Remediation:** Extend the deletion handler in `compliance.py` to:
- Identify all tables referencing `user_id` (or `phone_orders.phone_number`) for the requesting individual
- Include `transactions`, `phone_orders`, `phone_call_logs`, `vision_visitors` (matched on session or phone), and `customer_journeys` in both export and deletion paths
- Log the extended deletion in `privacy_requests` with a `tables_affected` JSON field

---

### 3.6 Retention-Period Inconsistency — Camera Data

See [data-classification.md §3.4](./data-classification.md) for the DECISION. Once Aidan selects the authoritative period (30 or 90 days), update:
- The pg_cron or Celery Beat interval (§3.3)
- The `expires_at` default in a new migration
- The merchant-facing privacy disclosure language

---

### 3.7 Secure Disposal Standards

| Media / Store | Disposal Method |
|---|---|
| Supabase rows | `DELETE FROM <table> WHERE ...`; Supabase manages physical page reclamation (managed Postgres) |
| R2 cold objects | S3 `DeleteObject` API call against `meridian-archives` bucket per object key; no bulk lifecycle rule currently configured |
| Redis | `DEL` key; or flush on worker restart; no PII should persist > TTL |
| Jetson edge | `rm -rf` of embedding store + docker volume; physical device return to merchant at offboarding; confirm erasure in offboarding checklist |
| Railway process memory | No action needed — ephemeral; processes restart frequently; no PAN/CVV persisted |
| Developer laptops | Not in Meridian system boundary; Aidan uses FileVault/BitLocker; contractor devices governed by their NDA |

**No magnetic media or tape** is used. Physical destruction procedures are not required.

---

## Roles

| Role | Responsibility |
|---|---|
| Aidan Pierce (Policy Owner) | Implement and verify scheduled deletion jobs; execute manual termination-deletion procedure; resolve all open findings; approve any retention-period exception |
| CA Admins (Nguyen, Cheung) | Report any merchant termination request within 24 hours so the 60-day clock starts; no direct DB deletion authority |
| Future engineer | Must not add new data persistence without first consulting this policy and assigning a retention period |

---

## Owner

Aidan Pierce

---

## Review Cadence

Annual. Also triggered by: any new table added to schema, any change to the merchant SLA retention commitments, any privacy rights complaint, or any enforcement action by the OPC (Canada) or CNIL equivalent.

---

## Evidence that this Policy Operates

Auditors should verify:
1. **`compliance/evidence/POL-008/cleanup-scheduler-evidence.md`** — proof that `cleanup_expired_visitors()` runs on schedule (pg_cron job definition OR Celery Beat task config + execution log with row counts).
2. **`compliance/evidence/POL-008/termination-deletion-log.md`** — per-org log of termination date and confirmed deletion date; all entries should show ≤60-day window.
3. **`supabase/migrations/20260501_004_vision_intelligence.sql`** (line 97) — function definition; pg_cron evidence confirms it is scheduled.
4. **`src/workers/cold_storage.py`** — auditors should confirm whether an R2 deletion path exists (currently absent); the risk register (`compliance/risk/risk-register.md`) should show R7 with a resolution date.
5. **This file's git history** — `git log --follow compliance/policies/data-retention-disposal.md`.

---

## Related Policies

- [information-security-policy.md](./information-security-policy.md) — POL-001 master policy
- [data-classification.md](./data-classification.md) — POL-007 tier definitions, retention-period DECISION, resale-tier gap
- [vendor-third-party-management.md](./vendor-third-party-management.md) — POL-009 sub-processor data handling (Supabase, R2, Telnyx)
- [encryption-cryptography.md](./encryption-cryptography.md) — POL-004 encryption-at-rest controls that complement deletion
