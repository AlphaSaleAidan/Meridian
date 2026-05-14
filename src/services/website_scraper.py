"""
Merchant website + Google business scraper.

Scrapes existing merchant websites for business info and Google Maps
for reviews. Uses Qwen (local LLM) for copy generation — zero API cost.
"""

import json
import logging
import os
import re
from typing import Optional
from urllib.parse import urljoin, quote_plus

import httpx

logger = logging.getLogger("meridian.services.website_scraper")


async def scrape_website(url: str) -> dict:
    """Scrape a business website for structured info."""
    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

        result = {
            "business_name": _extract_title(html),
            "phone": _extract_phone(html),
            "email": _extract_email(html),
            "address": _extract_address(html),
            "about": _extract_about(html),
            "hours": {},
            "logo_url": _extract_logo(html, url),
            "social_links": _extract_social_links(html),
            "services": [],
        }

        json_ld = _extract_json_ld(html)
        if json_ld:
            if json_ld.get("name"):
                result["business_name"] = json_ld["name"]
            if json_ld.get("telephone"):
                result["phone"] = json_ld["telephone"]
            if json_ld.get("email"):
                result["email"] = json_ld["email"]
            addr = json_ld.get("address", {})
            if isinstance(addr, dict) and addr.get("streetAddress"):
                parts = [addr.get("streetAddress", ""), addr.get("addressLocality", ""),
                         addr.get("addressRegion", ""), addr.get("postalCode", "")]
                result["address"] = ", ".join(p for p in parts if p)
            if json_ld.get("description"):
                result["about"] = json_ld["description"][:500]
            hours = json_ld.get("openingHoursSpecification", [])
            if hours:
                result["hours"] = _parse_schema_hours(hours)

        return result
    except Exception as e:
        logger.error(f"Scrape failed for {url}: {e}")
        return {"error": str(e)}


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    if m:
        title = m.group(1).strip()
        for sep in [" | ", " - ", " — ", " · "]:
            if sep in title:
                return title.split(sep)[0].strip()
        return title
    return ""


def _extract_phone(html: str) -> str:
    m = re.search(r'href="tel:([^"]+)"', html)
    if m:
        return m.group(1).strip()
    m = re.search(r"(\+?1?\s*[\-.]?\s*\(?\d{3}\)?\s*[\-.]?\s*\d{3}\s*[\-.]?\s*\d{4})", html)
    return m.group(1).strip() if m else ""


def _extract_email(html: str) -> str:
    m = re.search(r'href="mailto:([^"?]+)"', html)
    if m:
        return m.group(1).strip()
    m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)
    return m.group(0) if m else ""


def _extract_address(html: str) -> str:
    m = re.search(r'<address[^>]*>(.*?)</address>', html, re.I | re.S)
    if m:
        text = re.sub(r"<[^>]+>", " ", m.group(1))
        return " ".join(text.split())[:200]
    return ""


def _extract_about(html: str) -> str:
    for pattern in [
        r'(?:about|description|who-we-are)[^>]*>([^<]{50,500})',
        r'<meta\s+name="description"\s+content="([^"]+)"',
        r'<meta\s+property="og:description"\s+content="([^"]+)"',
    ]:
        m = re.search(pattern, html, re.I)
        if m:
            return m.group(1).strip()[:500]
    return ""


def _extract_logo(html: str, base_url: str) -> str:
    for pattern in [
        r'<link[^>]+rel="icon"[^>]+href="([^"]+)"',
        r'<img[^>]+class="[^"]*logo[^"]*"[^>]+src="([^"]+)"',
        r'<meta\s+property="og:image"\s+content="([^"]+)"',
    ]:
        m = re.search(pattern, html, re.I)
        if m:
            src = m.group(1)
            if src.startswith("http"):
                return src
            return urljoin(base_url, src)
    return ""


def _extract_social_links(html: str) -> dict:
    socials = {}
    patterns = {
        "instagram": r'href="(https?://(?:www\.)?instagram\.com/[^"]+)"',
        "facebook": r'href="(https?://(?:www\.)?facebook\.com/[^"]+)"',
        "twitter": r'href="(https?://(?:www\.)?(?:twitter|x)\.com/[^"]+)"',
        "yelp": r'href="(https?://(?:www\.)?yelp\.com/[^"]+)"',
        "tiktok": r'href="(https?://(?:www\.)?tiktok\.com/[^"]+)"',
    }
    for platform, pattern in patterns.items():
        m = re.search(pattern, html, re.I)
        if m:
            socials[platform] = m.group(1)
    return socials


