# Camera Streaming + Retention + Overlay — Compliance Gap Report

**Scope:** Live camera streaming, footage/clip retention, and intelligence overlays for the
Meridian camera feature (see `docs/camera/streaming-overlays-plan.md`).
**Jurisdiction:** Canada (federal PIPEDA + provincial privacy + provincial cannabis-retail surveillance rules).
**Method:** Grounded **only** in compliance material already on file in this repo. Where the repo is
silent, the row is marked explicitly as *no on-file source — needs Aidan/Enoch*. **No web research,
no invented regulatory values.**
**Prepared:** 2026-06-24 · Phase 0 (doc-only) of the camera plan.

> **Headline finding (read this first):** The repo contains a solid *privacy-framework* posture doc
> (PIPEDA / Law 25 / CASL — `docs/MERIDIAN_COMPLIANCE_POSTURE.md`) and names every provincial
> cannabis regulator (`src/ai/canada/provincial.py`, `src/ai/economics/data/canada_benchmarks.yaml`).
> **However, there is ZERO on-file documentation of any cannabis-retail surveillance/CCTV retention
> floor (days of footage) for ANY province.** The regulator names on file describe *retail
> distribution models* (who may sell cannabis), not *camera retention requirements*. Therefore every
> per-province surveillance-retention value in §2 is **unconfirmed** and defaults to the plan's
> strictest-unknown floor (60 days), flagged for legal review. Do not ship province-specific retention
> claims to merchants until Aidan/Enoch supply the source regulation.

---

## 1. Inventory — Canadian compliance docs on file

Search performed across the repo (`*.md *.html *.sql *.py *.ts *.tsx *.js *.yaml *.json`, excluding
`node_modules`) for: PIPEDA, Law 25, Quebec, CASL, Alberta PIPA, BC PIPA, AGCO, AGLC, LCRB, SLGA,
LGCA, Cannabis NL, surveillance, retention, video, privacy.

### Substantive compliance documents

| Doc | Path | What it covers | Relevance to camera feature |
|-----|------|----------------|------------------------------|
| **Compliance & Privacy Posture v1.0** | `docs/MERIDIAN_COMPLIANCE_POSTURE.md` | PIPEDA, Law 25, CASL, sub-processors, breach plan, data residency, camera "privacy by design", retention table, compliance DB schema | **Primary source.** Establishes the privacy framework and the existing camera-analytics privacy stance. |
| **Compliance sheet (investor HTML)** | `docs/meridian-compliance-sheet.html` | Visual summary of the posture doc — "Zero Biometrics", CASL enforcement, 24-month breach retention | Restates the posture doc; no new retention values. |
| **Camera streaming + overlays plan** | `docs/camera/streaming-overlays-plan.md` | What the new build does (WebRTC live view, overlays, connector, per-province retention columns, AGPL note) | **Source of truth for "current build behavior"** in §3/§4. Explicitly defers per-province retention to *this* report. |
| **Phase-1 migration** | `supabase/migrations/20260624_camera_streaming_phase1.sql` | Adds `locations.surveillance_required` + `locations.surveillance_retention_days` (default 60); P0 RLS fix on `vision_*` | Defines where retention values get seeded; default already 60d. |
| **Compliance tables migration** | `migrations/021_compliance_tables.sql` | `compliance_documents`, `compliance_acceptances`, `casl_consent_records`, `privacy_requests`, `breach_log`, `data_inventory` | Backs the consent/acceptance + breach-log claims. |
| **CASL guard** | `src/compliance/casl_guard.py`, `src/api/routes/compliance.py`, `services/phone_agent/casl_compliance.py` | Programmatic CASL consent enforcement on commercial email | Source for the CASL row in §3. |

### Supporting (regulator names / context only — NOT retention sources)

