"""
Per-restaurant personalization brief builder.

Fetches the merchant's website (homepage + cheap sub-pages like /about and /menu),
strips HTML to plain text, then calls the configured LLM gateway to produce a
≤120-word plain-prose brief capturing:

  - cuisine type and vibe / tone of voice
  - signature or popular items
  - anything distinctive (neighborhood story, dietary specialties, local reputation)

Usage
-----
    from restaurant_brief import build_brief

    brief = await build_brief(business_name, website_url, menu_items)
    # Returns "" on any failure — never raises into the call path.

Reviews plug-in
---------------
The ``reviews`` keyword argument is accepted but intentionally unused in this
phase (Google Reviews / Yelp are explicitly out of scope for now). The design
point for plugging them in later:

  1. Populate ``reviews`` with a list of short review-text strings, e.g.:
         ["Great tacos, very fresh ingredients", "Cozy spot, friendly staff"]
  2. The summarisation prompt already has a ``reviews_block`` slot — that block
     is empty when ``reviews`` is None/empty, and populated otherwise.
  3. No other changes needed: the brief length cap and failure handling
     work identically regardless of source.

Call path safety
----------------
``build_brief`` never raises. Any exception is caught, logged at WARNING/ERROR
level, and "" is returned. An empty brief leaves both prompt paths completely
unchanged (byte-for-byte identical output).
"""

import logging
import os
import re
from typing import Optional

logger = logging.getLogger("meridian.phone_agent.restaurant_brief")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

_BRIEF_MAX_WORDS = 120
_WEBSITE_TEXT_LIMIT = 4000   # chars fed to the LLM after HTML stripping
_FETCH_TIMEOUT = 20.0         # seconds for all website fetches combined


# ── SSRF guard ────────────────────────────────────────────────────────────────

def _is_private_url(url: str) -> bool:
    """Block private/internal IP targets (SSRF guard).

    Mirrors the logic in src/api/auth.py ``is_private_url`` but kept local so
    this module is self-contained in the services/phone_agent package.
    """
    from ipaddress import ip_address, ip_network
    from urllib.parse import urlparse
    import socket

    _PRIVATE: list = [
        ip_network("10.0.0.0/8"),
        ip_network("172.16.0.0/12"),
        ip_network("192.168.0.0/16"),
        ip_network("127.0.0.0/8"),
        ip_network("169.254.0.0/16"),
        ip_network("::1/128"),
        ip_network("fc00::/7"),
    ]
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return True
    if hostname.lower() in ("localhost", "metadata.google.internal"):
        return True
    try:
        addr = ip_address(hostname)
        return any(addr in net for net in _PRIVATE)
    except ValueError:
        pass
    try:
        for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
            if any(ip_address(sockaddr[0]) in net for net in _PRIVATE):
                return True
    except Exception:  # noqa: BLE001
        pass
    return False


# ── Website fetching ──────────────────────────────────────────────────────────

async def _fetch_one_page(url: str, client) -> str:
    """Fetch a single URL, following redirects with SSRF guard. Returns "" on any error."""
    try:
        import httpx
        for _ in range(4):  # max redirect hops
            resp = await client.get(
                url,
                headers={"User-Agent": "MeridianBot/1.0 (restaurant-brief)"},
                follow_redirects=False,
            )
            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("location", "")
                if not loc:
                    break
                next_url = str(httpx.URL(url).join(loc))
                if _is_private_url(next_url):
                    logger.debug("_fetch_one_page: redirect to private URL blocked: %s", next_url)
                    return ""
                url = next_url
                continue
            if resp.status_code == 200:
                return resp.text
            return ""
    except Exception as exc:  # noqa: BLE001
        logger.debug("_fetch_one_page failed %s: %s", url, exc)
    return ""


