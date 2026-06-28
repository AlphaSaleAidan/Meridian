# Encryption & Cryptography Policy
**Document ID:** POL-004
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce
**Review Cadence:** Annual, or on any change to cryptographic libraries or key infrastructure
**Related Policies:** [POL-001 Information Security](./information-security-policy.md), [POL-002 Access Control](./access-control.md), [POL-003 Password & Authentication](./password-authentication.md)
**TSC Controls:** CC6.1 (encryption at rest), CC6.7 (encryption in transit), CC9.2 (vendor crypto)

---

## Purpose

Define Meridian's cryptographic standards for data at rest, data in transit, and key management. Correct a documented error in prior compliance documentation. Establish key rotation procedures.

---

## Scope

All Meridian systems processing or storing tenant data: FastAPI backend (`src/security/encryption.py`), Supabase managed Postgres, Railway TLS, Cloudflare TLS, Contabo VPS, and any async worker that handles OAuth tokens.

---

## Documentation Correction

> **IMPORTANT — Auditors and future policy authors must note:**
> `docs/MERIDIAN_COMPLIANCE_POSTURE.md` line 279 states the POS token encryption algorithm is "Fernet/AES-128-CBC." This is **incorrect**.
>
> The actual implementation in `src/security/encryption.py` uses **AES-256-GCM** (256-bit key, GCM authenticated encryption mode). This policy supersedes that statement. Any future audit, questionnaire, or sub-processor disclosure must reference AES-256-GCM as the algorithm for POS OAuth tokens.
>
> `docs/MERIDIAN_COMPLIANCE_POSTURE.md` should be updated to reflect this correction. Track in `compliance/evidence/POL-004/doc-correction.md`.

---

## Procedure

### 1. Encryption at Rest

#### 1a. POS OAuth Tokens — AES-256-GCM

POS provider OAuth tokens (Square, etc.) are stored encrypted in Supabase. Encryption and decryption are performed exclusively in `src/security/encryption.py`.

- **Algorithm:** AES-256-GCM (authenticated encryption — provides both confidentiality and integrity/tamper detection).
- **Key source:** `ENCRYPTION_KEY` environment variable, a 32-byte (256-bit) value stored as a Railway encrypted environment variable.
- **Key format:** Must be exactly 32 bytes. If the key is not exactly 32 bytes, `src/security/encryption.py` raises an error at startup — fail-closed.
- **Versioning:** The encryption implementation supports a `v1:` versioned ciphertext prefix scheme. This enables key rotation without re-encrypting all existing tokens at once: new tokens are encrypted with the new key under `v2:`, existing `v1:` tokens are decrypted with the old key until re-encrypted on next read. See §3 for the full rotation procedure.
- **Nonce:** A fresh 12-byte random nonce is generated per encryption operation. The nonce is prepended to the ciphertext and stored with it.

#### 1b. Supabase Managed Postgres

