# Pre-Launch QA — CANADA Operations (2026-06-28)

Canada-only sweep (4 agents: merchant journey, rep portal, money/CAD, phone+camera+compliance). Scope = `/canada/*` routes, Canadian merchants/reps, CAD/GST-HST, PIPEDA/Law 25/CASL. **LIVE** = reproduced against prod. Deduped.

**Counts:** ~13 P0 · ~13 P1 · ~8 P2/P3.
**Bottom line:** the launch-blocking cluster is **currency** — Canadian merchants are billed and charged in **USD across every path** (subscription, phone orders, Square invoices), a ~37% overcharge, and CA Square merchants hit a **silent ordering blackout**. Plus **6 ZERO-POS-doctrine violations** in the rep portal and **3 compliance gaps** (recording disclosure, CASL, RLS leak).

---

## 🔴 P0 — Blocks CA launch

### Currency — CA merchants charged in USD everywhere (CONFIRMED at code level)
Root cause: `order_normalizer.normalize_order` never stamps a `currency` key, and every billing/payment path defaults to `"USD"`. Only the Stripe *phone-order* path (`payment_links.py:142`) and `process_renewals` read CAD correctly.
1. **Phone-order Square/Meridian pay links default USD.** `payment_links.py:273,404` (`order.get("currency","USD")`) + `order_normalizer.py` (no currency emitted). CA customer pays a USD-denominated link (~37% FX overcharge).
2. **Square POS order creation sends `currency:"USD"` → Square CA account returns 400 (currency mismatch) → order never reaches the kitchen.** `pos_connector.py:142`. **Silent ordering blackout for every CA Square merchant.**
3. **Stripe subscription checkout hardcodes `"usd"`** for ad-hoc price + setup-fee line items. `stripe_checkout.py:135,151`. CA merchant's subscription billed USD.
4. **Square subscription invoices default USD** — `InvoiceRequest` has no currency field; `billing_service.create_invoice(currency="USD")`. The CA onboarding wizard sends CAD amounts with no currency. `billing.py` model, `billing_service.py:252`, `CanadaCustomerOnboardingWizard.tsx:438`.
5. **`CanadaPortalCreateCustomerPage` sends `country:'CA'` (ignored) instead of `currency:'CAD'`** → checkout link in USD. `CanadaPortalCreateCustomerPage.tsx:599` (note: `CanadaPortalLeadDetailPage.tsx:382` does it right — this page is the outlier).
> **Fix (one cluster):** add a `currency` field threaded from the CA portal/merchant config; default CAD for CA. Stamp `currency:"cad"` in `normalize_order`; change the `"USD"` fallbacks; add `currency` to `InvoiceRequest`/`CheckoutSessionRequest`; pass `currency:'CAD'` from the Create-Customer page. (Quick guard: flip `UNIFIED_PAYMENTS_ENABLED=1` — the Stripe phone-order path is already CAD-correct.)

