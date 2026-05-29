"""Credit-pack purchase flow via Square custom invoices.

End-to-end:
  1. merchant clicks Buy → POST /api/credits/purchase
  2. create_purchase_invoice() inserts a `pending` credit_purchases row,
     creates a Square invoice, publishes it, returns the hosted URL.
  3. customer pays on Square's hosted checkout page.
  4. Square posts invoice.payment_made to /api/credits/webhook/square.
  5. handle_invoice_payment() flips the row to `paid`, calls credits_grant()
     in the same logical step, and is idempotent so duplicate webhooks
     never double-credit.
"""
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

import httpx

from ..square.client import SquareClient
from .service import grant

logger = logging.getLogger("meridian.credits.purchase")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_ANON_KEY", "")
)
SQUARE_LOCATION_ID = os.getenv("SQUARE_LOCATION_ID", "")
SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN", "")
INVOICE_DUE_DAYS = int(os.getenv("CREDIT_INVOICE_DUE_DAYS", "7"))


@dataclass(frozen=True)
class CreditPack:
    pack_id: str
    credits: int
    price_cents_usd: int
    price_cents_cad: int
    label: str


# Mirror of frontend CREDIT_PACKS in content-demo-data.ts.
# Change these in lockstep — they're publicly visible pricing.
PACKS: dict[str, CreditPack] = {
    "starter": CreditPack(pack_id="starter", credits=2_000, price_cents_usd=200, price_cents_cad=275, label="Starter"),
    "popular": CreditPack(pack_id="popular", credits=5_000, price_cents_usd=450, price_cents_cad=620, label="Popular"),
    "pro":     CreditPack(pack_id="pro",     credits=15_000, price_cents_usd=1_200, price_cents_cad=1_650, label="Pro"),
    "agency":  CreditPack(pack_id="agency",  credits=50_000, price_cents_usd=3_500, price_cents_cad=4_800, label="Agency"),
}


@dataclass
class PurchaseResult:
    success: bool
    purchase_id: str = ""
    invoice_url: str = ""
    invoice_id: str = ""
    credit_amount: int = 0
    price_cents: int = 0
    currency: str = "USD"
    error: str = ""


def _supabase_headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


async def _insert_pending_purchase(
    merchant_id: str,
    pack: CreditPack,
    customer_email: str,
    customer_name: str,
    currency: str,
    price_cents: int,
    idempotency_key: str,
) -> Optional[dict[str, Any]]:
    if not (SUPABASE_URL and SUPABASE_KEY):
        return None
    payload = {
        "merchant_id": merchant_id,
        "pack_id": pack.pack_id,
        "credit_amount": pack.credits,
        "price_cents": price_cents,
        "currency": currency,
        "customer_email": customer_email,
        "customer_name": customer_name,
        "idempotency_key": idempotency_key,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=INVOICE_DUE_DAYS)).isoformat(),
        "metadata": {"pack_label": pack.label},
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(
                f"{SUPABASE_URL}/rest/v1/credit_purchases",
                headers=_supabase_headers(),
                json=payload,
            )
            if res.status_code in (200, 201):
                rows = res.json()
                return rows[0] if rows else None
            logger.error("insert purchase %d: %s", res.status_code, res.text[:200])
    except Exception as e:
        logger.error("insert purchase failed: %s", e)
    return None


async def _patch_purchase(purchase_id: str, fields: dict[str, Any]) -> None:
    if not (SUPABASE_URL and SUPABASE_KEY):
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.patch(
                f"{SUPABASE_URL}/rest/v1/credit_purchases?id=eq.{purchase_id}",
                headers=_supabase_headers(),
                json=fields,
            )
            if res.status_code not in (200, 204):
                logger.warning("patch purchase %d: %s", res.status_code, res.text[:200])
    except Exception as e:
        logger.warning("patch purchase failed: %s", e)


async def _find_purchase_by_invoice(square_invoice_id: str) -> Optional[dict[str, Any]]:
    if not (SUPABASE_URL and SUPABASE_KEY):
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(
                f"{SUPABASE_URL}/rest/v1/credit_purchases"
                f"?square_invoice_id=eq.{square_invoice_id}"
                f"&select=*&limit=1",
                headers=_supabase_headers(),
            )
            if res.status_code == 200 and res.json():
                return res.json()[0]
    except Exception as e:
        logger.warning("find purchase by invoice failed: %s", e)
    return None


