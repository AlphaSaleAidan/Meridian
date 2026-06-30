"""
Domain: PRODUCTS / MENU & CATALOG ENGINEERING.

Each archetype is a distinct reasoning pattern about the catalog itself — which
items to protect, reprice, promote, cut, bundle, attach, or re-price-ladder.
Specialization per vertical changes what an "item" is (a menu item vs a retail
SKU vs a billable service vs a hospitality offering) and WHO performs the lever
(a barista's suggestive sell, a stylist's retail shelf, a service-advisor's
upsell), so a café insight and an optometry insight are genuinely different
reasoning — not a relabeled number.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register


def _item(v: Vertical) -> str:
    """What one catalog line is called for this vertical."""
    if v.family == "food_service":
        return "menu item"
    if v.family == "retail":
        return "SKU"
    if v.family == "hospitality":
        return "offering"
    return "service"


def _seller(v: Vertical) -> str:
    """Who is positioned to make the suggestive sell."""
    return v.staff_role


# ── Menu-engineering quadrants ───────────────────────────────────────────────
def _star_protect(v: Vertical, situation: str) -> Built:
    item = _item(v)
    extra = {
        "declining": " Volume on these has slipped lately — defend it now, before a star quietly demotes to a plowhorse.",
    }.get(situation, "")
    return Built(
        title=f"Protect your {X} star {item}s — high margin AND high volume",
        observation=f"{X} {item}s sit in the star quadrant: each clears ${X} margin and together they carry {X}% of {v.sale_unit}s.",
        reasoning=f"Stars win on BOTH axes, so any erosion — a stockout, a quality slip, an absent-minded price hike — costs you twice (the margin and the traffic that {item} anchors). They are assets to defend, not levers to squeeze.{extra}",
        conclusion=f"Guarantee availability and consistency on these {X}; hold price unless input costs move; keep them where the eye lands first and have {_seller(v)}s name them by default.",
        expected_effect=f"Defending the stars protects ~${X}/mo of margin that no other {item} replaces.",
        recommend_when={"state": "star_quadrant", "min_signal": "product_margin"},
        tags=("products", "menu_engineering", "star", v.family),
    )


def _plowhorse_reprice(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"Your plowhorse {item}s are popular but barely profitable",
        observation=f"{X} {item}s account for {X}% of {v.sale_unit}s but only {X}% of margin — each sells well at just ${X} contribution.",
        reasoning=f"High volume on a thin margin means a small unit-economics fix is amplified by every sale: a modest price move, a portion/recipe re-engineer, or a cheaper input flows straight to the bottom line precisely BECAUSE the volume is already there.",
        conclusion=f"Raise price by a single increment OR re-engineer cost on these {X} {item}s; volume is sticky enough to absorb it, so test on the top {X} first.",
        expected_effect=f"A ${X} margin gain × this volume is worth ~${X}/mo with negligible demand loss.",
        recommend_when={"state": "plowhorse_quadrant", "min_signal": "product_margin"},
        tags=("products", "menu_engineering", "plowhorse", v.family),
    )


def _puzzle_promote(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"High-margin {item}s nobody orders — promote your puzzles",
        observation=f"{X} {item}s earn ${X}+ margin each — your best per-unit economics — yet each moves under {X} {v.sale_unit}s/week.",
        reasoning=f"Puzzles already clear the hard part (margin); they only lack exposure. Because each unit pays so well, even a small volume lift is high-yield — the fix is visibility and a recommendation, not a price change.",
        conclusion=f"Feature these {X} prominently, sample/cross-sell them, and have {_seller(v)}s suggest one by name; measure trial over {X} weeks.",
        expected_effect=f"Lifting each puzzle by just {X} {v.sale_unit}s/week adds ~${X}/mo at their premium margin.",
        recommend_when={"state": "puzzle_quadrant", "min_signal": "product_margin"},
        tags=("products", "menu_engineering", "puzzle", v.family),
    )


def _dog_cut(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"Cut the dogs — {X} {item}s that are neither popular nor profitable",
        observation=f"{X} {item}s sit low on both axes: under {X} {v.sale_unit}s/week each AND below-average margin.",
        reasoning=f"Dogs don't just fail to earn — they tax the whole catalog: menu real estate, prep/training time, holding stock, and decision friction for the customer. Removing them concentrates demand onto items that do pay.",
        conclusion=f"Retire or rework these {X} {item}s; redirect the freed space/attention to your stars and puzzles, and watch for demand migrating up.",
        expected_effect=f"Pruning the long tail recovers ~{X} hours of prep/handling and simplifies choice, lifting attach on retained {item}s.",
        recommend_when={"state": "dog_quadrant", "min_signal": "product_margin"},
        tags=("products", "menu_engineering", "dog", v.family),
    )


# ── Attach / bundle / basket ─────────────────────────────────────────────────
def _attach_gap(v: Vertical, situation: str) -> Built:
    item = _item(v)
    if v.family == "food_service":
        pair = "a side, drink, or dessert"
    elif v.family == "retail":
        pair = "the natural companion SKU"
    else:
        pair = "the obvious add-on or aftercare product"
    return Built(
        title=f"Your top {item} sells naked — the attach is missing",
        observation=f"{X}% of tickets containing your lead {item} include nothing else, even though {pair} pairs with it on {X}% of the tickets that do attach.",
        reasoning=f"A natural add-on that's already proven to pair (high margin, low friction) is being left off most baskets — almost always a prompt problem, not a demand one. The traffic to capture it is already at the counter.",
        conclusion=f"Make the attach the default ask: have {_seller(v)}s suggest {pair} on every lead-{item} sale, or surface it at the point of choice.",
        expected_effect=f"Moving attach from {X}% to {X}% on this {item} alone is worth ~${X}/mo.",
        recommend_when={"state": "attach_gap", "min_signal": "basket"},
        tags=("products", "attach", v.family),
    )


def _bundle_opportunity(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"Two {item}s sell together constantly — formalize the bundle",
        observation=f"{X} {item} pairs co-occur on {X}% of multi-line tickets, yet there's no packaged price for them.",
        reasoning=f"Customers are already self-assembling these combinations. Pricing them as one bundle raises average {v.sale_unit} value and protects margin (you set the blended price) while making the easy choice easier — a packaging move, distinct from merely prompting an add-on.",
        conclusion=f"Create a named, single-price bundle for the top {X} pairs at a small discount to the sum; track bundle take-rate vs à-la-carte.",
        expected_effect=f"A {X}% bundle take-rate lifts average ticket by ${X}, ~${X}/mo.",
        recommend_when={"state": "bundle_candidate", "min_signal": "basket"},
        tags=("products", "bundle", v.family),
    )


def _basket_affinity(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"Frequently-bought-together {item}s aren't merchandised together",
        observation=f"{X} {item} pairs show strong basket affinity (lift > {X}×) but sit in different sections / screens, so the cross-sell is left to chance.",
        reasoning=f"Affinity is latent demand: customers want both, but placement — not price or a verbal prompt — is the barrier. Co-locating proven pairs converts an existing intent into an extra line with zero discounting (distinct from a priced bundle).",
        conclusion=f"Place the top {X} affinity partners adjacent (shelf, endcap, combo screen, or recommended-with), and re-measure co-attach.",
        expected_effect=f"Adjacency typically lifts pair attach by {X}%, ~${X}/mo in incremental {v.sale_unit}s.",
        recommend_when={"state": "unmerchandised_affinity", "min_signal": "basket"},
        tags=("products", "merchandising", "affinity", v.family),
    )


def _combo_attach(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Combo / meal-deal attach is below benchmark",
        observation=f"Only {X}% of eligible {v.sale_unit}s convert to a combo, versus a {X}% benchmark for {v.name.lower()}s.",
        reasoning=f"The combo is your highest-margin, fastest-throughput configuration — it lifts ticket AND speeds the line. A low combo rate at the {v.channels[0]} point means the upgrade prompt is weak or the price gap is mis-set, not that customers won't take it.",
        conclusion=f"Re-price the combo gap to an easy yes and script the upsize at order; A/B the prompt on the {X} highest-traffic items.",
        expected_effect=f"Each point of combo rate is ~${X}/mo here; closing to benchmark is ~${X}/mo.",
        recommend_when={"state": "combo_below_benchmark", "min_signal": "basket"},
        tags=("products", "attach", "combo", v.family),
    )


def _retail_attach_to_service(v: Vertical, situation: str) -> Built:
    if v.key in ("auto_repair", "oil_change", "tire_shop"):
        goods, who = "parts / fluids / accessories", "service advisor"
    elif v.key == "optometry":
        goods, who = "frames and lens add-ons", "optician"
    elif v.key in ("salon", "nail_salon", "barbershop", "spa"):
        goods, who = "take-home retail (haircare / aftercare)", "stylist"
    elif v.key in ("dental", "vet"):
        goods, who = "home-care and product add-ons", "front-desk"
    else:
        goods, who = "take-home product", _seller(v)
    return Built(
        title=f"You perform the {v.sale_unit} but miss the {goods} attach",
        observation=f"Only {X}% of {v.sale_unit}s leave with {goods}, though the captive, just-served customer is the easiest retail sale you get.",
        reasoning=f"A service business has a trust window the moment work is done: the {who} has demonstrated expertise and the customer is primed. Retail attach here is near-pure margin and requires no new traffic — letting it sit at {X}% leaves the highest-intent buyer un-asked.",
        conclusion=f"Give each {who} one recommended product per {v.sale_unit} tied to the work performed; track retail attach as a per-{_seller(v)} number.",
        expected_effect=f"Lifting retail attach to {X}% adds ~${X}/mo at retail margin with no added service capacity.",
        recommend_when={"state": "retail_attach_gap", "min_signal": "basket"},
        tags=("products", "attach", "retail_in_service", v.family),
    )


def _low_attach_high_traffic(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"Your busiest {item} has your worst attach rate",
        observation=f"Your #1-traffic {item} appears on {X}% of tickets but attaches a second line only {X}% of the time — below the catalog average of {X}%.",
        reasoning=f"Leverage scales with traffic: a weak attach on a niche item is rounding error, but the same gap on your single most-purchased {item} is the largest dollar lever in the catalog. The volume that makes it your hero is exactly what makes its low attach expensive.",
        conclusion=f"Fix attach on THIS {item} first — pair it with a proven companion and prompt it every time — before optimizing anything lower-traffic.",
        expected_effect=f"Each attach point on the hero {item} is ~${X}/mo — the catalog's highest-yield single fix.",
        recommend_when={"state": "hero_low_attach", "min_signal": "basket"},
        tags=("products", "attach", "leverage", v.family),
    )


def _modifier_underused(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Paid modifiers / customizations are barely chosen",
        observation=f"Add-on modifiers (extra portions, premium swaps, upsizes) attach to only {X}% of {v.sale_unit}s despite a ${X} average uplift when chosen.",
        reasoning=f"Modifiers are upsell WITHIN an item — no new product, no extra prep line, pure ticket lift. A low modifier rate means the option isn't surfaced at the moment of choice, not that customers don't want the upgrade.",
        conclusion=f"Surface the top {X} modifiers as one-tap defaults at order and have {_seller(v)}s offer the premium swap by name.",
        expected_effect=f"Doubling modifier attach is worth ~${X}/mo on existing volume.",
        recommend_when={"state": "modifier_underused", "min_signal": "transactions"},
        tags=("products", "modifier", "upsell", v.family),
    )


# ── Lifecycle / exposure ─────────────────────────────────────────────────────
def _new_item_underexposed(v: Vertical, situation: str) -> Built:
    item = _item(v)
    extra = {
        "emerging": " Early repeat rate on it is strong, so the ceiling is real — push exposure before the launch window closes.",
    }.get(situation, "")
    return Built(
        title=f"Your new {item} converts well but almost nobody tries it",
        observation=f"A recently added {item} is reached by only {X}% of customers, yet of those who try it, {X}% reorder within {X} visits.",
        reasoning=f"Strong repeat with weak trial is a discovery problem, not a product problem: the {item} earns loyalty once tasted but isn't getting in front of enough people during its launch window.{extra}",
        conclusion=f"Run a time-boxed push — feature placement, a trial offer, and a {_seller(v)} recommendation — to force first trial; hold price.",
        expected_effect=f"Lifting trial to {X}% at the proven repeat rate compounds to ~${X}/mo within {X} months.",
        recommend_when={"state": "new_item_low_trial", "min_signal": "daily_product_performance"},
        tags=("products", "lifecycle", "new_item", v.family),
    )


def _category_cannibalization(v: Vertical, situation: str) -> Built:
    item = _item(v)
    extra = {
        "leaking": " Net category revenue is flat-to-down while the new item grows — confirming substitution, not expansion.",
    }.get(situation, "")
    return Built(
        title=f"A newer {item} is cannibalizing a higher-margin sibling",
        observation=f"Since the newer {item} launched, a higher-margin sibling's {v.sale_unit}s fell {X}% while total category volume rose only {X}%.",
        reasoning=f"Growth that comes by stealing from a better-margin item isn't growth — it's a margin downgrade hiding inside a volume number. The customer was going to buy from the category anyway; you just moved them to the cheaper line.{extra}",
        conclusion=f"Re-price or re-position to protect the margin leader: widen the price/quality gap, or aim the newer {item} at a genuinely new occasion rather than the same shelf.",
        expected_effect=f"Halting the margin mix-shift recovers ~${X}/mo without losing the volume.",
        recommend_when={"state": "cannibalization", "min_signal": "product_margin"},
        tags=("products", "cannibalization", "mix", v.family),
    )


def _seasonal_item_window(v: Vertical, situation: str) -> Built:
    item = _item(v)
    if situation == "seasonal_trough":
        lever = f"sunset the off-season {item}s and free the space/prep for what sells now"
        why = "carrying a seasonal line past its window ties up prep, stock, and menu space for demand that has left"
        eff = f"clearing the dead seasonal line recovers ~${X}/mo of space and handling"
    else:  # seasonal_peak
        lever = f"pre-stage the seasonal {item}s and brief {_seller(v)}s before the curve, not after"
        why = "seasonal demand arrives as a sharp curve; being ready a week early captures the front of it while competitors are still ramping"
        eff = f"capturing the front of the curve is worth ~${X}/mo in peak-season {v.sale_unit}s"
    return Built(
        title=f"Time your seasonal {item}s to the demand curve, not the calendar",
        observation=f"Your seasonal {item}s do {X}% of their volume in a {X}-week window, but launch/teardown lags the curve by ~{X} weeks.",
        reasoning=f"For a seasonal catalog, {why}.",
        conclusion=f"This season, {lever}.",
        expected_effect=eff,
        recommend_when={"state": "seasonal_item_window", "min_signal": "daily_product_performance"},
        tags=("products", "seasonal", "timing", v.family),
    )


def _lto_cadence(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"Your limited-time {item}s run on no rhythm",
        observation=f"LTOs appear {X} times/year at irregular gaps; each historically lifts traffic {X}% for {X} weeks, then fades with no successor queued.",
        reasoning=f"LTOs work by manufacturing novelty and a reason to return — but only if there's a predictable cadence customers learn to anticipate. Sporadic drops waste the traffic spike because nothing catches the lapsed visitor on the way back down.",
        conclusion=f"Set a fixed LTO calendar (every {X} weeks) and queue the next {item} before the current one ends so the lift never fully decays.",
        expected_effect=f"A steady cadence smooths and compounds the per-LTO lift to ~${X}/mo in repeat traffic.",
        recommend_when={"state": "lto_no_cadence", "min_signal": "daily_product_performance"},
        tags=("products", "lto", "cadence", v.family),
    )


def _daypart_menu_gap(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"A strong {item} sells in only one daypart",
        observation=f"{X} {item}s do {X}% of their volume in a single daypart and almost nothing outside it, while the adjacent daypart runs thin on options.",
        reasoning=f"An item proven to sell is being artificially confined to one part of the day. The same kitchen/stock can extend it into a soft daypart, lifting low-traffic hours with a product you already make — far cheaper than inventing something new.",
        conclusion=f"Extend the top {X} into the adjacent soft daypart (a tweak in framing/positioning), and measure incremental {v.sale_unit}s there.",
        expected_effect=f"Filling the soft daypart with proven {item}s is worth ~${X}/mo at little added cost.",
        recommend_when={"state": "daypart_confined", "min_signal": "daily_product_performance"},
        tags=("products", "daypart", "menu", v.family),
    )


# ── Concentration / structure ────────────────────────────────────────────────
def _hero_overdependence(v: Vertical, situation: str) -> Built:
    item = _item(v)
    extra = {
        "concentrated": " A single supply hiccup or taste shift on this one {item} would crater the day — the concentration is now a standalone risk.".replace("{item}", item),
    }.get(situation, "")
    return Built(
        title=f"One {item} carries too much of your revenue",
        observation=f"Your single top {item} drives {X}% of {v.sale_unit}s; the next {X} combined do less.",
        reasoning=f"Over-reliance on one {item} is fragility: a stockout, a price-sensitive customer, a competitor's copy, or simple fatigue with that one line puts an outsized share of revenue at risk with no cushion behind it.{extra}",
        conclusion=f"Build a #2 deliberately — promote a high-potential puzzle into a co-hero — while fiercely protecting the current one; don't cut, diversify.",
        expected_effect=f"Growing a credible second hero de-risks ~{X}% of revenue currently riding one {item}.",
        recommend_when={"state": "hero_concentration", "min_signal": "product_performance"},
        tags=("products", "concentration", "risk", v.family),
    )


def _portfolio_margin_concentration(v: Vertical, situation: str) -> Built:
    item = _item(v)
    extra = {
        "concentrated": " These few {item}s also share an input/supplier, so the margin base is even thinner than the count suggests.".replace("{item}", item),
    }.get(situation, "")
    return Built(
        title=f"Most of your margin comes from a handful of {item}s",
        observation=f"{X} {item}s generate {X}% of total margin while representing only {X}% of {v.sale_unit}s — your profit is narrower than your sales look.",
        reasoning=f"Revenue concentration and MARGIN concentration are different risks: you can look diversified by volume yet have nearly all your profit resting on a few lines. If any of those few slip on cost or demand, profit falls far faster than revenue.",
        conclusion=f"Identify the {X} margin pillars and protect their unit economics first; then deliberately raise margin on the next tier so profit isn't a single-point failure.{extra}",
        expected_effect=f"Broadening the margin base guards ~{X}% of profit now dependent on {X} {item}s.",
        recommend_when={"state": "margin_concentration", "min_signal": "product_margin"},
        tags=("products", "concentration", "margin", v.family),
    )


def _sku_proliferation(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"Catalog bloat — a long tail of {item}s that don't earn their slot",
        observation=f"The bottom {X}% of {item}s produce under {X}% of {v.sale_unit}s, yet each adds variants, prep steps, or stock to manage.",
        reasoning=f"Every extra {item} has a hidden cost the sales number ignores: training, prep/holding complexity, slower service, and choice overload that depresses conversion on your winners. Past a point, breadth subtracts.",
        conclusion=f"Rationalize the tail — consolidate near-duplicate variants and retire the weakest {X} — to speed service and sharpen the menu's signal.",
        expected_effect=f"Trimming the tail cuts complexity cost and typically lifts conversion on retained {item}s by {X}%.",
        recommend_when={"state": "sku_bloat", "min_signal": "product_performance"},
        tags=("products", "complexity", "rationalization", v.family),
    )


def _category_breadth_gap(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"A category your basket implies — but you don't carry",
        observation=f"{X}% of baskets stop short at a category boundary where customers clearly want an adjacent line you don't stock; comparable {v.name.lower()}s attach it on {X}% of tickets.",
        reasoning=f"This is the inverse of bloat: a genuine hole in the lineup. The demand signal (incomplete baskets, requests, competitor attach) shows customers would buy an adjacent category here, so every visit forfeits a line you could have owned.",
        conclusion=f"Pilot a tight {X}-SKU entry into the missing category beside its natural partner and measure attach before expanding.",
        expected_effect=f"Capturing the adjacent category at a {X}% attach is worth ~${X}/mo in net-new basket value.",
        recommend_when={"state": "category_gap", "min_signal": "basket"},
        tags=("products", "assortment", "breadth", v.family),
    )


# ── Price ladder / presentation ──────────────────────────────────────────────
def _price_point_gap(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"A missing rung in your price ladder",
        observation=f"Your {item} prices cluster at {X} points with a gap of ${X} between tiers — customers either trade down hard or balk at the jump.",
        reasoning=f"A ladder with a missing rung loses two groups at once: value seekers with no entry below the cluster, and would-be trade-ups facing too big a leap to the premium. The gap caps both your floor traffic and your mix-up potential.",
        conclusion=f"Introduce one {item} at the missing price point (good-better-best), positioned to catch the trade-up rather than discount the existing tier.",
        expected_effect=f"Filling the rung captures both lost trade-downs and easier trade-ups, ~${X}/mo in mix.",
        recommend_when={"state": "price_ladder_gap", "min_signal": "product_performance"},
        tags=("products", "price_architecture", "ladder", v.family),
    )


def _price_anchor_missing(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"No premium anchor — your mid-tier looks expensive",
        observation=f"Your lineup tops out at ${X}; with no higher anchor, {X}% of customers default to the cheapest {item} rather than the mid-tier.",
        reasoning=f"Absent a visible premium option, the highest price present becomes the reference point and everything reads 'expensive.' A deliberate high anchor reframes the mid-tier as the sensible choice — the goal isn't to sell the anchor, it's to shift the mix upward (distinct from filling a ladder gap).",
        conclusion=f"Add a clear premium {item} above the range as a decoy/anchor and watch mid-tier share rise even if the anchor itself sells little.",
        expected_effect=f"Anchoring typically shifts {X}% of mix up one tier, ~${X}/mo with no discounting.",
        recommend_when={"state": "no_premium_anchor", "min_signal": "product_performance"},
        tags=("products", "price_architecture", "anchor", v.family),
    )


def _charm_pricing_untested(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"Round price endings you've never tested",
        observation=f"{X}% of your {item}s end in round numbers (e.g. ${X}.00) at price points where ending and presentation measurably move conversion.",
        reasoning=f"Price ENDINGS and how a number is displayed change perceived value independent of the actual price — a presentation lever, not a discount. Untested round endings leave a free, reversible conversion test on the table.",
        conclusion=f"A/B charm vs round endings on the top {X} {item}s for {X} weeks and keep whichever wins; change nothing else.",
        expected_effect=f"A typical ending lift of {X}% on this volume is ~${X}/mo at zero margin cost.",
        recommend_when={"state": "price_ending_untested", "min_signal": "product_performance"},
        tags=("products", "pricing_presentation", v.family),
    )


def _discount_dependency(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"{X} {item}s that only move when discounted",
        observation=f"{X}% of these {item}s' {v.sale_unit}s happen on promotion; at full price they nearly stall.",
        reasoning=f"A line that only sells on discount has trained its customers to wait for the markdown — eroding both margin and reference price. The promo isn't incremental demand, it's a recurring margin leak disguised as a sale.",
        conclusion=f"Break the cycle: either reset to a credible everyday price and stop the promo, or cut the {item} if it can't stand without the discount.",
        expected_effect=f"Ending habitual discounting on these recovers ~${X}/mo of given-away margin.",
        recommend_when={"state": "discount_dependent", "min_signal": "transactions"},
        tags=("products", "pricing", "discount_leak", v.family),
    )


# ── Differentiation / repeat ─────────────────────────────────────────────────
def _signature_undermarketed(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"Your signature {item} isn't doing differentiation work",
        observation=f"A distinctive, hard-to-copy {item} is ordered by only {X}% of customers and isn't featured in any first-impression surface.",
        reasoning=f"A signature {item} is your cheapest differentiation — the thing customers describe to others and return for. Leaving it under-marketed wastes the one line competitors can't easily match; it should headline the experience, not hide in the list.",
        conclusion=f"Make the signature {item} the hero of menu/shelf/first contact and arm {_seller(v)}s with its story; treat it as brand, not just SKU.",
        expected_effect=f"Elevating the signature lifts trial and word-of-mouth, ~${X}/mo plus repeat-visit gains.",
        recommend_when={"state": "signature_undermarketed", "min_signal": "product_performance"},
        tags=("products", "differentiation", "signature", v.family),
    )


def _trial_to_repeat_gateway(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"Your gateway {item} drives repeat — but few customers ever start it",
        observation=f"Customers whose first purchase includes a specific {item} return {X}% more often, yet only {X}% of first-timers are steered to it.",
        reasoning=f"In a repeat-purchase business, the FIRST {item} a customer tries predicts whether they come back. A proven gateway that converts trial into loyalty is being left to chance at the exact moment — the first visit — when it matters most.",
        conclusion=f"Route first-time customers to the gateway {item} (intro offer, default recommendation) and measure {X}-visit retention against a control.",
        expected_effect=f"Lifting gateway adoption among first-timers compounds into ~${X}/mo of retained lifetime value.",
        recommend_when={"state": "gateway_underused", "min_signal": "transactions"},
        tags=("products", "retention", "gateway", v.family),
    )


def _premium_tier_undersold(v: Vertical, situation: str) -> Built:
    item = _item(v)
    return Built(
        title=f"Your premium {item} tier is undersold for a high-ticket business",
        observation=f"The top-tier {item} is chosen on only {X}% of {v.sale_unit}s, though customers here already accept ${X}+ transactions.",
        reasoning=f"In a high-ticket category the customer has already cleared the price-objection hurdle, so the gap between mid and premium is small relative to the {v.sale_unit} — yet the upgrade isn't being presented with its value framed. The trade-up is the easiest incremental margin you have.",
        conclusion=f"Have {_seller(v)}s present the premium {item} as the default consult/recommendation with its value spelled out; track tier mix.",
        expected_effect=f"Shifting {X}% of mix to premium at this ticket size is worth ~${X}/mo.",
        recommend_when={"state": "premium_undersold", "min_signal": "transactions"},
        tags=("products", "trade_up", "premium", v.family),
    )


def _service_package_upsell(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"One-off {v.sale_unit}s that should be packages / memberships",
        observation=f"{X}% of {v.sale_unit}s are sold à la carte even though {X}% of those customers return within {X} weeks — clear package/membership candidates.",
        reasoning=f"Customers already behaving like members are paying per-visit prices and staying free to churn. Packaging recurring demand locks in revenue, raises lifetime value, and smooths cash — and the buyers most likely to convert are visible in their own repeat pattern.",
        conclusion=f"Offer a package/membership to repeat customers at their next visit (priced below their effective per-{v.sale_unit} run-rate) and track conversion.",
        expected_effect=f"Converting {X}% of qualifying repeaters to packages adds ~${X}/mo of committed revenue.",
        recommend_when={"state": "package_upsell", "min_signal": "transactions"},
        tags=("products", "packaging", "membership", v.family),
    )


# ── Registration ─────────────────────────────────────────────────────────────
_MARGIN_FUSION = (
    "MarginFusionAgent: join a cost/recipe-cost source (COGS, supplier invoices, "
    "recipe BOM) to product_performance to compute per-item contribution margin — "
    "cost data is not yet ingested, so margin-quadrant work runs blind without it."
)
_MARKET_BASKET = (
    "MarketBasketAgent: build item-pair co-occurrence + lift from transaction "
    "line items (requires line-level itemization on transactions) to drive "
    "attach, bundle, and affinity reasoning."
)

register(
    Archetype(
        key="star_protect", domain="products", name="Protect menu stars",
        build=_star_protect, situations=("baseline", "declining"),
        required_signals=("product_performance", "product_margin"),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_MARGIN_FUSION,
    ),
    Archetype(
        key="plowhorse_reprice", domain="products", name="Reprice plowhorses",
        build=_plowhorse_reprice, situations=("baseline",),
        required_signals=("product_performance", "product_margin"),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_MARGIN_FUSION,
    ),
    Archetype(
        key="puzzle_promote", domain="products", name="Promote puzzles",
        build=_puzzle_promote, situations=("baseline",),
        required_signals=("product_performance", "product_margin"),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_MARGIN_FUSION,
    ),
    Archetype(
        key="dog_cut", domain="products", name="Cut the dogs",
        build=_dog_cut, situations=("baseline",),
        required_signals=("product_performance", "product_margin"),
        required_agents=("ProductAnalyzer",),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_MARGIN_FUSION,
    ),
    Archetype(
        key="attach_gap", domain="products", name="Missing attach",
        build=_attach_gap, situations=("baseline",),
        required_signals=("transactions",),
        required_agents=("ProductAnalyzer", "AttachAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_MARKET_BASKET,
    ),
    Archetype(
        key="bundle_opportunity", domain="products", name="Bundle opportunity",
        build=_bundle_opportunity, situations=("baseline",),
        required_signals=("transactions",),
        required_agents=("ProductAnalyzer", "AttachAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_MARKET_BASKET,
    ),
    Archetype(
        key="basket_affinity", domain="products", name="Unmerchandised affinity",
        build=_basket_affinity, situations=("baseline",),
        applies_families=("retail", "food_service"),
        required_signals=("transactions",),
        required_agents=("ProductAnalyzer", "AttachAnalyzer"),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_MARKET_BASKET,
    ),
    Archetype(
        key="combo_attach_below_benchmark", domain="products", name="Low combo attach",
        build=_combo_attach, situations=("baseline",),
        applies_keys=("qsr", "food_truck", "ghost_kitchen", "cafe", "bar"),
        required_signals=("transactions",),
        required_agents=("ProductAnalyzer", "AttachAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_MARKET_BASKET,
    ),
    Archetype(
        key="retail_attach_to_service", domain="products", name="Retail attach to service",
        build=_retail_attach_to_service, situations=("baseline",),
        applies_keys=("salon", "nail_salon", "barbershop", "spa", "optometry",
                      "auto_repair", "oil_change", "tire_shop", "dental", "vet", "pet_store"),
        required_signals=("transactions",),
        required_agents=("ProductAnalyzer", "AttachAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_MARKET_BASKET,
    ),
    Archetype(
        key="low_attach_high_traffic", domain="products", name="Hero item, weak attach",
        build=_low_attach_high_traffic, situations=("baseline",),
        required_signals=("transactions", "product_performance"),
        required_agents=("ProductAnalyzer", "AttachAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_MARKET_BASKET,
    ),
    Archetype(
        key="modifier_underused", domain="products", name="Underused modifiers",
        build=_modifier_underused, situations=("baseline",),
        applies_families=("food_service",),
        required_signals=("transactions",),
        required_agents=("ProductAnalyzer",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ModifierAttachAgent: extract modifier/option lines from transactions (modifier detail not yet broken out of the order payload) to rate per-item modifier attach + uplift.",
    ),
    Archetype(
        key="new_item_underexposed", domain="products", name="New item, low trial",
        build=_new_item_underexposed, situations=("baseline", "emerging"),
        required_signals=("daily_product_performance", "transactions"),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="category_cannibalization", domain="products", name="Cannibalization",
        build=_category_cannibalization, situations=("baseline", "leaking"),
        required_signals=("daily_product_performance", "product_margin"),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_MARGIN_FUSION,
    ),
    Archetype(
        key="seasonal_item_window", domain="products", name="Seasonal item timing",
        build=_seasonal_item_window, situations=("seasonal_peak", "seasonal_trough"),
        applies_flags=("seasonal",),
        required_signals=("daily_product_performance",),
        required_agents=("ProductAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="lto_cadence", domain="products", name="LTO cadence",
        build=_lto_cadence, situations=("baseline",),
        applies_families=("food_service", "retail"),
        required_signals=("daily_product_performance",),
        required_agents=("ProductAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="daypart_menu_gap", domain="products", name="Daypart-confined item",
        build=_daypart_menu_gap, situations=("baseline",),
        applies_families=("food_service",),
        required_signals=("daily_product_performance",),
        required_agents=("ProductAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="DaypartProductAgent: bucket daily_product_performance by daypart (hour-of-day not currently joined to per-item sales) to find items confined to one part of the day.",
    ),
    Archetype(
        key="hero_item_overdependence", domain="products", name="Hero overdependence",
        build=_hero_overdependence, situations=("baseline", "concentrated"),
        required_signals=("product_performance",),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="portfolio_margin_concentration", domain="products", name="Margin concentration",
        build=_portfolio_margin_concentration, situations=("baseline", "concentrated"),
        required_signals=("product_performance", "product_margin"),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_MARGIN_FUSION,
    ),
    Archetype(
        key="sku_proliferation", domain="products", name="Catalog bloat",
        build=_sku_proliferation, situations=("baseline",),
        required_signals=("product_performance",),
        required_agents=("ProductAnalyzer",),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="category_breadth_gap", domain="products", name="Assortment gap",
        build=_category_breadth_gap, situations=("baseline",),
        applies_families=("retail",),
        required_signals=("transactions",),
        required_agents=("ProductAnalyzer", "AttachAnalyzer"),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_MARKET_BASKET,
    ),
    Archetype(
        key="price_point_gap", domain="products", name="Price ladder gap",
        build=_price_point_gap, situations=("baseline",),
        required_signals=("product_performance",),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="price_anchor_missing", domain="products", name="Missing price anchor",
        build=_price_anchor_missing, situations=("baseline",),
        required_signals=("product_performance",),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="charm_pricing_untested", domain="products", name="Untested price endings",
        build=_charm_pricing_untested, situations=("baseline",),
        required_signals=("product_performance",),
        required_agents=("ProductAnalyzer",),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="discount_dependency", domain="products", name="Discount dependency",
        build=_discount_dependency, situations=("baseline",),
        required_signals=("transactions", "daily_product_performance"),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PromoLedgerAgent: tag transaction lines as promo vs full-price (discount flag not consistently captured) to size per-item discount dependency.",
    ),
    Archetype(
        key="signature_undermarketed", domain="products", name="Undermarketed signature",
        build=_signature_undermarketed, situations=("baseline",),
        required_signals=("product_performance",),
        required_agents=("ProductAnalyzer",),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="trial_to_repeat_gateway", domain="products", name="Gateway item",
        build=_trial_to_repeat_gateway, situations=("baseline",),
        applies_flags=("repeat_purchase",),
        required_signals=("transactions",),
        required_agents=("ProductAnalyzer", "CustomerAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="FirstPurchaseCohortAgent: link transactions to a customer identity and isolate first-purchase contents vs return rate (customer linkage on transactions not yet available).",
    ),
    Archetype(
        key="premium_tier_undersold", domain="products", name="Premium undersold",
        build=_premium_tier_undersold, situations=("baseline",),
        applies_flags=("high_ticket",),
        required_signals=("transactions", "product_performance"),
        required_agents=("ProductAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="service_package_upsell", domain="products", name="Package upsell",
        build=_service_package_upsell, situations=("baseline",),
        applies_flags=("membership",),
        required_signals=("transactions",),
        required_agents=("ProductAnalyzer", "CustomerAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="RepeatCohortAgent: join transactions to customer identity to detect à-la-carte repeaters who qualify for a package (customer linkage not yet on transactions).",
    ),
)
