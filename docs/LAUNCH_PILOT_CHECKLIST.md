# Real-Merchant Pilot Checklist — Launch Readiness

**Goal:** prove the full merchant lifecycle works on the **current** production version with one real merchant, end-to-end, before opening onboarding. Camera analytics is **paused ("releasing soon")** for launch — scope is **phone + POS + payments**.

**Pilot merchant:** Aidan Nguyen has connected before, but on an **older version** — so this is a re-validation on current prod, not a first run. Use his account (or a fresh test merchant) and walk every step below.

**Status legend:** ☐ not started · ☑ pass · ✗ fail (note + fix before launch)

---

## 0. Pre-flight (must be true before the pilot)
- ☑ **#198 applied** — anon RLS exposure closed (verified: 0 anon/authenticated grants, 0 wide-open policies, backend 200). *Done 2026-06-28.*
- ☐ **Cameras paused** — `CAMERA_LIVE_ENABLED` unset/false in prod backend; `VITE_CAMERA_LIVE` unset in frontend build. Verify `POST /api/vision/cameras` returns **403 "releasing soon"** and the showcase page shows the banner. *(PR: chore/launch-prep-camera-pause — merge + deploy.)*
- ☐ **Final per-order fee set** in config (decision: $1.50 / $1.25 / $2.50) — not the placeholder.
- ☐ **`UNIFIED_PAYMENTS_ENABLED=1`** confirmed in prod (Railway).
- ☐ **Stripe** is in the intended mode (live keys for a real charge, or test keys for a dry run) — be deliberate; a real pilot means a real card.
- ☐ Backend `/health` 200, `meridian.tips` 200, merchant portal loads.

## 1. Signup + login
- ☐ Merchant signs up / logs in to the live portal.
- ☐ Lands on the dashboard; no console errors; correct org context.

## 2. Onboarding wizard
- ☐ Onboarding wizard completes without error (org-id, business info, plan).
- ☐ Setup fee (if any) behaves correctly; commission display is hidden from the rep view.
- ☐ Verify the merchant row + config persisted (`phone_agent_config` / org tables) — via backend, not anon key.

## 3. POS connect (Clover is primary; Square must also work)
- ☐ **Clover** one-click OAuth connect → returns to portal **connected** (status reflects).
- ☐ **Square** one-click OAuth connect on a second test merchant → connected.
- ☐ Menu sync pulls real items (count > 0, prices correct, no $0 items).
- ☐ "Refresh from POS" works; last-sync timestamp updates.
- ☐ POS access token stored **encrypted** (not plaintext) and not readable via anon key (re-confirm post-#198).

## 4. Phone agent
- ☐ Number provisioned / connected for the merchant.
- ☐ Place a **real test call** → agent greets, takes a multi-item order with one modification.
- ☐ Agent reads back + confirms before submitting (no premature submit, no hallucinated items/prices).
- ☐ Order lands in the merchant's POS (Clover/Square) as an open order.
- ☐ Call logged to `phone_call_logs` (transcript captured) — feeds the new Agent Quality panel.

## 5. Get paid (the money path — verify hardest)
- ☐ Customer receives the branded text-to-pay link (SMS).
- ☐ Paying the link runs a **Stripe Connect destination charge**: customer charged once, **fee routed to Meridian**, remainder to the merchant's connected account.
- ☐ Fee amount matches the configured per-order fee exactly.
- ☐ Expired/already-paid link shows the **branded page**, not a dead Stripe bounce.
- ☐ Merchant payout appears (daily payout schedule) — confirm in Stripe dashboard.
- ☐ Refund path works (issue a small refund, confirm it reverses cleanly).

## 6. Webhooks + dedupe
- ☐ POS/Stripe webhooks process once (no duplicate orders/charges under retry) — `webhook_events` dedupe holding.

## 7. Quote flow (public pricing replacement)
- ☐ Public "Schedule a Quote" form submits → lands in `quote_requests`; sales gets the lead.

---

## Abort / rollback criteria
Stop the launch and fix first if any of these occur during the pilot:
- A duplicate or incorrect **charge**, or fee routed to the wrong party.
- Order submitted that the customer didn't confirm, or with wrong items/total.
- Any merchant or customer data readable with the **public anon key** (re-test post-#198).
- POS token stored in plaintext or exposed.
- Camera live endpoints reachable (should be 403).

**Rollbacks:** payments → flip `UNIFIED_PAYMENTS_ENABLED=0`; cameras → already off; RLS → recreate prior policies + re-grant (snapshot at `/root/meridian-rls-snapshot-20260628.json`).

## Sign-off
- ☐ All §1–7 pass on current prod.
- ☐ Money path verified with a real charge + payout + refund.
- ☐ Go / No-go: __________  (owner, date)
