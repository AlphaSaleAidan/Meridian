# Meridian DEFCON Readiness System

A single readiness scale across every subsystem, so any alert, report, or gut
feeling maps to the same five levels and the same expected response. DEFCON 1
is worst (all-hands, money/data/legal on fire); DEFCON 5 is normal operations.

## The scale

| DEFCON | Name | Meaning | Response time | Who |
|---|---|---|---|---|
| **1** | Catastrophic | Active funds loss, PII/card breach, mass mischarge, or a legal/regulatory clock started. | Minutes. Drop everything. | All hands + legal |
| **2** | Critical | A core revenue or availability system is down for **all** users (backend, phone fleet, all payments unconfirmed). | < 15 min | On-call, mitigate first |
| **3** | Major | One subsystem/rail degraded with real customer impact, but a fallback exists (one POS rail, SMS channel, one merchant line). | Same hour | On-call |
| **4** | Minor | Degradation with no direct customer impact **yet** — the warning shot (vendor credit low, elevated errors, a monitor finding, cert nearing expiry). | Same day | Owner |
| **5** | Normal | Baseline. Informational signals, routine ops, green monitors. | Routine | — |

Quick legend: **DEFCON 1** catastrophic · **DEFCON 2** critical · **DEFCON 3**
major · **DEFCON 4** minor · **DEFCON 5** normal.

**Mapping to the SEV ladder** (docs/runbooks/incidents/README.md): SEV-1 = DEFCON 1–2, SEV-2 = DEFCON 3–4, SEV-3 = DEFCON 5. DEFCON is now the primary scale; protocols keep their SEV tags for continuity.

## Two axes: severity vs. readiness

DEFCON here rates **event severity** (how bad, right now). Track it against
**detection readiness** — can we even see it? The most dangerous events are
high-severity + zero-detection: we'd only learn from an angry merchant, a
chargeback, or a regulator. Every catalog below flags these as **DETECTION
GAPS**, and closing them is the standing backlog this document generates.

## How to use this in a live event

1. **Rate it.** Pick the DEFCON from the tables below (or by the scale if it's
   novel). When unsure, round toward worse.
2. **Open the protocol.** DEFCON 1–2 events have a runbook in
   `docs/runbooks/incidents/`; the table's Mitigation column is the compressed
   version for everything else.
3. **Mitigate before diagnose.** Every row's mitigation restores service
   without root-causing (unset an env, redeploy previous, switch a rail).
4. **Log the timeline.** One line per action with times → postmortem +, for
   money events, the make-good ledger.
5. **Close by making the class impossible**, not by clearing the alert: a
   regression test, a monitor, or an invariant. DEFCON-1/2 postmortems go to
   memory within 24h.

## The pager — who gets woken up

Any detector that finds a DEFCON-1 or DEFCON-2 condition routes through
`src/services/defcon_alert.py::notify_defcon(level, event, detail, protocol)`,
which pages **every responder at once** — currently Aidan and Nathan
(`MERIDIAN_DEFCON_RESPONDERS`, default both) — with the level, what happened,
and the protocol to open. DEFCON-1 can also fire SMS (`MERIDIAN_DEFCON_SMS`).
Wired sources today: billing monitor + settlement check (DEFCON 1), edge
watchdog DOWN (DEFCON 2). It pages only at level ≤ 2 (noise never trains people
to ignore it), dedupes per event within a cooldown, and is fail-quiet — paging
never blocks the detector. New detectors page by calling `notify_defcon`.

## Standing defenses (already automated — the green baseline)

- Edge watchdog (portals, from Railway) — server-down detection.
- Billing invariant (charge time) — can't bill ≠ confirmed total.
- Settlement reconciliation (mark_order_paid) — underpayment alert.
- Billing monitor (6h, both Stripe accounts) — drift digest.
- CI parity ratchet — billed==confirmed across every rail, red before merge.
- Incident protocols + wiring test — alerts name their runbook; CI enforces it.

## The catalogs

Each subsystem's full failure space, DEFCON-rated, with detection status and
the fastest mitigation. Detection gaps are collected per section and rolled up
into the master gap backlog at the end.

---

## Payments & Billing

