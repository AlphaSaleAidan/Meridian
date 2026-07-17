# Meridian Commission & Payment Model — Proposal (July 2026)

**Status:** PROPOSAL — for decision by Aidan (CEO) + Enoch (CRO). Commission percentages are business decisions; this document models options and recommends defaults. Nothing here is wired into code yet.
**Author context:** grounded in prod Supabase (queried read-only 2026-07-17) and the shipped hierarchy (`supabase/migrations/20260716_sales_hierarchy.sql`), fee-terms canon (`src/billing/fee_terms.py`), and voice ledger (`src/services/voice_ledger.py`, `src/api/routes/vapi_webhook.py`).

---

## 1. Executive summary

We just shipped the 7-level sales org tree (admin → VP Sales → Regional → District → Office → Assistant Manager → Sales Rep) and locked contract terms per merchant. The commission tables (`commissions`, `payouts`, `rep_client_assignments`) exist in prod but are empty by design — the pay structure was deliberately left undecided. This document is that decision.

**What the real numbers say:** our AI phone agent costs us an average of **US$0.15 per call** (10 real calls, max US$0.29), while a mid-tier Canadian merchant pays **CA$500/month plus CA$1.99/order**. Even at healthy call volume, a merchant's contribution margin is roughly **85–90%** before commissions. That margin comfortably supports paying the sales org **25–30% of collected monthly subscription revenue** and still leaves the company the majority of every dollar.

**Recommendation in one paragraph:** pay a **diminishing override cascade** — the closer earns **20%** of the merchant's collected monthly fee as a recurring residual, with small overrides flowing up the chain (Assistant Manager 2%, Office Manager 4%, District 2%, Regional 1%, VP 1% — 30% max, and only occupied levels get paid; today's roster only occupies two levels, so real near-term cost is ~24%). The closer's first month is boosted: **100% of the first collected month** as an activation bonus instead of the residual. Residuals are paid **only on cash actually collected**, so churn stops payments automatically; activation bonuses claw back if a merchant churns inside 90 days. Payouts run **monthly, NET-15, CA$50/US$50 minimum**, manual e-transfer/Zelle at first, automated later. The 5-minute call cap is locked; keep phone pricing exactly as contracted (3 minutes included, then 45¢/min) — the data shows no reason to touch it yet, and the new `voice_call_endings` telemetry will tell us within 30 days if the cap is costing orders.

**One landmine to defuse before anything ships:** every rep row in prod has `commission_rate = 0.70`, written by signup code that meant "70%" — but the database function that computes commissions treats that as **0.7%**. The unit must be declared, the rows corrected, and rates moved to a role-keyed plan table before the first commission is ever calculated. Section 3.5 has the fix.

---

## 2. Unit economics per merchant

### 2.1 Real production numbers (all queries read-only, 2026-07-17)

| Metric | Value | Source query |
|---|---|---|
| Vapi cost per call (avg) | **US$0.147** (n=10, min $0.01, max $0.29; 2026-06-29 → 07-14) | `SELECT source, kind, COUNT(*), SUM(amount_cents), AVG(amount_cents) FROM voice_ledger GROUP BY source, kind` → `vapi_call/debit: n=10, total=147¢` |
| Overage revenue billed to date | **$0** (zero `duration_overage` credits; zero `stripe_fee` credits) | same query — only `vapi_call` rows exist |
| Phone orders | 4 (June), 7 (July MTD) | `SELECT date_trunc('month',created_at), COUNT(*) FROM phone_orders GROUP BY 1` |
| `voice_call_endings` | **0 rows** (telemetry shipped 07-16, not yet collecting) | `SELECT disposition, COUNT(*) FROM voice_call_endings GROUP BY 1` |
| Sales roster | 20 reps: 3 admin, 1 office_manager, 13 active sales_rep, 3 inactive; **all** `commission_rate = 0.70` | `SELECT role, is_active, COUNT(*), array_agg(DISTINCT commission_rate) FROM sales_reps GROUP BY role, is_active` |
| Closed deals | US: 7 `closed_won` @ $250/mo avg (3 lost); CA: 9 leads in walkthrough/checkout, none closed. **No** lead has fee-terms locked, no `plan_tier` set | `SELECT stage, COUNT(*), AVG(monthly_value) FROM us_leads GROUP BY stage` (+ canada_leads) |
| `commissions` / `payouts` / `rep_client_assignments` / `merchant_billing_terms` | **0 / 0 / 0 / 0 rows** | count query |
| Hierarchy migration | **applied to prod** (`role`, `manager_id`, `path`, `level` columns present) | `information_schema.columns` |

