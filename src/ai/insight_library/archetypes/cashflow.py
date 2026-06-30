"""
Domain: CASHFLOW / FINANCIAL HEALTH.

Each archetype is a distinct reasoning pattern about financial health and the
TIMING of cash — margin trend, cash-conversion cycle, settlement lag, runway,
receivables, and the gap between when money is earned and when it actually lands.
Specialization per vertical changes the binding constraint (inventory cash-trap
for inventory-heavy retail; AR aging for invoiced home services; MRR trend for
membership models; working-capital swing for seasonal trades), so a grocery
cashflow insight and a gym cashflow insight are genuinely different reasoning.

The swarm ingests daily_revenue, transactions, merchant_health (score/category/
trend), and credit_ledger. It does NOT ingest cost-of-goods, payables, supplier
terms, or invoice aging — so most of these are PARTIAL/MISSING with an upgrade
spec for a CashflowAgent / MarginTrendAgent.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register


# ── Margin & profitability ───────────────────────────────────────────────
def _margin_trend_declining(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "declining": " The slope is steepening, not flattening — act before it crosses your break-even line.",
    }.get(situation, "")
    return Built(
        title=f"Gross margin has slipped {X} points over {X} months",
        observation=f"Margin per {unit} fell from {X}% to {X}% across {X} months while {v.core_kpis[0]} held roughly flat.",
        reasoning=f"Flat volume with falling margin means cost is rising faster than price — every {unit} now carries less contribution, so the business runs harder for the same money. Catching the slope early is the difference between a price tweak and a structural squeeze.{extra}",
        conclusion=f"Identify the {X} cost lines driving the slip and either reprice the affected {unit}s or renegotiate input cost before margin crosses break-even.",
        expected_effect=f"Arresting the {X}-point slide preserves ~${X}/mo of contribution.",
        recommend_when={"state": "margin_declining", "min_signal": "cost_ledger"},
        tags=("cashflow", "margin", v.family),
    )


def _revenue_up_profit_flat(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Revenue up {X}% but profit flat — growth isn't paying",
        observation=f"Sales grew {X}% over {X} months while take-home stayed within {X}% of prior — costs absorbed the entire gain.",
        reasoning=f"Profitless growth is the most expensive kind: you've added {v.sale_unit} volume, labor, and working capital but kept none of it, so the business is bigger and more fragile without being richer — distinct from a margin slide because the rate may be fine while incremental cost eats the increment.",
        conclusion=f"Decompose the {X}% revenue gain into the cost lines that grew with it and stop funding the unprofitable slice.",
        expected_effect=f"Converting even half the growth to profit is worth ~${X}/mo that is currently passing straight through.",
        recommend_when={"state": "growth_not_converting", "min_signal": "cost_ledger"},
        tags=("cashflow", "profitability", v.family),
    )


def _discount_funded_growth(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your growth is discount-funded — {X}% of new volume is unprofitable",
        observation=f"{X}% of the last {X} months' {unit} growth carried a discount over {X}%, at a margin below your blended average.",
        reasoning=f"Discount-driven volume can look like momentum while quietly destroying cash: each promoted {unit} may sell below its true cost-to-serve, so growth ACCELERATES the cash drain rather than easing it — the opposite of what the topline implies.",
        conclusion=f"Measure contribution margin on discounted vs full-price {unit}s and cap promotions that clear below ${X} contribution.",
        expected_effect=f"Pruning unprofitable promoted volume recovers ~${X}/mo of cash now subsidizing the discount.",
        recommend_when={"state": "discount_funded_growth", "min_signal": "discount_events"},
        tags=("cashflow", "margin", "discounts", v.family),
    )


def _channel_margin_erosion(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Delivery/platform fees are eroding {X} points of margin",
        observation=f"{X}% of {unit}s now flow through {' / '.join([c for c in v.channels if c in ('delivery', 'online')][:2]) or 'third-party'} channels at a {X}% fee, up from {X}% a year ago.",
        reasoning=f"Third-party {' / '.join([c for c in v.channels if c in ('delivery', 'online')][:1]) or 'delivery'} volume often grows precisely where margin is thinnest: the platform fee is taken off the top of each {unit}, so a rising channel mix silently lowers blended margin even when the menu price is unchanged — a channel problem, not a pricing one.",
        conclusion=f"Compare net margin by channel and either add a channel-specific price or steer demand toward your owned channels.",
        expected_effect=f"Recovering the fee gap on {X}% of {unit}s is worth ~${X}/mo of margin.",
        recommend_when={"state": "channel_margin_erosion", "min_signal": "channel_fee_ledger"},
        tags=("cashflow", "margin", "channel", v.family),
    )


def _labor_cost_creep(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    return Built(
        title=f"Labor cost is outgrowing revenue — ratio up {X} points",
        observation=f"{role} cost rose to {X}% of revenue over {X} months, up from {X}%, while {v.sale_unit} volume grew only {X}%.",
        reasoning=f"When labor's share of revenue creeps up faster than sales, scheduled hours have decoupled from demand — you're paying for capacity the {unit}s aren't filling, which compresses cash even with a healthy topline, distinct from a margin-on-goods problem.",
        conclusion=f"Re-tie {role} hours to demand by daypart and hold the labor ratio at your {X}% target.",
        expected_effect=f"Returning to target trims ~${X}/mo of labor not backed by revenue.",
        recommend_when={"state": "labor_ratio_creep", "min_signal": "schedule_shifts"},
        tags=("cashflow", "labor_cost", v.family),
    )


# ── Cash timing & working capital ────────────────────────────────────────
def _cash_conversion_cycle_long(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Cash is tied up {X} days from purchase to sale",
        observation=f"Inventory sits ~{X} days before a {v.sale_unit} clears it, while supplier terms give you only {X} days to pay.",
        reasoning=f"For an inventory-heavy {v.family.replace('_', ' ')} operator the cash-conversion cycle IS the cash problem: when stock outlives your payables window you fund the gap out of pocket, so growth makes the squeeze worse — every extra {v.sale_unit} of inventory deepens it.",
        conclusion=f"Shorten the cycle by trimming slow SKUs to a {X}-day cover and pushing supplier terms toward your actual sell-through.",
        expected_effect=f"Cutting the cycle by {X} days frees ~${X} of cash currently locked in the shelf.",
        recommend_when={"state": "cash_cycle_long", "min_signal": "inventory_turns"},
        tags=("cashflow", "working_capital", "inventory", v.family),
    )


def _inventory_cash_trap(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"${X} of cash trapped in slow-moving stock",
        observation=f"{X}% of inventory value hasn't turned in {X}+ days, concentrated in {X} categories.",
        reasoning=f"Slow stock is cash sitting still: it was paid for, can't be spent, and ages toward markdown or waste — for an inventory-heavy operator this dead capital is invisible on the P&L but very real on the bank balance, distinct from the cycle length because it's the STUCK tail, not the average.",
        conclusion=f"Markdown or return the bottom {X}% of non-turning SKUs and stop reordering them until they clear.",
        expected_effect=f"Releasing trapped stock recovers ~${X} of cash and avoids the markdown that's coming anyway.",
        recommend_when={"state": "inventory_cash_trap", "min_signal": "inventory_aging"},
        tags=("cashflow", "working_capital", "inventory", v.family),
    )


def _payout_settlement_lag(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Card payouts land {X} days after the sale",
        observation=f"Card {unit}s settle to your account ~{X} days after capture, leaving ${X} in transit on an average day.",
        reasoning=f"Settlement lag is a silent overdraft because the {unit} is rung and the customer is gone, yet the cash isn't usable until the processor releases it — so for a thin-buffer operator that float gap can force borrowing to cover payables that fall due before the deposit clears, and the interest on money you've already earned is a pure, avoidable cost.",
        conclusion=f"Set up next-day funding with the processor, or reserve a cash buffer equal to {X} days of card volume to bridge the gap until deposits clear.",
        expected_effect=f"Closing the funding gap removes ~${X} of perpetual in-transit cash from your working balance.",
        recommend_when={"state": "settlement_lag", "min_signal": "credit_ledger"},
        tags=("cashflow", "timing", "settlement", v.family),
    )


def _deposit_timing_vs_payables(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Cash inflows land after your bills are due",
        observation=f"Your largest payables fall around the {X} of the month, but {X}% of deposits arrive after it.",
        reasoning=f"Cashflow stress is rarely about totals — it's about sequence: even a profitable {v.family.replace('_', ' ')} can miss payroll if money goes out before it comes in, so the misalignment of inflow and outflow timing is the risk, not the amount.",
        conclusion=f"Reschedule the {X} largest payables to just after your reliable deposit dates, or shift billing to pull cash in earlier.",
        expected_effect=f"Aligning timing avoids ~${X}/mo of avoidable short-term borrowing and overdraft fees.",
        recommend_when={"state": "inflow_outflow_misalignment", "min_signal": "payables_calendar"},
        tags=("cashflow", "timing", v.family),
    )


def _ar_aging(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"${X} of invoices are past due — {X}% over {X} days",
        observation=f"Outstanding receivables total ${X}, of which {X}% have aged past {X} days against your {X}-day terms.",
        reasoning=f"For an invoiced {v.family.replace('_', ' ')} the {v.sale_unit} isn't done when the work is — it's done when you're paid; aged AR is revenue you've already funded (labor, materials) but haven't collected, so it ties up cash exactly when the next job needs it.",
        conclusion=f"Chase the {X} oldest invoices first, add deposit-on-booking, and put auto-reminders on anything past {X} days.",
        expected_effect=f"Collecting the aged tail returns ~${X} of earned cash to the operating account.",
        recommend_when={"state": "ar_aging", "min_signal": "invoice_ledger"},
        tags=("cashflow", "receivables", v.family),
    )


def _prepay_deposit_acceleration(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Deposits could pull ${X} of cash forward",
        observation=f"{X}% of booked {unit}s are paid only at completion, despite an average {X}-day lead time from booking to service.",
        reasoning=f"For appointment-led work the booking lead time is free working capital you're not using: a deposit at booking converts a future receivable into cash-in-hand today AND cuts no-show loss — the timing lever is unique to businesses that schedule before they serve.",
        conclusion=f"Require a {X}% deposit to confirm any {unit}, charged at booking rather than at service.",
        expected_effect=f"Deposit-at-booking accelerates ~${X} of cash and reduces no-show exposure on the same flow.",
        recommend_when={"state": "deposit_acceleration", "min_signal": "deposit_ledger"},
        tags=("cashflow", "timing", "deposits", v.family),
    )


def _supplier_terms_not_optimized(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Supplier terms leave ${X} of free credit unused",
        observation=f"You pay {X} key suppliers on ~{X}-day terms while peers in {v.family.replace('_', ' ')} hold {X}-day terms on similar volume.",
        reasoning=f"Supplier credit is the cheapest working capital there is — interest-free days between receiving goods and paying for them; under-using it means you fund inventory from your own cash when the vendor would have, an avoidable squeeze for an inventory-heavy operator.",
        conclusion=f"Renegotiate the {X} largest suppliers to extend terms to {X} days, and set a payables policy that holds each invoice to its full due date — using your volume and payment history as the lever.",
        expected_effect=f"Extending terms frees ~${X} of working capital at zero financing cost.",
        recommend_when={"state": "supplier_terms_suboptimal", "min_signal": "payables_terms"},
        tags=("cashflow", "working_capital", "suppliers", v.family),
    )


# ── Coverage, runway & break-even ────────────────────────────────────────
def _fixed_cost_coverage_ratio(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Fixed costs eat the first {X} days of every month",
        observation=f"Rent, insurance, and base payroll total ${X}/mo — {X}% of revenue — and aren't covered until day {X}.",
        reasoning=f"A high fixed-cost share means low operating flexibility: until coverage is reached every dollar is spoken for, so a soft week threatens solvency rather than just profit — the ratio tells you how much cushion the business actually has, independent of margin per {v.sale_unit}.",
        conclusion=f"Track the day-of-month you hit coverage; if it's past day {X}, convert a fixed cost to variable or raise the coverage-day buffer.",
        expected_effect=f"Improving coverage by {X} days adds ~${X} of resilience against a slow stretch.",
        recommend_when={"state": "fixed_cost_heavy", "min_signal": "fixed_cost_ledger"},
        tags=("cashflow", "fixed_cost", "resilience", v.family),
    )


def _break_even_shift_risk(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Break-even has crept up to {X} {unit}s/day",
        observation=f"Your daily break-even rose from {X} to {X} {unit}s over {X} months as costs grew, while average daily volume is {X}.",
        reasoning=f"A rising break-even narrows your safety margin: when the {unit}s-per-day you must sell just to cover costs climbs toward your actual volume, an ordinary slow day flips from low-profit to loss-making — this is the cash early-warning the topline hides.",
        conclusion=f"Pull break-even back down by trimming the {X} cost lines that raised it, or lift average ticket to widen the gap.",
        expected_effect=f"Restoring a {X}-{unit} cushion protects ~${X}/mo against normal demand variance.",
        recommend_when={"state": "break_even_creep", "min_signal": "cost_structure"},
        tags=("cashflow", "break_even", v.family),
    )


def _cash_buffer_runway_thin(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Cash runway is down to ~{X} weeks",
        observation=f"At the current burn, the operating balance covers ~{X} weeks of expenses — below the {X}-week buffer healthy {v.family.replace('_', ' ')} peers hold.",
        reasoning=f"Runway is the master cashflow metric: it folds margin, timing, and fixed cost into one number — weeks of survival — so a thin buffer means a single bad month, equipment failure, or settlement delay becomes existential rather than inconvenient.",
        conclusion=f"Rebuild to a {X}-week buffer by holding ${X}/mo aside until the target is met before any discretionary spend.",
        expected_effect=f"Reaching a {X}-week buffer removes the single largest solvency risk to the business.",
        recommend_when={"state": "runway_thin", "min_signal": "daily_revenue"},
        tags=("cashflow", "runway", "resilience", v.family),
    )


def _revenue_concentration_cash_risk(v: Vertical, situation: str) -> Built:
    extra = {
        "concentrated": " The concentration is tightening, not easing — diversify the inflow before the dependency hardens.",
    }.get(situation, "")
    return Built(
        title=f"{X}% of revenue rides on a single {X}",
        observation=f"One {X} (channel / customer / day) drives {X}% of {v.sale_unit} revenue, up from {X}% a year ago.",
        reasoning=f"Concentrated revenue is a concentrated cashflow risk because a single stumble in that one channel, client, or peak day drives an immediate, large shortfall with nothing to absorb it — so diversification protects cash stability even when total revenue looks healthy, since the danger is the dependency itself, not the dollar total.{extra}",
        conclusion=f"Build a second inflow source up to {X}% of revenue and set a cap on how much any single channel, customer, or day may contribute, so no one stumble can drain the account.",
        expected_effect=f"De-risking the concentration protects ~${X}/mo of revenue exposed to a single point of failure.",
        recommend_when={"state": "revenue_concentrated", "min_signal": "transactions"},
        tags=("cashflow", "concentration", "resilience", v.family),
    )


def _chargeback_reserve_drag(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Processor is holding ${X} in reserve against disputes",
        observation=f"A rolling reserve of {X}% on card volume — ~${X} — is withheld from your payouts due to dispute history.",
        reasoning=f"A reserve is your own earned cash the processor parks until risk passes; it drags working capital exactly like aged AR, but the lever is different — you reduce it by lowering the chargeback rate that triggered it, not by collecting.",
        conclusion=f"Drive the dispute rate under the processor's {X}% line for {X} months to qualify for a reserve reduction.",
        expected_effect=f"Releasing the reserve returns ~${X} of withheld cash to the operating account.",
        recommend_when={"state": "reserve_drag", "min_signal": "credit_ledger"},
        tags=("cashflow", "timing", "chargeback", v.family),
    )


def _refund_drag_on_cash(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Refunds are draining {X}% of gross cash inflow",
        observation=f"Refunds returned ${X} ({X}% of gross) over {X} months, with a {X}-day lag between sale and refund.",
        reasoning=f"Refunds hit cash twice over: you may have already spent the {unit}'s margin before the money is clawed back, so a high, lagging refund rate makes inflow unpredictable and overstates how much cash is truly yours — a timing and reliability problem distinct from the loss-prevention angle.",
        conclusion=f"Reduce refund causes (returns, errors, dissatisfaction) on the top {X} drivers and tighten the refund window.",
        expected_effect=f"Cutting the refund rate stabilizes ~${X}/mo of inflow you can actually plan around.",
        recommend_when={"state": "refund_cash_drag", "min_signal": "transactions"},
        tags=("cashflow", "refunds", "timing", v.family),
    )


# ── Seasonal & subscription ──────────────────────────────────────────────
def _seasonal_cash_trough_runway(v: Vertical, situation: str) -> Built:
    extra = {
        "seasonal_trough": " The trough is approaching now — the reserve has to be built BEFORE it lands, not during.",
    }.get(situation, "")
    return Built(
        title=f"Your {X} season won't cover its own costs",
        observation=f"Revenue in your {X}-month low season runs {X}% below the annual average while fixed costs stay flat.",
        reasoning=f"Seasonal businesses don't fail in the slow season for lack of profit — they fail for lack of CASH: the trough's fixed costs must be pre-funded from peak-season surplus, so the danger is not setting aside enough while money is flowing.{extra}",
        conclusion=f"Reserve ${X}/mo during peak to fully fund the {X}-month trough, and trim variable cost going into the low season.",
        expected_effect=f"A funded trough avoids ~${X} of off-season borrowing and the rate that comes with it.",
        recommend_when={"state": "seasonal_trough_runway", "min_signal": "daily_revenue"},
        tags=("cashflow", "seasonal", "runway", v.family),
    )


def _peak_season_working_capital(v: Vertical, situation: str) -> Built:
    extra = {
        "seasonal_peak": " The ramp is imminent — the inventory/labor buy has to be financed ahead of the revenue it generates.",
    }.get(situation, "")
    return Built(
        title=f"Your {X} peak needs ${X} of working capital first",
        observation=f"Peak revenue runs {X}% above average, but the inventory and {v.staff_role} hours to serve it must be paid {X} weeks ahead of the sales.",
        reasoning=f"The counterintuitive cash risk of a strong season is the RAMP: you spend on stock and staff before the peak revenue arrives, so a great season can create a cash crunch at exactly the moment volume looks best — a working-capital timing problem, not a demand one.",
        conclusion=f"Pre-arrange ${X} of working capital (terms or a seasonal line) to fund the {X}-week ramp ahead of peak.{extra}",
        expected_effect=f"Funding the ramp lets you capture the full peak instead of leaving ~${X} of demand unserved for lack of stock/staff.",
        recommend_when={"state": "peak_working_capital", "min_signal": "daily_revenue"},
        tags=("cashflow", "seasonal", "working_capital", v.family),
    )


def _subscription_mrr_trend(v: Vertical, situation: str) -> Built:
    extra = {
        "declining": " MRR is contracting, so the cash base itself is shrinking — defend retention before adding acquisition spend.",
    }.get(situation, "")
    return Built(
        title=f"Recurring revenue trend is turning — net MRR {X}%",
        observation=f"Membership/recurring revenue moved {X}% over {X} months as {X} new {v.sale_unit}s were offset by {X} cancellations.",
        reasoning=f"For a membership model MRR is the cashflow foundation — predictable, compounding base revenue — so its trend matters more than any single month's sales: churn outrunning new joins erodes the very predictability the model is built on, and the damage compounds.",
        conclusion=f"Track net MRR (new minus churned) weekly and fix the top {X} churn drivers before they outpace acquisition.",
        expected_effect=f"Reversing the trend protects ~${X}/mo of compounding recurring cash.",
        recommend_when={"state": "mrr_trend", "min_signal": "subscription_ledger"},
        tags=("cashflow", "recurring", "membership", v.family),
    )


def _membership_churn_cash_leak(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Membership churn is leaking ${X}/mo of recurring cash",
        observation=f"{X}% of members lapse each month — ${X} of recurring revenue — and {X}% leave within their first {X} weeks.",
        reasoning=f"Churn is a cash leak that compounds backwards: each lapsed member removes not one payment but the entire future stream you'd already counted on, and early churn means you spent acquisition cost you never recovered — distinct from the MRR trend because it isolates the LEAK, not the net.",
        conclusion=f"Target the first-{X}-week onboarding window driving early churn and win back the {X} highest-value recent lapses.",
        expected_effect=f"Cutting churn one point preserves ~${X}/mo of recurring cash plus the acquisition cost behind it.",
        recommend_when={"state": "membership_churn_leak", "min_signal": "subscription_ledger"},
        tags=("cashflow", "recurring", "churn", "membership", v.family),
    )


# ── Fees, liabilities & capital structure ────────────────────────────────
def _processing_fee_drag(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Card processing fees have climbed to {X}% of revenue",
        observation=f"Payment processing cost rose from {X}% to {X}% of card revenue over {X} months as more {unit}s moved to premium-reward and keyed/online cards.",
        reasoning=f"Processing fees skim a percentage off the top of every card {unit}, so as the card mix shifts toward higher-interchange reward and keyed payments the blended rate creeps up and quietly costs real margin — and because it scales with every sale rather than with effort, the leak compounds precisely as volume grows.",
        conclusion=f"Renegotiate the processor rate against your volume, add a compliant card surcharge or cash discount, and route large {unit}s to lower-fee payment methods.",
        expected_effect=f"Trimming the effective rate by {X} points recovers ~${X}/mo straight to the bottom line.",
        recommend_when={"state": "processing_fee_creep", "min_signal": "credit_ledger"},
        tags=("cashflow", "fees", "margin", v.family),
    )


def _gift_card_liability_float(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Outstanding gift cards are ${X} of float you're misreading",
        observation=f"${X} in gift cards and store credit are sold but unredeemed, and {X}% are more than {X} months old.",
        reasoning=f"A gift card is cash collected today against a {unit} you owe later, so the balance is interest-free float now but a real future liability — and because some cards are redeemed alongside extra full-price items while a slice is never redeemed at all, treating the whole balance as either pure profit or pure debt misstates the cash you can actually use.",
        conclusion=f"Set aside a redemption reserve for the live balance, book aged breakage to income on a schedule, and run a campaign to redeem the oldest cards toward higher-ticket {unit}s.",
        expected_effect=f"Managing the float and breakage correctly frees ~${X} of usable cash and recognizes ${X}/mo of earned breakage.",
        recommend_when={"state": "gift_card_float", "min_signal": "gift_card_ledger"},
        tags=("cashflow", "liability", "float", v.family),
    )


def _debt_service_coverage(v: Vertical, situation: str) -> Built:
    extra = {
        "declining": " Coverage is tightening as payments step up — get ahead of it before a soft month can't make the payment.",
    }.get(situation, "")
    return Built(
        title=f"Loan payments eat {X}% of the cash you generate",
        observation=f"Monthly debt service is ${X} against ~${X} of operating cash flow — a coverage ratio of {X}x, below the {X}x lenders consider safe.",
        reasoning=f"Debt service is a fixed claim on cash that comes ahead of almost everything else, so a thin coverage ratio means a single soft month forces a choice between the loan and the operation — and because the payment doesn't flex with revenue, the squeeze lands hardest exactly when sales dip and cash is already short.{extra}",
        conclusion=f"Refinance toward a longer term or lower rate to cut the monthly payment, and reserve a debt-service buffer equal to {X} months of payments before any discretionary spend.",
        expected_effect=f"Restoring coverage to {X}x removes ~${X}/mo of forced-payment risk and frees cash for operations.",
        recommend_when={"state": "thin_debt_coverage", "min_signal": "debt_ledger"},
        tags=("cashflow", "debt", "resilience", v.family),
    )


def _capex_reserve_gap(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"No reserve for equipment that will cost ${X} to replace",
        observation=f"Your core equipment is {X}% through its useful life with an estimated ${X} replacement cost, yet no monthly capital reserve is being set aside for it.",
        reasoning=f"Equipment failure is not a question of if but when, so funding a major replacement out of one month's cash turns a predictable event into a crisis — and because the spend is large and lumpy, an unreserved {v.family.replace('_', ' ')} operator ends up borrowing at a bad rate or deferring the fix, which costs more than the smooth monthly set-aside would have.",
        conclusion=f"Set up a sinking fund and reserve ${X}/mo toward the replacement, sized to the equipment's remaining life, so the capital is in hand before it fails.",
        expected_effect=f"Pre-funding the replacement avoids ~${X} of emergency financing cost versus paying for it in a single month.",
        recommend_when={"state": "capex_reserve_gap", "min_signal": "asset_register"},
        tags=("cashflow", "capex", "resilience", v.family),
    )


def _early_pay_discount_untaken(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You're leaving ${X} of supplier early-pay discounts on the table",
        observation=f"{X} suppliers offer an early-payment discount (e.g. {X}% for paying within 10 days) but {X}% of those invoices are paid late or at net, capturing none of it.",
        reasoning=f"An unclaimed early-pay discount is a guaranteed return you're declining, because the discount annualized usually beats any other use of the cash, so paying late to 'hold' working capital here actually costs more than it saves — the opposite of the supplier-terms lever where stretching is the win.",
        conclusion=f"Capture the early-pay discounts whose annualized rate beats your cost of capital — set the payment run to hit those cutoffs first — and stretch only the terms that carry no discount.",
        expected_effect=f"Taking the worthwhile early-pay discounts saves ~${X}/mo at a return that beats holding the cash.",
        recommend_when={"state": "early_pay_discount_untaken", "min_signal": "payables_terms"},
        tags=("cashflow", "working_capital", "suppliers", "discounts", v.family),
    )


def _milestone_progress_billing(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You fund big jobs to completion before billing a cent",
        observation=f"Jobs over ${X} are billed only on completion after a ~{X}-week build, so you carry {X}% of the {unit} cost (labor + materials) out of pocket meanwhile.",
        reasoning=f"Billing only at the end of a long job means you bank the whole project as a working-capital loan to the customer, because materials and {v.staff_role} wages go out weeks before any cash comes in, so a string of big jobs can starve the account even when every one is profitable.",
        conclusion=f"Bill the job in milestones — collect a deposit at signing and progress draws at set stages — instead of carrying the whole {unit} to completion.",
        expected_effect=f"Milestone billing pulls ~${X} of cash forward per large job and cuts the working-capital drag.",
        recommend_when={"state": "progress_billing_untapped", "min_signal": "invoice_ledger"},
        tags=("cashflow", "working_capital", "receivables", v.family),
    )


register(
    Archetype(
        key="margin_trend_declining", domain="cashflow", name="Declining margin trend",
        build=_margin_trend_declining, situations=("baseline", "declining"),
        required_signals=("daily_revenue", "cost_ledger", "merchant_health"),
        required_agents=("MarginTrendAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="MarginTrendAgent: ingest cost-of-goods per item and trend contribution margin over time. The swarm has revenue and merchant_health trend but no cost data, so margin can't be computed today.",
    ),
    Archetype(
        key="revenue_up_profit_flat", domain="cashflow", name="Profitless growth",
        build=_revenue_up_profit_flat, situations=("baseline",),
        required_signals=("daily_revenue", "cost_ledger"),
        required_agents=("CashflowAgent", "MarginTrendAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: decompose revenue growth against the cost lines that grew with it. Requires a cost ledger the swarm does not ingest.",
    ),
    Archetype(
        key="discount_funded_growth", domain="cashflow", name="Discount-funded growth",
        build=_discount_funded_growth, situations=("baseline",),
        required_signals=("discount_events", "daily_revenue", "cost_ledger"),
        required_agents=("MarginTrendAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="MarginTrendAgent: tag promoted volume and compute its contribution margin vs full-price. Needs line-item discount + cost data.",
    ),
    Archetype(
        key="channel_margin_erosion", domain="cashflow", name="Channel margin erosion",
        build=_channel_margin_erosion, situations=("baseline",),
        applies_flags=("delivery_capable",),
        required_signals=("channel_fee_ledger", "transactions"),
        required_agents=("MarginTrendAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="MarginTrendAgent: split net margin by channel and apply platform-fee schedules. Channel is partially inferable from transactions, but third-party fee rates are not ingested.",
    ),
    Archetype(
        key="labor_cost_creep", domain="cashflow", name="Labor cost creep vs revenue",
        build=_labor_cost_creep, situations=("baseline",),
        required_signals=("schedule_shifts", "daily_revenue"),
        required_agents=("CashflowAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CashflowAgent: trend labor-cost-to-revenue ratio over time. Schedule_shifts and revenue exist; wage rates needed for true cost must be added.",
    ),
    Archetype(
        key="cash_conversion_cycle_long", domain="cashflow", name="Long cash-conversion cycle",
        build=_cash_conversion_cycle_long, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory_turns", "payables_terms"),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: compute days-inventory + days-payable to derive the cash-conversion cycle. Neither inventory turns nor payables terms are ingested.",
    ),
    Archetype(
        key="inventory_cash_trap", domain="cashflow", name="Cash trapped in slow stock",
        build=_inventory_cash_trap, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory_aging",),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: ingest per-SKU inventory aging to isolate the non-turning tail of trapped cash. No inventory aging feed exists.",
    ),
    Archetype(
        key="payout_settlement_lag", domain="cashflow", name="Card payout settlement lag",
        build=_payout_settlement_lag, situations=("baseline",),
        required_signals=("credit_ledger", "transactions"),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CashflowAgent: measure capture-to-deposit lag and compute average in-transit float. Credit_ledger gives settlement records; processor payout timestamps need linking.",
    ),
    Archetype(
        key="deposit_timing_vs_payables", domain="cashflow", name="Inflow/outflow timing mismatch",
        build=_deposit_timing_vs_payables, situations=("baseline",),
        required_signals=("payables_calendar", "daily_revenue"),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: align deposit timing against a payables calendar to flag sequence risk. Payables dates are not ingested.",
    ),
    Archetype(
        key="ar_aging", domain="cashflow", name="Accounts-receivable aging",
        build=_ar_aging, situations=("baseline",),
        applies_families=("home_services",),
        required_signals=("invoice_ledger",),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: ingest the invoice ledger (issued, due, paid dates) to compute AR aging buckets. Invoicing data is not collected.",
    ),
    Archetype(
        key="prepay_deposit_acceleration", domain="cashflow", name="Deposit cash acceleration",
        build=_prepay_deposit_acceleration, situations=("baseline",),
        applies_flags=("appointment_based",),
        required_signals=("deposit_ledger", "transactions"),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: join booking lead time to payment timing to quantify deposit-acceleration opportunity. Booking-to-payment linkage is not ingested.",
    ),
    Archetype(
        key="supplier_terms_not_optimized", domain="cashflow", name="Supplier terms not optimized",
        build=_supplier_terms_not_optimized, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("payables_terms",),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: ingest supplier terms vs peer benchmarks to surface unused free credit. No payables/terms source exists.",
    ),
    Archetype(
        key="fixed_cost_coverage_ratio", domain="cashflow", name="Fixed-cost coverage ratio",
        build=_fixed_cost_coverage_ratio, situations=("baseline",),
        required_signals=("fixed_cost_ledger", "daily_revenue"),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: compute the day-of-month fixed costs are covered from a fixed-cost ledger + daily revenue. Fixed costs are not ingested.",
    ),
    Archetype(
        key="break_even_shift_risk", domain="cashflow", name="Break-even creep",
        build=_break_even_shift_risk, situations=("baseline",),
        required_signals=("cost_structure", "transactions"),
        required_agents=("CashflowAgent", "MarginTrendAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: derive daily break-even from fixed + variable cost structure and trend it vs actual volume. Cost structure is not ingested.",
    ),
    Archetype(
        key="cash_buffer_runway_thin", domain="cashflow", name="Thin cash runway",
        build=_cash_buffer_runway_thin, situations=("baseline",),
        required_signals=("daily_revenue", "merchant_health"),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CashflowAgent: estimate burn and weeks-of-runway from revenue trend + merchant_health. A true balance/expense figure would sharpen it; today only revenue-side proxies exist.",
    ),
    Archetype(
        key="revenue_concentration_cash_risk", domain="cashflow", name="Revenue concentration risk",
        build=_revenue_concentration_cash_risk, situations=("baseline", "concentrated"),
        required_signals=("transactions", "daily_revenue"),
        required_agents=("CashflowAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CashflowAgent: measure revenue share by channel/day/customer to flag concentration. Channel/day are derivable from transactions; per-customer attribution would need customer ids.",
    ),
    Archetype(
        key="chargeback_reserve_drag", domain="cashflow", name="Chargeback reserve drag",
        build=_chargeback_reserve_drag, situations=("baseline",),
        required_signals=("credit_ledger", "chargeback_events"),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: detect processor reserve withholding from payout records. Reserve/dispute data is not pulled from the gateway.",
    ),
    Archetype(
        key="refund_drag_on_cash", domain="cashflow", name="Refund drag on cash",
        build=_refund_drag_on_cash, situations=("baseline",),
        required_signals=("transactions",),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CashflowAgent: quantify refund rate and sale-to-refund lag from transaction history. Refund linkage to original sale is needed for the lag dimension.",
    ),
    Archetype(
        key="seasonal_cash_trough_runway", domain="cashflow", name="Seasonal cash trough runway",
        build=_seasonal_cash_trough_runway, situations=("baseline", "seasonal_trough"),
        applies_flags=("seasonal",),
        required_signals=("daily_revenue",),
        required_agents=("CashflowAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CashflowAgent: project trough revenue vs fixed costs and size the peak-season reserve. Revenue seasonality is derivable; fixed-cost data would make the reserve exact.",
    ),
    Archetype(
        key="peak_season_working_capital", domain="cashflow", name="Peak working-capital ramp",
        build=_peak_season_working_capital, situations=("baseline", "seasonal_peak"),
        applies_flags=("seasonal",),
        required_signals=("daily_revenue",),
        required_agents=("CashflowAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CashflowAgent: model the pre-peak inventory/labor spend lead vs revenue arrival to size working capital. Revenue ramp is derivable; input-cost lead times must be added.",
    ),
    Archetype(
        key="subscription_mrr_trend", domain="cashflow", name="Recurring MRR trend",
        build=_subscription_mrr_trend, situations=("baseline", "declining"),
        applies_flags=("membership",),
        required_signals=("subscription_ledger", "transactions"),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: ingest subscription/membership events (new, churned, value) to compute net MRR trend. Recurring-billing data is not ingested.",
    ),
    Archetype(
        key="membership_churn_cash_leak", domain="cashflow", name="Membership churn cash leak",
        build=_membership_churn_cash_leak, situations=("baseline",),
        applies_flags=("membership",),
        required_signals=("subscription_ledger",),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: isolate churn cohorts (esp. early-life) and value the recurring stream lost. Needs member-level lifecycle data not ingested.",
    ),
    Archetype(
        key="processing_fee_drag", domain="cashflow", name="Card processing fee creep",
        build=_processing_fee_drag, situations=("baseline",),
        required_signals=("credit_ledger", "transactions"),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="CashflowAgent: trend effective processing rate (fees / card volume) and decompose by card type/entry mode. Credit_ledger carries settlement amounts; per-transaction fee and interchange tier need linking from the processor.",
    ),
    Archetype(
        key="gift_card_liability_float", domain="cashflow", name="Gift-card liability float",
        build=_gift_card_liability_float, situations=("baseline",),
        required_signals=("gift_card_ledger",),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: ingest gift-card/store-credit issuance and redemption events to compute outstanding liability, aging, and breakage. Stored-value ledger is not collected today.",
    ),
    Archetype(
        key="debt_service_coverage", domain="cashflow", name="Thin debt-service coverage",
        build=_debt_service_coverage, situations=("baseline", "declining"),
        required_signals=("debt_ledger", "daily_revenue"),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: ingest loan/lease schedules (payment, rate, term) and derive a debt-service-coverage ratio against operating cash flow. Debt obligations are not ingested.",
    ),
    Archetype(
        key="capex_reserve_gap", domain="cashflow", name="Equipment-replacement reserve gap",
        build=_capex_reserve_gap, situations=("baseline",),
        required_signals=("asset_register",),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: ingest an asset register (equipment, age, useful life, replacement cost) to size a monthly sinking-fund reserve vs the lumpy replacement spend. No asset/capex data is collected.",
    ),
    Archetype(
        key="early_pay_discount_untaken", domain="cashflow", name="Unclaimed early-pay discounts",
        build=_early_pay_discount_untaken, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("payables_terms",),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: ingest supplier early-payment discount terms + actual payment dates to flag discounts whose annualized return beats cost of capital. No payables/terms source exists.",
    ),
    Archetype(
        key="milestone_progress_billing", domain="cashflow", name="Progress-billing untapped",
        build=_milestone_progress_billing, situations=("baseline",),
        applies_families=("home_services",),
        required_signals=("invoice_ledger", "transactions"),
        required_agents=("CashflowAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashflowAgent: join job size + duration to billing timing to size the working-capital carried by end-of-job billing. Job-level billing schedule is not ingested.",
    ),
)
