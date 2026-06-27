# Meridian Customer Phone Wizard — How It Works (End to End)

> Audience: a non-engineer founder. This explains exactly what happens when a
> merchant sets up their AI phone agent, what the customer hears when they call,
> where the data lives, and how it gets billed. File/line references are included
> so an engineer can follow along too.

---

## 1. The one-paragraph version

A merchant opens the **Phone** pillar in their Meridian dashboard. A 5-step
wizard appears. The moment it loads, Meridian **automatically buys them a
dedicated phone number** (Telnyx or Twilio) and wires that number so incoming
calls hit our servers. The merchant picks a voice, a greeting, confirms their
menu, chooses where orders should go, and clicks **Activate**. From then on,
when a real customer dials that number, our backend answers, an AI talks to the
caller, takes their order, and sends it to the merchant's POS (or texts/emails
it). Every minute of conversation is metered against the merchant's credit
balance.

There are actually **two separate voice systems** in this codebase. The wizard
drives the **Telnyx/Twilio turn-based** system (`phone.py`). A newer
**Vapi** system (`vapi_webhook.py`) exists for the demo line and is billed
differently. **The wizard does not touch Vapi.** Section 5 makes this crystal
clear because it is the single most confusing thing here.

---

## 2. Flow diagram

```
                         ┌──────────────────────────────────────────────┐
                         │  MERCHANT (in the dashboard)                   │
                         └──────────────────────────────────────────────┘
                                            │
                   opens Phone pillar → SetupWizard.tsx mounts
                                            │
       ┌────────────────────────────────────┴───────────────────────────────┐
       │  ON MOUNT (automatic): POST /api/phone/provision-number              │
       │  → buys a Telnyx (or Twilio) number, wires its voice webhook to us   │
       └────────────────────────────────────┬───────────────────────────────┘
                                            │
   Step 0 Setup → Step 1 Voice → Step 2 Menu → Step 3 Routing → Step 4 Activate
                                            │
                       Click "Activate Agent" → POST /api/phone/config
                                            │
                         row saved in  phone_agent_config  (Supabase)
                                            ▼
        ════════════════════  LATER, A REAL CUSTOMER CALLS  ════════════════════
                                            │
                 Telnyx/Twilio receives the call, POSTs to our backend
                                            ▼
                         ┌───────────────────────────────┐
                         │  POST /twilio/voice (phone.py) │
                         │  • look up merchant by number  │
                         │  • after-hours gate            │
                         │  • credit-balance gate         │
                         │  • greet the caller            │
                         └───────────────┬───────────────┘
                                         │  caller speaks
                                         ▼
                  ┌───────────────────────────────────────────┐
                  │  POST /twilio/gather  (one per turn)        │
                  │  speech-to-text → AI brain → text-to-speech │
                  │  DeepSeek → SambaNova → local Qwen fallback │
                  │  Polly voice reads the reply back           │
                  └───────────────┬───────────────────────────┘
                                  │  loops until the order is confirmed
                                  ▼
                  ┌───────────────────────────────────────────┐
                  │  submit_order tool fires → _dispatch_order │
                  │  • POS connected?  → push order to POS     │
                  │  • not connected?  → demo order id MRD-#### │
                  └───────────────┬───────────────────────────┘
                                  │  call ends
                                  ▼
                  ┌───────────────────────────────────────────┐
                  │  POST /twilio/status                        │
                  │  • finalize the call log                    │
                  │  • deduct credits for the minutes used      │
                  └───────────────────────────────────────────┘
```

---

## 3. The wizard, step by step (`frontend/src/components/phone/SetupWizard.tsx`)

The wizard is one React component, rendered from the Phone Orders page
(`frontend/src/pages/PhoneOrdersPage.tsx:645`) and also as the "Set up" view of
the Phone pillar (`frontend/src/config/merchantPillars.tsx:99`). It tracks a
`step` counter 0–4 and a local `cfg` object holding the merchant's choices
(`SetupWizard.tsx:34`, `:41`).

### Automatic number provisioning (happens before step 0 is even touched)