**Data is thin.** Ten calls and eleven phone orders is not a distribution — every projection below is a clearly labeled assumption layered on the real per-call cost.

### 2.2 Contribution margin per merchant per tier

Contracted terms (canonical, `src/billing/fee_terms.py`): monthly fee US$250/350/500, CA$350/500/700; per-order fee US$0/$1.49/$1.00, CA$0/$1.99/$1.39 (Standard/Premium/Command); calls 3 min included then 45¢/min, hard cap 5 min ⇒ max 90¢ overage/call.

**Assumptions (labeled):** 300 phone orders/mo at maturity (≈10/day), 2.0 calls per order → 600 calls/mo; Vapi at the observed US$0.15/call; 10% of calls incur 1 overage minute; FX 1.37 CAD/USD. Conservative scenario: 100 orders / 200 calls.

| Tier | Monthly fee | Order-fee rev (100 / 300 orders) | Overage rev (200 / 600 calls) | Vapi cost (200 / 600 calls) | **Contribution (conserv. / mature)** |
|---|---|---|---|---|---|
| US Standard | $250 | $0 / $0 | $9 / $27 | $30 / $90 | **$229 / $187** |
| US Premium | $350 | $149 / $447 | $9 / $27 | $30 / $90 | **$478 / $734** |
| US Command | $500 | $100 / $300 | $9 / $27 | $30 / $90 | **$579 / $737** |
| CA Standard | CA$350 | 0 / 0 | CA$9 / 27 | CA$41 / 123 | **CA$318 / 254** |
| CA Premium | CA$500 | CA$199 / 597 | CA$9 / 27 | CA$41 / 123 | **CA$667 / CA$1,001** |
| CA Command | CA$700 | CA$139 / 417 | CA$9 / 27 | CA$41 / 123 | **CA$807 / CA$1,021** |

Two things this table exposes:
1. **Standard tier margin *shrinks* with usage** (no per-order fee funds the calls) — Standard merchants are loss-leaders on the phone product at volume; commissions on Standard should therefore lean lower or the tier should be steered against.
2. **A discrepancy to fix:** the applied per-order fee in live billing is the env default `MERIDIAN_SERVICE_FEE_CENTS` ($2.50) when `phone_agent_config.order_fee_cents` isn't set, while contracted tier rates are $0–$1.99. `src/billing/fee_reconciliation.py` exists precisely to flag this; provisioning must write the contracted rate into `phone_agent_config` (open decision D12).

---

## 3. Commission cascade options on the 7-level tree

All models share these ground rules: commissions accrue on **collected** monthly subscription revenue, in the **currency of the deal**; the closer is the rep on the lead at fee-terms lock; overrides flow up the `sales_reps.path` chain; **admin (level 1) never earns commission**.

### Model A — Flat closer % + fixed dollar override per level

Closer 20% of collected monthly fee; each occupied upline level gets a **flat** amount per active merchant-month: AM $10, OM $20, DM $10, RM $5, VP $5 (CA$ same figures).

- **Worked example — Middle-tier (Premium) CAD deal, CA$500/mo, full 6-deep chain:** closer CA$100 + AM 10 + OM 20 + DM 10 + RM 5 + VP 5 = **CA$150/mo (30%)**; company keeps CA$350.
- **Cost at 10 / 50 / 200 merchants** (avg CA$500, full chains): CA$1,500 / 7,500 / 30,000 per month. But fixed overrides don't scale with tier — on a CA$700 Command deal total drops to 27.1%, on CA$350 Standard it rises to 34.3%.
- **Incentives:** managers are paid for *merchant count*, not deal quality — they'll push volume and won't care about tier upsell. Predictable for budgeting; regressive against the tier strategy.

### Model B — Diminishing override cascade (RECOMMENDED)