def _html_to_text(html: str) -> str:
    """Strip tags and collapse whitespace. Falls back to regex if bs4 is unavailable."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
    except Exception:  # noqa: BLE001
        text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s{2,}", " ", text).strip()


async def _fetch_website_text(website_url: str) -> str:
    """Fetch homepage + cheap sub-pages (/about, /menu) with a shared timeout.

    Stops early when the combined text reaches _WEBSITE_TEXT_LIMIT so we never
    send more than necessary to the LLM. Returns "" on any failure.
    """
    if not website_url:
        return ""
    if _is_private_url(website_url):
        logger.warning("build_brief: website_url blocked by SSRF guard: %s", website_url)
        return ""
    try:
        import httpx
        root = website_url.rstrip("/")
        pages_to_try = [root, f"{root}/about", f"{root}/menu"]
        combined: list[str] = []
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT, follow_redirects=False) as client:
            for page_url in pages_to_try:
                if sum(len(t) for t in combined) >= _WEBSITE_TEXT_LIMIT:
                    break
                html = await _fetch_one_page(page_url, client)
                if html:
                    combined.append(_html_to_text(html))
        full = " ".join(combined)
        return full[:_WEBSITE_TEXT_LIMIT]
    except Exception as exc:  # noqa: BLE001
        logger.debug("_fetch_website_text error: %s", exc)
        return ""


# ── Menu summary ──────────────────────────────────────────────────────────────

def _menu_summary(menu_items: list[dict]) -> str:
    """Compact text list of the menu for the summarisation prompt (capped at 30 items)."""
    lines = []
    for item in (menu_items or [])[:30]:
        name = item.get("name", "")
        if not name:
            continue
        line = f"- {name}"
        price = item.get("price")
        if price:
            try:
                line += f" (${float(price):.2f})"
            except (TypeError, ValueError):
                pass
        lines.append(line)
    return "\n".join(lines) if lines else "(no menu items provided)"


# ── LLM call ──────────────────────────────────────────────────────────────────

async def _call_llm(prompt: str) -> str:
    """POST to the DeepSeek-compatible gateway. Returns "" on any failure."""
    if not DEEPSEEK_API_KEY:
        logger.debug("build_brief: DEEPSEEK_API_KEY not set — skipping LLM summarisation")
        return ""
    try:
        import httpx
        payload = {
            "model": DEEPSEEK_MODEL,
            "max_tokens": 200,
            "temperature": 0.4,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
        if resp.status_code != 200:
            logger.warning("build_brief: LLM gateway %d: %s", resp.status_code, resp.text[:120])
            return ""
        return (resp.json()["choices"][0]["message"].get("content") or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("build_brief: LLM call failed: %s", exc)
        return ""


# ── Public API ────────────────────────────────────────────────────────────────

async def build_brief(
    business_name: str,
    website_url: str,
    menu_items: list[dict],
    *,
    reviews: Optional[list[str]] = None,  # reserved — see module docstring for plug-in guide
) -> str:
    """Generate a ≤120-word personalization brief for a restaurant phone agent.

    Fetches the website, composes a summarisation prompt with the menu (and
    optional reviews), calls the LLM gateway, and returns plain-prose output.

    Always returns "" on any failure — never raises into the call path.

    Args:
        business_name: Restaurant name (for the prompt context).
        website_url: Public URL to fetch. Guarded against SSRF. May be "".
        menu_items: List of menu item dicts from phone_agent_config.
        reviews: (Reserved) List of review-text snippets. Currently unused;
                 accepted so the signature is stable when a reviews source is
                 wired in. Pass e.g. ``["Fresh ingredients", "Cozy atmosphere"]``.

    Returns:
        Plain-prose brief string, or "" if generation failed / no content found.
    """
    try:
        website_text = await _fetch_website_text(website_url or "")
        menu_text = _menu_summary(menu_items)

        if not website_text and not menu_items:
            logger.debug(
                "build_brief: no website content and no menu for '%s' — returning empty",
                business_name,
            )
            return ""

        # Reviews block — empty now; filled when a reviews source is plugged in.
        reviews_block = ""
        if reviews:
            snippets = "\n".join(f"- {r}" for r in reviews[:20])
            reviews_block = f"\n\nSAMPLE CUSTOMER REVIEWS:\n{snippets}"

        prompt = (
            f"You are writing a SHORT internal brief for a restaurant phone agent.\n\n"
            f"RESTAURANT: {business_name}\n\n"
            f"MENU:\n{menu_text}\n\n"
            + (f"WEBSITE CONTENT (excerpts):\n{website_text}\n\n" if website_text else "")
            + reviews_block
            + "\n\nWrite a brief (≤120 words, plain prose, NO markdown, NO bullet points, "
            "NO headers) that captures: the cuisine type and vibe/tone of voice, signature "
            "or popular items, and anything distinctive (neighborhood story, dietary "
            "specialties, local reputation). Write it so a phone agent can sound warm, "
            "personal, and knowledgeable about this specific restaurant."
        )

        brief = await _call_llm(prompt)
        if not brief:
            return ""

        # Hard backstop: clip to ~120 words in case the model overshoots.
        words = brief.split()
        if len(words) > _BRIEF_MAX_WORDS + 20:
            brief = " ".join(words[:_BRIEF_MAX_WORDS]) + "…"

        logger.info(
            "build_brief: generated %d-word brief for '%s' (website=%s)",
            len(brief.split()), business_name, bool(website_text),
        )
        return brief

    except Exception as exc:  # noqa: BLE001 — never raise into the call path
        logger.error("build_brief: unexpected error for '%s': %s", business_name, exc)
        return ""
