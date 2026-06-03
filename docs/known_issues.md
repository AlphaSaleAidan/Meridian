# Known Issues — tracked for post-Wave-1 follow-up

Items surfaced during the swarm upgrade that are out of scope for the
current run. Do not fix in-flight; pick up after Wave 1 lands.

---

## 1. DeepSeek rejects LiteLLM JSON-mode (`response_format`)

**Discovered:** 2026-06-02, during Wave 1 go-live Phase A seed.
**Owner:** TBD (router / `llm_layer.enhance_insights` surface).
**Severity:** Blocks Step 3 (tier-resolver) baseline; live structured-output
failure on the primary provider.

### What

`src/ai/llm_layer.enhance_insights(...)` asks LiteLLM for JSON output via
`response_format={"type": "json_object"}` (OpenAI-compatible JSON mode).
DeepSeek's API responds:

```
litellm.BadRequestError: DeepseekException -
  {"error":{"message":"This response_format type is unavailable now",
   "type":"invalid_request_error", ...}}
```

The router then falls back to OpenAI per the latency chain. On this VPS
the OpenAI key is quota-exhausted, so:

```
litellm.RateLimitError: RateLimitError: OpenAIException -
  You exceeded your current quota, please check your plan and billing
  details.
```

Net effect: every `enhance_insights` call during the Phase A baseline seed
failed (`success=0` in `swarm_traces`), even though both keys are present
and reachable.

### Reproduction

```
MERIDIAN_BASELINE_CONFIRMED_DEMO=1 \
DEMO_ORG_ID=00000000-0000-0000-0000-000000000000 \
PYTHONPATH=/root/Meridian \
python3 scripts/run_baseline_seed.py
```

Watch `data/swarm_traces.sqlite` — `enhance_insights` rows arrive with
`success=0` and the messages above in `error`.

### Possible fixes (evaluate later — do NOT do in this run)

1. **Drop OpenAI JSON-mode for DeepSeek.** Replace the `response_format`
   ask with explicit JSON-schema prompting + tool/function-calling for
   models that don't support OpenAI JSON mode. LiteLLM supports
   `tools=[…]` cross-provider; DeepSeek-V3 understands function-calling.
2. **Provider routing on JSON-mode.** Have the router send JSON-mode
   calls only to providers that support it (Groq's Llama-3.3-70B does;
   SambaNova varies by model; Cerebras does), and fall back to a plain-
   prompt JSON parser elsewhere.
3. **Top up OpenAI quota** for the meantime. Tactical only — doesn't
   address (1).

### Why this matters for the swarm upgrade

Step 3 of the masterplan (LiteLLM tier resolver + confidence escalation)
needs a populated SQLite baseline of real LLM calls to validate
acceptance. Currently we can produce trace rows but they're all
`success=0` — useless for the latency/cost-by-tier comparisons the
acceptance gate wants. Fixing the JSON-mode call also unblocks the
baseline seed.

---

## 2. Wave 1D — XGBoost + CalibratedClassifierCV not justified on synthetic evidence

**Discovered:** 2026-06-03, during Wave 1 go-live 1D gate.
**Owner:** TBD (predictive/churn_warning surface).
**Severity:** Wave 1 ships with the incumbent — `MERIDIAN_CHURN_CLASSIFIER`
defaults to `gradient_boosting` (sklearn `GradientBoostingClassifier`).
XGBoost path is committed behind the off-flag.

### What

The masterplan's 1D upgrade — replace `GradientBoostingClassifier` with
`XGBClassifier + CalibratedClassifierCV` — was supposed to improve
**calibration** (Brier + ECE) at no quality cost (AUC / AvgPrec). On the
synthetic churn DGP the test suite uses (n=5000, planted ~15% positive
rate, realised 22.7% after percentile-thresholding the noisy log-odds),
the upgrade does NOT clear the gate under either calibration method
tried — both isotonic and sigmoid (Platt).

Comparison (GBM = incumbent, XGB+cal = upgrade candidate, GBM unchanged
between runs because the test fixture is seeded):

| Metric | GBM | XGB + isotonic (cv=3) | XGB + sigmoid (cv=3) |
|--------|-----|-----------------------|----------------------|
| AUC    | 0.7320 | 0.7222 ❌ | 0.7214 ❌ |
| AvgPrec| 0.5479 | 0.5251 ❌ | 0.5285 ❌ |
| Brier  | 0.1439 | 0.1461 ❌ | 0.1464 ❌ |
| ECE    | 0.0393 | < incumbent ✅ | 0.0167 ✅ |

Gate is *Brier AND ECE strictly lower than incumbent, with AUC/AvgPrec
not worse*. Both candidates clear ECE but **fail Brier** (regress by
~0.002–0.003) and **fail AUC/AvgPrec** (regress by ~0.01–0.02).
Reading: the cv=3 calibration data cost dominates any quality signal
on this noisy DGP — both calibrators end up regressing the underlying
ranking quality while only the bin-summarised reliability metric (ECE)
improves.

### Reproduction