Percent-of-collected-MRR at every level: **Closer 20% → AM 2% → OM 4% → DM 2% → RM 1% → VP 1%** (30.0% ceiling). Unoccupied levels' overrides are **retained by the company** (no roll-up) — today's prod roster occupies only sales_rep + office_manager, so the realistic near-term cost is **24%** of MRR.

- **Worked example — same CA$500 Premium deal, full chain:** closer CA$100, AM CA$10, OM CA$20, DM CA$10, RM CA$5, VP CA$5 = CA$150. With today's actual roster (rep → OM only): closer CA$100 + OM CA$20 = **CA$120**.
- **Cost at 10 / 50 / 200 merchants** (avg CA$500): full chains CA$1,500 / 7,500 / 30,000; today's two-level reality CA$1,200 / 6,000 / 24,000.
- **Incentives:** every level's pay scales with tier and with retention — managers coach reps to sell Premium/Command and to keep merchants alive (residuals die with churn). OM gets the largest override because that's the level doing daily rep management. This is the standard, legible field-sales structure; easy to explain in recruiting ("build an office, earn 4% of everything it closes, forever-while-it-pays").

### Model C — Pool-based

25% of all collected MRR goes into a commission pool: 70% of the pool to closers pro-rata by their book, 30% split across the upline by level weights.

- **Worked example — CA$500 deal:** pool CA$125; closer CA$87.50; upline shares AM 7.50 / OM 15 / DM 7.50 / RM 3.75 / VP 3.75.
- **Cost at 10 / 50 / 200:** CA$1,250 / 6,250 / 25,000 — cheapest, but…
- **Incentives:** weakest individual attribution; a strong closer subsidizes weak ones; hard to explain on a statement; disputes guaranteed. Not recommended.

### Recommendation: **Model B**, with this recurring/one-time split

