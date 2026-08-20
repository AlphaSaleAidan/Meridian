"""
Billing API routes — Square invoicing and subscription management.

Endpoints:
  POST /api/billing/create-invoice   → Create custom invoice via Square
  POST /api/billing/cancel           → Cancel a subscription
  POST /api/billing/webhook          → Handle Square payment webhooks
  GET  /api/billing/status/:org_id   → Get subscription status
"""

import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, field_validator

from ..auth import (
    require_admin,
    require_admin_auth,
    require_admin_jwt,
    require_jwt,
    require_org_member,
    require_service_auth,
)
from ...db import get_db

import stripe  # noqa: E402 — Stripe subscription reads for the billing display

logger = logging.getLogger("meridian.billing.routes")

router = APIRouter(prefix="/api/billing", tags=["billing"])

MAX_AMOUNT_CENTS = 10_000_00  # $10,000 safety cap

# The subscription runs on the PLATFORM Stripe account (Meridian Checkout,
# STRIPE_SECRET_KEY), the same key the subscribe-link + activation webhook use.
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
_FRONTEND_URL = os.getenv("FRONTEND_URL", "https://meridian.tips")

# Access-wind-down enforcement kill-switch (Workstream 4).
# Proposed policy (flagged for Aidan in the PR):
#   full access to end of paid period -> 30-day read-only export window ->
#   deactivation. Until this flag is ON, self-cancel RECORDS the cancellation
#   and halts renewals but makes NO access change ('recorded' status) — nothing
#   cuts a live merchant off without sign-off. Default OFF.
WINDDOWN_READONLY_DAYS = 30


