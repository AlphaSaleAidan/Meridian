# Meridian — SOC 2 Readiness Roadmap

> Sequenced path from today (~46% Type-I design readiness) → Type I report → Type II. Driven by
> `gap-analysis.md`. Dates are relative; Aidan sets calendar dates and books the human/paid items.

## Recommended path

**Readiness → Type I → observation window (operate controls) → Type II.** Type I gives a usable report fast
for enterprise diligence; Type II (3–6 month window for a first-timer) closes serious procurement. The seed
round / enterprise deals are the forcing function.

## Phase ladder

| Phase | Goal | Exit criterion | Blocking owner |
|---|---|---|---|
| **0 — Scope & gap** ✅ | Confirm TSC scope; map every criterion | `gap-analysis.md` exists; scope decided | Aidan confirms scope |
| **1 — Technical controls** ◐ | Close CC6 (RLS, BOLA, MFA, secrets, tenant isolation); CC7/CC8 ops docs; PI1/A1 | R0–R5 done; negative tests green | Aidan merges PRs |
| **2 — Policies** ◐ | 19 policies tied to real controls | All policies authored + acknowledged | Aidan signs |
| **3 — Evidence pipeline** ◐ | Type I evidence backfilled; Type II collectors running | Evidence resolves per control ID | Aidan |
| **4 — Internal readiness (mock audit)** | Adversarial self-audit; drive % up | `internal-readiness-assessment.md`; readiness ≥ 85% | Aidan |
| **5 — Engage auditor** | Pick automation platform; book CPA; book pen test | Auditor engaged | **Aidan (business)** |
| **6 — Observation → Type II** | Operate controls over window | Type II examination | Aidan |

`✅ done · ◐ in progress (authored, awaiting merge/sign-off)`

## What was built this session (Phase 0–3 authored, nothing applied to live systems)

- `00-system-description.md`, `gap-analysis.md`, this roadmap.
- `/risk/` register + POS & camera threat models.
- `/vendors/` subservice register (carve-out).
- `/controls/` register + key control files with evidence pointers.
- `/policies/` the 19-policy set.
- `/evidence/` structure by control ID + **adversarial RLS negative tests** + Type I pointers.
- `internal-readiness-assessment.md` (mock audit).

**Nothing was applied to the live Supabase DB, Railway, or Contabo.** All code-level remediations (RLS fixes,
BOLA threading) are authored as reviewable artifacts/PR only. Aidan merges.

## The human/paid decisions only Aidan can make (do not let these silently block)

1. **TSC scope** — full five vs minimum-viable (Security+Availability+Confidentiality). (DECISION block in system description.)
2. **Type I vs Type II first** — recommend Type I now, Type II over the window.
3. **Compliance-automation platform** — Vanta / Drata / Secureframe / Thoropass / Tugboat. Evidence here is
   designed portable into any of them. Phase 5 decision; do not hard-recommend.
4. **CPA firm** — independent licensed firm issues the attestation.
5. **External penetration test** — annual, paid, third-party. Type II norm.
6. **Cyber / E&O insurance** — buyers and auditors ask.
7. **MFA enablement + evidence**, **background-check process**, **quarterly access & security reviews** — org rituals.

## Immediate next actions (in order)

1. Aidan confirms TSC scope (1 message).
2. Run **R0** — confirm live `pg_policies` against Supabase (read-only) to set the true RLS baseline.
3. Open PRs for **R1–R3** (the two CRITICAL access gaps) — highest readiness lift per unit effort.
4. **R4** (Twilio/PCI), then **R5–R7**.
5. Re-score `gap-analysis.md`; target ≥ 85% before Phase 5.
