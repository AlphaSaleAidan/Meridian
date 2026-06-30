"""
Domain: PAYMENTS / TRANSACTION MECHANICS.

Each archetype is a distinct reasoning pattern about how money actually moves —
tender mix and processing cost, tipping, disputes, deposits, recurring billing,
receivables, settlement. Specialization is structural: tip levers only fire for
`tipped` verticals, deposit/no-show levers for `appointment_based`/`high_ticket`,
open-tab/split-bill for `table_service`, recurring-payment churn for `membership`,
AR aging for service families. Many of these require feeds the swarm does not yet
ingest (processor statements, dispute feed, cash-drawer counts, gateway decline
logs, payout statements), so their capability is MISSING with the upgrade spec'd.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register


# ── tender mix & processing cost (universal) ─────────────────────────────
def _payment_mix_cost(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"High-fee cards carry too much of your {unit} mix",
        observation=f"{X}% of {unit} volume runs on premium-fee cards (credit/rewards) vs debit/cash, pushing your blended acceptance cost to {X}%.",
        reasoning=f"Tender mix is a cost lever you can steer: every point shifted from premium card to debit or cash drops straight to the bottom line without touching price or volume.",
        conclusion=f"Add a debit/cash incentive (or a card-tier nudge) at the {v.staff_role}/terminal to move {X} points of mix off premium cards.",
        expected_effect=f"Steering tender mix saves ~${X}/mo in acceptance cost at current volume.",
        recommend_when={"state": "expensive_tender_mix", "min_signal": "tender_type"},
        tags=("payments", "fees", "mix", v.family),
    )


def _processing_fee_load(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Processing fees are running {X}% of revenue — above benchmark",
        observation=f"Total card-processing fees equal {X}% of revenue this period, versus a {X}% benchmark for {v.family} of your size.",
        reasoning=f"An above-benchmark effective rate usually signals a mis-matched plan (flat vs interchange-plus), un-optimized downgrades, or surcharge headroom — recoverable without losing a single {v.sale_unit}.",
        conclusion=f"Audit the processor statement for downgrade reasons and renegotiate to interchange-plus, or add compliant surcharging to recover the {X}% gap.",
        expected_effect=f"Closing the {X}% rate gap is worth ~${X}/mo in recovered fees.",
        recommend_when={"state": "high_processing_load", "min_signal": "processor_fees"},
        tags=("payments", "fees", v.family),
    )


def _surcharge_opportunity(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You're absorbing card fees you could compliantly pass on",
        observation=f"{X}% of {unit}s are card-paid with no surcharge or cash-discount program, while acceptance cost runs {X}% of card revenue.",
        reasoning=f"In jurisdictions that permit it, a disclosed card surcharge or cash-discount shifts acceptance cost to the tender that causes it — most customers accept a clearly-posted fee.",
        conclusion=f"Roll out a compliant {X}% card surcharge (or cash discount), posted at entry and the terminal, after confirming local rules.",
        expected_effect=f"Compliant surcharging recovers ~${X}/mo currently absorbed as acceptance cost.",
        recommend_when={"state": "surcharge_untapped", "min_signal": "tender_type"},
        tags=("payments", "surcharge", "fees", v.family),
    )


def _small_ticket_card_fee(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Small card {unit}s are eaten by the flat fee component",
        observation=f"{X}% of card {unit}s are under ${X}, where the fixed per-transaction fee (~${X}) outweighs the percentage fee and crushes net margin.",
        reasoning=f"On tiny tickets the flat fee dominates: a ${X} card sale can hand back a double-digit effective rate, so small-ticket card acceptance is structurally the most expensive money you take.",
        conclusion=f"Set a card minimum of ${X} (or a cash nudge below it) so sub-threshold {unit}s either grow or move to fee-light tender.",
        expected_effect=f"Re-routing small card {unit}s saves ~${X}/mo in flat-fee drag.",
        recommend_when={"state": "small_ticket_fee_drag", "min_signal": "tender_type"},
        tags=("payments", "fees", v.family),
    )


# ── tipping (tipped verticals) ───────────────────────────────────────────
def _tip_rate_below_benchmark(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    extra = {
        "declining": " The tip rate has been sliding, not just sitting low — treat it as an eroding pattern, not a fixed level.",
    }.get(situation, "")
    return Built(
        title=f"Tip rate is running below benchmark for your {role}s",
        observation=f"Average tip is {X}% of {v.sale_unit} value against a {X}% benchmark for {v.family}; the gap is broad, not a few shifts.{extra}",
        reasoning=f"Tips are {role} income and a retention lever, not just customer goodwill; a structural shortfall usually traces to terminal prompts or service flow, both fixable without raising prices.",
        conclusion=f"Reset terminal tip suggestions to {X}/{X}/{X}% and coach the {X} weakest shifts on the ask; re-measure after {X} weeks.",
        expected_effect=f"Closing the tip gap adds ~${X}/mo to {role} take-home and supports retention.",
        recommend_when={"state": "tip_below_benchmark", "min_signal": "tips"},
        tags=("payments", "tips", v.family),
    )


def _tip_screen_default(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    unit = v.sale_unit
    return Built(
        title=f"Your {unit} tip prompt is suppressing what {role}s earn",
        observation=f"Tip-screen defaults on {unit}s are absent or set low (or appear after the customer has mentally checked out), and tip rate sits {X} points under benchmark.",
        reasoning=f"For a {v.family} {role}, the tip prompt is the highest-leverage tipping variable: suggested amounts, ordering, and timing anchor what a {unit} earns far more than service quality does.",
        conclusion=f"Enable suggested tips at {X}/{X}/{X}% on the {unit} screen, present them before payment confirmation, and avoid a $0-first layout.",
        expected_effect=f"Re-configuring the {unit} prompt typically lifts tip rate {X} points — ~${X}/mo to your {role}s.",
        recommend_when={"state": "tip_prompt_misconfigured", "min_signal": "terminal_config"},
        tags=("payments", "tips", "config", v.family),
    )


def _tip_by_shift_variance(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    return Built(
        title=f"Tip rate swings wildly between shifts and {role}s",
        observation=f"Tip rate ranges from {X}% to {X}% across shifts on similar {v.sale_unit}s — a {X}-point spread that tracks who's working, not what's sold.",
        reasoning=f"When the ask, not the service, drives the spread, the low end is a coachable behavior gap; the top performers' approach is a template, not luck.",
        conclusion=f"Pair the {X} lowest-tip {role}s with top earners' ask script for {X} weeks; standardize the winning prompt flow.",
        expected_effect=f"Lifting the bottom shifts toward the median adds ~${X}/mo in tips with no price change.",
        recommend_when={"state": "tip_variance_by_shift", "min_signal": "tips"},
        tags=("payments", "tips", "performance", v.family),
    )


def _tip_cash_vs_card_gap(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    return Built(
        title=f"Card tips far outpace cash tips — reconcile the tip-out",
        observation=f"Card tips average {X}% while recorded cash tips average {X}%, a {X}-point gap on comparable {v.sale_unit}s.",
        reasoning=f"A large card-vs-cash tip gap distorts pooled tip-outs and payout fairness across {role}s, and clouds true take-home — a reconciliation and fairness issue, not a revenue one.",
        conclusion=f"Reconcile cash vs card tips per {role} for tip-out accuracy and confirm the pooling formula reflects the real split.",
        expected_effect=f"Accurate reconciliation protects {role} payout fairness and removes ~${X} of monthly tip-out error.",
        recommend_when={"state": "cash_card_tip_gap", "min_signal": "tips"},
        tags=("payments", "tips", "reconciliation", v.family),
    )


# ── disputes / refunds / cash (universal) ────────────────────────────────
def _chargeback_cluster(v: Vertical, situation: str) -> Built:
    extra = {
        "concentrated": " The disputes cluster on one product/channel/reason — fix that root cause, don't treat it as random.",
        "anomaly": " Disputes spiked suddenly — check for a processing error, fraud run, or a single bad batch first.",
    }.get(situation, "")
    return Built(
        title=f"Chargebacks are clustering — {X}% above your baseline",
        observation=f"Dispute rate hit {X}% of {v.sale_unit}s this period, concentrated in {X} reason code(s)/channel(s).{extra}",
        reasoning=f"Beyond the refunded amount, dispute fees and rising chargeback ratios threaten your processing rate (and account standing); a cluster almost always has one addressable cause.",
        conclusion=f"Root-cause the dominant reason code (descriptor, fulfillment, fraud) and add the matching control — clearer descriptor, signature/AVS, or fulfillment proof.",
        expected_effect=f"Cutting the cluster avoids ~${X}/mo in disputes/fees and protects your rate.",
        recommend_when={"state": "chargeback_cluster", "min_signal": "disputes"},
        tags=("payments", "disputes", "risk", v.family),
    )


def _refund_rate_by_channel(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Refunds are concentrated in your {X} channel",
        observation=f"The {X} channel refunds {X}% of {unit}s vs {X}% elsewhere — a {X}-point gap on the same catalog.",
        reasoning=f"A channel-specific refund spike points to a channel-specific defect (mis-set expectations, fulfillment, or fit), not product quality; the fix is local, not catalog-wide.",
        conclusion=f"Audit the {X} channel's top refund reasons and fix the upstream cause (listing accuracy, handoff, or fulfillment) before discounting to compensate.",
        expected_effect=f"Closing the channel refund gap recovers ~${X}/mo in net {unit} value.",
        recommend_when={"state": "refund_channel_concentration", "min_signal": "refunds"},
        tags=("payments", "refunds", "channel", v.family),
    )


def _cash_vs_card_discrepancy(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Cash collected doesn't reconcile to expected",
        observation=f"Counted cash runs {X}% under expected on {X} of the last {X} closes — a consistent shortfall, not random rounding.",
        reasoning=f"A persistent cash variance signals till error, mis-rings, or shrink; unlike a one-off, a pattern points to a process or person and is worth closing before it compounds.",
        conclusion=f"Tighten close-out: blind drawer counts, per-{v.staff_role} till assignment, and variance review on any close over {X}%.",
        expected_effect=f"Eliminating the recurring shortfall recovers ~${X}/mo and deters shrink.",
        recommend_when={"state": "cash_discrepancy", "min_signal": "cash_drawer"},
        tags=("payments", "cash", "risk", v.family),
    )


# ── deposits / no-shows / tabs (structural) ──────────────────────────────
def _deposit_capture_gap(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"High-value {unit}s are booked without a deposit",
        observation=f"{X}% of {unit}s above ${X} are scheduled with no deposit or card-on-file, and {X}% of those end in a no-show/cancellation.",
        reasoning=f"An un-deposited high-value booking is exposed capacity: a no-show forfeits a slot that can't be re-sold, and there's no captured value to offset it.",
        conclusion=f"Require a {X}% deposit (or card-on-file) on bookings above ${X}, applied to the final {unit}.",
        expected_effect=f"Deposit capture recovers ~${X}/mo of currently-forfeited high-value capacity.",
        recommend_when={"state": "deposit_gap", "min_signal": "bookings"},
        tags=("payments", "deposits", v.family),
    )


def _no_show_fee_uncaptured(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You have a no-show policy but don't charge the fee",
        observation=f"{X}% of {unit}s no-show, but the stated no-show fee is collected on only {X}% of them — the policy exists on paper, not in the till.",
        reasoning=f"An uncollected no-show fee is no deterrent: customers learn the cancellation has no cost, so the no-show rate stays high and the lost slot goes unrecovered.",
        conclusion=f"Auto-charge the card-on-file no-show fee per policy (with a {X}-hour grace + reminder), so the deterrent is real and the slot is partly recovered.",
        expected_effect=f"Enforcing the fee both lowers no-shows and recovers ~${X}/mo in forfeited slots.",
        recommend_when={"state": "no_show_fee_uncaptured", "min_signal": "bookings"},
        tags=("payments", "no_show", v.family),
    )


def _open_tab_leakage(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Open tabs are walking out unclosed",
        observation=f"{X}% of {unit} tabs close to $0 / void or are force-closed at end of night, concentrated in your {X} window.",
        reasoning=f"An unclosed or walked tab is unpaid product plus the {v.staff_role} time to serve it; clustered in one window it's usually a card-hold or hand-off process gap, not random.",
        conclusion=f"Require a card pre-auth to open a tab above ${X} and add an end-of-shift open-tab sweep before {X}.",
        expected_effect=f"Closing the tab-leakage process recovers ~${X}/mo of walked product.",
        recommend_when={"state": "open_tab_leakage", "min_signal": "tab_events"},
        tags=("payments", "tabs", "leakage", v.family),
    )


# ── receivables / recurring (structural) ─────────────────────────────────
def _ar_invoice_aging(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    unit = v.sale_unit
    return Built(
        title=f"Receivables on completed {unit}s are aging past your terms",
        observation=f"{X}% of invoiced {unit} value is past due, with ${X} sitting beyond {X} days — well past your stated terms.",
        reasoning=f"For a {v.family} shop, an earned {unit} stuck in aged AR is cash you've financed for the customer; the older it gets the lower the collection odds, turning {role} labor already spent into write-off risk.",
        conclusion=f"Trigger an automated dunning ladder at {X}/{X}/{X} days, require deposits on new large {unit}s, and put repeat-late accounts on card-on-file before the next {role} is dispatched.",
        expected_effect=f"Tightening collections pulls ~${X} of aged AR back into cash within {X} days.",
        recommend_when={"state": "ar_aging", "min_signal": "invoices"},
        tags=("payments", "receivables", "cashflow", v.family),
    )


def _failed_recurring_payment(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    return Built(
        title=f"Members are churning on failed recurring charges",
        observation=f"{X}% of recurring {v.sale_unit} charges fail each cycle (expired/declined cards), and {X}% of those lapse instead of recovering — involuntary churn hiding inside your {v.core_kpis[0]}.",
        reasoning=f"Involuntary churn is the cheapest churn to fix: these members didn't choose to leave, so a card-update + retry flow saves {v.family} revenue that would otherwise vanish before a {role} ever knows the relationship was at risk.",
        conclusion=f"Add automated card-updater, smart retries, and a pre-expiry update prompt; flag the {X} highest-value at-risk members for {role} outreach.",
        expected_effect=f"Recovering involuntary churn saves ~${X}/mo in otherwise-lost {v.sale_unit} revenue.",
        recommend_when={"state": "failed_recurring_churn", "min_signal": "recurring_billing"},
        tags=("payments", "recurring", "churn", v.family),
    )


def _card_on_file_adoption(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Few repeat customers have a card on file",
        observation=f"Only {X}% of repeat customers have a stored card, despite averaging {X} {unit}s each — most re-enter payment every visit.",
        reasoning=f"Card-on-file lowers checkout friction, cuts declines on repeat purchases, and enables one-tap reorder; low adoption taxes your best customers at every visit.",
        conclusion=f"Prompt card-on-file enrollment at the {X} {unit} for repeat customers, tied to a one-tap reorder/loyalty perk.",
        expected_effect=f"Lifting card-on-file adoption speeds repeat checkout and lifts repeat frequency — ~${X}/mo.",
        recommend_when={"state": "low_card_on_file", "min_signal": "card_on_file"},
        tags=("payments", "card_on_file", "retention", v.family),
    )


def _recurring_billing_not_offered(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"You bill {v.sale_unit} plans one-time instead of on autopay",
        observation=f"{X}% of {v.sale_unit} renewals are manual/one-time charges rather than autopay, and manual renewals lapse at {X}% vs {X}% for autopay — visible in your {v.core_kpis[0]}.",
        reasoning=f"Every manual renewal is a re-decision point where {v.family} members leak away; autopay converts an active choice-to-stay into a passive default, the single biggest retention lever for {v.sale_unit}-based plans.",
        conclusion=f"Move renewals to opt-out autopay with a pre-charge reminder, defaulting new members to recurring at signup.",
        expected_effect=f"Shifting renewals to autopay lifts retention worth ~${X}/mo in preserved {v.sale_unit} revenue.",
        recommend_when={"state": "autopay_not_offered", "min_signal": "recurring_billing"},
        tags=("payments", "recurring", "retention", v.family),
    )


# ── gateway / checkout / settlement (universal) ──────────────────────────
def _auth_decline_rate(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Card declines are costing you completed {unit}s",
        observation=f"{X}% of card authorizations decline, and {X}% of declined {unit}s are abandoned rather than retried with another tender.",
        reasoning=f"A declined auth at the moment of purchase is a lost sale you already earned the demand for; soft declines (AVS, limit, network) are often recoverable with a retry or fallback prompt.",
        conclusion=f"Add a one-tap retry / alternate-tender prompt on decline and review the dominant decline codes for fixable causes (AVS rules, retry timing).",
        expected_effect=f"Recovering abandoned declines is worth ~${X}/mo in otherwise-lost {unit}s.",
        recommend_when={"state": "high_decline_rate", "min_signal": "auth_logs"},
        tags=("payments", "declines", v.family),
    )


def _prepay_preorder_conversion(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Prepay/preorder is offered but underused",
        observation=f"Only {X}% of eligible {unit}s use prepay/preorder, though prepaid {unit}s show {X}% lower no-show/abandon and {X}% higher attach.",
        reasoning=f"Prepayment locks the sale, smooths prep/capacity, and lifts attach because the spend decision is made up front; low adoption leaves that certainty and uplift on the table.",
        conclusion=f"Default the {X} channel to prepay (with pay-at-pickup as the opt-out) and add a small prepay incentive for repeat customers.",
        expected_effect=f"Shifting demand to prepay lifts certainty and attach — ~${X}/mo.",
        recommend_when={"state": "prepay_underused", "min_signal": "transactions"},
        tags=("payments", "prepay", v.family),
    )


def _split_payment_friction(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Group bills are split by hand and slow your turns",
        observation=f"{X}% of {unit}s involve a manual bill split that adds ~{X} min at the {v.staff_role} and produces {X}% of your tender errors.",
        reasoning=f"Manual splitting ties up the {v.staff_role} at the highest-leverage moment (table turn / line), and the errors it creates feed refunds and reconciliation work downstream.",
        conclusion=f"Enable item-level and even-split at the terminal plus QR pay-your-share, so groups settle without {v.staff_role} keying.",
        expected_effect=f"Faster splits free {X} {v.staff_role}-min/shift at peak and cut tender errors — ~${X}/mo.",
        recommend_when={"state": "split_payment_friction", "min_signal": "transactions"},
        tags=("payments", "checkout", v.family),
    )


def _settlement_timing(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your {unit} card batches settle slower than they need to",
        observation=f"Card batches close after the cutoff on {X}% of days on a {X}-day funding lag, delaying ${X} of daily {unit} volume into the next deposit.",
        reasoning=f"For a {v.family} business living on {v.core_kpis[0]}, settlement timing is free working capital: a later batch cutoff or faster funding plan moves earned {unit} revenue into your account sooner without changing a single sale.",
        conclusion=f"Move the batch cutoff before the processor's deadline and evaluate next-day/instant funding for the {X}% of {unit} volume that currently slips a day.",
        expected_effect=f"Tightening settlement frees ~${X} of working capital and steadies daily cash.",
        recommend_when={"state": "slow_settlement", "min_signal": "payouts"},
        tags=("payments", "settlement", "cashflow", v.family),
    )


register(
    # ── tender mix & processing cost (universal) ──
    Archetype(
        key="payment_mix_cost", domain="payments", name="Expensive tender mix",
        build=_payment_mix_cost, situations=("baseline",),
        required_signals=("tender_type", "transactions"),
        required_agents=("PaymentAnalyzer", "FeeAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="FeeScheduleAgent: tender type is on the transaction, but quantifying blended cost needs the per-tender fee schedule (interchange/markup); fee schedule is not ingested today.",
    ),
    Archetype(
        key="processing_fee_load", domain="payments", name="High processing-fee load",
        build=_processing_fee_load, situations=("baseline",),
        required_signals=("processor_fees", "transactions"),
        required_agents=("FeeAnalyzer", "PaymentAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ProcessorStatementAgent: ingest monthly processor statements (fees, downgrades, effective rate) to compute fee-as-%-of-revenue and benchmark it; statements are not ingested today.",
    ),
    Archetype(
        key="surcharge_opportunity", domain="payments", name="Surcharge opportunity",
        build=_surcharge_opportunity, situations=("baseline",),
        required_signals=("tender_type", "transactions"),
        required_agents=("PaymentAnalyzer", "FeeAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="FeeScheduleAgent (shared): card-paid share is known from tender_type; sizing the recoverable amount needs the fee schedule, and the recommendation must be gated by jurisdiction rules.",
    ),
    Archetype(
        key="small_ticket_card_fee", domain="payments", name="Small-ticket fee drag",
        build=_small_ticket_card_fee, situations=("baseline",),
        required_signals=("tender_type", "transactions"),
        required_agents=("FeeAnalyzer", "PaymentAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="FeeScheduleAgent (shared): ticket-size distribution by tender is derivable; isolating the flat-fee component needs the per-transaction fixed fee from the fee schedule.",
    ),
    # ── tipping (tipped only) ──
    Archetype(
        key="tip_rate_below_benchmark", domain="payments", name="Tip rate below benchmark",
        build=_tip_rate_below_benchmark, situations=("baseline", "declining"),
        required_signals=("tips", "transactions"),
        required_agents=("TipAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="TipBenchmarkAgent: tip amounts are on the transaction, but a vertical/size benchmark to compare against is not yet maintained — add a benchmark source.",
        applies_flags=("tipped",),
    ),
    Archetype(
        key="tip_screen_default", domain="payments", name="Tip prompt misconfigured",
        build=_tip_screen_default, situations=("baseline",),
        required_signals=("terminal_config", "tips"),
        required_agents=("TipAnalyzer",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="TerminalConfigAgent: read terminal tip-prompt settings (suggested %s, ordering, timing) to tie low tip rate to configuration; terminal config is not ingested today.",
        applies_flags=("tipped",),
    ),
    Archetype(
        key="tip_by_shift_variance", domain="payments", name="Tip variance by shift",
        build=_tip_by_shift_variance, situations=("baseline",),
        required_signals=("tips", "schedule_shifts"),
        required_agents=("TipAnalyzer", "StaffingAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="TipAttributionAgent: attributing tips to the working staff/shift needs employee_id on the transaction or a shift-overlap join (same gap as labor StaffAttribution).",
        applies_flags=("tipped",),
    ),
    Archetype(
        key="tip_cash_vs_card_gap", domain="payments", name="Cash vs card tip gap",
        build=_tip_cash_vs_card_gap, situations=("baseline",),
        required_signals=("tips", "tender_type"),
        required_agents=("TipAnalyzer", "ReconciliationAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashTipAgent: card tips are captured, but cash tips depend on declared/recorded amounts not reliably ingested — add a cash-tip declaration source for reconciliation.",
        applies_flags=("tipped",),
    ),
    # ── disputes / refunds / cash (universal) ──
    Archetype(
        key="chargeback_cluster", domain="payments", name="Chargeback cluster",
        build=_chargeback_cluster, situations=("baseline", "concentrated", "anomaly"),
        required_signals=("disputes", "transactions"),
        required_agents=("DisputeAuditor", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="DisputeFeedAgent: ingest the processor dispute/chargeback feed (reason codes, status, fees) to detect clusters; the dispute feed is not ingested today.",
    ),
    Archetype(
        key="refund_rate_by_channel", domain="payments", name="Refund rate by channel",
        build=_refund_rate_by_channel, situations=("baseline",),
        required_signals=("refunds", "transactions"),
        required_agents=("PaymentAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.FULL,
    ),
    Archetype(
        key="cash_vs_card_discrepancy", domain="payments", name="Cash discrepancy",
        build=_cash_vs_card_discrepancy, situations=("baseline",),
        required_signals=("cash_drawer", "transactions"),
        required_agents=("ReconciliationAgent", "PaymentAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CashDrawerAgent: reconcile counted cash to expected from drawer-count / close-out events; drawer counts are not ingested today.",
    ),
    # ── deposits / no-shows / tabs (structural) ──
    Archetype(
        key="deposit_capture_gap", domain="payments", name="Deposit capture gap",
        build=_deposit_capture_gap, situations=("baseline",),
        required_signals=("bookings", "deposits"),
        required_agents=("BookingAgent", "PaymentAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="DepositLinkAgent: bookings and ticket value are available, but linking which bookings carry a deposit needs the deposit/card-on-file field joined to the booking.",
        applies_flags=("appointment_based",),
        applies_keys=("jewelry",),
    ),
    Archetype(
        key="no_show_fee_uncaptured", domain="payments", name="No-show fee uncaptured",
        build=_no_show_fee_uncaptured, situations=("baseline",),
        required_signals=("bookings",),
        required_agents=("BookingAgent", "PaymentAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="NoShowAgent: requires booking outcome status (kept/no-show/cancelled) and whether a fee was charged; no-show status is not reliably ingested today.",
        applies_flags=("appointment_based",),
    ),
    Archetype(
        key="open_tab_leakage", domain="payments", name="Open-tab leakage",
        build=_open_tab_leakage, situations=("baseline",),
        required_signals=("tab_events", "transactions"),
        required_agents=("PaymentAnalyzer", "ReconciliationAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="TabLifecycleAgent: ingest open/void/force-close tab events to quantify walked tabs; tab lifecycle events are not captured today.",
        applies_flags=("table_service",),
    ),
    # ── receivables / recurring (structural) ──
    Archetype(
        key="ar_invoice_aging", domain="payments", name="AR / invoice aging",
        build=_ar_invoice_aging, situations=("baseline",),
        required_signals=("invoices",),
        required_agents=("ARAgent", "PaymentAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="InvoiceFeedAgent: ingest invoices with issue/due dates and payment status to compute AR aging buckets; the invoice/AR feed is not ingested today.",
        applies_families=("home_services",),
        applies_keys=("event_venue",),
    ),
    Archetype(
        key="failed_recurring_payment", domain="payments", name="Failed recurring churn",
        build=_failed_recurring_payment, situations=("baseline",),
        required_signals=("recurring_billing",),
        required_agents=("RecurringBillingAgent", "PaymentAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="RecurringBillingAgent: ingest recurring-charge attempts, failures, retries, and lapse outcomes to size involuntary churn; recurring billing events are not ingested today.",
        applies_flags=("membership",),
    ),
    Archetype(
        key="card_on_file_adoption", domain="payments", name="Low card-on-file adoption",
        build=_card_on_file_adoption, situations=("baseline",),
        required_signals=("card_on_file", "transactions"),
        required_agents=("PaymentAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="CardOnFileAgent: requires a stored-card flag per customer joined to repeat-purchase history; card-on-file status is not ingested today.",
        applies_flags=("repeat_purchase",),
    ),
    Archetype(
        key="recurring_billing_not_offered", domain="payments", name="Autopay not offered",
        build=_recurring_billing_not_offered, situations=("baseline",),
        required_signals=("recurring_billing",),
        required_agents=("RecurringBillingAgent", "PaymentAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="RecurringBillingAgent (shared): distinguishing manual vs autopay renewals and their lapse rates needs renewal-method data not ingested today.",
        applies_flags=("membership",),
    ),
    # ── gateway / checkout / settlement (universal) ──
    Archetype(
        key="auth_decline_rate", domain="payments", name="High decline rate",
        build=_auth_decline_rate, situations=("baseline",),
        required_signals=("auth_logs", "transactions"),
        required_agents=("PaymentAnalyzer", "FeeAnalyzer"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="GatewayLogAgent: ingest authorization attempts incl. declines and codes (only settled transactions are visible today) to measure decline rate and recovery.",
    ),
    Archetype(
        key="prepay_preorder_conversion", domain="payments", name="Prepay underused",
        build=_prepay_preorder_conversion, situations=("baseline",),
        required_signals=("transactions",),
        required_agents=("PaymentAnalyzer", "RevenueAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PrepayAgent: prepay vs pay-later is inferable from order/payment timing, but a clean prepay flag and no-show linkage would make the lift quantification reliable.",
    ),
    Archetype(
        key="split_payment_friction", domain="payments", name="Split-payment friction",
        build=_split_payment_friction, situations=("baseline",),
        required_signals=("transactions",),
        required_agents=("PaymentAnalyzer", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="SplitTenderAgent: multi-tender per check is detectable from transactions; quantifying added service time needs a timing/turn signal to confirm the peak cost.",
        applies_flags=("table_service",),
    ),
    Archetype(
        key="settlement_timing", domain="payments", name="Slow settlement",
        build=_settlement_timing, situations=("baseline",),
        required_signals=("payouts", "transactions"),
        required_agents=("PaymentAnalyzer", "ReconciliationAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="PayoutFeedAgent: ingest batch/settlement and payout timing to detect funding lag and cutoff misses; the payout feed is not ingested today.",
    ),
)
