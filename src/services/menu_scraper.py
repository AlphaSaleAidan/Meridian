"""
Menu Scraper — merchant website → structured menu items.

POST /api/menu/{merchant_id}/scrape hands a URL here; we fetch it (httpx,
15s timeout, 3 MB cap, public-host-only — SSRF guarded), discover likely
menu pages (same-origin links containing menu/food/order/…, max 5 pages),
pull readable text (stdlib HTMLParser — no bs4 in requirements), and run one
strict LLM extraction pass over the corpus.

LLM: DeepSeek chat (env DEEPSEEK_API_KEY — same provider phone.py uses),
``response_format={"type": "json_object"}`` (NOT json_schema; DeepSeek
doesn't support it). Items come back as {name, price, category, description,
confidence 0-1}; everything lands ``needs_review`` via menu_store — scraped
items are NEVER auto-published, and <0.7 confidence is amber-flagged.

Edge content:
  - linked PDFs: pypdf/pdfminer aren't in requirements.txt — we attempt a
    runtime import and otherwise skip the PDF and flag ``pdf_unsupported``
    rather than adding heavy deps.
  - image-only menus: when a page has almost no text but has images, the
    largest candidates are routed through menu_vision (flag ``images_used``).

Failures raise MenuScrapeError with a UI-safe message — never partial-silent.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import os
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger("meridian.services.menu_scraper")

MAX_BYTES = 3 * 1024 * 1024          # per-fetch size cap
FETCH_TIMEOUT = 15.0                 # seconds per request
MAX_PAGES = 5                        # root + discovered menu pages
MAX_IMAGES = 2                       # image-only fallback budget
MAX_CORPUS_CHARS = 24_000            # LLM input cap
MIN_TEXT_FOR_LLM = 200               # below this a page is "image-only"
LOW_CONFIDENCE = 0.7

MENU_LINK_HINTS = ("menu", "food", "order", "eat", "dine", "drink", "carte")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

_EXTRACT_SYSTEM_PROMPT = (
    "You extract restaurant menu items from scraped website text for a "
    "phone-ordering system. Return ONLY a JSON object of the form "
    '{"items": [{"name": string, "price": number or null, '
    '"category": string or null, "description": string or null, '
    '"confidence": number}]}.\n'
    "Rules:\n"
    "- price is in dollars as a plain number; null when missing, a range, or market price.\n"
    "- category is the menu section the item appears under; null if unclear.\n"
    "- description is the item's own short printed description; null if none.\n"
    "- confidence is 0-1: how sure you are this is a real orderable item with "
    "the right price. Navigation text, hours, addresses, reviews are NOT items.\n"
    "- Use exact printed names. NEVER invent items. No menu found → {\"items\": []}."
)


class MenuScrapeError(RuntimeError):
    """Raised with a UI-safe message when the scrape cannot complete."""


# ── HTML parsing (stdlib — bs4 is not in requirements) ──────────────────

class _PageParser(HTMLParser):
    """Collects visible text, anchor hrefs, and image srcs from one page."""

    _SKIP = {"script", "style", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.links: list[str] = []
        self.images: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "img" and attrs.get("src"):
            self.images.append(attrs["src"])

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth and data.strip():
            self.text_parts.append(data.strip())


def parse_page(html: str) -> tuple[str, list[str], list[str]]:
    """(visible text, links, image srcs) from raw HTML."""
    parser = _PageParser()
    try:
        parser.feed(html)
    except Exception:  # noqa: BLE001 — salvage whatever parsed before the error
        pass
    return "\n".join(parser.text_parts), parser.links, parser.images


def candidate_menu_links(base_url: str, links: list[str], limit: int = MAX_PAGES - 1) -> list[str]:
    """Same-origin links whose path/text smells like a menu page."""
    base = urlparse(base_url)
    out: list[str] = []
    seen = {base_url.rstrip("/")}
    for href in links:
        absolute = urljoin(base_url, href.strip())
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https") or parsed.netloc != base.netloc:
            continue
        clean = absolute.split("#")[0].rstrip("/")
        if clean in seen:
            continue
        if any(hint in parsed.path.lower() for hint in MENU_LINK_HINTS):
            seen.add(clean)
            out.append(clean)
            if len(out) >= limit:
                break
    return out


# ── fetching (SSRF-guarded, size-capped) ─────────────────────────────────

def _host_is_public(host: str) -> bool:
    """Resolve and require every address to be public — merchant-supplied
    URLs are fetched server-side, so private/loopback targets are refused."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        try:
            addr = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if not addr.is_global:
            return False
    return bool(infos)


