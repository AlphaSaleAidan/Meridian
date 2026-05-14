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


SOURCES = {
    "mckinsey": {
        "name": "McKinsey & Company",
        "base_url": "https://www.mckinsey.com",
        "start_paths": [
            "/industries/retail/our-insights",
            "/industries/consumer-packaged-goods/our-insights",
            "/capabilities/operations/our-insights",
        ],
        "topics": ["retail", "restaurant", "supply-chain", "operations", "digital-transformation"],
    },
    "hbr": {
        "name": "Harvard Business Review",
        "base_url": "https://hbr.org",
        "start_paths": [
            "/topic/subject/operations-and-supply-chain-management",
            "/topic/subject/customer-experience",
            "/topic/subject/analytics-and-data-science",
        ],
        "topics": ["analytics", "management", "customer-experience", "operations"],
    },
    "deloitte": {
        "name": "Deloitte Insights",
        "base_url": "https://www2.deloitte.com",
        "start_paths": [
            "/us/en/insights/industry/retail-distribution.html",
            "/us/en/insights/industry/restaurant-and-food-service.html",
        ],
        "topics": ["retail", "restaurant", "food-service", "technology"],
    },
    "mit_sloan": {
        "name": "MIT Sloan Management Review",
        "base_url": "https://sloanreview.mit.edu",
        "start_paths": [
            "/tag/analytics/",
            "/tag/digital-transformation/",
            "/tag/operations/",
        ],
        "topics": ["analytics", "digital-transformation", "operations", "ai"],
    },
    "a16z": {
        "name": "Andreessen Horowitz",
        "base_url": "https://a16z.com",
        "start_paths": [
            "/content-type/article/",
        ],
        "topics": ["fintech", "marketplace", "saas", "ai", "growth"],
    },
    "investopedia": {
        "name": "Investopedia",
        "base_url": "https://www.investopedia.com",
        "start_paths": [
            "/small-business-4427754",
            "/financial-analysis-4427788",
            "/terms/c/cashflow.asp",
            "/terms/b/burnrate.asp",
            "/terms/g/grossmargin.asp",
        ],
        "topics": ["finance", "small-business", "cash-flow", "margins", "accounting"],
    },
    "nra_restaurant": {
        "name": "National Restaurant Association",
        "base_url": "https://restaurant.org",
        "start_paths": [
            "/research-and-media/research",
            "/education-and-resources/running-a-restaurant",
        ],
        "topics": ["restaurant", "food-service", "labor", "food-cost", "operations"],
    },
    "score_org": {
        "name": "SCORE Small Business",
        "base_url": "https://www.score.org",
        "start_paths": [
            "/resource-library/topics/financial-management",
            "/resource-library/topics/marketing-and-sales",
        ],
        "topics": ["small-business", "finance", "marketing", "growth", "cash-flow"],
    },
    "toast_blog": {
        "name": "Toast Restaurant Blog",
        "base_url": "https://pos.toasttab.com",
        "start_paths": [
            "/blog/restaurant-management",
            "/blog/restaurant-finance",
            "/blog/restaurant-operations",
        ],
        "topics": ["restaurant", "pos", "operations", "finance", "food-cost"],
    },
    "lightspeed_blog": {
        "name": "Lightspeed Blog",
        "base_url": "https://www.lightspeedhq.com",
        "start_paths": [
            "/blog/category/restaurant-management",
            "/blog/category/retail-management",
        ],
        "topics": ["retail", "restaurant", "pos", "inventory", "analytics"],
    },
}

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


def tag_metadata(text: str, source_key: str, url: str) -> dict:
    source = SOURCES[source_key]
    domain_tags = []
    restaurant_keywords = ["restaurant", "food service", "dining", "menu", "kitchen", "pos", "point of sale",
                           "hospitality", "takeout", "delivery", "table", "reservation"]
    retail_keywords = ["retail", "store", "inventory", "supply chain", "checkout", "merchandise", "shelf",
                       "foot traffic", "conversion", "customer journey"]
    analytics_keywords = ["analytics", "data", "insight", "forecast", "predict", "metric", "kpi", "dashboard",
                          "visualization", "machine learning", "ai", "artificial intelligence"]
    financial_keywords = ["profit", "margin", "cash flow", "burn rate", "revenue", "cogs",
                          "cost of goods", "break even", "roi", "return on investment", "p&l",
                          "profit and loss", "balance sheet", "accounts receivable", "payroll",
                          "tax", "depreciation", "amortization", "working capital", "liquidity"]

    lower = text.lower()
    for kw in restaurant_keywords:
        if kw in lower:
            domain_tags.append("restaurant")
            break
    for kw in retail_keywords:
        if kw in lower:
            domain_tags.append("retail")
            break
    for kw in analytics_keywords:
        if kw in lower:
            domain_tags.append("analytics")
            break
    for kw in financial_keywords:
        if kw in lower:
            domain_tags.append("finance")
            break

    return {
        "source": source["name"],
        "source_key": source_key,
        "url": url,
        "domain_tags": list(set(domain_tags + source.get("topics", []))),
        "word_count": len(text.split()),
        "content_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


async def crawl_source(source_key: str, max_pages: int = 10, output_dir: Path = Path("./data")):
    if not HAS_CRAWL4AI:
        print(f"[SKIP] crawl4ai not installed. Run: pip install crawl4ai")
        return []

    source = SOURCES[source_key]
    print(f"\n[CRAWL] {source['name']} — up to {max_pages} pages")

    results = []
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
                    print(f"    [FAIL] {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
            except Exception as e:
                print(f"    [ERROR] {e}")

    return results


async def run_all(source_keys: list[str], max_pages: int, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
        "total_documents": 0,
        "total_words": 0,
    }

    for key in source_keys:
        if key not in SOURCES:
            print(f"[WARN] Unknown source: {key}")
            continue

        results = await crawl_source(key, max_pages=max_pages, output_dir=output_dir)
        word_count = sum(r["metadata"]["word_count"] for r in results)

        manifest["sources"][key] = {
            "name": SOURCES[key]["name"],
            "documents": len(results),
            "words": word_count,
            "ids": [r["id"] for r in results],
        }
        manifest["total_documents"] += len(results)
        manifest["total_words"] += word_count

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n[DONE] {manifest['total_documents']} documents, {manifest['total_words']} words")
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