| Path | What it actually contains | Why it is NOT a retention source |
|------|---------------------------|----------------------------------|
| `src/ai/canada/provincial.py` | Province profiles: cannabis **distribution model** + regulator name (AGCO, AGLC, LCRB, SLGA, LGCA, SQDC, NSLC, Cannabis NB, NLC, NTLCC, NULC) | Describes *who may sell* cannabis per province — says nothing about CCTV/surveillance retention. |
| `src/ai/economics/data/canada_benchmarks.yaml` | Regulator/distributor/private-retail map (ON→AGCO, QC→SQDC, AB→AGLC, BC→LCRB) | Same — retail structure, not camera rules. |
| `docs/playbook/10-pos-integrations/{cova-pos,greenline-pos}.md`, `_status/*` | Sales playbook: "AGCO/BCLDB compliant" POS integrations | Marketing/sales framing of POS compliance reporting; no surveillance retention figures. |

### Explicitly NOT on file (searched, not found)

- ❌ No `/legal` directory exists.
- ❌ **No surveillance / CCTV / video-footage retention floor (in days) for any province** — for
  AGCO (ON), AGLC (AB), LCRB (BC), SLGA (SK), LGCA (MB), SQDC (QC), or any Atlantic / NL / territory
  regulator. Confirmed by targeted grep for `retention`/`footage`/`recording`/`surveillance` + day/month
  quantities; the only numeric "days" hits are unrelated (cold-storage hot-tier `90`, a sales playbook
  "60 days", "7 days of joint data").
- ❌ No standalone Privacy Policy text, no Camera Analytics Consent disclosure text, no DPAs, no
  Transfer Risk Assessments (the posture doc *references* these as existing/pending but the text is
  not in this repo).
- ❌ No Alberta PIPA / BC PIPA / Quebec Law 25 statutory citation documents (only the posture doc's
  prose summary of Law 25).

---

## 2. Per-province cannabis-retail SURVEILLANCE RETENTION floor

**There is no on-file source for any of these values.** The posture doc's camera section
(`MERIDIAN_COMPLIANCE_POSTURE.md` §4) covers *anonymous analytics* retention (30d raw / 1yr
aggregated) but says **nothing** about provincial cannabis-licensing CCTV retention floors. The
streaming plan and the Phase-1 migration both default to a strictest-unknown floor of **60 days** and
defer the real values to this report. Accordingly every row below is **⚠️ unconfirmed**.

| Province | Regulator (name on file) | Retention floor (days) | Source doc path | Confidence |
|----------|--------------------------|------------------------|-----------------|-----------|
| ON | AGCO | ⚠️ unconfirmed — default 60d, flag for review | regulator name only: `src/ai/canada/provincial.py:92`; default: `…phase1.sql:134` | **None** (no retention source on file) |
| AB | AGLC | ⚠️ unconfirmed — default 60d, flag for review | name: `provincial.py:102-103`; default: `…phase1.sql:134` | **None** |
| BC | LCRB | ⚠️ unconfirmed — default 60d, flag for review | name: `provincial.py:97`; default: `…phase1.sql:134` | **None** |
| SK | SLGA | ⚠️ unconfirmed — default 60d, flag for review | name: `provincial.py:114-115`; default: `…phase1.sql:134` | **None** |
| MB | LGCA | ⚠️ unconfirmed — default 60d, flag for review | name: `provincial.py:119-120`; default: `…phase1.sql:134` | **None** |
| QC | SQDC — **private retail N/A** (govt-only monopoly) | N/A for private retail; if a QC tenant is govt/other, ⚠️ unconfirmed — default 60d | `provincial.py:109` ("SQDC is sole legal retailer — no private cannabis retail") | **N/A** (no private cannabis retail tenants possible) |
| Atlantic — NS | NSLC (govt-only) | ⚠️ unconfirmed — default 60d, flag for review | `provincial.py:125-126` | **None** |
| Atlantic — NB | Cannabis NB (govt-only) | ⚠️ unconfirmed — default 60d, flag for review | `provincial.py:131` | **None** |
| Atlantic — PE | PEI Cannabis Management Corp. (govt-only) | ⚠️ unconfirmed — default 60d, flag for review | `provincial.py:136` | **None** |
| NL | NLC + limited private retail (hybrid) | ⚠️ unconfirmed — default 60d, flag for review | `provincial.py:140-141` | **None** |
| Territories — YT | Yukon Liquor Corp. (hybrid) | ⚠️ unconfirmed — default 60d, flag for review | `provincial.py:145-146` | **None** |
| Territories — NT | NTLCC (govt-only) | ⚠️ unconfirmed — default 60d, flag for review | `provincial.py:150-151` | **None** |
| Territories — NU | NULC/NLC (govt-only) | ⚠️ unconfirmed — default 60d, flag for review | `provincial.py:155-156` | **None** |

