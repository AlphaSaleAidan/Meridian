# Issue #37 — Read-Only Audit: Swarm + Eval Tracks

> Generated 2026-06-03. Pure investigation; zero mutation. No commits, pushes,
> merges, resets, migrations, or HEAD switches in `/root/Meridian`. All branch
> reads done from `/tmp/meridian-overnight-wt/` via `git show` / `git log` —
> no checkouts. Report file is untracked in the worktree; not committed.

---

## TL;DR (the four asks, four answers)

| Question | Answer |
|---|---|
| **Cross-track deps with PR #34?** | **ZERO file-touch intersection** between `model-eval-harness` and `reconcile/contabo-prod-tree`. PR #34 can merge with no conflict against the eval track. |
| **Cross-track deps with main?** | All 27 eval-track files are new or additive against `origin/main`. Only one file (`docs/known_issues.md`) is touched by both the eval track and the P-series; the P-series adds a section the eval track doesn't know about — deliberate merge needed when both eventually land. |
| **Schema drift / untracked migrations?** | **NO prod-schema drift.** The track ships exactly one SQL file (`migrations/2026-06-02-swarm_traces.sql`), and that file is **SQLite, not Postgres**, targeting a local `data/swarm_traces.sqlite` file already gitignored. Lives in `migrations/`, not `supabase/migrations/`. Zero P-series-style risk. |
| **Latently-broken-against-prod code?** | **None.** No Meridian-Supabase code path on this track. The eval recons (`eval/recon.py`, `eval/square_recon.py`) hit prod via PostgREST `HEAD` + `SELECT *` — both are schema-agnostic and survive the P6 column renames. All wave-1 ML models (`economics/models.py`, `customer_ltv.py`, `churn_warning.py`) take data via function args, no DB calls. |
| **Optional FF projection** | `reconcile/contabo-prod-tree` is a direct descendant of `origin/main` — `git merge-base --is-ancestor` confirms. After PR #34 merges, the Contabo box's `git pull origin main` will be a clean fast-forward (no merge commit, no conflicts on `main`). The box's working tree is on `swarm-upgrade` not `main`, so the pull only affects the `main` ref. |

---

## 1. Commits in scope

The summary I was handed referenced "8 swarm + 2 eval" SHAs. **Reality on disk
is broader**: `model-eval-harness` carries 20 commits above `origin/main`
(18 swarm + 2 eval). The 8 SHAs in the summary are the Wave-1 model
implementations; the other 10 swarm commits are baseline infrastructure
(trace recorder, baseline seeder, doc inventory, dump aggregator, pytest
skeleton, etc.).

### Source-of-truth branch: `model-eval-harness`

This is the clean track. `swarm-upgrade` contains the same logical commits
PLUS the POS P-series PLUS canada-portal Phase 2 work — it's a mixed working
tree, not a track. The clean SHAs differ from the summary's:

