# Physical & Environmental Security Policy
**Document ID:** POL-008
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder, US signing authority)
**Review Cadence:** Annual; triggered on new infrastructure deployment or merchant-premises device incident

---

## Purpose

Document Meridian's physical and environmental security posture. Meridian operates no data center of its own. This policy records the complete carve-out of physical/environmental security to named subservice organizations, and defines Meridian's specific obligations at the boundary of merchant-premises edge camera devices and admin endpoint hardware.

---

## Scope

- All Meridian server-side infrastructure: Supabase (AWS us-east-1), Railway (AWS-backed), Contabo VPS (St. Louis, MO), Cloudflare global PoPs.
- Edge computing devices: NVIDIA Jetson camera nodes deployed on merchant premises.
- Endpoint devices: laptops and workstations used by Aidan Pierce, Aidan Nguyen, and Enoch Cheung to administer Meridian systems.

---

## Procedure

### 1. Data Center Physical Security — Carved Out to Subservice Organizations

Meridian does not own, lease, or operate any data center, server room, or co-location cabinet. All server-side compute, storage, and networking runs in facilities operated by the following subservice organizations:

| Subservice Org | What Meridian runs there | Physical location | Physical security attestation | Annual attestation evidence |
|---|---|---|---|---|
| **Supabase** (on AWS us-east-1) | Primary database (Postgres), Auth, Storage | AWS N. Virginia, US | Supabase SOC 2 Type II (public); AWS undergoes ISO 27001, SOC 1/2/3 examinations independently | `compliance/evidence/POL-008/vendor-attestations/supabase-soc2-<year>.pdf` |
| **Railway** | FastAPI backend (`api.meridian.tips`), env vars, deployment logs | AWS us-east (Railway-managed) | Railway SOC 2 Type II (public) | `compliance/evidence/POL-008/vendor-attestations/railway-soc2-<year>.pdf` |
| **Contabo** | Async workers (Celery/Beat, Redis, DeerFlow, Garry, Kimi K2.6 gateway), Contabo-hosted Canada frontend, PM2-managed processes | St. Louis, MO data center | **No independent SOC 2 or ISO 27001 — this is a known gap.** Physical security is Contabo's operational responsibility. | No attestation available. See compensating controls below. |
| **Cloudflare** | DNS, TLS termination, DDoS mitigation, Cloudflare Stream (camera relay), R2 cold-archive | 300+ global PoPs | Cloudflare SOC 2 Type II, ISO 27001 (public) | `compliance/evidence/POL-008/vendor-attestations/cloudflare-soc2-<year>.pdf` |

**Contabo compensating controls (for the absence of SOC 2):**
- Supabase holds canonical customer data; Contabo processes transient workloads and caches only.
- All data in transit to/from Contabo is TLS 1.2+ encrypted.
- SSH access to `209.126.80.45` is key-only (`PasswordAuthentication no`); Aidan Pierce's SSH private key is stored in 1Password (hardware-encrypted vault), not on disk.
- All secrets on the VPS live in `/root/.secrets/` (`chmod 700`); this directory is excluded from any backup automation that could leak it.
- No customer PII is logged to disk on Contabo in plaintext; application-level log filtering (`src/api/app.py` Sentry integration scrubs PII fields before any log emission).
- Contabo is a single-point-of-failure for async workers and the Canada frontend. This is documented as a High risk in `compliance/risk/register.md`. Mitigation: Railway backend remains the canonical API; Contabo failure degrades async processing but does not expose data.

**Annual evidence collection:** Aidan Pierce downloads current third-party attestation certificates (Supabase, Railway, Cloudflare) each year and stores them in `compliance/evidence/POL-008/vendor-attestations/`. Certificates are linked from `compliance/vendors/<vendor>.md`. For Contabo, re-check annually whether SOC 2 has been obtained.

---

### 2. Merchant-Premises Edge Devices (Jetson Camera Nodes)

Meridian deploys NVIDIA Jetson edge devices on merchant premises (restaurants, retail locations) for the AI camera vision product. These devices run inference on-premises and relay streams to Cloudflare Stream.

**Boundary of responsibility:**

| Responsibility | Party |
|---|---|
| Physical security of the Jetson hardware (locks, mounting, access restriction) | **Merchant** |
| Software security (firmware, models, encrypted comms, on-device data retention) | **Meridian** |
| Physical security of the facility housing the device | **Merchant** |

