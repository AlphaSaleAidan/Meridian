# OpenTable & SevenRooms — how to actually get in

Researched 2026-08-15. **Nothing here has been sent.** These are drafts and
verified routes for Aidan to send.

The headline: this is much more open than expected. OpenTable publishes an API
**named for this exact use case** — the *In House Booking API, aka Voice AI
API* — with public docs and a self-serve application form. It is not a closed
door; it is a queue and a certification.

---

## OpenTable

**Apply:** https://www.opentable.com/restaurant-solutions/api-partners/become-a-partner/

A five-step form. Have ready:
- an SMS-capable phone (step 2 is an email **and** SMS one-time-code check)
- company registration date
- **"Is the Product Live?"** — say yes, and have the Canada pilots demonstrably running
- **Number of Monthly Active Users** and **Number of Unique Restaurant Locations Live**
- any OpenTable restaurants already using us (currently none — say so)
- any other table-management systems we partner with (Square Appointments)

**Emails, all published by OpenTable — none guessed:**

| Address | Use |
|---|---|
| `busdev@opentable.com` | Partnerships / BD. Published on their integrations page. **Send the note below here.** |
| `api@opentable.com` | Partnerships & API integrations team; technical questions. 3–5 business day reply. |
| `partnersupport@opentable.com` | Partner-portal support, ~48h. Also where you subscribe to a new API. |
| `legal@opentable.com` | Terms questions. |

**Docs are public right now:** https://docs.opentable.com/ — a published Postman
collection covering Booking, CRM, Directory, Sync, POS and Reviews APIs. Worth
reading before applying, because it lets us scope the work honestly.

**The Voice AI API, in their words:**
> "Primarily developed to power Voice AI reservation systems, this API is
> designed for efficiency and integration with advanced conversational
> interfaces."

Endpoints: Availability Search, Get Experiences, **Slot Lock**, Create
Reservation, Modify, Cancel, Lookup. Note the Slot Lock — same idea as our own
`offered` hold, so the models line up.

**Their stated limits for voice partners:** a mobile number is required (no
landlines, because they SMS the guest); a Voice AI partner **cannot pass
OpenTable's 2% service charge to guests**; ticketed experiences unsupported.

**What approval actually costs us:**
- App Review is mandatory, and a material change means re-review.
- **≥14 days** certification on a pre-production submission. They test against
  a specific restaurant id and **ask for a phone number so they can call our
  agent themselves.** That is a real quality bar and we should want it.
- We must build a restaurant onboarding **and offboarding** flow (OAuth
  preferred) plus a marketplace tile: SVG logos at 64×64, 256×256 and 200×48, a
  400×300 login screenshot, a 400×400 product image, hero copy, ≤6 onboarding
  steps, and a partner support email.
- Security terms: encryption at rest, TLS 1.3, credentials encrypted in transit
  and at rest, breach notification.
- **No publicity without their written consent** — we cannot announce it
  unilaterally.
- No fee today; they reserve the right to charge. Liability cap $1,000.
- **No published minimum restaurant count, revenue, insurance or SOC 2.**

**Precedent:** Slang.ai is on OpenTable's own partner logo wall and has shipped
this integration since roughly September 2024. Popmenu is the worked example in
OpenTable's OAuth onboarding docs. Companies our size are through this door.

**Realistic timeline:** 2–4 months end to end. The long poles are their review
and the 14-day certification, not our engineering.

### Draft — to `busdev@opentable.com`

> **Subject:** Voice AI booking partner application — Meridian (Canada/US)
>
> Hello,
>
> I've submitted the partner application form and wanted to introduce us
> directly, since the API we're after is specific.
>
> Meridian is an AI phone agent for independent restaurants. We answer the
> restaurant's phone, take orders into their POS, and now take reservations.
> We're live with pilot restaurants in British Columbia and Ontario.
>
> We'd like to integrate the **In House Booking API (Voice AI)** so that
> callers to an OpenTable restaurant get a real OpenTable reservation rather
> than a message we take by hand. We've read the public docs; the Slot Lock →
> Create Reservation flow maps cleanly onto how our agent already holds a slot
> while a caller confirms.
>
> Two things I'd want to get right early:
>
> 1. The onboarding and offboarding flow and the marketplace tile — we'd rather
>    build to your spec from the start than retrofit.
> 2. Certification. We understand you call the agent as part of review. We'd
>    welcome that, and can have a test line pointed at a sandbox restaurant
>    whenever suits you.
>
> Happy to share our pilot restaurants and a recording of a live booking call.
> Who's the right person to talk to?
>
> Aidan Pierce
> Meridian — meridian.tips

---

## SevenRooms

**Apply:** https://sevenrooms.com/partnership-opportunities/ — one form,
"Tell us about your integration request". Reached from
https://sevenrooms.com/lets-talk/ → Partnership Inquiries → Integration Request.

**There is no partnerships email.** The only address published anywhere on
their site is `support@sevenrooms.com`, which is the customer-support queue and
the wrong door. Do not invent one — the form is the route.

**No public API docs.** `developer.` / `developers.` / `docs.` /
`apidocs.sevenrooms.com` all 404; `api.sevenrooms.com/docs/` returns 401. The
spec is behind partner auth, which means **we cannot scope the work before they
agree to talk.** That is the main practical difference from OpenTable.

**Nothing published** on eligibility, fees, security review or timeline. They
run a trust portal at trust.sevenrooms.com, which implies a vendor security
review exists, but not what they ask of inbound partners.

**Precedent, and it's encouraging:** their integrations directory has an
"SMS & Voice" category listing three AI voice companies — **Slang**,
**Bookline** (a small Spanish company) and **hey buddy** (Australian). Two of
the three are small non-US startups, which is the clearest evidence they'll
admit a company our size.

**The one real risk, stated plainly:** SevenRooms sells its own Voice AI
product, and they are now owned by DoorDash. We would be asking to integrate
with a platform that ships a competing first-party feature. They admitted
Slang, Bookline and hey buddy, so it isn't a blanket no — but expect a
partnerships negotiation rather than developer onboarding, and expect to be
qualified on installed base. Three pilots is not much leverage in that
conversation.

### Draft — for the form

> Meridian is an AI phone agent for independent restaurants, live with pilots
> in Canada. We answer the restaurant's phone and take orders into their POS;
> we've just added reservations.
>
> We'd like to write reservations into SevenRooms for mutual customers, the way
> Slang and Bookline do, so a caller to a SevenRooms venue gets a real booking
> in the system their staff already run rather than a message taken by hand.
>
> We're looking for API access and the onboarding requirements. Happy to go
> through whatever security review you need. Who should I be speaking to?
>
> Aidan Pierce — meridian.tips

---

## Suggested order

1. **OpenTable first.** The path is documented, the docs are readable today, an
   API exists that is literally named for what we do, and the bar is quality
   rather than size. Submit the form, then email `busdev@` naming the In-House
   Booking (Voice AI) API.
2. **SevenRooms in parallel.** One form, nothing to lose. Lower expectations,
   longer odds, and no way to chase it if it stalls.
3. **Neither blocks anything.** Square Appointments is already built and
   self-serve, and the calendar-feed path covers every merchant with no API at
   all. These two are upside, and the cost is lead time rather than
   engineering — which is exactly why they should start now.

## Not verified

Any SevenRooms partnerships email, their eligibility criteria, fees or approval
timeline; OpenTable's application-review SLA; OpenTable minimum MAU or
restaurant thresholds; whether OpenTable has any Reserve-with-Google-style
public feed. `www.opentable.com` refuses direct connections from our host, so
their pages were read through a text proxy — the content is verified, but the
form itself was never exercised.