| Event | DEFCON | Detection | Immediate mitigation | Prevention |
|---|---|---|---|---|
| Undercharge — tax/modifier dropped from itemized link | 1 | Billing monitor + settlement check (NOW) | Flip merchant `payment_link_provider→stripe` (invariant collapses to exact total) | CI parity ratchet + charge-time invariant ✅ |
| Overcharge — customer billed above confirmed total | 1 | GAP: monitor only flags UNDER | Refund delta immediately; proactive notice | Extend invariant to flag `billed>expected+surcharge` — **GAP** |
| Double-charge — same order two sessions | 1 | GAP: no cross-session dup check | Refund the duplicate | Idempotency on `pos_order_id`→session — **GAP** |
| Double fee taken — voice_ledger TOCTOU | 2 | Ledger balance anomaly (manual) | Credit merchant the extra fee | Unique index `(source,ref)` mig 073 ✅ |
| Charge on WRONG Stripe account after split | 2 | GAP | Unset `STRIPE_PHONE_SECRET_KEY` → reverts to platform | Membership guard `_connect_destination` ✅ |
| Foreign Connect acct rejected (belongs to old platform) | 3 | Log `not usable under phone-order key` | Falls back to direct charge automatically | Re-onboard `STRIPE_PHONE_ONBOARDING=1` ✅ |
| Webhook down → payments unconfirmed fleet-wide | 2 | Stripe dashboard delivery failures | Fix backend/secret; Stripe auto-retries 3d | fail-closed 503 + un-record retry ✅ |
| Webhook signature drift after rotation | 2 | 400s in Stripe deliveries | Re-sync `STRIPE_*_WEBHOOK_SECRET` to dashboard `whsec_` | $0.75 verify after any secret change |
| Stripe account restricted / funds frozen | 1 | GAP: no account-status poll | Complete verification; route new charges to other acct | Poll `/v1/account` requirements — **GAP** |
| Payout failure / paused | 3 | GAP | Dashboard → resolve requirement | Payout monitor — **GAP** |
| Demo test-charge leaks to real customer | 2 | GAP | Verify `_DEMO_MERCHANT_IDS` gate; unset `MERIDIAN_DEMO_TEST_CHARGE_CENTS` | Gate is id-allowlisted ✅ (audit on merchant-id changes) |
| FX: CAD order on US acct settles USD ~1-2% loss | 4 | GAP | Add CAD bank/settlement balance | Documented; per-country acct — **GAP** |
| Card-testing / fraud burst | 2 | GAP: no velocity alert | Stripe Radar rules; block; disable promo | Radar + velocity alert — **GAP** |
| Chargeback / dispute storm | 3 | Stripe email per dispute | Submit evidence (order + transcript) | Auto-evidence from phone_orders — **GAP** |
| Refund doesn't reverse POS ticket | 3 | GAP | Manual POS void | Refund→POS-void hook — **GAP** |
| Stripe API outage | 2 | 5xx from Stripe | POS-native pay rail fallback; queue | Multi-rail already exists (Clover/Square) |
| Key rotation breaks live charges | 2 | Charge 401s spike | Restore prior key; redeploy | Rotate in low-traffic window + verify |
| Settlement fail-open (paid-but-inactive) | 2 | Fixed #415 (raises+retries) | n/a | idempotent uuid5 commission ✅ |
| Negative/zero-amount order dispatched | 3 | order_normalizer empty-guard | n/a | empty-order refuse ✅ |
| Application-fee wrong (too high/low) | 3 | GAP | Adjust `MERIDIAN_SERVICE_FEE_CENTS`; credit | Fee assertion in invariant — partial |

### Detection gaps (build these)
- **Overcharge** detection (invariant flags under only) — highest priority, legal exposure.
- **Cross-session double-charge** dedup on `pos_order_id`.
- **Stripe account-status poll** (restricted/payout-paused) on both accounts.
- **Fraud velocity** alert (Radar events / rapid small charges).
- **Refund→POS-void** reconciliation.

---

## Voice & Phone

