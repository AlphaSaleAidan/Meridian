"""
Domain: FOOTFALL / IN-STORE VISION.

Each archetype is a distinct reasoning pattern about what the camera/vision
pipeline sees on the floor that the point-of-sale alone can't: people who enter
but don't buy, where they go, how long they linger, how long they wait, and who
they are. Specialization per vertical changes the lever (fitting-room funnel for
a boutique; queue balk for a quick-lube; chair-side dwell for a barbershop), so a
café footfall insight and a boutique footfall insight are genuinely different,
not relabeled.

These only apply where there is physical walk-in traffic to see, so every
archetype targets the families with a sales floor (food_service, retail,
personal_care, automotive, fitness) and/or the walk_in_heavy flag, and excludes
ghost_kitchen (no customers ever enter it).

Honesty about the swarm: the conversion/occupancy/queue numbers come from the
vision_traffic feed that already exists in PARTIAL form, but anything that needs
per-zone, per-visit, demographic, or re-identification understanding is MISSING
until the named vision agent is built.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register

# Families that have a physical sales floor a camera can watch.
FOOT_FAMILIES = ("food_service", "retail", "personal_care", "automotive", "fitness")
NO_GHOST = ("ghost_kitchen",)


# ── 1. Entries >> sales ───────────────────────────────────────────────────
def _conversion_gap(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "declining": " The gap is widening week over week — a conversion problem that is getting worse, not a one-off.",
        "emerging": " A newly-rising traffic source is padding entries without buying; qualify it before scaling spend on it.",
    }.get(situation, "")
    return Built(
        title=f"You draw the traffic but lose the sale — {X}% of entrants leave without buying",
        observation=f"Vision counts {X} entries/day but only {X} convert to a {unit} — a {X}% conversion rate against a {v.family} norm near {X}%.",
        reasoning=f"Every entrant is demand you already paid for in rent, location, and marketing; an entry that walks out empty is sunk cost, so the gap between traffic and {unit}s is your single largest recoverable line — bigger than squeezing the customers who already buy.{extra}",
        conclusion=f"Set a {unit}s-per-100-entries conversion target instead of an entry-count goal, add a floor-engagement play at the door, and flag any hour that falls below the target.",
        expected_effect=f"Closing the entry-to-{unit} gap by even {X}pts is worth ~${X}/mo on traffic you already have.",
        recommend_when={"state": "high_traffic_low_conversion", "min_signal": "vision_traffic"},
        tags=("footfall", "conversion", v.family),
    )


# ── 2. Short dwell — moving through, not shopping ──────────────────────────
def _dwell_low(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Shoppers pass through in {X}s — too fast to buy",
        observation=f"Median in-store dwell is {X} seconds; converting visits dwell {X}x longer than non-converting ones.",
        reasoning=f"For {v.name}, the {unit} decision needs consideration time — browsing the assortment, reading a board, being approached. Sub-threshold dwell means visitors never reach the consideration depth where a purchase forms, so they were never given the chance to convert.",
        conclusion=f"Slow the path: reposition a draw item deeper in, add a decision aid at {X}, or have a {v.staff_role} intercept before the {X}-second mark.",
        expected_effect=f"Lifting median dwell past the conversion threshold typically moves conversion {X}pts (~${X}/mo).",
        recommend_when={"state": "low_dwell_browse_only", "min_signal": "vision_visits"},
        tags=("footfall", "dwell", v.family),
    )


# ── 3. Queue abandonment (in-line balk) ───────────────────────────────────
def _queue_abandonment(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = " During the seasonal rush this balk rate compounds — protect the line before peak, not during." if situation == "seasonal_peak" else ""
    return Built(
        title=f"Customers join the line then leave it — {X} balks/day",
        observation=f"Average queue wait hits {X}s at peak; vision sees {X} customers join the line and exit before reaching the {v.staff_role}.",
        reasoning=f"A balk is the most expensive kind of lost sale: this visitor already chose to buy and physically committed to the line, so each one is a near-certain {unit} lost, not a maybe. Wait tolerance is a cliff — once it's crossed, abandonment spikes nonlinearly.{extra}",
        conclusion=f"Cap peak wait below the balk threshold: open a second point during the {X} window or pull a {v.staff_role} to expedite when the line passes {X} deep.",
        expected_effect=f"Recovering balked {unit}s is worth ~${X}/mo at your average ticket.",
        recommend_when={"state": "queue_balk_at_peak", "min_signal": "vision_traffic"},
        tags=("footfall", "queue", v.family),
    )


# ── 4. Dead zone — traffic in, no sales out ───────────────────────────────
def _dead_zone(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"A zone gets {X}% of your traffic and {X}% of your sales",
        observation=f"Vision routes {X}% of in-store movement through one zone, but POS attributes only {X}% of {v.sale_unit}s to the products shelved there.",
        reasoning=f"Footage and the foot traffic flowing to it both cost money; a zone that pulls shoppers but converts none of them is dead capital — the assortment, signage, price, or adjacency there is wrong, and the traffic proves it's not a discoverability problem.",
        conclusion=f"Re-merchandise that zone (swap in a proven category, add a {v.staff_role} touchpoint, or re-price) and re-measure its sales share in {X} weeks.",
        expected_effect=f"Bringing the dead zone to even half the store's average sales-per-visit is worth ~${X}/mo.",
        recommend_when={"state": "zone_traffic_without_sales", "min_signal": "zone_purchase_correlation"},
        tags=("footfall", "zone", "merchandising", v.family),
    )


# ── 5. Capture rate vs passersby ──────────────────────────────────────────
def _capture_rate(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Only {X}% of passersby come in",
        observation=f"Exterior vision counts {X} passersby/day; door entries are {X} — a {X}% capture rate.",
        reasoning=f"Capture rate sits upstream of every in-store number: dwell, conversion, and basket all multiply against entries, so a low capture rate caps total revenue no matter how good the floor is. For {v.name} on a {v.channels[0]} footing, the storefront is the funnel's mouth and it's the cheapest place to win volume.",
        conclusion=f"Treat the threshold as a conversion surface: test an A-frame/offer at the door, open sightlines, or a greeter during the {X} pass-by peak.",
        expected_effect=f"Each +1pt of capture adds ~{X} entries/day — ~${X}/mo at current conversion.",
        recommend_when={"state": "low_storefront_capture", "min_signal": "vision_traffic"},
        tags=("footfall", "capture", "storefront", v.family),
    )


# ── 6. Peak occupancy vs comfortable capacity ─────────────────────────────
def _peak_occupancy(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"At peak you're at {X}% of comfortable capacity — and conversion drops",
        observation=f"Occupancy hits {X} people against a comfortable cap of {X} between {X} and {X}; conversion in that window runs {X}pts below your daypart average.",
        reasoning=f"Past a density threshold the experience degrades — crowding, no room to browse, no {v.staff_role} free to help — and conversion falls even as the room fills. So your busiest minutes are also your least efficient: more bodies, fewer {unit}s per body.",
        conclusion=f"Relieve density at peak (faster throughput, a second service point, or flow control) rather than chasing more entries into an already-full room.",
        expected_effect=f"Restoring peak conversion to the daypart average recovers ~${X}/mo without a single extra entrant.",
        recommend_when={"state": "peak_density_conversion_drop", "min_signal": "vision_traffic"},
        tags=("footfall", "occupancy", "capacity", v.family),
    )


# ── 7. Browse → fitting room (apparel) ────────────────────────────────────
def _browse_to_fitting(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Shoppers browse but don't try on — only {X}% reach a fitting room",
        observation=f"Vision sees {X}% of floor browsers carry items toward the fitting rooms; the rest put them back or leave.",
        reasoning=f"In apparel, fitting-room entry is the single strongest pre-purchase signal — try-on converts several times the floor-only rate. The funnel is leaking before its highest-converting step, so the bottleneck is getting garments onto bodies, not getting bodies into the store.",
        conclusion=f"Lower the try-on barrier: a {v.staff_role} offering to start a room, clear room availability signage, and a 'grab one more' prompt at the rack.",
        expected_effect=f"Each +1pt of browse-to-try-on flows downstream to ~${X}/mo given try-on conversion economics.",
        recommend_when={"state": "fitting_room_underused", "min_signal": "vision_visits"},
        tags=("footfall", "fitting_room", "funnel", v.family),
        # boutique-only via applies_keys
    )


# ── 8. Fitting room → purchase (apparel) ──────────────────────────────────
def _fitting_to_purchase(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Try-on doesn't close — {X}% of fitting-room visits buy",
        observation=f"Of {X} fitting-room sessions/day, only {X}% end in a {v.sale_unit}.",
        reasoning=f"A fitting-room visitor is your highest-intent shopper — they've selected, carried, and tried on. A weak try-on-to-purchase rate means fit, price, or an unattended room is killing customers at the very last step, after every prior cost to acquire and convince them has already been spent.",
        conclusion=f"Staff the rooms: a {v.staff_role} checking in for sizes/alternatives, plus a frictionless price/checkout path from the room.",
        expected_effect=f"Lifting try-on close by {X}pts captures ~${X}/mo from shoppers already committed enough to undress.",
        recommend_when={"state": "fitting_room_low_close", "min_signal": "vision_visits"},
        tags=("footfall", "fitting_room", "conversion", v.family),
    )


# ── 9. Demographic mix vs product mix ─────────────────────────────────────
def _demographic_mix(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You're attracting one crowd and merchandising for another",
        observation=f"Vision demographics skew {X}% toward the {X} segment, but {X}% of floor space and the {v.core_kpis[0]} push serves a different segment.",
        reasoning=f"Traffic and inventory are pulling in opposite directions: the people who actually walk in don't see themselves in the assortment up front, so they under-convert while the merchandised-for segment never arrives. This is a matching problem invisible to POS — it only shows when you can see who's in the room.",
        conclusion=f"Re-weight front-of-store and {v.staff_role} attention toward the segment that's actually walking in for {X} weeks and measure conversion by segment.",
        expected_effect=f"Aligning merchandising to real visitor mix is worth ~${X}/mo in better-matched conversion.",
        recommend_when={"state": "demographic_product_mismatch", "min_signal": "vision_visits"},
        tags=("footfall", "demographics", "merchandising", v.family),
    )


# ── 10. Repeat-visitor share (vision re-ID) ───────────────────────────────
def _repeat_visitor(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"{X}% of visits are regulars who don't buy",
        observation=f"Vision re-identifies {X}% of daily visits as repeat faces; of those repeats, {X}% transact on a given visit.",
        reasoning=f"A recognized regular who browses without buying is a fundamentally different opportunity than one-time foot traffic: they've already chosen to keep coming back, so the relationship exists and only the {unit} is missing. Converting an existing repeat browser is far cheaper than capturing a new stranger.",
        conclusion=f"Give the {v.staff_role} a 'welcome back' cue for recognized repeats and a standing reason-to-buy (members' price, a held item) aimed at frequent non-buyers.",
        expected_effect=f"Converting even {X}% of repeat browsers/wk is worth ~${X}/mo from people already loyal with their feet.",
        recommend_when={"state": "repeat_browsers_not_buying", "min_signal": "vision_visits"},
        tags=("footfall", "repeat_visitor", "loyalty", v.family),
    )


# ── 11. Entrance vs back-of-store penetration ─────────────────────────────
def _penetration_depth(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Only {X}% of entrants reach the back of the store",
        observation=f"Vision shows {X}% of entrants never pass the front third; the back zones see {X}% of total movement.",
        reasoning=f"Penetration depth caps basket size — the deeper, often higher-margin zones simply never get seen, so layout and sightlines (not assortment) are leaving money on the back wall. A shopper can't buy what their feet never reach.",
        conclusion=f"Pull traffic deeper: place a known draw at the back, open a clear sightline/aisle from the door, and route the {v.staff_role} hand-off toward the rear.",
        expected_effect=f"Raising back-zone penetration {X}pts lifts attach/basket for ~${X}/mo.",
        recommend_when={"state": "shallow_penetration", "min_signal": "space_zones"},
        tags=("footfall", "zone", "layout", v.family),
    )


# ── 12. Window/display → entry conversion ─────────────────────────────────
def _window_conversion(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your window stops people but doesn't pull them in",
        observation=f"Vision counts {X} window-stops/day (passersby who pause) but only {X}% then enter.",
        reasoning=f"The display is winning the hard part — attention — and losing the easy part — the call to enter. A high stop rate with low entry means your most-seen merchandising surface is decorative, not persuasive; the offer or the 'come in' cue is missing, not the eyeballs.",
        conclusion=f"Add an explicit reason-to-enter to the window (price, 'today only', or a visible in-store payoff) and re-measure stop-to-entry.",
        expected_effect=f"Converting {X}pts more window-stops adds ~{X} entries/day (~${X}/mo).",
        recommend_when={"state": "window_stops_no_entry", "min_signal": "vision_traffic"},
        tags=("footfall", "window", "storefront", v.family),
    )


# ── 13. Visible wait → walkout (never joins line) ─────────────────────────
def _wait_walkout(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"People see the wait and leave without ever lining up",
        observation=f"When wait exceeds {X}s, vision sees {X} entrants turn around at the threshold without joining the queue.",
        reasoning=f"Unlike a balk (someone already in line), this is a pre-line walkout — the visitor sizes up the wait and never commits, so it's completely invisible to POS and the queue counter alike. Only vision sees it, and it's pure lost {unit} volume tied directly to perceived wait, not actual service time.",
        conclusion=f"Make the wait look shorter than it is (visible second register opening, fast-lane signage) and cap perceived wait during the {X} peak.",
        expected_effect=f"Recapturing pre-line walkouts is worth ~${X}/mo at your average {unit} value.",
        recommend_when={"state": "pre_line_walkout", "min_signal": "vision_traffic"},
        tags=("footfall", "queue", "walkout", v.family),
    )


# ── 14. Staffing vs footfall (conversion falls when thin) ─────────────────
def _staffing_mismatch(v: Vertical, situation: str) -> Built:
    extra = " Heading into the seasonal peak, the per-staff load will worsen — fix coverage before traffic climbs." if situation == "seasonal_peak" else ""
    return Built(
        title=f"When footfall-per-{v.staff_role} climbs, conversion falls",
        observation=f"In hours where entries-per-{v.staff_role} exceed {X}, conversion runs {X}pts below hours under that load.",
        reasoning=f"This joins what the camera sees (traffic) to who's on the floor (the schedule): past a service threshold a {v.staff_role} can't engage everyone, so high-traffic hours go under-served and convert worse than quieter, properly-staffed ones. The lost sales hide inside your busiest, best-looking hours.{extra}",
        conclusion=f"Schedule to footfall, not to clock: add coverage in the hours where entries-per-{v.staff_role} crosses {X}.",
        expected_effect=f"Restoring conversion in under-covered high-traffic hours recovers ~${X}/mo.",
        recommend_when={"state": "understaffed_vs_footfall", "min_signal": "vision_traffic"},
        tags=("footfall", "staffing", "conversion", v.family),
    )


# ── 15. Quick bounce (enter and immediately leave) ────────────────────────
def _quick_bounce(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"{X}% of entrants bounce within {X} seconds",
        observation=f"Vision sees {X}% of entries exit within {X}s, never leaving the front zone.",
        reasoning=f"A near-instant bounce is a different failure than slow browsing: it signals wrong-store, can't-find-it, or no-acknowledgement — the visitor formed a 'not for me' judgment before shopping even began. These never had a chance to convert, so they don't belong in your conversion denominator until the front-door experience is fixed.",
        conclusion=f"Fix the first {X} seconds: clear what-you-are signage, an unobstructed entry, and a {v.staff_role} acknowledgement within the bounce window.",
        expected_effect=f"Halving the bounce rate redirects ~{X} visits/day into real shopping (~${X}/mo).",
        recommend_when={"state": "high_entry_bounce", "min_signal": "vision_visits"},
        tags=("footfall", "bounce", "entry", v.family),
    )


# ── 16. Zone traffic imbalance (hot vs cold floor) ────────────────────────
def _zone_imbalance(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Traffic crowds into {X}% of your floor; the rest stays cold",
        observation=f"Vision concentrates {X}% of movement in a few zones while {X}% of zones see almost no shoppers.",
        reasoning=f"Cold zones are paid floor space pulling no shoppers — distinct from a dead zone (which gets traffic but no sales). This is a flow problem: layout and adjacency are funneling everyone down the same lanes, so whole sections of rent never get a chance to sell.",
        conclusion=f"Rebalance flow: move a destination category or a {v.staff_role} station into a cold zone and re-measure its traffic share.",
        expected_effect=f"Activating cold floor space toward store-average sales density is worth ~${X}/mo.",
        recommend_when={"state": "zone_traffic_imbalance", "min_signal": "space_zones"},
        tags=("footfall", "zone", "layout", v.family),
    )


# ── 17. Occupancy near capacity suppresses new entries ────────────────────
def _occupancy_deters(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"A full store turns people away at your busiest minute",
        observation=f"When occupancy nears the {X}-person cap, vision shows door entries flatten or dip even though passerby volume is still rising.",
        reasoning=f"At the very moment demand peaks, visible crowding/queuing deters new entrants — the store self-limits its own throughput. This is a capacity-shaped revenue ceiling distinct from conversion: the lost customers never even enter, so no in-store fix can recover them; only faster turnover or relieved density can.",
        conclusion=f"Increase throughput at the cap (expedite checkout, second service point, clear the entry) so occupancy turns over instead of saturating during the {X} peak.",
        expected_effect=f"Each relieved peak hour recaptures ~{X} suppressed entries (~${X}/mo).",
        recommend_when={"state": "occupancy_suppresses_entry", "min_signal": "vision_traffic"},
        tags=("footfall", "occupancy", "capacity", v.family),
    )


# ── 18. Conversion by daypart vs footfall ─────────────────────────────────
def _conversion_daypart(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your busiest daypart converts worst",
        observation=f"The {X} daypart pulls your highest footfall but converts {X}pts below the quieter {X} daypart.",
        reasoning=f"Footfall and conversion peak at different times, so raw traffic is a misleading success signal — the hours that look best on a door-counter are the least efficient at turning visitors into {unit}s. Optimizing for entries alone would double down on your weakest conversion window.",
        conclusion=f"Diagnose the high-traffic daypart specifically (staffing, queue, density) instead of judging it by its impressive entry count.",
        expected_effect=f"Lifting peak-daypart conversion toward your best daypart is worth ~${X}/mo.",
        recommend_when={"state": "peak_daypart_low_conversion", "min_signal": "vision_traffic"},
        tags=("footfall", "daypart", "conversion", v.family),
    )


# ── 19. No staff engagement → no conversion ───────────────────────────────
def _engagement_gap(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Unapproached shoppers don't convert",
        observation=f"Vision flags {X}% of visits with zero {v.staff_role}-proximity events; those visits convert {X}pts below engaged visits.",
        reasoning=f"For {v.name}, engagement — not traffic — is the missing lever: a shopper no one approaches self-serves a quick item or leaves, while a {v.staff_role} touchpoint reliably lifts {unit} rate and basket. The store has the visitors; it isn't spending its labor on them at the moment of decision.",
        conclusion=f"Set a coverage rule that every visit gets one {v.staff_role} acknowledgement, and route staff to unengaged zones first.",
        expected_effect=f"Engaging the currently-unapproached share is worth ~${X}/mo in incremental conversion.",
        recommend_when={"state": "unengaged_visits", "min_signal": "vision_visits"},
        tags=("footfall", "engagement", "conversion", v.family),
    )


# ── 20. Group vs solo conversion ──────────────────────────────────────────
def _group_solo(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Groups and solos get the same service but behave differently",
        observation=f"Vision splits visits {X}% solo / {X}% groups of {X}+; the two convert and basket very differently yet get identical floor treatment.",
        reasoning=f"Party size predicts behavior: groups dwell longer and basket bigger but need more {v.staff_role} bandwidth, while solos want speed. Serving both with one playbook under-serves the higher-value party type — a segmentation the camera can see but the POS can't.",
        conclusion=f"Give the {v.staff_role} a party-size cue and two scripts (fast path for solos, attentive path for groups) and measure {unit} value by party type.",
        expected_effect=f"Right-serving the higher-value party type is worth ~${X}/mo in basket and conversion.",
        recommend_when={"state": "party_size_mistreatment", "min_signal": "vision_visits"},
        tags=("footfall", "party_size", "service", v.family),
    )


# ── 21. High dwell + no buy (friction, not disinterest) ───────────────────
def _dwell_high_no_buy(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Long lingers that still don't buy",
        observation=f"Vision flags {X} visits/day dwelling past {X} minutes that end without a {v.sale_unit}.",
        reasoning=f"High dwell normally means high intent, so a long visit that ends empty is the opposite of a fast bounce — it's friction at the finish: can't find help, out-of-stock on the chosen item, price shock, or a checkout barrier. These shoppers wanted to buy and were blocked, making them the most recoverable lost sales on the floor.",
        conclusion=f"Intercept long-dwell non-buyers with a {v.staff_role} check-in at the {X}-minute mark and audit stock/price on the items they linger over.",
        expected_effect=f"Rescuing high-dwell non-buyers is worth ~${X}/mo from already-convinced shoppers.",
        recommend_when={"state": "high_dwell_no_purchase", "min_signal": "vision_visits"},
        tags=("footfall", "dwell", "friction", v.family),
    )


def _entry_direction_bias(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Shoppers all turn one way at the door — {X}% miss a whole side",
        observation=f"Vision shows {X}% of entrants turn toward the {X} side first, so the opposite side draws only {X}% of first-minute traffic.",
        reasoning=f"Entry direction is a hard-wired shopper habit, so a layout that fights it strands one side of the floor — the under-walked side gets few eyes no matter how strong its assortment, which means the rent and inventory there earn against a fraction of the traffic the busy side sees.",
        conclusion=f"Route the cold side back into the path — move a destination category or a {v.staff_role} station onto the under-walked side, and open a sightline that pulls the entry turn toward it.",
        expected_effect=f"Activating the starved side toward floor-average sales density is worth ~${X}/mo.",
        recommend_when={"state": "entry_direction_bias", "min_signal": "space_zones"},
        tags=("footfall", "zone", "layout", v.family),
    )


def _handling_no_buy(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"A product gets handled constantly but rarely bought",
        observation=f"Vision flags {X} pick-ups/day on one display, yet only {X}% convert to a {v.sale_unit} — far below the floor's touch-to-buy rate.",
        reasoning=f"A pick-up is the strongest shelf-level intent signal there is, so a product touched often but bought rarely isn't a discovery problem — it's an objection at the shelf (price shock, missing size, unclear value), which means the item is doing the hard work of attracting hands and losing at the last inch.",
        conclusion=f"Fix the shelf objection — re-price, add a value/size callout, or station a {v.staff_role} at the display — and re-measure touch-to-buy in {X} weeks.",
        expected_effect=f"Converting even {X}% more of the handled-not-bought intent is worth ~${X}/mo.",
        recommend_when={"state": "handled_not_bought", "min_signal": "vision_visits"},
        tags=("footfall", "engagement", "conversion", v.family),
    )


register(
    Archetype(
        key="footfall_conversion_gap", domain="footfall", name="Entries far exceed sales",
        build=_conversion_gap, situations=("baseline", "declining", "emerging"),
        required_signals=("vision_traffic", "transactions"),
        required_agents=("VisionTrafficAgent", "VisionConversionAgent"),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="VisionConversionAgent: join vision_traffic.entries to POS transactions per store-hour to compute true entry-to-sale conversion and the recoverable gap (vision_traffic exists; conversion join is the upgrade).",
    ),
    Archetype(
        key="footfall_dwell_low", domain="footfall", name="Low dwell — browse not buy",
        build=_dwell_low, situations=("baseline",),
        required_signals=("vision_visits",),
        required_agents=("VisitDwellAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="VisitDwellAgent: derive per-visit dwell from entry/exit track timestamps in the vision feed and segment converting vs non-converting dwell (per-visit tracking not yet ingested — extend vision_visits).",
    ),
    Archetype(
        key="footfall_queue_abandonment", domain="footfall", name="In-line queue balk",
        build=_queue_abandonment, situations=("baseline", "seasonal_peak"),
        required_signals=("vision_traffic",),
        required_agents=("VisionTrafficAgent", "QueueVisionAgent"),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="QueueVisionAgent: pair vision_traffic.queue_wait_avg_sec with line join/exit tracks to count balks vs completions (queue wait exists; per-person line tracking is the upgrade).",
    ),
    Archetype(
        key="footfall_dead_zone", domain="footfall", name="Zone with traffic but no sales",
        build=_dead_zone, situations=("baseline",),
        required_signals=("space_zones", "zone_purchase_correlation"),
        required_agents=("ZoneYieldAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ZoneYieldAgent: join space_zones traffic shares to zone_purchase_correlation (zone→SKU→POS) to rank sales-per-visit by zone and flag traffic-rich/sales-poor zones (zone mapping not yet built).",
    ),
    Archetype(
        key="footfall_capture_rate", domain="footfall", name="Capture rate vs passersby",
        build=_capture_rate, situations=("baseline",),
        required_signals=("vision_traffic",),
        required_agents=("StorefrontCaptureAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="StorefrontCaptureAgent: add an exterior/sidewalk passerby counter and divide door entries by passersby for capture rate (exterior counting not yet ingested — new camera scope).",
    ),
    Archetype(
        key="footfall_peak_occupancy", domain="footfall", name="Peak occupancy vs capacity",
        build=_peak_occupancy, situations=("baseline",),
        required_signals=("vision_traffic",),
        required_agents=("VisionTrafficAgent", "VisionConversionAgent"),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="VisionConversionAgent (shared): correlate vision_traffic.occupancy against a per-store comfortable-capacity constant and hourly conversion to find the density where conversion turns down (occupancy exists; capacity constant + correlation is the upgrade).",
    ),
    Archetype(
        key="footfall_browse_to_fitting", domain="footfall", name="Browse to fitting-room flow",
        build=_browse_to_fitting, situations=("baseline",),
        required_signals=("vision_visits", "space_zones"),
        required_agents=("FittingRoomAgent",),
        applies_keys=("boutique",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="FittingRoomAgent: track floor-browse → fitting-room-zone entry transitions per visit to compute the try-on funnel step (fitting-room zone + per-visit path not yet built).",
    ),
    Archetype(
        key="footfall_fitting_to_purchase", domain="footfall", name="Fitting-room to purchase",
        build=_fitting_to_purchase, situations=("baseline",),
        required_signals=("vision_visits", "transactions"),
        required_agents=("FittingRoomAgent",),
        applies_keys=("boutique",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="FittingRoomAgent (shared): join fitting-room sessions to subsequent POS transactions (session→checkout time/zone match) for try-on close rate (session-to-sale join not yet built).",
    ),
    Archetype(
        key="footfall_demographic_mix", domain="footfall", name="Visitor demographics vs product mix",
        build=_demographic_mix, situations=("baseline",),
        required_signals=("vision_visits", "transactions"),
        required_agents=("DemographicVisionAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="DemographicVisionAgent: estimate coarse visitor segments from the vision feed and compare segment share to product-mix/space allocation (demographic estimation not yet enabled — privacy-gated new model).",
    ),
    Archetype(
        key="footfall_repeat_visitor", domain="footfall", name="Repeat-visitor non-buyers",
        build=_repeat_visitor, situations=("baseline",),
        required_signals=("vision_visits", "transactions"),
        required_agents=("VisitorReIDAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="VisitorReIDAgent: re-identify returning visitors across days (privacy-preserving embeddings) and join to POS to find repeat browsers who rarely transact (re-ID not yet built — privacy-gated).",
    ),
    Archetype(
        key="footfall_penetration_depth", domain="footfall", name="Entrance vs back-of-store flow",
        build=_penetration_depth, situations=("baseline",),
        required_signals=("space_zones",),
        required_agents=("ZoneYieldAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ZoneYieldAgent (shared): compute penetration depth from space_zones path data (share of entrants reaching each zone band) (zone path mapping not yet built).",
    ),
    Archetype(
        key="footfall_window_conversion", domain="footfall", name="Window-stop to entry",
        build=_window_conversion, situations=("baseline",),
        required_signals=("vision_traffic",),
        required_agents=("StorefrontCaptureAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="StorefrontCaptureAgent (shared): detect exterior window-stop events (pause near display) and divide entries by stops for display pull-in rate (exterior dwell detection not yet ingested).",
    ),
    Archetype(
        key="footfall_wait_walkout", domain="footfall", name="Visible-wait walkout",
        build=_wait_walkout, situations=("baseline",),
        required_signals=("vision_traffic",),
        required_agents=("QueueVisionAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="QueueVisionAgent (shared): correlate vision_traffic.queue_wait_avg_sec with entrants who exit without joining the line (entry/exit exist; threshold-conditioned pre-line walkout detection is the upgrade).",
    ),
    Archetype(
        key="footfall_staffing_mismatch", domain="footfall", name="Footfall vs staffing conversion drop",
        build=_staffing_mismatch, situations=("baseline", "seasonal_peak"),
        required_signals=("vision_traffic", "schedule_shifts", "transactions"),
        required_agents=("VisionConversionAgent", "StaffingAgent"),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="VisionConversionAgent + StaffingAgent: join vision_traffic.entries to schedule_shifts headcount per hour and regress conversion on entries-per-staff (vision + schedule exist; the entries-per-staff conversion join is the upgrade).",
    ),
    Archetype(
        key="footfall_quick_bounce", domain="footfall", name="Quick entry bounce",
        build=_quick_bounce, situations=("baseline",),
        required_signals=("vision_visits",),
        required_agents=("VisitDwellAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="VisitDwellAgent (shared): flag visits whose exit follows entry within a short threshold and never leave the front zone (per-visit dwell + zone not yet ingested).",
    ),
    Archetype(
        key="footfall_zone_imbalance", domain="footfall", name="Hot vs cold floor zones",
        build=_zone_imbalance, situations=("baseline",),
        required_signals=("space_zones",),
        required_agents=("ZoneYieldAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ZoneYieldAgent (shared): compute the Gini/spread of traffic across space_zones to surface cold zones pulling no shoppers (zone mapping not yet built).",
    ),
    Archetype(
        key="footfall_occupancy_deters", domain="footfall", name="Saturation suppresses entry",
        build=_occupancy_deters, situations=("baseline",),
        required_signals=("vision_traffic",),
        required_agents=("VisionTrafficAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="VisionTrafficAgent: detect minutes where occupancy nears capacity while entry rate flattens/dips against rising context (occupancy + entries exist; the saturation-vs-entry inflection detection is the upgrade).",
    ),
    Archetype(
        key="footfall_conversion_daypart", domain="footfall", name="Busiest daypart converts worst",
        build=_conversion_daypart, situations=("baseline",),
        required_signals=("vision_traffic", "transactions"),
        required_agents=("VisionConversionAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="VisionConversionAgent (shared): bucket vision_traffic.conversion_rate by daypart and rank traffic vs conversion to expose high-traffic/low-conversion windows (conversion_rate exists; daypart bucketing is the upgrade).",
    ),
    Archetype(
        key="footfall_engagement_gap", domain="footfall", name="Unengaged visits don't convert",
        build=_engagement_gap, situations=("baseline",),
        required_signals=("vision_visits", "transactions"),
        required_agents=("EngagementVisionAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="EngagementVisionAgent: detect staff-customer proximity/interaction events from the vision feed and join to conversion (engaged vs unengaged visits) (staff-proximity detection not yet built).",
    ),
    Archetype(
        key="footfall_group_solo", domain="footfall", name="Group vs solo conversion",
        build=_group_solo, situations=("baseline",),
        required_signals=("vision_visits", "transactions"),
        required_agents=("PartyDetectAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="PartyDetectAgent: cluster co-arriving/co-moving tracks into parties and join party size to conversion and basket value (group detection not yet built).",
    ),
    Archetype(
        key="footfall_dwell_high_no_buy", domain="footfall", name="High dwell, no purchase",
        build=_dwell_high_no_buy, situations=("baseline",),
        required_signals=("vision_visits", "transactions"),
        required_agents=("VisitDwellAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="VisitDwellAgent (shared): flag long-dwell visits with no matching POS transaction and cross-check the lingered zone's stock/price (per-visit dwell + zone→SKU not yet built).",
    ),
    Archetype(
        key="footfall_entry_direction_bias", domain="footfall", name="Entry turn-direction bias",
        build=_entry_direction_bias, situations=("baseline",),
        required_signals=("space_zones",),
        required_agents=("ZoneYieldAgent",),
        applies_families=FOOT_FAMILIES, exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ZoneYieldAgent: derive first-turn direction from entry-path tracks and compute first-minute traffic share by side to surface a starved side of the floor (entry-path direction not yet tracked).",
    ),
    Archetype(
        key="footfall_handling_no_buy", domain="footfall", name="Handled but not bought",
        build=_handling_no_buy, situations=("baseline",),
        required_signals=("vision_visits", "transactions"),
        required_agents=("ProductHandlingAgent",),
        applies_families=("retail", "personal_care"), exclude_keys=NO_GHOST,
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ProductHandlingAgent: detect product pick-up/handling events at a display from the vision feed and join to POS to compute touch-to-buy per item (shelf-level handling detection not yet built).",
    ),
)
