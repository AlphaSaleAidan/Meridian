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

Uses Square catalog items:
  - $250/month (Standard)
  - $500/month (Premium)
  - $1,000/month (Command)
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

# Plan tier pricing (cents)
PLAN_PRICES = {
    "standard": 25000,   # $250/mo
    "premium": 50000,    # $500/mo
    "command": 100000,   # $1,000/mo
    "weekly": 6500,      # $65/wk
}

# Map plan names to catalog keys
PLAN_CATALOG_KEY = {
    "standard": "standard_monthly",
    "premium": "premium_monthly",
    "command": "command_monthly",
    "weekly": "weekly",
}


@dataclass
class CheckoutResult:
    success: bool = False
    checkout_url: Optional[str] = None
    checkout_id: Optional[str] = None
    order_id: Optional[str] = None
    error: Optional[str] = None


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

    # ── Checkout (Payment Links) ──

    async def create_checkout(
        self,
        org_id: str,
        amount_cents: int,
        customer_email: str,
        customer_name: str,
        business_name: str,
        plan: str = "standard",
        return_url: str = "",
        setup_fee_cents: int = 0,
        first_month_free: bool = False,
        rep_id: str = "",
        rep_name: str = "",
    ) -> CheckoutResult:
        """Create a Square Checkout (Payment Link) for a new customer subscription."""
        try:
            idempotency_key = str(uuid4())
            customer_id = await self._get_or_create_customer(
                customer_email, customer_name, business_name
            )

            line_items = []
            discount_uid = "first-month-free-discount"

            subscription_item = {
                "uid": "subscription-line-item",
                "name": f"Meridian Analytics - {plan.title()} Plan (Monthly)",
                "quantity": "1",
                "base_price_money": {
                    "amount": amount_cents,
                    "currency": "USD",
                },
                "note": f"Monthly subscription for {business_name}",
            }
            if first_month_free:
                subscription_item["applied_discounts"] = [{"discount_uid": discount_uid}]
            line_items.append(subscription_item)

            if setup_fee_cents > 0:
                line_items.append({
                    "uid": "setup-fee-line-item",
                    "name": "One-Time Setup Fee",
                    "quantity": "1",
                    "base_price_money": {
                        "amount": setup_fee_cents,
                        "currency": "USD",
                    },
                    "note": f"Setup & onboarding for {business_name}",
                })

            discounts = []
            if first_month_free:
                discounts.append({
                    "uid": discount_uid,
                    "name": "First Month Free",
                    "type": "FIXED_AMOUNT",
                    "amount_money": {
                        "amount": amount_cents,
                        "currency": "USD",
                    },
                    "scope": "LINE_ITEM",
                })

            metadata = {
                "org_id": org_id,
                "plan": plan,
                "billing_type": "subscription_initial",
                "setup_fee_cents": str(setup_fee_cents),
                "first_month_free": str(first_month_free).lower(),
            }
            if rep_id:
                metadata["rep_id"] = rep_id
            if rep_name:
                metadata["rep_name"] = rep_name

            order = {
                "location_id": SQUARE_LOCATION_ID,
                "line_items": line_items,
                "metadata": metadata,
            }

            if discounts:
                order["discounts"] = discounts

            checkout_options = {
                "merchant_support_email": "support@meridian.tips",
                "ask_for_shipping_address": False,
                "accepted_payment_methods": {"apple_pay": True, "google_pay": True},
            }
            if return_url:
                checkout_options["redirect_url"] = return_url

            payload = {
                "idempotency_key": idempotency_key,
                "order": order,
                "checkout_options": checkout_options,
                "pre_populated_data": {"buyer_email": customer_email},
            }

            resp = await self.http.post("/v2/online-checkout/payment-links", json=payload)
            data = resp.json()

            if resp.status_code == 200 and "payment_link" in data:
                link = data["payment_link"]
                checkout_url = link.get("long_url") or link.get("url", "")
                order_id = link.get("order_id", "")

                initial_status = "trialing" if first_month_free else "active"
                try:
                    await self._record_subscription(
                        org_id=org_id, plan=plan, amount_cents=amount_cents,
                        customer_email=customer_email,
                        square_customer_id=customer_id,
                        square_order_id=order_id,
                        status=initial_status,
                        setup_fee_cents=setup_fee_cents,
                        first_month_free=first_month_free,
                        rep_id=rep_id,
                        rep_name=rep_name,
                    )
                except Exception as e:
                    logger.warning(f"Failed to record subscription for org {org_id}: {e}")

                return CheckoutResult(
                    success=True, checkout_url=checkout_url,
                    checkout_id=link.get("id"), order_id=order_id,
                )
            else:
                errors = data.get("errors", [])
                error_msg = errors[0].get("detail", "Unknown error") if errors else "Checkout creation failed"
                logger.error(f"Square checkout error for org {org_id}: {error_msg}")
                return CheckoutResult(error=error_msg)

        except Exception as e:
            logger.exception(f"Checkout creation failed for org {org_id}")
            return CheckoutResult(error=str(e))

    # ── Invoices (one-time charges, setup fees) ──

    async def create_invoice(
        self,
        org_id: str,
        amount_cents: int,
        customer_email: str,
        description: str = "Meridian Analytics Subscription",
        due_days: int = 3,
        store_card: bool = False,
    ) -> InvoiceResult:
        """
        Create a Square Invoice. When store_card=True, the customer's payment
        method is saved on file for future automatic charges.
        """
        try:
            idempotency_key = str(uuid4())

            customer_id = await self._get_or_create_customer(
                customer_email, customer_email.split("@")[0], ""
            )

            order_resp = await self.http.post("/v2/orders", json={
                "idempotency_key": str(uuid4()),
                "order": {
                    "location_id": SQUARE_LOCATION_ID,
                    "line_items": [{
                        "name": description,
                        "quantity": "1",
                        "base_price_money": {"amount": amount_cents, "currency": "USD"},
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
                    "idempotency_key": str(uuid4()),
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
    ) -> SubscriptionResult:
        """
        Create a Square Subscription for automatic monthly billing.
        Requires the customer to already have a card on file (stored during
        initial invoice payment).

        Square handles all recurring charges, retries, and dunning from here.
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

            plan_variation_id = await self._get_or_create_subscription_plan(amount_cents, plan)
            if not plan_variation_id:
                return SubscriptionResult(error="Could not create subscription plan in Square catalog")

            start_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")

            resp = await self.http.post("/v2/subscriptions", json={
                "idempotency_key": str(uuid4()),
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
                        logger.warning(f"Square subscription cancel returned {resp.status_code}")

            await self.db.update("subscriptions", {
                "status": "canceled",
                "canceled_at": now.isoformat(),
                "cancel_reason": reason,
            }, filters={"org_id": f"eq.{org_id}", "status": "eq.active"})

            logger.info(f"Cancelled subscription for org {org_id}: {reason}")
            return True
        except Exception as e:
            logger.exception(f"Cancel failed for org {org_id}")
            return False

    # ── Fallback Renewal (cron safety net) ──

    async def process_renewals(self):
        """
        Renewal processor for subscriptions NOT on Square auto-billing.
        Runs daily via Celery beat. Handles:
        - Active subscriptions past their period end → create renewal invoice
        - Trialing subscriptions past trial_ends_at → convert to first paid invoice
        """
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
                meta = sub.get("metadata") or {}
                is_trial_conversion = sub.get("status") == "trialing"

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
                email = sub.get("contact_email") or sub.get("email", "")
                owner_name = sub.get("owner_name", "")
                business_name = sub.get("business_name", "")
                phone = sub.get("phone")
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

        except Exception as e:
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
        self, amount_cents: int, plan_name: str
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
                                "currency": "USD",
                            },
                        }],
                    },
                },
            })
            return resp.json().get("catalog_object", {}).get("id")
        except Exception as e:
            logger.warning(f"Subscription plan creation failed: {e}")
            return None

    async def _record_subscription(
        self,
        org_id: str,
        plan: str,
        amount_cents: int,
        customer_email: str,
        square_customer_id: Optional[str] = None,
        square_order_id: Optional[str] = None,
        status: str = "active",
        setup_fee_cents: int = 0,
        first_month_free: bool = False,
        rep_id: str = "",
        rep_name: str = "",
    ):
        """Record or update a subscription in the database."""
        now = datetime.now(timezone.utc)

        metadata = {
            "payment_method": "square",
            "square_customer_id": square_customer_id,
            "square_order_id": square_order_id,
            "billing_cycle": "monthly",
            "auto_renew": True,
            "renewal_period_months": 3,
            "created_via": "proposal_checkout",
        }

        # Track setup fee for commission
        if setup_fee_cents > 0:
            metadata["setup_fee_cents"] = setup_fee_cents
            metadata["setup_fee_rep_id"] = rep_id
            metadata["setup_fee_rep_name"] = rep_name

        if first_month_free:
            metadata["first_month_free"] = True
            metadata["trial_ends_at"] = (now + timedelta(days=30)).isoformat()

        if rep_id:
            metadata["rep_id"] = rep_id
            metadata["rep_name"] = rep_name

        await self.db.upsert("subscriptions", {
            "org_id": org_id,
            "tier": plan,
            "status": status,
            "monthly_price_cents": amount_cents,
            "contact_email": customer_email,
            "current_period_start": now.isoformat(),
            "current_period_end": (now + timedelta(days=30)).isoformat(),
            "metadata": metadata,
        }, on_conflict="org_id")