> **Honest note on the 60d default:** the plan calls it "strictest-known 60d," but **nothing on file
> establishes that 60d is in fact the strictest known provincial floor** — it is an internal
> conservative placeholder, not a value derived from any cited regulation. It is safe as a *floor*
> only if the true provincial minimums are ≤60d; if any real minimum is *higher* (e.g. some
> jurisdictions specify longer CCTV retention), 60d would be **non-compliant**. This must be verified
> before Phase 7 enforcement is sold as "Province minimum."

---

## 3. Privacy posture of the build (PIPEDA / Law 25 / CASL / AB-BC PIPA)

Build behavior is taken from `docs/camera/streaming-overlays-plan.md`; privacy framework from
`docs/MERIDIAN_COMPLIANCE_POSTURE.md`.

### Gap-report table

| Requirement | Source doc (on file) | Current build behavior (from plan) | Compliant? | Required change |
|-------------|----------------------|------------------------------------|-----------|-----------------|
| **PIPEDA — lawful purpose for video as personal info** | `MERIDIAN_COMPLIANCE_POSTURE.md` §1, §4 | Posture doc frames camera output as *anonymous analytics* (no images/video stored). New build adds **live video to the phone + recorded clips** (`/cameras/:id/clip?from=&to=`) — i.e. **identifiable footage is now transmitted and stored/retrievable**, a materially broader collection than the posture doc describes. | **Partial** | Update the posture doc + data-inventory to cover *live footage and clip storage* as a new personal-information category with a stated lawful purpose (loss prevention / operations). The "no images or video stored" claim is **no longer accurate** once clips exist. |
| **PIPEDA — consent / notice (signage)** | `MERIDIAN_COMPLIANCE_POSTURE.md` §4 (merchant must post signage, notify employees, accept Camera Consent) | Plan reuses existing camera onboarding; adds connector pairing. No new signage/notice gate documented for the *live-view/recording* expansion. | **Partial** | Extend the Camera Analytics Consent disclosure to explicitly cover live viewing + clip retention (not just anonymous counting); keep the signage/employee-notice obligation and surface it in the new "Connect your cameras" onboarding step (Phase 5). |
| **PIPEDA — retention limitation** | `MERIDIAN_COMPLIANCE_POSTURE.md` §2 (30d raw / 1yr aggregated analytics); `…phase1.sql:133-134` | `surveillance_retention_days` column exists (default 60); auto-purge floor planned for Phase 7 but **not yet built**. Clip retention period itself is not yet defined in any doc. | **Partial** | Define and document the actual clip/footage retention period; build the Phase-7 auto-purge; reconcile the 30d-analytics vs 60d-surveillance vs (undefined) clip-retention numbers so they are consistent and defensible. |
| **PIPEDA — safeguards** | `MERIDIAN_COMPLIANCE_POSTURE.md` §8; `…phase1.sql` (RLS, `stream_tokens` hashed, ≤60s view JWT) | Plan: tenant-scoped tables, RLS, P0 cross-tenant fix, hashed stream tokens, short-lived view JWTs, camera creds stay on connector, gitleaks for `rtsp://user:pass@`. | **Y** (for the access-control layer, *as designed*) | None for design; **must ship the Phase-1 cross-tenant denial e2e test** (plan commits to it) before this can be claimed as implemented rather than designed. |
| **PIPEDA — individual access** | `MERIDIAN_COMPLIANCE_POSTURE.md` §6 (`/api/privacy/*`, 30-day deadline) | Access pipeline exists for account/analytics data. Does **not** yet contemplate access/deletion requests over *stored footage/clips of identifiable individuals* (e.g. a customer requesting footage of themselves). | **Partial** | Extend the privacy-rights workflow to handle footage subject-access/deletion, or document why retained clips are out of scope (e.g. retention too short, no identity index). |
| **Quebec Law 25 — applicability / QC tenants** | `MERIDIAN_COMPLIANCE_POSTURE.md` §1, §4 | Posture doc treats Law 25 as fully in scope. **No tenant roster is on file**, so whether any QC-resident-data tenant exists cannot be confirmed from the repo. Plan's open question explicitly names "Pacific Revenue Systems / any QC-resident-data tenants." | **Partial / unconfirmed** | Aidan/Enoch to confirm QC tenant existence. If any, signage + heightened notice are mandatory and footage of identifiable individuals raises Law 25 exposure ($10M+ AMP regime per posture doc). |
| **Quebec Law 25 — data residency for footage** | `MERIDIAN_COMPLIANCE_POSTURE.md` §2 (all data in US; TRA + DPA + disclosure required) | Plan topology stores/relays footage via Contabo (US-side gateway) and Supabase (US AWS). Live footage of identifiable people would now cross the border. Plan flags this as an **open confirmation**. | **Partial** | Confirm whether QC footage may leave Canada. If Law 25 / a tenant contract forces Canadian residency, the `StreamGateway`/`KvsGateway` interface allows a Canadian region — but this is a **decision for Aidan/Enoch**, not resolvable from on-file docs. |
| **CASL — no CEMs from the camera feature** | `MERIDIAN_COMPLIANCE_POSTURE.md` §5; `src/compliance/casl_guard.py` | Camera/overlay feature sends operational data, not email. No new commercial-email path introduced by the plan. Existing CASL guard gates all commercial email. | **Y** | None — provided any future camera *alert emails* (e.g. anomaly notifications) route through the existing CASL guard / are classified transactional. Flag for Phase 8 if alerts are emailed. |
| **Alberta PIPA — collection notice / retention / access** | *No on-file source* (posture doc does not address PIPA) | AB cannabis retail is private (AGLC) → AB PIPA governs private-sector employee + customer surveillance. Build collects identifiable footage in AB. | **Unknown — no on-file source** | needs Aidan/Enoch: obtain AB PIPA surveillance guidance (notice, reasonable purpose, retention, access) and add to posture doc. |
| **BC PIPA — collection notice / retention / access** | *No on-file source* (posture doc does not address PIPA) | BC cannabis retail is private (LCRB) → BC PIPA governs. Build collects identifiable footage in BC. | **Unknown — no on-file source** | needs Aidan/Enoch: obtain BC PIPA / OIPC surveillance guidance and add to posture doc. |

