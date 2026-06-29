# Real-Merchant Pilot Checklist — Canada Launch (run: 2026-06-30)

**Goal:** prove the full Canadian merchant lifecycle works on **current prod**, end-to-end, with one real merchant before opening onboarding (launch 2026-07-01). Scope: **phone + POS + payments + camera analytics (anonymous mode)**. Camera identity/biometric tier is gated off.

**Pilot merchant:** Aidan Nguyen connected before on an **older version** → this is a re-validation on current prod. Use his account or a fresh CA test merchant. Walk every step; a real pilot means a **real CAD card**.

**Legend:** ☐ todo · ☑ pass · ✗ fail (note + fix before launch)

---

## 0. Pre-flight — already shipped (re-confirm, don't re-do)
- ☑ **Anon-RLS exposure closed** — phone_*/schedule_*/canada_leads/us_leads + vision anon grant (verified live; snapshots saved).
- ☑ **Unauth endpoints locked** — credits/ledger 401, starter-grant 401, mark-onboarded 403 (verified live).
- ☑ **Cameras anonymous-only** — `CAMERA_IDENTITY_ENABLED` off; `opt_in_identity` → 403; wizard shows "Coming soon". (#200 deployed.)
- ☑ **Per-order fee set** — `MERIDIAN_SERVICE_FEE_CENTS=150` ($1.50 CAD), `PLATFORM_FEE_BPS=0`, `UNIFIED_PAYMENTS_ENABLED=1`. (Active after redeploy.)
- ☑ **Stripe live** — platform acct "Meridian Checkout" + live key + Connect webhook secret present. (Routing unproven until this pilot's first charge.)
- ☐ Backend `/health` 200, `meridian.tips` + `/canada/*` 200, merchant portal loads (re-check morning of).

## 1. Signup + login (Canada)
- ☐ Merchant logs in at `/canada/login`; lands on `/canada/merchant`; correct org context; no console errors.
- ☐ Password reset works end-to-end (recovery link does NOT auto-log-out — fixed #206).

## 2. Onboarding wizard (Canada)
- ☐ `MerchantOnboardingWizard` completes without error (org-id, business info, plan in **CAD**).
- ☐ OAuth return handled cleanly (success **and** the partial/error path).
- ☐ Merchant row + config persisted (via backend, not anon key).

## 3. POS connect (Clover primary; Square must work)
- ☐ **Clover** one-click OAuth → returns **connected**; status reflects.
- ☐ **Square** one-click OAuth (2nd test merchant) → connected.
- ☐ Menu sync pulls real items (count > 0, correct prices, no $0). "Refresh from POS" updates last-sync.
- ☐ POS token stored **encrypted**, not anon-readable.

## 4. Phone agent (Canada)
- ☐ CA DID provisioned/connected.
- ☐ **Real test call** → greeting plays the **AI/recording disclosure** (PIPEDA/Law 25), then takes a multi-item order with one modification.
- ☐ Agent reads back + confirms before submitting (no premature submit, no hallucinated items/prices).
- ☐ **Human transfer** works — enter a valid number, ask for a human, call actually transfers (E.164 fix).
- ☐ (If French merchant) after-hours / prompts use a **French voice**, not garbled English.
- ☐ Order lands in POS (Clover/Square) as an open order; call logged to `phone_call_logs`.
- ☐ **No-POS path:** if the merchant has no POS, the order produces a **real SMS pay link** (not a fake "order placed").

## 5. Get paid — the money path (verify hardest, in CAD)
- ☐ Customer receives the branded text-to-pay link via SMS.
- ☐ Pay link page + charge are in **CAD** (not USD).
- ☐ Paying runs a **Stripe Connect destination charge**: customer charged once; **$1.50 CAD fee → Meridian**; remainder → merchant's connected account. **(This is the first real proof of fee routing.)**
- ☐ Fee amount is exactly **$1.50 CAD**.
- ☐ Expired/already-paid link shows the **branded page**, not a dead Stripe bounce.
- ☐ Merchant payout appears (daily) — confirm in Stripe dashboard.
- ☐ Refund a small amount → reverses cleanly (fee + transfer reversed).

## 6. Tax / locale correctness
- ☐ Order totals/receipts show **GST/HST** (not US 8%); currency is **CA$** everywhere (no bare `$`).

## 7. Webhooks + dedupe
- ☐ POS/Stripe webhooks process once under retry (no duplicate orders/charges).

## 8. Rep portal sanity (ZERO-POS)
- ☐ Rep portal shows **no POS connect/sync controls** — only the read-only "Synced successfully ✓" status on active deals.
- ☐ A rep sees **only their own** leads (canada_leads RLS isolation — verify with a 2nd rep account if available).

## 9. Quote flow
- ☐ Public "Schedule a Quote" submits → lands in `quote_requests`; sales gets the lead.

---

## Abort / rollback
Stop + fix first if: a duplicate/incorrect **charge** or fee to the wrong party; a charge in the **wrong currency (USD)**; an order the customer didn't confirm; any data readable via the **anon key**; POS token in plaintext; camera identity reachable (`opt_in_identity` must 403); a rep seeing another rep's leads.

**Rollbacks:** payments → `UNIFIED_PAYMENTS_ENABLED=0`; cameras → `CAMERA_IDENTITY_ENABLED=0`; RLS → restore from snapshots in `/root/meridian-*-rls-snapshot-20260628.json`.

## Sign-off
- ☐ §1–9 pass on current prod.
- ☐ Money path verified with a **real CAD charge + payout + refund**.
- ☐ Go / No-go: __________  (owner, date)
