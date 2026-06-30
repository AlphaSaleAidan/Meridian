"""
Domain: RISK / LOSS PREVENTION.

Each archetype is a distinct reasoning pattern about anomalies, leakage, fraud,
and compliance exposure. Specialization per vertical changes the loss mechanism
and the lever (post-tender voids for cash-heavy counters; reopened checks for
table service; age-verification logs for regulated retail; uncollected deposits
for high-ticket appointment work), so a cafe risk insight and a med-spa risk
insight are genuinely different reasoning, not a relabel.

Most of these need transaction-DETAIL signals (line items, tender type, void/
refund events) and per-EMPLOYEE attribution that the current swarm does not
ingest. Those are marked MISSING/PARTIAL with a concrete upgrade spec for a
LossPreventionAgent / AnomalyLedgerAgent / ComplianceCalendarAgent.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical
from .base import Archetype, Built, X, register


# ── Anomaly / leakage at the register ────────────────────────────────────
def _void_spike(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    unit = v.sale_unit
    extra = {
        "anomaly": " This is a sudden break from the prior {x}-week void rate — open it as an investigation, not a coaching note.".replace("{x}", X),
    }.get(situation, "")
    return Built(
        title=f"Void rate jumped to {X}% — {X}x your normal {unit} void baseline",
        observation=f"Voids ran {X}% of {unit}s over the last {X} days against a {X}% trailing baseline, clustered in the {X} window.",
        reasoning=f"Post-tender voids are the classic skim path: a {role} rings the {unit}, pockets the cash, then voids it so the drawer still balances. A rising void % while {v.core_kpis[0]} holds flat is a leakage signal, not a demand one.{extra}",
        conclusion=f"Pull the void log for the {X} window, require manager sign-off on any void over ${X}, and review the {X} {role}(s) driving the spike.",
        expected_effect=f"Closing a {X}% void leak protects ~${X}/mo that is otherwise leaving as untraceable cash.",
        recommend_when={"state": "void_rate_elevated", "min_signal": "void_events"},
        tags=("risk", "voids", "leakage", v.family),
    )


def _refund_rate_anomaly(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "anomaly": " The break is abrupt rather than a slow drift — check it before approving any further refunds.",
    }.get(situation, "")
    return Built(
        title=f"Refund rate at {X}% of {unit} value — {X}% above your norm",
        observation=f"Refunds totaled ${X} ({X}% of revenue) over {X} days vs a typical {X}%, with {X}% issued to original tender.",
        reasoning=f"Unlike a void, a refund moves money back out the door, so an elevated refund rate is real cash erosion — and refunds keyed to cash (not the card that paid) are a textbook diversion pattern distinct from genuine {unit} returns.{extra}",
        conclusion=f"Reconcile each refund over ${X} to its original tender, and flag any refund issued to a tender that differs from the sale.",
        expected_effect=f"Reining the rate back to baseline recovers ~${X}/mo of leaked cash.",
        recommend_when={"state": "refund_rate_elevated", "min_signal": "refund_events"},
        tags=("risk", "refunds", "leakage", v.family),
    )


def _discount_comp_abuse(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    unit = v.sale_unit
    return Built(
        title=f"Comps/discounts are {X}% of revenue — {X}% above category norm",
        observation=f"Manual comps and discounts removed ${X} from {X} {unit}s last month, {X}% of which came from {X} {role}(s).",
        reasoning=f"Comps are margin given away at the {role}'s discretion; when they cluster on specific {role}s or repeat customers they stop being goodwill and become an off-book price — the favored customer pays the {role}, not the till.",
        conclusion=f"Cap discretionary comps at ${X}/shift without approval and review the top-{X} comp issuers against repeat-recipient names.",
        expected_effect=f"Reclaiming abused comps recovers ~${X}/mo of margin currently given away.",
        recommend_when={"state": "comp_abuse_suspected", "min_signal": "discount_events"},
        tags=("risk", "discounts", "margin", v.family),
    )


def _no_sale_drawer_opens(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    return Built(
        title=f"No-sale drawer opens running {X}/day — {X}% tied to one {role}",
        observation=f"The drawer opened {X} times with no {v.sale_unit} attached last month, {X}% of them during the {X} window.",
        reasoning=f"A no-sale opens the till without a transaction — fine for making change, but a frequent, employee-concentrated pattern is the access half of a skim (open drawer, remove cash, no record), which is why it matters even with no {v.sale_unit} voided.",
        conclusion=f"Require a reason code on every no-sale and review the {X} {role}(s) whose no-sale count exceeds {X}/shift.",
        expected_effect=f"Tightening no-sale access removes an unmonitored cash window worth ~${X}/mo of exposure.",
        recommend_when={"state": "no_sale_frequency_high", "min_signal": "drawer_events"},
        tags=("risk", "cash_handling", v.family),
    )


def _after_hours_transactions(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "anomaly": " These appeared suddenly this period — verify them before the close is reconciled.",
    }.get(situation, "")
    return Built(
        title=f"{X} {unit}s rang up outside your open hours",
        observation=f"{X} transactions posted between {X} and {X} — before open or after close — totaling ${X} last month.",
        reasoning=f"Sales keyed when the doors are shut can't be real walk-in {unit}s; they're typically test rings, refund manipulation, or cleanup entries — each a sign the till is being touched off-clock with no customer present.{extra}",
        conclusion=f"Match every out-of-hours transaction to a logged reason (online order, prep) and flag the rest for the {v.staff_role} on record.",
        expected_effect=f"Surfacing off-hours activity closes a blind spot covering ~${X}/mo of unverifiable transactions.",
        recommend_when={"state": "after_hours_activity", "min_signal": "transactions"},
        tags=("risk", "anomaly", "after_hours", v.family),
    )


def _cash_variance(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Drawer counts off by ${X}+ on {X}% of shifts",
        observation=f"Cash variance exceeded ${X} on {X} of the last {X} closes, skewing {X} (short, not over).",
        reasoning=f"Random error swings both ways; a persistent SHORT bias is the fingerprint of skimming or miskeyed tender, because honest mistakes net toward zero over weeks while theft only ever runs one direction.",
        conclusion=f"Move to blind drawer counts, assign one {v.staff_role} per drawer per shift, and investigate any close short by more than ${X}.",
        expected_effect=f"Eliminating the short bias recovers ~${X}/mo and restores a trustworthy close.",
        recommend_when={"state": "cash_variance_biased", "min_signal": "drawer_counts"},
        tags=("risk", "cash_handling", "leakage", v.family),
    )


def _manual_price_override(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    unit = v.sale_unit
    return Built(
        title=f"Manual price overrides clustered on {X} {role}(s)",
        observation=f"{X} {unit}s were rung with a hand-keyed price instead of the catalog price last month, {X}% from the same {X} {role}(s).",
        reasoning=f"An override bypasses the priced catalog entirely, so it defeats every downstream margin and inventory control — clustered overrides mean a {role} is choosing the price the customer pays, which is where underring and friend-pricing live.",
        conclusion=f"Lock price entry to the catalog, require approval for any override beyond ${X}, and audit the override-heavy {role}(s).",
        expected_effect=f"Restoring catalog pricing recovers ~${X}/mo of margin lost to off-catalog rings.",
        recommend_when={"state": "override_cluster", "min_signal": "override_events"},
        tags=("risk", "pricing", "margin", v.family),
    )


def _single_employee_void_concentration(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    unit = v.sale_unit
    extra = {
        "concentrated": " The concentration itself is the finding — one node carries the whole risk, so a single conversation can close it.",
    }.get(situation, "")
    return Built(
        title=f"One {role} owns {X}% of all voids",
        observation=f"Across {X} {role}s, a single {role} accounts for {X}% of voids and {X}% of void dollars — {X}x the peer average.",
        reasoning=f"Voids spread across staff are noise; voids concentrated on one {role} are signal, because the same hand ringing and voiding {unit}s is exactly the loop a skim needs — peer-normalizing isolates the one node worth investigating.{extra}",
        conclusion=f"Shadow the flagged {role}'s voids for {X} shifts and require a second signature on their voids over ${X}.",
        expected_effect=f"Resolving one concentrated source addresses ~${X}/mo of void exposure in a single action.",
        recommend_when={"state": "void_concentration", "min_signal": "void_events"},
        tags=("risk", "voids", "attribution", v.family),
    )


def _duplicate_transaction(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "anomaly": " The cluster appeared this period and breaks the prior pattern — likely a terminal/config fault to fix now.",
    }.get(situation, "")
    return Built(
        title=f"{X} duplicate {unit} charges detected",
        observation=f"{X} near-identical transactions (same amount, terminal, within {X} seconds) posted last month, totaling ${X}.",
        reasoning=f"Duplicates are a two-sided risk: they either double-charge customers (chargeback and trust cost) or are a refund-skim setup (charge twice, refund one to a different tender) — distinct from a refund anomaly because the harm starts at capture, not return.{extra}",
        conclusion=f"Auto-flag same-amount same-terminal rings inside {X} seconds for review before settlement.",
        expected_effect=f"Catching duplicates pre-settlement avoids ~${X}/mo in refunds, chargebacks, and goodwill cost.",
        recommend_when={"state": "duplicate_charges", "min_signal": "transactions"},
        tags=("risk", "anomaly", "chargeback", v.family),
    )


def _gift_card_fraud(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Gift-card pattern looks manipulated — {X} suspect loads",
        observation=f"{X} gift cards were loaded then drained within {X} hours, and {X}% of redemptions trace to {X} card(s).",
        reasoning=f"Gift cards are stored value, so a load-and-drain loop or self-redemption converts {v.sale_unit} credit into cash or product with no customer — a leakage path that never touches the void or refund logs you'd normally watch.",
        conclusion=f"Cap single-load value at ${X}, require ID for loads over ${X}, and review cards with load-and-drain timing.",
        expected_effect=f"Closing the gift-card loop protects ~${X}/mo of stored value from diversion.",
        recommend_when={"state": "giftcard_anomaly", "min_signal": "giftcard_ledger"},
        tags=("risk", "gift_card", "leakage", v.family),
    )


def _tip_adjustment_anomaly(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    return Built(
        title=f"Tip adjustments inflated on {X}% of {role} checks",
        observation=f"{X} closed {v.sale_unit}s had tips adjusted upward after the customer left, averaging +${X}, concentrated on {X} {role}(s).",
        reasoning=f"A post-authorization tip bump is legitimate for a forgotten amount but a fraud channel when systematic: the {role} edits the tip on a low- or no-tip card, taking funds the customer never authorized — unique to tipped service and invisible to void/refund monitoring.",
        conclusion=f"Lock tip edits to within {X}% of the slip and flag any upward adjustment over ${X} for the {role} on record.",
        expected_effect=f"Stopping unauthorized adjustments removes ~${X}/mo of chargeback and trust exposure.",
        recommend_when={"state": "tip_adjustment_anomaly", "min_signal": "tip_adjustments"},
        tags=("risk", "tips", "chargeback", v.family),
    )


def _sales_tax_mismatch(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Collected sales tax doesn't reconcile — ${X} gap",
        observation=f"Tax collected was {X}% of taxable {unit} sales vs the expected {X}% rate, a ${X} discrepancy over {X} months.",
        reasoning=f"A tax-rate mismatch isn't theft but a compliance liability: under-collection means you owe the difference at filing (a cash surprise), over-collection is a customer-refund and audit risk — either way the ledger is wrong before it reaches your accountant.",
        conclusion=f"Audit taxable vs non-taxable {unit} categories in the catalog and correct any item rung at the wrong rate.",
        expected_effect=f"Fixing the rate avoids a ~${X} filing true-up and the penalty exposure that rides with it.",
        recommend_when={"state": "tax_reconciliation_gap", "min_signal": "tax_ledger"},
        tags=("risk", "compliance", "tax", v.family),
    )


# ── Compliance (regulated) ───────────────────────────────────────────────
def _license_compliance_expiry(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"A required license/permit expires in {X} days",
        observation=f"{X} of your operating credentials renew within {X} days, and {X} has no renewal on file.",
        reasoning=f"As a regulated {v.family.replace('_', ' ')} operator, an expired license isn't a paperwork lapse — it's a stop-work and fine event: lapsed authority can shutter the {v.sale_unit} line entirely, so the cost of missing the date dwarfs the renewal fee.",
        conclusion=f"Renew the {X} credential now and set a {X}-day advance reminder on every regulated license you hold.",
        expected_effect=f"Avoiding a lapse protects ${X}/day of revenue at risk during any forced closure.",
        recommend_when={"state": "license_expiring", "min_signal": "compliance_calendar"},
        tags=("risk", "compliance", "regulated", v.family),
    )


def _age_verification_gap(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Age-verification logged on only {X}% of restricted {unit}s",
        observation=f"Of {X} age-restricted {unit}s last month, only {X}% carry an ID-check record, with gaps clustered in the {X} window.",
        reasoning=f"Selling age-restricted product without a verifiable ID check exposes you to fines and license loss on a single failed compliance check or sting — for a regulated retailer the missing LOG is the liability even when the {v.staff_role} did check, because you can't prove it.",
        conclusion=f"Make the ID-check prompt a hard block on every restricted {unit} and audit the {X} {v.staff_role}(s) with the lowest capture rate.",
        expected_effect=f"Full verification coverage removes a per-incident fine of up to ${X} plus license-suspension risk.",
        recommend_when={"state": "age_verification_gap", "min_signal": "age_verification_log"},
        tags=("risk", "compliance", "age_restricted", "regulated", v.family),
    )


def _safety_health_flag(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"A data-driven safety/health signal needs review",
        observation=f"{X} incident/exception events were logged over {X} weeks ({X} above the prior period), concentrated in the {X} area of operations.",
        reasoning=f"In a {v.family.replace('_', ' ')} setting a rising exception count (temperature excursions, sanitation misses, near-misses) is a leading indicator of a health-code or liability event — catching the trend pre-incident is far cheaper than the closure or claim it predicts.",
        conclusion=f"Audit the flagged {X} events, retrain the {v.staff_role}(s) involved, and set a threshold alert at {X} events/week.",
        expected_effect=f"Acting on the leading signal avoids a single closure/claim event worth ${X}+ in lost days and remediation.",
        recommend_when={"state": "safety_exception_trend", "min_signal": "incident_log"},
        tags=("risk", "compliance", "safety", v.family),
    )


# ── Card-not-present & receivables risk ──────────────────────────────────
def _chargeback_spike(v: Vertical, situation: str) -> Built:
    extra = {
        "anomaly": " The jump is sudden, so a single bad batch or terminal is the likely cause — isolate it before it compounds.",
    }.get(situation, "")
    return Built(
        title=f"Chargebacks at {X}% of volume — past the {X}% risk line",
        observation=f"{X} chargebacks worth ${X} hit last month, {X}% of them from {' / '.join(v.channels[:2])} {v.sale_unit}s.",
        reasoning=f"Chargebacks cost twice — the lost sale plus the dispute fee — and crossing the processor's threshold triggers reserves or account termination, so a rising rate on your card-not-present {v.sale_unit}s threatens the ability to take cards at all.{extra}",
        conclusion=f"Add CVV/AVS checks on {' / '.join(v.channels[:2])} orders and contest the {X} disputes still inside the response window.",
        expected_effect=f"Pulling the rate back under {X}% avoids ~${X}/mo in fees and removes the account-reserve threat.",
        recommend_when={"state": "chargeback_elevated", "min_signal": "chargeback_events"},
        tags=("risk", "chargeback", "card_not_present", v.family),
    )


def _deposit_not_collected(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"{X}% of high-value {unit}s booked with no deposit",
        observation=f"{X} of your ${X}+ {unit}s were scheduled without the deposit your policy requires, exposing ${X} in held capacity.",
        reasoning=f"For high-ticket appointment work the deposit IS the no-show insurance: an uncollected deposit means a cancelled {unit} leaves you with paid {v.staff_role} time and a held slot you can't refill — a loss-prevention gap, not just a cashflow timing one.",
        conclusion=f"Make the deposit a hard requirement to confirm any {unit} over ${X}, charged at booking.",
        expected_effect=f"Enforcing deposits recovers ~${X}/mo otherwise lost to unprotected high-value no-shows.",
        recommend_when={"state": "deposit_not_enforced", "min_signal": "deposit_ledger"},
        tags=("risk", "deposits", "no_show", v.family),
    )


def _unusual_discount_high_value(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    unit = v.sale_unit
    return Built(
        title=f"Outsized discounts landing on your highest-value {unit}s",
        observation=f"Discounts over {X}% appeared on {X} {unit}s above ${X} last month — {X}% issued by the same {X} {role}(s).",
        reasoning=f"A big percentage off a small ticket is minor; the same percentage off a high-ticket {unit} is where real margin walks out, so discount abuse concentrates on big tickets by design — the dollar leakage scales with ticket size even at the same discount rate.",
        conclusion=f"Require approval for any discount over {X}% on {unit}s above ${X} and review the {role}(s) issuing them.",
        expected_effect=f"Gating high-ticket discounts recovers ~${X}/mo of margin currently discretionary.",
        recommend_when={"state": "high_value_discount_abuse", "min_signal": "discount_events"},
        tags=("risk", "discounts", "high_ticket", v.family),
    )


def _refund_after_close(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = {
        "anomaly": " It started this period and breaks the prior pattern — review before the next reconciliation.",
    }.get(situation, "")
    return Built(
        title=f"{X} refunds processed after close, with no customer present",
        observation=f"{X} refunds totaling ${X} were keyed between {X} and {X} — after the last {unit} of the day — over {X} weeks.",
        reasoning=f"A refund needs a returning customer; one keyed after close has none, making it the cleanest skim form (refund an old card or to cash with the floor empty) — distinct from the refund-rate anomaly because the TIMING, not the volume, is the tell.{extra}",
        conclusion=f"Block refunds outside open hours without a manager PIN and reconcile the {X} after-close refunds already on the books.",
        expected_effect=f"Closing the after-close refund window protects ~${X}/mo of unverifiable outflow.",
        recommend_when={"state": "after_close_refunds", "min_signal": "refund_events"},
        tags=("risk", "refunds", "after_hours", v.family),
    )


def _negative_inventory_adjustment(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Unexplained negative inventory adjustments — ${X} shrink",
        observation=f"{X} downward stock adjustments removed ${X} of inventory outside of sales last month, {X}% logged with no reason code.",
        reasoning=f"For an inventory-heavy {v.family.replace('_', ' ')} operator, manual write-downs are the cover story for product theft: shrink booked as 'damage' or 'count fix' hides {v.sale_unit}s that walked out — reason-code-less adjustments are the ones worth chasing because legitimate waste is documented.",
        conclusion=f"Require a reason code and a second approver on adjustments over ${X}, and reconcile the unexplained {X} against cycle counts.",
        expected_effect=f"Tightening adjustment controls recovers ~${X}/mo of inventory shrink now booked as 'loss'.",
        recommend_when={"state": "inventory_adjustment_anomaly", "min_signal": "inventory_adjustments"},
        tags=("risk", "shrinkage", "inventory", v.family),
    )


def _reopened_check_anomaly(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    return Built(
        title=f"Checks reopened after payment on {X}% of {role} tabs",
        observation=f"{X} {v.sale_unit}s were reopened and edited after being tendered last month, {X}% by the same {X} {role}(s).",
        reasoning=f"In table service a reopened check is the lever for the most common dine-in skim: close the tab to the customer's card, reopen it, drop an item, and keep the cash difference — a fraud unique to running tabs and invisible unless you watch post-payment edits.",
        conclusion=f"Lock checks at tender, require a manager PIN to reopen, and audit the {role}(s) with the most reopens.",
        expected_effect=f"Stopping post-payment edits recovers ~${X}/mo of skim hidden inside reopened tabs.",
        recommend_when={"state": "reopened_check_anomaly", "min_signal": "check_events"},
        tags=("risk", "table_service", "leakage", v.family),
    )


def _cash_mix_shift(v: Vertical, situation: str) -> Built:
    extra = {
        "anomaly": " The shift is abrupt, not seasonal — verify it against staffing changes before assuming it's customer behavior.",
    }.get(situation, "")
    return Built(
        title=f"Cash share of sales dropped {X} points unexplained",
        observation=f"Cash fell from {X}% to {X}% of {v.sale_unit} tender over {X} weeks with no change in customer mix or pricing.",
        reasoning=f"Card mix usually drifts slowly; a fast drop in REPORTED cash while card volume holds is the signature of cash sales never being rung — the money came in, the {v.sale_unit} never did, so the tender ledger under-counts cash that was actually collected.{extra}",
        conclusion=f"Compare reported cash to expected cash by daypart and audit shifts where the cash share falls below {X}%.",
        expected_effect=f"Recovering unrung cash sales protects ~${X}/mo that is currently invisible to the books.",
        recommend_when={"state": "cash_mix_shift", "min_signal": "tender_detail"},
        tags=("risk", "cash_handling", "anomaly", v.family),
    )


def _employee_discount_abuse(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    return Built(
        title=f"Employee-discount usage {X}x policy on {X} {role}(s)",
        observation=f"{X} {role}(s) applied the staff discount to {X} {v.sale_unit}s last month — {X}% on transactions with a paying customer present, not their own purchase.",
        reasoning=f"The employee discount is a benefit on the {role}'s OWN purchase; applied to a customer's {v.sale_unit} it becomes an unauthorized price cut the {role} can monetize (friend-pricing, or pocketing the difference) — distinct from generic comp abuse because it hides behind a legitimate discount code.",
        conclusion=f"Restrict the staff-discount code to transactions with no other customer and audit the top {X} users.",
        expected_effect=f"Closing the loophole recovers ~${X}/mo of margin given away under the staff code.",
        recommend_when={"state": "employee_discount_abuse", "min_signal": "discount_events"},
        tags=("risk", "discounts", "attribution", v.family),
    )


def _partial_refund_pattern(v: Vertical, situation: str) -> Built:
    role = v.staff_role
    return Built(
        title=f"Repeated small partial refunds — {X} below the review line",
        observation=f"{X} partial refunds averaging ${X} (all just under your ${X} review threshold) posted last month, {X}% from {X} {role}(s).",
        reasoning=f"Refunds sized deliberately below the approval threshold are structuring: many small returns stay invisible to any single-transaction check while summing to real loss — the PATTERN of just-under-limit amounts is the tell, not any one refund.",
        conclusion=f"Add a rolling per-{role} refund-count alert (not just per-transaction value) and review anyone over {X} partials/week.",
        expected_effect=f"Catching structured refunds recovers ~${X}/mo that slips beneath single-transaction controls.",
        recommend_when={"state": "structured_refunds", "min_signal": "refund_events"},
        tags=("risk", "refunds", "structuring", v.family),
    )


register(
    Archetype(
        key="void_spike", domain="risk", name="Void rate spike",
        build=_void_spike, situations=("baseline", "anomaly"),
        required_signals=("void_events", "transactions", "employee_id"),
        required_agents=("LossPreventionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LossPreventionAgent: ingest POS void events (item, amount, timestamp, employee_id) and compute trailing void-rate baselines per merchant/daypart. No transaction-detail or employee attribution is ingested today.",
    ),
    Archetype(
        key="refund_rate_anomaly", domain="risk", name="Refund rate anomaly",
        build=_refund_rate_anomaly, situations=("baseline", "anomaly"),
        required_signals=("refund_events", "transactions"),
        required_agents=("AnomalyLedgerAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="AnomalyLedgerAgent: ingest refund events with original-tender linkage so refunds keyed to a different tender than the sale can be flagged. Current swarm has aggregate revenue only.",
    ),
    Archetype(
        key="discount_comp_abuse", domain="risk", name="Comp/discount abuse",
        build=_discount_comp_abuse, situations=("baseline",),
        required_signals=("discount_events", "employee_id"),
        required_agents=("LossPreventionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LossPreventionAgent (shared): attribute comps/discounts to employee_id and recipient to surface concentration. Needs line-item discount data not currently ingested.",
    ),
    Archetype(
        key="no_sale_drawer_opens", domain="risk", name="No-sale drawer opens",
        build=_no_sale_drawer_opens, situations=("baseline",),
        applies_families=("retail", "food_service"),
        required_signals=("drawer_events", "employee_id"),
        required_agents=("LossPreventionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LossPreventionAgent: ingest drawer/no-sale events with employee attribution. POS hardware emits these but they are not collected.",
    ),
    Archetype(
        key="after_hours_transactions", domain="risk", name="After-hours transactions",
        build=_after_hours_transactions, situations=("baseline", "anomaly"),
        required_signals=("transactions",),
        required_agents=("AnomalyLedgerAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="AnomalyLedgerAgent: join transaction timestamps to the merchant's open-hours calendar to flag out-of-hours rings. Timestamps exist on transactions; the hours reference does not.",
    ),
    Archetype(
        key="cash_variance", domain="risk", name="Cash drawer variance bias",
        build=_cash_variance, situations=("baseline",),
        required_signals=("drawer_counts",),
        required_agents=("LossPreventionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LossPreventionAgent: ingest end-of-shift drawer counts vs expected cash to detect a directional (short) bias. No reconciliation data is captured today.",
    ),
    Archetype(
        key="manual_price_override", domain="risk", name="Manual price override cluster",
        build=_manual_price_override, situations=("baseline", "concentrated"),
        required_signals=("override_events", "employee_id"),
        required_agents=("LossPreventionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LossPreventionAgent: capture hand-keyed price overrides vs catalog price per employee. Requires line-item price-source flag not ingested.",
    ),
    Archetype(
        key="single_employee_void_concentration", domain="risk", name="Void concentration on one employee",
        build=_single_employee_void_concentration, situations=("baseline", "concentrated"),
        required_signals=("void_events", "employee_id"),
        required_agents=("AnomalyLedgerAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="AnomalyLedgerAgent: peer-normalize void rate by employee to isolate the single outlier node. Needs employee_id on void events (not ingested).",
    ),
    Archetype(
        key="duplicate_transaction", domain="risk", name="Duplicate transaction",
        build=_duplicate_transaction, situations=("baseline", "anomaly"),
        required_signals=("transactions",),
        required_agents=("AnomalyLedgerAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="AnomalyLedgerAgent: near-duplicate detection on (amount, terminal, time-delta). Transaction amounts/times exist but terminal id is not currently retained.",
    ),
    Archetype(
        key="gift_card_fraud", domain="risk", name="Gift-card fraud pattern",
        build=_gift_card_fraud, situations=("baseline",),
        applies_families=("retail", "food_service", "personal_care"),
        required_signals=("giftcard_ledger",),
        required_agents=("LossPreventionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LossPreventionAgent: ingest gift-card load/redeem events to detect load-and-drain timing and self-redemption. Stored-value ledger is not collected.",
    ),
    Archetype(
        key="tip_adjustment_anomaly", domain="risk", name="Tip adjustment anomaly",
        build=_tip_adjustment_anomaly, situations=("baseline",),
        applies_flags=("tipped",),
        required_signals=("tip_adjustments", "employee_id"),
        required_agents=("LossPreventionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LossPreventionAgent: capture post-authorization tip edits vs printed slip per employee. Tip-adjust events are not ingested.",
    ),
    Archetype(
        key="sales_tax_mismatch", domain="risk", name="Sales-tax reconciliation gap",
        build=_sales_tax_mismatch, situations=("baseline",),
        required_signals=("tax_ledger", "transactions"),
        required_agents=("ComplianceCalendarAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ComplianceCalendarAgent: reconcile collected tax vs taxable sales at the expected jurisdiction rate. Needs per-item taxable flag and jurisdiction rate table (neither ingested).",
    ),
    Archetype(
        key="license_compliance_expiry", domain="risk", name="License/permit expiry",
        build=_license_compliance_expiry, situations=("baseline",),
        applies_flags=("regulated",),
        required_signals=("compliance_calendar",),
        required_agents=("ComplianceCalendarAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ComplianceCalendarAgent: maintain a per-merchant credential registry (license type, expiry, renewal status) and emit advance-warning windows. No compliance calendar source exists.",
    ),
    Archetype(
        key="age_verification_gap", domain="risk", name="Age-verification gap",
        build=_age_verification_gap, situations=("baseline",),
        applies_keys=("liquor", "dispensary", "smoke_shop", "bar"),
        required_signals=("age_verification_log", "transactions", "employee_id"),
        required_agents=("ComplianceCalendarAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ComplianceCalendarAgent: ingest ID-check events and join to age-restricted SKUs to compute per-employee verification coverage. Verification logs are not captured.",
    ),
    Archetype(
        key="safety_health_flag", domain="risk", name="Safety/health exception trend",
        build=_safety_health_flag, situations=("baseline",),
        applies_families=("food_service", "health_wellness"),
        required_signals=("incident_log",),
        required_agents=("ComplianceCalendarAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ComplianceCalendarAgent: ingest incident/exception events (temp excursions, sanitation misses, near-misses) and trend them as leading indicators. No incident source is ingested.",
    ),
    Archetype(
        key="chargeback_spike", domain="risk", name="Chargeback spike",
        build=_chargeback_spike, situations=("baseline", "anomaly"),
        required_signals=("chargeback_events", "transactions"),
        required_agents=("AnomalyLedgerAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="AnomalyLedgerAgent: ingest processor dispute/chargeback feeds and compute rate vs the processor threshold by channel. Dispute data is not pulled from the gateway.",
    ),
    Archetype(
        key="deposit_not_collected", domain="risk", name="High-value deposit not collected",
        build=_deposit_not_collected, situations=("baseline",),
        applies_flags=("appointment_based", "high_ticket"),
        required_signals=("deposit_ledger", "transactions"),
        required_agents=("LossPreventionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LossPreventionAgent: join booking records to deposit charges to flag high-value appointments confirmed without the policy deposit. Deposit/booking linkage is not ingested.",
    ),
    Archetype(
        key="unusual_discount_high_value", domain="risk", name="Outsized discount on high-value sale",
        build=_unusual_discount_high_value, situations=("baseline",),
        applies_flags=("high_ticket",),
        required_signals=("discount_events", "transactions", "employee_id"),
        required_agents=("LossPreventionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LossPreventionAgent (shared): cross discount % against ticket value and employee to surface high-ticket discount abuse. Needs line-item discount + ticket value attribution.",
    ),
    Archetype(
        key="refund_after_close", domain="risk", name="Refund after close",
        build=_refund_after_close, situations=("baseline", "anomaly"),
        required_signals=("refund_events", "transactions"),
        required_agents=("AnomalyLedgerAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="AnomalyLedgerAgent: flag refunds timestamped outside open hours. Requires refund timestamps + open-hours reference (neither ingested).",
    ),
    Archetype(
        key="negative_inventory_adjustment", domain="risk", name="Negative inventory adjustment",
        build=_negative_inventory_adjustment, situations=("baseline",),
        applies_flags=("inventory_heavy",),
        required_signals=("inventory_adjustments", "employee_id"),
        required_agents=("LossPreventionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LossPreventionAgent: ingest manual stock adjustments (reason code, approver, value) and reconcile against cycle counts to separate documented waste from shrink. No inventory adjustment feed exists.",
    ),
    Archetype(
        key="reopened_check_anomaly", domain="risk", name="Reopened-check anomaly",
        build=_reopened_check_anomaly, situations=("baseline",),
        applies_flags=("table_service",),
        required_signals=("check_events", "employee_id"),
        required_agents=("LossPreventionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LossPreventionAgent: capture post-tender check reopen/edit events per server. Check lifecycle events are not ingested.",
    ),
    Archetype(
        key="cash_mix_shift", domain="risk", name="Cash tender-mix shift",
        build=_cash_mix_shift, situations=("baseline", "anomaly"),
        required_signals=("tender_detail", "transactions"),
        required_agents=("AnomalyLedgerAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="AnomalyLedgerAgent: track cash-vs-card tender share by daypart to detect unrung-cash signatures. Tender type is not retained on transactions today.",
    ),
    Archetype(
        key="employee_discount_abuse", domain="risk", name="Employee-discount abuse",
        build=_employee_discount_abuse, situations=("baseline",),
        required_signals=("discount_events", "employee_id"),
        required_agents=("LossPreventionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="LossPreventionAgent: detect staff-discount codes applied on customer-present transactions per employee. Needs discount-code + employee attribution not ingested.",
    ),
    Archetype(
        key="partial_refund_pattern", domain="risk", name="Structured partial refunds",
        build=_partial_refund_pattern, situations=("baseline",),
        required_signals=("refund_events", "employee_id"),
        required_agents=("AnomalyLedgerAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="AnomalyLedgerAgent: rolling per-employee refund-count + amount-distribution analysis to catch just-under-threshold structuring. Requires employee-attributed refund events.",
    ),
)