### Overlay analytics — privacy specifics (requested in brief §3)

Grounded in `docs/camera/streaming-overlays-plan.md` and `…phase1.sql`. The brief asks for three
confirmations; here is what the on-file docs do and do **not** establish:

| Overlay item | What on-file docs say | Compliant / status | Required change / decision |
|--------------|------------------------|--------------------|----------------------------|
| **Pose stored only as posture-label strings (never a biometric template)** | Plan describes pose as landmarks + gesture, overlay-consumed; layer is **off unless mediapipe installed**. **Nothing on file states pose is persisted only as label strings**, nor that landmark/skeleton data is discarded. The posture doc's "no biometric data" claim predates this overlay. | **Unconfirmed** | needs decision: explicitly specify and document that pose persists as posture *labels* only (e.g. "queuing", "reaching") and that raw landmark vectors are ephemeral. Until documented, the "zero biometrics" claim is at risk for the pose layer. |
| **FastReID identities anonymous/ephemeral; re-ID vector retention documented** | Plan: FastReID = "anonymous cross-camera ID", GPU-gated, currently **off (tracker-id fallback)**. Re-ID **vector retention is not documented anywhere** — neither the plan nor the posture doc states how long appearance embeddings are kept. | **Unconfirmed** | needs decision + doc: define re-ID embedding retention (ideally ephemeral / session-scoped) and confirm embeddings are not persisted in a way that enables re-identification across visits. This is the layer most exposed to Law 25 biometric arguments — treat carefully. |
| **Basket-linked tags / segment labels — merchant-visible vs internal-only** | Plan lists this as an **explicit open confirmation for Aidan** ("are re-ID badges / basket tags / segment labels merchant-visible or internal-only?"). POS x-ref writes to `cross_reference_insights`; overlay reads it (permission-gated). No on-file resolution. | **Decision pending — flag for Aidan/Enoch** | **Decision for Aidan/Enoch.** Surfacing basket-linked identity tags to merchants materially increases identifiability and Law 25/PIPEDA exposure; internal-only is the conservative default. Must be decided before Phase 6 (POS x-ref glue). |

