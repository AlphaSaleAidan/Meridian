"""
Billing Service — Square-based subscription billing for Meridian.

Handles:
  - Creating Square checkout links for initial payment
  - Creating Square invoices for custom amounts
  - Recurring billing (monthly auto-charge)
  - Subscription lifecycle (create, renew, cancel)
  - 3-month auto-renewal cycles
  - Setup fees (one-time line items)
  - First-month-free (Square discount)

Uses Square catalog items (US canonical tiers — see billing/fee_terms.py):
  - $250/month (Standard)
  - $350/month (Premium)
  - $500/month (Command)
  - $65/week (weekly plan)
  - Custom amounts via invoice API
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import httpx

from .fee_terms import CANONICAL_FEE_TERMS

logger = logging.getLogger("meridian.billing")

SQUARE_BASE = os.getenv("SQUARE_BASE_URL", "https://connect.squareup.com")
SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN", "")
SQUARE_LOCATION_ID = os.getenv("SQUARE_LOCATION_ID", "")
SQUARE_APP_ID = os.getenv("SQUARE_APP_ID", "sq0idp-3yhWe5-jCcvTFnilu22dtg")

CATALOG_ITEMS = {
    "standard_monthly": os.getenv("SQUARE_ITEM_250_MONTHLY", ""),
    "premium_monthly": os.getenv("SQUARE_ITEM_500_MONTHLY", ""),
    "command_monthly": os.getenv("SQUARE_ITEM_1000_MONTHLY", ""),
    "weekly": os.getenv("SQUARE_ITEM_65_WEEKLY", ""),
}

# Plan tier pricing (cents) — DERIVED from the canonical US fee schedule
# (fee_terms.CANONICAL_FEE_TERMS) so it can never drift from the contracted
# tiers. A hardcoded copy previously read premium $500 / command $1,000 vs the
# canonical $350 / $500 — a ~43% overcharge for anything routed through here.
# 'weekly' has no canonical tier (billed via the invoice API) and stays literal.
PLAN_PRICES = {
    tier: CANONICAL_FEE_TERMS["us"][tier]["monthly_fee_cents"]
    for tier in ("standard", "premium", "command")
}
PLAN_PRICES["weekly"] = 6500  # $65/wk

# Map plan names to catalog keys
PLAN_CATALOG_KEY = {
    "standard": "standard_monthly",
    "premium": "premium_monthly",
    "command": "command_monthly",
    "weekly": "weekly",
}


@dataclass
class InvoiceResult:
    success: bool = False
    invoice_id: Optional[str] = None
    invoice_url: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SubscriptionResult:
    success: bool = False
    subscription_id: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    error: Optional[str] = None


class BillingService:

    def __init__(self, db_client):
        self.db = db_client
        self.http = httpx.AsyncClient(
            base_url=SQUARE_BASE,
            headers={
                "Authorization": f"Bearer {SQUARE_ACCESS_TOKEN}",
                "Content-Type": "application/json",
                "Square-Version": "2024-01-18",
            },
            timeout=30.0,
        )

    # ── Invoices (one-time charges, setup fees) ──

    async def create_invoice(
        self,
        org_id: str,
        amount_cents: int,
        customer_email: str,
        description: str = "Meridian Analytics Subscription",
        due_days: int = 3,
        store_card: bool = False,
        currency: str = "USD",
        idempotency_key: Optional[str] = None,
    ) -> InvoiceResult:
        """
        Create a Square Invoice. When store_card=True, the customer's payment
        method is saved on file for future automatic charges.

        Pass a deterministic idempotency_key (e.g. "renewal-{sub_id}-{period_end}")
        when retries must NOT create a second invoice; defaults to a random key.
        """
        try:
            if idempotency_key is None:
                idempotency_key = str(uuid4())

            customer_id = await self._get_or_create_customer(
                customer_email, customer_email.split("@")[0], ""
            )

            order_resp = await self.http.post("/v2/orders", json={
                "idempotency_key": f"{idempotency_key}-order",
                "order": {
                    "location_id": SQUARE_LOCATION_ID,
                    "line_items": [{
                        "name": description,
                        "quantity": "1",
                        "base_price_money": {"amount": amount_cents, "currency": currency},
                    }],
                },
            })
            order_data = order_resp.json()
            order_id = order_data.get("order", {}).get("id")

            if not order_id:
                return InvoiceResult(error="Failed to create order for invoice")

            due_date = (datetime.now(timezone.utc) + timedelta(days=due_days)).strftime("%Y-%m-%d")

            recipient = {"customer_id": customer_id} if customer_id else {"email_address": customer_email}

            invoice_body = {
                "location_id": SQUARE_LOCATION_ID,
                "order_id": order_id,
                "primary_recipient": recipient,
                "payment_requests": [{
                    "request_type": "BALANCE",
                    "due_date": due_date,
                    "automatic_payment_source": "NONE",
                    "reminders": [{
                        "relative_scheduled_days": -1,
                        "message": f"Reminder: Your Meridian Analytics payment of ${amount_cents / 100:.2f} is due tomorrow.",
                    }],
                }],
                "delivery_method": "EMAIL",
                "title": "Meridian Analytics",
                "description": description,
                "accepted_payment_methods": {
                    "card": True,
                    "square_gift_card": False,
                    "bank_account": True,
                },
            }

            if store_card:
                invoice_body["store_payment_method_enabled"] = True

            invoice_resp = await self.http.post("/v2/invoices", json={
                "idempotency_key": idempotency_key,
                "invoice": invoice_body,
            })

            inv_data = invoice_resp.json()
            invoice = inv_data.get("invoice", {})

            if invoice.get("id"):
                pub_resp = await self.http.post(f"/v2/invoices/{invoice['id']}/publish", json={
                    "version": invoice.get("version", 0),
                    "idempotency_key": f"{idempotency_key}-publish",
                })
                pub_data = pub_resp.json()
                published = pub_data.get("invoice", invoice)

                return InvoiceResult(
                    success=True,
                    invoice_id=invoice["id"],
                    invoice_url=published.get("public_url") or invoice.get("public_url"),
                )
            else:
                errors = inv_data.get("errors", [])
                return InvoiceResult(error=errors[0].get("detail") if errors else "Invoice creation failed")

        except Exception as e:
            logger.exception(f"Invoice creation failed for org {org_id}")
            return InvoiceResult(error=str(e))

    # ── Square Subscriptions (auto-recurring) ──

    async def create_auto_subscription(
        self,
        org_id: str,
        amount_cents: int,
        customer_email: str,
        customer_name: str,
        business_name: str,
        plan: str = "starter",
        currency: str = "USD",
        start_date: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> SubscriptionResult:
        """
        Create a Square Subscription for automatic monthly billing.
        Requires the customer to already have a card on file (stored during
        initial invoice payment).

        Square handles all recurring charges, retries, and dunning from here.

        Args:
            start_date: First billing date ("YYYY-MM-DD"). Defaults to 30 days
                from now (correct after an initial month was just paid). Pass
                today's date when the period being billed starts immediately
                (e.g. renewals).
            idempotency_key: Deterministic key for retry safety; defaults to
                a random key.
        """
        try:
            customer_id = await self._get_or_create_customer(
                customer_email, customer_name, business_name
            )
            if not customer_id:
                return SubscriptionResult(error="Could not find/create Square customer")

            card_id = await self._get_card_on_file(customer_id)
            if not card_id:
                return SubscriptionResult(error="No card on file — customer must pay setup invoice first")

            plan_variation_id = await self._get_or_create_subscription_plan(amount_cents, plan, currency)
            if not plan_variation_id:
                return SubscriptionResult(error="Could not create subscription plan in Square catalog")

            if start_date is None:
                start_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")

            resp = await self.http.post("/v2/subscriptions", json={
                "idempotency_key": idempotency_key or str(uuid4()),
                "location_id": SQUARE_LOCATION_ID,
                "plan_variation_id": plan_variation_id,
                "customer_id": customer_id,
                "card_id": card_id,
                "start_date": start_date,
                "timezone": "America/New_York",
                "source": {"name": "Meridian Analytics"},
            })

            data = resp.json()
            sub = data.get("subscription", {})

            if sub.get("id"):
                logger.info(f"Created Square subscription {sub['id']} for org {org_id}, starts {start_date}")
                return SubscriptionResult(
                    success=True,
                    subscription_id=sub["id"],
                    status=sub.get("status"),
                    start_date=start_date,
                )
            else:
                errors = data.get("errors", [])
                error_msg = errors[0].get("detail") if errors else "Subscription creation failed"
                logger.error(f"Square subscription error for org {org_id}: {error_msg}")
                return SubscriptionResult(error=error_msg)

        except Exception as e:
            logger.exception(f"Subscription creation failed for org {org_id}")
            return SubscriptionResult(error=str(e))

    async def cancel_subscription(self, org_id: str, reason: str = "") -> bool:
        """Cancel a subscription. Stops future auto-renewals and Square subscription."""
        try:
            now = datetime.now(timezone.utc)

            rows = await self.db.select("subscriptions", filters={
                "org_id": f"eq.{org_id}", "status": "eq.active",
            }, limit=1)

            square_cancel_ok = True  # nothing to cancel at Square by default
            if rows:
                sub = rows[0]
                meta = sub.get("metadata") or {}
                square_sub_id = meta.get("square_subscription_id")

                if square_sub_id:
                    resp = await self.http.post(
                        f"/v2/subscriptions/{square_sub_id}/cancel", json={}
                    )
                    if resp.status_code in (200, 404):
                        logger.info(f"Cancelled Square subscription {square_sub_id}")
                    else:
                        square_cancel_ok = False
                        logger.error(
                            f"Square subscription cancel returned {resp.status_code} "
                            f"for {square_sub_id} — NOT marking canceled locally "
                            f"(Square will keep billing until resolved)"
                        )

            # Stripe merchants keep their subscription state on
            # organizations.metadata, NOT in this (Square-era) subscriptions
            # table — so the Square block above finds nothing and, without this,
            # "cancel" would leave the live Stripe subscription auto-renewing and
            # the merchant billed every month after they cancelled. Cancel it at
            # period end: future charges stop, the current paid period is
            # honoured, and Stripe fires customer.subscription.deleted at the end.
            stripe_cancel_ok = True
            try:
                org_rows = await self.db.select(
                    "organizations", "metadata",
                    filters={"id": f"eq.{org_id}"}, limit=1)
                ometa = (org_rows[0].get("metadata") if org_rows else {}) or {}
                if isinstance(ometa, str):
                    import json as _json
                    ometa = _json.loads(ometa or "{}")
                stripe_sub_id = ometa.get("stripe_subscription_id")
                stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
                if stripe_sub_id and stripe_key:
                    import stripe
                    stripe.Subscription.modify(
                        stripe_sub_id, cancel_at_period_end=True, api_key=stripe_key)
                    logger.info("Stripe subscription %s set to cancel at period end (org %s)",
                                stripe_sub_id, org_id)
            except Exception:
                stripe_cancel_ok = False
                logger.exception(
                    "Stripe subscription cancel FAILED for org %s — billing is "
                    "still LIVE, marking cancel_pending for operator follow-up", org_id)

            if not (square_cancel_ok and stripe_cancel_ok):
                await self.db.update("subscriptions", {
                    "status": "cancel_pending",
                    "cancel_reason": reason,
                }, filters={"org_id": f"eq.{org_id}", "status": "eq.active"})
                logger.error(f"Subscription for org {org_id} marked cancel_pending — needs operator follow-up")
                return False

            await self.db.update("subscriptions", {
                "status": "canceled",
                "canceled_at": now.isoformat(),
                "cancel_reason": reason,
            }, filters={"org_id": f"eq.{org_id}", "status": "eq.active"})

            logger.info(f"Cancelled subscription for org {org_id}: {reason}")
            return True
        except Exception:
            logger.exception(f"Cancel failed for org {org_id}")
            return False

    # ── Fallback Renewal (cron safety net) ──

    async def process_renewals(self):
        """
        DISABLED 2026-08-19 — billing is Stripe-only now.

        This used to create SQUARE renewal invoices for every subscription past
        its period end. Stripe subscriptions auto-renew natively (Stripe charges
        the card on file each period), so there is nothing to renew here, and
        minting a Square invoice would double-bill a Stripe merchant. The daily
        Celery beat entry was removed; this guard makes the manual
        /api/billing/process-renewals endpoint a safe no-op too.
        """
        logger.info("process_renewals is a no-op — renewals are handled by Stripe")
        return

    async def _process_renewals_legacy_square(self):
        try:
            now = datetime.now(timezone.utc)

            active_subs = await self.db.select("subscriptions", filters={
                "status": "eq.active",
                "current_period_end": f"lte.{now.isoformat()}",
            })

            trialing_subs = await self.db.select("subscriptions", filters={
                "status": "eq.trialing",
                "current_period_end": f"lte.{now.isoformat()}",
            })

            subs = (active_subs or []) + (trialing_subs or [])

            if not subs:
                logger.info("No renewals due today")
                return

            for sub in subs:
                # Resilience: skip malformed rows instead of aborting the whole
                # batch. A single row missing id/org_id/monthly_price_cents used
                # to raise KeyError below (e.g. `sub["monthly_price_cents"]`),
                # which propagated to the outer handler and killed every
                # remaining renewal in the run.
                if (not sub.get("id") or not sub.get("org_id")
                        or sub.get("monthly_price_cents") is None):
                    logger.warning(
                        "renewals: skipping malformed subscription row id=%r org=%r",
                        sub.get("id"), sub.get("org_id"),
                    )
                    continue

                meta = sub.get("metadata") or {}
                is_trial_conversion = sub.get("status") == "trialing"

                # Deterministic idempotency key: a retried renewal run for the
                # same subscription/period must not double-invoice.
                period_end_date = (sub.get("current_period_end") or now.isoformat())[:10]
                renewal_key = f"renewal-{sub['id']}-{period_end_date}"

                if meta.get("square_subscription_id"):
                    new_end = now + timedelta(days=30)
                    update_data = {
                        "current_period_start": now.isoformat(),
                        "current_period_end": new_end.isoformat(),
                    }
                    if is_trial_conversion:
                        update_data["status"] = "active"
                    await self.db.update("subscriptions", update_data,
                                         filters={"id": f"eq.{sub['id']}"})
                    if is_trial_conversion:
                        logger.info(f"Trial→active (Square auto-billing) for org {sub['org_id']}")
                    continue

                org_id = sub["org_id"]
                amount = sub["monthly_price_cents"]
                # Fee parity: the provisioned billing contract
                # (merchant_billing_terms) is the source of truth for the
                # monthly fee. Fall back to the subscription row when the
                # merchant has no terms row (legacy) or the lookup fails.
                try:
                    from .fee_terms import get_active_terms
                    terms = await get_active_terms(self.db, org_id)
                    contracted = terms.get("monthly_fee_cents") if terms else None
                    if contracted is not None and int(contracted) != int(amount):
                        logger.warning(
                            "fee-parity: org %s contracted monthly %s¢ != subscription "
                            "monthly_price_cents %s¢ — billing the contracted amount",
                            org_id, contracted, amount,
                        )
                        amount = int(contracted)
                except Exception as terms_err:  # noqa: BLE001 — fail-open to current behavior
                    logger.warning("fee-parity terms lookup failed for %s: %s", org_id, terms_err)
                # Pre-charge reconciliation guard: warn (never block) when the
                # merchant's live billing config drifts from the contract.
                try:
                    from .fee_reconciliation import check_merchant
                    for mm in await check_merchant(self.db, org_id):
                        logger.warning(
                            "fee-parity pre-invoice mismatch org=%s field=%s contracted=%s applied=%s",
                            org_id, mm["field"], mm["contracted"], mm["applied"],
                        )
                except Exception:  # noqa: BLE001 — guard must never affect billing
                    pass
                email = sub.get("contact_email") or sub.get("email", "")
                owner_name = sub.get("owner_name", "")
                business_name = sub.get("business_name", "")
                phone = sub.get("phone")
                sub_currency = meta.get("currency", "USD")
                tier_label = sub.get("tier", "Standard").replace("_", " ").title()
                description = (
                    f"Meridian Analytics - {tier_label} Plan (First Month)"
                    if is_trial_conversion
                    else f"Meridian Analytics - Monthly Renewal ({tier_label})"
                )

                customer_id = meta.get("square_customer_id")
                if customer_id:
                    card_id = await self._get_card_on_file(customer_id)
                    if card_id:
                        sub_result = await self.create_auto_subscription(
                            org_id=org_id,
                            amount_cents=amount,
                            customer_email=email,
                            customer_name=owner_name,
                            business_name=business_name,
                            plan=sub.get("tier", "starter"),
                            currency=sub_currency,
                            # The period being billed starts now — the default
                            # (+30d) would skip a month for renewals.
                            start_date=now.strftime("%Y-%m-%d"),
                            idempotency_key=renewal_key,
                        )
                        if sub_result.success:
                            import json as json_mod
                            await self.db.update("subscriptions", {
                                "current_period_start": now.isoformat(),
                                "current_period_end": (now + timedelta(days=30)).isoformat(),
                                "metadata": json_mod.dumps({
                                    **meta,
                                    "square_subscription_id": sub_result.subscription_id,
                                    "auto_billing": True,
                                    "subscription_started_at": now.isoformat(),
                                }),
                            }, filters={"id": f"eq.{sub['id']}"})
                            logger.info(f"Upgraded org {org_id} to auto-subscription: {sub_result.subscription_id}")
                            continue

                inv_result = await self.create_invoice(
                    org_id=org_id,
                    amount_cents=amount,
                    customer_email=email,
                    description=description,
                    store_card=True,
                    currency=sub_currency,
                    idempotency_key=renewal_key,
                )

                if inv_result.success:
                    import json as json_mod
                    new_end = now + timedelta(days=30)
                    renewal_meta = {
                        **meta,
                        "last_renewal": now.isoformat(),
                        "renewal_invoice_id": inv_result.invoice_id,
                        "renewal_invoice_url": inv_result.invoice_url,
                    }
                    if is_trial_conversion:
                        renewal_meta["trial_converted_at"] = now.isoformat()
                        renewal_meta["first_month_free"] = True

                    await self.db.update("subscriptions", {
                        "status": "active",
                        "current_period_start": now.isoformat(),
                        "current_period_end": new_end.isoformat(),
                        "metadata": json_mod.dumps(renewal_meta),
                    }, filters={"id": f"eq.{sub['id']}"})

                    action = "Trial→active" if is_trial_conversion else "Renewal"
                    logger.info(f"{action} for org {org_id}: invoice {inv_result.invoice_id}")

                    if phone and inv_result.invoice_url:
                        try:
                            from src.sms.client import send_invoice_sms
                            sms_label = (
                                f"{tier_label} (First Invoice)"
                                if is_trial_conversion
                                else f"{tier_label} (Renewal)"
                            )
                            await send_invoice_sms(
                                phone=phone,
                                owner_name=owner_name or "there",
                                business_name=business_name or "your business",
                                invoice_url=inv_result.invoice_url,
                                plan_label=sms_label,
                                amount_display=f"${amount / 100:.0f}/mo",
                            )
                        except Exception as sms_err:
                            logger.warning(f"Renewal SMS failed for {org_id}: {sms_err}")
                else:
                    import json as json_mod
                    logger.error(f"Renewal failed for org {org_id}: {inv_result.error}")
                    await self.db.update("subscriptions", {
                        "status": "past_due",
                        "metadata": json_mod.dumps({
                            **meta,
                            "renewal_failed_at": now.isoformat(),
                            "renewal_error": inv_result.error,
                        }),
                    }, filters={"id": f"eq.{sub['id']}"})

        except Exception:
            logger.exception("Renewal processing failed")

    # ── Private helpers ──

    async def _get_or_create_customer(
        self, email: str, name: str, business_name: str
    ) -> Optional[str]:
        """Find or create a Square customer record."""
        try:
            search_resp = await self.http.post("/v2/customers/search", json={
                "query": {"filter": {"email_address": {"exact": email}}},
            })
            customers = search_resp.json().get("customers", [])

            if customers:
                return customers[0]["id"]

            name_parts = name.split(" ", 1)
            create_resp = await self.http.post("/v2/customers", json={
                "idempotency_key": str(uuid4()),
                "given_name": name_parts[0],
                "family_name": name_parts[1] if len(name_parts) > 1 else "",
                "email_address": email,
                "company_name": business_name,
                "reference_id": f"meridian_{email}",
            })

            return create_resp.json().get("customer", {}).get("id")

        except Exception as e:
            logger.warning(f"Customer creation failed for {email}: {e}")
            return None

    async def _get_card_on_file(self, customer_id: str) -> Optional[str]:
        """Get the customer's most recent enabled card on file."""
        try:
            resp = await self.http.get("/v2/cards", params={"customer_id": customer_id})
            cards = resp.json().get("cards", [])
            active = [c for c in cards if c.get("enabled", True)]
            return active[-1]["id"] if active else None
        except Exception as e:
            logger.warning(f"Card lookup failed for customer {customer_id}: {e}")
            return None

    async def _get_or_create_subscription_plan(
        self, amount_cents: int, plan_name: str, currency: str = "USD",
    ) -> Optional[str]:
        """Get or create a Square catalog subscription plan for the given amount."""
        display_name = f"Meridian {plan_name.replace('_', ' ').title()} - ${amount_cents / 100:.0f}/mo"

        try:
            resp = await self.http.post("/v2/catalog/search", json={
                "object_types": ["SUBSCRIPTION_PLAN_VARIATION"],
                "query": {
                    "exact_query": {
                        "attribute_name": "name",
                        "attribute_value": display_name,
                    }
                },
            })
            objects = resp.json().get("objects", [])
            if objects:
                return objects[0]["id"]
        except Exception:
            pass

        try:
            ref_id = f"meridian-{plan_name}-{amount_cents}"
            resp = await self.http.post("/v2/catalog/upsert", json={
                "idempotency_key": str(uuid4()),
                "object": {
                    "type": "SUBSCRIPTION_PLAN_VARIATION",
                    "id": f"#{ref_id}",
                    "subscription_plan_variation_data": {
                        "name": display_name,
                        "phases": [{
                            "cadence": "MONTHLY",
                            "recurring_price_money": {
                                "amount": amount_cents,
                                "currency": currency,
                            },
                        }],
                    },
                },
            })
            return resp.json().get("catalog_object", {}).get("id")
        except Exception as e:
            logger.warning(f"Subscription plan creation failed: {e}")
            return None

