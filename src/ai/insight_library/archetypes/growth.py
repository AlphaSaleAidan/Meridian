"""
Domain: GROWTH / NEW REVENUE LINES & EXPANSION READINESS.

Each archetype is a distinct reasoning pattern about a revenue line that does not
exist yet — a channel, program, daypart, location, or product/service category
the business could ADD. This is forward-looking opportunity, NOT optimization of
something already running (that lives in channel/marketing/pricing/revenue). The
defining situation is "untapped" (a latent line never worked) or "emerging" (a
forming pattern that newly justifies opening the line).

Targeting is deliberately negative-space: a "launch X" archetype fires only for
verticals where X genuinely doesn't exist yet — subscription-launch EXCLUDES
membership verticals, online-ordering-launch targets verticals whose v.channels
LACK 'online', loyalty-launch skips repeat_purchase verticals. So the catalog
never tells a gym to "launch a membership" it already runs.

Signal provenance (rigorous, gaps explicit):
  * Readiness archetypes (turnaways, capacity, second-location) join existing
    transactions/hourly_revenue/schedule_shifts → PARTIAL via a readiness fusion
    agent.
  * "Untapped channel/program" archetypes need a benchmark of peers WITH the line
    plus the merchant's own demand shape → MISSING, each specs the
    ExpansionReadinessAgent / ChannelBenchmarkAgent / PeerBenchmarkAgent to build.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical, VERTICALS
from .base import Archetype, Built, X, register


# ── Negative-space targeting helpers (fed into applies_keys) ─────────────────
def _keys_with_any_flag(*flags: str) -> tuple[str, ...]:
    fs = set(flags)
    return tuple(v.key for v in VERTICALS if fs & v.flags)


def _keys_without_flag(*flags: str) -> tuple[str, ...]:
    """Verticals that carry NONE of the given flags — the negative space where a
    'launch this' line genuinely doesn't exist yet."""
    fs = set(flags)
    return tuple(v.key for v in VERTICALS if not (fs & v.flags))


def _keys_with_channel(*channels: str) -> tuple[str, ...]:
    cs = set(channels)
    return tuple(v.key for v in VERTICALS if cs & set(v.channels))


def _keys_lacking_channel(*channels: str) -> tuple[str, ...]:
    """Verticals whose channels include NONE of the given — the launch targets."""
    cs = set(channels)
    return tuple(v.key for v in VERTICALS if not (cs & set(v.channels)))