| Event | DEFCON | Detection | Immediate mitigation | Prevention |
|---|---|---|---|---|
| Whole fleet dead — Vapi out of credits | 2 | GAP: balance not in REST | Add credits/auto-reload (dashboard, Aidan) | Balance-low poll — **GAP** |
| Whole fleet dead — Railway backend down | 2 | Edge watchdog (api path) | Railway rollback | watchdog ✅ |
| One line dead air — wrong Telnyx connection | 3 | GAP | PATCH DID→conn `2990417629031695653` | Onboard on Vapi conn from start |
| Vapi API outage | 2 | Call errors | Wait; Telnyx fallback number gate | provider-agnostic webhook |
| Telnyx carrier outage | 2 | Inbound stops | Vapi-native numbers as backup | multi-carrier — **GAP** |
| Deepgram STT down | 3 | Transcription empty | Vapi auto-fallback STT | — |
| ElevenLabs TTS down | 3 | Call has no voice | Fall back to Vapi-native voice | persona fail-open ✅ |
| TTS cache serves robotic take | 3 | GAP: `ttsCharacters==0` | `cachingEnabled:false` on voice | set fleet-wide ✅ (audit new voices) |
| Wrong order captured (ASR mishears qty/item) | 2 | GAP: no readback-confirm audit | Read-back in prompt; merchant confirms | Confirm-before-submit + real-call scoring — **GAP** |
| Agent hallucinates menu/price | 2 | GAP | restaurant_brief grounding guard | menu = single source of truth ✅; drift audit — **GAP** |
| Agent takes order for inactive merchant | 3 | active-gate in webhook | `active=false` → inactive assistant | gate ✅ |
| Loop — agent calls agent | 4 | loop-guard in webhook | caller==agent DID → message-taker | guard ✅ |
| submit_order webhook 401 storm | 2 | 401s in logs | Re-sync `VAPI_SERVER_SECRET` one number first | fail-closed auth ✅ |
| assistant-request returns error/empty | 2 | GAP | redeploy; probe | monitor assistant-request 5xx — **GAP** |
| Concurrency cap (10) hit in rush | 3 | GAP | Raise Vapi concurrency | autoscale plan — **GAP** |
| Call-cost spike / robocall abuse burns credit | 2 | GAP | Block number; maxDuration cap | anomalous-call-cost alert — **GAP** |
| Multi-worker session loss (in-memory) | 3 | startup guard refuses | Keep 1 worker until Redis | Redis store + guard ✅ |
| Greeting discloses wrong business | 3 | GAP | Fix customGreeting/persona | greeting test — partial |
| PII in transcripts / recording retention | 2 | GAP | Purge; set retention | redaction + TTL — **GAP** |
| Agent won't end call (maxDuration) | 4 | cost per call | endCallPhrases + maxDuration | set ✅ |
| DID ported/lost / reclaim race | 3 | GAP | Re-provision from pool | pool-first + atomic store ✅ |

### Detection gaps (build these)
- **Vapi credit-balance** low-water alert (dashboard-scrape or spend-rate proxy).
- **Wrong-order rate** — real-call scoring on readback mismatch / edits.
- **assistant-request 5xx** monitor + **anomalous call-cost** alert (abuse/robocall).
- **Transcript PII redaction + retention** TTL.

---

## Infrastructure & Deploy

