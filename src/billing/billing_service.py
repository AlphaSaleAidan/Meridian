"""
Billing Service — Square-based subscription billing for Meridian.

Handles:
  - Creating Square checkout links for initial payment
  - Creating Square invoices (setup fees, one-time charges)
  - Auto-recurring subscriptions via Square Subscriptions API
  - Card-on-file storage for automatic monthly charges
  - Subscription lifecycle (create, cancel, fallback renewal)

Flow:
  1. SR onboards customer → setup fee invoice sent (card stored on payment)
  2. Customer pays invoice → webhook fires → card on file
  3. Square Subscription created with stored card → auto-bills monthly
  4. process_renewals() exists as fallback for non-subscription customers
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
    "weekly": os.getenv("SQUARE_ITEM_65_WEEKLY", ""),
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
    ) -> CheckoutResult:
        """Create a Square Checkout (Payment Link) for the initial subscription payment."""
        try:
            idempotency_key = str(uuid4())
            customer_id = await self._get_or_create_customer(
                customer_email, customer_name, business_name
            )

            payload = {
                "idempotency_key": idempotency_key,
                "order": {
                    "location_id": SQUARE_LOCATION_ID,
                    "line_items": [{
                        "name": f"Meridian Analytics - {plan.title()} Plan",
                        "quantity": "1",
                        "base_price_money": {"amount": amount_cents, "currency": "USD"},
                        "note": f"Monthly subscription for {business_name}",
                    }],
                    "metadata": {
                        "org_id": org_id,
                        "plan": plan,
                        "billing_type": "subscription_initial",
                    },
                },
                "checkout_options": {
                    "redirect_url": return_url,
                    "merchant_support_email": "support@meridian.tips",
                    "ask_for_shipping_address": False,
                    "accepted_payment_methods": {"apple_pay": True, "google_pay": True},
                },
                "pre_populated_data": {"buyer_email": customer_email},
            }

            resp = await self.http.post("/v2/online-checkout/payment-links", json=payload)
            data = resp.json()

            if resp.status_code == 200 and "payment_link" in data:
                link = data["payment_link"]
                checkout_url = link.get("long_url") or link.get("url", "")
                order_id = link.get("order_id", "")

                await self._record_subscription(
                    org_id=org_id, plan=plan, amount_cents=amount_cents,
                    customer_email=customer_email,
                    square_customer_id=customer_id,
                    square_order_id=order_id,
                    status="pending_payment",
                )

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

            invoice_body = {
                "location_id": SQUARE_LOCATION_ID,
                "order_id": order_id,
                "primary_recipient": {"email_address": customer_email},
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
                await self.http.post(f"/v2/invoices/{invoice['id']}/publish", json={
                    "version": invoice.get("version", 0),
                    "idempotency_key": str(uuid4()),
                })

                return InvoiceResult(
                    success=True,
                    invoice_id=invoice["id"],
                    invoice_url=invoice.get("public_url"),
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

            result = self.db.table("subscriptions").select("*").eq(
                "org_id", org_id
            ).eq("status", "active").single().execute()

            if result.data:
                sub = result.data
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

            self.db.table("subscriptions").update({
                "status": "canceled",
                "canceled_at": now.isoformat(),
                "cancel_reason": reason,
            }).eq("org_id", org_id).eq("status", "active").execute()

            logger.info(f"Cancelled subscription for org {org_id}: {reason}")
            return True
        except Exception as e:
            logger.exception(f"Cancel failed for org {org_id}")
            return False

    # ── Fallback Renewal (cron safety net) ──

    async def process_renewals(self):
        """
        Fallback renewal for subscriptions NOT on Square auto-billing.
        Runs daily via Celery beat. Only processes subscriptions that don't
        have a square_subscription_id (those are handled by Square directly).
        """
        try:
            now = datetime.now(timezone.utc)

            result = self.db.table("subscriptions").select(
                "*, organizations(name, email, owner_name, phone)"
            ).eq(
                "status", "active"
            ).lte(
                "current_period_end", now.isoformat()
            ).execute()

            if not result.data:
                logger.info("No renewals due today")
                return

            for sub in result.data:
                meta = sub.get("metadata") or {}

                # Skip if Square handles auto-billing for this subscription
                if meta.get("square_subscription_id"):
                    new_end = now + timedelta(days=30)
                    self.db.table("subscriptions").update({
                        "current_period_start": now.isoformat(),
                        "current_period_end": new_end.isoformat(),
                    }).eq("id", sub["id"]).execute()
                    continue

                org_id = sub["org_id"]
                amount = sub["monthly_price_cents"]
                org = sub.get("organizations", {})
                email = org.get("email", "")

                # Try to set up auto-subscription if card is on file
                customer_id = meta.get("square_customer_id")
                if customer_id:
                    card_id = await self._get_card_on_file(customer_id)
                    if card_id:
                        sub_result = await self.create_auto_subscription(
                            org_id=org_id,
                            amount_cents=amount,
                            customer_email=email,
                            customer_name=org.get("owner_name", ""),
                            business_name=org.get("name", ""),
                            plan=sub.get("tier", "starter"),
                        )
                        if sub_result.success:
                            self.db.table("subscriptions").update({
                                "current_period_start": now.isoformat(),
                                "current_period_end": (now + timedelta(days=30)).isoformat(),
                                "metadata": {
                                    **meta,
                                    "square_subscription_id": sub_result.subscription_id,
                                    "auto_billing": True,
                                    "subscription_started_at": now.isoformat(),
                                },
                            }).eq("id", sub["id"]).execute()
                            logger.info(f"Upgraded org {org_id} to auto-subscription: {sub_result.subscription_id}")
                            continue

                # Fallback: create a one-time invoice with card-on-file auto-pay
                inv_result = await self.create_invoice(
                    org_id=org_id,
                    amount_cents=amount,
                    customer_email=email,
                    description=f"Meridian Analytics - Monthly Renewal ({sub.get('tier', 'Standard')})",
                    store_card=True,
                )

                if inv_result.success:
                    new_end = now + timedelta(days=30)
                    self.db.table("subscriptions").update({
                        "current_period_start": now.isoformat(),
                        "current_period_end": new_end.isoformat(),
                        "metadata": {
                            **meta,
                            "last_renewal": now.isoformat(),
                            "renewal_invoice_id": inv_result.invoice_id,
                            "renewal_invoice_url": inv_result.invoice_url,
                        },
                    }).eq("id", sub["id"]).execute()

                    logger.info(f"Fallback renewal for org {org_id}: invoice {inv_result.invoice_id}")

                    phone = org.get("phone")
                    if phone and inv_result.invoice_url:
                        try:
                            from src.sms.client import send_invoice_sms
                            tier = sub.get("tier", "Standard").replace("_", " ").title()
                            await send_invoice_sms(
                                phone=phone,
                                owner_name=org.get("owner_name", "there"),
                                business_name=org.get("name", "your business"),
                                invoice_url=inv_result.invoice_url,
                                plan_label=f"{tier} (Renewal)",
                                amount_display=f"${amount / 100:.0f}/mo",
                            )
                        except Exception as sms_err:
                            logger.warning(f"Renewal SMS failed for {org_id}: {sms_err}")
                else:
                    logger.error(f"Renewal failed for org {org_id}: {inv_result.error}")
                    self.db.table("subscriptions").update({
                        "status": "past_due",
                        "metadata": {
                            **meta,
                            "renewal_failed_at": now.isoformat(),
                            "renewal_error": inv_result.error,
                        },
                    }).eq("id", sub["id"]).execute()

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
        status: str = "pending_payment",
    ):
        """Record or update a subscription in the database."""
        now = datetime.now(timezone.utc)

        self.db.table("subscriptions").upsert({
            "org_id": org_id,
            "tier": plan,
            "status": status,
            "monthly_price_cents": amount_cents,
            "current_period_start": now.isoformat(),
            "current_period_end": (now + timedelta(days=30)).isoformat(),
            "metadata": {
                "payment_method": "square",
                "square_customer_id": square_customer_id,
                "square_order_id": square_order_id,
                "billing_cycle": "monthly",
                "auto_renew": True,
                "created_via": "onboarding_checkout",
            },
        }, on_conflict="org_id").execute()
