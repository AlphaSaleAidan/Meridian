# Phone Orders — The Full Loop, Explained (2–3 min video script)

> Status: **LIVE** (Vapi voice agent, production, multi-tenant)
> Use this module three ways with the SAME 2–3 minute cut:
> 1. **Rep training** — learn the loop well enough to narrate any leg of it on demand.
> 2. **Merchant onboarding** — show a new merchant exactly what their customers will experience.
> 3. **Pitch asset** — the proof video for demos: nothing staged, every screen is the real product.

## What this video proves

A customer calls the merchant's number. An AI agent takes the order item by item, reads
it back with the total, and only submits after the customer confirms. A secure Stripe
pay-by-text link lands on the customer's phone within seconds. When they pay, the ticket
drops into the merchant's POS and fires to the kitchen — and the whole call, order, and
payment show up in the merchant's Meridian portal. **Call → order → pay link → POS →
kitchen. One loop, no humans, no fakes.**

Two payment modes exist. This script films the default **pay-now** mode, because it is
the money-flow showcase and it is the mode where the confirmation SMS fires (the SMS is
the pay-link message — there is no separate confirmation text). In pay-now, the kitchen
ticket is deliberately **held until payment confirms** (anti-scam: an unpaid order never
reaches the kitchen). In pay-at-pickup mode the ticket goes to the POS immediately
instead — mention it verbally if asked, don't film it.

---

## Beat table (0:00–2:30)

Every beat has three parallel tracks. A rep must be able to narrate ANY column on demand.

| # | Time | WHAT THE CUSTOMER HEARS | WHAT THE MERCHANT SEES | WHAT SHOWS IN THE PORTAL |
|---|------|-------------------------|------------------------|--------------------------|
| 1 | 0:00–0:10 | Phone rings once, then the agent's greeting — the merchant's own custom greeting, or the default: *"Thanks for calling Tony's Pizzeria! What can I get for you?"* | Nothing yet — staff are untouched. | Call Log tab: a live call appears against the merchant's number. |
| 2 | 0:10–0:35 | Item-by-item ordering. Customer: *"Can I get a large pepperoni pizza?"* Agent confirms name, size, quantity, and mods for EACH item: *"One large pepperoni — anything else on it?"* Customer adds a second item. | Nothing yet. | Nothing new — the order doesn't exist until it's confirmed. |
| 3 | 0:35–0:45 | The one gentle upsell (default setting — merchants can turn it off or make it more active): *"Can I throw in a drink or a side for you?"* Customer: *"Sure, a Coke."* Agent asks ONCE and moves on. | Nothing yet. | Nothing yet. |
| 4 | 0:45–1:00 | Order type + name: *"Is that for pickup or delivery?"* — *"Pickup."* — *"And what's the name for the order?"* — *"Sarah."* (If delivery, the agent collects the address here before anything else.) | Nothing yet. | Nothing yet. |
| 5 | 1:00–1:20 | The read-back. Agent reads the COMPLETE order — every item, size, topping — with the calculated total: *"So that's one large pepperoni pizza and one Coke, for pickup under Sarah — $21.60 total. Does that all look right?"* Customer: *"Yep."* Only NOW does the agent call `submit_order`. | Nothing yet — the hold is intentional. | Nothing yet. |
| 6 | 1:20–1:35 | The confirmation + pay-link line, straight from the live prompt: *"Thanks Sarah! Your pickup order — 2 items — is in. I've sent a secure payment link to your phone — you'll get a receipt once it goes through. See you soon!"* Call ends. | Nothing in the POS yet — in pay-now mode the ticket is HELD (`awaiting_payment`) until the money clears. | Call Log: the call flips to an order. Order shows status **Awaiting payment**, with the payment link attached. |
| 7 | 1:35–1:55 | (Silence — we're on the customer's phone screen now.) The SMS lands: *"Hi Sarah! Your pickup order from Tony's Pizzeria is confirmed. 2 items — $21.60. Pay here: [link]"* Customer taps it, pays on the Stripe-hosted checkout (Apple Pay / Google Pay / card — card data never touches Meridian). | Nothing yet. | Order still Awaiting payment — watch it flip in the next beat. |
| 8 | 1:55–2:15 | (Nothing — the customer is done.) | **This is the payoff shot.** Payment confirms → the ticket is pushed to the POS and released to the kitchen. On Square: an order appears in the merchant's Square dashboard and fires to the kitchen display/printer. (On Clover, until our App Market listing is approved, the order arrives as a text to the staff line + a dashboard ticket instead — see the Clover Read Only module.) If the merchant has a staff line configured, their phone buzzes with the ticket text too. | Order flips to **Paid**, kitchen released. Get Paid tab: collected total ticks up, Stripe fee breakdown visible. |
| 9 | 2:15–2:30 | — | — | Closing shot: Phone Orders **Overview** tab — Total Calls, Orders Placed, Paid, conversion and collection rates. One screen that proves the loop ran end to end. |

