"""
Domain: PRICING / MARGIN.

Each archetype is a distinct reasoning pattern about a margin or price lever — not
a number on the same idea. Specialization per vertical changes the lever and the
unit of value: pour cost & happy-hour cannibalization for a bar, markdown depth &
premium-mix drift for inventory_heavy retail, deposit-anchored package pricing for
appointment_based services, third-party commission erosion for delivery_capable
kitchens. Many of these need a true cost basis the swarm does not yet ingest, so
their swarm_capability is PARTIAL/MISSING with the upgrade agent spec'd.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register


# ── universal margin/price levers ────────────────────────────────────────
def _discount_leakage(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "leaking": " The discount has become the default price — full-price sales of this category are now the exception, not the rule.",
    }.get(situation, "")
    return Built(
        title=f"Your {X} category is over-discounted — {X}% of {unit}s sell below list",
        observation=f"{X}% of {X}-category {unit}s carry a discount averaging {X}% off, yet unit volume is flat vs the full-price period.",
        reasoning=f"A discount that doesn't move volume is pure margin handed back: you're funding a price cut customers would have paid through anyway, costing ~${X} in foregone margin per week.{extra}",
        conclusion=f"Cap the standing discount on {X} to {X}% (or make it loyalty-gated) and watch {X} weeks of volume before widening it again.",
        expected_effect=f"Reclaiming the unwarranted discount is worth ~${X}/mo in recovered margin at current volume.",
        recommend_when={"state": "category_over_discounted", "min_signal": "discounts_applied"},
        tags=("discount", "margin", v.family),
    )


def _margin_compression_trend(v: Vertical, situation: str) -> Built:
    extra = {
        "declining": " This is a slow bleed, not a blip — reprice systematically rather than chase one line item.",
        "anomaly": " The drop is abrupt — check for a supplier cost step-change or a mis-keyed price before any broad move.",
    }.get(situation, "")
    return Built(
        title=f"Gross margin has slipped {X} points over {X} months",
        observation=f"Blended gross margin fell from {X}% to {X}% while {v.sale_unit} prices held — the gap is cost-side or mix-side, not demand-side.{extra}",
        reasoning=f"Holding menu/shelf prices through rising input costs silently converts every {v.sale_unit} into a thinner one; at your volume each point of margin is ~${X}/mo.",
        conclusion=f"Reprice the {X} highest-cost-growth items to restore the lost points, or shift mix toward your {X} core_kpi winners.",
        expected_effect=f"Recovering {X} margin points is worth ~${X}/mo without adding a single {v.sale_unit}.",
        recommend_when={"state": "margin_eroding", "min_signal": "item_costs"},
        tags=("margin", "trend", v.family),
    )


def _underpriced_high_demand(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "emerging": " Demand for this item is still climbing — set the new price now, before the pattern hardens around the old one.",
    }.get(situation, "")
    return Built(
        title=f"Your best-selling {X} is priced like an average one",
        observation=f"{X} accounts for {X}% of {unit}s and rarely needs a discount to sell, yet it's priced within {X}% of slower siblings.",
        reasoning=f"An item that clears at full price with no promotional help is signalling willingness-to-pay above its sticker — the market is telling you it's underpriced.{extra}",
        conclusion=f"Test a {X}% price lift on {X} for {X} weeks; demand this strong rarely flinches at a small move.",
        expected_effect=f"A {X}% lift on a top-{X}% seller flows almost entirely to margin — ~${X}/mo.",
        recommend_when={"state": "high_demand_underpriced", "min_signal": "transactions"},
        tags=("pricing", "demand", v.family),
    )


def _premium_tier_untapped(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "untapped": " You have never offered a top tier here — this is greenfield, not a tweak.",
    }.get(situation, "")
    return Built(
        title=f"Your top customers have nothing left to trade up to",
        observation=f"The top {X}% of {unit}s already buy your most expensive option; {X}% of {v.staff_role}-served customers max out the menu without a premium choice.{extra}",
        reasoning=f"When your best customers hit the ceiling of the catalog, their extra willingness-to-pay leaks away unspent — a premium {unit} captures it without touching the base.",
        conclusion=f"Introduce one premium {unit} priced {X}% above today's top option (better materials/service/speed), aimed at the {X}% who already buy up.",
        expected_effect=f"Even {X}% premium adoption among top buyers adds ~${X}/mo in pure trade-up margin.",
        recommend_when={"state": "no_premium_tier", "min_signal": "transactions"},
        tags=("pricing", "premium", v.family),
    )


def _price_elasticity_headroom(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your last price change barely dented volume — there's headroom",
        observation=f"When {X} rose {X}% last time, {v.sale_unit} volume moved only {X}% — an elasticity well under 1.",
        reasoning=f"Inelastic demand means another measured increase keeps nearly all the volume while every cent of the rise drops to margin; you stopped short of the price ceiling.",
        conclusion=f"Take a second {X}% step on {X}, staged over {X} weeks, and re-measure elasticity before the next move.",
        expected_effect=f"A second inelastic step is worth ~${X}/mo with minimal {v.sale_unit} attrition.",
        recommend_when={"state": "inelastic_headroom", "min_signal": "price_history"},
        tags=("pricing", "elasticity", v.family),
    )


def _bundle_vs_alacarte(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your bundle costs you more than selling the parts",
        observation=f"The {X} bundle is priced {X}% below the sum of its items, yet {X}% of buyers would have bought the anchor item anyway.",
        reasoning=f"A bundle discount only pays for itself if it adds incremental items; here it mostly subsidizes {unit}s customers already wanted — leaking margin per bundle.",
        conclusion=f"Narrow the bundle discount to {X}% or swap a low-cost-high-perceived-value add-in for the discounted hero item.",
        expected_effect=f"Re-cutting the bundle recovers ~${X} per bundle, ~${X}/mo at current bundle mix.",
        recommend_when={"state": "bundle_underpriced", "min_signal": "item_costs"},
        tags=("pricing", "bundle", "margin", v.family),
    )


def _loss_leader_no_attach(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your loss-leader pulls traffic but not attach",
        observation=f"{X} is priced below cost to drive visits, but only {X}% of those {unit}s attach a full-margin item — below the {X}% the math requires.",
        reasoning=f"A loss-leader is an investment that only returns through attach; without the follow-on sale you're buying volume at a loss with no margin chaser behind it.",
        conclusion=f"Pair {X} with a one-tap {X} add-on prompt at the {v.staff_role}/checkout, or lift its price toward cost until attach earns the subsidy.",
        expected_effect=f"Lifting attach from {X}% to {X}% turns the loss-leader profitable — ~${X}/mo.",
        recommend_when={"state": "loss_leader_low_attach", "min_signal": "transactions"},
        tags=("pricing", "attach", v.family),
    )


def _surcharge_not_passed(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"A real cost increase isn't being passed through",
        observation=f"Your {X} input cost rose {X}% this period, but no surcharge or line-item pass-through appears on {v.sale_unit}s.",
        reasoning=f"Absorbing a discrete, explainable cost (materials, fuel, supplier fee) instead of surcharging it eats margin that customers generally accept when itemized and named.",
        conclusion=f"Add a transparent {X}% {X} surcharge (or fold it into the {X} price) and signal it as a pass-through, not a margin grab.",
        expected_effect=f"Passing through the increase protects ~${X}/mo currently absorbed as lost margin.",
        recommend_when={"state": "cost_not_passed_through", "min_signal": "item_costs"},
        tags=("pricing", "surcharge", "margin", v.family),
    )


def _promo_cannibalization(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your {X} promo is mostly cannibalizing full-price {unit}s",
        observation=f"{X}% of promo-window {unit}s come from customers who used to buy at full price in the adjacent {X} window — net new traffic is only {X}%, and {v.core_kpis[0]} barely moved.",
        reasoning=f"A promo that shifts existing demand instead of adding it just discounts {unit}s you'd have made anyway; the discount is a transfer from your margin to the same customers, and it pulls your {v.staff_role}s into a discounted rush that doesn't grow the day.",
        conclusion=f"Tighten the promo to off-peak {X} only, or make it require an attach/min-spend so it adds {unit}s rather than relocating them.",
        expected_effect=f"Stopping the cannibalized portion recovers ~${X}/mo of needlessly discounted margin.",
        recommend_when={"state": "promo_cannibalizing", "min_signal": "hourly_revenue"},
        tags=("pricing", "promo", v.family),
    )


def _cost_increase_not_repriced(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"{X} items rose in cost but haven't been repriced",
        observation=f"{X} {v.sale_unit} lines saw supplier cost up {X}%+ since their last price change {X} months ago — their menu/shelf price is stale.",
        reasoning=f"Price lists that lag cost changes erode margin item-by-item invisibly; the longer the lag, the more {v.sale_unit}s sell at last year's economics.",
        conclusion=f"Reprice the {X} affected lines to restore their original margin %, starting with the highest-volume ones.",
        expected_effect=f"Closing the repricing lag restores ~${X}/mo of margin already lost to cost drift.",
        recommend_when={"state": "stale_prices_vs_cost", "min_signal": "item_costs"},
        tags=("pricing", "cost", "margin", v.family),
    )


def _price_anchoring_missing(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"No high anchor — customers default to your cheapest {unit}",
        observation=f"Your menu/price list has no clearly-premium anchor, and {X}% of {unit}s land on the two lowest price points.",
        reasoning=f"Without a visibly-expensive anchor, the cheapest option looks like the safe choice; a high anchor (even one that rarely sells) re-frames mid-tier {unit}s as the sensible value pick.",
        conclusion=f"Add a deliberate premium anchor at {X}% above your current top price to pull selection toward the mid tier — it earns its keep even at {X}% take.",
        expected_effect=f"Re-anchoring typically lifts average {unit} value {X}% — ~${X}/mo — with no cost change.",
        recommend_when={"state": "no_price_anchor", "min_signal": "transactions"},
        tags=("pricing", "anchoring", "behavioral", v.family),
    )


def _daypart_dynamic_pricing(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"One flat price across very different dayparts",
        observation=f"Demand for {v.sale_unit}s swings {X}x between your {X} peak and your {X} lull, but price is identical in both.",
        reasoning=f"A single price under-charges scarce peak capacity and over-charges the dead window; daypart pricing both captures peak willingness-to-pay and pulls price-sensitive demand into the trough.",
        conclusion=f"Trial a {X}% peak uplift on {X} and a {X}% off-peak incentive in the {X} window for {X} weeks.",
        expected_effect=f"Daypart spread captures peak margin and fills the trough — ~${X}/mo combined.",
        recommend_when={"state": "flat_price_variable_demand", "min_signal": "hourly_revenue"},
        tags=("pricing", "daypart", "demand", v.family),
    )


def _minimum_order_threshold(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Small {unit}s are unprofitable with no order minimum",
        observation=f"{X}% of {X}-channel {unit}s fall below ${X}, where fixed {v.core_kpis[0]}-driving prep/handling cost outweighs the margin earned.",
        reasoning=f"Below a break-even ticket, every {v.family} {unit} loses money on fulfillment once the {v.staff_role}'s prep and packing time is counted; a minimum (or a small-order fee) either lifts the ticket or stops the loss-making ones.",
        conclusion=f"Set a ${X} order minimum on {X} (or a ${X} small-order fee), nudging sub-threshold {unit}s up to a profitable size.",
        expected_effect=f"Eliminating sub-break-even {unit}s and lifting the rest is worth ~${X}/mo.",
        recommend_when={"state": "unprofitable_small_orders", "min_signal": "transactions"},
        tags=("pricing", "threshold", "delivery", v.family),
    )


def _category_mix_margin_drift(v: Vertical, situation: str) -> Built:
    extra = {
        "declining": " The shift is sustained — defend blended margin by repricing or re-merchandising, not by waiting it out.",
    }.get(situation, "")
    return Built(
        title=f"Your sales mix is drifting toward low-margin categories",
        observation=f"The {X} category (margin {X}%) grew to {X}% of {v.sale_unit}s while your {X} high-margin category shrank — blended margin fell even at flat prices.{extra}",
        reasoning=f"Mix drift erodes margin without any single price moving; the P&L weakens purely because the basket is shifting toward thinner items.",
        conclusion=f"Re-merchandise or reprice to push mix back: feature {X} high-margin lines and lift the price floor on the growing low-margin category.",
        expected_effect=f"Restoring {X} points of mix is worth ~${X}/mo with no traffic change.",
        recommend_when={"state": "margin_mix_drift", "min_signal": "item_costs"},
        tags=("margin", "mix", v.family),
    )


def _attach_addon_underpriced(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your highest-attach add-on is priced too timidly",
        observation=f"{X} attaches to {X}% of {unit}s — clearly a want — yet it's priced at only {X}% of the base {unit}.",
        reasoning=f"An add-on customers reach for almost reflexively has pricing power the base item doesn't; a small lift on a high-attach extra compounds across nearly every {unit}.",
        conclusion=f"Lift {X} by {X}%; at its attach rate the volume risk is low and the per-{unit} margin gain is broad.",
        expected_effect=f"A {X}% lift across {X}% attach is worth ~${X}/mo in incremental margin.",
        recommend_when={"state": "addon_underpriced", "min_signal": "transactions"},
        tags=("pricing", "attach", v.family),
    )


def _tier_gap_good_better_best(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You sell cheap and premium but nothing in between",
        observation=f"{X}% of {unit}s land at your entry price and {X}% at premium, with a hollow middle — buyers are forced down because there's no 'better' option.",
        reasoning=f"A bimodal ladder pushes mid-intent customers to the floor; a deliberate middle tier captures the fence-sitters who want more than entry but won't jump to premium.",
        conclusion=f"Introduce a 'better' {unit} between your two price points, positioned {X}% above entry, to catch the down-forced middle.",
        expected_effect=f"A middle tier converts down-forced buyers upward — ~${X}/mo in mix uplift.",
        recommend_when={"state": "missing_middle_tier", "min_signal": "transactions"},
        tags=("pricing", "tiering", v.family),
    )


def _charm_pricing_absent(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Round-number prices are leaving psychological margin on the table",
        observation=f"{X}% of your {unit} prices sit on round numbers (${X}.00) rather than charm endings, and your top sellers are among them.",
        reasoning=f"Charm endings shift perceived price down a band while capturing nearly the same dollars; round prices forfeit that free perception gain on your highest-volume {unit}s.",
        conclusion=f"Restructure the {X} round-priced top sellers to charm endings and, where perception allows, capture the rounding upward instead of down.",
        expected_effect=f"Charm restructuring is a near-zero-risk ~${X}/mo capture across high-volume {unit}s.",
        recommend_when={"state": "round_price_points", "min_signal": "price_list"},
        tags=("pricing", "psychology", v.family),
    )


# ── flag/family-targeted levers ──────────────────────────────────────────
def _markdown_too_deep(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your clearance markdowns cut deeper than they need to",
        observation=f"{X} category cleared at {X}% off, but {X}% of those units sold within {X} days at the first markdown — the deeper cuts weren't needed to move them.",
        reasoning=f"Markdown depth should track aging, not panic; over-cutting fresh-aged stock gives away margin on units that would have cleared at a shallower discount.",
        conclusion=f"Stage markdowns ({X}% → {X}% → {X}%) by weeks-on-hand instead of one deep cut, reserving the deepest tier for genuinely aged {unit}s.",
        expected_effect=f"Staged markdowns recover ~${X}/mo of margin currently given away on early-clearing stock.",
        recommend_when={"state": "markdown_too_deep", "min_signal": "transactions"},
        tags=("pricing", "markdown", "inventory", v.family),
    )


def _premium_mix_shift_down(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "declining": " The trade-down is accelerating — intervene on merchandising/pricing before it resets your baseline ticket.",
    }.get(situation, "")
    return Built(
        title=f"Customers are trading down to your cheaper {unit}s",
        observation=f"Premium-tier share of {unit}s fell from {X}% to {X}% over {X} months while entry-tier share rose — average {unit} value is sliding.{extra}",
        reasoning=f"A trade-down trend quietly lowers ticket and margin even at unchanged prices; left alone it re-baselines customer expectations around the cheaper option.",
        conclusion=f"Re-merchandise the premium tier (visibility, bundling, {v.staff_role} prompts) and narrow the entry-to-premium gap so the step up feels smaller.",
        expected_effect=f"Recovering {X} points of premium share is worth ~${X}/mo in ticket value.",
        recommend_when={"state": "premium_trading_down", "min_signal": "transactions"},
        tags=("pricing", "mix", "premium", v.family),
    )


def _membership_underpriced(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your membership is priced below the value members actually pull",
        observation=f"Active members consume ${X} of {v.sale_unit} value per month against a ${X} membership price — a give-back of {X}% to your heaviest users.",
        reasoning=f"A membership that costs less than the value it unlocks subsidizes your most engaged customers — exactly the segment with the most willingness-to-pay and the least churn risk.",
        conclusion=f"Lift the membership price {X}% or add a usage cap/tier above the current one; high-usage members rarely churn over a modest increase.",
        expected_effect=f"Repricing the membership to its value is worth ~${X}/mo across the active base.",
        recommend_when={"state": "membership_underpriced", "min_signal": "membership_ledger"},
        tags=("pricing", "membership", v.family),
    )


def _seasonal_repricing_lag(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "seasonal_peak": " The peak is approaching — set the seasonal price before demand arrives, not after.",
        "seasonal_trough": " A trough is coming — pre-set a value price to protect volume rather than discount reactively.",
    }.get(situation, "")
    return Built(
        title=f"You hold one price through a {X}x seasonal demand swing",
        observation=f"{v.sale_unit} demand swings {X}x between your {X} season and off-season, yet price never moves with it.{extra}",
        reasoning=f"Flat year-round pricing under-charges in-season scarcity and over-charges in the slow season; seasonal pricing captures peak willingness-to-pay and defends off-season volume.",
        conclusion=f"Set an in-season {X}% uplift on {X} and an off-season value price, scheduled {X} weeks ahead of each turn.",
        expected_effect=f"Seasonal price spread is worth ~${X}/yr versus a single flat price.",
        recommend_when={"state": "seasonal_price_lag", "min_signal": "price_history"},
        tags=("pricing", "seasonal", v.family),
    )


def _high_ticket_discount_authority(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Discretionary discounts on big-ticket {unit}s are leaking margin",
        observation=f"{X}% of {unit}s above ${X} carry a {v.staff_role}-applied discount averaging {X}%, with wide variance between {v.staff_role}s on similar deals.",
        reasoning=f"Unbounded discount authority on high-ticket sales lets margin walk out the door deal-by-deal; the variance shows it's discretion, not a market necessity.",
        conclusion=f"Cap discretionary discounts at {X}% above ${X} (manager approval beyond that) and coach the high-discount {v.staff_role}s on holding price.",
        expected_effect=f"Tightening discount authority on big tickets protects ~${X}/mo in margin.",
        recommend_when={"state": "discount_authority_leak", "min_signal": "discounts_applied"},
        tags=("pricing", "discount", "high_ticket", v.family),
    )


def _gift_card_breakage(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Gift-card breakage isn't being recognized or worked",
        observation=f"${X} in gift cards issued over {X} months has {X}% still unredeemed past {X} months — a quiet liability with predictable breakage.",
        reasoning=f"Aged unredeemed balances are near-certain margin once breakage policy/period is set, and active gift-card sale is pre-paid, full-margin revenue with a redemption upside on attach.",
        conclusion=f"Recognize breakage on balances older than {X} months per policy, and push gift-card sales at {v.sale_unit} checkout to grow the float.",
        expected_effect=f"Recognized breakage plus float growth is worth ~${X} over the next {X} months.",
        recommend_when={"state": "giftcard_breakage", "min_signal": "gift_card_ledger"},
        tags=("pricing", "gift_card", "cashflow", v.family),
    )


def _delivery_platform_erosion(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Third-party delivery commission is eating your {unit} margin",
        observation=f"{X}% of {unit}s flow through delivery platforms at {X}% commission, leaving net margin of {X}% — below your in-house margin of {X}%, even as {v.core_kpis[0]} looks healthy.",
        reasoning=f"Platform {unit}s look like growth but each is sold at a structurally thinner margin, and your {v.staff_role}s do the same prep work for less; without a delivery-specific price it can be volume that loses money at the bottom line.",
        conclusion=f"Set platform-menu prices {X}% above in-house to offset commission, and steer repeat customers to first-party ordering with a {X} incentive.",
        expected_effect=f"Right-pricing platform menus and shifting repeat demand in-house is worth ~${X}/mo.",
        recommend_when={"state": "delivery_margin_erosion", "min_signal": "platform_payouts"},
        tags=("pricing", "delivery", "margin", v.family),
    )


def _volume_discount_unprofitable(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your bulk/multi-unit discount tier sells below break-even",
        observation=f"The {X}-unit discount tier prices each {unit} {X}% off, dropping net margin to {X}% — under the {X}% your fixed costs require.",
        reasoning=f"Volume discounts only pay off if they unlock genuinely incremental units or lower per-unit cost; here the tier just discounts demand you'd capture anyway, below break-even.",
        conclusion=f"Reset the bulk tier to no deeper than {X}% off (the break-even floor) or attach a minimum that makes the volume genuinely incremental.",
        expected_effect=f"Re-flooring the volume tier stops ~${X}/mo of below-cost selling.",
        recommend_when={"state": "volume_discount_below_breakeven", "min_signal": "item_costs"},
        tags=("pricing", "discount", "margin", v.family),
    )


register(
    # ── universal ──
    Archetype(
        key="discount_leakage", domain="pricing", name="Category over-discounted",
        build=_discount_leakage, situations=("baseline", "leaking"),
        required_signals=("discounts_applied", "transactions"),
        required_agents=("DiscountAuditor", "MarginAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="DiscountMarginAgent: join discounts_applied to item_costs so 'leakage' is measured against true margin, not list price; cost basis not yet ingested (see CostBasisAgent).",
    ),
    Archetype(
        key="margin_compression_trend", domain="pricing", name="Margin compression trend",
        build=_margin_compression_trend, situations=("baseline", "declining", "anomaly"),
        required_signals=("item_costs", "transactions"),
        required_agents=("MarginAnalyzer", "PriceAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CostBasisAgent: ingest supplier invoices / per-item cost so gross margin (and its trend) can be computed; no cost feed is ingested today.",
    ),
    Archetype(
        key="underpriced_high_demand", domain="pricing", name="Underpriced high-demand item",
        build=_underpriced_high_demand, situations=("baseline", "emerging"),
        required_signals=("transactions", "discounts_applied"),
        required_agents=("PriceAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="DemandPriceAgent: combine sell-through + zero-discount signal to rank willingness-to-pay; true headroom needs elasticity from price_history (see PriceHistoryAgent).",
    ),
    Archetype(
        key="premium_tier_untapped", domain="pricing", name="Premium tier untapped",
        build=_premium_tier_untapped, situations=("baseline", "untapped"),
        required_signals=("transactions", "price_list"),
        required_agents=("CatalogAgent", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="price_elasticity_headroom", domain="pricing", name="Elasticity headroom",
        build=_price_elasticity_headroom, situations=("baseline",),
        required_signals=("price_history", "transactions"),
        required_agents=("ElasticityAgent", "PriceAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="PriceHistoryAgent: snapshot the catalog over time to detect past price changes and pair them with volume, enabling elasticity estimation; price history is not retained today.",
    ),
    Archetype(
        key="bundle_vs_alacarte_margin", domain="pricing", name="Bundle vs a-la-carte margin",
        build=_bundle_vs_alacarte, situations=("baseline",),
        required_signals=("item_costs", "transactions"),
        required_agents=("MarginAnalyzer", "CatalogAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CostBasisAgent (shared): per-component cost is required to compare bundle margin to the sum of its parts; not ingested today.",
    ),
    Archetype(
        key="loss_leader_no_attach", domain="pricing", name="Loss-leader not converting attach",
        build=_loss_leader_no_attach, situations=("baseline",),
        required_signals=("transactions",),
        required_agents=("RevenueAnalyzer", "PriceAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="AttachAnalyzer: basket-level attach is derivable from transactions, but confirming the leader is below cost needs item_costs (CostBasisAgent).",
    ),
    Archetype(
        key="surcharge_not_passed_through", domain="pricing", name="Cost not passed through",
        build=_surcharge_not_passed, situations=("baseline",),
        required_signals=("item_costs", "price_history"),
        required_agents=("MarginAnalyzer", "PriceAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CostBasisAgent (shared): detecting an un-passed-through cost increase needs both ingested input costs and price history; neither is captured today.",
    ),
    Archetype(
        key="promo_cannibalization", domain="pricing", name="Promo cannibalization",
        build=_promo_cannibalization, situations=("baseline",),
        required_signals=("hourly_revenue", "discounts_applied"),
        required_agents=("DiscountAuditor", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PromoLiftAgent: separate net-new from shifted demand by comparing promo-window mix to a matched control period; needs customer/visit identity to be fully causal.",
        applies_families=("food_service",),
    ),
    Archetype(
        key="cost_increase_not_repriced", domain="pricing", name="Stale prices vs cost",
        build=_cost_increase_not_repriced, situations=("baseline",),
        required_signals=("item_costs", "price_history"),
        required_agents=("MarginAnalyzer", "PriceAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CostBasisAgent + PriceHistoryAgent (shared): repricing lag needs both the cost timeline and the last-price-change date per item; neither is ingested today.",
    ),
    Archetype(
        key="price_anchoring_missing", domain="pricing", name="Price anchor missing",
        build=_price_anchoring_missing, situations=("baseline",),
        required_signals=("transactions", "price_list"),
        required_agents=("CatalogAgent", "PriceAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="daypart_dynamic_pricing", domain="pricing", name="Daypart pricing opportunity",
        build=_daypart_dynamic_pricing, situations=("baseline",),
        required_signals=("hourly_revenue", "transactions"),
        required_agents=("PatternAnalyzer", "PriceAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="minimum_order_threshold", domain="pricing", name="Minimum order threshold",
        build=_minimum_order_threshold, situations=("baseline",),
        required_signals=("transactions",),
        required_agents=("RevenueAnalyzer", "PriceAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="OrderEconomicsAgent: ticket-size distribution is in transactions, but the break-even threshold needs per-order fulfillment cost (CostBasisAgent).",
        applies_flags=("delivery_capable",),
    ),
    Archetype(
        key="category_mix_margin_drift", domain="pricing", name="Margin mix drift",
        build=_category_mix_margin_drift, situations=("baseline", "declining"),
        required_signals=("item_costs", "transactions"),
        required_agents=("MarginAnalyzer", "MixAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CostBasisAgent (shared): blended-margin drift requires per-category margin, which needs ingested item costs; not available today.",
    ),
    Archetype(
        key="attach_addon_underpriced", domain="pricing", name="Add-on underpriced",
        build=_attach_addon_underpriced, situations=("baseline",),
        required_signals=("transactions",),
        required_agents=("RevenueAnalyzer", "PriceAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="AttachAnalyzer (shared): attach rate is derivable from transactions; pricing-power confidence improves with elasticity from price_history.",
    ),
    Archetype(
        key="tier_gap_good_better_best", domain="pricing", name="Missing middle tier",
        build=_tier_gap_good_better_best, situations=("baseline",),
        required_signals=("transactions", "price_list"),
        required_agents=("CatalogAgent", "MixAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="charm_pricing_absent", domain="pricing", name="Charm pricing absent",
        build=_charm_pricing_absent, situations=("baseline",),
        required_signals=("price_list",),
        required_agents=("CatalogAgent",),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="volume_discount_unprofitable", domain="pricing", name="Volume discount below break-even",
        build=_volume_discount_unprofitable, situations=("baseline",),
        required_signals=("item_costs", "discounts_applied"),
        required_agents=("MarginAnalyzer", "DiscountAuditor"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CostBasisAgent (shared): break-even on a bulk tier needs per-unit cost; not ingested today.",
    ),
    # ── flag/family targeted ──
    Archetype(
        key="markdown_too_deep", domain="pricing", name="Markdown too deep",
        build=_markdown_too_deep, situations=("baseline",),
        required_signals=("transactions", "price_history"),
        required_agents=("PriceAnalyzer", "MarginAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="MarkdownCadenceAgent: markdown depth + days-to-clear come from transactions+price_history; original-cost margin needs CostBasisAgent for the full picture.",
        applies_flags=("inventory_heavy",),
    ),
    Archetype(
        key="premium_mix_shift_down", domain="pricing", name="Trade-down trend",
        build=_premium_mix_shift_down, situations=("baseline", "declining"),
        required_signals=("transactions",),
        required_agents=("MixAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="TierMixAgent: requires items to be tagged by tier (entry/premium) so share-shift is measurable; catalog tier tagging is not yet standardized.",
        applies_families=("retail", "food_service", "hospitality"),
    ),
    Archetype(
        key="membership_underpriced", domain="pricing", name="Membership underpriced",
        build=_membership_underpriced, situations=("baseline",),
        required_signals=("membership_ledger", "transactions"),
        required_agents=("MembershipAgent", "MarginAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="MembershipValueAgent: member price is known, but value-consumed must be attributed per member (needs member_id on transactions) to size the give-back.",
        applies_flags=("membership",),
    ),
    Archetype(
        key="seasonal_repricing_lag", domain="pricing", name="Seasonal repricing lag",
        build=_seasonal_repricing_lag, situations=("baseline", "seasonal_peak", "seasonal_trough"),
        required_signals=("price_history", "hourly_revenue"),
        required_agents=("PriceAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="SeasonalPriceAgent: seasonal demand is derivable, but confirming price never moves with season needs price_history (PriceHistoryAgent).",
        applies_flags=("seasonal",),
    ),
    Archetype(
        key="high_ticket_discount_authority", domain="pricing", name="Discount authority leak",
        build=_high_ticket_discount_authority, situations=("baseline",),
        required_signals=("discounts_applied", "transactions"),
        required_agents=("DiscountAuditor", "MarginAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="DiscountAttributionAgent: discount depth by ticket is in transactions; attributing it per staff member needs employee_id on the sale (same gap as labor StaffAttribution).",
        applies_flags=("high_ticket",),
    ),
    Archetype(
        key="gift_card_breakage", domain="pricing", name="Gift-card breakage",
        build=_gift_card_breakage, situations=("baseline",),
        required_signals=("gift_card_ledger",),
        required_agents=("GiftCardAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="GiftCardLedgerAgent: ingest gift-card issuance/redemption events to compute outstanding liability and breakage by age cohort; not ingested today.",
        applies_families=("retail", "food_service", "personal_care", "fitness", "hospitality"),
    ),
    Archetype(
        key="delivery_platform_margin_erosion", domain="pricing", name="Delivery commission erosion",
        build=_delivery_platform_erosion, situations=("baseline",),
        required_signals=("platform_payouts", "transactions"),
        required_agents=("MarginAnalyzer", "ChannelAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="PlatformPayoutAgent: ingest third-party delivery payout statements to attribute commission per order and compute net delivery margin; payout feed not ingested today.",
        applies_flags=("delivery_capable",),
    ),
)
