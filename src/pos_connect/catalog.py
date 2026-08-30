"""
Meridian v1.5 integrations hub — the full catalog.

Three sources merge into one list the frontend renders:

  1. Dedicated integrations (Square, Clover, Toast) — their own routes/config.
  2. Registry providers (src/pos_connect/registry.py) — generic 1-click OAuth.
  3. Partner-tier entries below — no self-serve API today; the hub shows them
     with a "Request access" CTA that records demand in pos_waitlist. When a
     vendor grants us a partner OAuth client, the entry graduates into the
     registry and the card flips to 1-click with no frontend change.

Tiers surfaced to the frontend:
  "live"    — dedicated flow, production-proven (Square; Clover when enabled)
  "oauth"   — registry provider; 1-click when verified + creds present
  "manual"  — credential paste via /api/pos/connect (Toast today)
  "partner" — vendor gates API access behind a partnership; request-access CTA
"""
from __future__ import annotations

from dataclasses import dataclass

from .registry import PROVIDERS


@dataclass(frozen=True)
class PartnerEntry:
    key: str
    label: str
    category: str
    description: str
    docs_url: str = ""
    # Why it's partner-tier — surfaced in the card's tooltip/footnote.
    gate_note: str = ""


# Curated from the Marty-by-Lavu integration catalog + the categories Meridian
# already monetizes. Descriptions are merchant-facing copy.
PARTNER_ENTRIES: list[PartnerEntry] = [
    # Scheduling & labor
    PartnerEntry(
        key="sevenshifts", label="7shifts", category="scheduling",
        description="Team scheduling and labor analytics next to your sales curve.",
        docs_url="https://developers.7shifts.com/",
        gate_note="OAuth2 partner client issued via partnerships@7shifts.com — flips to 1-click once granted.",
    ),
    PartnerEntry(
        key="dolce", label="Dolce", category="scheduling",
        description="Scheduling, time tracking and labor cost tracking.",
        gate_note="No public self-serve API.",
    ),
    # Delivery & online ordering
    PartnerEntry(
        key="doordash", label="DoorDash", category="delivery",
        description="Marketplace orders and payout reconciliation inside Meridian.",
        docs_url="https://developer.doordash.com/",
        gate_note="Marketplace API pipeline currently closed to new partners; interest form filed.",
    ),
    PartnerEntry(
        key="grubhub", label="Grubhub", category="delivery",
        description="Grubhub order volume alongside in-store sales.",
        gate_note="Partner API only.",
    ),
    PartnerEntry(
        key="otter", label="Otter", category="delivery",
        description="One feed for every delivery app Otter aggregates.",
        docs_url="https://choco.com/us/otter",
        gate_note="Partner API only.",
    ),
    PartnerEntry(
        key="chowly", label="Chowly", category="delivery",
        description="Third-party delivery orders injected into your POS, analyzed here.",
        gate_note="Partner API only.",
    ),
    PartnerEntry(
        key="checkmate", label="Checkmate", category="delivery",
        description="Digital ordering channels consolidated into one revenue view.",
        gate_note="Partner API only.",
    ),
    PartnerEntry(
        key="flipdish", label="Flipdish", category="ordering",
        description="White-label online ordering performance and menu insights.",
        gate_note="Partner API only.",
    ),
    PartnerEntry(
        key="open_dining", label="Open Dining", category="ordering",
        description="Online orders straight to the kitchen, reported here.",
        gate_note="Partner API only.",
    ),
    # Reservations & loyalty
    PartnerEntry(
        key="opentable", label="OpenTable", category="reservations",
        description="Covers, no-shows and reservation pacing against revenue.",
        gate_note="Partner program only.",
    ),
    PartnerEntry(
        key="loyaltymatch", label="LoyaltyMatch", category="loyalty",
        description="Loyalty program performance tied to repeat-visit revenue.",
        gate_note="Partner API only.",
    ),
    PartnerEntry(
        key="pepper", label="Pepper", category="loyalty",
        description="Rewards engagement and retention analytics.",
        gate_note="Partner API only.",
    ),
    # Accounting & back office
    PartnerEntry(
        key="restaurant365", label="Restaurant365", category="accounting",
        description="Restaurant-native accounting synced with daily sales.",
        docs_url="https://www.restaurant365.com/",
        gate_note="Connect API is partner-gated.",
    ),
    PartnerEntry(
        key="shogo", label="Shogo", category="accounting",
        description="Nightly sales journal entries to Sage, NetSuite or Dynamics.",
        gate_note="Partner API only.",
    ),
    PartnerEntry(
        key="davo", label="DAVO", category="tax",
        description="Sales tax set aside daily and filed automatically.",
        gate_note="Partner API only.",
    ),
    # Inventory
    PartnerEntry(
        key="marketman", label="MarketMan", category="inventory",
        description="Food cost, ordering and waste tracking against sales mix.",
        docs_url="https://www.marketman.com/",
        gate_note="API keys issued per-account by MarketMan support.",
    ),
    PartnerEntry(
        key="bar_i", label="Bar-i", category="inventory",
        description="Liquid inventory variance against poured-vs-sold.",
        gate_note="No public API.",
    ),
]