| Event | DEFCON | Detection | Immediate mitigation | Prevention |
|---|---|---|---|---|
| Contabo box down (portals) | 2 | Edge watchdog | Control-panel reboot; nginx/pm2 restore on boot | watchdog ✅; box redundancy — **GAP** |
| Railway backend down / crashed deploy | 2 | watchdog(api) + /health | Railway rollback to prev SUCCESS | multi-worker guard ✅ |
| Bad deploy ships 0-route app (FastAPI) | 2 | 404 on every route | rollback | `<0.139` pin #446 ✅ |
| SSL cert expiry (certbot renew fail) | 2 | GAP: no expiry monitor | `certbot renew`; reload nginx | cert-expiry monitor — **GAP** |
| DNS misconfig/expiry/hijack (Namecheap) | 1 | GAP | Fix records; registrar lock | domain-expiry + DNS monitor — **GAP** |
| Supabase outage | 2 | 5xx per request | status page; wait; degrade | — |
| Supabase connection-pool exhaustion | 3 | asyncpg errors | restart; reduce pool | PgBouncer pooler — **GAP** |
| RLS/grant regression breaks queries (42501) | 2 | GAP at runtime | revert migration | RLS collector CI ✅ |
| Migration applied wrong / not applied | 2 | GAP (no ledger) | re-apply via mgmt API | migration lint ✅; apply-verify — partial |
| SW cache serves stale frontend | 3 | GAP | bump `CACHE_NAME`, redeploy dist | build-time cache name — **GAP** (documented) |
| Frontend dist clobbered by concurrent rsync | 3 | GAP | restore `/tmp/meridian-dist-backup-*.tgz` | edit source not dist ✅ (rule) |
| Env var missing/wrong after deploy | 2 | startup log / behavior | set var → auto-redeploy | — |
| Secret store `/root/.secrets` lost | 1 | GAP | restore from backup | offsite encrypted backup — **GAP** |
| Box CPU/RAM exhaustion (sidecar OOM) | 3 | GAP | kill offending proc (scoped) | move voice off box; alert — **GAP** |
| No alerting when box down (watchdog off) | 2 | meta-GAP | enable `MERIDIAN_EDGE_WATCH=1` | make watchdog default-on — **GAP** |
| Backup missing/corrupt | 1 | GAP | n/a (too late) | backup freshness monitor — partial |
| nginx 429 storm (ratelimit misfire) | 3 | 429s | adjust zone; reload | — |
| Log/disk full on box | 3 | GAP | rotate/clear logs | logrotate + disk alert — **GAP** |

