"""
Menu Extractor — Turn a merchant's read-only POS catalog into a menu "script"
for the AI phone agent.

The phone agent's system prompt is built from a list of menu items
(see api/routes/phone.py :: _build_system_prompt_for). Today that list comes
from phone_agent_config.menu_items, which a merchant types in by hand. We
already hold read-only POS credentials, and GenericRESTConnector.fetch_catalog()
already pulls the catalog over those creds. This module wires the two together:
pull the catalog, coerce it into the {name, price, category} shape the prompt
builder expects, and hand it back so the agent can talk about the real menu — no
merchant data entry, no UI.

Credential sourcing is the caller's job (see phone_dashboard.py ::
sync_menu_from_pos): OAuth-onboarded merchants store an encrypted token +
external_merchant_id in pos_connections, while hand-entered creds live on
phone_agent_config. This module just takes a resolved system_key + plaintext
access token (+ optional merchant_id/location_id for URL templating).

This is strictly a GET path. Nothing here creates, updates, or deletes anything
on the POS.

Coverage caveat: bearer / api-key systems (Square, Clover, and most Tier 1-3)
authenticate with the single stored token. Toast uses OAuth client-credentials
(client_id/secret + restaurant_id) and won't authenticate from a lone token —
its dedicated client (src/toast/client.py :: get_menu_items) is the right path
there. On any auth/transport failure we return [] and the caller keeps whatever
menu it already had.
"""
from __future__ import annotations

import logging
from typing import Any

from .base import POSConnectionConfig
from .registry import get_connector_config, resolve_alias
from .rest_connector import GenericRESTConnector

logger = logging.getLogger("meridian.pos.menu_extractor")


async def extract_menu_items(
    system_key: str,
    access_token: str,
    *,
    location_id: str = "",
    merchant_id: str = "",
    max_items: int = 300,
) -> list[dict]:
    """Read-only pull of a merchant's POS catalog → phone-agent menu items.

    Returns a list of ``{"name", "price"?, "category"?, "source_external_id"?}``
    dicts where ``price`` is in dollars (omitted when the POS doesn't expose
    one) and ``source_external_id`` is the POS catalog object id when exposed
    (menu_store's dedupe key across re-syncs). Returns ``[]`` on any failure so
    the caller can fall back to the existing stored menu.

    The connector layer already paginates (GenericRESTConnector.fetch_catalog,
    page_size×max_pages); ``max_items`` caps what we keep — anything past the
    cap is logged as dropped, never silently lost.
    """
    key = resolve_alias(system_key)
    api_config = get_connector_config(key)
    if not api_config:
        logger.info("menu extract: unknown POS '%s'", system_key)
        return []
    if api_config.get("auth_type") == "csv_only" or not api_config.get("catalog_endpoint"):
        logger.info("menu extract: '%s' has no catalog API", key)
        return []

    # Fill every id-shaped credential slot with what we have. base_url / endpoint
    # templates ({merchant_id}, {location_id}, {org_id}, ...) are resolved from
    # this dict by GenericRESTConnector._build_url, and POS systems disagree on
    # which slot the stored id belongs to, so we populate all the common ones.
    fill = merchant_id or location_id
    credentials = {
        "access_token": access_token,
        "api_key": access_token,
        "merchant_id": merchant_id or fill,
        "location_id": location_id or fill,
        "restaurant_id": fill,
        "org_id": fill,
        "retailer_id": fill,
    }

    conn_config = POSConnectionConfig(
        system_key=key,
        system_name=key.title(),
        tier=api_config.get("tier", 3),
        auth_method=api_config.get("auth_type", "bearer"),
        base_url=api_config.get("base_url", ""),
        credentials=credentials,
        merchant_id=merchant_id or fill,
        org_id=fill,
    )

    try:
        connector = GenericRESTConnector(conn_config, api_config)
        raw = await connector.fetch_catalog()
    except Exception as e:  # noqa: BLE001 — never let a POS error break prompt build
        logger.warning("menu extract: '%s' catalog fetch failed: %s", key, e)
        return []

    items = _coerce_catalog(raw, max_items=max_items)
    logger.info("menu extract: '%s' → %d items", key, len(items))
    return items