CATEGORY_LABELS: dict[str, str] = {
    "pos": "Point of Sale",
    "payments": "Payments",
    "accounting": "Accounting",
    "tax": "Tax",
    "scheduling": "Scheduling & Labor",
    "payroll": "Payroll",
    "delivery": "Delivery",
    "ordering": "Online Ordering",
    "reservations": "Reservations",
    "loyalty": "Loyalty",
    "marketing": "Marketing",
    "inventory": "Inventory",
}


def build_catalog(connected_providers: dict[str, str]) -> list[dict]:
    """Assemble the full hub catalog.

    `connected_providers` maps provider key → connection status ("connected",
    "error", …) for the requesting org, read from pos_connections. Keys not
    present are not connected.
    """
    from .. import config as _config

    items: list[dict] = []

    def conn_status(key: str) -> tuple[bool, str]:
        st = connected_providers.get(key, "")
        return st == "connected", st

    # 1. Dedicated flows.
    sq_connected, sq_status = conn_status("square")
    items.append({
        "key": "square", "label": "Square", "category": "pos", "tier": "live",
        "configured": bool(_config.square.app_id and _config.square.app_secret),
        "connected": sq_connected, "connection_status": sq_status,
        "authorize_path": "/api/square/authorize",
        "status_path": "/api/square/status",
        "description": "Sales, items, inventory and labor synced continuously.",
        "note": "", "docs_url": "",
    })
    cl_connected, cl_status = conn_status("clover")
    items.append({
        "key": "clover", "label": "Clover", "category": "pos",
        "tier": "live" if _config.clover.is_enabled else "oauth",
        "configured": _config.clover.has_oauth_credentials,
        "connected": cl_connected, "connection_status": cl_status,
        "authorize_path": "/api/clover/authorize",
        "status_path": "/api/clover/status",
        "description": "1-click connect for Clover and its bank-branded twins.",
        "note": "", "docs_url": "",
    })
    to_connected, to_status = conn_status("toast")
    items.append({
        "key": "toast", "label": "Toast", "category": "pos", "tier": "manual",
        "configured": bool(_config.toast.client_id and _config.toast.client_secret),
        "connected": to_connected, "connection_status": to_status,
        "authorize_path": None, "status_path": None,
        "description": "Connect with your Toast partner API credentials.",
        "note": "Toast grants API access through its certified-partner program; "
                "merchants on Toast paste their credentials until our partnership lands.",
        "docs_url": "https://doc.toasttab.com/doc/devguide/apiPartnerIntegrationOverview.html",
    })

    # 2. Registry providers (generic 1-click framework).
    for p in PROVIDERS.values():
        connected, status = conn_status(p.key)
        items.append({
            "key": p.key, "label": p.label, "category": p.category,
            "tier": "oauth",
            "configured": p.credentials_present(),
            "verified": p.verified,
            "connected": connected, "connection_status": status,
            "authorize_path": f"/api/pos/{p.key}/authorize" if p.enabled() else None,
            "status_path": f"/api/pos/{p.key}/status",
            "description": p.market_note,
            "note": "" if p.enabled() else "Coming soon — connector built, awaiting validation.",
            "docs_url": p.docs_url,
        })

    # 3. Partner-tier entries (request-access CTA).
    for e in PARTNER_ENTRIES:
        connected, status = conn_status(e.key)
        items.append({
            "key": e.key, "label": e.label, "category": e.category,
            "tier": "partner",
            "configured": False,
            "connected": connected, "connection_status": status,
            "authorize_path": None, "status_path": None,
            "description": e.description,
            "note": e.gate_note,
            "docs_url": e.docs_url,
        })

    return items