async def _square_get_or_create_customer(
    square: SquareClient,
    email: str,
    name: str,
) -> Optional[str]:
    """Email-keyed customer lookup; create if missing. Returns Square customer ID."""
    if not email:
        return None
    try:
        search = await square.post("/v2/customers/search", json={
            "query": {"filter": {"email_address": {"exact": email}}}
        })
        customers = search.get("customers") or []
        if customers:
            return customers[0].get("id")
    except Exception as e:
        logger.warning("customer search failed for %s: %s", email, e)

    try:
        first, _, last = name.partition(" ")
        created = await square.post("/v2/customers", json={
            "idempotency_key": str(uuid4()),
            "given_name": first or email.split("@")[0],
            "family_name": last,
            "email_address": email,
            "reference_id": f"meridian_credits_{email}",
        })
        return (created.get("customer") or {}).get("id")
    except Exception as e:
        logger.error("customer create failed for %s: %s", email, e)
        return None


async def create_purchase_invoice(
    merchant_id: str,
    pack_id: str,
    customer_email: str,
    customer_name: str = "",
    currency: str = "USD",
) -> PurchaseResult:
    """Create a pending purchase + Square invoice. Returns the hosted URL.

    On any failure after the DB row is inserted, the row is marked 'failed'
    so the admin dashboard can show the merchant a clear error.
    """
    pack = PACKS.get(pack_id)
    if not pack:
        return PurchaseResult(success=False, error=f"unknown pack '{pack_id}'")
    if not SQUARE_ACCESS_TOKEN or not SQUARE_LOCATION_ID:
        return PurchaseResult(success=False, error="Square not configured")
    if not customer_email:
        return PurchaseResult(success=False, error="customer_email required")

    price_cents = pack.price_cents_cad if currency.upper() == "CAD" else pack.price_cents_usd
    idempotency_key = str(uuid4())

    row = await _insert_pending_purchase(
        merchant_id=merchant_id,
        pack=pack,
        customer_email=customer_email,
        customer_name=customer_name,
        currency=currency,
        price_cents=price_cents,
        idempotency_key=idempotency_key,
    )
    if not row:
        return PurchaseResult(success=False, error="failed to record pending purchase")

    purchase_id = row["id"]

    description = (
        f"{pack.credits:,} Meridian credits — covers ~{pack.credits // 50} minutes of AI phone calls, "
        f"~{pack.credits // 50} SMS conversations, or {pack.credits // 100} social posts."
    )

    async with SquareClient(access_token=SQUARE_ACCESS_TOKEN) as square:
        customer_id = await _square_get_or_create_customer(square, customer_email, customer_name)
        if not customer_id:
            await _patch_purchase(purchase_id, {"status": "failed", "metadata": {**row.get("metadata", {}), "failure_reason": "customer_create_failed"}})
            return PurchaseResult(success=False, error="failed to create Square customer")

        # Order first — Square invoices wrap orders.
        try:
            order_resp = await square.post("/v2/orders", json={
                "idempotency_key": str(uuid4()),
                "order": {
                    "location_id": SQUARE_LOCATION_ID,
                    "line_items": [{
                        "name": f"{pack.label} Credit Pack ({pack.credits:,} credits)",
                        "quantity": "1",
                        "note": description,
                        "base_price_money": {"amount": price_cents, "currency": currency},
                    }],
                    "metadata": {
                        "kind": "credit_pack",
                        "merchant_id": merchant_id,
                        "pack_id": pack.pack_id,
                        "credit_amount": str(pack.credits),
                        "purchase_id": purchase_id,
                    },
                },
            })
            order_id = (order_resp.get("order") or {}).get("id")
            if not order_id:
                raise RuntimeError(f"no order id in response: {order_resp}")
        except Exception as e:
            logger.error("Square order create failed: %s", e)
            await _patch_purchase(purchase_id, {"status": "failed"})
            return PurchaseResult(success=False, error=f"Square order create failed: {e}")

        # Now the invoice itself.
        due_date = (datetime.now(timezone.utc) + timedelta(days=INVOICE_DUE_DAYS)).strftime("%Y-%m-%d")
        try:
            invoice_resp = await square.post("/v2/invoices", json={
                "idempotency_key": idempotency_key,
                "invoice": {
                    "location_id": SQUARE_LOCATION_ID,
                    "order_id": order_id,
                    "primary_recipient": {"customer_id": customer_id},
                    "payment_requests": [{
                        "request_type": "BALANCE",
                        "due_date": due_date,
                        "automatic_payment_source": "NONE",
                    }],
                    "delivery_method": "EMAIL",
                    "title": f"Meridian Credits — {pack.label} ({pack.credits:,} credits)",
                    "description": description,
                    "accepted_payment_methods": {
                        "card": True,
                        "square_gift_card": False,
                        "bank_account": True,
                    },
                    "custom_fields": [
                        {"label": "Credits", "value": f"{pack.credits:,}", "placement": "ABOVE_LINE_ITEMS"},
                        {"label": "Account", "value": merchant_id, "placement": "BELOW_LINE_ITEMS"},
                    ],
                },
            })
            invoice = invoice_resp.get("invoice") or {}
            invoice_id = invoice.get("id")
            if not invoice_id:
                errs = invoice_resp.get("errors") or []
                raise RuntimeError(errs[0].get("detail") if errs else "no invoice id")

            pub_resp = await square.post(f"/v2/invoices/{invoice_id}/publish", json={
                "version": invoice.get("version", 0),
                "idempotency_key": str(uuid4()),
            })
            published = pub_resp.get("invoice") or invoice
            invoice_url = published.get("public_url") or invoice.get("public_url") or ""
        except Exception as e:
            logger.error("Square invoice create/publish failed: %s", e)
            await _patch_purchase(purchase_id, {"status": "failed", "square_order_id": order_id})
            return PurchaseResult(success=False, error=f"Square invoice failed: {e}")

    await _patch_purchase(purchase_id, {
        "square_invoice_id": invoice_id,
        "square_order_id": order_id,
        "square_customer_id": customer_id,
        "invoice_url": invoice_url,
    })

    return PurchaseResult(
        success=True,
        purchase_id=purchase_id,
        invoice_url=invoice_url,
        invoice_id=invoice_id,
        credit_amount=pack.credits,
        price_cents=price_cents,
        currency=currency,
    )


