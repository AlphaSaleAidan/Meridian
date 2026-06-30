"""
Domain: INVENTORY / STOCK & SUPPLY.

Only fires for verticals that actually hold stock — every archetype here targets
the "inventory_heavy" or "perishable" structural flag, so service businesses with
no goods on hand never receive an inventory insight. Specialization per vertical
changes what is held and how it fails: a bakery's perishable waste (hours of shelf
life, bake-to-par lever) reads nothing like a florist's (days, conditioning +
pre-book lever) or a grocer's (FIFO rotation + markdown lever).

Inventory truth (on-hand, receipts, waste, counts) is frequently NOT in the POS
the swarm already reads, so many archetypes are PARTIAL/MISSING and name the
concrete fusion/ingest agent needed (WasteLedgerAgent, ShrinkageReconcileAgent,
etc.) rather than pretending the signal exists.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register


def _stock(v: Vertical) -> str:
    """What one held unit is called for this vertical."""
    if v.family == "retail":
        return "SKU"
    if v.family == "food_service":
        return "ingredient/prep item"
    if v.family == "automotive":
        return "part"
    return "stock item"


def _perish(v: Vertical) -> tuple[str, str, str]:
    """(shelf-life phrase, the rotation/waste lever, the waste KPI) per vertical —
    so perishable reasoning is genuinely different across bakery/florist/grocery."""
    if v.key == "bakery":
        return ("hours — most items are stale by next morning",
                "bake-to-par + same-day markdown of day-olds", "waste_pct")
    if v.key == "florist":
        return ("a few days, extended only by proper conditioning",
                "cold-chain conditioning, FIFO bucket rotation, and pre-book against events", "waste_pct")
    if v.key == "grocery":
        return ("mixed sell-by dates across the case",
                "strict FIFO facing + staged markdown before the date", "perishable_waste")
    if v.key == "dispensary":
        return ("potency/freshness windows under a regulated expiry",
                "date-controlled FIFO with compliant disposal of expired stock", "category_mix")
    if v.key in ("qsr", "food_truck", "ghost_kitchen"):
        return ("a short prepped hold time",
                "prep-to-par against forecast hourly demand", "prep_time")
    if v.key == "convenience":
        return ("dated grab-and-go and fresh items",
                "FIFO facing + pull-before-date on the fresh set", "perishable_waste")
    if v.key in ("full_restaurant", "bar", "hotel_fb"):
        return ("days for fresh inputs, shorter for prepped mise",
                "par-based prep + first-in-first-out walk-in rotation", "waste_pct")
    if v.key == "cafe":
        return ("a day or two for milk and pastries",
                "par-down on pastries + tight milk rotation", "waste_pct")
    return ("a limited shelf life", "FIFO rotation + timely markdown", v.core_kpis[0])


# ── Availability failures ────────────────────────────────────────────────────
def _stockout_top_seller(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    extra = {
        "leaking": " It has gone to zero on {X} of the last {X} count days — a recurring leak, not a one-off.".replace("{X}", X),
    }.get(situation, "")
    return Built(
        title=f"Your best {s} keeps going out of stock",
        observation=f"A top-{X} seller hit zero on-hand during {X} demand windows last month, each lasting ~{X} hours.",
        reasoning=f"A stockout on a SLOW mover is harmless; on a top seller it's the most expensive failure in the store — you lose the guaranteed sale, the attached basket, and sometimes the trip. The faster it sells, the less tolerance its buffer has for a late order.{extra}",
        conclusion=f"Raise the reorder point and safety stock on your top {X} {s}s specifically, and flag them for never-out priority on every order.",
        expected_effect=f"Eliminating top-seller stockouts recovers ~${X}/mo in otherwise-lost {v.sale_unit}s and their baskets.",
        recommend_when={"state": "top_seller_stockout", "min_signal": "inventory"},
        tags=("inventory", "stockout", "availability", v.family),
    )


def _substitution_loss(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"Stockouts are pushing customers to lower-margin {s}s",
        observation=f"When {X} high-margin {s}s are out, {X}% of those customers buy a cheaper substitute instead of leaving — a hidden margin trade-down.",
        reasoning=f"This stockout doesn't show up as lost revenue, so it hides: the sale still happens, but on a worse {s}. The damage is a silent margin downgrade every time the preferred item is unavailable — invisible on the top line, real on the bottom.",
        conclusion=f"Prioritize never-out coverage on the high-margin {s}s that have a cheaper substitute, since their stockout costs margin even when the sale completes.",
        expected_effect=f"Holding availability on these protects ~${X}/mo of margin lost to forced substitution.",
        recommend_when={"state": "substitution_downgrade", "min_signal": "inventory"},
        tags=("inventory", "stockout", "margin", v.family),
    )


def _reorder_point_miss(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"Reorder points are set too low for your lead times",
        observation=f"{X} {s}s reorder only after on-hand drops below {X} days of cover, but supplier lead time runs {X} days — the math guarantees gaps.",
        reasoning=f"A reorder point must equal demand-during-lead-time plus a buffer. When the trigger is below that, you're structurally ordering too late on every cycle — the stockouts aren't bad luck, they're arithmetic.",
        conclusion=f"Reset each reorder point to (avg daily demand × lead-time days) + safety stock; recompute whenever lead time shifts.",
        expected_effect=f"Correctly-set reorder points remove ~{X} structural stockouts/mo, ~${X}/mo recovered.",
        recommend_when={"state": "reorder_point_too_low", "min_signal": "inventory"},
        tags=("inventory", "replenishment", "reorder_point", v.family),
    )


def _safety_stock_absent(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"No safety stock on volatile-demand {s}s",
        observation=f"{X} {s}s carry zero buffer above expected demand, yet their daily sales swing ±{X}% — any above-average day stocks them out.",
        reasoning=f"Safety stock exists to absorb demand variance, not average demand. Items with high day-to-day swing need a buffer sized to that volatility; running them at exactly forecast means roughly half the days end short. This is distinct from a mis-set reorder POINT — here the buffer itself is missing.",
        conclusion=f"Add safety stock to the {X} most volatile {s}s sized to their demand variability, not a flat days-of-cover rule.",
        expected_effect=f"Buffering the volatile set cuts variance-driven stockouts ~{X}%, ~${X}/mo.",
        recommend_when={"state": "no_safety_stock", "min_signal": "inventory"},
        tags=("inventory", "replenishment", "safety_stock", v.family),
    )


def _demand_spike_unprepared(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    extra = {
        "seasonal_peak": " A known seasonal spike is approaching — stage the extra stock now, before lead time makes it impossible.",
    }.get(situation, "")
    return Built(
        title=f"Predictable demand spikes catch your stock flat",
        observation=f"On {X} recurring high-demand events, sell-through on {X} {s}s exceeds normal by {X}%, but order quantities don't change ahead of them.",
        reasoning=f"These spikes are foreseeable (weekend, payday, weather, event, holiday) yet ordering runs on a flat average. Because lead time blocks last-minute response, an un-staged spike converts directly into stockouts on your busiest days.{extra}",
        conclusion=f"Pre-order an uplift on the spike-sensitive {s}s ahead of each known event window rather than reacting after it starts.",
        expected_effect=f"Staging for spikes captures ~${X}/mo currently lost on your highest-demand days.",
        recommend_when={"state": "spike_unprepared", "min_signal": "inventory"},
        tags=("inventory", "forecasting", "spike", v.family),
    )


# ── Capital tied up ──────────────────────────────────────────────────────────
def _overstock_deadstock(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"Deadstock — {s}s sitting on capital you can't recover",
        observation=f"{X} {s}s have not sold a unit in {X}+ days yet still occupy ${X} of on-hand value and {X}% of your space.",
        reasoning=f"Deadstock is worse than a slow seller: it's frozen cash AND occupied space that a productive {s} could use. Every day it sits, it costs carrying and crowds out something that would turn — the loss compounds quietly.",
        conclusion=f"Liquidate the dead {X} {s}s (markdown, bundle, return-to-vendor) and stop reordering them; redeploy the freed cash to proven movers.",
        expected_effect=f"Clearing deadstock frees ~${X} of working capital and ~{X}% of space.",
        recommend_when={"state": "deadstock", "min_signal": "inventory"},
        tags=("inventory", "deadstock", "capital", v.family),
    )


def _carrying_cost_overstock(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"You're carrying months of cover on {s}s that don't need it",
        observation=f"{X} {s}s hold {X}+ days of supply when {X} days would cover demand to the next order, tying up ${X} unnecessarily.",
        reasoning=f"Carrying cost (capital, space, spoilage/obsolescence risk, insurance) runs ~{X}% of inventory value per year. Over-covering a steady, short-lead-time {s} buys no service-level benefit — it just pays that carrying tax on stock you didn't need early.",
        conclusion=f"Right-size cover on the over-stocked {s}s to lead-time + buffer and order more frequently in smaller lots.",
        expected_effect=f"Trimming excess cover saves ~${X}/mo in carrying cost without risking availability.",
        recommend_when={"state": "excess_cover", "min_signal": "inventory"},
        tags=("inventory", "carrying_cost", "capital", v.family),
    )


def _inventory_turns_low(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"Your inventory turns too slowly for the cash it ties up",
        observation=f"Overall turns run ~{X}× a year versus a {X}× benchmark for {v.name.lower()}s, with ${X} of average on-hand.",
        reasoning=f"Turns are how fast inventory becomes cash. Low turns mean the same dollars are working fewer times a year — a whole-portfolio efficiency problem (not one bad {s}) that drags return on the capital tied up in stock.",
        conclusion=f"Raise turns by shifting the assortment mix toward faster movers and shrinking cover on the slow tail; track turns as a standing metric.",
        expected_effect=f"Moving toward benchmark turns frees ~${X} of cash to redeploy and lifts return on inventory.",
        recommend_when={"state": "low_turns", "min_signal": "inventory"},
        tags=("inventory", "turns", "efficiency", v.family),
    )


def _moq_overbuy(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"Supplier minimums force you to overbuy slow {s}s",
        observation=f"{X} {s}s only sell ~{X}/month but a supplier MOQ forces buying {X}+ at a time — {X} months of cover bought at once.",
        reasoning=f"An MOQ that exceeds your sell-through converts a small need into a large capital and space commitment. The unit price looks fine, but the real cost is months of frozen cash and shelf for a {s} that barely moves.",
        conclusion=f"Renegotiate the MOQ, find a distributor with smaller break-packs, or drop the {s} if its economics only work at quantities you can't turn.",
        expected_effect=f"Fixing MOQ-driven overbuys frees ~${X} of capital and avoids predictable deadstock.",
        recommend_when={"state": "moq_overbuy", "min_signal": "inventory"},
        tags=("inventory", "purchasing", "moq", v.family),
    )


# ── Perishable / freshness ───────────────────────────────────────────────────
def _perishable_waste(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    life, lever, kpi = _perish(v)
    extra = {
        "seasonal_trough": " Demand is about to drop — pull pars down ahead of the trough instead of discovering the waste after it.",
    }.get(situation, "")
    return Built(
        title=f"Perishable waste is eating margin off your {s}s",
        observation=f"~{X}% of perishable {s}s are thrown out before sale (tracked via {kpi}), worth ~${X}/week — shelf life here is {life}.",
        reasoning=f"For this vertical the clock is unforgiving: {life}, so over-ordering doesn't become deadstock, it becomes garbage. Unlike durable overstock you can't markdown your way out later — the only lever is ordering/prepping closer to true demand.",
        conclusion=f"Cut waste with {lever}; set pars to forecast demand, not habit, on the highest-waste {s}s.{extra}",
        expected_effect=f"Halving waste on the top offenders recovers ~${X}/mo of pure margin.",
        recommend_when={"state": "perishable_waste", "min_signal": "inventory"},
        tags=("inventory", "waste", "perishable", v.family),
    )


def _expiry_clustering(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    life, lever, _ = _perish(v)
    reg = " For a regulated product, expired stock must be logged and destroyed compliantly — clustering raises both waste AND compliance exposure." if "regulated" in v.flags else ""
    return Built(
        title=f"Expiry dates are clustering — waste arrives in waves",
        observation=f"{X}% of perishable on-hand shares the same {X}-day expiry window, so spoilage hits in spikes rather than spreading out.",
        reasoning=f"Buying in big infrequent lots makes receipts — and therefore expiries — bunch up. When a cluster's date arrives faster than you can sell through it, a wave of stock expires at once. Smaller, staggered receipts spread the date risk across the {life}.{reg}",
        conclusion=f"Stagger deliveries of clustered {s}s into smaller more frequent lots and rotate by date; pre-markdown a cluster before its window closes.",
        expected_effect=f"Smoothing expiries cuts wave-spoilage by ~{X}%, ~${X}/mo recovered.",
        recommend_when={"state": "expiry_clustering", "min_signal": "inventory"},
        tags=("inventory", "waste", "expiry", v.family),
    )


def _freshness_rotation(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    life, lever, _ = _perish(v)
    return Built(
        title=f"FIFO rotation is slipping — fresh stock sells before old",
        observation=f"Spot checks show newer {s}s sold ahead of older ones on {X}% of the {X} fastest-perishing lines, aging the remainder into waste.",
        reasoning=f"When customers (or staff) reach for the freshest-looking unit, the oldest stock never sells and times out — even though total demand could have cleared it. With shelf life of {life}, broken rotation manufactures waste out of stock that would otherwise have sold.",
        conclusion=f"Enforce {lever}: face oldest-to-front, date-label, and make first-out the path of least resistance on the perishing lines.",
        expected_effect=f"Restoring rotation discipline converts ~${X}/mo of would-be waste into sales.",
        recommend_when={"state": "rotation_broken", "min_signal": "inventory"},
        tags=("inventory", "rotation", "freshness", v.family),
    )


def _order_cadence_misaligned(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    life, _, _ = _perish(v)
    return Built(
        title=f"Order frequency doesn't match how fast {s}s perish",
        observation=f"You order perishables every {X} days but their usable life is only {X} days — receipts age out before the next sell-through cycle.",
        reasoning=f"For perishables, order cadence must be tighter than shelf life. Ordering on a slower rhythm than the goods last guarantees a portion spoils each cycle regardless of how well you forecast volume — the timing, not the quantity, is the leak ({life}).",
        conclusion=f"Increase delivery frequency on the shortest-life {s}s so each receipt is sized to sell out before it expires, even at smaller lots.",
        expected_effect=f"Aligning cadence to shelf life cuts cyclical spoilage ~{X}%, ~${X}/mo.",
        recommend_when={"state": "cadence_vs_shelflife", "min_signal": "inventory"},
        tags=("inventory", "cadence", "perishable", v.family),
    )


def _overorder_pre_slow(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    life, _, _ = _perish(v)
    return Built(
        title=f"Over-ordering perishables right before your slow period",
        observation=f"Going into your weekly/seasonal lull, perishable receipts stay flat at peak-period levels, so {X}% of the last pre-lull order is wasted.",
        reasoning=f"Demand falls on a known schedule but the order ahead of it doesn't, so peak-sized receipts land just as sell-through collapses — and because shelf life here is {life}, that stock can't bridge to the next peak, which means it spoils rather than carrying over. The leak is the timing against the demand cliff, not chronic over-ordering.",
        conclusion=f"Cut perishable pars on the order immediately before each known lull, then raise them back ahead of the next peak.",
        expected_effect=f"Tapering the pre-lull order avoids ~${X}/mo of predictable end-of-period spoilage.",
        recommend_when={"state": "overorder_before_lull", "min_signal": "inventory"},
        tags=("inventory", "waste", "timing", v.family),
    )


def _waste_by_daypart(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    life, lever, _ = _perish(v)
    return Built(
        title=f"End-of-day perishables are made, not sold",
        observation=f"{X}% of daily perishable waste is stock prepped/stocked for a late daypart that consistently under-sells it.",
        reasoning=f"Production is leveled across the day while demand isn't — so the last daypart is over-supplied with goods that won't survive to tomorrow ({life}). The waste is a within-day pattern: too much made too late, not too much bought overall.",
        conclusion=f"Taper late-daypart prep/stocking to its real sell-through and use {lever} to clear the tail before close.",
        expected_effect=f"Right-timing late production cuts end-of-day waste ~{X}%, ~${X}/mo.",
        recommend_when={"state": "eod_waste", "min_signal": "inventory"},
        tags=("inventory", "waste", "daypart", v.family),
    )


def _seasonal_preorder_gap(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    life, _, _ = _perish(v)
    when = "events/holidays" if v.key == "florist" else "the seasonal peak"
    return Built(
        title=f"No pre-book against your perishable peaks",
        observation=f"Demand around {when} spikes {X}% on {X} dates, but perishable {s}s are bought on the normal cycle with no advance booking.",
        reasoning=f"Perishables can't be stockpiled far ahead ({life}), and suppliers ration scarce fresh product near a peak — so without a pre-booked allocation you face both stockouts AND price gouging exactly when demand is highest.",
        conclusion=f"Pre-book perishable allocations with suppliers ahead of {when}, timed to arrive just-in-time for the spike.",
        expected_effect=f"Securing peak allocation captures ~${X}/mo of peak demand and avoids spot-price premiums.",
        recommend_when={"state": "no_perishable_prebook", "min_signal": "inventory"},
        tags=("inventory", "forecasting", "perishable", v.family),
    )


# ── Accuracy / loss ──────────────────────────────────────────────────────────
def _shrinkage_variance(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    extra = {
        "anomaly": " Variance jumped sharply in the last {X} weeks versus baseline — investigate this window first.".replace("{X}", X),
    }.get(situation, "")
    return Built(
        title=f"Unexplained shrinkage between what sold and what's gone",
        observation=f"Counted on-hand trails sales-adjusted expected on-hand by {X}% on {X} {s}s — ${X}/mo vanishing without a sale.",
        reasoning=f"Shrinkage (theft, miscount, damage, scan errors) is margin leaving with no revenue attached. Because it never appears on the P&L as a line, it compounds unnoticed until a physical count exposes the gap.{extra}",
        conclusion=f"Reconcile the high-variance {s}s first, tighten receiving/scan accuracy, and secure or watch the worst offenders.",
        expected_effect=f"Closing the variance recovers ~${X}/mo of currently-untracked loss.",
        recommend_when={"state": "shrinkage_variance", "min_signal": "inventory"},
        tags=("inventory", "shrinkage", "loss", v.family),
    )


def _theft_prone_category(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    reg = " Regulated stock carries compliance penalties on top of the loss if it goes unaccounted." if "regulated" in v.flags else ""
    return Built(
        title=f"High-value, easily-concealed {s}s show outsized shrink",
        observation=f"A small set of high-value {s}s accounts for {X}% of total shrinkage despite being {X}% of units — the classic theft profile.",
        reasoning=f"Loss isn't uniform: small, valuable, easily-pocketed {s}s draw disproportionate theft. Treating shrink as a flat percentage hides that a few categories drive most of it, so blanket measures waste effort.{reg}",
        conclusion=f"Apply targeted controls (lock-up, secure display, tighter counts) to the {X} highest-shrink {s}s rather than store-wide.",
        expected_effect=f"Securing the theft-prone set cuts shrink ~{X}%, ~${X}/mo.",
        recommend_when={"state": "theft_prone", "min_signal": "inventory"},
        tags=("inventory", "shrinkage", "security", v.family),
    )


def _phantom_inventory(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"Phantom stock — the system says you have it, the shelf doesn't",
        observation=f"{X} {s}s show positive system on-hand but repeatedly can't be found to sell — phantom inventory on {X}% of audited lines.",
        reasoning=f"Phantom stock is worse than a plain stockout: the system thinks the {s} is covered, so it never reorders, and the item stays unsellable indefinitely. It's a record-accuracy failure that silently caps sales on items you believe are in stock.",
        conclusion=f"Zero-out and recount the phantom {s}s, then fix the root cause (mis-scan, theft, unrecorded damage) so the record stops drifting.",
        expected_effect=f"Correcting phantom records restarts reordering and recovers ~${X}/mo of frozen sales.",
        recommend_when={"state": "phantom_inventory", "min_signal": "inventory"},
        tags=("inventory", "accuracy", "phantom", v.family),
    )


def _cycle_count_neglect(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"Counts are stale — record accuracy is drifting",
        observation=f"{X}% of {s}s haven't been counted in {X}+ days; audited lines show an average {X}% record-vs-actual gap.",
        reasoning=f"Records drift continuously because every mis-scan, unlogged damage, and miscount compounds, so without regular cycle counts the record-vs-actual gap widens until reordering, valuation, and availability all run on numbers that are wrong — which means an annual-only count lets a year of error accumulate before anyone catches it.",
        conclusion=f"Schedule ABC-weighted cycle counts — count A-items every {X} days, B/C items less often — so accuracy stays current without a full shutdown.",
        expected_effect=f"Holding the record-vs-actual gap under {X}% prevents the bad-data stockouts and overbuys, worth ~${X}/mo recovered.",
        recommend_when={"state": "stale_counts", "min_signal": "inventory"},
        tags=("inventory", "accuracy", "cycle_count", v.family),
    )


def _backstock_invisibility(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"You're 'out' on the floor while stock sits in the back",
        observation=f"{X} {s}s sold out on the floor while units sat in back-stock — false stockouts on {X}% of audited fast movers.",
        reasoning=f"A false stockout costs the same sale as a real one, but for nothing — the inventory exists, it just never made it to where it sells. The gap is a replenishment-to-floor process failure, not a buying failure.",
        conclusion=f"Set floor-replenishment triggers and a back-to-floor routine on the fast movers so on-hand actually reaches the shelf.",
        expected_effect=f"Closing the floor gap recovers ~${X}/mo of sales lost on stock you already owned.",
        recommend_when={"state": "floor_replenishment_gap", "min_signal": "inventory"},
        tags=("inventory", "replenishment", "floor", v.family),
    )


# ── Supply / planning discipline ─────────────────────────────────────────────
def _supplier_lead_time_risk(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"Lead-time variability is forcing either stockouts or overstock",
        observation=f"Supplier lead time on {X} {s}s swings from {X} to {X} days, but ordering assumes a single fixed lead time.",
        reasoning=f"It's the VARIABILITY, not the average, that hurts: plan to the short case and you stock out when it runs long; plan to the long case and you carry excess the rest of the time. A fixed-lead-time assumption can't win against a swinging one.",
        conclusion=f"Size safety stock to lead-time variability on these {s}s and develop a backup supplier to compress the worst case.",
        expected_effect=f"Buffering lead-time risk avoids ~${X}/mo of swing-driven stockouts and excess.",
        recommend_when={"state": "lead_time_variable", "min_signal": "inventory"},
        tags=("inventory", "supply", "lead_time", v.family),
    )


def _supplier_concentration_risk(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    extra = {
        "concentrated": " That supplier has already missed {X} recent deliveries — the single point of failure is actively failing.".replace("{X}", X),
    }.get(situation, "")
    return Built(
        title=f"One supplier controls too much of your stock",
        observation=f"A single supplier provides {X}% of your {s}s, including {X} of your top sellers, with no qualified backup.",
        reasoning=f"Single-sourcing reads as free until it fails, because one outage, price hike, or quality lapse at that supplier hits a huge slice of your availability at once — and with no qualified backup you can't switch, so a single disruption drives simultaneous stockouts across your top sellers instead of a contained gap.{extra}",
        conclusion=f"Add a qualified secondary supplier for the critical {s}s now, even at slightly worse terms, so a single failure can't empty your shelves.",
        expected_effect=f"A backup source de-risks ~{X}% of stock currently dependent on one supplier.",
        recommend_when={"state": "supplier_concentration", "min_signal": "inventory"},
        tags=("inventory", "supply", "concentration", "risk", v.family),
    )


def _par_level_misset(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"Par levels are set by habit, not by demand",
        observation=f"{X} {s}s carry pars unchanged for {X}+ months while their demand moved {X}%, so each is now either chronically short or chronically long.",
        reasoning=f"Pars are a demand assumption frozen in time. When demand drifts and the par doesn't, the same number that once fit now mismatches every cycle — under-set pars stock out, over-set pars waste or tie up cash. Stale pars are a slow, systematic error.",
        conclusion=f"Recompute pars from recent demand on the {X} most-drifted {s}s and put pars on a periodic review, not set-and-forget.",
        expected_effect=f"Re-baselining stale pars cuts both stockouts and excess, ~${X}/mo.",
        recommend_when={"state": "par_drift", "min_signal": "inventory"},
        tags=("inventory", "par_levels", "planning", v.family),
    )


def _abc_neglect(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"You manage every {s} the same — but value is lopsided",
        observation=f"~{X}% of {s}s drive ~{X}% of value (your A-items), yet ordering, counting, and attention are spread evenly across the whole catalog.",
        reasoning=f"Uniform management is mis-allocated effort: the vital few A-items deserve tight control and frequent counts, while the trivial many can run on autopilot. Treating all {s}s alike under-protects the items that matter and over-services the ones that don't.",
        conclusion=f"Classify {s}s A/B/C by value and concentrate replenishment rigor, safety stock, and count frequency on the A-items.",
        expected_effect=f"Focusing control on the vital few cuts both stockouts on A-items and effort wasted on C-items.",
        recommend_when={"state": "no_abc_discipline", "min_signal": "inventory"},
        tags=("inventory", "abc", "planning", v.family),
    )


def _slow_mover_markdown(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    seasonal = "seasonal" in v.flags
    extra = " For a seasonal line, the markdown clock is the season itself — discount before the window closes, not after." if seasonal else ""
    return Built(
        title=f"Slow movers marked down too late to recover value",
        observation=f"{X} slow-moving {s}s are discounted only after {X}+ days of no movement, by which point recoverable value has decayed {X}%.",
        reasoning=f"Markdown timing is a curve: a small early discount clears stock while it still has value; waiting forces a deep late discount on stock worth less — or none at all. Late markdowns surrender the very margin a timely one would have saved.{extra}",
        conclusion=f"Trigger a staged markdown the moment a {s} breaches its days-of-cover threshold, escalating on a schedule rather than waiting for it to fully stall.",
        expected_effect=f"Earlier, staged markdowns recover ~${X}/mo of value otherwise lost to decay.",
        recommend_when={"state": "late_markdown", "min_signal": "inventory"},
        tags=("inventory", "markdown", "timing", v.family),
    )


def _seasonal_carryover(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    seasonal = "seasonal" in v.flags
    if seasonal:
        lever = "plan end-of-season sell-down (markdown cadence + return-to-vendor) into the buy itself"
        why = "seasonal {s}s have a hard demand cliff: whatever isn't sold by season-end becomes carryover that ties up cash for a year or sells at salvage".replace("{s}", s)
    else:
        lever = "set an exit plan for trend/fad {s}s before demand fades".replace("{s}", s)
        why = "fad-driven {s}s lose demand fast once the trend turns, leaving late-bought units stranded".replace("{s}", s)
    return Built(
        title=f"Last season's {s}s are still on the books",
        observation=f"{X} {s}s from a prior season/trend remain in stock at ${X} value, carried {X}+ months past their demand window.",
        reasoning=f"Carryover is the most predictable deadstock there is: {why}. Buying without a planned exit guarantees a tail of stranded stock every cycle.",
        conclusion=f"Clear the existing carryover now and {lever} so next cycle ends clean.",
        expected_effect=f"Eliminating carryover frees ~${X} of capital and prevents it recurring next season.",
        recommend_when={"state": "seasonal_carryover", "min_signal": "inventory"},
        tags=("inventory", "seasonal", "carryover", v.family),
    )


# ── New reasoning patterns ───────────────────────────────────────────────────
def _space_to_sales_mismatch(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"Shelf space doesn't match where sales come from",
        observation=f"Your top-selling {X}% of {s}s get only {X}% of facings while a slow category holds {X}% of the space — allocation is inverted from demand.",
        reasoning=f"Shelf space is a fixed, scarce asset, so facings handed to slow {s}s starve your fast movers — which drives avoidable on-shelf stockouts on the winners and leaves dead {s}s occupying room that would otherwise turn, meaning the layout caps sales no amount of buying can fix.",
        conclusion=f"Reallocate facings in proportion to each {s}'s sales velocity — expand the movers, shrink the slow tail — and re-plan the planogram.",
        expected_effect=f"Matching space to velocity cuts winner stockouts and lifts category sales ~{X}%, ~${X}/mo.",
        recommend_when={"state": "space_to_sales_mismatch", "min_signal": "inventory"},
        tags=("inventory", "space", "allocation", v.family),
    )


def _freight_order_consolidation(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"Frequent small orders are racking up freight and fees",
        observation=f"You place ~{X} sub-${X} POs/month to the same supplier, each carrying a ${X} freight/handling charge that adds {X}% to landed cost.",
        reasoning=f"Freight and small-order fees are fixed per shipment, so splitting demand across many tiny POs multiplies that fixed cost — which inflates landed cost on every unit and erodes margin, even though the unit price on the invoice never moved.",
        conclusion=f"Batch orders to that supplier into fewer, larger drops above the free-freight threshold, combining the slow {s}s onto the mover orders.",
        expected_effect=f"Hitting free-freight thresholds trims landed cost ~{X}%, ~${X}/mo saved.",
        recommend_when={"state": "freight_fragmented_orders", "min_signal": "inventory"},
        tags=("inventory", "purchasing", "freight", v.family),
    )


def _returns_not_restocked(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"Sellable returns aren't making it back to the floor",
        observation=f"{X}% of returned {s}s sit in a returns bin for {X}+ days before restocking — or get written off — while the same {s}s read as out-of-stock.",
        reasoning=f"A sellable return that never re-enters stock costs you twice, because the system still counts it as gone so it won't reorder, and the physical unit ages unsold in the back — which manufactures a false stockout and an avoidable write-off out of inventory you already paid for.",
        conclusion=f"Set a same-day restock routine for sellable returns and reconcile the returns bin weekly so good units rejoin available stock.",
        expected_effect=f"Restocking returns within a day recovers ~${X}/mo of false-stockout sales and avoided write-offs.",
        recommend_when={"state": "returns_not_restocked", "min_signal": "inventory"},
        tags=("inventory", "returns", "availability", v.family),
    )


def _consignment_slow_capital(v: Vertical, situation: str) -> Built:
    s = _stock(v)
    return Built(
        title=f"Slow high-value {s}s are freezing cash you could shift to the vendor",
        observation=f"{X} high-value {s}s turn under {X}x a year yet tie up ${X} of owned inventory — capital frozen on stock that barely moves.",
        reasoning=f"Owning slow, expensive {s}s outright means you finance their idle months, so the cash sits frozen and exposed to obsolescence instead of working — whereas consignment or vendor-managed terms shift that carrying cost and risk to the supplier, which frees your capital without dropping the assortment.",
        conclusion=f"Move the slow high-value {s}s to consignment or pay-on-scan terms so you stock the range without owning the idle capital.",
        expected_effect=f"Shifting these to consignment frees ~${X} of working capital and removes their obsolescence risk.",
        recommend_when={"state": "consignment_candidate", "min_signal": "inventory"},
        tags=("inventory", "capital", "consignment", v.family),
    )


# ── Registration ─────────────────────────────────────────────────────────────
_WASTE_LEDGER = (
    "WasteLedgerAgent: impute waste by joining successive inventory_snapshots "
    "(on-hand deltas) minus units sold from transactions, since spoilage/throw-away "
    "is never recorded in the POS — without it perishable waste is unobservable."
)
_SHRINK_RECONCILE = (
    "ShrinkageReconcileAgent: reconcile physical counts against sales-adjusted "
    "expected on-hand to quantify variance/shrink (physical count + receiving "
    "feeds are not yet ingested)."
)
_STOCKOUT_DETECT = (
    "StockoutDetectAgent: detect zero/near-zero on-hand during demand windows by "
    "joining inventory snapshots to hourly demand (continuous on-hand snapshots "
    "not yet captured — only periodic counts exist)."
)
_REORDER_ENGINE = (
    "ReorderPointAgent: compute demand-during-lead-time + safety stock per SKU "
    "(requires supplier lead-time and receipt timestamps, not currently ingested)."
)
_SUPPLY_INGEST = (
    "SupplyLedgerAgent: ingest purchase orders + receipts (supplier, lead time, "
    "MOQ, cost) — no supplier/PO feed exists today, so all supply-side reasoning "
    "is blind without it."
)
_COUNT_LEDGER = (
    "CountLedgerAgent: ingest cycle/physical counts and track record-vs-actual "
    "drift over time (count history is not stored today)."
)

register(
    # availability
    Archetype(
        key="stockout_top_seller", domain="inventory", name="Top-seller stockout",
        build=_stockout_top_seller, situations=("baseline", "leaking"),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory", "daily_product_performance"),
        required_agents=("InventoryAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_STOCKOUT_DETECT,
    ),
    Archetype(
        key="substitution_loss", domain="inventory", name="Substitution downgrade",
        build=_substitution_loss, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory", "transactions"),
        required_agents=("InventoryAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_STOCKOUT_DETECT,
    ),
    Archetype(
        key="reorder_point_miss", domain="inventory", name="Reorder point too low",
        build=_reorder_point_miss, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_REORDER_ENGINE,
    ),
    Archetype(
        key="safety_stock_absent", domain="inventory", name="No safety stock",
        build=_safety_stock_absent, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_REORDER_ENGINE,
    ),
    Archetype(
        key="demand_spike_unprepared", domain="inventory", name="Spike unprepared",
        build=_demand_spike_unprepared, situations=("baseline", "seasonal_peak"),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory", "daily_product_performance"),
        required_agents=("InventoryAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_REORDER_ENGINE,
    ),
    # capital
    Archetype(
        key="overstock_deadstock", domain="inventory", name="Deadstock",
        build=_overstock_deadstock, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory", "product_performance"),
        required_agents=("InventoryAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="DeadstockAgent: compute days-since-last-sale × on-hand value from inventory snapshots + sales (snapshot history not yet retained).",
    ),
    Archetype(
        key="carrying_cost_overstock", domain="inventory", name="Excess cover",
        build=_carrying_cost_overstock, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_REORDER_ENGINE,
    ),
    Archetype(
        key="inventory_turns_low", domain="inventory", name="Low turns",
        build=_inventory_turns_low, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory", "product_performance"),
        required_agents=("InventoryAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="TurnsAgent: compute COGS ÷ average on-hand per period (needs cost + retained snapshot history).",
    ),
    Archetype(
        key="moq_overbuy", domain="inventory", name="MOQ overbuy",
        build=_moq_overbuy, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_SUPPLY_INGEST,
    ),
    # perishable
    Archetype(
        key="perishable_waste", domain="inventory", name="Perishable waste",
        build=_perishable_waste, situations=("baseline", "seasonal_trough"),
        applies_flags=("perishable",),
        required_signals=("inventory", "daily_product_performance"),
        required_agents=("InventoryAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_WASTE_LEDGER,
    ),
    Archetype(
        key="expiry_clustering", domain="inventory", name="Expiry clustering",
        build=_expiry_clustering, situations=("baseline",),
        applies_flags=("perishable",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LotExpiryAgent: track per-lot receipt + expiry dates (lot/date attributes are not captured on inventory today).",
    ),
    Archetype(
        key="freshness_rotation", domain="inventory", name="Broken FIFO rotation",
        build=_freshness_rotation, situations=("baseline",),
        applies_flags=("perishable",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_WASTE_LEDGER,
    ),
    Archetype(
        key="order_cadence_misaligned", domain="inventory", name="Cadence vs shelf life",
        build=_order_cadence_misaligned, situations=("baseline",),
        applies_flags=("perishable",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_SUPPLY_INGEST,
    ),
    Archetype(
        key="overorder_pre_slow", domain="inventory", name="Over-order before lull",
        build=_overorder_pre_slow, situations=("baseline",),
        applies_flags=("perishable",),
        required_signals=("inventory", "daily_product_performance"),
        required_agents=("InventoryAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_WASTE_LEDGER,
    ),
    Archetype(
        key="waste_by_daypart", domain="inventory", name="End-of-day waste",
        build=_waste_by_daypart, situations=("baseline",),
        applies_flags=("perishable",),
        required_signals=("inventory", "daily_product_performance"),
        required_agents=("InventoryAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_WASTE_LEDGER,
    ),
    Archetype(
        key="seasonal_preorder_gap", domain="inventory", name="No perishable pre-book",
        build=_seasonal_preorder_gap, situations=("baseline",),
        applies_flags=("perishable",),
        required_signals=("inventory", "daily_product_performance"),
        required_agents=("InventoryAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_SUPPLY_INGEST,
    ),
    # accuracy / loss
    Archetype(
        key="shrinkage_variance", domain="inventory", name="Shrinkage variance",
        build=_shrinkage_variance, situations=("baseline", "anomaly"),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory", "transactions"),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_SHRINK_RECONCILE,
    ),
    Archetype(
        key="theft_prone_category", domain="inventory", name="Theft-prone shrink",
        build=_theft_prone_category, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_SHRINK_RECONCILE,
    ),
    Archetype(
        key="phantom_inventory", domain="inventory", name="Phantom stock",
        build=_phantom_inventory, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_COUNT_LEDGER,
    ),
    Archetype(
        key="cycle_count_neglect", domain="inventory", name="Stale counts",
        build=_cycle_count_neglect, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_COUNT_LEDGER,
    ),
    Archetype(
        key="backstock_invisibility", domain="inventory", name="False stockout",
        build=_backstock_invisibility, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LocationStockAgent: split on-hand into floor vs back-stock locations (inventory is tracked as a single pooled quantity today).",
    ),
    # supply / planning
    Archetype(
        key="supplier_lead_time_risk", domain="inventory", name="Lead-time variability",
        build=_supplier_lead_time_risk, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_SUPPLY_INGEST,
    ),
    Archetype(
        key="supplier_concentration_risk", domain="inventory", name="Supplier concentration",
        build=_supplier_concentration_risk, situations=("baseline", "concentrated"),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_SUPPLY_INGEST,
    ),
    Archetype(
        key="par_level_misset", domain="inventory", name="Par drift",
        build=_par_level_misset, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory", "daily_product_performance"),
        required_agents=("InventoryAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL, swarm_upgrade=_REORDER_ENGINE,
    ),
    Archetype(
        key="abc_analysis_neglect", domain="inventory", name="No ABC discipline",
        build=_abc_neglect, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory", "product_performance"),
        required_agents=("InventoryAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ABCClassifierAgent: rank SKUs by value contribution from product_performance × cost (cost data not yet ingested).",
    ),
    Archetype(
        key="slow_mover_markdown_timing", domain="inventory", name="Late markdown",
        build=_slow_mover_markdown, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory", "product_performance"),
        required_agents=("InventoryAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="DeadstockAgent (shared): flag SKUs breaching days-of-cover so markdowns trigger on schedule rather than after a full stall.",
    ),
    Archetype(
        key="seasonal_carryover", domain="inventory", name="Seasonal carryover",
        build=_seasonal_carryover, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory", "product_performance"),
        required_agents=("InventoryAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="DeadstockAgent (shared): identify prior-season SKUs carried past their demand window from snapshot history.",
    ),
    # new reasoning patterns
    Archetype(
        key="space_to_sales_mismatch", domain="inventory", name="Space vs sales mismatch",
        build=_space_to_sales_mismatch, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory", "product_performance"),
        required_agents=("InventoryAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="PlanogramAgent: join per-SKU facing/space allocation to sales velocity (shelf-space data is not captured today) to flag inverted space-to-sales.",
    ),
    Archetype(
        key="freight_order_consolidation", domain="inventory", name="Fragmented orders, freight drag",
        build=_freight_order_consolidation, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_SUPPLY_INGEST,
    ),
    Archetype(
        key="returns_not_restocked", domain="inventory", name="Returns not restocked",
        build=_returns_not_restocked, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory",),
        required_agents=("InventoryAnalyzer",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ReturnsLedgerAgent: ingest return/RMA events and restock timestamps (returns are not tracked against on-hand today) to surface sellable units stranded in the returns bin.",
    ),
    Archetype(
        key="consignment_slow_capital", domain="inventory", name="Consignment candidate",
        build=_consignment_slow_capital, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory", "product_performance"),
        required_agents=("InventoryAnalyzer", "ProductAnalyzer"),
        swarm_capability=SwarmCapability.MISSING, swarm_upgrade=_SUPPLY_INGEST,
    ),
)
