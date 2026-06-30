"""
Domain: CHANNEL / SALES & ORDER CHANNELS.

Each archetype is a distinct reasoning pattern about HOW orders arrive — phone,
drive-thru, delivery, online, booking, walk-in, self-serve — and where each
channel leaks revenue or margin. Targeting is channel-aware: an archetype only
instantiates for verticals whose `v.channels` actually carries the relevant
channel (drive-thru archetypes hit QSR only; delivery archetypes hit
delivery-capable verticals; phone archetypes hit phone-channel verticals).

Signal provenance (rigorous):
  * Phone archetypes read phone_call_logs (status / duration_seconds / transcript)
    and phone_orders (pos_success) — partially live via the voice agent.
  * Delivery/online/channel-mix archetypes join order channels to transactions and
    need a margin/mix fusion agent.
  * Where the join doesn't exist yet, the archetype is MISSING and specs the
    PhonePOSFusionAgent / ChannelMarginAgent / ChannelMixAgent that must be built.
"""
from __future__ import annotations

from ..schema import SwarmCapability
from ..verticals import Vertical, VERTICALS
from .base import Archetype, Built, X, register


# ── Channel-aware targeting (fed into applies_keys) ─────────────────────────
def _ch(*channels: str) -> tuple[str, ...]:
    """Vertical keys whose channels include ANY of the given channels."""
    cs = set(channels)
    return tuple(v.key for v in VERTICALS if cs & set(v.channels))


def _ch_all(*channels: str) -> tuple[str, ...]:
    """Vertical keys whose channels include ALL of the given channels."""
    cs = set(channels)
    return tuple(v.key for v in VERTICALS if cs.issubset(set(v.channels)))


def _single_channel_keys() -> tuple[str, ...]:
    """Verticals that sell through exactly one channel (single-channel risk)."""
    return tuple(v.key for v in VERTICALS if len(v.channels) == 1)