def _coerce_catalog(raw: Any, *, max_items: int) -> list[dict]:
    """Map raw catalog records into deduped {name, price?, category?} items."""
    records = _flatten_records(raw)
    out: list[dict] = []
    seen: set[str] = set()
    dropped = 0

    for rec in records:
        if not isinstance(rec, dict):
            continue
        name = _extract_name(rec)
        if not name:
            continue
        dedup_key = name.lower()
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        if len(out) >= max_items:
            dropped += 1
            continue

        item: dict[str, Any] = {"name": name}
        external_id = _extract_external_id(rec)
        if external_id:
            item["source_external_id"] = external_id
        price = _extract_price_dollars(rec)
        if price is not None:
            item["price"] = price
        category = _extract_category(rec)
        if category:
            item["category"] = category
        out.append(item)

    if dropped:
        logger.warning(
            "menu extract: item cap %d reached — %d unique catalog items dropped",
            max_items, dropped)
    return out


def _extract_external_id(rec: dict) -> str:
    """POS catalog object id (Square/Clover expose top-level `id`)."""
    for key in ("id", "item_id", "itemId", "guid", "uuid"):
        val = rec.get(key)
        if val and isinstance(val, (str, int)):
            return str(val).strip()
    return ""


def _flatten_records(raw: Any) -> list[Any]:
    """Catalogs arrive as a flat list, or nested under menus/groups (Toast-style).

    fetch_catalog already unwraps the top-level data_key. Here we additionally
    descend one level of menu→group→items nesting when present, so deeply
    structured catalogs still yield individual items.
    """
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []

    flat: list[Any] = []
    for rec in raw:
        if isinstance(rec, dict) and ("groups" in rec or "menuGroups" in rec):
            groups = rec.get("groups") or rec.get("menuGroups") or []
            for group in groups if isinstance(groups, list) else []:
                gitems = (group.get("items") or group.get("menuItems") or []) if isinstance(group, dict) else []
                for gi in gitems if isinstance(gitems, list) else []:
                    if isinstance(gi, dict) and "category" not in gi and group.get("name"):
                        gi = {**gi, "_menu_group": group["name"]}
                    flat.append(gi)
        else:
            flat.append(rec)
    return flat


def _extract_name(rec: dict) -> str:
    # Square nests the display name under item_data; everything else is flat.
    data = rec.get("item_data") if isinstance(rec.get("item_data"), dict) else rec
    for key in ("name", "itemName", "item_name", "displayName", "title", "productName", "description"):
        val = data.get(key)
        if val:
            return str(val).strip()
    return ""


def _extract_category(rec: dict) -> str:
    for key in ("category", "categoryName", "group", "_menu_group", "department"):
        val = rec.get(key)
        if val:
            return str(val).strip()
    return ""


def _extract_price_dollars(rec: dict) -> float | None:
    """Best-effort price in dollars, or None when the POS doesn't expose one.

    Handles the three common catalog price shapes:
      - Square:  item_data.variations[].item_variation_data.price_money.amount (cents)
      - Clover:  price (integer cents)
      - generic: price / unitPrice / amount (dollars or cents string)
    """
    cents = _square_price_cents(rec)
    if cents is not None:
        return round(cents / 100, 2)

    # Clover and similar expose an integer cents `price`.
    raw_price = rec.get("price")
    if isinstance(raw_price, int) and raw_price > 0:
        # Heuristic: integers are cents (Clover, Square money). A bare 12 would
        # be $0.12, which is implausibly cheap, so this is the safe read.
        return round(raw_price / 100, 2)

    for key in ("price", "unitPrice", "unit_price", "amount", "basePrice", "default_price"):
        val = rec.get(key)
        if val is None:
            continue
        try:
            num = float(str(val).replace("$", "").replace(",", "").strip())
        except (ValueError, TypeError):
            continue
        if num > 0:
            return round(num, 2)
    return None


def _square_price_cents(rec: dict) -> int | None:
    data = rec.get("item_data")
    if not isinstance(data, dict):
        return None
    variations = data.get("variations")
    if not isinstance(variations, list):
        return None
    for var in variations:
        if not isinstance(var, dict):
            continue
        vdata = var.get("item_variation_data") or var.get("itemVariationData") or {}
        money = vdata.get("price_money") or vdata.get("priceMoney") or {}
        amount = money.get("amount")
        if isinstance(amount, int) and amount > 0:
            return amount
    return None
