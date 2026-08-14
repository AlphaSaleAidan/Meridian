# Bookings — reservations and appointments

The phone agent can take a booking, not just an order. Restaurants get tables,
barbershops get chairs, detailers get bays.

## The problem this replaces

"Reservations" already existed in the product, but only as a sentence in a
prompt. `_reservation_block` told the agent to call `submit_order` with
`order_type='reservation'` and put the date, time and party size in a free-text
notes field. Nothing checked whether the business was open, whether anything
was free, or whether two callers had just been promised the same 7pm. The only
reservation data in the schema was `phone_agent_config.reservation_config`
(`{on_website, website_url}`), which is NULL on every merchant in production.

## The one idea

A restaurant table, a barber's chair, a detailing bay and a named staff member
are the same thing: a **resource** that holds exactly one booking at a time.
Model that once and every vertical works. A table carries `seats=4`; a chair
carries `seats=1`. Nothing else differs.

Duration comes from a **service**. A salon's services are literal ("Fade, 30
min"). A restaurant expresses turn time as one pseudo-service per party band
("Table for 1–4, 90 min"), so party size selects duration through the same
mechanism rather than a second one.

## The guarantee

Double-booking is prevented by the database, not by application code:

```sql
EXCLUDE USING gist (
    merchant_id WITH =, resource_id WITH =,
    tstzrange(starts_at, ends_at) WITH &&
) WHERE (status IN ('confirmed', 'seated'))
```

Two callers on two phone lines, a walk-in typed at the host stand and a synced
calendar event cannot take the same resource, however the race interleaves —
Postgres refuses the second write with SQLSTATE 23P01. The Python availability
check is a convenience for the caller experience; it is not what makes the
promise true.

Verified against Postgres 17.6: overlap rejected, back-to-back allowed
(half-open ranges), different resource allowed, cancellation frees the slot,
confirmation codes unique per live booking and reusable after cancellation.

`SupabaseREST._handle_error` deliberately swallows HTTP 409, which is exactly
how a collision arrives. Bookings therefore bypass the shared client and use
`booking_store._req`, where a 409 becomes `SlotTaken` and everything else
becomes a loud error.

## Honesty contract

A caller must never hang up believing they have a table when the write failed.
Every failure path — no availability, closed, mid-write collision, exception —
returns an honest sentence and never a confirmation. This mirrors the order
pipeline's `_order_reached` gate. `reserve()` walks every eligible resource and
only raises once all of them have refused.

## Time

Hours are authored in the merchant's local wall clock and evaluated against
`phone_agent_config.business_timezone`; storage and comparison are UTC. Storing
an opening time as a fixed UTC offset shifts a restaurant's whole evening twice
a year. There are no naive datetimes in the engine.

The prompt injects today's date **in the merchant's timezone** — this box runs
on CEST, which is already tomorrow for a North American merchant for part of
every evening.

## What ships

| Piece | Location |
|---|---|
| Schema (8 tables + the constraint) | `migrations/081_bookings.sql` |
| Persistence, collision-aware | `src/services/booking_store.py` |
| Availability + reserve | `src/services/booking_engine.py` |
| Phone tool handlers, spoken copy | `src/services/booking_agent.py` |
| Vapi tools + prompt block + dispatch | `src/api/routes/vapi_webhook.py` |
| Portal API (16 routes) | `src/api/routes/bookings.py` |
| SMS reminders (T-24h, T-2h) | `src/services/booking_reminders.py` |
| Calendar sync | `src/services/booking_sync.py` |
| Provider adapters | `src/services/booking_providers/` |
| Outbound .ics feed | `src/services/booking_feed.py` |
| Portal UI | `frontend/src/pages/Bookings*.tsx` |

Phone tools: `check_availability`, `book_reservation`, `cancel_reservation`,
`lookup_reservation`. Attached **only** when `booking_mode='native'`, which
defaults to `off` — so every existing merchant's assistant payload and prompt
are byte-identical to before.

## Integrations