def _check_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise MenuScrapeError("Please provide a full http(s) website address.")
    if not _host_is_public(parsed.hostname):
        raise MenuScrapeError("That address can't be reached from our servers.")


async def _fetch(client: httpx.AsyncClient, url: str) -> tuple[str, bytes]:
    """(content-type, body ≤3MB). Every redirect hop's host is re-checked."""
    _check_url(url)
    try:
        async with client.stream("GET", url) as res:
            final_host = res.request.url.host or ""
            if str(res.request.url) != url and not _host_is_public(final_host):
                raise MenuScrapeError("That address can't be reached from our servers.")
            if res.status_code >= 400:
                raise MenuScrapeError(
                    f"The website responded with an error ({res.status_code}).")
            body = b""
            async for chunk in res.aiter_bytes():
                body += chunk
                if len(body) > MAX_BYTES:
                    break
            return (res.headers.get("content-type", "").lower(), body[:MAX_BYTES])
    except httpx.HTTPError as exc:
        raise MenuScrapeError(f"Couldn't load that website: {exc.__class__.__name__}") from exc


def _pdf_to_text(data: bytes) -> str | None:
    """Best-effort PDF text.

    pypdf IS in requirements.txt now. It was deliberately left out to avoid
    "heavy deps", but that did not make PDFs unsupported — it made support
    ACCIDENTAL, because pypdf arrives transitively via browser-use in some
    environments and not others. The same menu upload parsed in dev and was
    flagged pdf_unsupported in production.

    The import stays at runtime and the fallbacks stay in place, so a stripped
    install still degrades instead of crashing. Three distinct answers, and
    the caller depends on the difference:

        text  the PDF was read
        ""    it was read and there was nothing usable in it (or it is corrupt)
        None  no PDF library at all → the caller flags pdf_unsupported
    """
    try:
        import io as _io

        from pypdf import PdfReader  # type: ignore[import-not-found]
        reader = PdfReader(_io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages[:20])
    except ImportError:
        pass
    except Exception:  # noqa: BLE001 — corrupt PDF
        return ""
    try:
        import io as _io

        from pdfminer.high_level import extract_text  # type: ignore[import-not-found]
        return extract_text(_io.BytesIO(data), maxpages=20)
    except ImportError:
        return None
    except Exception:  # noqa: BLE001
        return ""


# ── LLM extraction ───────────────────────────────────────────────────────

def parse_llm_items(content: str) -> list[dict]:
    """Model JSON → normalized item dicts (confidence clamped, junk dropped)."""
    try:
        parsed = json.loads(content)
    except ValueError as exc:
        raise MenuScrapeError("Menu extraction returned unreadable output — try again.") from exc
    raw_items = parsed.get("items") if isinstance(parsed, dict) else parsed
    items: list[dict] = []
    for it in raw_items if isinstance(raw_items, list) else []:
        if not isinstance(it, dict):
            continue
        name = str(it.get("name") or "").strip()
        if not name or len(name) > 120:
            continue
        item: dict = {"name": name}
        price = it.get("price")
        if isinstance(price, (int, float)) and price > 0:
            item["price"] = round(float(price), 2)
        for key, cap in (("category", 60), ("description", 300)):
            val = str(it.get(key) or "").strip()
            if val and val.lower() != "null":
                item[key] = val[:cap]
        conf = it.get("confidence")
        item["confidence"] = max(0.0, min(1.0, float(conf))) \
            if isinstance(conf, (int, float)) else 0.5
        items.append(item)
    return items


async def _extract_items_llm(client: httpx.AsyncClient, corpus: str) -> list[dict]:
    if not DEEPSEEK_API_KEY:
        raise MenuScrapeError("Menu extraction isn't configured (missing DEEPSEEK_API_KEY).")
    try:
        res = await client.post(
            f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={
                "model": DEEPSEEK_MODEL,
                "temperature": 0,
                "max_tokens": 4000,
                # json_object, NOT json_schema — DeepSeek rejects the latter.
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
                    {"role": "user", "content": corpus[:MAX_CORPUS_CHARS]},
                ],
            },
            timeout=60.0,
        )
    except httpx.HTTPError as exc:
        raise MenuScrapeError("Menu extraction timed out — try again in a minute.") from exc
    if res.status_code != 200:
        logger.warning("menu scrape LLM %s: %s", res.status_code, res.text[:300])
        raise MenuScrapeError("Menu extraction failed — try again in a minute.")
    try:
        content = res.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise MenuScrapeError("Menu extraction returned unreadable output — try again.") from exc
    return parse_llm_items(content)