As soon as the wizard mounts, a `useEffect` checks whether the merchant already
has a number. If not, it calls `phoneService.provisionNumber(...)` with the
org id and `country: 'CA'`, then writes the returned number into the form
(`SetupWizard.tsx:73-85`). A `useRef` guard (`provisionStarted`) stops React's
double-mount from buying two numbers. While it runs, the Phone Number field
shows "Provisioning your number…" with a spinner; on failure it shows an inline
red error (`SetupWizard.tsx:131-146`). The field is **read-only** — the merchant
never types a number.

| Step | What the merchant sees | Inputs | What it calls |
|------|------------------------|--------|---------------|
| **0 — Setup** (`:120`) | Business name + the auto-assigned phone number | Business name (editable); phone number (read-only, auto-filled) | Nothing on this step; provisioning already fired on mount |
| **1 — Voice** (`:153`) | Greeting text box, a grid of voice options with play buttons, a live waveform preview, and order-type toggles (pickup / delivery / dine-in) | Greeting, selected voice, order types | Plays local voice previews (`VoicePreview`); no backend save yet |
| **2 — Menu** (`:207`) | An editable list of menu items (name + price), seeded from POS sync or demo data, with add/remove | Add/edit/delete menu items | Edits an in-memory `menu` array only; nothing saved until Activate |
| **3 — Routing** (`:278`) | "Where should orders go?" — POS (Direct API or Webhook), SMS Alert, or Email | Picks one routing target | Sets `cfg.routing` locally only |
| **4 — Activate** (`:324`) | A summary table of every choice, a "Powered by Meridian AI" note, and a **Test Call** button | Final review | **Test Call** opens `TestCallModal`; **Activate** calls `phoneService.saveConfig(...)` |

### What "Activate Agent" actually saves (`SetupWizard.tsx:379-393`)

```
saveConfig({
  merchant_id, business_name, phone_number, greeting, voice,
  order_types, menu_items, active: true
})
```

**Important nuance for the founder:** the **routing choice from step 3 is NOT
sent** in this payload. Neither is a transfer number or business hours. So today
the routing screen is essentially cosmetic — the actual order destination is
decided at call time by whether a POS is connected (see section 4). This is
called out again in the recommendations.

### The "Test Call" button (`TestCallModal.tsx`)

This is **not** a real phone call. It uses the browser's microphone
(`SpeechRecognition`, `TestCallModal.tsx:22`) to capture the founder's voice,
sends the transcript to `POST /api/phone/test-chat` (`:82`), and reads the AI's
reply back with browser text-to-speech. It runs the **same AI brain** the live
phone agent uses, scoped to this merchant's own menu and greeting, so it is a
faithful preview without spending phone minutes.

---

## 4. The service layer (`frontend/src/lib/phone-service.ts`)

Every wizard/dashboard call to the backend goes through the `phoneService`
object. All calls attach a Supabase auth header (`getAuthHeaders()`), and the
base URL comes from `VITE_API_URL` (`phone-service.ts:7`).

| Method | HTTP call | Used by | Purpose |
|--------|-----------|---------|---------|
| `provisionNumber` (`:105`) | `POST /api/phone/provision-number` | Wizard on mount | Buy + wire a dedicated number |
| `saveConfig` (`:51`) | `POST /api/phone/config` | Wizard Activate, Settings | Create/update the config row |
| `getConfig` (`:42`) | `GET /api/phone/config/{id}` | Page load | Read current config (returns `{exists:false}` if none) |
| `getCalls` (`:60`) | `GET /api/phone/calls/{id}` | Dashboard | Call history (mapped to UI rows by `mapCallRow`) |
| `getStats` (`:70`) | `GET /api/phone/stats/{id}` | Dashboard | Aggregated totals (calls, conversion, revenue) |
| `testChat` (`:79`) | `POST /api/phone/test-chat` | Test Call modal | Run the agent brain in-app |
| `getMenuStatus` (`:96`) | `GET /api/phone/menu/status/{id}` | Settings | Menu-build progress (idle/building/ready/error) |
| `scanMenuPhoto` (`:126`) | `POST /api/phone/menu/scan-photo/{id}` | Settings | Digitize a photo of a paper menu (vision model) |