Researched 2026-08-14. There is no Plaid-for-bookings: nothing sells write
access across OpenTable, Booksy, Vagaro and Fresha. Coverage is a barbell — one
calendar substrate for the long tail, plus vertical APIs where density earns
the work.

**Built now**

- **Calendar feed (.ics), inbound** — read-only, no vendor approval, no
  credential to rotate. The merchant pastes a link; their commitments start
  blocking our slots. Parser is hand-rolled (four fields from VEVENT, from a
  merchant-supplied URL — every dependency here is a new parser exposed to
  semi-trusted input). Handles RFC 5545 folding, DATE vs DATE-TIME, TZID,
  CANCELLED and TRANSPARENT. **Recurring events (RRULE) are read as their base
  occurrence only** — a half-correct expansion would block the wrong hours,
  which is worse than not importing, and the portal says so.
- **Calendar feed (.ics), outbound** — the merchant subscribes in Google,
  Outlook or Apple and sees every booking. This is *the* integration for every
  tool with no API. One-way, and refreshed on the client's schedule (hours, not
  minutes, for Google) — the portal states this rather than implying live sync.
- **Google Calendar** — adapter complete (`freebusy.query`, `events.insert`,
  delete; refresh tokens AES-GCM encrypted). **Not connectable until someone
  creates a Google Cloud OAuth client**; `is_configured()` is False without
  `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` and the portal hides the button
  rather than offering one that cannot complete.