```
PYTHONPATH=/root/Meridian /root/Meridian/.venv/bin/python \
  -m pytest tests/ml_eval/test_churn_classifier.py -v -s
```

The fixture seeds via `RNG_SEED=23`; the table above is reproducible
verbatim. The test file currently mirrors production
(`method="sigmoid"`); the prior isotonic comparison was captured before
the sigmoid swap.

### Possible follow-ups (evaluate later)

1. **Validate on real Meridian churn data.** Synthetic noise is the
   load-bearing assumption here. Real customer panels may have
   structure XGB exploits better than GBM, or the calibration may
   actually need it. The synthetic finding is informative but not
   final.
2. **Try `CalibratedClassifierCV(cv="prefit")` on a true held-out set**
   instead of cv=3 over the training fold. Eliminates the cv-fold
   training-data cost. Requires a real train/calibration/test triple
   on real data — synthetic test fixture would need restructuring.
3. **Skip CalibratedClassifierCV entirely** and use XGB's native
   `objective="binary:logistic"` probabilities with temperature
   scaling on a held-out fold. Simpler and avoids the cv=3 data cost.

### Why this matters for the swarm upgrade

We have a clear, reproducible finding: on this DGP the upgrade is not
justified. Shipping behind an off-flag preserves the implementation
without forcing a downstream change. The test will continue to fail
on the synthetic gate until real-data validation either confirms the
upgrade or motivates removing the XGB path. **Do not loosen the gate
thresholds to make the test pass** — the test is now the watchdog.

---

## 3. Wave 1B — pymc-marketing CLV: per-customer credible intervals unvalidated

**Discovered:** 2026-06-03, during Wave 1 go-live 1B gate.
**Owner:** TBD (`src/ai/agents/customer_ltv.py`).
**Severity:** Wave 1 ships with the incumbent — `MERIDIAN_CLV_BACKEND`
defaults to `lifetimes` (MLE point estimates). pymc-marketing path is
committed behind the off-flag.

### What

The 1B upgrade was supposed to add **per-customer credible intervals**
on top of the lifetimes MLE point estimates. The cohort-level CLV
reconciles between backends (ratio within tolerance), so the headline
number is sound. The per-customer intervals are NOT trustworthy on the
evidence we have:

On the memory-capped MCMC fit (n=120, draws=300, tune=300, chains=2,
cores=1, OMP_NUM_THREADS=1 — required so the fit fits in the VPS heap
alongside PoolDrop and qwen-server):

- **30% (28/92) of returning customers** had width-collapsed credible
  intervals (`hi − lo < 1.0`). Threshold for the test was <25%.
- **Only 7% (6/92) of lifetimes-MLE points** fell inside the
  pymc-marketing 80% credible interval. Threshold for the test was
  ≥50%.

Reading: under the memory cap, the posterior is simultaneously
over-concentrated (collapsed widths) and mis-centered (low coverage)
on a third of the cohort. We cannot conclude the pymc-marketing CIs
are calibrated; we also cannot conclude they aren't, because the MCMC
budget was tight on purpose.

### What ships

- Cohort-mean CLV (which reconciles) — **safe to surface**.
- Per-customer CLV with credible intervals from pymc-marketing —
  **not surfaced**. `MERIDIAN_CLV_BACKEND=lifetimes` (default).

### Possible follow-ups (evaluate later)

1. **Validate on real Meridian transaction data** with full-scale MCMC
   (draws ≥ 2000, tune ≥ 2000, chains = 4, cores ≥ 2). Requires
   memory headroom — currently blocked by PoolDrop dev server's 25GB
   resident footprint. Convert PoolDrop to a prod build after
   Thursday's demo, then revisit.
2. **Investigate the degenerate CIs** — likely the small-cohort
   posterior collapses on customers with thin frequency histories.
   Either filter those customers out of the per-customer CI surface,
   or report a "low-confidence" flag instead of a credible interval
   below a width threshold.
3. **Add a calibration backtest harness** that holds out the last N
   days of transactions per customer and checks coverage of the
   credible intervals against realised CLV. Synthetic eval is not a
   substitute.

### Why this matters

The cohort number was the original ask; the per-customer CIs were a
stretch goal. Shipping cohort-only is honest and safe. The
implementation work is preserved behind the flag and can be revisited
without re-implementing.

---

## 4. POS beta-gate (P0+P1) verified only on synthetic payloads

**Discovered:** 2026-06-03, immediately after the P0+P1 beta gate.
**Owner:** TBD — first real-merchant connection is the load test.
**Severity:** Beta-blocker risk surface. Code paths verified, but a
real Square / Clover / Toast merchant has not yet been connected.

### What

The P0 schema migration (`supabase/migrations/20260603_pos_beta_wiring.sql`)
+ P1 application wiring were verified end-to-end on **synthetic
order payloads**, not against a live merchant token, because:

1. The only Square production token on this box is the operator's own
   dev/test Square account (1 location, 56 orders, 0% `customer_id`
   coverage — Stage A recon
   `eval/reports/square_recon_2026-06-03.md`). Useless as an
   identity-persistence test.
