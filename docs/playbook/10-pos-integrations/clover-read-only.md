# Clover Read Only — What We Can and Can't Do Today

> **MAINTENANCE NOTE — update this module the day Clover App Market approval lands.**
> Three sections change on approval day:
> 1. **Gated behind App Market approval** (moves to "what works today")
> 2. **The exact words to use** (the "orders arrive by text" sentence flips)
> 3. **Objection handling vs Square** (objection #1 goes away)

> **Status 2026-07-20:** The dev-dashboard app (`YK86AE2YAHSP2`) now requests **Orders Write + Customers Write** — saved live on the Clover developer dashboard. App Market approval has NOT landed: the app is still an unpublished DRAFT (no release submitted, 0 merchant installs), so every gate below still applies for real merchants. What changed: merchants who authorize the draft app from now on grant write scopes, so order injection can finally be exercised end-to-end in dev/sandbox.

This module exists so nobody oversells Clover. Read it before your first Clover pitch.
For connection mechanics and failure modes, see the main [Clover guide](clover.md).

## What works TODAY (read-only)

Meridian connects to Clover via OAuth — the merchant clicks Connect, logs into Clover,
approves, done. From that moment we **read** their data; we never write to their POS:

- **Menu / catalog sync** — items, categories, stock counts, tenders, tax rates
- **Sales data** — orders, payments, and refunds, with an initial backfill on connect
  and incremental sync every 15 minutes (plus webhooks for near-real-time updates)
- **Operations data** — employees, customers, devices, merchant profile

That read-only feed powers essentially the full analytics suite: revenue trends and
forecasting, Money Left on Table, peak hours, basket analysis, product velocity and
inventory intelligence, employee performance, discount/promo ROI, and anomaly detection.
Tokens are encrypted at rest; we request read access only.

**Phone orders work for Clover merchants today** — with one boundary: the order can't be
injected into their Clover yet. Instead, the moment an order is placed (and paid, in
pay-now mode), it arrives **instantly by text** to the staff line and appears as a ticket
in their Meridian dashboard for one-tap manual entry.

## Gated behind App Market approval

- **Write access** to the merchant's Clover (orders, inventory writes)
- **Order injection** — phone orders dropping straight into their Clover as a native
  ticket that fires to the kitchen printer

The code for this is already built (order → line items → print event). It switches on
when Clover approves our App Market listing and merchants re-authorize with the
elevated permissions. Until then: SMS + dashboard ticket.

## The exact words to use (say these verbatim)

> "Today Meridian reads your Clover data for analytics and menu sync; phone orders
> arrive instantly by text."

> "The moment our Clover App Market listing is approved, orders drop straight into your
> Clover — and you'll get that as a free update, nothing to reinstall."

> "We never write to your Clover today, so there is zero risk to your books — we can't
> touch a ticket, a price, or a payout."

> "Everything else — the analytics, the AI phone agent, pay-by-text — is fully live for
> you right now."

Do NOT say: "orders go straight into your Clover" (not yet), "we're approved in the App
Market" (we're not, yet), or promise an approval date.

## Demo script — the read-only value in 2 minutes

1. **Connect (0:00–0:40).** Portal → Settings → POS Connections → Connect Clover. The
   merchant logs into their own Clover and approves. Say: "That's the whole setup —
   read-only access, your data starts syncing now."
2. **Menu synced (0:40–1:10).** Open the synced catalog — their real items, categories,
   and prices, untouched. Say: "This is your live menu, pulled straight from Clover.
   It's also what the AI phone agent will read from."
3. **Analytics view (1:10–2:00).** Open the dashboard on a connected account (use the
   demo org if their backfill is still running): revenue trend, peak hours, Money Left
   on Table. Say: "This is what your last 18 months look like once the backfill
   finishes — usually first insights within 24 hours."

## Objection handling vs Square (honest answers only)

| Objection | Honest answer |
|-----------|---------------|
| "On Square, phone orders go straight into the POS. Why not on my Clover?" | "True — Square lets us inject orders today, Clover gates that behind their App Market review. Until we're approved, your orders arrive instantly by text and in your dashboard; the day approval lands, they drop straight into your Clover as a free update. Nothing else about the product is different." |
| "So should I just switch to Square?" | "No — don't switch a POS over this. The analytics, the phone agent, and pay-by-text are identical on Clover today. The only difference is one re-key step per phone order, and it's temporary." |
| "How long until approval?" | "Clover controls that timeline, so I won't promise a date. What I can promise: your contract and price don't change, and you get order injection automatically the day it's approved." |

## CERTIFICATION CHECK

**Q1. A Clover merchant asks: "So when someone phone-orders, it prints in my kitchen like
a normal ticket, right?" What's the correct answer today?**

- A) Yes — orders print to the kitchen automatically. ✗
- B) No — phone orders never work on Clover. ✗
- C) Not yet — today the order arrives instantly by text and as a dashboard ticket;
  native injection into Clover turns on when our App Market listing is approved, as a
  free update. **✓ CORRECT**
- D) Only if they also connect Square. ✗

**Q2. Which of these can Meridian do on a Clover account TODAY?**

- A) Update item prices in the merchant's Clover. ✗ (write access — gated)
- B) Read orders, payments, catalog, and employees for analytics and menu sync.
  **✓ CORRECT**
- C) Push a phone order into Clover so it fires the kitchen printer. ✗ (gated behind
  App Market approval)
- D) Nothing — Clover isn't supported. ✗

---

_Grounded in: `src/clover/` (OAuth, client, sync engine — read endpoints),
`src/services/pos_connectors/clover_kitchen.py` (built-but-gated order injection),
`services/phone_agent/pos_connector.py` (SMS/dashboard fallback path)._
_Last updated: 2026-07-16_