### Detection gaps (build these)
- **Cert-expiry + domain-expiry** monitor (both are silent-until-fatal, DEFCON-1/2).
- **Edge watchdog default-ON** (it's the meta-detector; off = blind).
- **Offsite `/root/.secrets` encrypted backup** + **DB backup freshness** alert.
- **Disk/CPU/RAM** alert on Contabo.

---

## Data & Security

| Event | DEFCON | Detection | Immediate mitigation | Prevention |
|---|---|---|---|---|
| Active PII/card breach / exfiltration | 1 | GAP | Rotate all keys; revoke; isolate; **legal clock** | audit-log + anomaly egress — **GAP** |
| RLS regression exposes cross-tenant data | 1 | RLS collector (periodic) | REVOKE/DROP bad policy via mgmt API | collector in CI ✅; runtime — partial |
| Anon key reads sensitive table | 1 | RLS collector | REVOKE anon grant | explicit-deny mig 075 ✅ |
| Secret leaked (git/logs/bundle/chat) | 1 | GAP | Rotate immediately; invalidate | secret-scan CI + masking — partial |
| Supabase mgmt token compromised | 1 | GAP | Rotate token (full DB control!) | vault + rotation — **GAP** |
| API key compromised/abused | 2 | GAP | Rotate; restrict | per-key scoping — partial |
| Auth bypass / BOLA on rep-portal routes | 1 | CC6.6 route ratchet | add auth dep; redeploy | route-auth ratchet ✅ |
| Session hijack/fixation (in-memory, no revoke) | 2 | GAP | invalidate; restart (clears) | Redis + revocation — **GAP** |
| ENCRYPTION_KEY leaked (all captures decryptable) | 1 | GAP | rotate key; re-encrypt | key vault — **GAP** |
| ENCRYPTION_KEY lost (captures unreadable) | 3 | decrypt fails | captures refuse Redis (in-proc) | fail-safe ✅ |
| Unsigned webhook spoofing (pay/vapi/toast) | 2 | GAP per-endpoint | enforce sig; fail-closed | most fail-closed ✅; audit all |
| PostgREST/SQL injection | 2 | GAP | patch; WAF | InputValidator; param queries |
| Admin MFA absent | 3 | known | restrict allowlist | add MFA — **GAP** |
| `TENANCY_ENFORCEMENT_DISABLED` abused | 1 | GAP | ensure unset in prod | remove kill-switch — **GAP** |
| Ransomware / DB deletion | 1 | GAP | restore backup; IR | immutable backup — **GAP** |
| Dependency CVE / supply chain | 2 | GAP | patch/pin | dep-scan CI — **GAP** |
| `.env.local` tracked in git | 2 | fixed (untracked) | remove; rotate | gitignore ✅ |
| Data-subject/deletion request unhandled | 3 | GAP | manual fulfil | DSAR workflow — **GAP** |

### Detection gaps (build these)
- **Secret-scanning CI** (gitleaks) + **egress/anomaly** on DB reads.
- **Vault + rotation** for mgmt token + ENCRYPTION_KEY (both are DEFCON-1 single points).
- **Session revocation** (Redis) + **admin MFA** + **dependency CVE scan**.

### Breach legal clock
On any confirmed PII/card exposure (DEFCON 1): **start the clock immediately.**
- **Quebec Law 25**: report to the CAI + notify affected individuals *without
  delay* for any incident posing a risk of "serious injury"; keep an incident
  register. **PIPEDA**: report to the OPC + notify individuals on "real risk of
  significant harm," as soon as feasible. Do not wait for full root-cause to
  notify. Legal (Grellas Shah — see counsel-bot) looped from minute one.

---

## POS & Fulfillment

| Event | DEFCON | Detection | Immediate mitigation | Prevention |
|---|---|---|---|---|
| Paid but NO kitchen ticket (customer charged, no food) | 1 | kitchen monitor ✅ (paid-vs-pushed sweep, DEFCON-1 page) | manual re-push; refund if unmade | kitchen monitor ✅ |
| Kitchen ticket wrong items/qty/price | 1 | GAP | merchant calls customer; correct | POS-payload parity test — **GAP** |
| Double kitchen ticket | 3 | fixed (CAS claim) | void duplicate | claim-then-fanout ✅ |
| POS OAuth token expired/revoked (silent) | 2 | needs_reconnect banner | reconnect OAuth | token-health poll — partial |
| POS API outage (Square/Clover/Toast) | 2 | push 5xx | deferred ticket + merchant SMS fallback | retry queue — partial |
| Currency-enum / payload 400 (the fixed class) | 2 | fixed #438 | uppercase currency | kitchen prove-out test ✅ |
| Order routed to wrong merchant/location | 1 | GAP | halt; correct location_id | location assertion — **GAP** |
| POS rejects (item not in their catalog) | 3 | push error | manual entry | menu-sync check — **GAP** |
| Deferred ticket lost if webhook fails | 2 | tied to webhook | resend webhook (drains) | retry ✅ |
| Clover injection: no device online | 3 | HCO/inject error | ticket visible in Clover dashboard | device-online check — partial |
| Menu drift: Meridian price ≠ POS price | 2 | GAP | reconcile menus | menu-sync monitor — **GAP** |
| Tax: Meridian tax ≠ POS tax | 3 | GAP | align tax_rate | tax-source-of-truth — **GAP** |
| Modifiers/toppings dropped in POS payload | 2 | GAP | fix normalizer→POS map | payload parity test — **GAP** |
| Test/demo order hits real kitchen | 3 | GAP | demo-merchant gate | id-allowlist ✅ (audit) |
| Rush overwhelms injection | 3 | GAP | queue/throttle | backpressure — **GAP** |
| Lightspeed/other rail assumed live but inert | 4 | known (no keys) | don't route to it | capability flag ✅ |

### Detection gaps (build these)
- ~~**Paid-without-kitchen-push monitor**~~ — **BUILT** (`src/services/kitchen_monitor.py`):
  sweeps paid `phone_orders` every 10 min and pages DEFCON 1 when neither the POS
  push (`pos_success` / `pos_delivery_status` / `fulfillment_*`) nor the merchant
  SMS fallback (`merchant_notify_status`) delivered a ticket within the grace
  period. Detection only — re-push stays manual so no order can be double-ticketed.
- **POS-payload parity test** (items/qty/price/modifiers/tax Meridian→POS).
- **Menu-sync** + **location-id assertion** + **POS token-health** poll.

---

## Communications, Compliance & Business Continuity

| Event | DEFCON | Detection | Immediate mitigation | Prevention |
|---|---|---|---|---|
| Outbound email dead (Resend/Postal domain unverified/blocked) | 2 | GAP: no send-success monitor | switch provider (Postal↔Resend fallback exists) | send-failure-rate alert — **GAP** |
| Email blacklist / reputation tank | 2 | GAP | warm alt domain; pause bulk | DMARC/reputation monitor — **GAP** |
| Receipt SMS undelivered (customer thinks unpaid) | 3 | GAP: no delivery check | per-country from-number; call customer | delivery-status webhook — **GAP** |
| SMS TCPA/CAN-SPAM/opt-out violation | 1 | GAP | honor opt-out; stop sends | opt-out enforcement + audit — partial |
| False marketing claim resurfaces (data-residency) | 2 | GAP | edit copy; redeploy | SEO-copy claim scan — **GAP** (regressed once) |
| "Certified" claim slips into copy | 2 | GAP | remove word | copy lint for banned terms — **GAP** |
| Merchant/customer lawsuit (billing/privacy/food) | 1 | inbound legal | preserve evidence; counsel | make-good + evidence trail ✅(billing) |
| Vendor ban / price hike / API deprecation / shutdown | 2 | vendor email | activate fallback; migrate | multi-vendor + exit plan — partial |
| Payment processor freezes funds | 1 | Stripe notice | second processor; comply | acct diversification — **GAP** |
| **Key-person: Aidan unavailable** | 2 | n/a | **runbooks + key access must not be solo** | documented access + delegate — **GAP** |
| Domain/registrar lockout or expiry | 1 | GAP | recover account; renew | auto-renew + expiry monitor — **GAP** |
| GBP / listing hijack | 3 | GAP | reclaim listing | ownership monitor — **GAP** |
| Support overwhelmed (no ticketing) | 3 | GAP | triage manually | support system — **GAP** |
| Negative PR / social incident | 3 | GAP | respond; correct | brand monitor — **GAP** |
| SLA/contract breach with merchant | 3 | merchant complaint | remediate; credit | SLA tracking — **GAP** |
| No business insurance | 2 | known | obtain E&O/cyber | — |

### Detection gaps (build these)
- **Email send-failure-rate** + **SMS delivery-status** monitors (silent comms failure = invisible lost receipts).
- **Marketing-copy lint** (banned: "certified", false residency) in CI — this class regressed once.
- **Domain/registrar expiry** monitor.

### Bus-factor / continuity
The single largest continuity risk is **key-person concentration**: keys live in
`/root/.secrets` on one box, vendor dashboards are one login, and the operator
is one person. Continuity requires: (1) a sealed **break-glass** copy of
critical credentials + this runbook set held by a trusted second party; (2)
vendor accounts with a second admin where possible; (3) **auto-renew** on domain
+ certs so absence is survivable; (4) these DEFCON protocols readable and
runnable by anyone (human or a Claude session) — which is the point of writing
them down.

---

## Master detection-gap backlog (ranked)

The high-severity + no-detection intersections — where we'd learn from a victim,
not a monitor. Build order:

1. ~~**Paid-without-kitchen-push monitor**~~ (DEFCON 1, POS) — charged, no food, merchant
   blind. **CLOSED** — `src/services/kitchen_monitor.py`, on by default
   (`MERIDIAN_KITCHEN_MONITOR=0` disables).
2. **Overcharge detection** (DEFCON 1, payments) — invariant flags under only; legal exposure.
3. **Cert + domain expiry monitors** (DEFCON 1–2, infra) — silent until total outage.
4. **Secret-scan CI + mgmt-token/ENCRYPTION_KEY vault** (DEFCON 1, security).
5. **Vapi credit-low + call-cost-abuse alerts** (DEFCON 2, voice) — fleet stops silently.
6. **Cross-session double-charge dedup** (DEFCON 1, payments).
7. **Edge watchdog default-ON** (DEFCON 2 meta — the detector that must never be off).
8. **Email/SMS delivery monitors** (DEFCON 2–3, comms) — invisible lost receipts.
9. **Marketing-copy CI lint** (DEFCON 2, compliance) — false-claim class regressed once.
10. **Break-glass credential + runbook copy** (DEFCON 2, bus-factor).

Each becomes a tracked build item. A DEFCON catalog with a known gap list beats
a perfect-looking one that hides them — closing this backlog is the ongoing work.
