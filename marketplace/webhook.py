"""
Square webhook for data marketplace purchases.

On payment.completed:
  1. Identify which dataset was purchased from order line items
  2. Generate presigned R2 download URL
  3. Email buyer the download link via Postal

Uses Square Checkout API for payment links and webhooks for fulfillment.
"""
import hashlib
import hmac
import os
import logging
from datetime import date

from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger("meridian.marketplace.webhook")

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])

PRODUCT_MAP = {
    "meridian_benchmarks_monthly": {
        "name": "Industry Benchmarks",
        "r2_key_pattern": "datasets/meridian_benchmarks_{month}.parquet",
        "price_cents": 29900,
    },
    "meridian_foot_traffic_monthly": {
        "name": "Foot Traffic Intelligence",
        "r2_key_pattern": "datasets/meridian_foot_traffic_all_{month}.parquet",
        "price_cents": 49900,
    },
    "meridian_full_suite_monthly": {
        "name": "Full Analytics Suite",
        "r2_key_pattern": "datasets/",
        "price_cents": 79900,
    },
    "meridian_historical_archive": {
        "name": "Historical Archive",
        "r2_key_pattern": "datasets/",
        "price_cents": 299900,
    },
}


def _verify_square_signature(body: bytes, signature: str, webhook_url: str) -> bool:
    secret = os.getenv("SQUARE_MARKETPLACE_WEBHOOK_SECRET", "")
    if not secret:
        return False
    combined = webhook_url.encode() + body
    expected = hmac.new(secret.encode(), combined, hashlib.sha256).digest()
    import base64
    expected_b64 = base64.b64encode(expected).decode()
    return hmac.compare_digest(expected_b64, signature)


@router.post("/webhook")
async def square_marketplace_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("x-square-hmacsha256-signature", "")
    webhook_url = str(request.url)

    if os.getenv("SQUARE_MARKETPLACE_WEBHOOK_SECRET") and not _verify_square_signature(payload, sig, webhook_url):
        raise HTTPException(status_code=400, detail="Invalid signature")

    import json
    event = json.loads(payload)
    event_type = event.get("type", "")

    if event_type == "payment.completed":
        payment = event.get("data", {}).get("object", {}).get("payment", {})
        buyer_email = payment.get("buyer_email_address", "")
        order_id = payment.get("order_id", "")
        amount_cents = payment.get("total_money", {}).get("amount", 0)

        product_key = _resolve_product_from_order(event)
        product = PRODUCT_MAP.get(product_key)

        if buyer_email and product:
            try:
                from storage.r2_publisher import generate_buyer_download_url

                month = date.today().strftime("%Y-%m")
                r2_key = product["r2_key_pattern"].format(month=month)
                download_url = generate_buyer_download_url(r2_key, expiry_hours=48)

                await _send_dataset_email(buyer_email, product["name"], download_url)
                await _log_data_sale(buyer_email, product_key, amount_cents)

                logger.info("Dataset delivered to %s: %s", buyer_email, product["name"])
            except Exception as e:
                logger.error("Dataset delivery failed for %s: %s", buyer_email, e)

    elif event_type == "subscription.updated":
        sub = event.get("data", {}).get("object", {}).get("subscription", {})
        if sub.get("status") == "CANCELED":
            logger.info("Subscription cancelled: %s", sub.get("id"))

    return {"received": True}


def _resolve_product_from_order(event: dict) -> str:
    """Match Square order line items to our product catalog."""
    note = event.get("data", {}).get("object", {}).get("payment", {}).get("note", "")
    for key in PRODUCT_MAP:
        if key in note:
            return key

    line_items = (
        event.get("data", {}).get("object", {}).get("order", {}).get("line_items", [])
    )
    for item in line_items:
        item_name = (item.get("name") or "").lower()
        if "benchmark" in item_name:
            return "meridian_benchmarks_monthly"
        elif "foot traffic" in item_name:
            return "meridian_foot_traffic_monthly"
        elif "full suite" in item_name or "analytics suite" in item_name:
            return "meridian_full_suite_monthly"
        elif "archive" in item_name or "historical" in item_name:
            return "meridian_historical_archive"

    return ""


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
