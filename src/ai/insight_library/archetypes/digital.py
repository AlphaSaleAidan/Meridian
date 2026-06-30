"""
Domain: DIGITAL / ONLINE PRESENCE & CONVERSION FUNNEL.

Each archetype is a distinct reasoning pattern about the DIGITAL FRONT DOOR and the
mechanics of turning an online impression into a visit or order: the Google
Business Profile / maps listing, the website and its conversion path, online
photos/menu, the click-to-call / reserve / order funnel, and cross-platform
listing (NAP) consistency. This is funnel mechanics — distinct from the marketing
domain (email/loyalty/reviews-as-reputation) and the channel domain (phone
handling, drive-thru, delivery economics). Marketing creates demand; digital is
about whether the online surfaces convert the demand that's already searching.

Capability is graded honestly. NONE of these signals exist in the current swarm —
they require NEW external collectors (Google Business Profile API, web analytics,
listing scrapers, maps rank crawlers). Every archetype is therefore MISSING or, at
most, PARTIAL where an existing internal signal (transactions, phone_call_logs)
covers one side of the join. Each specs the concrete collector to build:
  * DigitalPresenceAgent   — GBP/website completeness, photos, hours, posts, attrs
  * OnlineFunnelAgent      — web/app analytics: sessions → conversion, cart, mobile
  * ListingConsistencyAgent— cross-platform NAP / category / hours reconciliation
  * MapsRankAgent          — geo-grid map-pack rank vs proximity and competitors
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical, VERTICALS
from .base import Archetype, Built, X, register


# ── Targeting helpers (fed into applies_keys) ───────────────────────────────
def _keys_with_channel(*channels: str) -> tuple[str, ...]:
    cs = set(channels)
    return tuple(v.key for v in VERTICALS if cs & set(v.channels))


def _keys_with_any_flag(*flags: str) -> tuple[str, ...]:
    fs = set(flags)
    return tuple(v.key for v in VERTICALS if fs & v.flags)


_ALL = tuple(v.key for v in VERTICALS)  # universal: every local business has a listing

# Reusable upgrade specs (kept rigorous and concrete) ────────────────────────
_GBP_UP = "DigitalPresenceAgent: pull the Google Business Profile via the Business Profile API and score completeness/photos/hours/attributes; no GBP collector is wired today."
_WEB_UP = "OnlineFunnelAgent: ingest web/app analytics (sessions, events, conversions) and join to transactions; no analytics pipeline exists today."
_NAP_UP = "ListingConsistencyAgent: scrape Google/Apple/Bing/Yelp/Facebook listings and reconcile name/address/phone/hours/category; no listing scraper exists today."
_MAPS_UP = "MapsRankAgent: run a geo-grid of map-pack queries around the business and record rank vs distance and competitors; no maps rank crawler exists today."


# ═══════════════════════ LISTING / GBP / MAPS ═══════════════════════════════
def _gbp_incomplete(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your Google Business Profile is incomplete — the listing does half its job",
        observation=f"Your GBP is missing {X} of the fields searchers act on (hours, services, attributes, photos) and is {X}% complete.",
        reasoning=f"The Business Profile is the first surface a local searcher sees for a {v.name.lower()}, and Google ranks and displays complete profiles ahead of thin ones; every missing field is both a ranking drag and a question the searcher can't answer, so they pick a competitor whose listing does answer it.",
        conclusion=f"Fill in the {X} highest-impact fields first — set the hours and primary category, add your services, and load fresh photos — then keep attributes current.",
        expected_effect=f"A fully-built profile lifts listing visibility and click-through, recovering ~${X}/mo of searches that currently bounce to competitors.",
        recommend_when={"state": "gbp_incomplete", "min_signal": "gbp_profile"},
        tags=("digital", "gbp", "listing", v.family),
    )


def _gbp_posts_unused(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You never post to your Google profile — a free slot on the search result sits empty",
        observation=f"Zero GBP posts in the last {X} days; the offers/updates module on your listing is blank while competitors refresh theirs.",
        reasoning=f"GBP posts occupy real estate directly on the search/maps result and signal an active, current business; for a {v.name.lower()}, an unused posting slot forgoes free placement at the exact moment a searcher is deciding — the space is yours and it's showing nothing.",
        conclusion=f"Publish a weekly GBP post (offer, event, or new {v.sale_unit}) and feature your current promotion in the offers module.",
        expected_effect=f"An active posting cadence lifts profile engagement and click-through worth ~${X}/mo at near-zero cost.",
        recommend_when={"state": "gbp_posts_idle", "min_signal": "gbp_profile"},
        tags=("digital", "gbp", "content", v.family),
    )


def _maps_ranking_vs_proximity(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You rank in the map pack near your door but vanish a few blocks out",
        observation=f"Geo-grid tracking shows you in the top-3 within {X}m of the storefront but off the first map screen beyond {X}m, where much of your draw lives.",
        reasoning=f"Map-pack rank decays with searcher distance; for a {v.name.lower()} that draws from a wider radius than its immediate block, a tight ranking footprint means searchers in your real catchment never see you — proximity is doing the ranking work that profile strength and reviews should be extending.",
        conclusion=f"Set the correct primary category, collect {X} new reviews a month, complete the profile, and build {X} local citations to widen the radius where you place.",
        expected_effect=f"Extending your ranked radius captures the searches just outside your block, worth ~${X}/mo of new discovery.",
        recommend_when={"state": "maps_rank_proximity_bound", "min_signal": "maps_geo_grid"},
        tags=("digital", "maps", "ranking", v.family),
    )


def _maps_photo_freshness(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Customer photos define your listing — your own are stale",
        observation=f"{X}% of the photos on your maps listing are user-uploaded and your newest owner photo is {X} months old.",
        reasoning=f"On maps, photos are the strongest visual cue a searcher uses to choose, so when user photos outnumber and outdate yours, whoever happened to snap a picture — not the owner — sets the listing's impression, which drives comparison-stage clicks to whichever {v.name.lower()} simply looks better and costs you the {v.sale_unit} before a visit.",
        conclusion=f"Upload a current owner photo set (interior, {v.sale_unit}, team) and set a monthly schedule to refresh it so your images lead the listing.",
        expected_effect=f"A current owner-led photo set lifts listing click-through worth ~${X}/mo of better-qualified discovery.",
        recommend_when={"state": "maps_photos_stale", "min_signal": "gbp_profile"},
        tags=("digital", "maps", "photos", v.family),
    )


def _directory_category_miscategorized(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your listing's primary category is wrong — you're competing in the wrong race",
        observation=f"Your GBP primary category doesn't match how a {v.name.lower()} should be classified, and {X} relevant secondary categories are unset.",
        reasoning=f"Primary category is the single biggest lever on which searches a listing is even eligible for; a mismatched category means Google ranks you for the wrong intent and omits you from the right one, so even a strong profile competes in a race it can't win and misses the race it should.",
        conclusion=f"Set the correct primary category and add the {X} valid secondary categories that match your actual {v.sale_unit} mix.",
        expected_effect=f"Correct categorization makes you eligible for the right searches, worth ~${X}/mo of recovered relevant discovery.",
        recommend_when={"state": "category_mismatch", "min_signal": "gbp_profile"},
        tags=("digital", "listing", "category", v.family),
    )


def _third_party_listing_inconsistency(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your name/address/phone disagree across the web",
        observation=f"NAP audit finds {X} conflicting versions of your hours/phone/address across Google, Apple, Bing, Yelp, and Facebook.",
        reasoning=f"Inconsistent NAP confuses both ranking algorithms (which use citation agreement as a trust signal) and customers (who may call a dead number or arrive after a wrong-listed close); for a {v.name.lower()} dependent on local search, every conflicting listing is a trust deduction and a literal lost customer.",
        conclusion=f"Set one canonical NAP record and push the correction out to each of the {X} platforms that currently disagree.",
        expected_effect=f"Consistent citations restore local trust signals and stop misdirected customers, worth ~${X}/mo.",
        recommend_when={"state": "nap_inconsistent", "min_signal": "listing_scan"},
        tags=("digital", "listing", "nap", v.family),
    )


def _online_hours_inaccurate(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your posted online hours don't match when you're actually open",
        observation=f"Listed hours conflict with actual operating hours on {X} days/week, and holiday hours are unset.",
        reasoning=f"Wrong online hours are uniquely damaging: a searcher who sees 'open', drives over, and finds you closed converts a ready {v.sale_unit} into a frustrated non-customer — and Google penalizes listings flagged for inaccurate hours; for a {v.name.lower()}, this fails the customer at the most committed moment in the funnel.",
        conclusion=f"Correct the weekly hours to match reality and set special/holiday hours in advance across every listing.",
        expected_effect=f"Accurate hours stop wasted trips and listing penalties, recovering ~${X}/mo of misdirected demand.",
        recommend_when={"state": "hours_inaccurate", "min_signal": "listing_scan"},
        tags=("digital", "listing", "hours", v.family),
    )


def _zero_click_info_gap(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Searchers ask questions your listing leaves unanswered",
        observation=f"{X} questions sit unanswered in your listing Q&A and key attributes searchers filter on are unset.",
        reasoning=f"More local journeys now end on the search result itself ('zero-click'); if your listing doesn't answer the deciding question — parking, accessibility, what a {v.name.lower()} offers — the searcher resolves the doubt by choosing a competitor whose listing does, so the gap costs you the visit before a click ever happens.",
        conclusion=f"Seed and answer the {X} most common questions and set every attribute searchers filter on for a {v.name.lower()}.",
        expected_effect=f"Answering deciding questions on the listing captures zero-click choosers worth ~${X}/mo.",
        recommend_when={"state": "listing_info_gap", "min_signal": "gbp_profile"},
        tags=("digital", "listing", "zero_click", v.family),
    )


def _search_visibility_for_category(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You're invisible for the category searches that should find you",
        observation=f"For the {X} core '{v.name.lower()} near me'-style queries, you don't appear on the first page of results or the map pack.",
        reasoning=f"Category and 'near me' searches are the top of your discovery funnel — the highest-intent way a new customer finds a {v.name.lower()}; absence from page one for your own category means new-customer discovery is structurally capped no matter how good the in-store experience is, because the funnel never starts.",
        conclusion=f"Build a page for each of the {X} highest-intent category queries, add them to your listing and citations, and set a monthly rank check.",
        expected_effect=f"Reaching page one for core category queries opens net-new discovery worth ~${X}/mo.",
        recommend_when={"state": "category_search_invisible", "min_signal": "serp_rank"},
        tags=("digital", "search", "visibility", v.family),
    )


# ═══════════════════════ WEBSITE / CONVERSION ═══════════════════════════════
def _website_conversion_low(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your website gets visitors but converts almost none",
        observation=f"The site draws {X} sessions/month but only {X}% take the primary action (call, book, order, directions) — visits arrive and leave.",
        reasoning=f"Traffic without conversion means the top of the funnel works and the page doesn't: for a {v.name.lower()} the visitor came with intent and the site failed to give a fast, obvious next step, so paid-for and earned attention evaporates at the one screen you fully control.",
        conclusion=f"Put the single primary action above the fold on every page and strip the steps between landing and that action.",
        expected_effect=f"Lifting site conversion by {X}pts on existing traffic is worth ~${X}/mo at your average {v.sale_unit} value.",
        recommend_when={"state": "web_conversion_low", "min_signal": "web_analytics"},
        tags=("digital", "website", "conversion", v.family),
    )


def _website_load_speed_drop(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your site is slow enough to be shedding visitors before it loads",
        observation=f"Largest-contentful-paint runs {X}s on mobile and bounce climbs sharply past the {X}s mark where most of your sessions sit.",
        reasoning=f"Page speed is a conversion and ranking factor at once: a visitor searching for a {v.name.lower()} abandons a slow page within seconds, and Google demotes slow pages — so every extra second silently subtracts from both discovery and the visitors who do arrive, before your content gets a chance.",
        conclusion=f"Compress images, defer non-critical scripts, and get mobile LCP under {X}s on the pages that take the most traffic.",
        expected_effect=f"Cutting load time under the abandon threshold recovers ~${X}/mo of pre-bounce visitors.",
        recommend_when={"state": "web_speed_slow", "min_signal": "web_analytics"},
        tags=("digital", "website", "speed", v.family),
    )


def _mobile_experience_gap(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Most of your traffic is mobile and your mobile experience is the worst",
        observation=f"{X}% of sessions are on mobile but mobile converts at {X}% versus {X}% on desktop — the gap is the experience, not the audience.",
        reasoning=f"Local searches for a {v.name.lower()} skew heavily mobile and high-intent (often in-the-moment), so a broken mobile flow — tiny tap targets, buried call/directions, a form that won't submit — fails your largest and most ready segment exactly where they decide.",
        conclusion=f"Fix the mobile path first: thumb-reachable call/book/directions buttons, no horizontal scroll, and a one-screen primary action.",
        expected_effect=f"Closing the mobile-vs-desktop conversion gap on existing mobile traffic is worth ~${X}/mo.",
        recommend_when={"state": "mobile_conversion_gap", "min_signal": "web_analytics"},
        tags=("digital", "website", "mobile", v.family),
    )


def _online_photos_quality(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your online photos undersell the {v.sale_unit}",
        observation=f"Your site/listing leads with {X} low-quality or outdated images, and the {v.sale_unit} that drives choice has no strong representative shot.",
        reasoning=f"For a visually-decided purchase the photo is the pitch, so when a searcher comparing a {v.name.lower()} judges quality from images in seconds, weak or stale shots drive the click to a competitor whose photos simply look better — which costs you the visit regardless of who actually does the better work.",
        conclusion=f"Replace the hero images: stage and upload {X} current, well-lit shots of your best {v.sale_unit}s and the space, and set them as the lead image on every surface.",
        expected_effect=f"Stronger photography lifts both listing and site click-through, worth ~${X}/mo of better-converting discovery.",
        recommend_when={"state": "photos_weak", "min_signal": "gbp_profile"},
        tags=("digital", "photos", "conversion", v.family),
    )


def _social_to_site_dropoff(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your social following doesn't make it to a booking or order",
        observation=f"Social profiles drive {X} link clicks/month but only {X}% reach a conversion action; the link-in-bio path leaks almost everyone.",
        reasoning=f"Social earns attention but rarely closes inside the app, so the handoff from a {v.name.lower()}'s profile to your own book/order surface is where intent converts or leaks; a cluttered or dead-end link-in-bio path drives the followers you already paid to build straight back out without acting.",
        conclusion=f"Build a single-purpose landing page whose only job is the primary action, point the social link at it instead of a generic homepage, and add one clear call-to-action above the fold.",
        expected_effect=f"Fixing the social-to-conversion handoff turns existing followers into ~${X}/mo of booked {v.sale_unit}s.",
        recommend_when={"state": "social_funnel_leak", "min_signal": "web_analytics"},
        tags=("digital", "social", "funnel", v.family),
    )


def _online_promo_not_surfaced(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your current promotion is invisible online",
        observation=f"An active in-store offer appears on {X} of your online surfaces; the listing, site, and order page don't mention it.",
        reasoning=f"A promotion only works where the customer actually decides; for a {v.name.lower()}, running an offer in-store but not on the listing/site/order page means the digital searcher — often the new customer you most want — never sees the reason to choose you, so the promo subsidizes people already walking in.",
        conclusion=f"Surface the live offer consistently across GBP posts, the site hero, and the online order/book entry point while it runs.",
        expected_effect=f"Surfacing the promo where searchers decide pulls incremental {v.sale_unit}s worth ~${X}/mo from the same offer spend.",
        recommend_when={"state": "promo_not_surfaced", "min_signal": "gbp_profile"},
        tags=("digital", "promo", "surfacing", v.family),
    )


# ═══════════════════════ MENU / ASSORTMENT (online) ═════════════════════════
def _online_menu_stale_missing(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your menu online is missing or out of date",
        observation=f"Your published menu/service list is {X} months stale or absent on {X} of your key surfaces (site, listing, order page).",
        reasoning=f"The menu is the deciding content for a {v.name.lower()}, so a missing or stale list means a searcher comparing options can't see what you offer or at what price and picks a competitor whose menu is current — which costs you the comparison before the visit and sets a wrong expectation that fails again at purchase.",
        conclusion=f"Publish a current, structured menu/service list on every surface, set one owner to sync it whenever items or prices change, and standardize the format across site, listing, and order page.",
        expected_effect=f"A current, everywhere-consistent menu lifts choose-rate worth ~${X}/mo of comparison-stage demand.",
        recommend_when={"state": "menu_stale", "min_signal": "listing_scan"},
        tags=("digital", "menu", "content", v.family),
    )


def _online_menu_pricing_mismatch(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your online prices don't match the register",
        observation=f"Prices published online differ from POS prices on {X}% of items, with the online figures running stale.",
        reasoning=f"A price mismatch breaks trust at the worst moment: a customer who chose a {v.name.lower()} on an online price and is charged another feels misled, and online-order platforms surface stale prices to everyone comparing; the gap quietly converts a price advantage into a complaint and a chargeback risk.",
        conclusion=f"Sync published prices to the POS as the source of truth and add a check whenever menu/price changes ship.",
        expected_effect=f"Aligning online and register pricing removes friction and disputes worth ~${X}/mo and protects trust.",
        recommend_when={"state": "price_mismatch_online", "min_signal": "listing_scan"},
        tags=("digital", "menu", "pricing", v.family),
    )


def _online_vs_instore_assortment_gap(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your online catalog shows a fraction of what's on the shelf",
        observation=f"Only {X}% of your in-store assortment is listed online; top-selling {v.sale_unit}s are absent from the digital catalog.",
        reasoning=f"For a {v.name.lower()} with an online channel, the catalog is the storefront — an item not listed cannot be discovered or bought online no matter how well it sells in person, so a thin catalog caps online revenue at a slice of true assortment and hides your best movers from digital shoppers.",
        conclusion=f"Prioritize listing the top in-store sellers online first, then close the long tail; keep availability synced.",
        expected_effect=f"Listing the missing top sellers online unlocks ~${X}/mo of demand the catalog currently hides.",
        recommend_when={"state": "assortment_gap_online", "min_signal": "web_analytics"},
        tags=("digital", "assortment", "catalog", v.family),
    )


def _review_velocity_online(v: Vertical, situation: str) -> Built:
    extra = (" The trickle has slowed further over the last few periods — the trend, not just the level, is now working against you."
             if situation == "declining" else "")
    return Built(
        title=f"Your online review velocity has stalled — the listing is going quiet",
        observation=f"You earned {X} new reviews in the last {X} days versus competitors' {X}; the inflow has slowed to a trickle.{extra}",
        reasoning=f"Review RECENCY and VELOCITY (distinct from average score) feed both ranking and the searcher's read of whether a {v.name.lower()} is currently busy and trusted; a stalled inflow makes even a high historical rating look dormant, so the listing loses ground to competitors who are simply collecting reviews faster.",
        conclusion=f"Add a frictionless review ask right after a good {v.sale_unit} (QR/text link) to restore a steady inflow, not a one-time burst.",
        expected_effect=f"Restoring review velocity lifts listing rank and trust, worth ~${X}/mo of recovered discovery and choose-rate.",
        recommend_when={"state": "review_velocity_low", "min_signal": "review_stream"},
        tags=("digital", "reviews", "velocity", v.family),
    )


# ═══════════════════════ FUNNEL: CALL / RESERVE / ORDER ═════════════════════
def _click_to_call_friction(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"People tap to call you and don't get through",
        observation=f"{X} click-to-call taps from your listing/site fail to connect to an answered call ({X}% miss), per analytics joined to call logs.",
        reasoning=f"A click-to-call tap is the highest-intent action a mobile searcher takes for a {v.name.lower()} — they're done comparing and want to act; when that tap dead-ends in a missed or unanswered call, you lose a customer who had already chosen you, which is the most expensive kind of leak because the funnel did everything right until the last step.",
        conclusion=f"Ensure the listed number rings a covered line (or voice agent) during open hours and audit that every digital surface dials the right, answered number.",
        expected_effect=f"Connecting the high-intent click-to-call taps you already get is worth ~${X}/mo of chosen-then-lost {v.sale_unit}s.",
        recommend_when={"state": "click_to_call_friction", "min_signal": "web_analytics"},
        tags=("digital", "funnel", "click_to_call", v.family),
    )


def _online_reservation_friction(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your online booking flow loses people before they confirm",
        observation=f"{X} visitors start an online reservation/booking but only {X}% finish; the flow drops them between start and confirmation.",
        reasoning=f"For an appointment-led {v.name.lower()}, online booking is the primary conversion path; a flow that demands an account, hides availability, or buries confirmation sheds high-intent customers mid-commit — they came ready to book and the mechanics, not the demand, lost them.",
        conclusion=f"Cut the booking flow to the minimum (show live availability, allow guest booking, confirm in one step) and re-measure completion.",
        expected_effect=f"Lifting booking completion by {X}pts on existing starts is worth ~${X}/mo of recovered appointments.",
        recommend_when={"state": "booking_friction", "min_signal": "web_analytics"},
        tags=("digital", "funnel", "reservation", v.family),
    )


def _online_booking_lead_time_friction(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your earliest bookable online slot is too far out",
        observation=f"The soonest slot a customer can self-book online is {X} days away, while {X}% of demand wants service within {X} days.",
        reasoning=f"Online booking only converts the demand its calendar can accommodate; for a {v.name.lower()}, if the first self-serve slot is far out while near-term capacity actually exists (cancellations, held slots, walk-in gaps), the booking tool turns away same-week buyers who then book a competitor — a self-inflicted funnel cap.",
        conclusion=f"Release near-term and cancellation slots to online booking and surface 'soonest available' so short-lead demand can self-serve.",
        expected_effect=f"Opening near-term online availability captures short-lead demand worth ~${X}/mo currently lost to wait.",
        recommend_when={"state": "booking_lead_time_long", "min_signal": "web_analytics"},
        tags=("digital", "funnel", "lead_time", v.family),
    )


def _online_waitlist_booking_adoption(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Walk-ins wait in person while an online waitlist sits unused",
        observation=f"{X}% of peak arrivals queue physically with no online waitlist/join-ahead option, and {X} balk at the visible line.",
        reasoning=f"A digital waitlist/join-ahead converts the customers a visible physical queue scares off into held, tracked demand; for a high-traffic {v.name.lower()}, no online waitlist means peak balkers are pure loss — they leave rather than wait, and you never knew they came.",
        conclusion=f"Offer online join-ahead/waitlist so customers can claim a place remotely and arrive when it's their turn.",
        expected_effect=f"Capturing peak balkers via an online waitlist recovers ~${X}/mo of walked-away demand.",
        recommend_when={"state": "waitlist_unused", "min_signal": "web_analytics"},
        tags=("digital", "funnel", "waitlist", v.family),
    )


def _online_order_funnel_dropoff(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your online order funnel leaks between menu and checkout",
        observation=f"{X}% of visitors who open the online order page reach the cart but only {X}% complete checkout; the drop concentrates at {X}.",
        reasoning=f"For a {v.name.lower()} with online ordering, the steps after 'add to cart' are pure mechanics — account walls, surprise fees, slow loads — and each one sheds a customer who had already chosen what to buy; a funnel that loses people post-intent wastes the demand the rest of the system worked to create.",
        conclusion=f"Instrument the order funnel, find the single worst drop step, and remove it (guest checkout, fees shown up front, fewer taps).",
        expected_effect=f"Recovering checkout completion on existing order-page traffic is worth ~${X}/mo of abandoned {v.sale_unit}s.",
        recommend_when={"state": "order_funnel_dropoff", "min_signal": "web_analytics"},
        tags=("digital", "funnel", "online_order", v.family),
    )


def _cart_abandonment_online(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Online carts get filled and abandoned",
        observation=f"{X}% of online carts are abandoned before purchase, concentrated at the {X} step, with no recovery touch sent.",
        reasoning=f"An abandoned cart is the warmest possible signal — the customer chose specific items and stopped at the last step; for a {v.name.lower()} selling online, leaving abandonment unaddressed wastes both the conversion (fix the step) and the recovery (a timely nudge), so you lose buyers who were one tap from done.",
        conclusion=f"Reduce the abandonment cause at the {X} step (shipping/fees/account) and add a single recovery touch for logged-in carts.",
        expected_effect=f"Recovering a share of abandoned carts is worth ~${X}/mo on demand already at the finish line.",
        recommend_when={"state": "cart_abandonment", "min_signal": "web_analytics"},
        tags=("digital", "funnel", "cart", v.family),
    )


def _qr_table_order_adoption(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"No QR/at-table ordering — every order waits on a {v.staff_role}",
        observation=f"100% of orders route through a {v.staff_role} with no QR/at-table self-order option, and reorder rate drops when the floor is busy.",
        reasoning=f"At-table QR ordering removes the {v.staff_role} bottleneck on the highest-margin moment — the reorder/add-on — letting guests order the instant they want more rather than waiting to flag someone down; for a table-service {v.name.lower()}, the missing self-order path caps incremental orders precisely when staff are most stretched.",
        conclusion=f"Pilot QR at-table ordering for drinks/add-ons during peak and measure incremental order count and ticket against {v.staff_role}-only tables.",
        expected_effect=f"At-table self-ordering lifts reorder/attach during peak, worth ~${X}/mo of incremental {v.sale_unit}s.",
        recommend_when={"state": "qr_order_untapped", "min_signal": "web_analytics"},
        tags=("digital", "funnel", "qr_order", v.family),
    )


# ═══════════════════════ OWNED SURFACE / CHANNEL OWNERSHIP ══════════════════
def _no_website_presence(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You have no website — every customer journey ends on someone else's surface",
        observation=f"There is no owned website for the {v.name.lower()}; an estimated {X}% of would-be visitors land only on third-party listings or social pages you don't control.",
        reasoning=f"Without an owned site you control no surface that fully converts a searcher, so every booking, order, and menu view happens on a third party that owns the customer data, sets the rules, and can re-rank or charge you — which caps both conversion and the SEO that feeds discovery.",
        conclusion=f"Build a lightweight owned website with the primary action (book, order, call, directions) above the fold, then point every listing and social profile at it.",
        expected_effect=f"An owned conversion surface recaptures journeys now lost to third parties, worth ~${X}/mo at your average {v.sale_unit} value.",
        recommend_when={"state": "no_website", "min_signal": "listing_scan"},
        tags=("digital", "website", "presence", v.family),
    )


def _online_ordering_channel_absent(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You have no owned online-order link — demand routes through high-fee marketplaces",
        observation=f"{X}% of online {unit}s come through third-party marketplaces at a {X}% fee, while you offer no direct order/book link of your own.",
        reasoning=f"When the only digital way to buy is a marketplace, every online {unit} pays that platform a fee and the platform — not you — owns the customer relationship, so demand you could serve directly leaks margin and repeat-contact data on every single order.",
        conclusion=f"Stand up a direct online order/book channel, surface it ahead of marketplace links, and offer a small direct-order perk to convert marketplace buyers onto your own channel.",
        expected_effect=f"Shifting {X}% of marketplace {unit}s to a direct channel recovers ~${X}/mo in fees plus owned customer data.",
        recommend_when={"state": "owned_order_channel_absent", "min_signal": "transactions"},
        tags=("digital", "channel", "ownership", v.family),
    )


def _gbp_messaging_unanswered(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Customers message your listing and hear nothing back",
        observation=f"{X}% of messages sent through your Google profile/website chat go unanswered for {X}+ hours, and the messaging feature is left half-configured.",
        reasoning=f"A listing message is a high-intent question from someone deciding right now, so a slow or absent reply drives that ready customer to a competitor who answers, and Google de-prioritizes profiles with poor response rates — which quietly suppresses the listing for everyone else too.",
        conclusion=f"Enable and route listing/chat messages to a covered inbox, set an auto-reply with hours, and answer within {X} minutes during open hours.",
        expected_effect=f"Connecting the high-intent messages you already receive is worth ~${X}/mo in chosen-then-lost {v.sale_unit}s.",
        recommend_when={"state": "messaging_unanswered", "min_signal": "gbp_profile"},
        tags=("digital", "funnel", "messaging", v.family),
    )


# ═══════════════════════ ENGAGEMENT / ATTRIBUTION / SEARCH ══════════════════
def _review_response_absent(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You never reply to reviews — your reputation is a one-sided conversation",
        observation=f"You've responded to only {X}% of the last {X} reviews, and every negative one sits with no owner reply.",
        reasoning=f"Owner responses are a public ranking and trust signal, so a prospect reading reviews for a {v.name.lower()} reads an unanswered complaint as unresolved and Google de-prioritizes disengaged profiles — which means silence both suppresses the listing and hands the deciding impression to your unhappiest customer.",
        conclusion=f"Reply to every review within {X} hours — thank the positives and offer a concrete fix on the negatives — and set a standing routine so none goes unanswered.",
        expected_effect=f"An active response routine lifts listing trust and choose-rate worth ~${X}/mo of recovered discovery.",
        recommend_when={"state": "reviews_unanswered", "min_signal": "review_stream"},
        tags=("digital", "reviews", "engagement", v.family),
    )


def _branded_search_competitor_ads(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Competitors are buying ads on your own name",
        observation=f"On searches for your business name, {X} competitor or aggregator ads sit above your listing, intercepting an estimated {X}% of your branded clicks.",
        reasoning=f"A branded search is your warmest demand because the customer already wants a {v.name.lower()} by name, so a rival's ad sitting above your result siphons buyers who were coming to you specifically — which means you lose the cheapest, highest-intent traffic there is before they ever reach your door.",
        conclusion=f"Claim the top of your own branded results: run a low-cost brand-defense ad and tighten the listing and title tags so the organic result also owns the first screen.",
        expected_effect=f"Recapturing intercepted branded clicks is worth ~${X}/mo of demand already asking for you.",
        recommend_when={"state": "branded_search_intercepted", "min_signal": "serp_rank"},
        tags=("digital", "search", "branded", v.family),
    )


def _analytics_attribution_blindspot(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You can't tell which channel actually brings customers in",
        observation=f"No conversion tracking ties bookings/orders back to a source, so {X}% of marketing spend runs across {X} channels you can't measure.",
        reasoning=f"Without attribution you're flying blind on spend, so for a {v.name.lower()} every untracked dollar means you can't separate the channel that drives {v.sale_unit}s from the one that drives nothing — which guarantees budget drifts to whatever is loudest rather than what actually converts.",
        conclusion=f"Set up basic conversion tracking (call tracking, booking/form events, UTM tags) and reallocate spend toward the {X} channels that prove out, away from the ones that don't.",
        expected_effect=f"Reallocating spend from unmeasured to proven channels recovers ~${X}/mo of wasted budget.",
        recommend_when={"state": "attribution_blindspot", "min_signal": "web_analytics"},
        tags=("digital", "analytics", "attribution", v.family),
    )


def _local_landing_page_missing(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Searchers across your service area land on a page that names none of them",
        observation=f"You serve {X} distinct neighborhoods/areas but run one generic page, so {X}% of local-intent queries hit content that mentions no specific place.",
        reasoning=f"Local search rewards relevance to the searcher's place, so a single generic page for a {v.name.lower()} that covers several areas ranks strongly for none of them — which means high-intent 'near me' searchers in each pocket of your catchment see a competitor whose page actually names their neighborhood.",
        conclusion=f"Build a dedicated, indexable page for each of the {X} core service areas with local details, then link them from the main site and your listing.",
        expected_effect=f"Area-specific pages open net-new local discovery worth ~${X}/mo across the catchment.",
        recommend_when={"state": "local_pages_missing", "min_signal": "serp_rank"},
        tags=("digital", "search", "local_pages", v.family),
    )


# ═══════════════════════ REGISTER ═══════════════════════════════════════════
register(
    # ── Listing / GBP / Maps ──
    Archetype(
        key="gbp_incomplete", domain="digital", name="GBP incomplete",
        build=_gbp_incomplete, situations=("untapped",),
        required_signals=("gbp_profile",),
        required_agents=("DigitalPresenceAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_GBP_UP,
        applies_keys=_ALL,
    ),
    Archetype(
        key="gbp_posts_unused", domain="digital", name="GBP posting slot idle",
        build=_gbp_posts_unused, situations=("untapped",),
        required_signals=("gbp_profile",),
        required_agents=("DigitalPresenceAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_GBP_UP + " Posting history additionally requires the localPosts read scope.",
        applies_keys=_ALL,
    ),
    Archetype(
        key="maps_ranking_vs_proximity", domain="digital", name="Maps rank proximity-bound",
        build=_maps_ranking_vs_proximity, situations=("baseline",),
        required_signals=("maps_geo_grid",),
        required_agents=("MapsRankAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_MAPS_UP,
        applies_keys=_ALL,
    ),
    Archetype(
        key="maps_photo_freshness", domain="digital", name="Maps photos stale",
        build=_maps_photo_freshness, situations=("untapped",),
        required_signals=("gbp_profile",),
        required_agents=("DigitalPresenceAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_GBP_UP + " Photo provenance (owner vs user) and recency come from the media read scope.",
        applies_keys=_ALL,
    ),
    Archetype(
        key="directory_category_miscategorized", domain="digital", name="Listing category mismatch",
        build=_directory_category_miscategorized, situations=("untapped",),
        required_signals=("gbp_profile",),
        required_agents=("DigitalPresenceAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_GBP_UP + " Category correctness is scored against the vertical taxonomy once the profile is read.",
        applies_keys=_ALL,
    ),
    Archetype(
        key="third_party_listing_inconsistency", domain="digital", name="NAP inconsistency",
        build=_third_party_listing_inconsistency, situations=("leaking",),
        required_signals=("listing_scan",),
        required_agents=("ListingConsistencyAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_NAP_UP,
        applies_keys=_ALL,
    ),
    Archetype(
        key="online_hours_inaccurate", domain="digital", name="Online hours inaccurate",
        build=_online_hours_inaccurate, situations=("leaking",),
        required_signals=("listing_scan",),
        required_agents=("ListingConsistencyAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_NAP_UP + " Hours accuracy additionally needs the merchant's true hours of operation to compare against.",
        applies_keys=_ALL,
    ),
    Archetype(
        key="zero_click_info_gap", domain="digital", name="Listing info gap",
        build=_zero_click_info_gap, situations=("untapped",),
        required_signals=("gbp_profile",),
        required_agents=("DigitalPresenceAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_GBP_UP + " Q&A and attribute coverage come from the questions/attributes read scopes.",
        applies_keys=_ALL,
    ),
    Archetype(
        key="search_visibility_for_category", domain="digital", name="Category search invisible",
        build=_search_visibility_for_category, situations=("untapped",),
        required_signals=("serp_rank",),
        required_agents=("MapsRankAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_MAPS_UP + " Organic page-one presence also needs a SERP crawler beyond the map-pack grid.",
        applies_keys=_ALL,
    ),
    # ── Website / conversion ──
    Archetype(
        key="website_conversion_low", domain="digital", name="Website conversion low",
        build=_website_conversion_low, situations=("baseline",),
        required_signals=("web_analytics",),
        required_agents=("OnlineFunnelAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_WEB_UP,
        applies_keys=_keys_with_channel("online", "booking"),
    ),
    Archetype(
        key="website_load_speed_drop", domain="digital", name="Website slow",
        build=_website_load_speed_drop, situations=("baseline",),
        required_signals=("web_analytics",),
        required_agents=("OnlineFunnelAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_WEB_UP + " Core Web Vitals/LCP come from a synthetic or field-data (CrUX) probe.",
        applies_keys=_keys_with_channel("online", "booking"),
    ),
    Archetype(
        key="mobile_experience_gap", domain="digital", name="Mobile conversion gap",
        build=_mobile_experience_gap, situations=("baseline",),
        required_signals=("web_analytics",),
        required_agents=("OnlineFunnelAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_WEB_UP + " Device-segmented conversion needs the analytics device dimension.",
        applies_keys=_ALL,
    ),
    Archetype(
        key="online_photos_quality", domain="digital", name="Online photos weak",
        build=_online_photos_quality, situations=("untapped",),
        required_signals=("gbp_profile",),
        required_agents=("DigitalPresenceAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_GBP_UP + " Photo quality/recency scoring runs on the fetched media set.",
        applies_keys=_ALL,
    ),
    Archetype(
        key="social_to_site_dropoff", domain="digital", name="Social-to-site dropoff",
        build=_social_to_site_dropoff, situations=("leaking",),
        required_signals=("web_analytics",),
        required_agents=("OnlineFunnelAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_WEB_UP + " Referral-source attribution from social needs UTM/referrer capture.",
        applies_keys=_ALL,
    ),
    Archetype(
        key="online_promo_not_surfaced", domain="digital", name="Promo not surfaced online",
        build=_online_promo_not_surfaced, situations=("leaking",),
        required_signals=("gbp_profile", "listing_scan"),
        required_agents=("DigitalPresenceAgent", "ListingConsistencyAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_GBP_UP + " Detecting whether a live offer appears across surfaces also needs the listing scan and the merchant's active promo list.",
        applies_keys=_ALL,
    ),
    # ── Menu / assortment (online) ──
    Archetype(
        key="online_menu_stale_missing", domain="digital", name="Online menu stale/missing",
        build=_online_menu_stale_missing, situations=("leaking",),
        required_signals=("listing_scan",),
        required_agents=("ListingConsistencyAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_NAP_UP + " Menu freshness compares published menus across surfaces to a current source menu.",
        applies_families=("food_service", "personal_care", "health_wellness"),
    ),
    Archetype(
        key="online_menu_pricing_mismatch", domain="digital", name="Online price mismatch",
        build=_online_menu_pricing_mismatch, situations=("leaking",),
        required_signals=("listing_scan", "transactions"),
        required_agents=("ListingConsistencyAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade=_NAP_UP + " The POS side (transactions) gives true prices; only the published-price scrape is missing, so this is PARTIAL.",
        applies_families=("food_service",),
    ),
    Archetype(
        key="online_vs_instore_assortment_gap", domain="digital", name="Online assortment gap",
        build=_online_vs_instore_assortment_gap, situations=("leaking",),
        required_signals=("web_analytics", "transactions"),
        required_agents=("OnlineFunnelAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade=_WEB_UP + " In-store assortment comes from transactions; only the online catalog snapshot is missing, so this is PARTIAL.",
        applies_keys=_keys_with_channel("online"),
    ),
    Archetype(
        key="review_velocity_online", domain="digital", name="Review velocity stalled",
        build=_review_velocity_online, situations=("baseline", "declining"),
        required_signals=("review_stream",),
        required_agents=("DigitalPresenceAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="DigitalPresenceAgent: pull review timestamps from GBP + platforms to compute velocity/recency (distinct from the marketing domain's score-based reputation); no review timestamp stream is ingested today.",
        applies_keys=_ALL,
    ),
    # ── Owned surface / channel ownership ──
    Archetype(
        key="no_website_presence", domain="digital", name="No owned website",
        build=_no_website_presence, situations=("untapped",),
        required_signals=("listing_scan",),
        required_agents=("ListingConsistencyAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_NAP_UP + " Detecting the absence of an owned site (vs only third-party listings) comes from the same listing scan.",
        applies_keys=_ALL,
    ),
    Archetype(
        key="online_ordering_channel_absent", domain="digital", name="Owned order channel absent",
        build=_online_ordering_channel_absent, situations=("untapped",),
        required_signals=("transactions",),
        required_agents=("OnlineFunnelAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade=_WEB_UP + " Marketplace vs direct split is partly visible in transactions (channel tag); only the owned-order-page presence check is missing, so this is PARTIAL.",
        applies_keys=_keys_with_channel("online", "delivery"),
    ),
    Archetype(
        key="gbp_messaging_unanswered", domain="digital", name="Listing messaging unanswered",
        build=_gbp_messaging_unanswered, situations=("leaking",),
        required_signals=("gbp_profile",),
        required_agents=("DigitalPresenceAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_GBP_UP + " Message volume and response latency require the Business Messages read scope.",
        applies_keys=_ALL,
    ),
    # ── Funnel: call / reserve / order ──
    Archetype(
        key="click_to_call_friction", domain="digital", name="Click-to-call friction",
        build=_click_to_call_friction, situations=("leaking",),
        required_signals=("web_analytics", "phone_call_logs"),
        required_agents=("OnlineFunnelAgent", "PhoneInsightAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade=_WEB_UP + " The answered-call side exists in phone_call_logs; only the click-to-call tap event is missing, so the join is PARTIAL.",
        applies_keys=_keys_with_channel("phone"),
    ),
    Archetype(
        key="online_reservation_friction", domain="digital", name="Booking flow friction",
        build=_online_reservation_friction, situations=("leaking",),
        required_signals=("web_analytics",),
        required_agents=("OnlineFunnelAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_WEB_UP + " Booking funnel steps require event instrumentation on the reservation flow.",
        applies_keys=_keys_with_channel("booking"),
    ),
    Archetype(
        key="online_booking_lead_time_friction", domain="digital", name="Booking lead-time too long",
        build=_online_booking_lead_time_friction, situations=("leaking",),
        required_signals=("web_analytics",),
        required_agents=("OnlineFunnelAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_WEB_UP + " Soonest-bookable-slot vs requested-date needs the booking system's availability feed.",
        applies_keys=_keys_with_any_flag("appointment_based"),
    ),
    Archetype(
        key="online_waitlist_booking_adoption", domain="digital", name="Online waitlist unused",
        build=_online_waitlist_booking_adoption, situations=("untapped",),
        required_signals=("web_analytics",),
        required_agents=("OnlineFunnelAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_WEB_UP + " Peak-balk estimation needs join-ahead instrumentation and door/queue counts.",
        applies_keys=_keys_with_any_flag("walk_in_heavy", "table_service"),
    ),
    Archetype(
        key="online_order_funnel_dropoff", domain="digital", name="Order funnel dropoff",
        build=_online_order_funnel_dropoff, situations=("leaking",),
        required_signals=("web_analytics", "transactions"),
        required_agents=("OnlineFunnelAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade=_WEB_UP + " Completed online orders exist in transactions; only the pre-checkout funnel events are missing, so this is PARTIAL.",
        applies_keys=_keys_with_channel("online"),
    ),
    Archetype(
        key="cart_abandonment_online", domain="digital", name="Cart abandonment",
        build=_cart_abandonment_online, situations=("leaking",),
        required_signals=("web_analytics",),
        required_agents=("OnlineFunnelAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_WEB_UP + " Cart-level events and step attribution require checkout instrumentation.",
        applies_keys=tuple(set(_keys_with_channel("online")) & set(_keys_with_any_flag("inventory_heavy"))),
    ),
    Archetype(
        key="qr_table_order_adoption", domain="digital", name="QR at-table ordering untapped",
        build=_qr_table_order_adoption, situations=("untapped",),
        required_signals=("web_analytics", "transactions"),
        required_agents=("OnlineFunnelAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_WEB_UP + " At-table self-order adoption needs QR-order session events tied to table/check.",
        applies_keys=_keys_with_any_flag("table_service"),
    ),
    # ── Engagement / attribution / search (new) ──
    Archetype(
        key="review_response_absent", domain="digital", name="Reviews unanswered",
        build=_review_response_absent, situations=("leaking",),
        required_signals=("review_stream",),
        required_agents=("DigitalPresenceAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="DigitalPresenceAgent: pull each review with its owner-response status/timestamp from GBP + platforms to compute response rate and latency (distinct from review velocity); no review-response stream is ingested today.",
        applies_keys=_ALL,
    ),
    Archetype(
        key="branded_search_competitor_ads", domain="digital", name="Branded search intercepted",
        build=_branded_search_competitor_ads, situations=("leaking",),
        required_signals=("serp_rank",),
        required_agents=("MapsRankAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_MAPS_UP + " Branded-term interception additionally needs a SERP crawl of the business-name query to detect competitor/aggregator ads above the listing.",
        applies_keys=_ALL,
    ),
    Archetype(
        key="analytics_attribution_blindspot", domain="digital", name="Attribution blindspot",
        build=_analytics_attribution_blindspot, situations=("baseline",),
        required_signals=("web_analytics",),
        required_agents=("OnlineFunnelAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_WEB_UP + " Source-to-conversion attribution needs UTM/referrer capture plus call/booking event tracking joined to transactions.",
        applies_keys=_keys_with_channel("online", "booking", "phone"),
    ),
    Archetype(
        key="local_landing_page_missing", domain="digital", name="Local landing pages missing",
        build=_local_landing_page_missing, situations=("untapped",),
        required_signals=("serp_rank",),
        required_agents=("MapsRankAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade=_MAPS_UP + " Per-area page coverage also needs a crawl of the merchant's own site to map which service areas have a dedicated indexable page.",
        applies_keys=_ALL,
    ),
)
