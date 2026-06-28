# Asset Management Policy
**Document ID:** POL-011
**Version:** v0.1
**Date:** 2026-06-28
**Owner:** Aidan Pierce (Founder, US signing authority)
**Review Cadence:** Annual, or on any addition or retirement of a system component within the audit boundary
**Parent Policy:** [information-security-policy.md](./information-security-policy.md)

---

## Purpose

Define the complete inventory of assets within the Meridian system boundary, assign an owner and classification to each asset, and establish lifecycle procedures for adding, modifying, and retiring assets. This policy is also the authoritative reference for the audit boundary split between Railway (primary production backend) and Contabo VPS (async compute + Canada static frontend) — a split that is material to any SOC 2 system description.

Meridian is not SOC 2 certified. This policy is part of an internal control framework authored to support readiness for a future Type II examination.

---

## Scope

Covers all hardware, software, data stores, network services, source repositories, and domains that are part of the Meridian production system or directly support it. Assets outside the boundary (e.g., sub-processor internal infrastructure, contractor personal devices) are noted as carved-out.

---

## Procedure

### 3.1 Audit Boundary — Critical Split

## DECISION (Aidan — boundary confirmation required for SOC 2 System Description)

The Meridian production environment is deliberately split across two hosting providers with different risk profiles:

**Railway** (automated deployments, SOC 2 Type II):
- FastAPI backend: auto-deploys from `main` via Railway GitHub integration
- Global frontend: React/Vite SPA, Railway-served

**Contabo VPS (209.126.80.45, St. Louis, MO)** (no SOC 2, compensating controls per POL-009 §3.7):
- Async compute workers: Celery/Beat, DeerFlow, scraper, Garry self-healing agent (PM2)
- Redis broker/cache
- **Canada portal static frontend**: manually built `frontend/dist/` deployed by SSH push; git push to `main` does NOT update this surface. The Canada-facing portal at `meridian.tips` for Canadian merchants is served from this manually maintained static directory (`CONTEXT.md:12-13`, `docs/ARCHITECTURE.md:87-88`). This is the single highest documentation debt in the system description: the same `src/frontend/` codebase has two live deployments with different update cadences, different host security postures, and different change-management procedures.

A SOC 2 system description must state both paths explicitly and explain the manual-deploy control gap.

---

### 3.2 Asset Inventory

#### 3.2.1 Compute and Hosting

| Asset | Type | Owner | Host | Classification | Notes |
|---|---|---|---|---|---|
| `api.meridian.tips` FastAPI backend | Service | Aidan Pierce | Railway | Production — Confidential | 4 uvicorn workers; auto-deploys from `main`; `Procfile`, `railway.toml` |
| React/Vite global frontend | Service | Aidan Pierce | Railway | Production — Internal | Served from Railway; mirrors `main` |
| Canada portal static dist | Service | Aidan Pierce | Contabo VPS `/root/Meridian/frontend/dist/` | Production — Confidential | Manually built and deployed; **not auto-updated by Railway CI** |
| Celery worker pool (8 workers) | Process | Aidan Pierce | Contabo VPS (PM2 `ecosystem.config.js`) | Production — Confidential | Processes POS sync, insights, forecasting |
| Celery Beat scheduler | Process | Aidan Pierce | Contabo VPS (PM2) | Production — Confidential | Schedules periodic tasks; `cleanup_expired_visitors()` job is NOT here yet (open finding POL-008 §3.3) |
| DeerFlow async agent | Process | Aidan Pierce | Contabo VPS (PM2) | Production — Internal | Autonomous data-flow orchestration |
| Scraper worker | Process | Aidan Pierce | Contabo VPS (PM2) | Production — Internal | Previously OOM'd via Playwright Chrome; paused per memory note; re-enable only with resource limit |
| Garry self-healing agent | Process | Aidan Pierce | Contabo VPS (PM2) | Production — Internal | Monitors and restarts failed PM2 processes |
| Local Qwen LLM | Process | Aidan Pierce | Contabo VPS (PM2) | Production — Internal | Inference for on-box AI tasks; model weights on VPS disk |
| Redis (single node) | Service | Aidan Pierce | Contabo VPS | Production — Confidential | Celery broker + cache; ephemeral data only; no PII should persist beyond TTL |
| Nginx reverse proxy | Service | Aidan Pierce | Contabo VPS | Production — Internal | Routes `meridian.tips` Canada traffic; TLS termination via Cloudflare |

