# Meridian — SOC 2 Readiness (`/compliance`)

> **Readiness, not certification.** Meridian is **not** "SOC 2 compliant/certified." SOC 2 is an attestation
> issued by an independent CPA firm; this directory builds the *readiness* that makes the audit a formality.
> Current readiness is tracked as a percentage in [`gap-analysis.md`](./gap-analysis.md), **not** as a claim.

## Start here
| File | What it is |
|---|---|
| [`00-system-description.md`](./00-system-description.md) | System boundary + **TSC scope DECISION** (Aidan confirms) |
| [`gap-analysis.md`](./gap-analysis.md) | **Source of truth** — every criterion → state → gap → remediation → status → readiness % |
| [`readiness-roadmap.md`](./readiness-roadmap.md) | Sequenced path: readiness → Type I → Type II; the human/paid decisions |
| [`internal-readiness-assessment.md`](./internal-readiness-assessment.md) | Phase 4 adversarial mock audit (findings ledger) |

## Structure
- [`controls/`](./controls/) — control register + deep-dives (`CC6.1-RLS`, `CC6.1-TENANT`, `CC5-SOD-COMPENSATING`).
- [`policies/`](./policies/) — 19 policies tailored to Meridian's real stack.
- [`evidence/`](./evidence/) — organized by control ID; includes the **RLS cross-tenant negative test** + the
  **authored (not applied) RLS fix migration**.
- [`vendors/`](./vendors/) — subservice org register (carve-out method).
- [`risk/`](./risk/) — risk register + POS & camera threat models.

## Ground rules honored in everything here
1. Never claim "SOC 2 compliant/certified" — track readiness %.
2. No placeholders — human decisions are **DECISION blocks** (choice + recommended default + tradeoff).
3. Nothing was applied to live Supabase / Railway / Contabo. All code-level remediations (RLS fix, BOLA
   threading) are **authored artifacts / PR only**. Aidan reviews and merges.
4. Adversarial verification — the denied path has a negative test (`evidence/CC6.1-RLS/test_rls_cross_tenant.py`).
5. Never fabricate evidence — gaps are stated as gaps; the negative test is marked *not yet executed in CI*.

## The four things only Aidan can decide (do not let them silently block)
TSC scope (full 5 vs minimum-viable) · Type I vs II first · compliance-automation platform + CPA firm +
external pen test · cyber/E&O insurance. Plus org rituals: MFA enablement, background checks, quarterly
access/security reviews. See the roadmap.

## Top of the critical path (highest readiness lift)
**R0** confirm live `pg_policies` → **R1/R3** fix RLS wide-open + restore camera P0 + run denial test in CI →
**R2** finish `enforce_service_member` rollout → **R4** Twilio signature + remove raw PAN/CVV.
