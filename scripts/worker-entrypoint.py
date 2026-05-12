#!/usr/bin/env python3
"""Railway Worker — runs all 3 autonomous daemons in one process."""
import asyncio
import signal
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ai.swarm_trainer import get_swarm_trainer


async def run_scraper():
    """Business knowledge scraper — 6h cycles."""
    # Import inline to avoid top-level crawl4ai issues
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "scraper"))
    try:
        from scraper_daemon import main as scraper_main
        await scraper_main()
    except ImportError:
        # Fallback: run the script directly
        from scripts.scraper_daemon_loop import scrape_loop
        await scrape_loop()


async def run_swarm_trainer():
    """Swarm trainer — 5min cycles."""
    trainer = get_swarm_trainer()
    print("[Worker] SwarmTrainer starting (300s interval)")
    await trainer.start_autonomous(interval_seconds=300)


async def run_evolver():
    """Evolver — 4h cycles via subprocess."""
    evolver_dir = os.path.join(os.path.dirname(__file__), "..", "services", "evolver")
    while True:
        try:
            print(f"[Worker] Evolver cycle starting")
            proc = await asyncio.create_subprocess_exec(
                "node", "index.js", "--review",
                cwd=evolver_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=1800)
            if stdout:
                for line in stdout.decode().strip().split("\n")[-5:]:
                    print(f"[Evolver] {line}")
            print(f"[Worker] Evolver cycle complete (exit={proc.returncode})")
        except asyncio.TimeoutError:
            print("[Worker] Evolver timed out (30min), killing")
            proc.kill()
        except Exception as e:
            print(f"[Worker] Evolver error: {e}")

        await asyncio.sleep(14400)  # 4 hours


async def main():
    print("=" * 50)
    print("  MERIDIAN AUTONOMOUS WORKER")
    print("  SwarmTrainer (5min) + Scraper (6h) + Evolver (4h)")
    print("=" * 50)

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: sys.exit(0))

    await asyncio.gather(
        run_swarm_trainer(),
        run_scraper_loop(),
        run_evolver(),
    )


async def run_scraper_loop():
    """Inline scraper loop — no import dependency issues."""
    import json
    import time
    import hashlib
    from datetime import datetime, timezone
    from pathlib import Path

    SCRAPE_INTERVAL = 6 * 3600
    OUTPUT_DIR = Path(__file__).parent.parent / "data" / "scraped"
    MANIFEST = OUTPUT_DIR / "manifest.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
    except ImportError:
        print("[Scraper] crawl4ai not available — scraper disabled")
        while True:
            await asyncio.sleep(3600)
        return

    SOURCES = {
        "mckinsey": ("https://www.mckinsey.com", ["/industries/retail/our-insights", "/industries/consumer-packaged-goods/our-insights"]),
        "hbr": ("https://hbr.org", ["/topic/subject/analytics-and-data-science", "/topic/subject/customer-experience"]),
        "deloitte": ("https://www2.deloitte.com", ["/us/en/insights/industry/retail-distribution.html"]),
        "mit_sloan": ("https://sloanreview.mit.edu", ["/topic/data-and-analytics"]),
        "nrf": ("https://nrf.com", ["/blog"]),
        "restaurant_biz": ("https://www.restaurantbusinessonline.com", ["/technology"]),
    }

    def load_manifest():
        if MANIFEST.exists():
            return json.loads(MANIFEST.read_text())
        return {"scraped_urls": [], "total_articles": 0, "last_cycle": None}

    while True:
        manifest = load_manifest()
        total_new = 0
        start = time.monotonic()

        try:
            browser_config = BrowserConfig(headless=True)
            async with AsyncWebCrawler(config=browser_config) as crawler:
                for key, (base_url, paths) in SOURCES.items():
                    for path in paths:
                        url = base_url + path
                        if url in manifest["scraped_urls"]:
                            continue
                        try:
                            config = CrawlerRunConfig(word_count_threshold=100, exclude_external_links=True)
                            result = await crawler.arun(url=url, config=config)
                            if result.success and result.markdown and len(result.markdown) > 200:
                                url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
                                article = {
                                    "source_key": key, "url": url,
                                    "title": (result.metadata or {}).get("title", ""),
                                    "content": result.markdown[:50000],
                                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                                }
                                (OUTPUT_DIR / f"{key}_{url_hash}.json").write_text(json.dumps(article, indent=2))
                                manifest["scraped_urls"].append(url)
                                manifest["total_articles"] += 1
                                total_new += 1
                                print(f"  [Scraper] {key}: {article['title'][:80]}")
                        except Exception as e:
                            print(f"  [Scraper] {key} error: {e}")
                        await asyncio.sleep(5)
        except Exception as e:
            print(f"[Scraper] Cycle error: {e}")

        manifest["last_cycle"] = datetime.now(timezone.utc).isoformat()
        MANIFEST.write_text(json.dumps(manifest, indent=2))
        elapsed = time.monotonic() - start
        print(f"[Scraper] Cycle done: {total_new} new, {manifest['total_articles']} total ({elapsed:.0f}s)")
        await asyncio.sleep(SCRAPE_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
