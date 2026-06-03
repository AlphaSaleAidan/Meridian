"""
Business Knowledge Agent — Training Data Scraper
Uses Crawl4AI for async web crawling of business intelligence sources.

Usage:
    pip install crawl4ai
    python scraper.py --sources all --output ./data
    python scraper.py --sources mckinsey,hbr --output ./data --max-pages 20
"""
import argparse
import asyncio
import hashlib
import json
import re
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
    HAS_CRAWL4AI = True
except ImportError:
    HAS_CRAWL4AI = False


try:
    from sources import SOURCES
except ImportError:
    from .sources import SOURCES

CLEANING_PATTERNS = [
    r"<script[\s\S]*?</script>",
    r"<style[\s\S]*?</style>",
    r"<nav[\s\S]*?</nav>",
    r"<footer[\s\S]*?</footer>",
    r"<header[\s\S]*?</header>",
    r"<!--[\s\S]*?-->",
    r"\s{3,}",
]


def clean_text(raw: str) -> str:
    text = raw
    for pat in CLEANING_PATTERNS:
        text = re.sub(pat, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Category -> keyword list. The previous implementation used `kw in lower`
# substring matching, which mistags any text containing common English
# substrings — e.g. "said" → analytics because "said" contains "ai", which
# was on the analytics keyword list. The on-disk data/scraped/ corpus is
# not affected (the daemon writes tags from source.topics directly and never
# calls this function; the one-shot scraper produced only 6 of 282 files),
# so this is a forward fix — it prevents future mistagging of new content.
# The matcher below uses word-boundary regex and drops the bare "ai"
# keyword; its longer companion "artificial intelligence" still triggers
# the analytics tag for AI-themed content.
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "restaurant": [
        "restaurant", "food service", "dining", "menu", "kitchen", "pos", "point of sale",
        "hospitality", "takeout", "delivery", "table", "reservation",
    ],
    "retail": [
        "retail", "store", "inventory", "supply chain", "checkout", "merchandise", "shelf",
        "foot traffic", "conversion", "customer journey",
    ],
    "analytics": [
        "analytics", "data", "insight", "forecast", "predict", "metric", "kpi", "dashboard",
        "visualization", "machine learning", "artificial intelligence",
        # Bare "ai" intentionally removed — its substring match on said/main/again
        # tagged ~44 unrelated files. "artificial intelligence" still catches the
        # real concept.
    ],
    "finance": [
        "profit", "margin", "cash flow", "burn rate", "revenue", "cogs", "cost of goods",
        "break even", "roi", "return on investment", "p&l", "profit and loss",
        "balance sheet", "accounts receivable", "payroll", "tax", "depreciation",
        "amortization", "working capital", "liquidity",
    ],
}

# Pre-compiled, word-boundary-anchored matchers, one per category.
# Re-escapes "p&l" so the `&` doesn't get regex-interpreted.
_DOMAIN_MATCHERS: dict[str, re.Pattern[str]] = {
    category: re.compile(
        r"\b(?:" + "|".join(re.escape(kw) for kw in keywords) + r")\b",
    )
    for category, keywords in _DOMAIN_KEYWORDS.items()
}


def tag_metadata(text: str, source_key: str, url: str) -> dict:
    source = SOURCES[source_key]
    lower = text.lower()
    domain_tags: list[str] = [
        category for category, matcher in _DOMAIN_MATCHERS.items()
        if matcher.search(lower) is not None
    ]

    return {
        "source": source["name"],
        "source_key": source_key,
        "url": url,
        "domain_tags": list(set(domain_tags + source.get("topics", []))),
        "word_count": len(text.split()),
        "content_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


async def crawl_source(
    source_key: str,
    max_pages: int = 10,
    output_dir: Path = Path("./data"),
) -> tuple[list[dict], int]:
    """Crawl up to max_pages from a source registry entry.

    Returns:
        (results, error_count)
            results — list of stored entry dicts (length 0..max_pages)
            error_count — number of URLs that errored (exception) OR returned
                          a non-success crawl result. Callers can distinguish
                          "source has no content" (results == [] AND
                          error_count == 0) from "source is broken"
                          (results == [] AND error_count > 0).

    Previously this returned just the list, so a fully-broken source was
    indistinguishable from an empty source — Pin #1 silent-fail.
    """
    if not HAS_CRAWL4AI:
        print(f"[SKIP] crawl4ai not installed. Run: pip install crawl4ai")
        return [], 0

    source = SOURCES[source_key]
    print(f"\n[CRAWL] {source['name']} — up to {max_pages} pages")

    results: list[dict] = []
    error_count = 0
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(
        word_count_threshold=100,
        excluded_tags=["nav", "footer", "header", "aside"],
        remove_overlay_elements=True,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        pages_crawled = 0

        for path in source["start_paths"]:
            if pages_crawled >= max_pages:
                break

            url = f"{source['base_url']}{path}"
            print(f"  [{pages_crawled + 1}/{max_pages}] {url}")

            try:
                result = await crawler.arun(url=url, config=run_config)
                if result.success and result.markdown:
                    cleaned = clean_text(result.markdown)
                    if len(cleaned.split()) < 50:
                        print(f"    [SKIP] Too short ({len(cleaned.split())} words)")
                        continue

                    meta = tag_metadata(cleaned, source_key, url)
                    entry = {
                        "id": f"{source_key}_{meta['content_hash']}",
                        "title": result.metadata.get("title", "Untitled") if result.metadata else "Untitled",
                        "content": cleaned,
                        "metadata": meta,
                    }
                    results.append(entry)
                    pages_crawled += 1

                    out_file = output_dir / f"{entry['id']}.json"
                    out_file.write_text(json.dumps(entry, indent=2))
                    print(f"    [OK] {meta['word_count']} words, tags: {meta['domain_tags']}")
                else:
                    error_count += 1
                    print(f"    [FAIL] {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
            except Exception as e:
                error_count += 1
                print(f"    [ERROR] {e}")

    return results, error_count


async def run_all(source_keys: list[str], max_pages: int, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
        "total_documents": 0,
        "total_words": 0,
        "total_errors": 0,  # NEW: aggregates per-source crawl_source error_count
    }

    for key in source_keys:
        if key not in SOURCES:
            print(f"[WARN] Unknown source: {key}")
            continue

        results, error_count = await crawl_source(
            key, max_pages=max_pages, output_dir=output_dir,
        )
        word_count = sum(r["metadata"]["word_count"] for r in results)

        manifest["sources"][key] = {
            "name": SOURCES[key]["name"],
            "documents": len(results),
            "words": word_count,
            "errors": error_count,
            "ids": [r["id"] for r in results],
        }
        manifest["total_documents"] += len(results)
        manifest["total_words"] += word_count
        manifest["total_errors"] += error_count

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(
        f"\n[DONE] {manifest['total_documents']} documents, "
        f"{manifest['total_words']} words, "
        f"{manifest['total_errors']} errors"
    )
    print(f"       Manifest: {manifest_path}")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Meridian Business Knowledge Scraper")
    parser.add_argument("--sources", default="all", help="Comma-separated source keys or 'all'")
    parser.add_argument("--output", default="./data", help="Output directory")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages per source")
    args = parser.parse_args()

    if args.sources == "all":
        keys = list(SOURCES.keys())
    else:
        keys = [k.strip() for k in args.sources.split(",")]

    asyncio.run(run_all(keys, args.max_pages, Path(args.output)))


if __name__ == "__main__":
    main()