> **Cross-cutting biometric caveat:** the posture doc's central selling point — *"No biometric data
> collected or stored… fully outside the scope of CAI biometric enforcement"* — was written for the
> **anonymous-counting** system. The new build adds **live identifiable footage, optional pose, and
> optional cross-camera re-ID**. Whether the "zero biometrics / outside CAI scope" claim survives is
> **not resolved by any on-file doc** and depends on the pose/re-ID/basket-tag decisions above. Do not
> repeat the "zero biometrics" claim for the streaming feature until those are settled.

---

## 4. Outputs

### 4a. Prioritized remediation list

1. **P0 — verify the real per-province surveillance retention floors** (AGCO/AGLC/LCRB/SLGA/LGCA +
   Atlantic/NL/territories). No on-file source exists; the 60d default is an unverified placeholder.
   *Owner: Aidan/Enoch (legal/regulatory).* Blocks any merchant-facing "Province minimum" claim
   (Phase 7).
2. **P0 — settle the biometric posture for the new layers** (pose label-only persistence; re-ID
   embedding retention; basket-tag merchant visibility). Determines whether the "zero biometrics /
   outside CAI scope" claim is still truthful. *Owner: Aidan/Enoch + engineering doc.*
3. **P1 — update the Compliance & Privacy Posture doc** to reflect that the build now transmits and
   stores **identifiable footage/clips**. The current "no images or video stored — only numerical
   metrics" statement becomes false once `/clip` exists. Add a footage personal-information category,
   lawful purpose, retention period, and footage subject-access handling.
4. **P1 — ship the Phase-1 cross-tenant denial e2e test** so safeguards (RLS / P0 fix) are
   *implemented*, not just *designed*, before any live footage flows.
5. **P1 — define clip/footage retention period + build Phase-7 auto-purge** with an enforced floor of
   `max(provincial_minimum, configured)`; reconcile the 30d-analytics / 60d-surveillance / undefined-clip
   numbers.
6. **P2 — resolve QC data residency** for footage (confirm QC tenants; decide Canadian region vs
   US + TRA/DPA). Interface (`StreamGateway`/`KvsGateway`) already supports a region swap.
7. **P2 — obtain AB PIPA / BC PIPA surveillance guidance** and add to the posture doc (private-sector
   cannabis retail in AB/BC is governed by PIPA, currently unaddressed on file).