#### 3.2.2 Database and Storage

| Asset | Type | Owner | Host | Classification | Data Tier |
|---|---|---|---|---|---|
| Supabase PostgreSQL | Database | Aidan Pierce | AWS us-east-1 (Supabase managed), project `kbuzufjxwflrutowwnfl` | Production — Restricted | Tier 2 + Tier 3 (see POL-007) |
| Cloudflare R2 `meridian-archives` bucket | Object storage | Aidan Pierce | Cloudflare (US region, automatic) | Production — Confidential/Restricted | Written by `cold_storage.py`; no deletion schedule (open finding POL-008 §3.3) |
| Merchant-premises Jetson edge device | Edge hardware | Merchant (operated by Meridian software) | Merchant site | Production — Restricted (biometric) | Camera inference, ByteTrack re-ID, VIP face embeddings; `edge/`, `src/ai/reid/` |
| `/root/.secrets/` on Contabo VPS | Secret store | Aidan Pierce | Contabo VPS (chmod 700) | Production — Restricted | API keys, DB connection strings; chmod 700; never in version control |

#### 3.2.3 Source Repositories

| Asset | Type | Owner | Host | Classification |
|---|---|---|---|---|
| `AlphaSaleAidan/Meridian` (private) | Git repository | Aidan Pierce | GitHub | Confidential — contains application source; no secrets committed |
| `AlphaSaleAidan/Meridian` GitHub Actions | CI/CD | Aidan Pierce | GitHub | Confidential — triggers Railway deploys |
| Supabase migration scripts | Schema files | Aidan Pierce | `supabase/migrations/` in repo | Confidential — schema is sensitive |

#### 3.2.4 Domains and DNS

| Asset | Type | Owner | Registrar/DNS | Notes |
|---|---|---|---|---|
| `meridian.tips` | Domain | Aidan Pierce | Cloudflare DNS | Primary merchant-facing domain; Canada portal at root |
| `api.meridian.tips` | Subdomain | Aidan Pierce | Cloudflare DNS → Railway | FastAPI backend; Cloudflare proxied |
| `meridian.tips/canada/*` | URL path | Aidan Pierce | Served from Contabo static dist | Manually deployed Canada portal routes |

#### 3.2.5 Third-Party Services (In-Boundary Integrations)

| Asset | Type | Owner | Notes |
|---|---|---|---|
| Telnyx account | Telephony | Aidan Pierce | Phone call routing, DTMF for phone-pay; TeXML app "Meridian Phone Calls" App ID 2975326560921322657 |
| Square partner credentials | POS integration | Aidan Pierce | OAuth client used by merchants; tokens stored in Supabase `pos_connections` AES-256-GCM |
| Stripe account (platform billing) | Payments | Aidan Pierce | Platform-level billing only; not used for merchant end-customer payment processing |
| Resend account | Email delivery | Aidan Pierce | Transactional emails; merchant-facing CASL consent flows |
| Railway account | Hosting | Aidan Pierce | Sole billing and admin authority |
| Cloudflare account | CDN + DNS + R2 | Aidan Pierce | All DNS, TLS termination, cold storage |
| Supabase account | Database | Aidan Pierce | Sole admin; MFA required |
| GitHub account `AlphaSaleAidan` | Source control | Aidan Pierce | Sole owner of `Meridian` repo |

Sub-processor details (certifications, DPAs, Quebec PIAs) are in `compliance/vendors/`. See POL-009.

---

### 3.3 Asset Lifecycle

#### Adding a New Asset

Before any new system component is added to the production environment:

1. **Classify** the asset using the data tier definitions in POL-007 (§3.2)
2. **Document** in this policy (add a row to §3.2 above)
3. **Vendor onboarding** if the asset is a third-party service (POL-009 §3.3)
4. **Change management** review per POL-006 if the asset changes the attack surface
5. **Aidan Pierce approval** — countersign the asset addition in `compliance/evidence/POL-011/asset-changes.md`