# ═══════════════════════ PHONE ══════════════════════════════════════════════
def _missed_phone_calls(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = " The miss rate spikes during your busiest hours — exactly when calls are most likely to be a ready buyer." if situation == "concentrated" else ""
    return Built(
        title=f"You miss {X}% of inbound calls — and each is a lost {unit}",
        observation=f"phone_call_logs shows {X} inbound calls last period with status=missed/unanswered on {X}% of them.{extra}",
        reasoning=f"For a {v.name.lower()}, an inbound call is a high-intent customer ready to book or order; a missed call doesn't wait — it dials the next {v.name.lower()}, so the miss rate is a direct, recurring leak of pre-qualified {unit} demand.",
        conclusion=f"Route overflow to a callback queue or voice agent during the {X} highest-miss hours and confirm every missed number gets a same-day call back.",
        expected_effect=f"Recovering {X}% of {X} missed calls is worth ~${X}/mo at your average {unit} value.",
        recommend_when={"state": "missed_calls", "min_signal": "phone_call_logs"},
        tags=("channel", "phone", v.family),
    )


def _phone_order_conversion_low(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Answered calls rarely become {unit}s — {X}% conversion",
        observation=f"Of {X} answered calls, only {X}% reach phone_orders with pos_success=true; the rest end without an order.",
        reasoning=f"An answered call is already past the hardest step (intent + contact); a low call-to-{unit} rate means the handoff is failing — long holds, unsure {v.staff_role}s, or no clear path to close — so you pay to answer and still lose the {unit}.",
        conclusion=f"Script the top {X} call reasons to a confirmed order, and make sure the {v.staff_role} can complete payment/booking on the call without a transfer.",
        expected_effect=f"Lifting call-to-{unit} conversion by {X}pts is worth ~${X}/mo on existing answered volume.",
        recommend_when={"state": "phone_conversion_low", "min_signal": "phone_orders"},
        tags=("channel", "phone", "conversion", v.family),
    )


def _phone_hold_time(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Callers wait {X}s on hold before anyone answers",
        observation=f"Median time-to-answer in phone_call_logs is {X}s, and abandon rate climbs sharply past {X}s.",
        reasoning=f"Hold time is the single biggest controllable cause of phone abandonment: every extra few seconds before a human answers converts a ready {v.sale_unit} into a hang-up, and the caller blames the {v.name.lower()}, not the queue.",
        conclusion=f"Add coverage or an instant-answer voice agent so time-to-answer stays under {X}s during the {X} peak call hours.",
        expected_effect=f"Cutting hold time under the abandon threshold recovers ~${X}/mo of hung-up demand.",
        recommend_when={"state": "phone_hold_long", "min_signal": "phone_call_logs"},
        tags=("channel", "phone", v.family),
    )


def _call_abandon_at_peak(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Calls get abandoned exactly when you're busiest",
        observation=f"{X}% of call abandons cluster in the {X}–{X} window, which is also your highest {v.sale_unit} volume — staff are serving in-person and the phone rings out.",
        reasoning=f"Peak is when phone demand and in-person demand collide for the same {v.staff_role}; without a dedicated answer path the phone always loses to the customer at the counter, so your busiest hours silently shed your most valuable inbound calls.",
        conclusion=f"Decouple phone answering from the counter during peak — overflow to a callback queue or voice agent for the {X} busiest hours.",
        expected_effect=f"Catching peak-window abandons is worth ~${X}/mo in otherwise-lost {v.sale_unit}s.",
        recommend_when={"state": "call_abandon_peak", "min_signal": "phone_call_logs"},
        tags=("channel", "phone", "peak", v.family),
    )


def _voicemail_no_callback(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Voicemails pile up with no callback",
        observation=f"{X} calls hit voicemail last period; only {X}% received an outbound callback, and median callback lag is {X} hours.",
        reasoning=f"A voicemail is a warm lead that decays by the hour; for a {v.name.lower()} where the customer can easily choose a competitor, a slow or missing callback wastes intent you already captured — the lead was free, the loss is not.",
        conclusion=f"Assign voicemail callbacks to a named owner with a {X}-hour SLA and track callback rate as a channel KPI.",
        expected_effect=f"Closing the callback gap recovers ~${X}/mo from leads you already received.",
        recommend_when={"state": "voicemail_no_callback", "min_signal": "phone_call_logs"},
        tags=("channel", "phone", "followup", v.family),
    )


def _phone_upsell_gap(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Phone orders skip the upsell that in-person {unit}s get",
        observation=f"Transcript analysis shows an add-on/upsell is offered on only {X}% of phone {unit}s versus {X}% at the counter, and phone ticket runs {X}% lower.",
        reasoning=f"The phone strips away the visual menu and impulse cues that drive attach in person; without a scripted prompt the {v.staff_role} defaults to order-taking, so every phone {unit} quietly under-monetizes versus the same order placed in-store.",
        conclusion=f"Script a single best-attach prompt for the top {X} phone orders and have the voice agent/{v.staff_role} offer it every time.",
        expected_effect=f"Closing the phone-vs-counter attach gap lifts phone ticket ~{X}% — worth ~${X}/mo.",
        recommend_when={"state": "phone_upsell_gap", "min_signal": "phone_orders"},
        tags=("channel", "phone", "upsell", v.family),
    )


def _phone_agent_deflection(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Repetitive calls eat {v.staff_role} time that could be automated",
        observation=f"{X}% of inbound calls are routine (hours, status, simple {v.sale_unit}s) consuming ~{X} {v.staff_role}-minutes/day on calls that need no judgment.",
        reasoning=f"Every routine call answered by a {v.staff_role} is double-charged: you pay labor AND you pull that person off in-person {v.sale_unit}s; routine, scriptable calls are exactly what a voice agent handles without the service tradeoff.",
        conclusion=f"Deflect the top {X} routine call types to a voice agent and reserve {v.staff_role} answering for complex or high-value calls.",
        expected_effect=f"Automating routine calls frees ~{X} {v.staff_role}-hours/wk worth ~${X}/mo while protecting answer rate.",
        recommend_when={"state": "phone_deflectable", "min_signal": "phone_call_logs"},
        tags=("channel", "phone", "automation", v.family),
    )


def _phone_conversion_by_rep(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Some {v.staff_role}s close phone {unit}s far better than others",
        observation=f"Call-to-{unit} conversion ranges from {X}% to {X}% across {v.staff_role}s on similar call volume and mix.",
        reasoning=f"A wide per-{v.staff_role} conversion spread on comparable calls means the gap is skill/script, not luck; the top performer's phone approach is a free, in-house playbook the rest aren't using, so the spread is recoverable revenue.",
        conclusion=f"Capture the top {v.staff_role}'s call pattern, train the bottom {X} to it, and re-measure conversion after {X} weeks.",
        expected_effect=f"Pulling the low half toward the top quartile is worth ~${X}/mo in incremental phone {unit}s.",
        recommend_when={"state": "phone_conversion_spread", "min_signal": "phone_orders"},
        tags=("channel", "phone", "performance", v.family),
    )


# ═══════════════════════ DRIVE-THRU ═════════════════════════════════════════
def _drive_thru_time(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your drive-thru is too slow — {X}s over target",
        observation=f"Average drive-thru time runs {X}s versus a {X}s target, and the lane backs up during the {X} peak.",
        reasoning=f"Drive-thru is a throughput business: every extra second per car shrinks cars-per-hour at peak and, past a visible queue length, customers drive off entirely — so slow times cap both peak revenue and the willingness of the next car to even pull in.",
        conclusion=f"Attack the slowest station in the sequence (order/pay/present), pre-stage the top {X} items at peak, and re-time after the fix.",
        expected_effect=f"Cutting {X}s off peak service adds cars-per-hour worth ~${X}/mo.",
        recommend_when={"state": "drive_thru_slow", "min_signal": "drive_thru_timing"},
        tags=("channel", "drive_thru", "throughput", v.family),
    )


def _drive_thru_vs_lobby_mix(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your drive-thru and lobby are out of balance",
        observation=f"Drive-thru carries {X}% of {v.sale_unit}s but only {X}% of staff at peak, so the lane slows while the lobby sits idle (or the reverse).",
        reasoning=f"Drive-thru and lobby draw from one labor pool but have different speed economics; staffing them by headcount instead of by channel volume leaves the higher-throughput channel under-resourced and the slower one over-resourced at the same moment.",
        conclusion=f"Re-weight peak staffing to the channel mix — shift {X} crew to the lane during the {X} drive-thru peak.",
        expected_effect=f"Matching labor to channel mix at peak is worth ~${X}/mo in recovered throughput.",
        recommend_when={"state": "drive_thru_mix_imbalance", "min_signal": "drive_thru_timing"},
        tags=("channel", "drive_thru", "staffing", v.family),
    )


# ═══════════════════════ DELIVERY ═══════════════════════════════════════════
def _delivery_fee_erosion(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = " The eroded share is growing as delivery mix rises — the leak widens every month it's ignored." if situation == "leaking" else ""
    return Built(
        title=f"Third-party delivery fees are eating your margin",
        observation=f"Marketplace commissions take {X}% of each delivery {unit}, dropping delivery contribution to {X}% versus {X}% on a walk-in {unit}.{extra}",
        reasoning=f"Delivery volume can look like growth while quietly diluting blended margin: a {unit} that nets little after a 20-30% commission grows revenue and shrinks profit, so unmanaged platform mix can make a busier {v.name.lower()} less profitable.",
        conclusion=f"Set delivery-specific menu pricing to absorb the fee, steer repeat customers to first-party ordering, and drop money-losing items from the platform.",
        expected_effect=f"Repricing/steering delivery to a positive contribution recovers ~${X}/mo of margin.",
        recommend_when={"state": "delivery_fee_erosion", "min_signal": "delivery_orders"},
        tags=("channel", "delivery", "margin", v.family),
    )


def _channel_margin_mix(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your channels don't earn the same margin — and growth is in the worst one",
        observation=f"Walk-in {unit}s net {X}% margin, delivery {X}%, online {X}%; the fastest-growing channel is also the lowest-margin.",
        reasoning=f"Top-line channel growth is misleading when channels differ in contribution; shifting mix toward a low-margin channel can raise revenue while flattening profit, so the right question isn't 'which channel is growing' but 'which channel grows margin'.",
        conclusion=f"Rank channels by contribution, then steer marketing and promos toward the highest-margin channel and reprice the lowest.",
        expected_effect=f"Shifting {X}% of mix toward the high-margin channel is worth ~${X}/mo in blended margin.",
        recommend_when={"state": "channel_margin_mix", "min_signal": "transactions"},
        tags=("channel", "margin", "mix", v.family),
    )


def _delivery_radius_profitability(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Your far-edge delivery zone loses money",
        observation=f"Deliveries beyond {X} km take {X} min longer and, after driver time/fee, net negative on the average {v.sale_unit}.",
        reasoning=f"Delivery profitability falls with distance: time, fuel, and lateness-driven refunds rise while the {v.sale_unit} value doesn't, so an over-wide radius subsidizes distant orders with margin earned on close ones.",
        conclusion=f"Tighten the radius or add a distance-based minimum/surcharge beyond {X} km, and re-check contribution by zone.",
        expected_effect=f"Right-sizing the delivery zone protects ~${X}/mo and improves on-time rate.",
        recommend_when={"state": "delivery_radius_unprofitable", "min_signal": "delivery_orders"},
        tags=("channel", "delivery", "geo", v.family),
    )


def _delivery_platform_dependence(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"One delivery platform owns your delivery revenue",
        observation=f"{X}% of delivery {unit}s come through a single marketplace that controls the customer relationship and sets the {X}% commission.",
        reasoning=f"Concentration in one platform is a pricing-power risk: the marketplace owns the customer data and can raise commission or de-rank you at will, so an over-dependent {v.name.lower()} has no leverage and no direct path back to those customers.",
        conclusion=f"Diversify to a second platform AND build a first-party order channel, converting repeat marketplace customers with an in-bag incentive.",
        expected_effect=f"Reducing single-platform dependence de-risks ~${X}/mo and recovers margin on converted repeat orders.",
        recommend_when={"state": "delivery_platform_concentration", "min_signal": "delivery_orders"},
        tags=("channel", "delivery", "concentration", v.family),
    )


def _delivery_min_order(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Small delivery orders cost more to fulfill than they earn",
        observation=f"{X}% of delivery {unit}s fall below ${X}, where fixed pick/pack/drive cost exceeds the order's contribution.",
        reasoning=f"Delivery carries a near-fixed fulfillment cost per drop regardless of basket size; below a break-even basket, each delivered {unit} loses money, so a too-low (or absent) minimum quietly funds unprofitable orders.",
        conclusion=f"Set a delivery minimum at the break-even basket (~${X}) or add a small-order fee, and nudge add-ons to clear it.",
        expected_effect=f"Lifting sub-threshold orders over break-even protects ~${X}/mo in delivery margin.",
        recommend_when={"state": "delivery_min_order", "min_signal": "delivery_orders"},
        tags=("channel", "delivery", "margin", v.family),
    )


def _delivery_refund_rate(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Delivery orders get refunded far more than in-store",
        observation=f"Refund/adjustment rate on delivery {unit}s is {X}% versus {X}% in-store, concentrated in {X} recurring issues (missing item, late, quality).",
        reasoning=f"A delivery refund is a triple loss — the food, the fee, and the customer's trust — and unlike an in-store fix you can't recover it on the spot; a high delivery refund rate signals a packing/handoff process gap that compounds with volume.",
        conclusion=f"Add a delivery order-accuracy check at handoff and fix the top {X} refund reasons before scaling delivery volume.",
        expected_effect=f"Halving the delivery refund gap protects ~${X}/mo and lifts platform rating.",
        recommend_when={"state": "delivery_refund_high", "min_signal": "delivery_orders"},
        tags=("channel", "delivery", "quality", v.family),
    )


# ═══════════════════════ ONLINE ═════════════════════════════════════════════
def _online_share_lagging(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    extra = " The category around you is shifting online faster than you are — the gap is widening." if situation == "emerging" else ""
    return Built(
        title=f"Your online {unit} share lags the category",
        observation=f"Online is {X}% of your {unit}s versus a ~{X}% benchmark for comparable {v.name.lower()}s; growth is flat.{extra}",
        reasoning=f"Online {unit}s carry higher attach and lower marginal labor than counter orders; under-indexing online means you're working harder per {unit} than peers AND missing the customers who simply won't call or queue.",
        conclusion=f"Promote the online channel at every touchpoint (receipt, signage, QR) and remove the top {X} friction points in checkout.",
        expected_effect=f"Closing the online-share gap is worth ~${X}/mo in incremental, lower-cost {unit}s.",
        recommend_when={"state": "online_share_low", "min_signal": "online_orders"},
        tags=("channel", "online", "mix", v.family),
    )


def _online_vs_instore_price_parity(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your online and in-store prices don't match — and it's costing you",
        observation=f"{X}% of items differ in price between online and in-store, with online averaging {X}% higher/lower with no deliberate strategy.",
        reasoning=f"Unintended price gaps confuse and erode trust: if online is higher you suppress the cheaper-to-serve channel; if lower you give away margin to customers who'd have paid counter price — either way the gap is an accident, not a plan.",
        conclusion=f"Set a deliberate channel-pricing policy (parity, or a justified channel premium) and reconcile the {X} mismatched items.",
        expected_effect=f"Aligning channel pricing on purpose protects ~${X}/mo and removes a trust leak.",
        recommend_when={"state": "price_parity_gap", "min_signal": "online_orders"},
        tags=("channel", "online", "pricing", v.family),
    )


def _online_fulfillment_delay(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Online orders sit too long before fulfillment",
        observation=f"Median time from online {unit} placed to ready/handed-off is {X} min, and {X}% breach the promised window.",
        reasoning=f"An online order's clock starts the moment it's placed, not when staff notice it; slow acknowledgment burns the convenience that made the customer order online, driving cancellations and one-and-done behavior on your highest-potential channel.",
        conclusion=f"Add an audible/queued online-order alert at the make line and set a {X}-min acknowledgment SLA.",
        expected_effect=f"Tightening online fulfillment protects repeat online {unit}s worth ~${X}/mo.",
        recommend_when={"state": "online_fulfillment_slow", "min_signal": "online_orders"},
        tags=("channel", "online", "ops", v.family),
    )


# ═══════════════════════ BOOKING ════════════════════════════════════════════
def _booking_channel_friction(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Customers start a booking and don't finish",
        observation=f"{X}% of online booking sessions abandon before confirming, clustering at the {X} step (time selection / details / deposit).",
        reasoning=f"A booking abandon is a customer who already decided to come and was stopped by friction; for an appointment-led {v.name.lower()} that drop is a lost {unit} AND a lost downstream rebook, so checkout friction compounds over the relationship.",
        conclusion=f"Instrument the booking funnel, remove the friction at the worst step, and offer a held-slot reminder to recover abandoners.",
        expected_effect=f"Recovering {X}% of abandoned bookings is worth ~${X}/mo in {unit}s on existing demand.",
        recommend_when={"state": "booking_friction", "min_signal": "booking_sessions"},
        tags=("channel", "booking", "funnel", v.family),
    )


def _booking_no_show_by_channel(v: Vertical, situation: str) -> Built:
    return Built(
        title=f"Online bookings no-show more than phone or walk-in",
        observation=f"No-show rate is {X}% on self-serve online bookings versus {X}% on {v.staff_role}-taken ones, on similar {v.sale_unit}s.",
        reasoning=f"A frictionless online booking is also a low-commitment one; without the social contract of speaking to a {v.staff_role}, online bookings need their own confirmation/deposit friction or they translate to empty {v.sale_unit} slots you can't refill.",
        conclusion=f"Add a confirmation step (deposit or two-way reminder) specifically to the online booking path and re-measure no-show by channel.",
        expected_effect=f"Closing the online no-show gap recovers ~${X}/mo of otherwise-empty capacity.",
        recommend_when={"state": "online_booking_noshow", "min_signal": "booking_sessions"},
        tags=("channel", "booking", "no_show", v.family),
    )


# ═══════════════════════ CROSS-CHANNEL ══════════════════════════════════════
def _self_serve_vs_staffed_mix(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Customers who'd self-serve are still tying up your {v.staff_role}s",
        observation=f"Only {X}% of {unit}s flow through self-serve (online/kiosk) despite {X}% being simple, repeatable orders a {v.staff_role} handles manually.",
        reasoning=f"Routing simple, known orders through staff spends your scarcest peak resource on low-judgment work; shifting them to self-serve frees the {v.staff_role} for high-touch {unit}s and removes a bottleneck without cutting service where it matters.",
        conclusion=f"Promote self-serve for the top {X} repeat order types and reserve {v.staff_role} attention for complex or high-value {unit}s.",
        expected_effect=f"Shifting routine volume to self-serve frees peak labor worth ~${X}/mo.",
        recommend_when={"state": "self_serve_underused", "min_signal": "online_orders"},
        tags=("channel", "self_serve", "mix", v.family),
    )


def _channel_cannibalization(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"A new channel is shifting orders, not adding them",
        observation=f"Since launching {X}, online/delivery {unit}s rose {X}% while walk-in fell {X}% — net {unit} growth is near zero.",
        reasoning=f"Channel growth only pays if it's incremental; when a new channel mostly migrates existing demand into a higher-cost path, you add fulfillment cost and platform fees for the same customers — a margin loss disguised as channel success.",
        conclusion=f"Measure incrementality (new customers vs migrated) and stop subsidizing the new channel for demand you already owned cheaply.",
        expected_effect=f"Correcting for cannibalization protects ~${X}/mo currently spent moving demand sideways.",
        recommend_when={"state": "channel_cannibalization", "min_signal": "transactions"},
        tags=("channel", "mix", "margin", v.family),
    )


def _after_hours_demand(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Demand keeps arriving after you close — and goes uncaptured",
        observation=f"{X} calls hit voicemail and {X} online sessions occur after closing each week, with no order path open.",
        reasoning=f"After-hours contacts are intent that doesn't reschedule to your hours — it routes to whoever IS reachable; a {v.name.lower()} with no async path (voice agent, online preorder, scheduled order) simply hands that demand to a competitor.",
        conclusion=f"Open an always-on capture path: a voice agent for after-hours calls and online preorder/scheduling for after-hours browsers.",
        expected_effect=f"Capturing after-hours intent is worth ~${X}/mo in {unit}s that currently leak nightly.",
        recommend_when={"state": "after_hours_uncaptured", "min_signal": "phone_call_logs"},
        tags=("channel", "after_hours", v.family),
    )


def _single_channel_risk(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"You sell through one channel only — no demand backstop",
        observation=f"100% of {unit}s come through {v.channels[0].replace('_',' ')}; there is no phone, online, or booking path to capture demand when that channel is disrupted or saturated.",
        reasoning=f"A single-channel {v.name.lower()} has no shock absorber: weather, a slow location day, or a peak that exceeds counter capacity has nowhere to overflow, so demand that can't use the one channel is simply lost rather than redirected.",
        conclusion=f"Add one complementary channel (online preorder or phone order) sized to capture overflow and bad-day demand.",
        expected_effect=f"A second channel as a demand backstop is worth ~${X}/mo in recovered overflow {unit}s.",
        recommend_when={"state": "single_channel_risk", "min_signal": "transactions"},
        tags=("channel", "risk", "mix", v.family),
    )


def _peak_channel_overflow(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your walk-in peak overflows with no order-ahead relief valve",
        observation=f"At the {X} peak, queue/wait exceeds {X} min and {X}% of would-be {unit}s walk, yet order-ahead/online is barely promoted then.",
        reasoning=f"A physical queue has a hard ceiling; once the line passes a visible threshold, additional demand balks no matter how fast the {v.staff_role}s work — order-ahead is the only lever that adds throughput without adding counter space.",
        conclusion=f"Push order-ahead specifically during the {X} peak (signage, app nudge) to divert balk-prone demand off the line.",
        expected_effect=f"Diverting even {X}% of peak balkers to order-ahead is worth ~${X}/mo.",
        recommend_when={"state": "peak_channel_overflow", "min_signal": "online_orders"},
        tags=("channel", "online", "peak", v.family),
    )


def _channel_margin_leader_underpromoted(v: Vertical, situation: str) -> Built:
    unit = v.sale_unit
    return Built(
        title=f"Your highest-margin channel gets the least promotion",
        observation=f"The {X} channel nets the best contribution per {unit} ({X}%) but receives the least marketing spend and lowest share of {unit}s.",
        reasoning=f"Marketing should flow to where each {unit} earns the most, not where volume already is; under-promoting the best-margin channel leaves the most profitable demand un-stimulated while spend props up lower-margin paths.",
        conclusion=f"Re-allocate promotion toward the highest-contribution channel and set a share-of-{unit} growth target for it.",
        expected_effect=f"Shifting demand toward the margin-leading channel is worth ~${X}/mo in blended contribution.",
        recommend_when={"state": "margin_leader_underpromoted", "min_signal": "transactions"},
        tags=("channel", "margin", "mix", v.family),
    )


# ─────────────────────────── REGISTER ───────────────────────────────────────
_PHONE = _ch("phone")
_DRIVE = _ch("drive_thru")
_DELIVERY = _ch("delivery")
_ONLINE = _ch("online")
_BOOKING = _ch("booking")
_ONLINE_AND_WALKIN = _ch_all("online", "walk_in")
_PHONE_OR_ONLINE = _ch("phone", "online")

register(
    # ── Phone ──
    Archetype(
        key="missed_phone_calls", domain="channel", name="Missed inbound calls",
        build=_missed_phone_calls, situations=("baseline", "concentrated"),
        required_signals=("phone_call_logs",),
        required_agents=("PhoneInsightAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PhoneInsightAgent: aggregate phone_call_logs (status/duration) into miss-rate-by-hour; voice-agent logs exist for some merchants but coverage and status normalization are partial.",
        applies_keys=_PHONE,
    ),
    Archetype(
        key="phone_order_conversion_low", domain="channel", name="Low call-to-order",
        build=_phone_order_conversion_low, situations=("baseline",),
        required_signals=("phone_call_logs", "phone_orders"),
        required_agents=("PhonePOSFusionAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PhonePOSFusionAgent: join answered phone_call_logs to phone_orders.pos_success to compute call-to-order conversion; the call↔order key is not reliably linked today.",
        applies_keys=_PHONE,
    ),
    Archetype(
        key="phone_hold_time", domain="channel", name="Long hold time",
        build=_phone_hold_time, situations=("baseline",),
        required_signals=("phone_call_logs",),
        required_agents=("PhoneInsightAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PhoneInsightAgent (shared): derive time-to-answer and abandon-vs-hold curve from phone_call_logs timestamps.",
        applies_keys=_PHONE,
    ),
    Archetype(
        key="call_abandon_at_peak", domain="channel", name="Peak call abandonment",
        build=_call_abandon_at_peak, situations=("baseline",),
        required_signals=("phone_call_logs", "hourly_revenue"),
        required_agents=("PhoneInsightAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="PhoneInsightAgent + PatternAnalyzer: cross call-abandon timestamps with hourly_revenue peaks to prove the collision of phone and in-person demand.",
        applies_keys=_PHONE,
    ),
    Archetype(
        key="voicemail_no_callback", domain="channel", name="Voicemail not returned",
        build=_voicemail_no_callback, situations=("baseline",),
        required_signals=("phone_call_logs",),
        required_agents=("PhonePOSFusionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="PhonePOSFusionAgent: pair inbound voicemails with subsequent outbound callbacks (outbound call logging not yet ingested) to measure callback rate and lag.",
        applies_keys=_PHONE,
    ),
    Archetype(
        key="phone_upsell_gap", domain="channel", name="Phone upsell gap",
        build=_phone_upsell_gap, situations=("baseline",),
        required_signals=("phone_orders", "transactions"),
        required_agents=("PhonePOSFusionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="PhonePOSFusionAgent: NLP over phone_call_logs.transcript to detect attach offers and compare phone vs counter ticket — transcript mining is not built yet.",
        applies_keys=_PHONE,
    ),
    Archetype(
        key="phone_agent_deflection", domain="channel", name="Routine-call deflection",
        build=_phone_agent_deflection, situations=("baseline",),
        required_signals=("phone_call_logs",),
        required_agents=("PhoneInsightAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="PhoneInsightAgent: classify call intent from transcript to size deflectable routine-call volume — call-reason classification is not yet implemented.",
        applies_keys=_PHONE,
    ),
    Archetype(
        key="phone_conversion_by_rep", domain="channel", name="Per-rep call conversion",
        build=_phone_conversion_by_rep, situations=("baseline",),
        required_signals=("phone_orders", "phone_call_logs"),
        required_agents=("PhonePOSFusionAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="PhonePOSFusionAgent: attribute calls/orders to the answering staff member (no agent_id on phone_call_logs today) to rank per-rep conversion.",
        applies_keys=_PHONE,
    ),
    # ── Drive-thru (QSR-only via channel) ──
    Archetype(
        key="drive_thru_time", domain="channel", name="Slow drive-thru",
        build=_drive_thru_time, situations=("baseline",),
        required_signals=("drive_thru_timing",),
        required_agents=("DriveThruTimingAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="DriveThruTimingAgent: ingest lane timing per station (order/pay/present) — drive-thru timer data is not connected; derive per-car time and queue length.",
        applies_keys=_DRIVE,
    ),
    Archetype(
        key="drive_thru_vs_lobby_mix", domain="channel", name="Lane/lobby imbalance",
        build=_drive_thru_vs_lobby_mix, situations=("baseline",),
        required_signals=("drive_thru_timing", "schedule_shifts"),
        required_agents=("DriveThruTimingAgent", "StaffingAgent"),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="DriveThruTimingAgent + StaffingAgent: compare per-channel volume to per-channel staffing at peak; requires lane timing ingest plus channel-tagged labor.",
        applies_keys=_DRIVE,
    ),
    # ── Delivery (delivery-channel verticals) ──
    Archetype(
        key="delivery_fee_erosion", domain="channel", name="Delivery fee erosion",
        build=_delivery_fee_erosion, situations=("baseline", "leaking"),
        required_signals=("delivery_orders", "transactions"),
        required_agents=("ChannelMarginAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ChannelMarginAgent: join delivery_orders (commission/fee fields) to item margin in transactions to compute per-channel contribution; fee parsing per platform is partial.",
        applies_keys=_DELIVERY,
    ),
    Archetype(
        key="channel_margin_mix", domain="channel", name="Channel margin mix",
        build=_channel_margin_mix, situations=("baseline", "leaking"),
        required_signals=("transactions", "delivery_orders", "online_orders"),
        required_agents=("ChannelMarginAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ChannelMarginAgent (shared): compute contribution per channel and overlay growth rate to flag growth concentrating in the lowest-margin channel.",
        applies_keys=_DELIVERY,
    ),
    Archetype(
        key="delivery_radius_profitability", domain="channel", name="Delivery radius profit",
        build=_delivery_radius_profitability, situations=("baseline",),
        required_signals=("delivery_orders",),
        required_agents=("ChannelMarginAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ChannelMarginAgent (geo): attach delivery distance/drive-time to each delivery order (geo fields not ingested) to compute contribution by distance band.",
        applies_keys=_DELIVERY,
    ),
    Archetype(
        key="delivery_platform_dependence", domain="channel", name="Single-platform dependence",
        build=_delivery_platform_dependence, situations=("baseline", "concentrated"),
        required_signals=("delivery_orders",),
        required_agents=("ChannelMarginAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ChannelMarginAgent (shared): break delivery_orders down by platform to surface concentration and commission exposure.",
        applies_keys=_DELIVERY,
    ),
    Archetype(
        key="delivery_min_order", domain="channel", name="Sub-break-even delivery",
        build=_delivery_min_order, situations=("baseline",),
        required_signals=("delivery_orders",),
        required_agents=("ChannelMarginAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ChannelMarginAgent (shared): model fixed fulfillment cost per drop and flag delivery baskets below break-even.",
        applies_keys=_DELIVERY,
    ),
    Archetype(
        key="delivery_refund_rate", domain="channel", name="Delivery refund rate",
        build=_delivery_refund_rate, situations=("baseline",),
        required_signals=("delivery_orders", "transactions"),
        required_agents=("ChannelMarginAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ChannelMarginAgent (quality): ingest delivery refund/adjustment events and reason codes (not captured today) and compare to in-store refund rate.",
        applies_keys=_DELIVERY,
    ),
    # ── Online ──
    Archetype(
        key="online_share_lagging", domain="channel", name="Online share lagging",
        build=_online_share_lagging, situations=("baseline", "emerging"),
        required_signals=("online_orders", "transactions"),
        required_agents=("ChannelMixAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ChannelMixAgent: compute online share of orders vs a category benchmark; benchmark library not yet assembled.",
        applies_keys=_ONLINE,
    ),
    Archetype(
        key="online_vs_instore_price_parity", domain="channel", name="Channel price parity",
        build=_online_vs_instore_price_parity, situations=("baseline",),
        required_signals=("online_orders", "transactions"),
        required_agents=("ChannelPriceAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ChannelPriceAgent: reconcile item-level prices between online_orders and in-store transactions to detect unintended channel price gaps.",
        applies_keys=_ONLINE_AND_WALKIN,
    ),
    Archetype(
        key="online_fulfillment_delay", domain="channel", name="Slow online fulfillment",
        build=_online_fulfillment_delay, situations=("baseline",),
        required_signals=("online_orders",),
        required_agents=("OnlineOpsAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="OnlineOpsAgent: capture online order lifecycle timestamps (placed→ready→handed-off); online ops events are not ingested today.",
        applies_keys=_ONLINE,
    ),
    # ── Booking ──
    Archetype(
        key="booking_channel_friction", domain="channel", name="Booking funnel friction",
        build=_booking_channel_friction, situations=("baseline",),
        required_signals=("booking_sessions",),
        required_agents=("BookingFunnelAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="BookingFunnelAgent: instrument the online booking funnel (step-level events not captured) to locate abandonment and recover held slots.",
        applies_keys=_BOOKING,
    ),
    Archetype(
        key="booking_no_show_by_channel", domain="channel", name="Online-booking no-show",
        build=_booking_no_show_by_channel, situations=("baseline",),
        required_signals=("booking_sessions",),
        required_agents=("BookingFunnelAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="BookingFunnelAgent (shared): split no-show rate by booking origin (online vs staff-taken) — booking origin is not tagged on appointments today.",
        applies_keys=_BOOKING,
    ),
    # ── Cross-channel ──
    Archetype(
        key="self_serve_vs_staffed_mix", domain="channel", name="Self-serve underused",
        build=_self_serve_vs_staffed_mix, situations=("baseline",),
        required_signals=("online_orders", "transactions"),
        required_agents=("ChannelMixAgent",),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ChannelMixAgent (shared): classify orders as simple/repeatable and measure how many simple orders still route through staff vs self-serve.",
        applies_keys=_ONLINE_AND_WALKIN,
    ),
    Archetype(
        key="channel_cannibalization", domain="channel", name="Channel cannibalization",
        build=_channel_cannibalization, situations=("baseline",),
        required_signals=("transactions", "online_orders", "delivery_orders"),
        required_agents=("ChannelMixAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ChannelMixAgent (incrementality): measure new-vs-migrated customers when a channel launches (needs stable cross-channel customer identity) to separate incremental growth from cannibalization.",
        applies_keys=_PHONE_OR_ONLINE,
    ),
    Archetype(
        key="after_hours_demand", domain="channel", name="After-hours demand",
        build=_after_hours_demand, situations=("baseline",),
        required_signals=("phone_call_logs", "online_orders"),
        required_agents=("ChannelMixAgent", "PhoneInsightAgent"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ChannelMixAgent + PhoneInsightAgent: count after-close voicemails and online sessions against business hours to size uncaptured async demand.",
        applies_keys=_PHONE_OR_ONLINE,
    ),
    Archetype(
        key="single_channel_risk", domain="channel", name="Single-channel risk",
        build=_single_channel_risk, situations=("baseline",),
        required_signals=("transactions",),
        required_agents=("ChannelMixAgent",),
        swarm_capability=SwarmCapability.FULL,
        applies_keys=_single_channel_keys(),
    ),
    Archetype(
        key="peak_channel_overflow", domain="channel", name="Peak overflow to order-ahead",
        build=_peak_channel_overflow, situations=("baseline",),
        required_signals=("online_orders", "hourly_revenue"),
        required_agents=("ChannelMixAgent", "PatternAnalyzer"),
        swarm_capability=SwarmCapability.PARTIAL,
        swarm_upgrade="ChannelMixAgent + PatternAnalyzer: cross peak queue/wait signals with order-ahead share to size balk-prone demand divertible to online.",
        applies_keys=_ONLINE,
    ),
    Archetype(
        key="channel_margin_leader_underpromoted", domain="channel", name="Margin-leader underpromoted",
        build=_channel_margin_leader_underpromoted, situations=("baseline",),
        required_signals=("transactions", "delivery_orders", "online_orders"),
        required_agents=("ChannelMarginAgent",),
        swarm_capability=SwarmCapability.MISSING,
        swarm_upgrade="ChannelMarginAgent (allocation): rank channels by contribution and compare to marketing spend/share by channel to flag the under-promoted margin leader.",
        applies_keys=_PHONE_OR_ONLINE,
    ),
)