This boundary is documented in the Merchant Agreement. See [DECISION — Merchant Agreement Clause](#decision--merchant-agreement-physical-security-clause) below.

**Meridian software obligations for edge devices:**

**2.1 On-device data retention**

Raw video frames are NOT stored persistently on the Jetson device. The device processes frames in memory and discards them after inference. Inference embeddings (numeric vectors only, no identifiable images) may cache locally. Retention cap: 90 days, enforced by an on-device cleanup process.

## DECISION (Aidan) — On-Device Cleanup Verification

**Context:** The 90-day embedding cache cleanup needs to be confirmed as implemented. If the Jetson cleanup process lives at `src/workers/jetson_cleanup.py` (or equivalent), document the exact mechanism and confirm it runs on a cron schedule.

**Action required:** Locate or write the Jetson cleanup routine, document its schedule and what it deletes. Store a sample cron output in `compliance/evidence/POL-008/jetson-cleanup-sample.log`. If no cleanup is yet implemented, create a ticket and treat this as a High risk in the risk register until resolved.

**2.2 Communication security**

All video relay from Jetson to Cloudflare Stream uses HTTPS (TLS 1.3). The device authenticates to Cloudflare Stream using a per-device token stored in the device's encrypted filesystem partition (if supported by Jetson OS) or in a restricted file (`chmod 600`, accessible only by the inference process user). Per-device tokens — not a shared secret — so revocation is surgical.

**2.3 Tamper and theft response**

If a Jetson device is reported stolen, tampered with, or goes offline unexpectedly in a way consistent with tampering:

1. Aidan Pierce is notified (via merchant or monitoring alert) and initiates the response.
2. **Within 2 hours:** Rotate the affected device's Cloudflare Stream API token (Cloudflare dashboard → Stream → API tokens → revoke by token ID).
3. **Within 2 hours:** Set `is_active = false` on the device's row in the Supabase `merchant_devices` table (disables data ingestion from that device at the API layer).
4. **Within 24 hours:** Notify the merchant in writing (email to primary contact on file) describing the action taken and what data, if any, was on the device at time of incident.
5. **Log the incident** in `compliance/evidence/POL-008/device-incidents.md` with: device ID, merchant, date, nature of incident, response steps, and resolution.
6. Assess whether the incident constitutes a data breach under applicable law (given embeddings-only on-device data, this is likely not a breach, but assess and document the reasoning).

**Device inventory:** All deployed Jetson devices are tracked in the Supabase `merchant_devices` table (fields: device_id, merchant_id, location, install_date, is_active, cloudflare_stream_token_id). This table is the authoritative inventory. An export is included in quarterly evidence collection.

---

### 3. Admin Endpoint Security

Aidan Pierce, Aidan Nguyen, and Enoch Cheung each use personal laptops to administer Meridian systems. Laptop compromise is a high-impact event (SSH key theft, browser session hijacking to Railway/Supabase/GitHub).

## DECISION (Aidan) — Admin Endpoint Controls

**Context:** Full-disk encryption and automatic screen lock are the two highest-ROI endpoint controls. They are organizational/human decisions that cannot be implemented via code.

**Required decisions — document outcomes in `compliance/evidence/POL-008/endpoint-config.md`:**

1. **Disk encryption:** Confirm that all admin laptops (Aidan Pierce, Aidan Nguyen, Enoch Cheung) have full-disk encryption enabled:
   - macOS: FileVault enabled (System Settings → Privacy & Security → FileVault)
   - Windows: BitLocker enabled
   - Linux: LUKS full-disk encryption at install time
   - Record: Name | Device type | Encryption method | Verified by | Date

2. **Screen lock:** Confirm automatic screen lock triggers after ≤10 minutes of inactivity on all admin devices.

3. **1Password / credential vault:** Confirm all three admins use a password manager (not browser-saved credentials) for Meridian system logins. Record in evidence.

4. **SSH key storage:** Aidan Pierce's SSH private key for Contabo VPS — confirm it is stored ONLY in 1Password or the OS keychain, not as a plaintext file on disk.

**Until this DECISION is resolved:** Document in `compliance/risk/register.md` as a Medium risk (endpoint compromise) with target resolution date.

---

## Roles & Responsibilities

| Role | Responsibility |
|---|---|
| **Aidan Pierce** | Collect annual vendor attestation certificates; respond to Jetson device incidents; verify endpoint controls annually; own this policy. |
| **CA Admins (Nguyen, Cheung)** | Report any physical security concerns (lost laptop, suspected device tampering) to Aidan Pierce immediately. Maintain disk encryption and screen lock on personal admin devices. |
| **Merchants** | Physical security of Jetson device hardware per Merchant Agreement. Report suspected theft or tampering to Meridian immediately. |

---

## Owner

Aidan Pierce. Policy exceptions require written approval from Aidan Pierce logged in `compliance/evidence/POL-001/exceptions.md`.

---

## Review Cadence

Annual. Also triggered within 30 days of: new infrastructure vendor onboarded, Jetson device incident, admin laptop known compromise, or Contabo SOC 2 status change.

---

## ## DECISION (Aidan) — Merchant Agreement Physical Security Clause

**Context:** The Merchant Agreement must explicitly define the physical security boundary (merchant is responsible for physical device security; Meridian is responsible for software). Without this clause, Meridian may inherit physical security liability.

**Action required:** Confirm whether the current Merchant Agreement / Terms of Service contains a physical device security clause. If not, add one. Once confirmed, reference the relevant clause and version here.

---

## Evidence that this Policy Operates

Auditors should verify:

1. **`compliance/evidence/POL-008/vendor-attestations/`** — Current SOC 2 / ISO 27001 certificates for Supabase, Railway, and Cloudflare, downloaded within the past 12 months.
2. **Supabase `merchant_devices` table export** — Current device inventory with `is_active` status.
3. **`compliance/evidence/POL-008/device-incidents.md`** — Log of any Jetson device incidents (empty = no incidents in period).
4. **`compliance/evidence/POL-008/endpoint-config.md`** — Admin laptop disk encryption and screen lock verification records.
5. **`compliance/evidence/POL-008/jetson-cleanup-sample.log`** — Sample output from on-device cleanup cron confirming 90-day retention enforcement.
6. **This file's git history** — `git log --follow compliance/policies/physical-environmental-security.md`