- **Activation bonus (one-time):** closer receives **100% of the first collected monthly fee** (replaces month-1 residual; overrides still pay normally on month 1). On a CA$500 deal the closer makes CA$500 up front — big, immediate, recruiting-friendly.
- **Residual (recurring):** the 20%/2%/4%/2%/1%/1% cascade from month 2, **for as long as the merchant pays**. No arbitrary 12-month cut-off — retention is the product's whole thesis, and paying on collected cash makes the residual self-limiting.
- **Churn stop:** a residual accrues only when an invoice is actually collected. Merchant cancels or fails payment → the next accrual simply never happens. No manual switch-off needed.
- **Clawback:** if a merchant churns within **90 days**, the activation bonus is clawed back pro-rata (churn day 30 → 2/3 clawed back), netted against the rep's future commissions (never invoiced back to the rep). Commissions on refunded invoices reverse via a negative `commissions` row.
- **Rep fee slider (+US$100 / +CA$150 headroom above tier base):** the closer keeps **50% of the slider premium each month** on top of the base residual; overrides are computed on the **tier base only**. This makes selling above base directly and visibly profitable for the closer (sell CA$650 instead of CA$500 → +CA$75/mo personal) without inflating the whole cascade. Alternative (simpler): treat the full monthly as ordinary MRR — decision D5.
- **Commission base:** monthly subscription fee **only**. Order fees and call overage are excluded — they fund the AI infrastructure (Section 2 shows Standard-tier margins can't carry commissions on usage revenue).

### 3.5 The `commission_rate` landmine (must fix before any commission is calculated)

- Schema: `sales_reps.commission_rate DECIMAL(5,2) DEFAULT 30.00` — **percent** semantics; `calculate_commission()` (migrations/022) computes `gross × rate / 100`; `admin.py` validates 0–100.
- Reality: **all 20 prod rows hold `0.70`**, written by `src/api/routes/canada.py:251`, `us.py:259`, and `careers_pipeline.py:141` — clearly intended as a *fraction* meaning 70%. Under the RPC's math that pays **0.7%**.
- **Resolution (proposed):** (1) declare the canonical unit **percent**; (2) stop using a free-form per-rep column at all — create a `commission_plans` table keyed by role (percent per level, activation multiplier, clawback window) and snapshot the whole plan onto each commission row; (3) backfill the 0.70 rows to the decided closer rate; (4) add `CHECK (commission_rate BETWEEN 0 AND 100)` and fix the three signup writers; (5) frontend `commission-flags.ts` (`COMMISSION_TRACKING_PAUSED`) stays `true` until this lands.
- **Second schema blocker:** `uq_commissions_source UNIQUE (source_type, source_reference)` allows only **one** commission row per payment — a cascade needs one row per upline level. The constraint must become `(source_type, source_reference, rep_id)`, plus new columns `level`, `origin_rep_id` (the closer), `merchant_id`.

---

## 4. Payout mechanics

**What exists:** `payouts` table (method: venmo/zelle/bank_transfer/manual), `record_manual_payout()` RPC that batches all unpaid earned commissions, admin read routes in `src/api/routes/payouts.py` (`/summary`, `/reps`, `/balances`, `/history`), and `CommissionService` (`src/payouts/commission_service.py`). What's missing is the **trigger** and the **cadence policy**.

**Proposed policy:**
- **Cadence:** monthly, covering the prior calendar month, paid by the **15th** (NET-15). Collected-cash basis.
- **Minimum:** CA$50 / US$50; below-minimum balances roll forward.
- **Statements:** auto-generated per rep per period from `commissions` rows (merchant, tier, gross collected, rate, level, amount, running balance); visible in the rep portal; the statement is the dispute artifact.
- **Dispute window:** 14 days from statement issue; disputed rows flip to the existing `disputed` status and are excluded from the payout run until resolved.
- **Method:** P1 stays manual (e-transfer CA / Zelle US) recorded via `record_manual_payout`; P3 automates transfers via the existing Stripe Connect rails (migration `028_unified_stripe_connect.sql`).

**The missing trigger — concrete wiring plan:**
1. **First payment:** `checkout.session.completed` in `src/api/routes/stripe_checkout.py` (already signature-verified and deduped via `webhook_events`) → resolve org → fire activation bonus + month-1 overrides.
2. **Renewals:** `invoice.paid` (stripe_checkout.py:165 — today it only logs) → map `subscription → org` via `checkout_sessions` → fire monthly residual cascade.
3. **Square rail:** `src/billing/billing_service.py` is Square-based; if any merchant is billed on Square invoices, the Square invoice-paid webhook must call the same hook — `src/payouts/webhook_hook.py:on_payment_received()` was built for exactly this and currently has **zero callers**.
4. Replace single-rep `calculate_commission()` with `calculate_commission_cascade(p_org_id, p_gross, p_source_type, p_source_ref)`: resolve closer via `rep_client_assignments` (provisioned at deal close, alongside the `merchant_billing_terms` write in the close flow), walk `sales_reps.path` upline, insert one idempotent row per occupied level from the `commission_plans` snapshot.
5. **Assignment provisioning:** at fee-terms lock (`lock_lead_fee_terms` / `set_merchant_billing_terms` call sites), insert `rep_client_assignments(rep_id=lead.rep_id, org_id=merchant)` — this is the join the cascade needs and it is empty today.
6. Cross-check: monthly reconciliation extends `fee_reconciliation.py` — "every collected invoice has exactly N cascade rows; every cascade row maps to a collected invoice."

---

## 5. Phone pricing forward (5-minute cap: LOCKED)

Real data: our all-in Vapi cost averages **US$0.147/call** (max $0.29, n=10 — cited in §2.1). At the contracted 45¢/min overage, **one** overage minute more than covers our entire average call cost. The cap math holds: 5-min cap − 3 included ⇒ max 2 overage minutes ⇒ **max 90¢/call billed**, while our own worst-case cost at the cap is roughly US$0.35–0.50.

| Option | Expected effect | Verdict |
|---|---|---|
| **Keep 3-min included @ 45¢/min** | Zero contract churn; overage revenue currently $0 and immaterial; margin already 85–90% | **Recommended** |
| 2-min included @ 45¢/min | Adds maybe CA$27–80/mo/merchant at mature volume; re-papers every signed lead (`fee_terms_locked_at` doctrine says terms are locked — changing requires supersede-not-update rows and rep conversations); perception risk pre-PMF | Not now |
| Flat per-call fee | Simpler to explain, but invalidates the canonical fee schedule, the slider, and the reconciliation module in one move | Not now |

**Watch before changing anything** — `voice_call_endings` (shipped 07-16, 0 rows yet):
- `disposition='cutoff'` share of calls, and especially **cutoff with `had_order=false`** — the direct measure of "orders the cap is killing." Threshold to react: >5% of calls.
- Duration distribution p90 vs 300s; overage incidence (calls >3 min).
- Re-decide after **≥200 calls or 30 days**, whichever is later.

---

## 6. Site integration plan

**P1 — Read-only earnings visibility (est. 2 weeks: ~1 backend, ~1 frontend)**
- Rep portal **Earnings** tab (both `frontend/src/pages/canada/portal/` and `us/portal/`): personal residuals, pending/paid, statement list. Reads `commissions`/`payouts` under the already-shipped downline RLS policies (`commissions_downline_read`, `payouts_downline_read`).
- **Downline rollup** on the existing Team pages using `build_tree()` scoping from `src/api/hierarchy.py` — managers see subtree earnings, never lateral branches.
- Admin commission console: extend `src/api/routes/payouts.py` (routes already exist) + an admin page; record manual payouts.
- Flip `COMMISSION_TRACKING_PAUSED=false` only after the §3.5 unit fix lands.
- Prereq (small migration): cascade columns + unique-constraint change + `commission_plans` table.

**P2 — Automated calculation (est. 2–3 weeks)**
- `calculate_commission_cascade()` RPC + Stripe/Square webhook wiring (§4) + `rep_client_assignments` provisioning at close + clawback/negative rows on refund/early churn + monthly statement generation + reconciliation checks. Red-first tests alongside `tests/rls/test_hierarchy_isolation.py`.

**P3 — Automated payouts + merchant transparency (est. 2–4 weeks)**
- Payout run cron (NET-15), dispute workflow on `disputed` status, Stripe Connect transfers (028 rails), and a merchant-facing **"Get Paid" / billing transparency** page: contracted terms from `merchant_billing_terms`, live voice-ledger balance, per-order fee ledger — the merchant sees exactly what they signed and what they're charged.

---

## 7. Open decisions table

| # | Decision | Options | **Recommended default** |
|---|---|---|---|
| D1 | Cascade model | A flat-override / B diminishing % / C pool | **B** |
| D2 | Closer residual % | 15 / 20 / 25% | **20%** |
| D3 | Override ladder | per-level %s | **AM 2, OM 4, DM 2, RM 1, VP 1 (30% ceiling)** |
| D4 | Unoccupied-level overrides | company keeps vs roll up to next occupied level | **Company keeps** |
| D5 | Slider premium (+$100/CA$150) | closer keeps 50% of premium vs treat as ordinary MRR | **Closer keeps 50%; overrides on tier base only** |
| D6 | Activation bonus | 100% of first month vs flat $200 vs none | **100% of first collected month (replaces month-1 residual)** |
| D7 | Residual duration | perpetual-while-paying vs 12/24-month cap | **Perpetual while collected** |
| D8 | Clawback window | 60 / 90 / 120 days, pro-rata | **90 days, pro-rata, netted against future commissions** |
| D9 | Commission base | monthly fee only vs + order fees/overage | **Monthly subscription fee only, collected cash** |
| D10 | `commission_rate` unit resolution | percent + plan table vs fraction | **Percent; role-keyed `commission_plans`; backfill the 0.70 rows** |
| D11 | Payout cadence / minimum / dispute | monthly NET-15, $50 min, 14-day window | **As stated** |
| D12 | Per-order fee alignment | provision contracted tier rate into `phone_agent_config` vs keep $2.50 env default | **Provision contracted rate; reconcile via fee_reconciliation** |
| D13 | Payout currency | deal currency vs convert to USD | **Deal currency** |
| D14 | Phone pricing | keep 3-min included / 2-min / flat per-call | **Keep 3-min @ 45¢; re-decide after ≥200 calls of `voice_call_endings` data** |
| D15 | Standard-tier commission | same cascade vs reduced (e.g. closer 15%) given negative usage margin | **Same cascade for simplicity; monitor** |

---
*Every number above is either cited to a prod query (§2.1) or labeled as an assumption. Prepared 2026-07-17.*