Note: the wizard itself only uses `provisionNumber` and `saveConfig`. The menu
sync/scan/status calls are driven from the Settings tab, not the 5-step wizard.

---

## 5. The backend dashboard routes (`src/api/routes/phone_dashboard.py`)

All routes here are prefixed `/api/phone` and protected by
`require_service_auth` (`phone_dashboard.py:21`, applied as a dependency on
every endpoint). Merchant ids must be UUIDs (`_validate_merchant_id`, `:54`).

### `POST /provision-number` (`:714`)

The heart of "auto-provision a number."

- Picks a provider from the `PHONE_PROVIDER` env var (default `twilio`; Telnyx
  is preferred in practice — `:584`).
- **Idempotent**: if the merchant already has a `phone_number`, it returns that
  unchanged and never double-buys (`:735-737`).
- Searches for an available voice+SMS number in the requested country
  (`_telnyx_search` `:659` / `_twilio_search` `:610`).
- Buys it and **wires the webhooks**:
  - Twilio (`_twilio_purchase` `:628`): sets `VoiceUrl → /twilio/voice` and
    `StatusCallback → /twilio/status` on the purchased number.
  - Telnyx (`_telnyx_purchase` `:683`): attaches the number to
    `TELNYX_VOICE_CONNECTION_ID` (the TeXML app whose voice webhook already
    points at our backend) plus the messaging profile.
- Saves the number onto `phone_agent_config` and returns
  `{phone_number, provisioned, already_existed}`. Provider errors (no funds,
  regulatory bundle missing) are surfaced verbatim as a 502 so the wizard's
  inline error is meaningful (`:646-652`, `:698-706`).

### `GET /config/{merchant_id}` (`:59`) and `POST /config` (`:79`)

`GET` returns the config row (with the POS access token stripped out, `:75`) or
`{exists:false}`. `POST` upserts: it strips out `None` fields, stamps
`updated_at`, then updates if a row exists or inserts otherwise. The POS access
token is never returned to the browser.

### `POST /menu/sync/{merchant_id}` (`:266`) and `GET /menu/status` (`:273`)

`menu/sync` pulls the merchant's catalog **read-only** from their connected POS
and stores it as `menu_items` (`_sync_menu_from_pos_impl` `:161`). Credentials
resolve in order: manual token on the config row first, then the OAuth
connection in `pos_connections` (decrypted, `:112`). The same path auto-fires
when a POS is first connected (`auto_build_menu_on_connect` `:249`). `menu/status`
reports progress (`building`/`ready`/`error`/`idle`). **Known ceiling**
(documented at `:142-156`): the "building" flag is per-worker in memory, so with
multiple API workers a status poll can miss an in-flight build — cosmetic only,
the menu still builds.

### `POST /menu/scan-photo/{merchant_id}` (`:322`)

Upload a photo of a paper menu → a vision model extracts items → merged onto the
existing menu (or replaced with `?replace=true`). 12 MB cap; the image is never
stored.

### `POST /test-chat` (`:549`)

Runs the **real production brain** (`_ask_ai` imported from `phone.py`, `:557`)
against a per-merchant prompt built from their own menu/greeting
(`_build_test_prompt` `:513`). Returns `{reply, ended, order}`. This is what
powers the wizard's Test Call.

### `GET /calls`, `/orders`, `/stats` (`:402`, `:424`, `:446`)

Read endpoints for the dashboard — call logs, phone orders, and aggregated
stats (total calls, conversion rate, revenue, average duration) over N days.

---

## 6. What happens when a customer calls (`src/api/routes/phone.py`)

This is the live, turn-based agent. It is prefixed `/twilio` (`:36`) and is what
the provisioned numbers point at.

### `POST /twilio/voice` — the call connects (`:790`)

1. **Identify the merchant.** Looks up `phone_agent_config` by the dialed number
   (`To` field) via `_fetch_merchant_config` (`:557`). If nothing matches it
   falls back to the demo merchant (`:825-827`). (Outbound test calls pass
   `?merchant_id=` to target a specific merchant — `:814`.)
2. **Start a call log** in `phone_call_logs` (`:829`).
3. **After-hours gate** (`:836-846`): if the merchant set both business hours and
   a timezone and it is currently closed, it plays their after-hours message and
   hangs up. Unconfigured merchants are never gated.