**Why Google first:** the scope is *sensitive*, not *restricted* (Calendar is
absent from Google's restricted list), so it needs brand review but **not** the
annual CASA assessment that prices small platforms out. Free to 1M req/day. And
it is the only substrate the long tail actually has — auto detailers have no
integrable software at all.

**Next, not built**

- **Square Appointments** — self-serve OAuth, `CreateBooking`,
  `SearchAvailability`, webhooks, and Meridian already runs Square OAuth. Two
  real costs: our scopes are read-only by design (`src/config.py:232`), so
  adding `APPOINTMENTS_WRITE` forces every merchant to re-authorize; and
  seller-level writes **403 unless the merchant pays for Appointments
  Plus/Premium**. Qualify on that before selling booking.
- **OpenTable / SevenRooms** — real write paths, both partner-gated. The cost
  is lead time, not engineering; start the applications in parallel.

**Do not chase.** Resy and Tock have no third-party surface. Booksy, Fresha,
Vagaro, Squire, Phorest and GlossGenius publish no developer portal — they
expose booking to Google's Reserve programme, not to us. Auto-detailing
software (Urable, Mobile Tech RX) runs no developer programme; serve detailers
with our calendar plus Google. Schedulicity no longer exists — its domain
redirects to Vagaro. Cronofy is technically fine and commercially out at an
$819/mo floor; Nylas at ~$1.50/connected account is the only sensible
aggregator, and it buys calendar breadth, not booking-tool coverage.

`booking_providers/registry.py` carries the unreachable tools *with reasons and
workarounds*, and the portal shows them. A merchant on Booksy who sees nothing
about Booksy assumes we haven't got round to it.

**Open question worth resolving by hand:** do Booksy/Vagaro/Fresha sync two-way
with Google Calendar? If they do, the Google path already reaches them and the
roadmap shortens. Test in trial accounts.

## Square Appointments (built)

The only major booking platform in this space with a self-serve API. Square
splits it in two, and the split decides what we can promise:

| Level | Scopes | Plan needed | What it grants |
|---|---|---|---|
| Buyer | `APPOINTMENTS_READ` + `APPOINTMENTS_WRITE` | **any, incl. free** | SearchAvailability, CreateBooking, CancelBooking — the whole loop |
| Seller | `APPOINTMENTS_ALL_READ` + `APPOINTMENTS_ALL_WRITE` | Appointments Plus/Premium | reading bookings taken elsewhere (busy import) |

So "Square booking needs a paid plan" is **wrong**. A free-plan barbershop gets
the entire booking loop; the paid plan only adds our ability to see their other
bookings. `detect_access_level()` probes with a one-row ListBookings and the
portal states which they have.

Booking scopes are requested through a **separate** OAuth flow
(`/api/bookings/square/authorize`), never bolted onto the POS connection —
`src/config.py:232` keeps the POS scopes read-only and that promise is kept.

Square gotchas encoded in the adapter: `service_variation_version` is required
and must be fresh; cancel re-reads `version` first (optimistic concurrency);
idempotency key is our own booking id; terminal Square statuses are not
imported as busy; the availability window clamps to 31 days.

### booking_mode = 'provider'

Their system owns the calendar; we search and write into it and keep a local
mirror row for reminders and today's book. **Who is authoritative decides what
a failure means:** a mirror collision or database failure must not become an
apology, because Square already accepted and the booking stands. But if *Square*
is unreachable we do **not** quietly fall back to our own calendar for the
write — a booking their staff never see is not a booking. Availability reads do
fall back, because stale slots beat refusing a live caller, and the write
reconciles.

## Cancellation recovery — the differentiator

Competitive research (2026-08-15) found every incumbent's waitlist is **a list a
human works**. Boulevard's "waitlist notifications" notify staff. Vagaro and
SevenRooms document waitlist *management*. Consumer versions are first-come
"notify me" blasts. When a 7pm cancels at 4pm on a Friday, nobody acts, and the
table goes empty.

The same research killed a comfortable assumption: **answering the phone is no
longer a differentiator.** SevenRooms Voice AI, Fresha AI Concierge
($99.95/loc + $0.60/min), Mindbody, Slang.ai ($399–599/loc) and Loman all book
by phone today. Every one of them is *inbound*. They answer a call; they do not
place one. Acting on a cancellation is the half nobody automates.

How ours works:

- **One guest at a time, and the slot is really held.** The hold is a real
  `bookings` row in `offered` status, so the exclusion constraint protects it
  like a confirmed booking — the phone agent physically cannot sell it out from
  under someone still reading the text. Verified on PG 17.
- **Ranked by value, but only where value is known.** Settled POS spend and
  real no-show history decide the order where they exist; arrival time where
  they don't. `rank_reason` records which applied, so "why did they get it?"
  has an answer. A no-show outweighs a big spend — turning up beats spending.
- **A cooldown**, found by test rather than by reasoning: the first version
  released an expired hold and immediately re-offered the same slot to the
  person who had just ignored it.
- **A failed notification releases the hold.** Holding a table for someone we
  could not reach serves nobody.
- **Outbound voice is written but env-gated off.** This Telnyx account has no
  outbound voice profile, so automated calls cannot originate. SMS is the live
  channel and the portal says so.

## Reminders

Celery beat, every 15 minutes, two passes at T-24h and T-2h. Idempotent by
construction: a booking is picked up only while its send-marker column is NULL,
and the marker is written **only after a successful send** — a failed text stays
eligible for the next sweep. A duplicate reminder is an annoyance; a missing one
is a no-show.

## Deliberate limitations

- Overnight service is two rows (Fri 17:00–23:59 + Sat 00:00–02:00). A 1 AM
  booking genuinely belongs to Saturday, and this keeps slot generation
  trivially correct. The portal splits it for the merchant.
- RRULE expansion, as above.
- Pacing counts *arrivals* per interval, not occupancy — that is what actually
  lands on a kitchen at once.
- The `.ics` feed URL is the credential; calendar clients cannot send an
  `Authorization` header. 32 hex chars, unique-indexed, rotatable, 404 on
  miss, and it carries only what is already in a booking confirmation.

## To go live

1. Apply `migrations/081_bookings.sql` in the Supabase SQL editor (house
   doctrine: migrations are hand-applied). Idempotent; verified on PG 17.
2. Set `booking_mode='native'` and `booking_noun` on the merchants who want it,
   then add their resources, services and hours in the portal.
3. Optional: create a Google Cloud OAuth client to light up Google Calendar.

## Tests

```bash
python -m pytest tests/test_booking_engine.py tests/test_booking_agent.py \
  tests/test_booking_ics.py tests/test_booking_feed_and_reminders.py -q
python -m pytest tests/compliance -q      # the CI gate
```
