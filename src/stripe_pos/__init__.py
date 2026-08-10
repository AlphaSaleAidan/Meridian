"""
Stripe payments connector (1-click OAuth via src/pos_connect/).

Named stripe_pos — NOT src/stripe/ — so the package never shadows the
`stripe` PyPI SDK that src/api/routes/stripe_connect.py lazy-imports.

This is the POS-analytics ingest side of Stripe (merchant connects their
existing Stripe account, Meridian reads charges for revenue analytics). It is
completely separate from the platform's own Stripe Connect payments/fee rails
in stripe_connect.py / stripe_checkout.py, which use different credentials.
"""
from .client import StripePOSAPIError, StripePOSClient
from .mappers import StripePOSMapper
from .sync_engine import StripePOSSyncEngine

__all__ = [
    "StripePOSAPIError",
    "StripePOSClient",
    "StripePOSMapper",
    "StripePOSSyncEngine",
]