4. **Credit gate** (`:850-858`): if the merchant can't cover even one minute
   (`has_balance`), it plays a "this account is temporarily paused" message and
   hangs up, logging status `credits_paused`. The demo merchant bypasses this.
5. **Streaming vs turn-based** (`:869-878`): if `MEDIA_STREAMS_ENABLED` and the
   merchant is opted in (and not French — the streaming ASR is English-only), it
   hands the call to the Pipecat WebSocket. Otherwise (the default for nearly
   everyone) it runs the turn-based path below.
6. **Build the session** (`:893-917`): stores the system prompt (built from the
   merchant's menu via `_build_merchant_prompt` `:634`), speech hints from the
   menu, the transfer number, POS credentials, and capture mode. Then it greets
   the caller (`:918-922`).

### `POST /twilio/gather` — one turn of conversation (`:925`)

Called once per caller utterance:

1. **Get the caller's words.** Reads `SpeechResult` if the real-time recognizer
   returned text; otherwise downloads the recording and transcribes it via
   Telnyx STT (`_transcribe_recording` `:295`). If results keep coming back
   empty it self-heals from `gather` to `record` capture (`:949-968`).
2. **Ask the AI** (`_ask_ai` `:524`): tries **DeepSeek** first, then
   **SambaNova**, then **local Qwen** as a last-resort fallback (`:527-537`).
   The reply is spoken back with the **Amazon Polly "Joanna"** voice in the
   TwiML (`:236`, `:273`).
3. **Handle tool calls** (`:980`):
   - `transfer_call` → dial the merchant's human transfer number, if set (`:981`).
   - `end_call` → say goodbye and hang up, log `no_order` (`:991`).
   - `submit_order` → dispatch the order, then confirm with an order number
     (`:997`).

### Submitting the order (`_dispatch_order` `:1130`)

- Resolves the merchant's POS at order time (`_resolve_pos_for_session` `:1045`):
  manual token on the config wins, else the decrypted OAuth connection.
- **If a POS is connected** → `create_pos_order(...)` pushes the real order
  (`:1151`).
- **If no POS** → returns a demo order id of the form **`MRD-####`** (a number
  derived from the call id, `:1136`). This same `MRD-####` fallback is used if
  the POS push throws (`:1156`), so the caller always hears a confirmation
  number even when nothing reached a POS. For a founder: an `MRD-` number means
  "no POS received this — it was handled as a demo/fallback."

### `POST /twilio/status` — the call ends (`:1163`)

On `completed` (and similar terminal states) it finalizes the call log and, for
real (non-demo) completed calls, **deducts credits** for the minutes used
(`_charge_for_call` `:729`).

---

## 7. The Vapi line is a DIFFERENT system (read this twice)

There are two parallel voice stacks. They look similar but do not share code,
numbers, or billing:

| | **Wizard path** (this doc) | **Vapi demo path** |
|---|---|---|
| Code | `src/api/routes/phone.py` | `src/api/routes/vapi_webhook.py` |
| Numbers | Telnyx/Twilio bought by the wizard | A single Vapi number config |
| Webhook | `/twilio/voice`, `/twilio/gather`, `/twilio/status` | `/api/vapi/webhook` |
| Brain | DeepSeek → SambaNova → Qwen, Polly TTS | Vapi-hosted models |
| Billing | **Credits** (`src/credits/`, 50 credits/min) | **Voice ledger** (cents, `voice_ledger`) |
| Driven by the wizard? | **YES** | **NO** |

When a merchant goes through the 5-step wizard, they get a **Telnyx/Twilio**
number that rings `phone.py`. The Vapi webhook (`vapi_webhook.py`) is a separate
production experiment (the "+1 380… demo line" in the team's notes) that resolves
merchants from the dialed number on its own and bills through `voice_ledger`
(credit = Stripe service-fee revenue, debit = Vapi call cost — see
`migrations/029_voice_ledger.sql` and `src/services/voice_ledger.py`). **No part
of the wizard provisions, configures, or bills through Vapi.** If you change the
wizard and expect the demo line to change, it won't, and vice-versa.

---

## 8. Data model — what's stored per merchant

From `supabase/migrations/20260507_phone_agent.sql` (+ later migrations 024 streaming,
027 timezone):

**`phone_agent_config`** — one row per merchant (`merchant_id` unique). The
wizard's settings live here:

- `business_name`, `phone_number`, `greeting`, `voice`, `language`
- `active` (the Activate toggle), `menu_items` (JSON), `order_types` (JSON)
- `pos_system`, `pos_access_token` (encrypted/stripped on read), `pos_location_id`
- `business_hours` (JSON), `business_timezone` (migration 027),
  `after_hours_message`, `transfer_number`, `max_concurrent_calls`
- `streaming_enabled` (migration 024), `special_instructions_enabled`

**`phone_call_logs`** — one row per call: `call_sid`, `caller_phone`, `status`
(`in_progress` / `order_placed` / `no_order` / `after_hours` / `credits_paused`
/ `transferred`), `duration_seconds`, `order_data`, `pos_result`, `transcript`.

**`phone_orders`** — denormalized orders for the dashboard: items, totals,
order type, POS result, status.

**`voice_ledger`** (migration 029) — **Vapi path only**, not the wizard.

---

## 9. Money & credits — how a call is paid for

The wizard path bills through the **credits** system (`src/credits/`):

- **Rate** (`src/credits/costs.py:41`): `PHONE_CALL_PER_MIN = 50 credits/min`,
  underlying cost ~$0.015/min. A credit is ~$0.001 retail, so a minute is ~5¢.
- **Rounding** (`cost_for_phone_call` `costs.py:119`): rounded up to the next
  30 seconds, minimum 1 full minute. A 31-second call costs a full minute.
- **Free starter grant** (`costs.py:111`): `STARTER_GRANT = 1000` credits on
  signup (~20 minutes of calls), enough to demo and close a few orders before
  paying. **Low-balance nudge** at `200` credits (`costs.py:116`).
- **Pre-call gate** (`phone.py:850`): a call is refused with a spoken message if
  the merchant can't cover one minute. There is no concept of "included minutes
  then overage" — it's a straight prepaid credit balance.
- **Post-call charge** (`phone.py:729`, called from `/twilio/status`): minutes
  used are deducted after the call. If a long call runs the balance negative
  mid-conversation, it is allowed to finish and flagged for reconciliation
  (`:746-753`).

**Does the wizard check the balance before Activate?** **No.** The wizard never
reads or shows the credit balance. The only enforcement is the per-call gate in
`phone.py` — so a merchant can fully "activate" an agent that has zero credits
and only discover it when callers hear "this account is temporarily paused."
This is the #1 recommendation below.

---

## 10. Recommendations (ranked by value)

### 1. Credit-balance check before Activate, with a top-up link — **HIGH value, effort M**
- **Current:** the wizard never looks at the credit balance. A merchant can
  Activate with 0 credits; the first real caller hears "account paused"
  (`phone.py:850-858`). The balance API already exists
  (`GET /api/credits/balance/{merchant_id}`).
- **Proposed:** on the Activate step, fetch the balance. If it's below one call's
  worth (or below `LOW_BALANCE_THRESHOLD = 200`), show a warning with a top-up
  CTA before/after Activate. Don't block — warn clearly.
- **Files:** `frontend/src/components/phone/SetupWizard.tsx` (Activate step +
  a new `phoneService.getBalance`), `frontend/src/lib/phone-service.ts`.
- **Effort:** M (frontend only; the endpoint exists).

### 2. Persist the routing choice (and transfer number) on Activate — **HIGH value, effort S**
- **Current:** step 3 collects `cfg.routing`, but `saveConfig` never sends it
  (`SetupWizard.tsx:379-390`). Routing is decided at call time purely by whether
  a POS is connected. The transfer number and business hours are likewise never
  collected/saved by the wizard, even though the backend and live call path
  fully support them (`phone.py:836`, `:981`; `phone_dashboard.py` config fields).
- **Proposed:** include the routing intent (and, ideally, a transfer number
  field) in the Activate payload so the merchant's explicit choice is honored and
  the summary screen isn't misleading. This is mostly wiring existing fields.
- **Files:** `frontend/src/components/phone/SetupWizard.tsx`,
  `frontend/src/lib/phone-service.ts` (the `PhoneConfig` type already has the
  fields). Backend already accepts them (`phone_dashboard.py:33-51`).
- **Effort:** S.

### 3. Business-hours + after-hours message step — **HIGH value, effort M**
- **Current:** the backend fully supports an after-hours gate
  (`phone.py:836-846`) keyed on `business_hours` + `business_timezone`, but the
  wizard never collects them, so it's dormant for wizard-onboarded merchants.
- **Proposed:** add a small "Hours" sub-step (or fold into Routing) to capture
  open hours, timezone, and a closed-message. Saves directly into the existing
  config columns.
- **Files:** `SetupWizard.tsx` (new inputs), `phone-service.ts` (already typed).
  No backend change needed.
- **Effort:** M (a weekly-hours UI is the bulk of the work).

### 4. Human-transfer fallback number in Routing, E.164-validated — **MEDIUM-HIGH value, effort S/M**
- **Current:** the live agent will warm-transfer to a human via the
  `transfer_call` tool **only if `transfer_number` is set** (`phone.py:974-989`),
  but the wizard never asks for one.
- **Proposed:** add a "Transfer to a human at…" field in step 3, validate it as
  E.164 (`+1…`), and save it. Big trust win — callers with complaints/questions
  reach a person instead of looping.
- **Files:** `SetupWizard.tsx` (input + validation), `phone-service.ts`.
- **Effort:** S/M.

### 5. Menu validation feedback — no silent skips, flag $0 items — **MEDIUM value, effort S**
- **Current:** the add-item handler silently ignores a row with no name or a
  non-numeric price (`SetupWizard.tsx:56-64`), and items can be saved with a $0
  price. The live agent then renders $0 items without a price
  (`phone.py:619-621`), so callers may hear an item with no price.
- **Proposed:** show inline validation ("name and price required"), and warn on
  $0 items at Activate ("3 items have no price — callers won't hear a price").
- **Files:** `SetupWizard.tsx` (step 2 + Activate summary).
- **Effort:** S.

### 6. "Refresh from POS" button + last-sync staleness indicator — **MEDIUM value, effort M**
- **Current:** menu sync runs on POS connect and via a Settings action, but the
  wizard's menu step doesn't show when the menu was last synced or offer a manual
  refresh. `GET /api/phone/menu/status` already returns `updated_at` and state.
- **Proposed:** in step 2, show "Last synced from {POS} · 3 days ago" with a
  Refresh button calling `POST /api/phone/menu/sync`. Surfaces staleness so the
  agent isn't quoting an old menu.
- **Files:** `SetupWizard.tsx` (step 2), `phone-service.ts` (`syncMenu` helper;
  `getMenuStatus` already exists). No backend change.
- **Effort:** M.

### 7. Provisioning timeout / error UX — **MEDIUM value, effort S**
- **Current:** on-mount provisioning shows a spinner and an inline error
  (`SetupWizard.tsx:73-85`, `:140-146`) but offers **no retry** and no timeout —
  if Telnyx/Twilio is slow or the regulatory bundle is missing, the merchant is
  stuck on "Provisioning…" with no way forward.
- **Proposed:** add a "Try again" button on error, a timeout that surfaces a
  friendly message, and optionally an area-code picker (the backend already
  accepts `area_code` — `phone_dashboard.py:601`).
- **Files:** `SetupWizard.tsx` (provisioning effect + step 0 UI).
- **Effort:** S.

### Additional findings worth flagging

- **Two billing systems coexist** (credits vs `voice_ledger`). It's worth a
  product decision on which is canonical for production so reporting isn't split.
  Today the wizard path = credits, Vapi demo = ledger (section 7).
- **Country is hardcoded to `'CA'`** in the wizard's provisioning call
  (`SetupWizard.tsx:80`). US/other merchants can't self-provision a local number
  from the wizard. Effort S to make it a field.
- **`active` is the only lifecycle control.** There's no "pause" affordance in
  the wizard; consider a deactivate path (the column and live checks already
  support it — `phone.py:1253`).
```
