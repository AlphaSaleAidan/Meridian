# Meridian SR Auto Dialer — Build Plan

> Branch `feat/rep-autodialer` (off `origin/main` @ `0f5d738e`). Never merges without Aidan's approval.
> Scope: a rep-facing **Auto Dialer tab** in the SR portals (Canada first-class, US mirror) and an
> **admin-or-better Call Console** on the Canada side to manage/process calls as they happen.

## 1. What we're mimicking (competitor research summary)

Surveyed: Orum, Nooks, Kixie PowerCall, PhoneBurner, JustCall, Aircall, Close, Salesloft, Outreach, RingCentral Engage Voice.

**v1 must-haves** (industry consensus for an in-CRM power dialer):
1. **Power dial** — single-line auto-advance over a queue, configurable wrap-up seconds, pause/resume. (Parallel/predictive deliberately skipped: predictive drags in the CRTC ≤5%/month abandonment-rate regime with 3-year record-keeping; power dial has zero abandonment risk because the rep is always present.)
2. **Browser softphone (WebRTC)** — the norm across the whole category (Close/Kixie/Nooks/Orum are all in-browser). Telnyx WebRTC, since Meridian already runs Telnyx.
3. **Contact card + inline notes** beside the dial pad; every attempt auto-logged.
4. **One-click dispositions** with automation hooks — the highest-leverage feature in the category (PhoneBurner's "disposition sets"): disposition → tag + note + schedule callback / mark DNC / advance lead stage in one click.
5. **Timezone-aware callback scheduling** that re-injects the lead into the queue when due.
6. **Compliance gate at dial time (hard block, not a warning)** — internal DNC list + calling-hours window derived from the lead's area code. Canada CRTC UTRs: weekdays 09:00–21:30, weekends 10:00–18:00 local; US TCPA 08:00–21:00 local.
7. **Session stats / analytics** — dials, connects, connect rate, talk time, dispositions per rep/day.
8. **Admin live console** — who's dialing / on a call / wrapping, live timers, call history with dispositions + notes, callbacks due, DNC management, per-rep analytics.

**Deferred to v1.5+** (specced, not built now): voicemail drop (needs media injection into the call leg — Call Control `playback_start` on a conference), local-presence number pools + spam-reputation rotation, listen/whisper/barge (needs conference-bridge architecture), inbound ring group + screen-pop, AI call summaries, parallel 3-line dialing with answering-machine detection, on-screen scripts with merge fields, call recording storage (needs consent flow + retention policy + storage bucket — do not half-ship recording).

## 2. Architecture decisions

| Decision | Choice | Why |
|---|---|---|
| Dialing mode | Power dial (single line, auto-advance) | Throughput without the predictive compliance regime; rep always present |
| Voice path | **Telnyx WebRTC** browser softphone; backend mints on-demand telephony-credential tokens (`POST /v2/telephony_credentials` on a Credential Connection + `/token`) | Repo already Telnyx end-to-end; no new vendor. First WebRTC in the codebase (recon confirmed none exists) |
| Fallback / preview | **SIM mode**: when `TELNYX_WEBRTC_CONNECTION_ID` is unset the softphone runs a clearly-labeled simulator (state machine only, no PSTN traffic) | Lets the whole workflow run in previews and before Telnyx credential-connection setup; badge in UI so it can never be mistaken for live |
| Call state source of truth | Browser SDK events → backend `PATCH /api/dialer/calls/{id}`; Telnyx webhooks are a v1.5 enrichment | Simplest correct loop; webhook enrichment additive later |
| Queue source | Rep's **own** leads (`canada_leads` / `us_leads`, `rep_id = me`) in callable stages + due callbacks first; optional claim-from-unassigned via conditional service-role UPDATE (`rep_id IS NULL` guard → atomic per-row) | RLS-consistent; avoids pool-locking complexity in v1 |
| Live admin updates | Supabase Realtime on the new dialer tables (publication added in the migration), bridged into react-query — same pattern as `canada_leads` | Already CSP-allowed (`wss://*.supabase.co`); no new backend WS (multi-worker guard makes backend WS fan-out a Redis project) |
| Storage plane | New `dialer_*` tables. **Do NOT extend `phone_call_logs`** (merchant-tenant scoped, inbound order agent) | Recon: naming-collision trap; dialer is rep/lead-scoped |
| Preview data plane | `DIALER_DEV_STORE=1` → sessions/calls/callbacks/DNC held in an in-process store (same interface as the Supabase store); **leads still come from the real DB via the caller's JWT**. Banner in UI when active | Migrations are hand-applied by doctrine — the preview must not require touching the live schema; no fabricated business data |
| Roles | Rep endpoints: `require_jwt` + `hierarchy.resolve_scope`. Admin endpoints: `hierarchy.require_org_admin` ("admin or better" = role `admin` or `ADMIN_EMAILS`) | Existing two-plane doctrine |

## 3. Data model — `supabase/migrations/20260812_autodialer.sql`

All tables RLS-enabled; rep access via email-join to `sales_reps` (same idiom as `canada_leads`); manager/admin read via `current_rep_role()`/`rep_path_for()`; service-role full access. Registered in `tests/compliance` SENSITIVE_TABLES. Realtime publication on `dialer_sessions` + `dialer_calls`.

- **`dialer_sessions`** — id, rep_id → sales_reps, market (`canada|us`), status (`active|paused|ended`), wrap_up_seconds (default 15), started_at, ended_at, dials/connects/talk_seconds counters.
- **`dialer_calls`** — id, session_id, rep_id, lead_id + lead_table (`canada_leads|us_leads`), phone_e164, direction (`outbound`), status (`queued|dialing|ringing|connected|ended|failed|blocked`), blocked_reason, telnyx_call_id, started_at/answered_at/ended_at, duration_seconds, talk_seconds, disposition (CHECK: `meeting_booked|interested|callback|left_voicemail|no_answer|busy|bad_number|not_interested|dnc|other`), notes, sim (bool — true when placed in SIM mode).
- **`dialer_callbacks`** — id, rep_id, lead_id, lead_table, call_id, phone_e164, due_at timestamptz, timezone, note, status (`pending|done|cancelled`).
- **`dialer_dnc`** — phone_e164 UNIQUE, market, reason, added_by_rep_id, created_at. (Internal DNC; `dnc` disposition writes here instantly.)

## 4. Backend — FastAPI

New files (each <500 lines):
- **`src/services/dialer_compliance.py`** — NANP area-code → IANA timezone map (all CA area codes + US), `calling_window_check(phone_e164, now)` → allowed/blocked-until (CRTC vs TCPA by country), E.164 normalization re-exported from `phone_safety`.
- **`src/services/dialer_store.py`** — store interface + two impls: `SupabaseDialerStore` (PostgREST, service role for writes) and `MemoryDialerStore` (preview; `DIALER_DEV_STORE=1`).
- **`src/api/routes/dialer.py`** — rep surface, `prefix="/api/dialer"`:
  - `GET /queue?market=` — due callbacks first, then own callable leads (every stage except `closed_won`/`closed_lost`, DNC-excluded, 4h re-attempt cooldown), each item pre-annotated `callable_now` + local time.
  - `POST /sessions` / `PATCH /sessions/{id}` (pause/resume/end) / `GET /sessions/current`
  - `POST /calls` — **the compliance gate**: DNC check + calling-window check → 200 (call row created) or 409 `{blocked_reason}`.
  - `PATCH /calls/{id}` — status transitions + timings from the browser SDK.
  - `POST /calls/{id}/disposition` — disposition + note; side effects: `dnc` → insert `dialer_dnc`; `callback` → insert `dialer_callbacks`; optional lead-stage advance (service-role, guarded to the caller's own lead).
  - `POST /webrtc-token` — mints Telnyx credential token, or `{mode:"sim"}` when unconfigured.
  - `GET /callbacks` / `PATCH /callbacks/{id}`
- **`src/api/routes/dialer_admin.py`** — `prefix="/api/dialer/admin"`, router-level `Depends(require_org_admin)`:
  - `GET /live` — active sessions joined with reps + current call (the live board's initial snapshot; realtime keeps it fresh).
  - `GET /calls` — history w/ filters (rep, disposition, date range) + CSV-friendly shape.
  - `GET /analytics?days=` — dials/connects/connect-rate/talk-time/dispositions per rep + totals.
  - `GET|POST|DELETE /dnc` — DNC manager.
  - `GET /callbacks` — all pending callbacks (team-wide).
  - `PATCH /calls/{id}` — admin re-disposition/annotate (processing calls after the fact).
- Register both routers in `src/api/app.py`.
- Tests: `tests/api/test_dialer_compliance.py` — window math (CRTC weekday/weekend edges, TCPA, unknown area code ⇒ blocked-safe), DNC gate, disposition side effects against the memory store.

Env (names only): `TELNYX_API_KEY` (exists), `TELNYX_WEBRTC_CONNECTION_ID` (new, optional — SIM mode without it), `TELNYX_DIALER_CALLER_ID` (falls back to `TELNYX_PHONE_NUMBER_CA`), `DIALER_DEV_STORE`.

## 5. Frontend — React/Vite

Shared (market-agnostic) pieces:
- **`lib/dialer-api.ts`** — typed client modeled on `team-api.ts` (`req<T>` with `err.status`), all endpoint fns + TS types.
- **`hooks/useDialerSession.ts`** — the power-dial state machine: `idle → queue-ready → dialing → ringing → connected → wrap-up(countdown) → auto-advance`, pause/resume, hard-stop, per-session stats. Consumes softphone events + drives API writes.
- **`lib/dialer-softphone.ts`** — softphone facade: `TelnyxSoftphone` (dynamic-imports `@telnyx/webrtc`, logs in with backend-minted token, `newCall({destinationNumber, callerNumber})`, maps SDK states) and `SimSoftphone` (timer-driven state walk, labeled). Both emit the same event union.
- **`components/dialer/`** — `SessionHUD` (status pill, timers, stats, wrap-up countdown ring, pause/stop), `QueuePanel` (upcoming leads + due callbacks, callable-now indicators), `ContactCard` (lead details, history, notes textarea), `DispositionGrid` (one-click grid incl. callback scheduling popover + DNC confirm), `CallControls` (mute/hangup/keypad), `AdminLiveBoard`, `AdminCallsTable`, `AdminAnalyticsTiles`, `AdminDncPanel`. Canada tokens (`pm-accent`, `pm-canada-*`), lucide icons, `PortalPage` wrapper.
- **`lib/canada-admins.ts`** — `isCanadaAdmin(email)` single source (mirrors `us-admins.ts`); used by new pages (existing triplicated arrays left untouched this PR).

Pages + wiring:
- `pages/canada/portal/CanadaPortalAutoDialerPage.tsx` — rep dialer.
- `pages/canada/portal/CanadaPortalCallConsolePage.tsx` — admin console (gated `repTier==='admin' || isCanadaAdmin`; renders AccessDenied otherwise). Live board via Supabase Realtime on `dialer_sessions`/`dialer_calls` bridged into react-query (falls back to 5s polling when realtime unavailable, e.g. dev store).
- `pages/us/portal/USPortalAutoDialerPage.tsx` — thin market="us" wrapper over the same components (additive; zero Canada files changed for it).
- `App.tsx`: two lazy consts + `auto-dialer` / `call-console` routes in the `/canada/portal` block, `auto-dialer` in `/us/portal`.
- `CanadaSalesLayout.tsx`: `{ path: …/auto-dialer, icon: PhoneCall, label: 'Auto Dialer' }` in `salesNavBase`; `{ path: …/call-console, icon: Headphones, label: 'Call Console' }` as the **first real item under the existing empty `adminNavItems` heading** (already admin-gated at assembly).
- `SalesPortalMobileNav.tsx`: Auto Dialer in the More sheet (Call Console too, admin tier only). US layout nav gets Auto Dialer.
- `package.json`: add `@telnyx/webrtc`.
- **`docs/CANADA_PORTAL_TRUTH.md`**: new SR-portal truth rows (required by repo doctrine for any `pages/canada/` change).

## 6. Compliance posture (v1)

- Hard dial-time block: internal DNC + CRTC/TCPA windows in the **lead's** local time (area-code derived; unknown area code = blocked, fail-safe). UI shows why + when callable.
- `dnc` disposition writes the number to `dialer_dnc` instantly; queue excludes DNC before it's ever surfaced.
- No recording in v1 (consent + retention unresolved — deliberately not half-shipped). No predictive dialing ever without a separate compliance workstream (CRTC abandonment records).
- National DNCL subscription (CRTC) is an org-level action item for Aidan before any cold-list calling; the internal gate is necessary-not-sufficient and the plan says so out loud.

## 7. Build order (the one-shot checklist)

1. [x] Recon (frontend portal, backend telephony, competitor features)
2. [ ] Migration `20260812_autodialer.sql` + compliance-test registration
3. [ ] `dialer_compliance.py` + unit tests green
4. [ ] `dialer_store.py` (memory + supabase impls)
5. [ ] `dialer.py` + `dialer_admin.py` routers + `app.py` registration; backend boots
6. [ ] Frontend lib/hooks/softphone + components
7. [ ] Pages + routes + nav (Canada, US, admin) + CANADA_PORTAL_TRUTH.md update
8. [ ] `npm run build` (tsc) green; backend pytest green
9. [ ] Local run (uvicorn :8000 + vite :3000, `DIALER_DEV_STORE=1`, SIM softphone), visual screenshot check
10. [ ] cloudflared quick tunnel → preview URL to Aidan
11. [ ] Commit(s) on `feat/rep-autodialer`, push branch, open PR — **no merge, no push to main**

## 7b. Phone-lead pool + capture/recapture + booking (2026-08-12, added)

Doctrine: the dialer works a DEDICATED pool, never `canada_leads` (the live
pipeline). Cold prospects with raw numbers in `canada_leads` would pollute every
stage count and trip the RLS/regression tripwires — so a separate table + a single
deliberate promote is the only bridge.

- **`canada_phone_leads`** (migration `20260812_canada_phone_leads.sql`, APPLIED to
  live 08-12): the dialing pool. Carries enrichment — `pos_system` ("has Square/
  Clover/no POS"), `vertical`, `est_monthly_value`, `website` — surfaced on every
  call card and queue row. Lifecycle `status` (new→attempting→contacted→callback→
  booked→converted / not_interested / bad_number / dnc / dead), `attempts`,
  `last_disposition`, and `next_action_at` (the recapture clock).
- **Capture**: `POST /api/dialer/phone-leads` (one) + `/import` (bulk paste; de-dupes
  against the rep's pool, skips invalid). UI: "Add leads" drawer (add-one form +
  paste-a-list). This is how "the numbers are already there" — reps load a list once.
- **Recapture** (fully automatic): each disposition updates the pool row — no_answer
  → +4h, busy → +2h, voicemail/interested/other → +24h, callback → the callback time,
  dead/not-interested/bad-number/dnc → out. The queue (`GET /queue`) only returns rows
  whose `next_action_at` is due, ordered most-overdue first. Worked-but-unconverted
  leads resurface on their own.
- **Booking calendar** (`dialer_appointments`): "Meeting booked" opens a slot picker
  (quick-slots + datetime + duration). `POST /api/dialer/appointments` books it AND
  promotes in the same click. Calendar/agenda view in the dialer (Dialer|Calendar
  toggle) + admin Console "Calendar" tab; mark done/no-show/cancel.
- **One-click "Send to pipeline"** (`POST /phone-leads/{id}/promote`): the ONLY write
  into `canada_leads` — creates a pipeline row (stage `appointment_set`, phone,
  vertical, value from cents, `source: auto-dialer:<batch>`, POS in notes), links
  `converted_lead_id`, marks the pool row converted. On the contact card, and implicit
  in every booking. So the pipeline only ever receives qualified/booked leads.
- Dialer telemetry (sessions/calls) still runs in the `DIALER_DEV_STORE` for previews;
  the durable pool/appointments/promote always hit real Supabase.
- E2E-verified 08-12 through the UI: import → enriched queue → dial → enriched card →
  Meeting booked → slot picker → book → appointment on calendar + phone lead booked +
  clean promoted `canada_leads` row; all test data deleted.

## 8. Post-approval runbook (not done in this PR)

- Apply `20260812_autodialer.sql` to live Supabase (human step, with snapshot).
- Create a Telnyx **Credential Connection** for WebRTC; set `TELNYX_WEBRTC_CONNECTION_ID` + `TELNYX_DIALER_CALLER_ID` in Railway env.
- Register + subscribe to Canada National DNCL before cold-list campaigns.
- v1.5 queue: voicemail drop, recording (consent flow first), local presence pools, listen/whisper/barge, inbound ring group.
