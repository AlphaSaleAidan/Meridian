"""
Unified payments — Stripe Connect.

One processor across any POS: each merchant gets a Stripe *connected account*
during onboarding; the customer pays via Stripe Checkout (destination charge →
the merchant's account, minus a Meridian application fee). The order still goes
to whichever POS the merchant runs; "take the money" is always Stripe.

Endpoints:
  POST /api/stripe/connect/onboard/{merchant_id} → create connected account (if
       needed) + return a Stripe onboarding link (used by the onboarding wizard)
  GET  /api/stripe/connect/status/{merchant_id}  → onboarding / charges status
  POST /api/stripe/connect/webhook               → account.updated (mark
       charges_enabled) + checkout.session.completed (mark the order paid)

All Stripe calls are lazy-imported so the module loads with no SDK/key present.
"""
import json
import logging
import os
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import enforce_service_member, require_service_auth
from ...db import get_db

logger = logging.getLogger("meridian.stripe.connect")

router = APIRouter(prefix="/api/stripe/connect", tags=["stripe-connect"])

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
CONNECT_WEBHOOK_SECRET = os.getenv("STRIPE_CONNECT_WEBHOOK_SECRET", "")
# PHONE-ORDER ACCOUNT SPLIT (see services/phone_agent/payment_links.py): phone
# order checkouts can run on their own Stripe account, which signs its webhooks
# with its own secret and mints its own connected accounts. Both stay optional —
# unset, this module behaves exactly as it did on a single platform account.
STRIPE_PHONE_SECRET_KEY = os.getenv("STRIPE_PHONE_SECRET_KEY", "")
PHONE_WEBHOOK_SECRET = os.getenv("STRIPE_PHONE_WEBHOOK_SECRET", "")
# Opt-in: create NEW connected accounts under the phone-order platform. Default
# off so onboarding keeps landing on the existing platform until ops flips it.
PHONE_ONBOARDING = os.getenv("STRIPE_PHONE_ONBOARDING", "0") == "1"
CONNECT_RETURN_URL = os.getenv("CONNECT_RETURN_URL", "https://meridian.tips/canada/portal?payments=connected")
CONNECT_REFRESH_URL = os.getenv("CONNECT_REFRESH_URL", "https://meridian.tips/canada/portal?payments=retry")
CONNECT_COUNTRY = os.getenv("CONNECT_DEFAULT_COUNTRY", "CA")
# Platform publishable key for the embedded Connect.js flow. Prefer the phone-
# order account's pk when the split is on; fall back to the platform pk.
CONNECT_PUBLISHABLE_KEY = (
    os.getenv("STRIPE_PHONE_PUBLISHABLE_KEY")
    or os.getenv("STRIPE_PUBLISHABLE_KEY", "")
)

# phone_agent modules (pay_on_phone.mark_order_paid) live in a sibling dir.
_PHONE_AGENT_DIR = str(Path(__file__).resolve().parents[3] / "services" / "phone_agent")
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)


def _stripe(api_key: str = ""):
    import stripe
    stripe.api_key = api_key or STRIPE_SECRET_KEY
    return stripe


def _onboarding_key() -> str:
    """Platform account that NEW connected accounts are created under."""
    if PHONE_ONBOARDING and STRIPE_PHONE_SECRET_KEY:
        return STRIPE_PHONE_SECRET_KEY
    return STRIPE_SECRET_KEY


def _webhook_secrets() -> list[str]:
    """Signing secrets accepted on the Connect webhook, primary first. Two
    endpoints (one per platform account) deliver the same event shapes; a
    signature valid under either is processed identically."""
    return [s for s in (CONNECT_WEBHOOK_SECRET, PHONE_WEBHOOK_SECRET) if s]


def _retrieve_account(acct: str):
    """Read a connected account from whichever platform owns it. Accounts minted
    before the phone-order split live on the original platform and ones minted
    after STRIPE_PHONE_ONBOARDING live on the new one, so the status endpoint
    tries the platform key first and the phone key second."""
    keys = [k for k in (STRIPE_SECRET_KEY, STRIPE_PHONE_SECRET_KEY) if k]
    err: Exception | None = None
    for key in keys:
        try:
            return _stripe(key).Account.retrieve(acct, api_key=key)
        except Exception as e:  # noqa: BLE001 — try the other platform
            err = e
    raise err if err else RuntimeError("Stripe not configured")


