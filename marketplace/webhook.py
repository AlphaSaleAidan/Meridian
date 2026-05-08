"""
Stripe webhook for data marketplace purchases.

On checkout.session.completed:
  1. Identify which dataset was purchased
  2. Generate presigned R2 download URL
  3. Email buyer the download link via Postal

On customer.subscription.deleted:
  - Revoke API access
"""
import os
import logging

import stripe
from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger("meridian.marketplace.webhook")

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

PRODUCT_MAP = {
    "meridian_benchmarks_monthly": {
        "name": "Industry Benchmarks",
        "r2_key_pattern": "datasets/meridian_benchmarks_{month}.parquet",
    },
    "meridian_foot_traffic_monthly": {
        "name": "Foot Traffic Intelligence",
        "r2_key_pattern": "datasets/meridian_foot_traffic_all_{month}.parquet",
    },
    "meridian_full_suite_monthly": {
        "name": "Full Analytics Suite",
        "r2_key_pattern": "datasets/",
    },
    "meridian_historical_archive": {
        "name": "Historical Archive",
        "r2_key_pattern": "datasets/",
    },
}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    webhook_secret = os.getenv("STRIPE_MARKETPLACE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        buyer_email = session.get("customer_details", {}).get("email")
        product_key = session.get("metadata", {}).get("product", "")
        product = PRODUCT_MAP.get(product_key)

        if buyer_email and product:
            try:
                from storage.r2_publisher import generate_buyer_download_url
                from datetime import date

                month = date.today().strftime("%Y-%m")
                r2_key = product["r2_key_pattern"].format(month=month)
                download_url = generate_buyer_download_url(r2_key, expiry_hours=48)

                await _send_dataset_email(buyer_email, product["name"], download_url)
                await _log_data_sale(buyer_email, product_key, session.get("amount_total", 0))

                logger.info("Dataset delivered to %s: %s", buyer_email, product["name"])
            except Exception as e:
                logger.error("Dataset delivery failed for %s: %s", buyer_email, e)

    elif event["type"] == "customer.subscription.deleted":
        customer_id = event["data"]["object"].get("customer")
        logger.info("Subscription cancelled: %s", customer_id)

    return {"received": True}


async def _send_dataset_email(to: str, product_name: str, download_url: str):
    from src.email.postal_client import PostalClient
    client = PostalClient()
    await client.send(
        to=to,
        subject=f"Your Meridian {product_name} Dataset is Ready",
        html=f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #2563eb;">Your Dataset is Ready</h1>
            <p>Thank you for purchasing <strong>{product_name}</strong>.</p>
            <p><a href="{download_url}" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Download Dataset</a></p>
            <p style="color: #6b7280; font-size: 14px;">This link expires in 48 hours. Contact support@meridian.tips if you need a new link.</p>
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
            <p style="color: #9ca3af; font-size: 12px;">Meridian Intelligence — Real POS + Camera Analytics</p>
        </div>
        """,
        tag="marketplace_purchase",
    )


async def _log_data_sale(email: str, product: str, amount_cents: int):
    try:
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
        sb.table("data_sales").insert({
            "buyer_email": email,
            "product": product,
            "amount_cents": amount_cents,
            "status": "delivered",
        }).execute()
    except Exception as e:
        logger.warning("Failed to log data sale: %s", e)