def _winddown_enforced() -> bool:
    """True only when SUBSCRIPTION_WINDDOWN_ENFORCED is explicitly truthy.

    Default OFF (conservative): cancel is recorded, renewals stop, but access
    is not changed until Aidan flips this flag.
    """
    return os.environ.get("SUBSCRIPTION_WINDDOWN_ENFORCED", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


async def _resolve_owned_org(user: dict) -> str | None:
    """Return the org_id the session user is the OWNER of, or None.

    The org is derived from the SESSION (businesses.owner_user_id == user.id),
    never from the request body. Members who are not owners get None — only an
    owner may cancel the account. Global ADMIN_EMAILS are NOT auto-granted an
    org here (admins use the admin-locked /cancel route).
    """
    user_id = user.get("id") or user.get("sub") or ""
    if not user_id:
        return None
    try:
        db = get_db()
        rows = await db.select(
            "businesses", "id",
            filters={"owner_user_id": f"eq.{user_id}"},
            limit=1,
        )
    except Exception as exc:
        logger.warning("owner-org lookup failed for user %s: %s", user_id, exc)
        return None
    if rows:
        return str(rows[0].get("id"))
    return None


async def _is_active_sales_rep(user: dict) -> bool:
    """True if the session user has an ACTIVE sales_reps row (by email).

    Rep portals (Accounts/LeadDetail/OnboardingWizard pages) drive the invoice
    and payment-notification routes on behalf of their clients, and reps are
    not `business_users` members of those orgs — so org-membership alone would
    lock them out. An active rep row is the entitlement instead.
    """
    raw = (user.get("email") or "").strip()
    email = raw.lower()
    if not email:
        return False
    try:
        db = get_db()
        # Case-insensitive: sales_reps.email can be stored mixed-case (Supabase
        # auth lowercases the login, but a raw signup insert did not), so
        # eq.<lower> would miss and fail-close a real rep. ilike is
        # case-insensitive; _ and % are ilike wildcards (emails contain _), so
        # narrow with an exact compare in Python.
        rows = await db.select(
            "sales_reps", "id,email,is_active",
            filters={"email": f"ilike.{raw}", "is_active": "eq.true"},
            limit=10,
        )
        return any((r.get("email") or "").strip().lower() == email for r in rows)
    except Exception as e:
        logger.warning("sales_reps lookup failed for %s: %s", email, e)
        return False  # fail closed


async def _enforce_billing_org_access(principal: dict, org_id: str) -> None:
    """Org-scope guard for service-authed billing mutations (June
    require_service_auth cross-tenant BOLA batch).

    Allowed: machine principals (admin key / service token), members of the
    target org (merchant self-serve onboarding), global ADMIN_EMAILS, and
    ACTIVE sales reps. Everyone else — e.g. an ordinary logged-in merchant
    naming ANOTHER org's id — is denied 403.
    """
    if not principal or principal.get("kind") in ("admin", "service"):
        return
    user = principal.get("user") or {}
    try:
        # require_org_member passes members + ADMIN_EMAILS and honors the
        # TENANCY_ENFORCEMENT_DISABLED rollback knob.
        await require_org_member(user, org_id)
        return
    except HTTPException:
        if await _is_active_sales_rep(user):
            return
        raise


# ── Request/Response Models ──

class InvoiceRequest(BaseModel):
    org_id: str
    amount_cents: int
    customer_email: str
    description: str = "Meridian Analytics Subscription"
    due_days: int = 3
    currency: str = "USD"              # "CAD" for Canada portal

    @field_validator("amount_cents")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount_cents must be positive")
        if v > MAX_AMOUNT_CENTS:
            raise ValueError(f"amount_cents exceeds maximum ({MAX_AMOUNT_CENTS})")
        return v


class CancelRequest(BaseModel):
    org_id: str
    reason: str = ""


class SelfCancelRequest(BaseModel):
    """Owner-initiated cancellation from the merchant Settings page.

    org_id is intentionally ABSENT — the org is resolved from the session
    owner, never trusted from the body. reason is optional. talk_first is the
    retention off-ramp: when true the endpoint records NOTHING and cancels
    NOTHING.
    """
    reason: str = ""
    talk_first: bool = False


class UpdatePaymentMethodRequest(BaseModel):
    org_id: str
    customer_email: str
    customer_name: str
    business_name: str


class PaymentNotifyRequest(BaseModel):
    org_id: str
    customer_email: str
    contact_name: str
    business_name: str
    rep_name: str = ""
    rep_email: str = ""


# ── Route handlers ──

@router.post("/create-invoice")
async def create_invoice(req: InvoiceRequest, principal=Depends(require_service_auth)):
    """
    Create a Square Invoice for custom amounts or manual billing.
    Used for non-standard pricing or when the SR sets a custom amount.
    """
    await _enforce_billing_org_access(principal, req.org_id)
    try:
        from src.billing.billing_service import BillingService

        db = get_db()
        service = BillingService(db)

        result = await service.create_invoice(
            org_id=req.org_id,
            amount_cents=req.amount_cents,
            customer_email=req.customer_email,
            description=req.description,
            due_days=req.due_days,
            currency=req.currency,
        )

        if result.success:
            return {
                "invoice_id": result.invoice_id,
                "invoice_url": result.invoice_url,
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)

    except ImportError:
        raise HTTPException(status_code=501, detail="Billing service not yet configured.")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Invoice creation failed")
        raise HTTPException(status_code=500, detail="Invoice creation failed")


# No rep/merchant frontend calls /cancel (verified: zero callers in frontend/src).
# Subscription cancellation is a service/admin operation, so it is admin-locked.
# require_admin_auth still accepts MERIDIAN_SERVICE_TOKEN + admin key for automation.
@router.post("/cancel", dependencies=[Depends(require_admin_auth)])
async def cancel_subscription(req: CancelRequest):
    """Cancel a subscription. Stops future auto-renewals."""
    try:
        from src.billing.billing_service import BillingService

        db = get_db()
        service = BillingService(db)

        success = await service.cancel_subscription(req.org_id, req.reason)

        if success:
            return {"status": "cancelled", "org_id": req.org_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel subscription")

    except ImportError:
        raise HTTPException(status_code=501, detail="Billing service not yet configured.")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Cancellation failed")
        raise HTTPException(status_code=500, detail="Cancellation failed")


@router.post("/self-cancel")
async def self_cancel_subscription(
    req: SelfCancelRequest,
    user: dict = Depends(require_jwt),
):
    """Owner self-serve cancellation (merchant Settings → Cancel account).

    Auth: the authenticated OWNER of the org only. The org is derived from the
    session (businesses.owner_user_id), never from the body — a non-owner
    member or an outsider naming an org is denied 403.

    Flow contract:
      - talk_first=true  → retention off-ramp. Records NOTHING, cancels
        NOTHING. Returns {canceled: false, talk_first: true} so the UI can
        route the owner to support.
      - otherwise → records an append-only subscription_cancellations row
        (timestamp + reason + who), halts renewals via the existing
        billing_service.cancel_subscription path, and emits the commission-halt
        hook. Access-wind-down is RECORDED only unless SUBSCRIPTION_WINDDOWN_ENFORCED.
    """
    org_id = await _resolve_owned_org(user)
    if not org_id:
        # Not the owner of any org (or unverifiable) → cannot cancel.
        raise HTTPException(
            403, "Only the account owner can cancel the subscription.")

    # Retention off-ramp: talk to us first. Record nothing, cancel nothing.
    if req.talk_first:
        logger.info("Self-cancel: owner %s chose talk-first for org %s (no cancellation recorded)",
                    user.get("email"), org_id)
        return {"canceled": False, "talk_first": True, "org_id": org_id}

    db = get_db()
    now = datetime.now(timezone.utc)
    enforced = _winddown_enforced()

    # ── Access wind-down policy (RECORDED here; enforcement gated) ──
    # Proposed: full access to end of paid period → 30-day read-only export
    # window → deactivation. Default (flag OFF) records 'recorded' and makes
    # NO access change.
    access_until = None
    read_only_until = None
    winddown_status = "recorded"
    if enforced:
        sub_rows = []
        try:
            sub_rows = await db.select(
                "subscriptions", filters={"org_id": f"eq.{org_id}"}, limit=1)
        except Exception:
            sub_rows = []
        period_end = None
        if sub_rows:
            period_end = sub_rows[0].get("current_period_end")
        access_until = period_end or now.isoformat()
        try:
            base = datetime.fromisoformat(str(access_until).replace("Z", "+00:00"))
        except Exception:
            base = now
        read_only_until = (base + timedelta(days=WINDDOWN_READONLY_DAYS)).isoformat()
        winddown_status = "active_until_period_end"

    # 1) Record the cancellation (append-only audit) — timestamp + reason + who.
    cancel_row = {
        "org_id": org_id,
        "canceled_by_user_id": user.get("id") or user.get("sub") or "",
        "canceled_by_email": user.get("email") or "",
        "reason": req.reason or "",
        "canceled_at": now.isoformat(),
        "winddown_status": winddown_status,
        "access_until": access_until,
        "read_only_until": read_only_until,
        # Commission-halt hook: mark intent. Wiring to
        # commission_engine.cancel_account(org_id) lands when
        # feat/canada-commission-engine merges — see PR body.
        "commission_halt_requested": True,
    }
    try:
        await db.insert("subscription_cancellations", cancel_row)
    except Exception:
        logger.exception("Failed to record cancellation for org %s", org_id)
        raise HTTPException(500, "Could not record cancellation")

    # 2) Halt renewals via the existing billing service (Square + local status).
    try:
        from src.billing.billing_service import BillingService
        service = BillingService(db)
        await service.cancel_subscription(org_id, req.reason or "owner self-cancel")
    except ImportError:
        logger.warning("Billing service unavailable during self-cancel for %s", org_id)
    except Exception:
        # The cancellation is already recorded; renewal-halt failure is an
        # operator follow-up, not a reason to 500 the owner.
        logger.exception("cancel_subscription failed during self-cancel for %s", org_id)

    # 3) Commission-halt: halt this account's FUTURE (pending) milestones.
    #    Earned/paid rows are NEVER clawed back. Best-effort — the cancellation
    #    is already recorded; a halt hiccup is an operator follow-up, not a 500.
    #    Flag-gated by the same Canada kill-switch as accrual.
    try:
        from src.services.commission_engine import (
            CommissionEngineService,
            canada_commission_live,
        )

        if canada_commission_live():
            halted = await CommissionEngineService(db=db).cancel_account(org_id)
            logger.info("commission halt: %d future milestones halted for %s", halted, org_id)
    except Exception:
        logger.exception("commission cancel_account failed for %s", org_id)

    # 4a) Stop the phone agent — INDEPENDENT safety plane. Done as its own
    #     best-effort step (not folded into reclaim) so that even if the reclaim
    #     below throws, a cancelled merchant's agent is already deactivated and
    #     the Vapi gate declines further calls (no runaway Vapi/Telnyx spend).
    try:
        from src.services.number_pool import deactivate_phone_agent
        await deactivate_phone_agent(db, org_id)
    except Exception:
        logger.exception("phone-agent deactivate failed during self-cancel for %s", org_id)

    # 4b) Reclaim the phone number to the pool for reassignment. The DID (Telnyx
    #     + Vapi binding) is kept — only the assignment is undone, so a new
    #     merchant can be handed this number. Best-effort: the cancellation is
    #     already recorded; a reclaim hiccup is an operator follow-up, not a 500.
    try:
        from src.services.number_pool import release_to_pool
        reclaimed = await release_to_pool(db, org_id)
        if reclaimed:
            logger.info("Self-cancel: reclaimed %s from %s → pool",
                        reclaimed["phone_number"], org_id)
    except Exception:
        logger.exception("number reclaim failed during self-cancel for %s", org_id)

    logger.info("Self-cancel recorded for org %s by owner %s (winddown_enforced=%s)",
                org_id, user.get("email"), enforced)
    return {
        "canceled": True,
        "talk_first": False,
        "org_id": org_id,
        "canceled_at": now.isoformat(),
        "winddown_enforced": enforced,
        "winddown_status": winddown_status,
    }


async def _stripe_billing_state(db, org_id: str) -> dict | None:
    """Billing status from the org's Stripe subscription.

    The checkout webhook (_activate_from_checkout) writes plan_tier /
    payment_status / stripe_customer_id / stripe_subscription_id to
    organizations.metadata. Returns None when the org has no Stripe subscription
    yet, so the caller falls back to the legacy Square subscriptions table.
    """
    import json as _json
    try:
        rows = await db.select("organizations", "metadata",
                               filters={"id": f"eq.{org_id}"}, limit=1)
    except Exception:
        return None
    if not rows:
        return None
    meta = rows[0].get("metadata") or {}
    if isinstance(meta, str):
        try:
            meta = _json.loads(meta)
        except Exception:
            meta = {}
    sub_id = meta.get("stripe_subscription_id")
    pay_status = meta.get("payment_status")
    if not (sub_id or pay_status):
        return None
    out = {
        "provider": "stripe",
        "status": pay_status or ("active" if sub_id else "pending_payment"),
        "tier": meta.get("plan_tier"),
        "stripe_customer_id": meta.get("stripe_customer_id"),
        "monthly_price_cents": None,
        "current_period_end": None,
        "setup_fee_cents": meta.get("setup_fee_cents", 0) or 0,
        "manageable": bool(meta.get("stripe_customer_id")),
    }
    # Enrich with live Stripe detail — real status, next renewal, amount.
    if sub_id and STRIPE_SECRET_KEY:
        try:
            sub_obj = stripe.Subscription.retrieve(
                sub_id, api_key=STRIPE_SECRET_KEY, expand=["items.data.price"])
            # StripeObject intercepts .get via __getattr__ — use a plain dict.
            sub = sub_obj.to_dict()
            out["status"] = sub["status"]
            items = (sub.get("items") or {}).get("data") or []
            # current_period_end moved to the item level in newer Stripe API
            # versions; read either place.
            cpe = sub.get("current_period_end") or (
                items[0].get("current_period_end") if items else None)
            if cpe:
                out["current_period_end"] = datetime.fromtimestamp(
                    cpe, tz=timezone.utc).isoformat()
            if items:
                out["monthly_price_cents"] = items[0]["price"].get("unit_amount")
        except Exception as e:  # noqa: BLE001 — enrichment is best-effort
            logger.warning("stripe subscription retrieve failed for %s: %s", org_id, e)
    return out


class _BillingPortalRequest(BaseModel):
    return_path: str = "/settings"


@router.post("/portal/{org_id}")
async def open_billing_portal(org_id: str, req: _BillingPortalRequest,
                              user: dict = Depends(require_jwt)):
    """A Stripe Customer Portal link so the merchant manages their own
    subscription (card on file, invoices, cancel). Needs the stripe customer set
    on the org when they paid the subscribe-link."""
    await _enforce_billing_org_access({"kind": "user", "user": user}, org_id)
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503, "billing not configured")
    state = await _stripe_billing_state(get_db(), org_id)
    customer = (state or {}).get("stripe_customer_id")
    if not customer:
        raise HTTPException(404, "no Stripe customer on file yet")
    try:
        sess = stripe.billing_portal.Session.create(
            customer=customer,
            return_url=f"{_FRONTEND_URL}{req.return_path}",
            api_key=STRIPE_SECRET_KEY,
        )
        return {"url": sess.url}
    except Exception as e:  # noqa: BLE001
        logger.warning("stripe billing portal failed for %s: %s", org_id, e)
        raise HTTPException(502, "could not open the billing portal")


@router.get("/status/{org_id}")
async def get_billing_status(org_id: str, user: dict = Depends(require_jwt)):
    """Get current subscription/billing status for an organization.

    BOLA guard: an authenticated caller may only read the billing status of an
    org they belong to (member / owner / ADMIN_EMAILS / active sales rep) — the
    same plane every billing mutation in this file uses. Without this, any
    logged-in user could read any org's subscription tier/price/rep by UUID.
    """
    await _enforce_billing_org_access({"kind": "user", "user": user}, org_id)
    try:
        db = get_db()

        # Stripe is the source of truth now: the checkout webhook writes the
        # subscription state to the org record. Prefer it; the subscriptions
        # table is legacy Square and is empty for Stripe merchants.
        stripe_state = await _stripe_billing_state(db, org_id)
        if stripe_state:
            return stripe_state

        try:
            rows = await db.select(
                "subscriptions",
                filters={"org_id": f"eq.{org_id}"},
                limit=1,
            )
        except Exception:
            return {"status": "none", "tier": None}

        if rows:
            sub = rows[0]
            metadata = sub.get("metadata") or {}
            return {
                "status": sub.get("status"),
                "tier": sub.get("tier"),
                "monthly_price_cents": sub.get("monthly_price_cents"),
                "current_period_start": sub.get("current_period_start"),
                "current_period_end": sub.get("current_period_end"),
                "auto_renew": metadata.get("auto_renew", True),
                "canceled_at": sub.get("canceled_at"),
                "setup_fee_cents": metadata.get("setup_fee_cents", 0),
                "first_month_free": metadata.get("first_month_free", False),
                "rep_id": metadata.get("rep_id", ""),
                "rep_name": metadata.get("rep_name", ""),
            }
        else:
            return {"status": "none", "tier": None}

    except RuntimeError:
        return {"status": "unavailable", "tier": None}
    except Exception:
        logger.exception(f"Status check failed for org {org_id}")
        raise HTTPException(status_code=500, detail="Could not retrieve billing status")


# ── Fee allocation mode (rep-set, owner-read-only + change requests) ──

_FEE_MODES = ("business_pays", "split_5050", "customer_pays")
_FEE_MODE_LABELS = {
    "business_pays": "Business pays the fee",
    "split_5050": "Split 50/50 with the customer",
    "customer_pays": "Customer pays the fee",
    None: "Standard (default)",
}


class FeeChangeRequestBody(BaseModel):
    org_id: str
    requested_mode: str
    reason: str = ""

    @field_validator("requested_mode")
    @classmethod
    def _valid_mode(cls, v: str) -> str:
        if v not in _FEE_MODES:
            raise ValueError(f"requested_mode must be one of {_FEE_MODES}")
        return v


@router.get("/fee-mode/{org_id}")
async def get_fee_mode(org_id: str, user: dict = Depends(require_jwt)):
    """Owner-facing READ-ONLY view of the merchant's fee allocation mode. The
    mode is set by the sales rep at close and cannot be changed here — the owner
    can only file a change request (POST /fee-mode/change-request)."""
    # require_jwt yields the raw user dict — wrap it in the principal shape
    # _enforce_billing_org_access expects, else the org owner is denied 403.
    await _enforce_billing_org_access({"kind": "user", "user": user}, org_id)
    db = get_db()
    mode = None
    try:
        rows = await db.select(
            "phone_agent_config", "fee_allocation_mode",
            filters={"merchant_id": f"eq.{org_id}"}, limit=1,
        )
        if rows:
            mode = rows[0].get("fee_allocation_mode")
    except Exception:  # noqa: BLE001 — fail-open to the legacy/default label
        logger.warning("fee-mode lookup failed for %s", org_id, exc_info=True)
    if mode not in _FEE_MODES:
        mode = None
    return {
        "org_id": org_id,
        "fee_allocation_mode": mode,
        "label": _FEE_MODE_LABELS.get(mode, _FEE_MODE_LABELS[None]),
        "editable": False,  # owner cannot change it — rep-set + fixed
    }


@router.post("/fee-mode/change-request")
async def create_fee_change_request(
    req: FeeChangeRequestBody, user: dict = Depends(require_jwt)
):
    """File an owner-initiated fee-mode change request (a simple ticket). Inserts
    a fee_change_requests row (HQ/service reads all) and drops an in-app
    notification. HQ actions it out of band — the owner cannot self-serve the
    change. Reuses the existing notification path; no email is sent from here."""
    await _enforce_billing_org_access({"kind": "user", "user": user}, req.org_id)
    db = get_db()

    # Current mode for the audit record (best-effort; NULL = legacy/default).
    current_mode = None
    try:
        rows = await db.select(
            "phone_agent_config", "fee_allocation_mode",
            filters={"merchant_id": f"eq.{req.org_id}"}, limit=1,
        )
        if rows and rows[0].get("fee_allocation_mode") in _FEE_MODES:
            current_mode = rows[0]["fee_allocation_mode"]
    except Exception:  # noqa: BLE001
        logger.warning("fee-mode current lookup failed for %s", req.org_id, exc_info=True)

    request_id = str(uuid4())
    try:
        await db.insert("fee_change_requests", {
            "id": request_id,
            "org_id": req.org_id,
            "current_mode": current_mode,
            "requested_mode": req.requested_mode,
            "reason": (req.reason or "").strip() or None,
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:  # noqa: BLE001
        logger.error("fee_change_requests insert failed for %s: %s", req.org_id, e)
        raise HTTPException(status_code=500, detail="Could not file the change request")

    # Notify HQ via the existing in-app notification rail (no email built here).
    try:
        from .webhooks import _send_notification
        await _send_notification(
            org_id=req.org_id,
            title="Fee handling change requested",
            body=(f"Requested change to '{_FEE_MODE_LABELS.get(req.requested_mode)}' "
                  f"(from '{_FEE_MODE_LABELS.get(current_mode)}'). "
                  f"{('Reason: ' + req.reason.strip()) if req.reason.strip() else ''}").strip(),
            priority="normal",
        )
    except Exception:  # noqa: BLE001 — notification is best-effort; the row is the record
        logger.warning("fee-change notification failed for %s", req.org_id, exc_info=True)

    return {"ok": True, "request_id": request_id, "status": "open",
            "requested_mode": req.requested_mode}


@router.post("/update-payment-method")
async def update_payment_method(req: UpdatePaymentMethodRequest, principal=Depends(require_service_auth)):
    """
    Generate a new Square invoice so the customer can update their card on file.
    Creates a fresh invoice at the current subscription price with card storage enabled.
    Returns the invoice URL to send to the customer.
    """
    await _enforce_billing_org_access(principal, req.org_id)
    try:
        from src.billing.billing_service import BillingService

        db = get_db()

        rows = await db.select("subscriptions", filters={"org_id": f"eq.{req.org_id}"}, limit=1)
        amount_cents = 25000
        plan = "standard"
        sub_data = rows[0] if rows else {}
        if sub_data:
            amount_cents = sub_data.get("monthly_price_cents", 25000)
            plan = sub_data.get("tier", "standard")

        service = BillingService(db)
        inv_result = await service.create_invoice(
            org_id=req.org_id,
            amount_cents=amount_cents,
            customer_email=req.customer_email,
            description=f"Meridian Analytics - {plan.title()} Plan (Payment Update)",
            due_days=7,
            store_card=True,
        )

        if inv_result.success:
            meta = sub_data.get("metadata") or {}
            import json as json_mod
            updated_meta = {
                **meta,
                "update_invoice_id": inv_result.invoice_id,
                "update_invoice_url": inv_result.invoice_url,
                "update_requested_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.update("subscriptions", {"metadata": json_mod.dumps(updated_meta)}, filters={"org_id": f"eq.{req.org_id}"})

            return {
                "ok": True,
                "invoice_url": inv_result.invoice_url,
                "invoice_id": inv_result.invoice_id,
                "amount_cents": amount_cents,
            }
        else:
            raise HTTPException(400, inv_result.error or "Could not create payment update link")

    except ImportError:
        raise HTTPException(501, "Billing service not configured")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Payment method update failed")
        raise HTTPException(500, "Could not create payment update link")


@router.post("/notify-payment-failed")
async def notify_payment_failed(req: PaymentNotifyRequest, principal=Depends(require_service_auth)):
    """
    Send a 'payment failed' email to the customer with a link to update their card.
    Auto-generates a new invoice link if one doesn't already exist.
    """
    await _enforce_billing_org_access(principal, req.org_id)
    try:
        db = get_db()
        rows = await db.select("subscriptions", filters={"org_id": f"eq.{req.org_id}"}, limit=1)
        sub_data = rows[0] if rows else {}

        meta = sub_data.get("metadata") or {} if sub_data else {}
        update_url = meta.get("update_invoice_url") or meta.get("renewal_invoice_url")
        amount_cents = sub_data.get("monthly_price_cents", 25000) if sub_data else 25000

        if not update_url:
            try:
                from src.billing.billing_service import BillingService
                service = BillingService(db)
                inv = await service.create_invoice(
                    org_id=req.org_id,
                    amount_cents=amount_cents,
                    customer_email=req.customer_email,
                    description="Meridian Analytics - Payment Update",
                    due_days=7,
                    store_card=True,
                )
                if inv.success:
                    update_url = inv.invoice_url
            except ImportError:
                pass

        if not update_url:
            update_url = "https://meridian.tips/canada/login"

        from ...email.send import send_payment_failed
        amount_display = f"${amount_cents / 100:.2f}"
        result = await send_payment_failed(
            to=req.customer_email,
            business_name=req.business_name,
            contact_name=req.contact_name,
            amount=amount_display,
            update_url=update_url,
            rep_name=req.rep_name,
            org_id=req.org_id,
        )

        email_sent = result.get("status") == "sent" or result.get("id") is not None
        return {"ok": True, "email_sent": email_sent, "update_url": update_url}

    except RuntimeError:
        raise HTTPException(503, "Database not available")
    except Exception:
        logger.exception("Payment failed notification error")
        raise HTTPException(500, "Could not send payment notification")


@router.post("/process-renewals", dependencies=[Depends(require_admin)])
async def process_renewals():
    """
    Manually trigger subscription renewal processing.
    Creates Square invoices for any subscriptions past their period end.
    Normally run by daily Celery beat task.
    """
    try:
        from src.billing.billing_service import BillingService

        db = get_db()
        service = BillingService(db)
        await service.process_renewals()
        return {"status": "ok"}
    except ImportError:
        raise HTTPException(status_code=501, detail="Billing service not configured.")
    except Exception:
        logger.exception("Manual renewal processing failed")
        raise HTTPException(status_code=500, detail="Renewal processing failed")


@router.get("/invoice-url/{org_id}")
async def get_invoice_url(org_id: str, user: dict = Depends(require_jwt)):
    """
    Get the latest invoice URL for an org — used for in-platform pay buttons.
    Returns the most recent setup or recurring invoice link.
    """
    # BOLA guard: an authenticated caller may only read invoice links for an org
    # they belong to — the SAME plane every other billing route in this file
    # uses. Without this, any logged-in user could pull any org's invoice URL +
    # subscription/payment state by UUID (CONFIRMED BOLA, 2026-07-22).
    await _enforce_billing_org_access({"kind": "user", "user": user}, org_id)
    try:
        db = get_db()
        try:
            rows = await db.select(
                "subscriptions",
                filters={"org_id": f"eq.{org_id}"},
                limit=1,
            )
        except Exception:
            raise HTTPException(404, "No subscription found")

        if not rows:
            raise HTTPException(404, "No subscription found")

        meta = rows[0].get("metadata") or {}

        renewal_url = meta.get("renewal_invoice_url")
        setup_url = meta.get("setup_invoice_url")
        recurring_url = meta.get("recurring_invoice_url")

        invoice_url = renewal_url or recurring_url or setup_url

        if not invoice_url:
            raise HTTPException(404, "No invoice URL available")

        return {
            "invoice_url": invoice_url,
            "org_id": org_id,
            "type": "renewal" if renewal_url else ("recurring" if recurring_url else "setup"),
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Invoice URL lookup failed for {org_id}")
        raise HTTPException(500, "Could not retrieve invoice URL")


@router.post("/check-trials", dependencies=[Depends(require_admin)])
async def check_expiring_trials():
    """
    Check for trials expiring within the next 3 days and send reminder emails.
    Called by a daily cron job or admin trigger.
    """
    try:
        db = get_db()
        now = datetime.now(timezone.utc)

        for days_out in (3, 1):
            target = now + timedelta(days=days_out)
            target_date = target.strftime("%Y-%m-%d")

            try:
                rows = await db.select(
                    "subscriptions",
                    filters={
                        "status": "eq.trialing",
                        "current_period_end": f"gte.{target_date}T00:00:00Z",
                    },
                )
                rows = [r for r in rows if r.get("current_period_end", "") <= f"{target_date}T23:59:59Z"]
            except Exception as e:
                logger.warning(f"Trial check query failed: {e}")
                rows = []

            for sub in rows:
                email = sub.get("contact_email") or sub.get("email")
                if not email:
                    continue
                try:
                    from ...email.send import send_trial_expiring
                    name = (sub.get("owner_name") or sub.get("name") or "").split()[0] or "there"
                    await send_trial_expiring(
                        to=email,
                        first_name=name,
                        days_remaining=days_out,
                        org_id=sub.get("org_id"),
                    )
                    logger.info(f"Sent trial expiring email ({days_out}d) to {email}")
                except Exception as e:
                    logger.warning(f"Trial expiring email failed for {email}: {e}")

        return {"status": "ok"}
    except Exception:
        logger.exception("Trial check failed")
        raise HTTPException(status_code=500, detail="Trial check failed")


@router.post("/webhook")
async def handle_billing_webhook(request: Request):
    """
    Handle Square payment webhook events for subscription billing.

    Key events:
    - payment.completed → Activate subscription, record setup fee commission
    - payment.updated → Handle Square renamed event (same as completed if status=COMPLETED)
    - invoice.payment_made → Record renewal payment
    """
    try:
        raw_body = await request.body()
        sig_key = os.environ.get("SQUARE_WEBHOOK_SIGNATURE_KEY", "")
        if not sig_key:
            logger.warning("SQUARE_WEBHOOK_SIGNATURE_KEY not configured — rejecting webhook")
            return Response(status_code=503)
        signature = request.headers.get("x-square-hmacsha256-signature", "")
        # Must be the exact URL Square signs against; str(request.url)
        # reconstructs the internal/http URL behind the Railway proxy and
        # always mismatches.
        from ...config import app as _app_config
        notification_url = _app_config.billing_webhook_url
        combined = notification_url.encode("utf-8") + raw_body
        expected = hmac.new(
            key=sig_key.encode("utf-8"),
            msg=combined,
            digestmod=hashlib.sha256,
        ).digest()
        import base64
        expected_b64 = base64.b64encode(expected).decode("utf-8")
        if not hmac.compare_digest(expected_b64, signature):
            logger.warning("Billing webhook signature mismatch")
            return Response(status_code=403)

        import json as json_mod
        body = json_mod.loads(raw_body)
        event_type = body.get("type", "")
        data = body.get("data", {}).get("object", {})

        logger.info(f"Billing webhook: {event_type}")

        db = get_db()
        import json as json_mod

        if event_type in ("payment.completed", "payment.updated"):
            payment = data.get("payment", {})

            if event_type == "payment.updated" and payment.get("status") != "COMPLETED":
                return {"status": "ignored", "reason": "payment not completed yet"}

            order_id = payment.get("order_id", "")

            if order_id:
                try:
                    # Server-side narrowing: only statuses the activation logic
                    # acts on. Matching still scans metadata.square_order_id in
                    # Python — filtering that server-side needs a verified jsonb
                    # column + index (follow-up).
                    subs = await db.select("subscriptions", filters={
                        "status": "in.(active,trialing,pending_payment,past_due)",
                    })
                except Exception:
                    subs = []
                for sub in subs:
                    meta = sub.get("metadata") or {}
                    if meta.get("square_order_id") == order_id:
                        updated_meta = {
                            **meta,
                            "payment_completed_at": datetime.now(timezone.utc).isoformat(),
                            "square_payment_id": payment.get("id"),
                        }

                        if meta.get("first_month_free"):
                            updated_meta["trial_status"] = "active"

                        try:
                            await db.update("subscriptions", {
                                "status": "active",
                                "metadata": json_mod.dumps(updated_meta),
                            }, filters={"id": f"eq.{sub['id']}"})
                        except Exception as e:
                            logger.warning(f"Failed to activate subscription: {e}")

                        setup_fee = meta.get("setup_fee_cents", 0)
                        rep_id = meta.get("setup_fee_rep_id") or meta.get("rep_id")
                        if setup_fee and rep_id:
                            try:
                                await db.insert("commissions", {
                                    "rep_id": rep_id,
                                    "org_id": sub["org_id"],
                                    "type": "setup_fee",
                                    "amount_cents": setup_fee,
                                    "commission_rate": 1.0,
                                    "commission_cents": setup_fee,
                                    "status": "earned",
                                    "notes": f"Setup fee for {sub.get('tier', 'standard')} plan",
                                })
                                logger.info(f"Recorded setup fee commission: ${setup_fee/100:.2f} for rep {rep_id}")
                            except Exception as e:
                                logger.warning(f"Failed to record setup fee commission: {e}")

                        logger.info(f"Activated subscription for order {order_id}")

                        recipient = sub.get("contact_email") or sub.get("email")
                        if recipient:
                            try:
                                from ...email.send import send_payment_receipt
                                amount_cents = payment.get("amount_money", {}).get("amount", sub.get("monthly_price_cents", 0))
                                await send_payment_receipt(
                                    to=recipient,
                                    business_name=sub.get("business_name", "Your Business"),
                                    plan_name=sub.get("tier", "Standard").title(),
                                    amount=f"${amount_cents / 100:.2f}",
                                    period="Monthly",
                                    invoice_url=payment.get("receipt_url", ""),
                                    org_id=sub.get("org_id"),
                                )
                            except Exception as e:
                                logger.warning(f"Payment receipt email failed: {e}")
                        break

        elif event_type == "invoice.payment_made":
            invoice = data.get("invoice", {})
            invoice_id = invoice.get("id", "")

            if invoice_id:
                try:
                    # Server-side narrowing (see payment.completed branch above).
                    subs = await db.select("subscriptions", filters={
                        "status": "in.(active,trialing,pending_payment,past_due)",
                    })
                except Exception:
                    subs = []
                for sub in subs:
                    meta = sub.get("metadata") or {}
                    matched = (
                        meta.get("setup_invoice_id") == invoice_id
                        or meta.get("renewal_invoice_id") == invoice_id
                    )
                    if not matched:
                        continue

                    now = datetime.now(timezone.utc)

                    if sub.get("status") in ("pending_payment", "past_due"):
                        try:
                            await db.update("subscriptions", {
                                "status": "active",
                                "metadata": json_mod.dumps({
                                    **meta,
                                    "payment_completed_at": now.isoformat(),
                                }),
                            }, filters={"id": f"eq.{sub['id']}"})
                            logger.info(f"Activated subscription from invoice {invoice_id}")
                        except Exception as e:
                            logger.warning(f"Failed to activate subscription: {e}")

                    if meta.get("awaiting_auto_subscription") and not meta.get("square_subscription_id"):
                        try:
                            from src.billing.billing_service import BillingService
                            billing = BillingService(db)
                            amount = meta.get("target_monthly_cents") or sub.get("monthly_price_cents", 0)

                            sub_result = await billing.create_auto_subscription(
                                org_id=sub["org_id"],
                                amount_cents=amount,
                                customer_email=sub.get("contact_email") or sub.get("email", ""),
                                customer_name=sub.get("owner_name", ""),
                                business_name=sub.get("business_name", ""),
                                plan=sub.get("tier", "starter"),
                            )

                            if sub_result.success:
                                await db.update("subscriptions", {
                                    "metadata": json_mod.dumps({
                                        **meta,
                                        "square_subscription_id": sub_result.subscription_id,
                                        "auto_billing": True,
                                        "awaiting_auto_subscription": False,
                                        "subscription_start_date": sub_result.start_date,
                                        "payment_completed_at": now.isoformat(),
                                    }),
                                }, filters={"id": f"eq.{sub['id']}"})
                                logger.info(
                                    f"Auto-subscription created for org {sub['org_id']}: "
                                    f"{sub_result.subscription_id}, starts {sub_result.start_date}"
                                )
                            else:
                                logger.warning(
                                    f"Auto-subscription failed for org {sub['org_id']}: "
                                    f"{sub_result.error} — will fall back to cron renewals"
                                )
                        except Exception as e:
                            logger.warning(f"Auto-subscription setup error: {e}")

                    break

        return {"status": "ok"}

    except RuntimeError:
        # Return 5xx so Square retries the event instead of dropping it.
        logger.error("Database not available for billing webhook")
        return Response(status_code=500)
    except Exception:
        logger.exception("Billing webhook processing failed")
        return Response(status_code=500)


# ── Fee parity: billing terms + reconciliation ──


class TermsOverrideRequest(BaseModel):
    """Admin override of a merchant's billing terms. Supersedes the active
    merchant_billing_terms row (never updates in place) — the row history is
    the audit trail. override_reason is mandatory."""

    override_reason: str
    plan_tier: str | None = None
    monthly_fee_cents: int | None = None
    order_fee_cents: int | None = None
    call_overage_cents_per_min: int | None = None
    included_call_min: int | None = None

    @field_validator("override_reason")
    @classmethod
    def reason_required(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) < 5:
            raise ValueError("override_reason is required (min 5 characters) — it is the audit record")
        return v

    @field_validator("monthly_fee_cents", "order_fee_cents",
                     "call_overage_cents_per_min", "included_call_min")
    @classmethod
    def non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("fee values must be >= 0")
        return v


@router.post("/terms/{merchant_id}/override")
async def override_billing_terms(
    merchant_id: str,
    req: TermsOverrideRequest,
    admin: dict = Depends(require_admin_jwt),
):
    """Admin-only manual correction of a merchant's billing terms.

    Merges the provided fields over the current active terms (or, when the
    merchant has none, over nothing — only the provided fields are recorded),
    then supersedes the old row and inserts the new one. At least one fee
    field must be provided."""
    from ...billing.fee_terms import FEE_TERM_FIELDS, get_active_terms, set_merchant_billing_terms

    patch = {
        "plan_tier": (req.plan_tier or "").strip().lower() or None,
        "monthly_fee_cents": req.monthly_fee_cents,
        "order_fee_cents": req.order_fee_cents,
        "call_overage_cents_per_min": req.call_overage_cents_per_min,
        "included_call_min": req.included_call_min,
    }
    if all(v is None for v in patch.values()):
        raise HTTPException(400, "Provide at least one fee field to override")

    db = get_db()
    current = await get_active_terms(db, merchant_id) or {}
    terms = {f: current.get(f) for f in FEE_TERM_FIELDS}
    terms.update({k: v for k, v in patch.items() if v is not None})

    row = await set_merchant_billing_terms(
        db, merchant_id, terms,
        source_lead_id=current.get("source_lead_id"),
        source_market=current.get("source_market"),
        created_by=admin.get("email", ""),
        override_reason=req.override_reason,
    )
    if row is None:
        raise HTTPException(502, "Could not record billing terms (is migration 20260716_merchant_billing_terms applied?)")
    logger.info("billing terms OVERRIDE for %s by %s: %s", merchant_id, admin.get("email"), req.override_reason)
    return {"ok": True, "merchant_id": merchant_id, "terms": row}


@router.get("/reconciliation")
async def billing_reconciliation(_admin: dict = Depends(require_admin_jwt)):
    """Pre-invoice fee reconciliation: for every merchant with a live
    subscription, diff the contracted terms (merchant_billing_terms, falling
    back to the closed lead) against what live billing actually applies.
    Zero mismatches = healthy."""
    from ...billing.fee_reconciliation import reconcile_all

    return await reconcile_all(get_db())