async def handle_invoice_payment(
    square_invoice_id: str,
    square_payment_id: str = "",
) -> bool:
    """Webhook handler: mark purchase paid and grant credits. Idempotent.

    Returns True if credits were granted in this call, False if the purchase
    was already paid (duplicate webhook) or no matching purchase exists.
    """
    purchase = await _find_purchase_by_invoice(square_invoice_id)
    if not purchase:
        logger.info("No credit_purchases row for invoice %s — not a credit pack", square_invoice_id)
        return False

    if purchase.get("granted_at"):
        logger.info("Duplicate invoice.payment_made for %s — already granted", square_invoice_id)
        return False

    merchant_id = purchase["merchant_id"]
    credit_amount = int(purchase["credit_amount"])
    purchase_id = purchase["id"]

    # Grant first; on success, mark the row. If the grant fails the row
    # stays pending and the next webhook retry will pick it up.
    new_balance = await grant(
        merchant_id=merchant_id,
        amount=credit_amount,
        action_type="square_purchase",
        action_id=purchase_id,
        metadata={
            "pack_id": purchase.get("pack_id"),
            "square_invoice_id": square_invoice_id,
            "square_payment_id": square_payment_id,
            "price_cents": purchase.get("price_cents"),
            "currency": purchase.get("currency"),
        },
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    await _patch_purchase(purchase_id, {
        "status": "paid",
        "paid_at": now_iso,
        "granted_at": now_iso,
        "square_payment_id": square_payment_id or None,
    })
    logger.info(
        "Credit purchase %s: granted %d credits to %s (new balance %d)",
        purchase_id, credit_amount, merchant_id, new_balance,
    )
    return True