8. **P3 — route any future camera alert emails through the existing CASL guard** (no current
   email path; flag for Phase 8 if anomaly alerts become emails).

### 4b. Exact per-province values to seed into `locations.surveillance_retention_days`

**Recommendation: seed every province with the 60d placeholder that the migration already defaults
to, and DO NOT present any of these as a real "provincial minimum" until §4a item 1 is resolved.**
No on-file doc supports a province-specific number, so seeding anything other than the uniform
conservative default would be inventing values.

| `locations.state` | Seed value (days) | Basis | Status |
|-------------------|-------------------|-------|--------|
| ON | 60 | strictest-unknown placeholder (migration default) | ⚠️ verify (AGCO) |
| AB | 60 | placeholder | ⚠️ verify (AGLC) + AB PIPA |
| BC | 60 | placeholder | ⚠️ verify (LCRB) + BC PIPA |
| SK | 60 | placeholder | ⚠️ verify (SLGA) |
| MB | 60 | placeholder | ⚠️ verify (LGCA) |
| QC | 60 | placeholder | N/A for private cannabis retail (SQDC monopoly); applies only if a non-cannabis/govt QC tenant uses cameras — still verify |
| NS | 60 | placeholder | ⚠️ verify (NSLC) |
| NB | 60 | placeholder | ⚠️ verify (Cannabis NB) |
| PE | 60 | placeholder | ⚠️ verify (PEI CMC) |
| NL | 60 | placeholder | ⚠️ verify (NLC) |
| YT | 60 | placeholder | ⚠️ verify (Yukon Liquor Corp.) |
| NT | 60 | placeholder | ⚠️ verify (NTLCC) |
| NU | 60 | placeholder | ⚠️ verify (NULC/NLC) |

(The migration `…phase1.sql:134` already sets `DEFAULT 60`, so no per-row seed is strictly required
until verified values exist; the table above documents the intended state.)

---

## 5. Items requiring Aidan or Enoch to confirm

1. **Real surveillance/CCTV retention floors per province** (AGCO/AGLC/LCRB/SLGA/LGCA + Atlantic/NL/
   territories) — no on-file source; cannot be filled without legal/regulatory input.
2. **Is 60d actually the strictest-known floor**, or just a placeholder? If any true minimum exceeds
   60d, the default is non-compliant.
3. **Pose persistence**: confirm pose is stored only as posture-label strings and raw landmark
   vectors are ephemeral (not on file).
4. **Re-ID embedding retention**: define how long FastReID appearance vectors are kept and confirm
   they cannot re-identify across visits (not on file).
5. **Basket-linked tags / segment labels — merchant-visible or internal-only?** (the plan's own open
   question; conservative default = internal-only).
6. **QC tenant existence + footage data residency** (e.g. Pacific Revenue Systems): does any
   QC-resident-data tenant exist, and must their footage stay in Canada under Law 25 / contract?
7. **AB PIPA / BC PIPA surveillance obligations** — no on-file source; private-sector cannabis retail
   in AB/BC falls under PIPA, currently unaddressed.
8. **Footage subject-access / deletion** — confirm whether the privacy-rights pipeline must handle
   requests over stored clips of identifiable individuals, or document why it's out of scope.
9. **AGPL licensing of YOLO/boxmot** (already flagged in the plan; not a privacy item but a
   compliance/legal item Enoch should sign off) — boxmot dropped, YOLO→RF-DETR scheduled Phase 4.
10. **Canadian Privacy Officer designation** — posture doc §12 still lists confirming Enoch Cheung as
    Canadian Privacy Officer as pending.

---

*Grounding statement: every "Compliant = Y" in this report cites an on-file doc establishing the
control as designed; no value in §2 / §4b is invented — all are the explicit strictest-unknown
placeholder because the repo contains no provincial surveillance-retention source. All ⚠️ and
"needs Aidan/Enoch" rows reflect genuine absence of on-file documentation, not an oversight in the
search.*