2. No Clover or Toast credentials are on the box at all.
3. The Meridian production transactions table itself still has 3
   rows (Phase 1 recon).

### What was actually tested

- `Square DataMapper.map_transaction` — fed a synthetic
  `{id, location_id, customer_id, total_money:{currency:'CAD'}, ...}`
  payload; verified output keys include `customer_id`,
  `customer_email`, `currency`.
- `Toast ToastDataMapper.map_order` — fed a synthetic order with
  `checks[0].customer = {guid, email}`; verified the same three keys
  populate.
- `Clover CloverDataMapper.map_order_to_transaction` — fed a
  synthetic order with `customers.elements[0].id`; verified.
- `normalize_transaction` (GenericREST) — fed synthetic payloads with
  inline + caller-default currency variants; verified.
- Production DB columns + FK + indexes — verified via
  `information_schema` query after the management-API apply.
- Frontend type-check (`tsc --noEmit`) passed on every edited file
  plus the 7 `connectPos` callers.
- Production smoke test (a real Square merchant credential-pasting
  into the wizard and watching the backfill land on the
  `transactions` table with `customer_id` + `currency` populated)
  has **NOT** been run.

### What we still don't know

- Whether Square's `/v2/orders/search` response shape on a real
  merchant matches what the mapper expects (esp. tender shapes,
  void/cancel state mapping, line-item line-discount handling on
  large orders).
- Whether Clover's `/orders` response shape on a real bank-channel
  rebrand (PNC POS, Wells Fargo POS, etc.) deserialises the same
  way as canonical Clover.
- Whether Toast's `client_id` / `client_secret` exchange round-trip
  works under our actual partner-program credentials (we don't
  have a Toast partner token).
- Whether `db.batch_upsert` (Supabase REST PostgREST under the
  hood) rejects unknown columns silently or noisily if a sync
  engine accidentally emits one — we haven't observed a row land
  in `transactions` from a real backfill yet.

### What unblocks each of these

The **first real beta merchant** unblocks them all at once:
connect, watch the backfill complete (or fail), then inspect
`transactions` for `customer_id` + `currency` + `customer_email`
populated rows and `pos_connections.connected_by_rep_id` written.
If anything is dropped silently, the gap shows up as a column
returning NULL where the upstream payload had a value.

Until that happens, treat P0+P1 as "code is in place, contract
not yet observed in production".

---

## 5. P4 — Clover mapper fixes (FIXED-BUT-UNVERIFIED)

**Discovered:** 2026-06-03, during the P4 mapper-vs-schema audit
triggered by the e2e Square backfill test.
**Fixed in commit:** the P4 mapper-fix commit (`src/clover/mappers.py`
+ `src/clover/sync_engine.py`).
**Severity:** Code is now correct. Live verification still pending
the first real Clover merchant connection — no Clover token exists
on this VPS so end-to-end exercise is not yet possible.

### What was wrong

The Clover sync engine's mapper output had several column-name and
required-field mismatches against the destination tables. Every
mismatch was silent — PostgREST drops unknown columns and only
fails when a NOT NULL column ends up NULL after the drop. Net
effect: a real Clover merchant connecting today would have hit
NOT NULL violations on `transactions.transaction_at` and
`transaction_items.{transaction_at, product_name}` on the first
batch upsert, and the backfill would have aborted with zero rows
landed (same failure shape Square hit before P4).

Specifically:

| Mapper | Bug | Fix |
|---|---|---|
| `map_merchant_to_location` | `postal_code` → silent drop | renamed to `zip_code` (the actual column) |
| `map_order_to_transaction` | `transaction_time` → silent drop → `transactions.transaction_at NOT NULL` violation | renamed to `transaction_at` |
| `map_order_to_transaction` | `status` → silent drop (not a column) | replaced with `type` (`sale` / `void`, derived from Clover's `state`) |
| `map_line_item` | `transaction_time` → silent drop → `transaction_items.transaction_at NOT NULL` violation | renamed to `transaction_at`; sync engine call sites updated to pass the new kwarg name |
| `map_line_item` | `name` → silent drop → `transaction_items.product_name NOT NULL` violation | renamed to `product_name` |

A few decorative fields (`pos_type`, `country`, `timezone`,
`currency` on locations; `is_online`, `source`, `created_at` on
transactions) are still emitted by the mapper and still silently
dropped by PostgREST. They're harmless — kept so a trace of the
upstream-Clover shape is observable in the raw mapper output. The
real upsert payload that PostgREST writes is now schema-compatible.

### What's still pending

End-to-end run against a real Clover merchant — the same
contract awaiting a real Square merchant for `customer_id`
persistence verification.

Until a Clover token is on this box, treat the fix as "code is
correct, contract not yet observed in production." Once a Clover
beta merchant connects:

1. Confirm the full `locations → products → transactions → items`
   chain lands rows for them, parallel to the Square e2e run.
2. Confirm `customer_id` populates from
   `order.customers.elements[0].id` (verified inline in the mapper
   but the e2e contract still awaits real data).
3. Confirm `currency` populates from `merchant.defaultCurrency` (also
   verified inline; awaits a real account where Clover sets it).

---