---

## Recording checklist (nothing faked on camera)

Set up BEFORE hitting record:

- [ ] **Demo tenant with a seeded menu** — a dedicated org with `phone_agent_config`
      filled in: business name, greeting, menu items with real prices (use per-size
      pricing on at least one item so the read-back math is visibly correct).
- [ ] **Sandbox POS** — connect Square **sandbox** credentials to the demo tenant so the
      ticket really appears in a real (sandbox) Square dashboard. Use the `demo_safe`
      flag only for dry runs — it makes the POS push logs-only, so no ticket will appear
      on camera.
- [ ] **Stripe test mode** for the pay link, so the on-camera payment is a real checkout
      flow without a real charge. Avoid the `demo-merchant` id for the filmed take: it
      simulates "paid" instantly, which skips the payment beat you want to film.
- [ ] **Know the clock**: calls hard-cap at 5 minutes and 3 minutes are included — the
      scripted call comfortably fits, but don't ad-lib a 4-minute order.
- [ ] Do one full dry run and confirm all three legs fire: SMS received, sandbox POS
      ticket created after payment, portal order flips to Paid.

Capture list (three devices/screens, synced by the call audio):

1. **Customer's phone** — screen recording: the call, the SMS arriving, the Stripe
   checkout, the receipt.
2. **POS / KDS shot** — the Square (sandbox) dashboard or kitchen display at the moment
   the ticket lands (beat 8). This is the money shot; frame it tight.
3. **Portal screen capture** — Phone Orders page: Call Log during the call, the order
   row flipping Awaiting payment → Paid, and the Overview tab for the close.

---

## Rep narration cues (one line per beat)

| Beat | Say this |
|------|----------|
| 1 | "That's not a person — that's the merchant's AI line answering on the first ring, with their own greeting." |
| 2 | "It takes the order item by item and confirms size, quantity, and toppings on every single one." |
| 3 | "One polite upsell, once, then it moves on — the merchant controls this setting." |
| 4 | "Pickup or delivery, plus a name — and if it's delivery, it won't proceed without an address." |
| 5 | "Nothing is submitted until the customer hears the full order and the total read back and says yes." |
| 6 | "The moment they confirm, the order is in and a secure payment link is already on its way to their phone." |
| 7 | "Pay by text — Stripe-hosted, Apple Pay ready. Card data never touches us." |
| 8 | "And here's the part that matters: the second the payment clears, the ticket drops into the POS and fires to the kitchen. Unpaid orders never get cooked." |
| 9 | "Every call, order, and dollar is right here in the portal — that whole loop just ran with zero staff time." |

---

_Grounded in: `src/api/routes/vapi_webhook.py` (call flow, upsell, read-back, submit_order,
pay-link line), `services/phone_agent/pay_on_phone.py` (pay-now hold + POS push after
payment), `services/phone_agent/sms_checkout.py` (SMS copy),
`frontend/src/pages/PhoneOrdersPage.tsx` (Overview / Call Log / Get Paid tabs)._
_Last updated: 2026-07-16_
