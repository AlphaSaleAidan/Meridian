#!/usr/bin/env python3
"""Business Knowledge Scraper Daemon — continuously scrapes business intelligence sources.

Cycles through all sources every 6 hours, scraping new articles.
Stores results in data/scraped/ as JSON.
"""
import asyncio
import json
import sys
import os
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "scraper"))

SCRAPE_INTERVAL = 3 * 3600  # 3 hours between full cycles
MAX_PAGES_PER_SOURCE = 8
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "scraped"
MANIFEST = OUTPUT_DIR / "manifest.json"

try:
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
    HAS_CRAWL4AI = True
except ImportError:
    HAS_CRAWL4AI = False

from sources import SOURCES


def load_manifest() -> dict:
    default = {"scraped_urls": [], "total_articles": 0, "last_cycle": None}
    if MANIFEST.exists():
        data = json.loads(MANIFEST.read_text())
        if "scraped_urls" not in data:
            data["scraped_urls"] = []
        if "total_articles" not in data:
            data["total_articles"] = data.get("total_documents", 0)
        return data
    return default


def save_manifest(manifest: dict):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2))


async def scrape_source(crawler, source_key: str, source: dict, manifest: dict) -> int:
    new_articles = 0
    paths = source.get("start_paths") or source.get("paths", [])
    for path in paths[:MAX_PAGES_PER_SOURCE]:
        url = source["base_url"] + path
        if url in manifest["scraped_urls"]:
            continue
        try:
            config = CrawlerRunConfig(
                word_count_threshold=100,
                exclude_external_links=True,
            )
            result = await crawler.arun(url=url, config=config)
            if result.success and result.markdown and len(result.markdown) > 200:
                import hashlib
                url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
                filename = f"{source_key}_{url_hash}.json"
                article = {
                    "source": source["name"],
                    "source_key": source_key,
                    "url": url,
                    "title": result.metadata.get("title", "") if result.metadata else "",
                    "content": result.markdown[:50000],
                    "word_count": len(result.markdown.split()),
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }
                (OUTPUT_DIR / filename).write_text(json.dumps(article, indent=2))
                manifest["scraped_urls"].append(url)
                manifest["total_articles"] += 1
                new_articles += 1
                print(f"  [{source_key}] Scraped: {result.metadata.get('title', url)[:80]}")
            else:
                print(f"  [{source_key}] Skip (no content): {url}")
        except Exception as e:
            print(f"  [{source_key}] Error on {url}: {e}")
        await asyncio.sleep(5)
    return new_articles


async def run_cycle():
    if not HAS_CRAWL4AI:
        print("[Scraper] crawl4ai not installed — skipping cycle")
        return 0

    manifest = load_manifest()
    total_new = 0

    browser_config = BrowserConfig(headless=True)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for key, source in SOURCES.items():
            print(f"[Scraper] Crawling {source['name']}...")
            new = await scrape_source(crawler, key, source, manifest)
            total_new += new

    manifest["last_cycle"] = datetime.now(timezone.utc).isoformat()
    save_manifest(manifest)
    return total_new


async def main():
    print(f"[Scraper] Starting autonomous scraping daemon ({SCRAPE_INTERVAL}s interval)")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            start = time.monotonic()
            new = await run_cycle()
            elapsed = time.monotonic() - start
            manifest = load_manifest()
            print(f"[Scraper] Cycle complete: {new} new articles, "
                  f"{manifest['total_articles']} total, {elapsed:.0f}s elapsed")
        except Exception as e:
            print(f"[Scraper] Cycle error: {e}")

        print(f"[Scraper] Next cycle in {SCRAPE_INTERVAL // 3600}h")
        await asyncio.sleep(SCRAPE_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Scraper] Stopped")