def _construct_event(stripe, payload: bytes, sig: str):
    """Verify against each configured secret; raise the last error if none match."""
    err: Exception | None = None
    for secret in _webhook_secrets():
        try:
            return stripe.Webhook.construct_event(payload, sig, secret)
        except Exception as e:  # noqa: BLE001 — try the next secret, then re-raise
            err = e
    raise err if err else RuntimeError("no webhook secret configured")


async def _set_config(db, merchant_id: str, patch: dict) -> None:
    rows = await db.select("phone_agent_config", filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    if rows:
        await db.update("phone_agent_config", patch, filters={"merchant_id": f"eq.{merchant_id}"})
    else:
        await db.insert("phone_agent_config", {"merchant_id": merchant_id, **patch})


async def _merchant_service_fee_cents(merchant_id: str) -> int:
    """Per-order fee to credit for a paid phone order, in precedence order:
      1. rep-set override (phone_agent_config.order_fee_cents, migration 042)
      2. provisioned billing contract (merchant_billing_terms.order_fee_cents)
      3. MERIDIAN_SERVICE_FEE_CENTS env default
    Lookup failures at any layer (including pre-migration schemas) fall
    through to the next — the fee lookup never breaks the webhook."""
    fee = int(os.getenv("MERIDIAN_SERVICE_FEE_CENTS", "0") or 0)
    try:
        rows = await get_db().select(
            "phone_agent_config", "order_fee_cents",
            filters={"merchant_id": f"eq.{merchant_id}"}, limit=1,
        )
        if rows and rows[0].get("order_fee_cents") is not None:
            return max(int(rows[0]["order_fee_cents"]), 0)
    except Exception as e:  # noqa: BLE001 — fee lookup never breaks the webhook
        logger.warning("order-fee override lookup failed for %s: %s", merchant_id, e)
    try:
        from ...billing.fee_terms import get_active_terms  # fail-open internally
        terms = await get_active_terms(get_db(), merchant_id)
        if terms and terms.get("order_fee_cents") is not None:
            return max(int(terms["order_fee_cents"]), 0)
    except Exception as e:  # noqa: BLE001
        logger.warning("billing-terms fee lookup failed for %s: %s", merchant_id, e)
    return fee


async def _reversed_fee_cents(db, merchant_id: str, order_id) -> int:
    """Service-fee cents already reversed for this order (sum of prior
    stripe_fee_reversal debits). Lets a later/larger partial (or full) refund
    reverse only the not-yet-reversed DELTA instead of double-debiting. Fails to
    0 (fail-open) — worst case we under-reverse, never over-reverse."""
    try:
        rows = await db.select(
            "voice_ledger", "amount_cents,note",
            filters={"merchant_id": f"eq.{merchant_id}", "source": "eq.stripe_fee_reversal"},
            limit=1000,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("refund: prior-reversal lookup failed for %s: %s", merchant_id, e)
        return 0
    suffix = f":{order_id}"
    return sum(
        int(r.get("amount_cents") or 0)
        for r in (rows or []) if str(r.get("note") or "").endswith(suffix)
    )


async def _reverse_paid_order(
    db, payment_intent: str, *, disputed: bool,
    amount_charged: int = 0, amount_refunded: int = 0, fully_refunded: bool = True,
) -> None:
    """A charge was refunded/disputed — undo what payment confirmation did,
    PROPORTIONAL to how much actually left the merchant.

    Linked by the payment_intent stored as phone_orders.payment_txn_id at pay
    time. A partial refund (`fully_refunded=False`) marks the order
    'partially_refunded' and reverses only the pro-rata slice of the service fee
    (fee × amount_refunded / amount_charged); a full refund/dispute marks it
    refunded/disputed and reverses the whole fee. The reversal debits only the
    DELTA past what's already been reversed for this order (via
    _reversed_fee_cents), so a $2 then $5 refund on the same order reverse
    correctly and a webhook RETRY of either never double-reverses. Best-effort
    throughout: a missing row / column / ledger hiccup is logged, never raised
    (the webhook must still 200 so Stripe stops retrying). Website orders take
    their fee as a checkout line, not a ledger credit, so nothing to reverse.

    Note: sales-rep commission is milestone/subscription-based (accrued at deal
    close, not per phone order), so a per-order refund correctly touches nothing
    in the commission ledger — there is no per-order commission to reverse."""
    if not payment_intent:
        return
    if disputed:
        status = "disputed"
    elif fully_refunded:
        status = "refunded"
    else:
        status = "partially_refunded"
    try:
        rows = await db.select(
            "phone_orders", "id,merchant_id,status",
            filters={"payment_txn_id": f"eq.{payment_intent}"}, limit=1,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("refund: phone_orders lookup failed for %s: %s", payment_intent, e)
        return
    if not rows:
        logger.info("refund: no phone order for payment_intent %s (website/other) — nothing to reverse",
                    payment_intent)
        return
    order = rows[0]
    merchant_id = order.get("merchant_id") or ""
    try:
        await db.update("phone_orders", {"status": status},
                        filters={"id": f"eq.{order['id']}"})
    except Exception as e:  # noqa: BLE001
        logger.warning("refund: status flip failed for order %s: %s", order.get("id"), e)

    if merchant_id:
        fee_cents = await _merchant_service_fee_cents(merchant_id)
        if fee_cents > 0:
            # Target reversal: whole fee on a full refund/dispute; pro-rata on a
            # partial. Clamp to [0, fee_cents]. amount_charged<=0 (dispute object
            # carries no amount_refunded) falls back to the full fee.
            if disputed or fully_refunded or amount_charged <= 0:
                target = fee_cents
            else:
                target = int(round(fee_cents * amount_refunded / amount_charged))
                target = max(0, min(target, fee_cents))
            already = await _reversed_fee_cents(db, merchant_id, order.get("id"))
            delta = target - already
            if delta > 0:
                try:
                    from ...services.voice_ledger import debit
                    # ref carries the cumulative refunded amount so distinct
                    # partial-refund totals post distinctly while a retry of the
                    # same refund (same cumulative amount) dedupes as a no-op.
                    ref = f"{payment_intent}:{amount_refunded}" if not (disputed or fully_refunded) else payment_intent
                    await debit(merchant_id, delta, source="stripe_fee_reversal",
                                ref=ref, note=f"{status}:{order.get('id')}")
                    logger.info("refund: reversed %d¢ of %d¢ fee for merchant %s (%s, refunded %d/%d¢)",
                                delta, fee_cents, merchant_id, status, amount_refunded, amount_charged)
                except Exception as e:  # noqa: BLE001 — ledger reversal never blocks the webhook
                    logger.error("refund: voice_ledger reversal failed for %s: %s", merchant_id, e)


async def _ensure_connected_account(stripe, key: str, merchant_id: str) -> str:
    """The merchant's Stripe connected account id, creating it once if needed.

    The merchant does NOT need their own Stripe account — this creates an
    Express connected account FOR them under the phone-order platform, with
    daily payouts to their bank. Stripe collects the (legally required) KYC +
    bank details during onboarding; we never see raw bank numbers."""
    db = get_db()
    rows = await db.select("phone_agent_config",
                           filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    row = rows[0] if rows else {}
    acct = (row.get("stripe_account_id") or "").strip()
    if acct:
        return acct
    try:
        # api_key passed per request as well as globally: an await between
        # these two calls can let another task reassign the SDK global.
        account = stripe.Account.create(
            api_key=key,
            type="express",
            country=CONNECT_COUNTRY,
            email=(row.get("merchant_email") or None),
            capabilities={"card_payments": {"requested": True}, "transfers": {"requested": True}},
            business_profile={"name": row.get("business_name") or None},
            # Pay the merchant out DAILY — after we auto-take the service fee
            # (application_fee on each destination charge), Stripe settles the
            # remainder to them on a daily schedule.
            settings={"payouts": {"schedule": {"interval": "daily"}}},
            metadata={"merchant_id": merchant_id},
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Stripe account create failed for %s: %s", merchant_id, e)
        raise HTTPException(status_code=502, detail="Could not create Stripe account") from e
    acct = account["id"]
    await _set_config(db, merchant_id, {"stripe_account_id": acct})
    return acct


@router.post("/onboard/{merchant_id}")
async def onboard(merchant_id: str, principal=Depends(require_service_auth)):
    """Create the merchant's Stripe connected account (once) and return a hosted
    onboarding link (the redirect fallback to the embedded flow below)."""
    await enforce_service_member(principal, merchant_id)
    key = _onboarding_key()
    if not key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    stripe = _stripe(key)
    acct = await _ensure_connected_account(stripe, key, merchant_id)
    link = stripe.AccountLink.create(
        api_key=key,
        account=acct,
        refresh_url=CONNECT_REFRESH_URL,
        return_url=CONNECT_RETURN_URL,
        type="account_onboarding",
    )
    return {"account_id": acct, "onboarding_url": link["url"]}


@router.post("/account-session/{merchant_id}")
async def account_session(merchant_id: str, principal=Depends(require_service_auth)):
    """Embedded onboarding: create (once) the merchant's connected account and
    an AccountSession with the account_onboarding component, so Stripe's
    embedded form renders INSIDE the Meridian portal — the merchant never
    leaves meridian.tips and never signs into Stripe. Returns the short-lived
    client_secret + the platform publishable key the frontend Connect.js needs.

    The client polls GET /status/{merchant_id} after onExit to confirm
    charges_enabled; the account.updated webhook also syncs it server-side."""
    await enforce_service_member(principal, merchant_id)
    key = _onboarding_key()
    pub = CONNECT_PUBLISHABLE_KEY
    if not key or not pub:
        raise HTTPException(status_code=503,
                            detail="Stripe embedded onboarding not configured")
    stripe = _stripe(key)
    acct = await _ensure_connected_account(stripe, key, merchant_id)
    try:
        session = stripe.AccountSession.create(
            api_key=key,
            account=acct,
            components={"account_onboarding": {"enabled": True}},
        )
    except Exception as e:  # noqa: BLE001
        logger.error("AccountSession create failed for %s: %s", merchant_id, e)
        raise HTTPException(status_code=502,
                            detail="Could not start onboarding") from e
    return {"account_id": acct,
            "client_secret": session["client_secret"],
            "publishable_key": pub}


@router.get("/status/{merchant_id}")
async def status(merchant_id: str, principal=Depends(require_service_auth)):
    """Onboarding status for the wizard — refreshes charges_enabled from Stripe."""
    await enforce_service_member(principal, merchant_id)
    db = get_db()
    rows = await db.select("phone_agent_config", filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    acct = (rows[0].get("stripe_account_id") if rows else "") or ""
    if not acct:
        return {"connected": False, "charges_enabled": False}
    if not (STRIPE_SECRET_KEY or STRIPE_PHONE_SECRET_KEY):
        return {"connected": True, "account_id": acct, "charges_enabled": bool(rows[0].get("stripe_charges_enabled"))}
    acc = _retrieve_account(acct)
    charges = bool(acc.get("charges_enabled"))
    # keep our copy in sync so the checkout gate is accurate
    await _set_config(db, merchant_id, {"stripe_charges_enabled": charges})
    return {
        "connected": True,
        "account_id": acct,
        "charges_enabled": charges,
        "details_submitted": bool(acc.get("details_submitted")),
        "payouts_enabled": bool(acc.get("payouts_enabled")),
    }


@router.post("/webhook")
async def connect_webhook(request: Request):
    """Stripe Connect webhook: keep charges_enabled in sync and mark orders paid."""
    stripe = _stripe()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    # Fail closed: a spoofed checkout.session.completed could mark a CAD order
    # paid and release it. Never process an unverified Connect event.
    if not _webhook_secrets():
        logger.error("No Connect webhook signing secret set (STRIPE_CONNECT_WEBHOOK_SECRET / "
                     "STRIPE_PHONE_WEBHOOK_SECRET) — refusing Connect webhook (fail closed)")
        raise HTTPException(status_code=503, detail="Webhook not configured")
    try:
        _construct_event(stripe, payload, sig)  # verify signature (raises if bad)
    except Exception as e:  # noqa: BLE001
        logger.error("Connect webhook verify failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")
    # Read the VERIFIED payload as plain dicts. The stripe SDK's StripeObject in
    # this version is not dict-subclassed, so event.get(...) raises
    # "AttributeError: get" and 500s every webhook. The bytes are already
    # signature-verified above, so json.loads is safe.
    event = json.loads(payload)

    # Idempotency: dedupe on event.id via the same durable webhook_events table
    # the platform + Square/Clover/Toast webhooks use, so a REDELIVERED event
    # (Stripe retries on any non-2xx / timeout) can't re-run the release. This
    # is defense-in-depth alongside the single-event gating below; it does not
    # dedupe the distinct checkout.session.completed vs payment_intent.succeeded
    # pair (different ids) — that's what the gating handles.
    event_id = event.get("id", "")
    if event_id:
        try:
            from .webhooks import _record_webhook_event
            if not await _record_webhook_event(event_id, provider="stripe_connect"):
                return {"received": True, "dedup": True}
        except Exception:  # noqa: BLE001 — fail-open to downstream idempotency on a DB hiccup
            pass

    etype = event.get("type", "")
    obj = event.get("data", {}).get("object", {})
    db = get_db()

    if etype == "account.updated":
        acct = obj.get("id", "")
        charges = bool(obj.get("charges_enabled"))
        rows = await db.select("phone_agent_config", filters={"stripe_account_id": f"eq.{acct}"}, limit=1)
        if rows:
            await db.update("phone_agent_config", {"stripe_charges_enabled": charges},
                            filters={"stripe_account_id": f"eq.{acct}"})
            logger.info("Connect account %s charges_enabled=%s", acct, charges)

    elif etype in ("charge.refunded", "charge.dispute.created",
                   "charge.dispute.funds_withdrawn"):
        # Money left the merchant after we'd marked the order paid and credited
        # our fee. Reflect it: flip the phone order to refunded/disputed and
        # REVERSE the fee we credited, or a refunded order keeps billing the
        # merchant a service fee for revenue they no longer have. Linked by the
        # payment_intent we stored as phone_orders.payment_txn_id at pay time.
        disputed = etype.startswith("charge.dispute")
        pi = obj.get("payment_intent") or (
            obj.get("charge") if disputed else obj.get("id")) or ""
        # charge.refunded carries the CUMULATIVE amounts on the Charge object;
        # obj.refunded is True only once fully refunded. Disputes withdraw the
        # whole charge → treat as full. This lets a $2 courtesy refund on a $60
        # order reverse ~3% of the fee instead of the whole thing.
        amount_charged = int(obj.get("amount") or 0)
        amount_refunded = int(obj.get("amount_refunded") or 0)
        fully_refunded = (
            disputed or bool(obj.get("refunded"))
            or amount_charged <= 0                 # amounts unavailable → full (legacy-safe)
            or amount_refunded >= amount_charged
        )
        await _reverse_paid_order(
            db, str(pi), disputed=disputed,
            amount_charged=amount_charged, amount_refunded=amount_refunded,
            fully_refunded=fully_refunded,
        )

    elif etype == "checkout.session.expired":
        # Stripe Checkout sessions die ~24h after creation. Without this the
        # short pay-link row stays 'created', so /p/<code> 303s a customer to a
        # dead Stripe page. Flip it to expired → pay_redirect shows the branded
        # "ask for a fresh link" page instead.
        sid = obj.get("id", "")
        if sid:
            try:
                await db.update(
                    "checkout_sessions", {"status": "expired"},
                    filters={"provider_ref": f"eq.{sid}", "status": "neq.complete"},
                )
                logger.info("Stripe session %s expired → checkout_sessions marked", sid)
            except Exception as e:  # noqa: BLE001 — never fail the webhook on a stale row
                logger.warning("expire flip failed for session %s: %s", sid, e)

    elif etype in ("checkout.session.completed", "payment_intent.succeeded"):
        meta = obj.get("metadata", {}) or {}
        merchant_id = meta.get("merchant_id", "")
        pos_order_id = meta.get("pos_order_id", "")
        caller_phone = meta.get("caller_phone", "")
        website_order_id = meta.get("website_order_id", "")
        txn = obj.get("payment_intent") or obj.get("id", "")
        if website_order_id:
            # Mobile/website order: payment is the gate — mark paid and release
            # the kitchen ticket (dispatched as PAID). Idempotent inside.
            try:
                from ...services.pos_connectors.website_order_dispatch import (
                    mark_paid_and_dispatch,
                )
                result = await mark_paid_and_dispatch(website_order_id, payment_txn_id=str(txn))
                logger.info("Stripe payment confirmed → website order: %s", result)
            except Exception as e:  # noqa: BLE001 — webhook must still 200 so Stripe stops retrying spuriously
                logger.error("mark_paid_and_dispatch failed for %s: %s", website_order_id, e)
        elif etype == "checkout.session.completed":
            # Phone order release ONLY on the canonical single event — the SAME
            # gate the receipt + voice_ledger credit below already use.
            # payment_intent.succeeded fires for the same order, and
            # mark_order_paid re-creates the DEFERRED POS ticket non-atomically
            # (SELECT-then-PATCH, no CAS), so processing both events concurrently
            # (two uvicorn workers) double-pushes the kitchen ticket. A phone
            # pay_now Checkout always emits checkout.session.completed, so gating
            # here loses no releases. (website path above stays on both events —
            # mark_paid_and_dispatch is an atomic CAS, so it's already safe.)
            try:
                from pay_on_phone import mark_order_paid
                result = await mark_order_paid(
                    merchant_id=merchant_id, caller_phone=caller_phone,
                    pos_order_id=pos_order_id, method="stripe", payment_txn_id=str(txn),
                    # amount actually paid — disambiguates which open order this
                    # settles when pos_order_id is empty (deferred pay_now) and a
                    # repeat caller has more than one open order.
                    paid_amount_cents=int(obj.get("amount_total") or 0),
                )
                logger.info("Stripe payment confirmed → order released: %s", result)
            except Exception as e:  # noqa: BLE001 — webhook must still 200 so Stripe stops retrying spuriously
                logger.error("mark_order_paid failed for %s: %s", merchant_id, e)

        # Text the customer a paid receipt via the SHARED, idempotent helper —
        # the SAME send the streaming pay_at_pickup path uses. Only on
        # checkout.session.completed (canonical, fires once) so
        # payment_intent.succeeded can't double-send; the helper is also
        # idempotent on the order id so a webhook retry (or the streaming path
        # already having sent) never double-texts.
        if etype == "checkout.session.completed" and caller_phone:
            try:
                from merchant_config import get_merchant_config, _demo_config
                from order_receipt import ReceiptClaim, send_order_receipt
                cfg = (await get_merchant_config(merchant_id)) if merchant_id else None
                cfg = cfg or _demo_config(merchant_id or "demo")
                name = (obj.get("customer_details") or {}).get("name") or ""
                order = {
                    "merchant_id": merchant_id,
                    "business_name": getattr(cfg, "business_name", "") or "",
                    "customer_name": name,
                    "caller_phone": caller_phone,
                }
                # CLAIM the right phone_orders row. For pay_now the POS ticket is
                # DEFERRED, so the held row carried pos_order_id="" at checkout and
                # metadata.pos_order_id is empty here — claiming on the Stripe
                # session id (obj.id) matched ZERO rows and SILENTLY DROPPED the
                # receipt. mark_order_paid (above) just released this caller's
                # newest order, so claim on merchant+phone most-recent. Only when a
                # real pos_order_id rode along in metadata (non-deferred) do we
                # claim on it directly.
                dedup = str(pos_order_id or obj.get("id") or txn)
                if pos_order_id:
                    claim = ReceiptClaim(column="pos_order_id", value=str(pos_order_id),
                                         dedup_id=dedup)
                else:
                    claim = ReceiptClaim(merchant_id=merchant_id, caller_phone=caller_phone,
                                         dedup_id=dedup)
                res = await send_order_receipt(
                    order, cfg,
                    order_id=dedup,
                    claim=claim,
                    paid=True,
                    amount_cents=obj.get("amount_total"),
                    currency=obj.get("currency"),
                )
                logger.info("Receipt SMS to %s: %s", caller_phone, res)
            except Exception as e:  # noqa: BLE001 — receipt never blocks the webhook
                logger.error("receipt SMS failed for %s: %s", merchant_id, e)

        # Credit our service-fee revenue to this merchant's voice ledger. Only on
        # checkout.session.completed (the one canonical event per order — the
        # session id is a stable idempotency ref); payment_intent.succeeded fires
        # for the same order and would double-post under a different ref.
        # Phone orders only — website orders take their fee as a checkout line /
        # application fee, so a ledger credit would double-count that revenue.
        if etype == "checkout.session.completed" and merchant_id and not website_order_id:
            fee_cents = await _merchant_service_fee_cents(merchant_id)
            if fee_cents > 0:
                try:
                    from ...services.voice_ledger import credit
                    await credit(merchant_id, fee_cents, source="stripe_fee",
                                 ref=str(obj.get("id") or txn), note=pos_order_id or None)
                except Exception as e:  # noqa: BLE001 — ledger never blocks the webhook
                    logger.error("voice_ledger credit failed for %s: %s", merchant_id, e)

    return {"received": True}
