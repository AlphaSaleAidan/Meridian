"""
Billing Service — Square-based subscription billing for Meridian.

Handles:
  - Creating Square checkout links for initial payment
  - Creating Square invoices for custom amounts
  - Recurring billing (monthly auto-charge)
  - Subscription lifecycle (create, renew, cancel)
  - 3-month auto-renewal cycles

Uses Square catalog items:
  - $250/month (standard field sales)
  - $65/week (weekly plan)
  - Custom amounts via invoice API
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

import httpx

logger = logging.getLogger("meridian.billing")

SQUARE_BASE = os.getenv("SQUARE_BASE_URL", "https://connect.squareup.com")
SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN", "")
SQUARE_LOCATION_ID = os.getenv("SQUARE_LOCATION_ID", "")
SQUARE_APP_ID = os.getenv("SQUARE_APP_ID", "sq0idp-3yhWe5-jCcvTFnilu22dtg")

# Known catalog item IDs (set these in env after creating items in Square)
CATALOG_ITEMS = {
    "standard_monthly": os.getenv("SQUARE_ITEM_250_MONTHLY", ""),
    "weekly": os.getenv("SQUARE_ITEM_65_WEEKLY", ""),
}


@dataclass
class CheckoutResult:
    """Result of a checkout creation."""
    success: bool = False
    checkout_url: Optional[str] = None
    checkout_id: Optional[str] = None
    order_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class InvoiceResult:
    """Result of an invoice creation."""
    success: bool = False
    invoice_id: Optional[str] = None
    invoice_url: Optional[str] = None
    error: Optional[str] = None


class BillingService:
    """
    Manages Square billing for Meridian subscriptions.

    Usage:
        service = BillingService(supabase_client)

        # Create a checkout link for onboarding
        result = await service.create_checkout(
            org_id="uuid",
            amount_cents=25000,
            customer_email="owner@biz.com",
            customer_name="James Chen",
            business_name="Lucky Dragon Kitchen",
            plan="standard",
            return_url="https://meridian.tips/onboard?checkout=success"
        )

        # Create a custom invoice
        result = await service.create_invoice(
            org_id="uuid",
            amount_cents=50000,
            customer_email="owner@biz.com",
            description="Meridian Premium - Custom pricing"
        )

        # Process monthly renewals (called by cron)
        await service.process_renewals()
    """

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
        """
        Create a Square Checkout (Payment Link) for the initial subscription payment.
        Returns a URL that redirects the customer to Square's hosted checkout.
        """
        try:
            idempotency_key = str(uuid4())

            # Create or find Square customer
            customer_id = await self._get_or_create_customer(
                customer_email, customer_name, business_name
            )

            # Build the checkout payload
            payload = {
                "idempotency_key": idempotency_key,
                "order": {
                    "location_id": SQUARE_LOCATION_ID,
                    "line_items": [
                        {
                            "name": f"Meridian Analytics - {plan.title()} Plan",
                            "quantity": "1",
                            "base_price_money": {
                                "amount": amount_cents,
                                "currency": "USD",
                            },
                            "note": f"Monthly subscription for {business_name}",
                        }
                    ],
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
                    "accepted_payment_methods": {
                        "apple_pay": True,
                        "google_pay": True,
                    },
                },
                "pre_populated_data": {
                    "buyer_email": customer_email,
                },
            }

            # Use Payment Links API
            resp = await self.http.post("/v2/online-checkout/payment-links", json=payload)
            data = resp.json()

            if resp.status_code == 200 and "payment_link" in data:
                link = data["payment_link"]
                checkout_url = link.get("long_url") or link.get("url", "")
                order_id = link.get("order_id", "")

                # Record in database
                await self._record_subscription(
                    org_id=org_id,
                    plan=plan,
                    amount_cents=amount_cents,
                    customer_email=customer_email,
                    square_customer_id=customer_id,
                    square_order_id=order_id,
                    status="pending_payment",
                )

                return CheckoutResult(
                    success=True,
                    checkout_url=checkout_url,
                    checkout_id=link.get("id"),
                    order_id=order_id,
                )
            else:
                errors = data.get("errors", [])
                error_msg = errors[0].get("detail", "Unknown error") if errors else "Checkout creation failed"
                logger.error(f"Square checkout error for org {org_id}: {error_msg}")
                return CheckoutResult(error=error_msg)

        except Exception as e:
            logger.exception(f"Checkout creation failed for org {org_id}")
            return CheckoutResult(error=str(e))

    async def create_invoice(
        self,
        org_id: str,
        amount_cents: int,
        customer_email: str,
        description: str = "Meridian Analytics Subscription",
        due_days: int = 3,
    ) -> InvoiceResult:
        """
        Create a Square Invoice for custom amounts or manual billing.
        The invoice is emailed to the customer with a pay link.
        """
        try:
            idempotency_key = str(uuid4())

            # Create an order first
            order_resp = await self.http.post("/v2/orders", json={
                "idempotency_key": str(uuid4()),
                "order": {
                    "location_id": SQUARE_LOCATION_ID,
                    "line_items": [
                        {
                            "name": description,
                            "quantity": "1",
                            "base_price_money": {
                                "amount": amount_cents,
                                "currency": "USD",
                            },
                        }
                    ],
                },
            })
            order_data = order_resp.json()
            order_id = order_data.get("order", {}).get("id")

            if not order_id:
                return InvoiceResult(error="Failed to create order for invoice")

            # Create the invoice
            due_date = (datetime.utcnow() + timedelta(days=due_days)).strftime("%Y-%m-%d")

            invoice_resp = await self.http.post("/v2/invoices", json={
                "idempotency_key": idempotency_key,
                "invoice": {
                    "location_id": SQUARE_LOCATION_ID,
                    "order_id": order_id,
                    "primary_recipient": {
                        "email_address": customer_email,
                    },
                    "payment_requests": [
                        {
                            "request_type": "BALANCE",
                            "due_date": due_date,
                            "automatic_payment_source": "NONE",
                            "reminders": [
                                {
                                    "relative_scheduled_days": -1,
                                    "message": f"Reminder: Your Meridian Analytics payment of ${amount_cents / 100:.2f} is due tomorrow.",
                                },
                            ],
                        }
                    ],
                    "delivery_method": "EMAIL",
                    "title": "Meridian Analytics",
                    "description": description,
                    "accepted_payment_methods": {
                        "card": True,
                        "square_gift_card": False,
                        "bank_account": True,
                    },
                },
            })

            inv_data = invoice_resp.json()
            invoice = inv_data.get("invoice", {})

            if invoice.get("id"):
                # Publish the invoice (sends the email)
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

    async def process_renewals(self):
        """
        Process monthly subscription renewals.
        Called by a daily cron job. Finds subscriptions due for renewal
        and creates Square charges or invoices.

        Billing logic:
        - Charged monthly on the subscription anniversary date
        - Auto-renewed until customer cancels
        - Every 3 months: subscription is reconfirmed (notification sent)
        """
        try:
            now = datetime.utcnow()

            # Find active subscriptions where current_period_end is today or past
            result = self.db.table("subscriptions").select(
                "*, organizations(name, email, owner_name)"
            ).eq(
                "status", "active"
            ).lte(
                "current_period_end", now.isoformat()
            ).execute()

            if not result.data:
                logger.info("No renewals due today")
                return

            for sub in result.data:
                org_id = sub["org_id"]
                amount = sub["monthly_price_cents"]
                org = sub.get("organizations", {})
                email = org.get("email", "")
                months_active = 0

                if sub.get("current_period_start"):
                    start = datetime.fromisoformat(sub["current_period_start"].replace("Z", "+00:00"))
                    months_active = (now - start).days // 30

                # Every 3 months, send a reconfirmation notice
                if months_active > 0 and months_active % 3 == 0:
                    logger.info(f"3-month reconfirmation for org {org_id}")
                    # Create notification for admin review
                    self.db.table("notifications").insert({
                        "org_id": org_id,
                        "channel": "email",
                        "subject": f"3-Month Subscription Review: {org.get('name', 'Customer')}",
                        "body": f"Subscription for {org.get('name')} has been active for {months_active} months at ${amount/100:.2f}/mo. Auto-renewing.",
                        "status": "pending",
                    }).execute()

                # Create the renewal charge via invoice
                inv_result = await self.create_invoice(
                    org_id=org_id,
                    amount_cents=amount,
                    customer_email=email,
                    description=f"Meridian Analytics - Monthly Renewal ({sub.get('tier', 'Standard')})",
                )

                if inv_result.success:
                    # Update subscription period
                    new_start = now
                    new_end = now + timedelta(days=30)

                    self.db.table("subscriptions").update({
                        "current_period_start": new_start.isoformat(),
                        "current_period_end": new_end.isoformat(),
                        "metadata": {
                            **(sub.get("metadata") or {}),
                            "last_renewal": now.isoformat(),
                            "renewal_invoice_id": inv_result.invoice_id,
                            "months_active": months_active + 1,
                        },
                    }).eq("id", sub["id"]).execute()

                    logger.info(f"Renewed subscription for org {org_id}: invoice {inv_result.invoice_id}")
                else:
                    logger.error(f"Renewal failed for org {org_id}: {inv_result.error}")

                    # Mark as past_due after failed renewal
                    self.db.table("subscriptions").update({
                        "status": "past_due",
                        "metadata": {
                            **(sub.get("metadata") or {}),
                            "renewal_failed_at": now.isoformat(),
                            "renewal_error": inv_result.error,
                        },
                    }).eq("id", sub["id"]).execute()

        except Exception as e:
            logger.exception("Renewal processing failed")

    async def cancel_subscription(self, org_id: str, reason: str = "") -> bool:
        """Cancel a subscription. Stops future renewals."""
        try:
            self.db.table("subscriptions").update({
                "status": "canceled",
                "canceled_at": datetime.utcnow().isoformat(),
                "cancel_reason": reason,
            }).eq("org_id", org_id).eq("status", "active").execute()

            logger.info(f"Cancelled subscription for org {org_id}: {reason}")
            return True
        except Exception as e:
            logger.exception(f"Cancel failed for org {org_id}")
            return False

    # ── Private helpers ──

    async def _get_or_create_customer(
        self, email: str, name: str, business_name: str
    ) -> Optional[str]:
        """Find or create a Square customer record."""
        try:
            # Search for existing customer
            search_resp = await self.http.post("/v2/customers/search", json={
                "query": {
                    "filter": {
                        "email_address": {"exact": email},
                    },
                },
            })
            search_data = search_resp.json()
            customers = search_data.get("customers", [])

            if customers:
                return customers[0]["id"]

            # Create new customer
            name_parts = name.split(" ", 1)
            create_resp = await self.http.post("/v2/customers", json={
                "idempotency_key": str(uuid4()),
                "given_name": name_parts[0],
                "family_name": name_parts[1] if len(name_parts) > 1 else "",
                "email_address": email,
                "company_name": business_name,
                "reference_id": f"meridian_{email}",
            })
            create_data = create_resp.json()

            return create_data.get("customer", {}).get("id")

        except Exception as e:
            logger.warning(f"Customer creation failed for {email}: {e}")
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
        now = datetime.utcnow()

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
                "renewal_period_months": 3,
                "created_via": "onboarding_checkout",
            },
        }, on_conflict="org_id").execute()
