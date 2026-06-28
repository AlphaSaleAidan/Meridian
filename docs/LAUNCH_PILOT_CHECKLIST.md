# Real-Merchant Pilot Checklist — Launch Readiness

**Goal:** prove the full merchant lifecycle works on the **current** production version with one real merchant, end-to-end, before opening onboarding. Scope is **phone + POS + payments + camera analytics (anonymous mode)**. The camera **identity/biometric tier** (`opt_in_identity`, face embeddings, demographics) is **gated off** until the consent-signage flow ships.

**Pilot merchant:** Aidan Nguyen has connected before, but on an **older version** — so this is a re-validation on current prod, not a first run. Use his account (or a fresh test merchant) and walk every step below.

**Status legend:** ☐ not started · ☑ pass · ✗ fail (note + fix before launch)

---

## 0. Pre-flight (must be true before the pilot)
- ☑ **#198 applied** — anon RLS exposure closed (verified: 0 anon/authenticated grants, 0 wide-open policies, backend 200). *Done 2026-06-28.*
- ☐ **Cameras anonymous-only** — `CAMERA_IDENTITY_ENABLED` unset/false in prod backend; `VITE_CAMERA_IDENTITY` unset in frontend build. Verify a camera registers in `anonymous` mode (200) but `opt_in_identity` is rejected **403 "releasing soon"**, and the wizard's Opt-in Identity option shows "Coming soon" (unselectable). *(PR #200.)*
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
- Camera identity tier reachable without consent — `opt_in_identity` must 403, and no `visitor_hash`/`embedding_hash` or demographic rows should appear while `CAMERA_IDENTITY_ENABLED` is off.

**Rollbacks:** payments → flip `UNIFIED_PAYMENTS_ENABLED=0`; cameras → set `CAMERA_IDENTITY_ENABLED=0` (anonymous stays live) or disable the camera; RLS → recreate prior policies + re-grant (snapshot at `/root/meridian-rls-snapshot-20260628.json`).

## Sign-off
- ☐ All §1–7 pass on current prod.
- ☐ Money path verified with a real charge + payout + refund.
- ☐ Go / No-go: __________  (owner, date)