# ── orchestrator ─────────────────────────────────────────────────────────

async def scrape_menu(url: str) -> dict:
    """Fetch → discover → extract. Returns {items, pages, flags} or raises
    MenuScrapeError. Items are agent-shape dollars + confidence — the route
    lands them via menu_store.ingest_items(source='scrape')."""
    flags: list[str] = []
    corpus_parts: list[str] = []
    pages_fetched: list[str] = []
    image_urls: list[str] = []
    pdf_urls: list[str] = []

    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT, follow_redirects=True,
        headers={"User-Agent": "MeridianMenuBot/1.0 (+https://meridian.tips)"},
    ) as client:
        ctype, body = await _fetch(client, url)
        if "pdf" in ctype:
            pdf_urls.append(url)
            to_visit: list[str] = []
        else:
            text, links, images = parse_page(body.decode("utf-8", errors="replace"))
            corpus_parts.append(text)
            pages_fetched.append(url)
            image_urls.extend(urljoin(url, src) for src in images[:10])
            to_visit = candidate_menu_links(url, links)
            pdf_urls.extend(link for link in to_visit if link.lower().endswith(".pdf"))
            to_visit = [link for link in to_visit if not link.lower().endswith(".pdf")]

        for link in to_visit:
            try:
                sub_ctype, sub_body = await _fetch(client, link)
            except MenuScrapeError:
                continue  # one bad subpage never sinks the scrape
            if "pdf" in sub_ctype:
                pdf_urls.append(link)
                continue
            sub_text, _, sub_images = parse_page(sub_body.decode("utf-8", errors="replace"))
            corpus_parts.append(f"\n\n=== {link} ===\n{sub_text}")
            pages_fetched.append(link)
            image_urls.extend(urljoin(link, src) for src in sub_images[:10])

        for pdf_url in pdf_urls[:2]:
            try:
                _, pdf_body = await _fetch(client, pdf_url)
            except MenuScrapeError:
                continue
            pdf_text = _pdf_to_text(pdf_body)
            if pdf_text is None:
                if "pdf_unsupported" not in flags:
                    flags.append("pdf_unsupported")
            elif pdf_text.strip():
                corpus_parts.append(f"\n\n=== {pdf_url} (PDF) ===\n{pdf_text}")
                pages_fetched.append(pdf_url)

        corpus = "\n".join(part for part in corpus_parts if part).strip()

        # Image-only menus: barely any text → try the vision model on the
        # most menu-looking images.
        if len(corpus) < MIN_TEXT_FOR_LLM and image_urls:
            items = await _extract_from_images(client, image_urls, flags)
            if items:
                return {"items": items, "pages": pages_fetched, "flags": flags}

        if len(corpus) < MIN_TEXT_FOR_LLM:
            hint = " (its menu appears to be a PDF we can't read yet)" \
                if "pdf_unsupported" in flags else ""
            raise MenuScrapeError(
                f"Couldn't find readable menu content on that website{hint}. "
                "Try a direct link to the menu page, or upload a photo/CSV instead.")

        items = await _extract_items_llm(client, corpus)

    if not items:
        raise MenuScrapeError(
            "No menu items were found on that website. Try a direct link to "
            "the menu page, or upload a photo/CSV instead.")
    if any(i.get("confidence", 0) < LOW_CONFIDENCE for i in items):
        flags.append("low_confidence_items")
    return {"items": items, "pages": pages_fetched, "flags": flags}


async def _extract_from_images(client: httpx.AsyncClient, image_urls: list[str],
                               flags: list[str]) -> list[dict]:
    """Route apparent image-only menus through the wired vision extractor."""
    from .menu_vision import MenuVisionError, extract_menu_from_image

    ranked = sorted(
        dict.fromkeys(image_urls),
        key=lambda u: (not any(h in u.lower() for h in MENU_LINK_HINTS)),
    )
    items: list[dict] = []
    for img_url in ranked[:MAX_IMAGES]:
        try:
            ctype, body = await _fetch(client, img_url)
            if not ctype.startswith("image/"):
                continue
            extracted = await extract_menu_from_image(body, ctype)
            items.extend({**it, "confidence": 0.6} for it in extracted)
        except (MenuScrapeError, MenuVisionError) as exc:
            logger.info("menu scrape image pass failed for %s: %s", img_url, exc)
            if "image_menu_unreadable" not in flags:
                flags.append("image_menu_unreadable")
    if items:
        flags.append("images_used")
    return items
