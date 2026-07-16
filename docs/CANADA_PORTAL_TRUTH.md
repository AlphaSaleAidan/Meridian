# Canada Portal — Source of Truth

> **Rule zero: if a feature's state isn't recorded here, it isn't canonical.**
> Every PR that changes a Canada-side surface MUST update this file in the same PR.
> Claude sessions: read this before touching anything under `frontend/src/pages/canada/`.

**Current canonical:** branch `canada/portal-unified` @ `58a453c8` (PR #96) ·
live bundle `index-DnKEg-Nt.js` · SW cache `meridian-v4-20260612` · deployed 2026-06-12.

---

## 1. The three Canada surfaces (never confuse them)

| Surface | URL | Who uses it | Auth |
|---------|-----|-------------|------|
| **SR (sales rep) portal** | `/canada/portal/*` | Meridian reps selling to merchants | Rep login (`sales-auth`) |
| **Customer portal** | `/canada/dashboard`, `/canada/onboard`, `/customer/login` | The merchant themselves | Customer Supabase login |
| **Demo portal** | `/canada/demo/*` | Prospects (public, synthetic CAD data) | None |

The **US portal is a separate product** (`USPortal*` pages). US and Canada are
**intentionally different** — "fixing" one to match the other is a regression.

---

## 2. Feature truth table — SR portal

| Feature | Correct state | Wrong state (= regression) |
|---------|--------------|---------------------------|
| Proposals | "Generate Proposal" produces the **personalized-deck proposals**; the old top-of-page "Open personalized deck" card is **removed** | Separate "Open Personalized" button; old static proposals |
| Price slider | Slider-selected price **flows into the generated proposal** (incl. first-month-free, checkout QR) | Proposal ignores slider price |
| **POS** | **ZERO POS UI anywhere in the SR portal.** No connect form, no picker grid, no status card. Create-Customer keeps only a plain optional dropdown ("What POS do they currently run?") | Any "Connect POS" form, POSSystemPicker grid, or POS status card visible to a rep |
| Customer account creation | Rep creates account → temp password (`Mer-XXXXXXXX`) emailed; customer forced to reset on first login; rep cannot touch admin/rep/non-Canada accounts | Manual password entry; no forced reset |
| Lead pipeline | Stages without "POS Connected" as a rep action; stage flips to `pos_connected` automatically from the backend when customer data flows | Rep manually marks/causes POS connection |
| Setup handoff | "Send Their Setup Link" step — rep sends link, **customer completes setup in their own portal** | "Help Customer Connect POS" framing / rep-driven connection |
| Commissions | Page exists but pay structure **intentionally unbuilt** — do NOT wire `calculate_commission` | Anyone "finishing" commissions without Aidan's spec |
| Org hierarchy (2026-07-16) | 7-level roles on `sales_reps` (admin → vp_sales → regional_manager → district_manager → office_manager → assistant_manager → sales_rep) with materialized-path downlines. Team page renders the **indented org tree**; role badges come from `frontend/src/lib/role-colors.ts` (define colors THERE, never inline). **Scoped visibility**: admin = forest; managers = own subtree + upline names; leaf reps = self only. Enforced by TWO independent planes — RLS (`20260716_sales_hierarchy.sql`) AND backend filters (`src/api/hierarchy.py`); never remove one because the other exists. Admin edits role/manager via the Team editor → `POST /api/team/assign` (outrank + cycle guards). | Wide-open roster/leads policies; role colors redefined inline; scoping done in only one plane |
| Recruiting (2026-07-16) | `/canada/portal/recruiting` — staged pipeline (applied → screened → interview → offer → hired \| rejected) over `career_applications.stage`. Applications **no longer** auto-create an inactive `sales_reps` row at apply time; the rep row is created at **stage='hired'** with `manager_id = recruiter_id` (tree grows from recruiting). Managers see their branch only. Pre-pipeline applicants keep their legacy inactive rows (Team > Applications approve/reject still works). | Apply-time `sales_reps` upsert reintroduced; unscoped pipeline |

## 3. Feature truth table — customer portal

| Feature | Correct state |
|---------|--------------|
| POS connection | Done HERE by the customer via **one-click OAuth** — the Connect POS step's Square/Clover card → `GET /api/{square\|clover}/authorize?org_id&return_to=/canada/onboard?oauth=connected`; provider hosts the login, callback stores the encrypted token in `pos_connections`, redirects back, wizard advances to Invite Team. No key entry. Square is live (sandbox default); **Clover authorize 503s until `CLOVER_APP_ID/SECRET` are set**. Ingestion verified by `src/tests/test_pos_ingestion.py` (mock tier, zero keys; auto-runs live sandbox when `SQUARE_ACCESS_TOKEN`/`CLOVER_*` present). Both mappers now emit the canonical `transaction_at/type` columns (Clover previously emitted `transaction_time/status/pos_type`, silently dropped by PostgREST → `transaction_at` NOT NULL violation → Clover ingestion failed; fixed 2026-06-15). Square still omits `currency` (nullable; minor follow-up). |
| Onboarding wizard | Trimmed 2-step flow: **Connect POS → Invite Team → done** (2026-06-15). Account is pre-created by the rep (create-customer) and the customer arrives authenticated, so the wizard **starts at Connect POS** — Account/Agreement/Inventory/Schedule/Payment steps removed. **Connect POS shows only Square + Clover** (the supported providers; full 80-system picker not used here). Staff step is a copy/text **invite link** (`/canada/staff-join?org=<org_id>`) — staff self-add. NOTE: the `/canada/staff-join` landing page is a follow-up (not yet built). |
| First login | Temp password accepted once, forced reset (`must_reset_password` metadata) |
| Phone setup wizard (`/canada/merchant/phone?view=setup`, also renders on `/canada/demo`) | The "Set it up" step's forwarding instructions are the shared **`ForwardingWizard`** component (`components/phone/ForwardingWizard.tsx`, 2026-07-16): carrier select (Rogers/Bell/Telus/Freedom/Fido/Koodo/Vidéotron + US + Other) → per-carrier dial codes for BOTH full and conditional (busy/no-answer) forwarding, incl. deactivation codes → **"Verify forwarding" live check** (backend test-calls the store line; green check when it lands on the agent DID). Overflow mode preselects the conditional tab. The old inline CA/US star-code lists are removed. Wizard fires `phone_activation_events` funnel events (demo mode: no backend writes, simulated verify). The transfer-number field helper text warns against pointing transfers at the forwarded store line (transfer-loop guard; backend rejects agent DIDs with a 422). Pricing disclosure card reads live `/api/phone/fees` dials; fallback cap copy is now 8 min (was 5). |

## 4. Feature truth table — demo portal

| Feature | Correct state |
|---------|--------------|
| Shell | Flat-nav merchant layout (Home / Top Actions / Inventory / Schedule / Phone Calls / Camera), teal Canada branding |
| Tour | **No** "Take a Tour" launcher banner |
| Top 3 Actions | Dedicated "Top Actions" nav page; home hero "Money left on the table" = sum of action impacts |
| Data | Synthetic CAD; pre-connection pages show real empty chart/heatmap shells |

---

## 5. Progression timeline (how we got here — and how it broke)

| Date | Event |
|------|-------|
| Jun 3 | Lineages **diverge**: demo-shell work forks off main (merge-base `49773a3b`) |
| Jun 5–7 | Demo/phone work continues on fork; SR-portal work (proposals, price sync, POS-stage drop, wizards) lands on **main** via PRs #32–#81 |
| Jun 8 | **Clobber #1** — uncommitted WIP deployed overnight |
| Jun 11–12 | Temp-password + secret-scanning merged to main (#91, #92); fork formalized as tag `canada-portal-canonical` (PR #90) |
| Jun 12 03:43 | **Clobber #2** — concurrent session deploys main build → demo shell regresses |
| Jun 12 05:53 | **Clobber #3** — restore from canonical tag → SR portal regresses (tag never had main's SR work) |
| Jun 12 | **Union merge** `156fdff5` (PR #96): main's SR portal + canonical demo, conflicts resolved |
| Jun 12 | POS UI fully removed from SR portal (`e8a592bb`, `58a453c8`) — this removal **existed in no branch**; it was lost session work, reimplemented |
| Jun 12 | Deployed `index-DnKEg-Nt.js`; SW cache dated; stale tunnel/preview servers identified |

**Root causes, in order of damage:**
1. Two long-lived parallel lineages, each "fixed" over the other on deploy.
2. Work done in sessions that never committed/pushed (the POS removal) — looked done, then vanished.
3. Review surfaces on the wrong timeline: stale cloudflared tunnel (June-10 preview), unchanging SW cache name, parallel dev servers.

---

## 6. The anti-bad-branching system

### For every change (Claude sessions and humans)

1. **One canonical line.** Until PR #96 merges: `canada/portal-unified`. After: `main`. Feature branches fork from it and merge back within days, not weeks.
2. **Never two sessions on the same surface.** Before starting portal work, check for other active sessions/worktrees touching `frontend/` (`git worktree list`, `ps aux | grep vite`). One writer at a time.
3. **Commit + push the moment something works.** Uncommitted work in a session is work that does not exist. The POS removal was lost exactly this way.
4. **Update this file in the same PR** as any Canada-surface change — the diff to section 2–4 IS the changelog.
5. **Deploy = build from the canonical line + `.env.local` + bump `CACHE_NAME` in `sw.js` (dated) + backup-swap + verify.** Full procedure: `docs/30-operations/frontend-deploy.md`.

### Verifying you're on the right timeline (Aidan's 30-second check)

```bash
# What is the server actually serving?
curl -s https://meridian.tips/ | grep -o 'index-[A-Za-z0-9_-]*\.js'
# Compare with "Current canonical" at the top of this file.
```

- Always review on **https://meridian.tips** — never a `trycloudflare.com` or `localhost` URL left over from an old session (those are frozen snapshots).
- After any deploy: one hard refresh (Ctrl+Shift+R). The dated SW cache makes this self-healing going forward.
- If the site looks wrong: check the bundle hash FIRST (command above). Hash matches canonical → it's your browser/tab. Hash differs → someone deployed the wrong thing; restore from the newest `dist.bak-*`.

### Marking progress points

When a state is reviewed and declared good, tag it:

```bash
git tag canada-portal-YYYYMMDD <commit> && git push origin canada-portal-YYYYMMDD
```

…and update the "Current canonical" line at the top of this file. Tags are
restore points; this file is the map.