def _extract_json_ld(html: str) -> Optional[dict]:
    for m in re.finditer(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(m.group(1))
            if isinstance(data, list):
                data = data[0]
            t = data.get("@type", "")
            if t in ("LocalBusiness", "Restaurant", "FoodEstablishment",
                      "AutoRepair", "CafeOrCoffeeShop", "Store", "Organization"):
                return data
        except Exception:
            continue
    return None


def _parse_schema_hours(specs) -> dict:
    days_map = {
        "Monday": "monday", "Tuesday": "tuesday", "Wednesday": "wednesday",
        "Thursday": "thursday", "Friday": "friday", "Saturday": "saturday",
        "Sunday": "sunday",
    }
    hours = {}
    if isinstance(specs, list):
        for spec in specs:
            days = spec.get("dayOfWeek", [])
            if isinstance(days, str):
                days = [days]
            opens = spec.get("opens", "")
            closes = spec.get("closes", "")
            for day in days:
                key = days_map.get(day.split("/")[-1], day.lower())
                hours[key] = f"{opens}-{closes}"
    return hours


async def scrape_google_reviews(business_name: str, address: str = "") -> dict:
    """Scrape Google Maps for rating and reviews. No API key needed."""
    query = f"{business_name} {address}".strip()
    search_url = f"https://www.google.com/maps/search/{quote_plus(query)}"

    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        ) as client:
            resp = await client.get(search_url)
            html = resp.text

        result: dict = {
            "google_rating": None,
            "google_review_count": None,
            "google_reviews": [],
            "google_place_id": None,
        }

        # Extract rating from the page data — Google embeds structured data in the HTML
        # Pattern: "X.X stars" or rating value in JSON-like structures
        rating_patterns = [
            r'"(\d\.\d)" stars',
            r'(\d\.\d)\s*stars?\s*[-·]\s*(\d[\d,]*)\s*reviews?',
            r'"averageRating":(\d\.\d)',
            r'"ratingValue":"(\d\.\d)"',
            r'aria-label="(\d\.\d) stars',
            r'class="[^"]*"[^>]*>(\d\.\d)</span>\s*<span[^>]*>\((\d[\d,]*)\)',
        ]
        for pat in rating_patterns:
            m = re.search(pat, html, re.I)
            if m:
                result["google_rating"] = float(m.group(1))
                if m.lastindex and m.lastindex >= 2:
                    result["google_review_count"] = int(m.group(2).replace(",", ""))
                break

        # Try to extract review count separately if we got rating but not count
        if result["google_rating"] and not result["google_review_count"]:
            count_patterns = [
                r'(\d[\d,]*)\s*reviews?',
                r'"reviewCount":"?(\d[\d,]*)"?',
                r'"userRatingCount":(\d+)',
            ]
            for pat in count_patterns:
                m = re.search(pat, html, re.I)
                if m:
                    result["google_review_count"] = int(m.group(1).replace(",", ""))
                    break

        # Extract individual review snippets from the page
        # Google embeds review text in various data attributes and spans
        review_patterns = [
            r'"snippet":"([^"]{20,300})"[^}]*"author":"([^"]+)"[^}]*"rating":(\d)',
            r'"text":"([^"]{20,300})"[^}]*"authorName":"([^"]+)"[^}]*"starRating":(\d)',
            r'class="[^"]*review[^"]*"[^>]*>.*?<span[^>]*>([^<]{20,300})</span>.*?<span[^>]*>([^<]+)</span>',
        ]
        seen_texts = set()
        for pat in review_patterns:
            for m in re.finditer(pat, html, re.S):
                text = m.group(1).strip()
                if text in seen_texts or len(text) < 20:
                    continue
                seen_texts.add(text)
                review = {"text": text, "author": m.group(2).strip() if m.lastindex >= 2 else "Google User"}
                if m.lastindex >= 3:
                    review["rating"] = int(m.group(3))
                else:
                    review["rating"] = 5
                review["date"] = ""
                result["google_reviews"].append(review)
                if len(result["google_reviews"]) >= 10:
                    break
            if result["google_reviews"]:
                break

        # Extract place ID if present
        place_m = re.search(r'place_id[=:]"?(ChIJ[a-zA-Z0-9_-]+)"?', html)
        if place_m:
            result["google_place_id"] = place_m.group(1)

        logger.info(f"Google scrape for '{business_name}': rating={result['google_rating']}, reviews={len(result['google_reviews'])}")
        return result

    except Exception as e:
        logger.warning(f"Google scrape failed for '{business_name}': {e}")
        return {
            "google_rating": None,
            "google_review_count": None,
            "google_reviews": [],
            "google_place_id": None,
        }


async def generate_copy(business_data: dict) -> dict:
    """Use local Qwen to generate polished website copy."""
    try:
        from src.inference.local_llm import generate
        prompt = f"""You are writing website copy for a local business.

Business name: {business_data.get('business_name', 'Our Business')}
Business type: {business_data.get('business_type', 'restaurant')}
About: {business_data.get('about', '')}
Location: {business_data.get('address', '')}

Write these three things:
1. A punchy hero headline (max 8 words, no punctuation at end)
2. A supporting subheadline (max 15 words, one sentence)
3. A clean about paragraph (2-3 sentences, warm and professional)

Return ONLY JSON: {{"headline": "", "subheadline": "", "about": ""}}"""

        raw = generate(
            prompt,
            system="You are a premium copywriter. Return only valid JSON, no markdown.",
            max_tokens=300,
            temperature=0.7,
        )

        m = re.search(r"\{[^}]+\}", raw, re.S)
        if m:
            return json.loads(m.group(0))
        return {"headline": business_data.get("business_name", "Welcome"),
                "subheadline": "Discover what makes us special",
                "about": business_data.get("about", "")}
    except Exception as e:
        logger.warning(f"LLM copy generation failed: {e}")
        return {
            "headline": business_data.get("business_name", "Welcome"),
            "subheadline": "Discover what makes us special",
            "about": business_data.get("about", ""),
        }


def generate_slug(business_name: str) -> str:
    slug = business_name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    slug = slug.strip("-")[:50]
    return slug or "my-business"