# ═══════════════════════ EXPANSION READINESS ════════════════════════════════
def _second_location_readiness(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    kpi = v.core_kpis[0]
    extra = (" Demand has been climbing for several periods straight — the readiness window is opening now, not someday."
             if situation == "emerging" else "")
    return Built(
        title=f"Your single site is maxing out — the numbers say a second location is on the table",
        observation=f"This site runs at {X}% of practical capacity ({kpi} pinned near its ceiling for {X}+ weeks) while {unit} demand keeps arriving at the door.",
        reasoning=f"A {v.name.lower()} that is consistently demand-constrained rather than demand-starved has already proven the format; the next unit of growth can't come from this footprint, so incremental demand is either lost or must be served by a second site.{extra}",
        conclusion=f"Run a site/feasibility study for a second location in your draw area, and build its opening base from the {X}% of demand this site already turns away.",
        expected_effect=f"A proven-format second site typically opens against ~${X}/mo of pre-existing overflow demand rather than from zero.",
        recommend_when={"state": "capacity_pinned_demand_growing", "min_signal": "hourly_revenue"},
        tags=("growth", "expansion", "second_location", v.family),
    )


def _capacity_expansion_turnaways(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    if "appointment_based" in v.flags:
        cap = f"fully-booked {v.staff_role} slots with a waitlist behind them"
        add = f"add a {v.staff_role} station/chair or extend the booking grid"
    elif "table_service" in v.flags:
        cap = f"covers turned away at peak when every seat is full"
        add = f"add seats, a bar rail, or a turn-faster service model"
    else:
        cap = f"{unit}s lost when the line/queue exceeds what customers will wait for"
        add = f"add a service point/register or a second prep line"
    return Built(
        title=f"You're turning away demand you could physically serve",
        observation=f"At peak you hit {X} {cap} on {X} days a week — measured turn-aways, not a soft estimate.",
        reasoning=f"Turn-aways at a hard capacity ceiling are the cleanest expansion signal there is: the demand already showed up and the only thing missing is room/throughput to take it, so the investment is justified by booked-not-served volume rather than a forecast.",
        conclusion=f"To capture it, {add}; size the add to the measured peak turn-away, not to average volume.",
        expected_effect=f"Converting the recurring turn-away into served {unit}s is worth ~${X}/mo at current pricing.",
        recommend_when={"state": "turnaways_at_capacity", "min_signal": "hourly_revenue"},
        tags=("growth", "capacity", v.family),
    )


def _franchise_multiunit_benchmark_gap(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    kpi = v.core_kpis[0]
    return Built(
        title=f"Your {kpi} sits below multi-unit benchmark — a replicable upside before you scale",
        observation=f"Your {kpi} runs {X}% under the multi-unit/franchise benchmark for a {v.name.lower()}, while your other unit economics are in range.",
        reasoning=f"A single metric lagging the multi-unit benchmark on an otherwise healthy {v.name.lower()} usually means a transferable playbook gap, not a market limit; closing it before opening more units multiplies the fix across every future site instead of baking the weakness in.",
        conclusion=f"Diagnose the one process behind the {kpi} gap (layout, script, mix, or scheduling) and prove the fix on this site before treating the format as franchise-ready.",
        expected_effect=f"Lifting {kpi} to benchmark is worth ~${X}/mo here and compounds per additional unit opened.",
        recommend_when={"state": "below_multiunit_benchmark", "min_signal": "transactions"},
        tags=("growth", "benchmark", "expansion", v.family),
    )


def _delivery_expansion_readiness(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = (" Off-premise demand is showing up unprompted via phone/online — the pull exists before you've built the lane."
             if situation == "emerging" else "")
    return Built(
        title=f"You don't deliver yet — but the off-premise demand is already knocking",
        observation=f"{X}% of inbound contacts ask about delivery/off-premise and you currently fulfill {X} of them; no delivery line exists in your channel mix.{extra}",
        reasoning=f"For a delivery-capable {v.name.lower()} with proven product, a delivery line extends the same kitchen/inventory to a wider radius at marginal cost; the readiness test is whether asked-for-but-declined demand already exists — and here it does, so the line opens against real requests rather than a guess.",
        conclusion=f"Pilot delivery in your tightest profitable radius (own-driver or one platform) for {X} weeks and measure incremental vs cannibalized {unit}s before committing.",
        expected_effect=f"A delivery line sized to existing asked-for demand adds ~${X}/mo in incremental {unit}s net of fulfillment cost.",
        recommend_when={"state": "delivery_demand_unserved", "min_signal": "phone_call_logs"},
        tags=("growth", "delivery", "channel_launch", v.family),
    )


def _service_area_geographic_expansion(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Demand is clustering just outside your service area",
        observation=f"{X}% of declined/out-of-area requests come from {X} adjacent ZIPs that border your current radius, repeating week over week.",
        reasoning=f"For a route-based {v.name.lower()}, an adjacent cluster of declined jobs means the next service area is already self-identifying; extending the boundary there adds route density to existing crews rather than standing up a whole new market cold, so drive-time per {unit} barely moves.",
        conclusion=f"Extend the service boundary to the {X} highest-request adjacent ZIPs, batch them onto existing routes, and re-test margin after {X} weeks of density.",
        expected_effect=f"Annexing the proven adjacent cluster adds ~${X}/mo of routeable {unit}s at near-current drive cost.",
        recommend_when={"state": "adjacent_demand_cluster", "min_signal": "transactions"},
        tags=("growth", "service_area", "expansion", v.family),
    )


# ═══════════════════════ UNTAPPED B2B / WHOLESALE / EVENTS ══════════════════
def _catering_channel_untapped(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You have a kitchen and no catering line — the highest-ticket order you never take",
        observation=f"You run zero catering/large-format orders despite {X} inbound large-quantity asks per month and a menu that travels.",
        reasoning=f"Catering monetizes capacity you already pay for during off-peak prep windows: one order replaces dozens of single {unit}s at a higher margin and lands a repeating B2B relationship, so for a {v.name.lower()} the absence of a catering line is unbooked high-ticket demand, not a missing capability.",
        conclusion=f"Stand up a one-page catering menu with a {X}-hour lead time and minimum, and capture the inbound large-quantity asks you currently turn away.",
        expected_effect=f"A catering line landing even {X} orders/month adds ~${X}/mo at a higher margin than counter {unit}s.",
        recommend_when={"state": "catering_untapped", "min_signal": "transactions"},
        tags=("growth", "catering", "b2b", v.family),
    )


def _wholesale_supply_untapped(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Other businesses could be reselling your product — you have no wholesale line",
        observation=f"You produce {X} {unit}s/day with spare production capacity in off-peak windows and sell {X}% of it retail-only.",
        reasoning=f"A {v.name.lower()} that already makes product at quality can sell it wholesale/white-label to cafes, offices, or grocers using the same production run; wholesale trades a lower unit price for predictable volume that fills idle capacity, turning fixed kitchen/equipment cost into a second revenue stream rather than chasing more retail foot traffic.",
        conclusion=f"Pitch {X} nearby accounts (cafes/offices/grocers) a standing wholesale order at a volume price and produce it inside your existing off-peak prep block.",
        expected_effect=f"A standing wholesale account base fills idle capacity for ~${X}/mo of incremental volume revenue.",
        recommend_when={"state": "wholesale_untapped", "min_signal": "transactions"},
        tags=("growth", "wholesale", "b2b", v.family),
    )


def _corporate_b2b_accounts_untapped(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"No corporate/B2B accounts — you're selling one {unit} at a time to walk-ins only",
        observation=f"Your customer base is {X}% individual consumers with effectively zero recurring corporate/business accounts on file.",
        reasoning=f"A corporate account converts sporadic individual {unit}s into a contracted, repeating relationship (standing orders, employee perks, office accounts) at predictable volume; for a {v.name.lower()} surrounded by local employers, the absence of any B2B book means the most stable demand tier is entirely unworked.",
        conclusion=f"Build a simple business-account offer (billing terms + a volume perk) and approach the {X} largest employers within walking/driving distance.",
        expected_effect=f"A handful of standing corporate accounts adds ~${X}/mo of contracted, repeat {unit} volume.",
        recommend_when={"state": "b2b_accounts_untapped", "min_signal": "transactions"},
        tags=("growth", "b2b", "accounts", v.family),
    )


def _private_event_revenue(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You could host private events — and currently host none",
        observation=f"You field {X} private-party/buyout inquiries a month and convert effectively none into a booked event.",
        reasoning=f"A private event monetizes your space during a controllable window at a guaranteed minimum spend — far above the same hours sold as à la carte {unit}s; for a {v.name.lower()} with an existing room and staff, declining event inquiries leaves the highest-yield use of your floor on the table.",
        conclusion=f"Package a private-event/buyout offer (minimum spend + set menu/service) and respond to inquiries with it within {X} hours instead of an ad-hoc quote.",
        expected_effect=f"Booking even {X} private events/month adds ~${X}/mo at a guaranteed minimum above normal floor yield.",
        recommend_when={"state": "private_events_untapped", "min_signal": "transactions"},
        tags=("growth", "events", "private_event", v.family),
    )


def _corporate_gifting_program(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"No corporate-gifting line — you sell gifts one occasion at a time",
        observation=f"Gift-occasion {unit}s are {X}% of sales but arrive as one-off individual purchases; you run no corporate/bulk-gifting offer.",
        reasoning=f"Corporate gifting converts your existing gift product into bulk, calendar-driven B2B orders (client gifts, staff appreciation, holiday batches) at a higher ticket and a predictable annual cadence; for a {v.name.lower()} already trusted for gifts, the absence of a bulk-gifting program leaves the most repeatable gift demand unbooked.",
        conclusion=f"Create a corporate-gifting sheet (bulk tiers + delivery/branding options) and pitch it to {X} local businesses ahead of the next gifting season.",
        expected_effect=f"A corporate-gifting program adds ~${X}/mo of higher-ticket, calendar-driven {unit}s.",
        recommend_when={"state": "corporate_gifting_untapped", "min_signal": "transactions"},
        tags=("growth", "gifting", "b2b", v.family),
    )


def _recurring_contract_b2b(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You sell one-off jobs but have no recurring commercial contracts",
        observation=f"{X}% of your {unit}s are one-time residential jobs; recurring commercial/maintenance contracts make up effectively none of the book.",
        reasoning=f"A recurring commercial contract converts unpredictable one-off {unit}s into scheduled, route-efficient, prepaid-ish revenue that smooths the calendar; for a {v.name.lower()} with proven crews, the absence of a commercial-contract tier means the most stable, plannable demand is unworked while you re-sell every job from scratch.",
        conclusion=f"Build a commercial maintenance-contract offer (scheduled visits + priority service) and target the {X} nearby properties/businesses that fit your route footprint.",
        expected_effect=f"A base of recurring commercial contracts adds ~${X}/mo of scheduled, route-dense revenue.",
        recommend_when={"state": "recurring_b2b_untapped", "min_signal": "transactions"},
        tags=("growth", "b2b", "recurring", v.family),
    )


# ═══════════════════════ PROGRAM LAUNCHES (negative-space) ══════════════════
def _subscription_program_launch(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = (" A repeat-buyer core is forming on its own — productizing it as a subscription now locks the cadence in."
             if situation == "emerging" else "")
    return Built(
        title=f"Your regulars buy on a rhythm — but you sell no subscription to lock it in",
        observation=f"{X}% of revenue comes from customers who repurchase every {X} days, yet you offer no subscription/auto-replenish option.{extra}",
        reasoning=f"A {v.name.lower()} with a natural repurchase rhythm is leaving recurring revenue uncaptured: a subscription converts a remembered, manual repeat into a default, prepaid one — lifting retention and lifetime value while smoothing demand — and it doesn't exist here yet, so the rhythm runs on the customer's memory instead of your billing.",
        conclusion=f"Productize the most-repeated {unit} into a subscription at a small standing discount and offer it to the {X}% who already buy on cadence.",
        expected_effect=f"Converting even {X}% of rhythm-buyers to a subscription adds ~${X}/mo of recurring, prepaid revenue.",
        recommend_when={"state": "subscription_untapped", "min_signal": "transactions"},
        tags=("growth", "subscription", "recurring", v.family),
    )


def _membership_program_launch(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You have loyal regulars but no membership to formalize them",
        observation=f"Your top {X}% of customers account for {X}% of {unit}s and visit on a tight cadence, yet there's no membership/VIP tier to enroll them in.",
        reasoning=f"A membership turns your most frequent customers into prepaid, committed members with predictable monthly revenue and higher switching cost; for a {v.name.lower()} whose regulars already behave like members, the missing program means you carry the loyalty benefit (frequency) without the loyalty mechanism (commitment + prepayment).",
        conclusion=f"Design a membership tier (monthly fee for priority/perks/included {unit}s) priced off your regulars' actual spend, and invite the top {X}% first.",
        expected_effect=f"A membership enrolling your core regulars adds ~${X}/mo of committed monthly revenue and raises retention.",
        recommend_when={"state": "membership_untapped", "min_signal": "transactions"},
        tags=("growth", "membership", "recurring", v.family),
    )


def _loyalty_program_launch(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"No loyalty program — you have no reason for a one-time buyer to return",
        observation=f"Repeat-customer share is only {X}% and you run no loyalty/rewards mechanism to pull a first visit into a second.",
        reasoning=f"For a {v.name.lower()} where the same customer COULD buy repeatedly, a loyalty program is the cheapest retention lever there is — it converts a satisfied one-time {unit} into a tracked, incentivized habit; its absence means every visit is acquired fresh with nothing engineered to bring the customer back.",
        conclusion=f"Launch a simple earn-and-reward loyalty mechanic tied to your POS and seed it at the point of the first {unit}, then measure second-visit rate.",
        expected_effect=f"Lifting repeat rate by {X}pts via loyalty is worth ~${X}/mo in retained {unit} value.",
        recommend_when={"state": "loyalty_untapped", "min_signal": "transactions"},
        tags=("growth", "loyalty", "retention", v.family),
    )


def _gift_card_program_untapped(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"No gift-card program — free working capital and new customers you don't collect",
        observation=f"You sell no gift cards despite {X} gift-occasion asks a month and a product people give as presents.",
        reasoning=f"Gift cards are prepaid revenue (cash today for a {unit} later, plus typical breakage) AND a new-customer acquisition channel — each card hands your brand to a recipient who may never have visited; for a {v.name.lower()} with giftable product, the missing program forgoes both the float and the referral built into every sale.",
        conclusion=f"Stand up digital + physical gift cards at the counter and online, and merchandise them ahead of the next {X} gift occasions.",
        expected_effect=f"A gift-card program adds ~${X}/mo of prepaid revenue plus new-customer visits from recipients.",
        recommend_when={"state": "gift_card_untapped", "min_signal": "transactions"},
        tags=("growth", "gift_card", "prepaid", v.family),
    )


def _package_bundle_program_launch(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You sell single {unit}s only — no multi-{unit} package to lift commitment",
        observation=f"{X}% of customers buy the same {unit} repeatedly but you offer no prepaid package/series; every purchase is transactional.",
        reasoning=f"A prepaid package (a series of {unit}s sold together) raises average order value, locks in future visits, and improves cash timing — all without acquiring a new customer; for a {v.name.lower()} with a repeatable core {unit}, the absence of any package means you re-sell the same buyer one {unit} at a time.",
        conclusion=f"Bundle the core {unit} into a prepaid {X}-pack at a modest per-{unit} discount and offer it to repeat buyers at checkout.",
        expected_effect=f"A package program lifts average commitment and adds ~${X}/mo of prepaid, locked-in {unit}s.",
        recommend_when={"state": "package_untapped", "min_signal": "transactions"},
        tags=("growth", "bundle", "package", v.family),
    )


def _referral_program_launch(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Word-of-mouth happens by accident — you run no referral program",
        observation=f"An estimated {X}% of new customers already arrive via word-of-mouth, yet there's no mechanism to reward or accelerate it.",
        reasoning=f"For a {v.name.lower()} where trust drives the purchase, referrals are your lowest-cost and highest-converting acquisition source; leaving them unincentivized means you capture only the referrals that happen spontaneously and none of the larger volume a structured give-get would unlock.",
        conclusion=f"Launch a give-get referral offer (reward for both referrer and new customer) and trigger the ask right after a high-satisfaction {unit}.",
        expected_effect=f"A referral program converting existing advocacy adds ~${X}/mo of low-CAC new-customer {unit}s.",
        recommend_when={"state": "referral_untapped", "min_signal": "transactions"},
        tags=("growth", "referral", "acquisition", v.family),
    )


def _premium_tier_launch(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You have no premium tier — every customer buys the same mid {unit}",
        observation=f"Your {unit} mix is {X}% a single mid-tier offering with no good/better/best ladder; willingness-to-pay above it is uncaptured.",
        reasoning=f"A premium tier captures the customers who would happily pay more for a better/faster/included-extras version of the same {unit}; for a {v.name.lower()} with only one tier, that latent high-spend demand has nothing to buy, so you anchor the entire base to the middle and forgo the margin at the top.",
        conclusion=f"Introduce a clearly-differentiated premium tier above the current {unit} (added service, priority, or quality) and present it as the default upgrade.",
        expected_effect=f"A premium tier captured by even {X}% of buyers adds ~${X}/mo of higher-margin {unit} value.",
        recommend_when={"state": "premium_tier_untapped", "min_signal": "transactions"},
        tags=("growth", "premium", "tiering", v.family),
    )


def _preorder_advance_sales_launch(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You sell only what's on hand today — no preorder/advance line",
        observation=f"You run out of {X} popular {unit}s before peak and field {X} 'can you hold one' asks, but take no advance/preorders.",
        reasoning=f"Preorders convert uncertain same-day demand into committed, paid-ahead production — cutting waste on perishables and sellouts on hits; for a {v.name.lower()} that already sells out and gets asked to reserve, the missing preorder line means you guess production instead of building to confirmed orders.",
        conclusion=f"Open advance/preorders for your top {X} sell-out {unit}s with a cutoff time, and build that batch to confirmed orders.",
        expected_effect=f"A preorder line cuts sell-out loss and waste, worth ~${X}/mo on the items that move first.",
        recommend_when={"state": "preorder_untapped", "min_signal": "transactions"},
        tags=("growth", "preorder", "advance_sales", v.family),
    )


# ═══════════════════════ NEW LINES: DAYPART / SERVICE / RETAIL ══════════════
def _new_daypart_launch(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = (" Customers are already showing up at the edge of your hours looking for it — the daypart is forming before you've opened it."
             if situation == "emerging" else "")
    return Built(
        title=f"A whole daypart sits dark — you're open but not selling into it",
        observation=f"Your {X} window produces under {X}% of daily {unit}s and runs no daypart-specific offer (e.g. breakfast/late-night), while nearby demand for it exists.{extra}",
        reasoning=f"Launching a daypart leverages rent, equipment, and a partly-staffed floor you already pay for during a low-yield window; for a {v.name.lower()}, a purpose-built menu/offer for that slot can turn near-fixed cost into incremental {unit}s without a new location — the slot is open, it just has nothing to sell.",
        conclusion=f"Pilot a focused daypart offer for the {X} window (tight menu, one promo) for {X} weeks and measure incremental {unit}s against the dark baseline.",
        expected_effect=f"A working new daypart converts paid-for dead hours into ~${X}/mo of incremental {unit}s.",
        recommend_when={"state": "daypart_untapped", "min_signal": "hourly_revenue"},
        tags=("growth", "daypart", "new_line", v.family),
    )


def _new_service_line_adjacent(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"There's an adjacent service your customers ask for and you don't offer",
        observation=f"{X} customers a month request an adjacent service you currently refer out or decline, with no in-house line to capture it.",
        reasoning=f"An adjacent service line uses the same customers, space, and {v.staff_role} skill base to capture demand you're already generating but handing to someone else; for a {v.name.lower()}, the asked-for-but-referred-out volume is the cheapest expansion there is because acquisition is already done — the customer is in the chair.",
        conclusion=f"Add the single most-requested adjacent service in-house (or via a resident specialist) and offer it to the customers already asking.",
        expected_effect=f"Capturing the referred-out adjacent demand adds ~${X}/mo at near-zero incremental acquisition cost.",
        recommend_when={"state": "adjacent_service_untapped", "min_signal": "transactions"},
        tags=("growth", "service_line", "new_line", v.family),
    )


def _retail_product_line_addition(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You perform a service but sell no take-home product",
        observation=f"You run effectively zero retail attach — under {X}% of {unit}s carry a take-home product — so customers leave with the service done but nothing to use at home.",
        reasoning=f"A service customer in your chair has already paid for your expertise and trusts your recommendation, which makes the end of a {unit} the highest-converting retail moment there is; for a {v.name.lower()} with no retail line, that high-trust window leaks margin every visit because nothing is on the shelf to attach.",
        conclusion=f"Curate a tight retail shelf of products that extend the {unit} result and have the {v.staff_role} recommend one at the end of each service.",
        expected_effect=f"A retail attach line adds ~${X}/mo at retail margin off visits you're already serving.",
        recommend_when={"state": "retail_line_untapped", "min_signal": "transactions"},
        tags=("growth", "retail", "attach", v.family),
    )


def _workshop_class_revenue_line(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your expertise could be sold as a class — and currently isn't",
        observation=f"You have product, space, and skill but run no paid workshops/classes; your only revenue line is the {unit} itself.",
        reasoning=f"A workshop monetizes the same expertise and space during off-peak hours at a per-seat ticket, AND doubles as marketing that pulls new customers into your {unit} funnel; for a {v.name.lower()} with a teachable craft, the absence of a class line leaves a high-margin, low-incremental-cost use of slow hours unworked.",
        conclusion=f"Pilot a single ticketed workshop in an off-peak slot (cap the seats, use existing space/stock) and measure ticket revenue plus downstream {unit}s from attendees.",
        expected_effect=f"A recurring workshop line adds ~${X}/mo of per-seat revenue plus new-customer pull-through.",
        recommend_when={"state": "workshop_untapped", "min_signal": "transactions"},
        tags=("growth", "workshop", "new_line", v.family),
    )


def _branded_merch_line(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your regulars would wear your brand — you sell no merch",
        observation=f"You have a loyal, identity-driven customer base and {X} brand mentions/tags a month, but no branded-merchandise line.",
        reasoning=f"For a {v.name.lower()} where customers identify with the brand, merch is both a retail-margin product and walking advertising; loyal regulars want to display the affiliation, so the missing line forgoes high-margin sales AND the organic reach each branded item generates.",
        conclusion=f"Launch a small branded-merch run (the {X} items your community would actually wear/use) and sell it at the counter and online.",
        expected_effect=f"A branded-merch line adds ~${X}/mo at retail margin plus organic brand reach from every item sold.",
        recommend_when={"state": "merch_untapped", "min_signal": "transactions"},
        tags=("growth", "merch", "retail", v.family),
    )


def _private_label_launch(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You resell everyone else's brands — none of them are yours",
        observation=f"100% of your assortment is third-party brands; your top category moves {X} {unit}s/week with no private-label equivalent.",
        reasoning=f"A private-label product in a high-volume category captures the margin you currently hand to suppliers and builds an asset only your store carries; for a {v.name.lower()} with proven category velocity, the absence of any owned label means your best-selling shelf space earns only distributor margin.",
        conclusion=f"Introduce a private-label SKU in your highest-velocity, lowest-loyalty category and merchandise it beside the national brand to test trade-in.",
        expected_effect=f"A private-label line in your top category lifts category margin by ~${X}/mo on existing volume.",
        recommend_when={"state": "private_label_untapped", "min_signal": "transactions"},
        tags=("growth", "private_label", "retail", v.family),
    )


def _mobile_service_expansion(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You're location-bound — a mobile/pop-up line could meet customers off-site",
        observation=f"You serve {unit}s only at your fixed location and field {X} requests a month for on-site/at-home/event service you can't fulfill.",
        reasoning=f"A mobile or pop-up extension takes your proven {unit} to demand that won't or can't come to you (events, offices, neighborhoods you don't draw from) using existing staff on otherwise-idle hours; for a {v.name.lower()}, the off-site asks you decline are demand your fixed footprint structurally can't reach.",
        conclusion=f"Pilot a mobile/pop-up offering for the most-requested off-site occasion and book it into low-utilization hours before adding dedicated capacity.",
        expected_effect=f"A mobile/pop-up line captures off-site demand worth ~${X}/mo without enlarging the fixed site.",
        recommend_when={"state": "mobile_untapped", "min_signal": "transactions"},
        tags=("growth", "mobile", "new_line", v.family),
    )


# ═══════════════════════ CHANNEL LAUNCHES (negative-space) ══════════════════
def _online_ordering_launch(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = (" Customers are increasingly calling to ask for online ordering — the demand for the channel is surfacing before you've built it."
             if situation == "emerging" else "")
    return Built(
        title=f"You have no online ordering — every {unit} requires a call or a visit",
        observation=f"Your channels are {X} (none online): customers can't place a {unit} digitally, and you field {X} 'do you have online ordering' asks a month.{extra}",
        reasoning=f"An online ordering channel captures the buyer who won't call and won't wait on hold — it sells while you're busy or closed and lifts average ticket via unhurried browsing; for a {v.name.lower()} with no digital order path, that entire convenience-driven demand segment has no way to buy from you.",
        conclusion=f"Stand up a simple online ordering page for your top {X} {unit}s (own-site or one platform) and route it to the same prep flow.",
        expected_effect=f"An online ordering channel adds ~${X}/mo of incremental, often higher-ticket {unit}s from buyers who skip the phone.",
        recommend_when={"state": "online_channel_untapped", "min_signal": "transactions"},
        tags=("growth", "online", "channel_launch", v.family),
    )


def _ecommerce_shipping_launch(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You sell to walk-ins only — no shippable e-commerce storefront",
        observation=f"Your sales are {X}% in-store with no ship-to-customer e-commerce line, despite a product that travels and {X} out-of-area inquiries a month.",
        reasoning=f"For a {v.name.lower()} with shippable, non-perishable goods, an e-commerce storefront breaks the geographic ceiling entirely — the same inventory serves customers far outside your trade area; the missing channel caps your addressable market at walk-in radius even though the product could sell nationwide.",
        conclusion=f"Launch a shippable storefront for your most travel-friendly, highest-margin SKUs and fulfill from existing stock before scaling the catalog.",
        expected_effect=f"A shippable e-commerce line adds ~${X}/mo of out-of-area demand off existing inventory.",
        recommend_when={"state": "ecommerce_untapped", "min_signal": "transactions"},
        tags=("growth", "ecommerce", "channel_launch", v.family),
    )


def _seasonal_popup_opportunity(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"A predictable seasonal spike comes and goes without a dedicated push",
        observation=f"Your {X} season drives a {X}% demand swing every year, but you run the same baseline format through it with no seasonal pop-up/line.",
        reasoning=f"A predictable seasonal surge is a standing, pre-qualified demand window; for a {v.name.lower()}, meeting it with a purpose-built pop-up, limited line, or temporary capacity captures spike spend that a baseline format under-serves — the demand is calendar-certain, only the dedicated offer is missing.",
        conclusion=f"Build a seasonal pop-up/limited line scoped to the {X} window (special menu, kit, or capacity add) and pre-sell it before the season opens.",
        expected_effect=f"A dedicated seasonal line captures spike demand worth ~${X} per season above the baseline format.",
        recommend_when={"state": "seasonal_popup_untapped", "min_signal": "transactions"},
        tags=("growth", "seasonal", "popup", v.family),
    )


# ═══════════════════════ NEW LINES: HOURS / ASSETS / PARTNERSHIPS ═══════════
def _closed_window_launch(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = (" Customers are already trying the door and calling during the closed window — the demand is arriving before the line exists."
             if situation == "emerging" else "")
    return Built(
        title=f"You're closed during a window customers keep asking for",
        observation=f"You field {X} requests a month during the {X} hours/day you're shut, and nearby peers who open then capture {X}% more weekly {unit}s.{extra}",
        reasoning=f"Opening a currently-closed window is nearly pure incremental revenue, because the rent and equipment are already paid year-round, so the only added cost is variable {v.staff_role} hours while the demand already shows up at a locked door — unlike a slow daypart, here you capture nothing at all today.",
        conclusion=f"Pilot opening the most-requested closed window for {X} weeks with a lean {v.staff_role} crew, and measure incremental {unit}s against the closed baseline before making it permanent.",
        expected_effect=f"A proven new open-window converts fixed overhead into ~${X}/mo of incremental {unit}s.",
        recommend_when={"state": "closed_window_untapped", "min_signal": "phone_call_logs"},
        tags=("growth", "hours", "new_line", v.family),
    )


def _space_equipment_rental_untapped(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    fam = v.family.replace("_", " ")
    return Built(
        title=f"Your space and equipment sit idle — you could rent them out",
        observation=f"Your {fam} space/equipment runs at {X}% utilization, idle for {X}+ hours a week with no rental income.",
        reasoning=f"Idle space and equipment are fixed costs earning nothing in the gaps, because you pay rent and depreciation whether or not they're in use, so renting them out in off-hours converts dead overhead into a near-pure-margin second income with no new asset purchase.",
        conclusion=f"Rent the idle {fam} space or equipment by the hour/session to vetted users in your off-peak windows, and set a rate that covers variable cost plus margin.",
        expected_effect=f"Renting idle capacity even {X} hours/week adds ~${X}/mo at near-pure margin.",
        recommend_when={"state": "rental_capacity_untapped", "min_signal": "schedule_shifts"},
        tags=("growth", "rental", "new_line", v.family),
    )


def _local_partnership_bundle(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"No co-marketed bundle with a neighboring business — shared customers, zero shared offer",
        observation=f"You share a customer base with {X} adjacent local businesses but run no joint bundle or cross-referral, capturing {X}% of the obvious overlap.",
        reasoning=f"A partnership bundle pools two trusted brands to reach each other's customers at zero ad cost, because each business vouches for the other to an already-warm audience, so a co-offer converts far better than cold acquisition while the two split the cost of promotion.",
        conclusion=f"Build a co-marketed bundle with one complementary nearby business — a paired {unit}-plus-their-service offer and a two-way referral — and split the promotion at the point of sale.",
        expected_effect=f"A single local partnership bundle adds ~${X}/mo of cross-referred {unit}s at near-zero acquisition cost.",
        recommend_when={"state": "partnership_bundle_untapped", "min_signal": "transactions"},
        tags=("growth", "partnership", "bundle", v.family),
    )


# ═══════════════════════ REGISTER ═══════════════════════════════════════════
_FOOD = ("food_service",)

_READINESS_UP = "ExpansionReadinessAgent: fuse hourly_revenue + schedule_shifts + transactions into a sustained capacity-utilization-vs-demand signal; the per-period utilization ceiling and turn-away estimate are not computed today."
_PEER_UP = "PeerBenchmarkAgent: compare this merchant's line presence/metrics against an anonymized cohort of same-vertical peers WITH the line; no peer-benchmark corpus is ingested yet."
_CHANNELBM_UP = "ChannelBenchmarkAgent: size untapped-channel demand from inbound asks (phone_call_logs/transcripts) + peer channel adoption; ask-mining and channel benchmarks are not built yet."

register(
    # ── Expansion readiness ──
    Archetype(
        key="second_location_readiness", domain="growth", name="Second-location readiness",
        build=_second_location_readiness, situations=("untapped", "emerging"),
        required_signals=("hourly_revenue", "schedule_shifts", "transactions"),
        required_agents=("ExpansionReadinessAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade=_READINESS_UP,
    ),
    Archetype(
        key="capacity_expansion_turnaways", domain="growth", name="Capacity expansion (turn-aways)",
        build=_capacity_expansion_turnaways, situations=("untapped",),
        required_signals=("hourly_revenue", "schedule_shifts"),
        required_agents=("ExpansionReadinessAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade=_READINESS_UP + " Turn-away counting additionally needs queue/booking-decline capture not yet ingested for all verticals.",
        applies_keys=_keys_with_any_flag("appointment_based", "table_service", "walk_in_heavy"),
    ),
    Archetype(
        key="franchise_multiunit_benchmark_gap", domain="growth", name="Multi-unit benchmark gap",
        build=_franchise_multiunit_benchmark_gap, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("PeerBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_PEER_UP,
    ),
    Archetype(
        key="delivery_expansion_readiness", domain="growth", name="Delivery-expansion readiness",
        build=_delivery_expansion_readiness, situations=("untapped", "emerging"),
        required_signals=("phone_call_logs", "transactions"),
        required_agents=("ChannelBenchmarkAgent", "PhoneInsightAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_CHANNELBM_UP + " Delivery-ask detection requires transcript intent classification.",
        applies_keys=tuple(set(_keys_with_any_flag("delivery_capable")) & set(_keys_lacking_channel("delivery"))),
    ),
    Archetype(
        key="service_area_geographic_expansion", domain="growth", name="Service-area expansion",
        build=_service_area_geographic_expansion, situations=("untapped", "emerging"),
        required_signals=("transactions",),
        required_agents=("ExpansionReadinessAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="GeoDemandAgent: cluster declined/out-of-area job requests by ZIP against current service boundary; out-of-area request capture is not ingested today.",
        applies_families=("home_services",),
    ),
    # ── Untapped B2B / wholesale / events ──
    Archetype(
        key="catering_channel_untapped", domain="growth", name="Catering line untapped",
        build=_catering_channel_untapped, situations=("untapped", "emerging"),
        required_signals=("transactions", "phone_call_logs"),
        required_agents=("ChannelBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_CHANNELBM_UP + " Large-order ask detection needs transcript/quantity mining.",
        applies_families=_FOOD,
    ),
    Archetype(
        key="wholesale_supply_untapped", domain="growth", name="Wholesale line untapped",
        build=_wholesale_supply_untapped, situations=("untapped",),
        required_signals=("transactions", "schedule_shifts"),
        required_agents=("ExpansionReadinessAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_READINESS_UP + " Wholesale fit additionally needs spare-production-capacity estimation from prep/throughput data.",
        applies_keys=("bakery", "cafe", "ghost_kitchen", "qsr", "food_truck"),
    ),
    Archetype(
        key="corporate_b2b_accounts_untapped", domain="growth", name="Corporate accounts untapped",
        build=_corporate_b2b_accounts_untapped, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("PeerBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="B2BAccountAgent: classify customers as individual vs business from transaction patterns to size the missing corporate book; no account-type signal exists today.",
        applies_families=("food_service", "personal_care", "retail"),
    ),
    Archetype(
        key="private_event_revenue", domain="growth", name="Private-event revenue untapped",
        build=_private_event_revenue, situations=("untapped",),
        required_signals=("transactions", "phone_call_logs"),
        required_agents=("ChannelBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_CHANNELBM_UP + " Buyout/party inquiry detection needs transcript intent mining.",
        applies_keys=("full_restaurant", "bar", "entertainment", "spa", "salon", "hotel_fb"),
    ),
    Archetype(
        key="corporate_gifting_program", domain="growth", name="Corporate-gifting untapped",
        build=_corporate_gifting_program, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("ChannelBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="GiftOccasionAgent: detect gift-occasion purchases and bulk-gift potential from basket/seasonality; gift-vs-self classification is not built yet.",
        applies_keys=("florist", "jewelry", "spa", "med_spa", "bakery", "bookstore"),
    ),
    Archetype(
        key="recurring_contract_b2b", domain="growth", name="Recurring commercial contracts untapped",
        build=_recurring_contract_b2b, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("B2BAccountAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="B2BAccountAgent: separate one-off residential from recurring commercial jobs to size the missing contract tier; job-type classification is not ingested today.",
        applies_families=("home_services",),
    ),
    # ── Program launches (negative-space) ──
    Archetype(
        key="subscription_program_launch", domain="growth", name="Subscription launch (no membership)",
        build=_subscription_program_launch, situations=("untapped", "emerging"),
        required_signals=("transactions",),
        required_agents=("LifecycleAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="LifecycleAgent: detect per-customer repurchase cadence from transactions to identify subscription-ready rhythm buyers; cadence modeling exists partially for some POS feeds.",
        applies_keys=_keys_without_flag("membership"),
    ),
    Archetype(
        key="membership_program_launch", domain="growth", name="Membership launch",
        build=_membership_program_launch, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("LifecycleAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="LifecycleAgent: rank top-frequency customers and their cadence/spend to size a membership tier; frequency cohorting is partially available.",
        applies_keys=_keys_with_any_flag("appointment_based", "repeat_purchase"),
        exclude_keys=_keys_with_any_flag("membership"),
    ),
    Archetype(
        key="loyalty_program_launch", domain="growth", name="Loyalty launch (low repeat)",
        build=_loyalty_program_launch, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("LifecycleAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="LifecycleAgent: compute repeat-customer share to confirm the retention gap a loyalty program would close; requires stable customer identity across transactions.",
        applies_keys=_keys_without_flag("repeat_purchase", "membership"),
    ),
    Archetype(
        key="gift_card_program_untapped", domain="growth", name="Gift-card program untapped",
        build=_gift_card_program_untapped, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("ChannelBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="GiftOccasionAgent: confirm absence of gift-card sales in the POS feed and size gift-occasion demand; gift-card SKU detection is not normalized across POS today.",
        applies_families=("food_service", "retail", "personal_care", "health_wellness", "fitness", "hospitality"),
    ),
    Archetype(
        key="package_bundle_program_launch", domain="growth", name="Prepaid package launch",
        build=_package_bundle_program_launch, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("LifecycleAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="LifecycleAgent: identify repeated single-item buyers who would convert to a prepaid series; repeat-SKU cohorting is partially available.",
        applies_keys=_keys_with_any_flag("appointment_based", "repeat_purchase"),
    ),
    Archetype(
        key="referral_program_launch", domain="growth", name="Referral program launch",
        build=_referral_program_launch, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("AttributionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="AttributionAgent: estimate word-of-mouth share of new customers (source attribution) to size referral upside; acquisition-source capture does not exist today.",
        applies_keys=_keys_with_any_flag("high_ticket", "appointment_based", "membership"),
    ),
    Archetype(
        key="premium_tier_launch", domain="growth", name="Premium-tier launch",
        build=_premium_tier_launch, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("PeerBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="TierGapAgent: detect a single-tier offering and estimate untapped willingness-to-pay above it; price-ladder analysis is not built yet.",
        applies_keys=_keys_without_flag("high_ticket"),
    ),
    Archetype(
        key="preorder_advance_sales_launch", domain="growth", name="Preorder/advance-sales launch",
        build=_preorder_advance_sales_launch, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("ExpansionReadinessAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="SelloutAgent: detect items that sell out before peak and reserve-ask volume to size preorder demand; sellout/stockout timing is not captured for all POS feeds.",
        applies_keys=_keys_with_any_flag("perishable", "seasonal"),
    ),
    # ── New lines: daypart / service / retail ──
    Archetype(
        key="new_daypart_launch", domain="growth", name="New-daypart launch",
        build=_new_daypart_launch, situations=("untapped", "emerging"),
        required_signals=("hourly_revenue",),
        required_agents=("PatternAnalyzer", "ExpansionReadinessAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ExpansionReadinessAgent: flag low-yield open windows that could host a new daypart and compare to local daypart demand; the peer daypart benchmark is not ingested.",
        applies_families=_FOOD,
    ),
    Archetype(
        key="new_service_line_adjacent", domain="growth", name="Adjacent service line",
        build=_new_service_line_adjacent, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("ChannelBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="AdjacencyAgent: mine referred-out/declined requests for the most-asked adjacent service; referral-out and decline capture is not ingested today.",
        applies_families=("personal_care", "health_wellness", "automotive", "home_services"),
    ),
    Archetype(
        key="retail_product_line_addition", domain="growth", name="Retail attach line (service verticals)",
        build=_retail_product_line_addition, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("PeerBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="RetailAttachAgent: confirm near-zero retail attach and benchmark against peers who retail; service-vs-retail line classification is not built yet.",
        applies_families=("personal_care", "health_wellness", "fitness"),
        exclude_keys=_keys_with_any_flag("inventory_heavy"),
    ),
    Archetype(
        key="workshop_class_revenue_line", domain="growth", name="Workshop/class line",
        build=_workshop_class_revenue_line, situations=("untapped",),
        required_signals=("transactions", "hourly_revenue"),
        required_agents=("ExpansionReadinessAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ExpansionReadinessAgent: identify off-peak windows that could host ticketed workshops; class-revenue modeling is not built yet.",
        applies_keys=("florist", "bakery", "cafe", "salon", "nail_salon", "yoga_studio", "bookstore", "pet_store"),
    ),
    Archetype(
        key="branded_merch_line", domain="growth", name="Branded-merch line",
        build=_branded_merch_line, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("PeerBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="BrandAffinityAgent: estimate brand-identification (mentions/tags + loyalty) to size merch demand; social/mention ingest does not exist today.",
        applies_keys=("gym", "crossfit", "yoga_studio", "entertainment", "cafe", "bar", "tattoo"),
    ),
    Archetype(
        key="private_label_launch", domain="growth", name="Private-label launch (retail)",
        build=_private_label_launch, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("PeerBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CategoryVelocityAgent: rank category velocity vs brand loyalty to pick the private-label entry point; brand-loyalty signal per category is not ingested.",
        applies_families=("retail",),
    ),
    Archetype(
        key="mobile_service_expansion", domain="growth", name="Mobile/pop-up line",
        build=_mobile_service_expansion, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("ChannelBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="AdjacencyAgent: mine off-site/at-home/event service requests the fixed site declines; off-site request capture is not ingested.",
        applies_keys=("salon", "barbershop", "nail_salon", "spa", "car_wash"),
    ),
    # ── Channel launches (negative-space) ──
    Archetype(
        key="online_ordering_launch", domain="growth", name="Online-ordering launch (no online channel)",
        build=_online_ordering_launch, situations=("untapped", "emerging"),
        required_signals=("transactions", "phone_call_logs"),
        required_agents=("ChannelBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_CHANNELBM_UP + " 'Do you have online ordering' ask detection needs transcript mining.",
        applies_keys=tuple(set(_keys_lacking_channel("online")) & set(
            _keys_with_any_flag("perishable", "inventory_heavy", "repeat_purchase"))),
    ),
    Archetype(
        key="ecommerce_shipping_launch", domain="growth", name="E-commerce shipping launch",
        build=_ecommerce_shipping_launch, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("ChannelBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_CHANNELBM_UP + " Out-of-area inquiry sizing needs source/geo capture not ingested today.",
        applies_keys=tuple(set(_keys_lacking_channel("online")) & set(_keys_with_any_flag("inventory_heavy"))
                           - set(_keys_with_any_flag("perishable", "regulated"))),
    ),
    Archetype(
        key="seasonal_popup_opportunity", domain="growth", name="Seasonal pop-up line",
        build=_seasonal_popup_opportunity, situations=("untapped", "seasonal_peak"),
        required_signals=("transactions",),
        required_agents=("PatternAnalyzer",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PatternAnalyzer: quantify the recurring seasonal swing from transaction history to scope a dedicated seasonal line; baseline-vs-season decomposition is partially available.",
        applies_keys=_keys_with_any_flag("seasonal"),
    ),
    # ── New lines: hours / assets / partnerships ──
    Archetype(
        key="closed_window_launch", domain="growth", name="Closed-window launch",
        build=_closed_window_launch, situations=("untapped", "emerging"),
        required_signals=("hourly_revenue", "phone_call_logs"),
        required_agents=("ChannelBenchmarkAgent", "ExpansionReadinessAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_CHANNELBM_UP + " Closed-window ask detection needs inbound-request capture during non-open hours, plus a peer open-hours benchmark not ingested today.",
        applies_families=("food_service", "personal_care", "health_wellness", "retail", "automotive"),
    ),
    Archetype(
        key="space_equipment_rental_untapped", domain="growth", name="Idle space/equipment rental",
        build=_space_equipment_rental_untapped, situations=("untapped",),
        required_signals=("schedule_shifts", "transactions"),
        required_agents=("ExpansionReadinessAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_READINESS_UP + " Rental fit additionally needs an idle-asset/idle-space utilization estimate from schedule + capacity data not computed today.",
        applies_families=("personal_care", "health_wellness", "fitness", "food_service"),
    ),
    Archetype(
        key="local_partnership_bundle", domain="growth", name="Local partnership bundle",
        build=_local_partnership_bundle, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("PeerBenchmarkAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_PEER_UP + " Co-marketing fit additionally needs nearby-business adjacency + shared-audience estimation not ingested today.",
    ),
)
