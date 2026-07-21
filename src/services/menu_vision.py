"""
Menu-from-photo extraction (supplementary menu builder).

A merchant photographs a paper/printed menu; we send the image to an
OpenAI-compatible vision model (gpt-4o by default) and get back the agent's
``{name, price?, category?}`` menu-item shape — the SAME shape
``menu_extractor.extract_menu_items`` produces from a POS catalog, so the phone
agent prompt picks it up with no other changes.

This is *supplementary* to the POS-catalog auto-builder: scanned items are
merged onto whatever menu already exists (see ``merge_menu_items``) rather than
replacing it, so a merchant can scan a daily-specials board on top of their POS
menu.

The vision call is isolated in ``extract_menu_from_image`` so the merge logic
(``merge_menu_items``, ``normalize_items``) is unit-testable without a network.
"""
from __future__ import annotations

import base64
import json
import logging
import os

import httpx

logger = logging.getLogger("meridian.services.menu_vision")

# Vision models that can read an image. Configurable so we can move off gpt-4o
# without a code change. MENU_VISION_* vars are dedicated so vision can point
# at a different OpenAI-compatible provider (e.g. Moonshot/Kimi) without
# redirecting the global OPENAI_* fallback path, whose model names would not
# exist on the other provider.
_MODEL = os.getenv("MENU_VISION_MODEL", "gpt-4o")
_BASE_URL = (
    os.getenv("MENU_VISION_BASE_URL")
    or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
).rstrip("/")

# Reasoning models constrain sampling params: Moonshot's kimi-k3 rejects any
# temperature except 1 ("invalid temperature: only 1 is allowed"), and its
# reasoning tokens eat into max_tokens before the JSON comes out. Both knobs
# follow the provider choice, defaulting to the gpt-4o values.
def _vision_temperature() -> float:
    try:
        return float(os.getenv("MENU_VISION_TEMPERATURE", "0"))
    except ValueError:
        return 0.0


def _vision_max_tokens() -> int:
    try:
        return int(os.getenv("MENU_VISION_MAX_TOKENS", "4000"))
    except ValueError:
        return 4000


_SUPPORTED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_ITEMS = 200

_SYSTEM_PROMPT = (
    "You are a menu digitizer for a restaurant phone-ordering system. "
    "Read the menu in the image and extract every orderable item.\n"
    "Return ONLY a JSON object of the form "
    '{"items": [{"name": string, "price": number or null, "category": string or null}]}.\n'
    "Rules:\n"
    "- price is in dollars as a plain number (12.5, not \"$12.50\"). "
    "If a price is missing, a range, or market-price, use null.\n"
    "- category is the menu section the item appears under (e.g. \"Appetizers\", "
    '"Mains", "Drinks"); use null if there is no section.\n'
    "- Use the exact item name as printed. Do NOT include descriptions, "
    "ingredients, calorie counts, hours, addresses, or phone numbers.\n"
    "- Do NOT invent items that are not visible. If the image is not a menu, "
    'return {"items": []}.'
)


class MenuVisionError(RuntimeError):
    """Raised when the menu image cannot be processed."""


def _coerce_price(raw) -> float | None:
    """Best-effort dollars-as-float; tolerate "$12.50", "12,50", "" -> None."""
    if raw is None:
        return None
    # str() handles int/float too (no "$"/"," in their repr), so one path covers all.
    s = str(raw).strip().replace("$", "").replace(",", ".")
    if not s:
        return None
    try:
        v = float(s)
        return round(v, 2) if v >= 0 else None
    except ValueError:
        return None


def normalize_items(raw_items) -> list[dict]:
    """Coerce model output into the canonical ``{name, price?, category?}`` shape.

    Drops anything without a usable name, clamps the list length, and strips
    empties. Mirrors the contract of ``menu_extractor.extract_menu_items``.
    """
    out: list[dict] = []
    if not isinstance(raw_items, list):
        return out
    for it in raw_items:
        if not isinstance(it, dict):
            continue
        name = str(it.get("name") or "").strip()
        if not name or len(name) > 120:
            continue
        item: dict = {"name": name}
        price = _coerce_price(it.get("price"))
        if price is not None:
            item["price"] = price
        category = str(it.get("category") or "").strip()
        if category and category.lower() != "null":
            item["category"] = category[:60]
        out.append(item)
        if len(out) >= _MAX_ITEMS:
            break
    return out


def merge_menu_items(existing: list[dict] | None, scanned: list[dict]) -> list[dict]:
    """Merge scanned items onto an existing menu (supplementary, not replace).

    Dedupe is by case-insensitive name. An existing item wins on identity but a
    scanned item fills in a missing price/category (so re-scanning a board that
    now shows prices enriches the entry). Returns a new list; inputs untouched.
    """
    merged: list[dict] = []
    index: dict[str, int] = {}
    for it in existing or []:
        if not isinstance(it, dict) or not str(it.get("name") or "").strip():
            continue
        copy = dict(it)
        merged.append(copy)
        index[str(copy["name"]).strip().lower()] = len(merged) - 1

    for it in scanned:
        key = str(it.get("name") or "").strip().lower()
        if not key:
            continue
        if key in index:
            cur = merged[index[key]]
            if cur.get("price") is None and it.get("price") is not None:
                cur["price"] = it["price"]
            if not cur.get("category") and it.get("category"):
                cur["category"] = it["category"]
        else:
            merged.append(dict(it))
            index[key] = len(merged) - 1
    return merged


async def extract_menu_from_image(image_bytes: bytes, content_type: str) -> list[dict]:
    """Send the image to the vision model and return normalized menu items.

    Raises ``MenuVisionError`` on missing key, unsupported type, or a model/
    transport failure so the route can surface a clean reason to the UI.
    """
    api_key = (
        os.getenv("MENU_VISION_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
    )
    if not api_key:
        raise MenuVisionError(
            "vision model not configured (MENU_VISION_API_KEY / OPENAI_API_KEY missing)"
        )

    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype not in _SUPPORTED_TYPES:
        raise MenuVisionError(f"unsupported image type: {ctype or 'unknown'}")
    if not image_bytes:
        raise MenuVisionError("empty image")

    data_uri = f"data:{ctype};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    payload = {
        "model": _MODEL,
        "temperature": _vision_temperature(),
        "max_tokens": _vision_max_tokens(),
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Digitize this menu."},
                    {"type": "image_url", "image_url": {"url": data_uri, "detail": "high"}},
                ],
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(
                f"{_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise MenuVisionError(f"vision request failed: {exc}") from exc

    if res.status_code != 200:
        logger.warning("menu vision %s: %s", res.status_code, res.text[:300])
        raise MenuVisionError(f"vision model returned {res.status_code}")

    try:
        content = res.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except (KeyError, IndexError, ValueError) as exc:
        raise MenuVisionError("could not parse vision model response") from exc

    items = normalize_items(parsed.get("items") if isinstance(parsed, dict) else parsed)
    logger.info("menu vision extracted %d items via %s", len(items), _MODEL)
    return items