| Track | summary SHA | model-eval-harness SHA | swarm-upgrade SHA |
|---|---|---|---|
| Wave 1D Platt | `5890b4fb` | `5890b4fb` (same) | `5890b4fb` (same) |
| Wave 1 DGP refinements | `2a6e2af2` | `2a6e2af2` (same) | `2a6e2af2` (same) |
| Phase 1 PostgREST recon | `ae218649` | `ac5143a8` (rebased) | `ae218649` (summary's) |
| Stage A Square recon | `5d3b52a0` | `bd9c1f48` (rebased) | `5d3b52a0` (summary's) |
| `docs(known-issues): POS beta synthetic-only` | `86b44d38` | **NOT PRESENT** | `86b44d38` |

The eval pair was rebased between the two branches. `86b44d38` is
**P-series-only content** that arrived during the reconciliation work; it is
not part of the swarm/eval track proper.

### Full chain on `model-eval-harness` (reverse chronological, top = HEAD)

```
bd9c1f48  feat(eval): stage A — Square API read-only feasibility recon
ac5143a8  feat(eval): phase 1 data-feasibility recon (read-only PostgREST probe)
5890b4fb  feat(swarm): wave 1D — switch CalibratedClassifierCV to Platt (sigmoid)
2a6e2af2  test(swarm): wave 1 DGP refinements + memory-safe MCMC + known_issues skeleton
6053b3dc  chore(swarm): pin Wave 1 deps + auto-load .env in seed runner
b0a799ec  feat(swarm): wave 1D — XGBoost + CalibratedClassifierCV churn classifier
98ffd602  feat(swarm): wave 1A — add panel elasticity (OLS + DoubleML)
601a7c15  feat(swarm): wave 1B — add pymc-marketing CLV path with credible intervals
f14de719  fix(swarm): seed runner refuses unconfirmed demo orgs
3f06e55f  fix(swarm): make trace recorder non-blocking on the realtime path
ba101278  feat(swarm): add pytest skeleton asserting baseline artifact present
f7b3e9fd  feat(swarm): add dump_baseline aggregator → tests/ml_eval/baseline_2026-06.json
86e5d6ef  feat(swarm): add baseline seed runner for the 25 doc-spec tasks
ecd6e7fe  feat(swarm): tee every BaseAgent.analyze() invocation into swarm_traces
794bc540  feat(swarm): tee every LiteLLM call into swarm_traces
2936a936  feat(swarm): wave 1C — Apriori → FP-Growth basket-analysis swap
518ba356  chore(swarm): trim trace_recorder docstring under 300-line limit
7b0c765c  feat(swarm): add stdlib sqlite3 trace_recorder for agent + LLM tees
436d8f4a  feat(swarm): add swarm_traces SQLite schema for baseline tee
6a9e7f72  docs(swarm): phase 0 inventory, agent registry, and baseline
```

All 20 commits are small (1–5 files each). Total surface: **27 unique files**.

---

## 2. File surface

### Grouped by directory

| Directory | Files | Purpose |
|---|---|---|
| `docs/` | 4 (`agent_registry.md`, `known_issues.md`, `swarm_baseline.md`, `swarm_inventory.md`) | Phase 0 inventory, baseline doc, known issues |
| `eval/` | 5 (`__init__.py`, `recon.py`, `square_recon.py`, 2 report mds) | Read-only feasibility recons |
| `migrations/` | 1 (`2026-06-02-swarm_traces.sql`) | **SQLite** schema for local trace DB |
| `requirements-ml.txt` | 1 | Pinned ML deps |
| `scripts/` | 2 (`dump_baseline.py`, `run_baseline_seed.py`) | 25-task seed + aggregator |
| `src/ai/` | 8 (`trace_recorder.py`, `agent_logger.py`, `llm_layer.py`, `agents/base.py`, `agents/customer_ltv.py`, `predictive/churn_warning.py`, `economics/models.py`) | Wave-1 model code + LLM tee |
| `tests/ml_eval/` + `tests/` | 7 (5 wave-1 tests + baseline-present + nonblocking trace test) | New test surface |

---

## 3. Cross-track dependency map

### Method

```
git diff --name-only origin/main..<branch> > files_<branch>.txt
comm -12 files_A.txt files_B.txt
```

Same method that found `docs/known_issues.md` as the sole P-series ↔ swarm
entanglement in the earlier audit.

### Findings

| Pair | Intersection | Risk |
|---|---|---|
| `model-eval-harness` ∩ `reconcile/contabo-prod-tree` (PR #34) | **0 files** | None |
| `model-eval-harness` ∩ `swarm-upgrade` | **27 files (all 27)** | `swarm-upgrade` is the superset working tree; same logical content, no conflict |
| `model-eval-harness` ∩ `origin/main` | 0 files (all 27 are new or additions) | None |

**One file warrants a deliberate merge later, not now:**

- **`docs/known_issues.md`** — content on `model-eval-harness` ends at
  section #3 (Wave 1D not justified on synthetic evidence). `swarm-upgrade`
  adds a section #4 about POS beta synthetic-only (from commit `86b44d38`,
  P-series origin). When both tracks eventually land on `main` separately,
  this file will need a 3-way merge that keeps **both** sections. Not a
  conflict today; flag for the eventual second merge.

---

## 4. Schema drift / untracked migrations

The P-series root cause: P6 column renames were applied to prod via the
Supabase Management API but no tracked migration captured the DDL. PR #34's
`supabase/migrations/20260603_p6_pos_connections_rename.sql` (idempotent,
guarded with `information_schema` checks) closes that gap.

**Does the eval track have the same problem?**

### The one SQL file: `migrations/2026-06-02-swarm_traces.sql`

```sql
-- 2026-06-02-swarm_traces.sql
-- Swarm trace table — Phase 0/Step 2 baseline instrumentation.
--
-- This table is intentionally SQLite-compatible (stdlib sqlite3 writer in
-- src/ai/trace_recorder.py). The same DDL applies cleanly to Postgres if
-- we later promote it to Supabase; SQLite is used today so the recorder is
-- a zero-dep, on-box, no-server tee with no extra requirements.
```

Findings:

1. **SQLite, not Postgres.** Explicit header comment + `INTEGER PRIMARY KEY
   AUTOINCREMENT` + `datetime('now')` default. Cannot run as a Postgres
   migration without rewrites; would not be applied to prod by accident.
2. **Lives in `migrations/`, NOT `supabase/migrations/`.** The Supabase CLI
   only picks up the supabase-prefixed path. The tracked tool will never
   try to push this file to prod.
3. **Writes target `data/swarm_traces.sqlite`** (per `trace_recorder.py`
   line: `MERIDIAN_SWARM_TRACE_DB` env var, default
   `data/swarm_traces.sqlite`).
4. **`.gitignore` already excludes `data/swarm_traces.sqlite`** (added by
   PR #34, commit 15 — `data/swarm_traces.sqlite` line). Consistent with
   the file being a local artifact, not a tracked one.
5. **No `ALTER TABLE`, no `DROP`, no DDL targeting any Meridian table.**

**Verdict: zero drift surface.** This is not a Supabase migration. The
P-series pattern (DDL applied to prod outside the tracked set) cannot
occur here.

### Other prod-DB touches in the track?

Searched all 8 `src/ai/` files + 2 scripts for Supabase / PostgREST /
table mutations:

- `src/ai/agent_logger.py` — no Supabase or PostgREST refs.
- `src/ai/llm_layer.py` — no Supabase refs (LiteLLM tee only).
- `src/ai/trace_recorder.py` — local SQLite only.
- `src/ai/agents/base.py` — no DB calls in the swarm-modified portion.
- `src/ai/economics/models.py`, `src/ai/agents/customer_ltv.py`,
  `src/ai/predictive/churn_warning.py` — take data via function args;
  no DB reads/writes.
- `scripts/run_baseline_seed.py` — no prod refs (calls in-process agent
  methods only).

The only code in the track that hits prod is `eval/recon.py` and
`eval/square_recon.py` — covered in §5.

---

## 5. Latently-broken-against-prod code

### `eval/recon.py` (713 lines, read-only PostgREST recon)

Touches these prod tables via the PostgREST gateway:

```
businesses, business_users, business_locations,
locations, organizations, pos_connections,
daily_revenue, hourly_revenue, daily_product_performance,
inventory_snapshots, employees, products,
insights, forecasts, merchant_health, …
```

**Includes `pos_connections` — the P6-renamed table.**

Two reasons it survives the rename:

1. **Census reads use `HEAD` with `count=exact`** — they ask Postgres for
   a row count, not column data. Column-agnostic.
2. **Per-table column discovery uses `select=*`** — returns all columns
   regardless of names. Column-agnostic.

The script never SELECTs `merchant_id`, `access_token_encrypted`,
`refresh_token_encrypted`, or `location_ids` by name. **Not broken.**

### `eval/square_recon.py`

Hits the Square HTTP API, not Meridian's Supabase. No prod-schema
coupling at all. Not affected by P6.

### Wave-1 model code (`economics/models.py`, `customer_ltv.py`, `churn_warning.py`)

All three take data via function args (the seed runner / call-site
passes a `pd.DataFrame` or list of dicts). None opens a Supabase
client. **Not broken against prod.**

### `scripts/run_baseline_seed.py`

Refuses to run unless `MERIDIAN_BASELINE_CONFIRMED_DEMO=1` and a demo
`DEMO_ORG_ID` is set (commit `f14de719` enforces this). Even if run,
it calls in-process agent methods with synthetic inputs. No prod data
read/write.

### Pre-existing limitations documented in `known_issues.md` (in-scope to acknowledge, out-of-scope to fix)

- **#1 DeepSeek + LiteLLM JSON-mode failure.** Every
  `llm_layer.enhance_insights(...)` call writes `success=0` to
  `swarm_traces` because DeepSeek rejects `response_format` and the
  OpenAI fallback is quota-exhausted on this VPS. **Means the
  baseline-seed produces no useful T1/T2/T3 latency data until
  Step 3 fixes the routing.** Documented at `docs/known_issues.md` §1.
- **#2 Wave 1D not justified on synthetic evidence.** Ships gated
  behind `MERIDIAN_CHURN_CLASSIFIER`; incumbent is the default.

Neither is a regression — both are upfront documented limitations on
the track itself.

---

## 6. Optional dry-run fast-forward projection (PR #34 → Contabo box)

### Method (read-only)

```bash
# In a separate worktree, never on /root/Meridian's main ref:
git merge-base --is-ancestor origin/main reconcile/contabo-prod-tree
# Exit 0 = reconcile is a descendant of main → FF is clean.
```

### Result

**`origin/main` is an ancestor of `reconcile/contabo-prod-tree`.**
PR #34 will merge as a fast-forward (no merge commit, no conflict
resolution required).

### What this means for the Contabo box

After PR #34 merges to `main`:

- `/root/Meridian` is currently on branch `swarm-upgrade` (not `main`).
- A `git pull` against the `main` ref will fast-forward only the
  remote-tracking `origin/main` ref and (if anyone runs it from
  `main`) the local `main` ref.
- The working tree on `swarm-upgrade` is **not affected by the FF**
  unless someone separately rebases or merges. That has to be
  watched live by you, per your stated process.

### Caveats worth knowing before the live watch

1. **`swarm-upgrade` already contains everything in
   `reconcile/contabo-prod-tree`** — the P-series, the migration, the
   schema-rename code edits, the canada.py auth fix. The diff
   `main..swarm-upgrade` is currently 59 files; after PR #34 lands,
   the diff `main..swarm-upgrade` shrinks to ~ the additional
   canada-portal Phase 2 commits + swarm/eval commits the box has
   absorbed but main doesn't yet have.
2. **The 42 uncommitted files in `/root/Meridian` are still
   uncommitted.** They are not part of PR #34. After FF, the working
   tree still shows those 42 dirty entries until someone deals with
   them (separate from this exercise).
3. **`.gitignore` change in PR #34 (commit 15)** widens `.env` →
   `.env*`. If the box has any `.env.local` / `.env.production` files
   that were previously tracked, they will become ignored after FF.
   Probably fine; worth eyeballing the live diff for any actually-
   tracked `.env*` files.

---

## 7. Suggested round-2 scoping for Issue #37

Pre-scoped from the audit, in order of value:

1. **`model-eval-harness` can land standalone.** Zero conflict with
   PR #34's reconciliation. Suggest it goes in its own PR after
   PR #34 is merged + verified, so the diff stays clean and any
   review attention focuses on the ML/eval surface, not the
   reconciliation.
2. **Fix the DeepSeek JSON-mode issue (§5 known_issues #1) before
   the baseline-seed produces useful T1/T2/T3 data.** The track
   itself works; the *signal* it produces is currently
   `success=0`-dominated.
3. **`docs/known_issues.md` 3-way merge.** When eval lands after
   PR #34 (or the next P-series-derived PR), the eval branch has
   sections #1–3, main will have section #4. Take all four —
   sequencing doesn't matter, the sections are independent.
4. **Optional: rename `migrations/2026-06-02-swarm_traces.sql`** to
   something like `local-schemas/2026-06-02-swarm_traces.sqlite.sql`
   to make the local-only status unambiguous to future readers. Pure
   nit; the header comment already says so.

---

## 8. Constraints honored

| Rule | How honored |
|---|---|
| No commits / pushes / merges / resets | All reads via `git log` / `git show` / `git diff` / `git merge-base`. No mutations. |
| No migrations applied | Zero SQL executed. The one SQL file in scope (swarm_traces) is read, not run. |
| Nothing on `main` | Untouched. |
| Nothing on `/root/Meridian` HEAD | Untouched. `git worktree list` shows it still on `swarm-upgrade` at `4de9c15e`. |
| Nothing fires `deploy-frontend.yml` | No frontend files touched, no `main` push. |
| `PR #34` untouched | No comments, no merge, no force-push. Read-only metadata reads only. |
| Stop if mutation needed | Not encountered. Everything answerable from `git show`. |

---

Generated 2026-06-04 ~early-morning UTC. Untracked file at
`/tmp/meridian-overnight-wt/ISSUE-37-AUDIT.md`. Delete after use.