All data in Supabase Postgres (project `kbuzufjxwflrutowwnfl`, AWS us-east-1) is encrypted at rest using **AES-256** managed by AWS RDS (Supabase's underlying infrastructure). This is documented in Supabase's SOC 2 Type II report, available at `https://supabase.com/security`.

Meridian does not manage the Supabase database encryption key. Key management is the responsibility of Supabase/AWS.

#### 1c. Redis (Contabo)

Redis is used as a Celery broker and result backend on the Contabo VPS (209.126.80.45). Redis data is **not encrypted at rest** by default on this configuration.

## DECISION (Aidan)

**Gap:** Redis on Contabo stores Celery task queues and intermediate results. If any of this data contains tenant PII or POS token fragments, it is at risk if the VPS is compromised.

**Recommended default:** Enable Redis `requirepass` authentication (already recommended in the Contabo hardening runbook). Evaluate whether Redis is storing any PII-bearing task payloads; if so, either enable Redis encryption-at-rest (Redis Enterprise feature, not available on this open-source setup) or ensure no PII enters the Redis queue.

**Action required:** Aidan to audit Celery task payloads for PII and document the decision in `compliance/evidence/POL-004/redis-decision.md`.

### 2. Encryption in Transit

#### 2a. API Endpoints (api.meridian.tips)

All API traffic is served over TLS 1.2+ via Railway's managed TLS. HTTP Strict Transport Security (HSTS) is enforced by Meridian application middleware:

- **Source file:** `src/api/middleware/security_headers.py:13`
- **Header:** `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` (recommended value — verify actual configured value against the file).
- Railway does not allow unencrypted HTTP on custom domains. TLS downgrade attacks are additionally mitigated by the HSTS header once the browser caches it.

#### 2b. Frontend (meridian.tips Canada portal)

The Canada portal static frontend is served from Cloudflare (CDN + TLS termination) to the Contabo VPS. Cloudflare enforces TLS 1.2+ on the browser-to-Cloudflare leg. The Cloudflare-to-origin leg uses Cloudflare's "Full (Strict)" SSL mode, requiring a valid origin certificate on the Contabo nginx configuration.

## DECISION (Aidan)

**Verify:** Confirm that the Cloudflare SSL mode for the Canada portal is set to "Full (Strict)" (not "Flexible," which would leave the origin leg unencrypted). Document in `compliance/evidence/POL-004/cloudflare-ssl-config.md` with a dated screenshot.

#### 2c. Supabase Client Connections

All connections from Meridian backend to Supabase use TLS (enforced by Supabase; connections without TLS are rejected). The `SUPABASE_URL` always uses `https://`.

#### 2d. Internal Services (Contabo)

Communication between async workers and Redis on Contabo is over localhost (127.0.0.1), not exposed to the network. No TLS is required for loopback-only connections, but Redis must be bound only to 127.0.0.1 (verify in Redis config: `bind 127.0.0.1`).

## DECISION (Aidan)

**RTSP Edge Encryption:** The Meridian camera vision feature involves RTSP streams from merchant cameras. RTSP streams may traverse the public internet depending on merchant network configuration.

**Options:**
- (A) Document that RTSP is out of scope (stream data stays within merchant's local network and never traverses Meridian infrastructure).
- (B) Require merchants to use RTSP over TLS (rtsps://) or a VPN tunnel if the stream traverses the public internet.
- (C) Add a disclaimer to the camera feature onboarding that merchants are responsible for securing their network path to the camera.

**Recommended default:** Option A + Option C. Meridian's camera feature receives frames at the inference endpoint (which is HTTPS). The merchant's network path to the camera is outside Meridian's control. Document this scope boundary in the camera feature's data flow diagram.

**Action required:** Aidan to select an option and record in `compliance/evidence/POL-004/rtsp-decision.md`.

### 3. Key Management and Rotation

#### 3a. ENCRYPTION_KEY Rotation Procedure

The versioned scheme in `src/security/encryption.py` supports zero-downtime rotation:

1. Generate a new 32-byte key: `openssl rand -hex 16` (produces 32 hex chars = 16 bytes; for 32 bytes use `openssl rand -hex 32` which produces a 64-char hex string — confirm the implementation's expected format: raw bytes vs. hex-encoded).
2. Add `ENCRYPTION_KEY_V2` to Railway environment alongside `ENCRYPTION_KEY` (old).
3. Deploy the API with code that reads new tokens under `v2:` prefix using `ENCRYPTION_KEY_V2`, and continues to decrypt `v1:` tokens using `ENCRYPTION_KEY`.
4. Run a background migration job that re-encrypts all `v1:` tokens as `v2:` tokens.
5. Once all tokens are `v2:`, remove `ENCRYPTION_KEY` from Railway and rename `ENCRYPTION_KEY_V2` to `ENCRYPTION_KEY`.
6. Deploy again; confirm no `v1:` tokens remain in the database.
7. Log the rotation in `compliance/evidence/POL-004/key-rotation-log.md` with date, reason, and who performed it.

**Rotation triggers:** Suspected exposure of `ENCRYPTION_KEY`; departure of any engineer with Railway access; at least every 2 years (recommended: annually).

#### 3b. Key Length Requirements

| Key / Secret | Required Length | Algorithm |
|---|---|---|
| `ENCRYPTION_KEY` | 32 bytes (256 bits) | AES-256-GCM |
| `MERIDIAN_ADMIN_KEY` | ≥ 32 random characters | HMAC-based comparison |
| `OAUTH_STATE_SECRET` | ≥ 32 random characters | HMAC state signing |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase-issued (≥ 256-bit JWT secret) | HS256 JWT |

#### 3c. Prohibited Algorithms

The following algorithms must not be used in any new Meridian code:
- MD5, SHA-1 (for security purposes; SHA-1 in git is acceptable)
- DES, 3DES, RC4
- AES-ECB mode
- RSA < 2048-bit
- Fernet (AES-128-CBC) for new token encryption (deprecated in Meridian context by this policy)

---

## Roles & Responsibilities

| Role | Responsibility |
|---|---|
| Aidan Pierce | Manage `ENCRYPTION_KEY` lifecycle; approve any new cryptographic primitive introduced to codebase; execute key rotations |
| Any engineer | Must not introduce prohibited algorithms; any new encryption use requires review against this policy; flag algorithm choices in PR description |

---

## Evidence that this Policy Operates

1. **`src/security/encryption.py` at HEAD** — confirms AES-256-GCM algorithm, 32-byte key requirement, versioned ciphertext prefix, per-operation random nonce. Auditors should diff this file against the algorithm claims in this policy.
2. **`src/api/middleware/security_headers.py:13`** — confirms HSTS header is applied to all API responses.
3. **`compliance/evidence/POL-004/key-rotation-log.md`** — dated log of all `ENCRYPTION_KEY` rotations.
4. **`compliance/evidence/POL-004/doc-correction.md`** — records the correction of the AES-128-CBC error in `docs/MERIDIAN_COMPLIANCE_POSTURE.md`.
5. **`compliance/evidence/POL-004/cloudflare-ssl-config.md`** — dated screenshot of Cloudflare SSL mode for Canada portal.
6. **Railway environment variable list** — confirms `ENCRYPTION_KEY` is set (value masked); auditors may request dated console screenshot.
7. **Supabase SOC 2 report** — third-party evidence for AES-256 at rest on managed Postgres; link: `https://supabase.com/security`.