#### Modifying an Existing Asset

Material modifications — changes to data scope, network exposure, authentication mechanism, or hosting provider — follow the same procedure as addition. Minor modifications (version bumps, config tuning within existing scope) are governed by POL-006 (Change Management) only.

#### Retiring an Asset

1. **Data disposal:** Follow POL-008 §3.2 (deletion triggers) before decommissioning
2. **Credential revocation:** Revoke all API keys, OAuth tokens, and SSH keys associated with the asset
3. **DNS/routing cleanup:** Remove DNS records, Railway services, or PM2 process configs
4. **Documentation:** Mark the asset retired in §3.2 with the retirement date; do not delete the row
5. **Sub-processor offboarding** if applicable (POL-009 §3.6)

---

### 3.4 Boundary Notes for Auditors

1. **Canada static frontend** (`meridian.tips` served from Contabo): Railway's SOC 2 carve-out does not cover this surface. Contabo compensating controls apply (POL-009 §3.7). The manual deployment process means a code change requires: SSH to Contabo, `npm run build`, copy `dist/` to serving path, confirm `env.local` is present (the build is environment-dependent; a missing `.env.local` produces a silently broken demo-mode build).

2. **Jetson edge devices** are on the merchant's physical premises and network. Meridian controls the software stack (`edge/`) but not the physical security of the device or the merchant's LAN. The audit boundary includes Meridian's software on the Jetson but explicitly excludes the merchant's physical facility and network infrastructure.

3. **Supabase migrations are applied manually and deliberately** (`docs/ARCHITECTURE.md:88-89`). Railway CI deploying a new backend does not automatically apply the matching migration. This is a deliberate control (prevents accidental schema changes) but means deployment and migration are separate change events that must be coordinated.

4. **Redis contains no persistent Tier 2+ data** by design. If any Celery task is found to serialize PII into queue payloads, that constitutes a boundary violation requiring immediate remediation.

---

## Roles

| Role | Responsibility |
|---|---|
| Aidan Pierce (Policy Owner) | Maintain this asset inventory; approve all additions; execute asset retirement procedures; confirm Canada static build is current after any deploy |
| CA Admins (Nguyen, Cheung) | Report any system component they use that is not listed here; no authority to add assets to the production boundary |
| Future engineer | Must register any new infrastructure component in this policy before provisioning |

---

## Owner

Aidan Pierce

---

## Review Cadence

Annual. Triggered review on: any new service added to Railway or Contabo PM2, any new Supabase table or bucket, any new domain or subdomain, or any merchant-site Jetson deployment.

---

## Evidence that this Policy Operates

Auditors should verify:
1. **`compliance/evidence/POL-011/asset-changes.md`** — log of all asset additions and retirements since policy inception, with dates and approvals.
2. **`ecosystem.config.js`** (Contabo VPS) — confirms the PM2 process list matches §3.2.1; no undocumented processes.
3. **Railway project dashboard** — confirms the Railway services match §3.2.1; no unaccounted services.
4. **`supabase/migrations/`** — migration history confirms Supabase schema tables match §3.2.2.
5. **Cloudflare DNS zone** for `meridian.tips` — DNS records match §3.2.4; no shadow subdomains.
6. **`edge/docker-compose.yml`** — confirms Jetson software stack is as described; confirm no cloud egress of face embeddings without explicit merchant config.
7. **This file's git history** — `git log --follow compliance/policies/asset-management.md`.

---

## Related Policies

- [information-security-policy.md](./information-security-policy.md) — POL-001 master policy; §2 scope defines the system boundary at a high level
- [data-classification.md](./data-classification.md) — POL-007 data tiers referenced in asset classifications
- [vendor-third-party-management.md](./vendor-third-party-management.md) — POL-009 governs third-party assets listed in §3.2.5
- [data-retention-disposal.md](./data-retention-disposal.md) — POL-008 governs data disposal at asset retirement
- [change-management.md](./change-management.md) — POL-006 change controls for asset modifications