### ZERO-POS doctrine violations (rep portal) — 6, all rep-facing
6. **Accounts page exposes full POS connect/sync UI to reps** — provider badge, live `/api/pos/connections` fetch, "POS System" card, "Last POS sync", **"Sync POS Data" button**. `CanadaPortalAccountsPage.tsx:51-61,118-146,332,413,519-538`. (Worst — it's POS *control*, not just display.)
7. **Dashboard kanban has a "POS Connected" column** (+ on deal cards + activity feed). `CanadaPortalDashboardPage.tsx:63`, `canada-sales-demo-data.ts:297`.
8. **Lead-detail Project Files seeded with `pos_setup_guide.pdf` on EVERY lead.** `CanadaPortalLeadDetailPage.tsx:63,696`.
9. **Leads list shows "POS Connected" badge** on cards. `CanadaPortalLeadsPage.tsx:39`.
10. **Dashboard welcome step 3: "Walk your customer through POS setup."** `CanadaPortalDashboardPage.tsx:162`.
11. **`/canada/portal/badge` renders the US badge component** (USD/US copy for CA reps). `App.tsx:505` (no `CanadaPortalBadgePage` exists).
> Plus minor POS copy on the lead "Create Customer Account" card (`CanadaPortalLeadDetailPage.tsx:1462`).

### Compliance (CA legal exposure)
12. **No AI/call-recording disclosure in the CA phone greeting** — calls are recorded+transcribed every turn; greeting/system prompt has no PIPEDA/Law 25 disclosure. `phone.py:168-181`, `bot.py:161-187`. Fix: backend-enforced disclosure prefix for CA merchants ("…I'm an automated assistant, this call may be recorded…").
13. **`canada_leads` RLS is open — any authenticated rep can read any rep's leads.** Policy `USING(auth.uid() IS NOT NULL)`; `getById()` is unfiltered by `rep_id`. `20260511_fix_canada_leads_rls.sql:7`, `canada-leads-service.ts:186`. (`fix/leads-rep-isolation` authored, not applied.)

---

## 🟠 P1 — Breaks a core CA flow

14. **Transfer number not E.164 → human-transfer calls dropped.** Wizard accepts `416-555-1234`; Telnyx `<Dial>` rejects bare numbers. `canada/merchant/PhoneSetupWizard.tsx:84`, `phone.py:986`. Fix: require/normalize `+1XXXXXXXXXX`.
15. **CA no-POS merchants have NO payment path** — `voice_sms_handoff.py` is DRAFT/unintegrated; `submit_order` returns fake success and never sends a pay link. (Most early CA merchants have no POS.) `voice_sms_handoff.py:16`, `phone.py:997-1056`. Fix: wire `send_payment_link_to_caller` at the documented `PAYMENT_LINK_HANDOFF` site.
16. **Password reset auto-logs-out the recovery session** — `onAuthStateChange` treats `PASSWORD_RECOVERY` as `SIGNED_IN`; `/canada/login` then logs the user out before they can set a password → self-service reset impossible. `CanadaLoginPage.tsx:38`, `auth.tsx:186`.
17. **`country:'US'` + `taxRate:0.08` hardcoded for CA merchants** in the Phone pillar → US tax on order totals/receipts. `PhoneOrdersPage.tsx:620-621`. Fix: use the `cad` flag (GST/HST, country `'CA'`).
18. **French after-hours message spoken by English `Polly.Joanna`** → garbled audio for Quebec callers. `phone.py:846` (and other `<Say>` sites). Fix: `Polly.Léa`/`Chantal` (fr-CA) when `language=fr`.
19. **Camera "Analytics" tab serves the public SEO marketing page** (USD $490 pricing, FAQ, CTAs) inside the authenticated CA portal. `merchantPillars.tsx:35`. Fix: import the app analytics page.
20. **Stripe Connect status fetch missing auth → CA merchant always sees "Not Connected"** (Get-Paid flow unreachable). `PhoneOrdersPage.tsx:400`.
21. **"Top Actions" + "Taxes & Expenses" pillars show in CA portal despite spec** — `MerchantLayout` never reads `canadaModuleFlags`; `tax` has no flag at all. Sidebar + **mobile bottom nav overflows** (8 items on 375px, Camera/Settings clipped). `MerchantLayout.tsx:9,116`.
22. **Rep commission rate % still shown in rep Settings** (residue of the commission-removal pass; reps can derive their pay). `CanadaPortalSettingsPage.tsx:109`.
23. **Renewal / payment-recovery invoices billed USD for CA subs** — `update_payment_method` + `notify_payment_failed` ignore the sub's stored `currency:"CAD"`. `billing.py:269-382`.
24. **Notification-prefs GET/PUT send no auth headers** (CA-16 residue; BOLA once backend lands). `SettingsPage.tsx:58,74`.
25. **Commercial emails to CA reps bypass CASL** — `send_weekly_report`/`send_update_brief` call `_client.send()` directly; `casl_guard.casl_wrapped_send` exists but is never called. `email/send.py:121,403`. (CASL CEM exposure.)

---

## 🟡 P2 / 🔵 P3 — Polish / correctness
- **SLA documents generated with `posSystem:'TBD'`** emailed to customers. `CanadaPortalLeadDetailPage.tsx:492,538`.
- **Per-order fee currency-ambiguous** — `MERIDIAN_SERVICE_FEE_CENTS` charged as CAD cents; if sized for USD, ~28% under-collection. `payment_links.py:38`.
- **No GST/HST on Meridian's B2B SaaS invoices** (CRA remittance risk unless prices are documented tax-inclusive). `billing_service.py:253`.
- **Receipt/failure emails show bare `$343.00`** (no CAD designator). `billing.py:364,607`.
- **`CanadaInvoicePage` is a non-functional stub** (no amount/tax/pay button). `canada/CanadaInvoicePage.tsx`.
- **Get-Paid fee labels use bare `$` not `CA$`.** `PhoneOrdersPage.tsx:489,513,581`.
- **Bell Canada forwarding code wrong** — wizard says `*72`, Bell uses `*21`. `PhoneSetupWizard.tsx:76`.
- **No in-app PIPEDA camera-signage notice** in the setup/empty-state. `LiveCamerasPage.tsx:139`.
- **SMS Canadian-number guard blocks US testers** during launch QA. `sms_order.py:385`.
- **Landing "Get Started Free / no credit card" contradicts "Plans from CA$350/mo".** `CanadaLandingPage.tsx:178,313`.
- **Landing claims Moneris & Alice POS support** — not in the picker (only Square/Clover). `CanadaLandingPage.tsx:364`.
- **`/canada/setup` "Account Setup" badge styled red** (looks like an error on first login). `CanadaSetupPage.tsx:78`.
- **Realtime lead subscription not filtered by `rep_id`** (noise + cost). `canada-leads-service.ts:289`.
- **Compliance landing card 3 duplicates cards 1–2.** `CanadaLandingPage.tsx:344`.

---

## ⚙️ Owner: Aidan / config (Railway)
- Set `MERIDIAN_SERVICE_FEE_CENTS` as a **CAD** value (the ~$1.50 decision; document the currency).
- `UNIFIED_PAYMENTS_ENABLED=1` (the Stripe phone-order path is CAD-correct — flipping it sidesteps P0 #1).
- Confirm `TENANCY_ENFORCEMENT_DISABLED` unset/false.
- Apply `fix/leads-rep-isolation` migration (P0 #13).

## Recommended fix order for Wednesday (CA)
1. **Currency cluster (P0 #1-5)** — one PR: `currency` field threaded CA→CAD across normalize_order/payment_links/pos_connector/stripe_checkout/billing. Without it, every CA charge is wrong and CA Square ordering is dead.
2. **ZERO-POS rep-portal sweep (P0 #6-11)** — strip POS UI/copy/seed-file from the rep portal; fix the badge route.
3. **Compliance (P0 #12-13)** — CA greeting recording disclosure + apply leads RLS isolation.
4. **Phone/locale P1 (#14-19)** — E.164 transfer, no-POS pay link, password-reset, CA tax/country, fr TTS, camera tab.
5. P2/P3 + CASL wiring post/around launch.
