"""
Webhook Hook — Integrates commission tracking into existing Square/Clover webhook flow.

Drop this into the existing webhook handler chain. When a payment.created event
comes in from Square, call `on_payment_received()` to auto-calculate rep commission.

Integration point in `src/services/square/webhook_handlers.py`:
    from src.payouts.webhook_hook import on_payment_received
    
    # Inside handle_payment_created():
    await on_payment_received(
        org_id=connection.org_id,
        amount=payment_amount,
        payment_id=square_payment_id,
        source="square"
    )
"""

import logging
from decimal import Decimal
from typing import Optional

logger = logging.getLogger("meridian.payouts.webhook_hook")

# Lazy init — set during app startup
_commission_service = None


def init_commission_hook(db_client):
    """Initialize the commission service. Call once during app startup."""
    global _commission_service
    from .commission_service import CommissionService
    _commission_service = CommissionService(db_client)
    logger.info("Commission webhook hook initialized")


async def on_payment_received(
    org_id: str,
    amount: float,
    payment_id: Optional[str] = None,
    source: str = "square",
) -> Optional[str]:
    """
    Called when an inbound payment is received via webhook.
    
    Auto-calculates commission for the assigned rep (if any).
    Returns commission_id or None if no rep is assigned.
    
    Args:
        org_id: The merchant organization UUID
        amount: Payment amount in dollars
        payment_id: Square/Clover payment reference ID
        source: 'square' or 'clover'
    """
    if not _commission_service:
        logger.warning("Commission service not initialized, skipping")
        return None

    try:
        result = await _commission_service.process_payment(
            org_id=org_id,
            gross_amount=Decimal(str(amount)),
            source_type=f"{source}_payment",
            source_reference=payment_id,
        )

        if result.success and result.commission_id:
            logger.info(
                f"Commission auto-recorded: ${result.commission_amount} "
                f"({result.commission_rate}%) for {result.rep_name} "
                f"on ${amount} {source} payment from org {org_id}"
            )
            return result.commission_id
        
        return None

    except Exception as e:
        logger.error(f"Commission hook failed for org {org_id}: {e}")
        return None
