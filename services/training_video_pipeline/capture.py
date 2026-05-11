"""
Capture screenshots of the Meridian demo dashboard for training videos.

Navigates the live demo at the Vercel deployment and saves 1920x1080
screenshots of every key page. These are used by the video pipeline
as "screen recording" frames that get Ken Burns animation.

Usage:
  python capture.py                    # Capture all screens
  python capture.py --page overview    # Capture one page
  python capture.py --list             # List available pages
"""

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger("meridian.capture")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DEMO_BASE = "https://meridian-dun-nu.vercel.app/demo"
SCREENS_DIR = Path(__file__).parent / "assets" / "screens"

PAGES = {
    "overview":       {"path": "",              "wait": 3, "desc": "Main dashboard overview"},
    "revenue":        {"path": "/revenue",      "wait": 3, "desc": "Revenue analytics"},
    "products":       {"path": "/products",     "wait": 3, "desc": "Product performance"},
    "inventory":      {"path": "/inventory",    "wait": 3, "desc": "Inventory intelligence"},
    "insights":       {"path": "/insights",     "wait": 3, "desc": "AI insights feed"},
    "forecasts":      {"path": "/forecasts",    "wait": 3, "desc": "Revenue forecasting"},
    "agents":         {"path": "/agents",       "wait": 3, "desc": "AI agent dashboard"},
    "actions":        {"path": "/actions",       "wait": 3, "desc": "Recommended actions"},
    "customers":      {"path": "/customers",    "wait": 3, "desc": "Customer analytics"},
    "staff":          {"path": "/staff",        "wait": 3, "desc": "Staff performance"},
    "peak-hours":     {"path": "/peak-hours",   "wait": 3, "desc": "Peak hour optimizer"},
    "margins":        {"path": "/margins",      "wait": 3, "desc": "Margin analysis"},
    "menu-matrix":    {"path": "/menu-matrix",  "wait": 3, "desc": "Menu engineering matrix"},
    "anomalies":      {"path": "/anomalies",    "wait": 3, "desc": "Anomaly detection"},
    "notifications":  {"path": "/notifications","wait": 2, "desc": "Notification center"},
    "settings":       {"path": "/settings",     "wait": 2, "desc": "Settings page"},
    "phone-orders":   {"path": "/phone-orders", "wait": 3, "desc": "Phone order agent"},
}

# Which screenshots map to which training modules
MODULE_SCREENS = {
    "module_1": ["overview", "insights", "revenue", "agents", "settings"],
    "module_2": ["overview", "revenue", "insights", "products", "customers"],
    "module_3": ["overview", "revenue", "products", "peak-hours", "agents", "insights", "forecasts", "customers"],
    "module_4": ["overview", "revenue", "products", "margins", "menu-matrix", "peak-hours", "customers", "inventory"],
    "module_5": ["overview", "revenue", "customers", "insights", "agents"],
    "module_6": ["settings", "overview", "insights"],
    "module_7": ["overview", "peak-hours", "customers", "anomalies"],
    "module_8": ["overview", "revenue", "settings"],
    "module_9": ["settings", "overview", "insights"],
}


async def capture_all(pages_to_capture: list[str] | None = None):
    from playwright.async_api import async_playwright

    SCREENS_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )
        page = await context.new_page()

        targets = pages_to_capture or list(PAGES.keys())

        # First load: dismiss the business type selector by clicking Restaurant
        logger.info("Loading demo and selecting Restaurant business type...")
        await page.goto(DEMO_BASE, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        try:
            restaurant_btn = page.locator("text=Restaurant").first
            if await restaurant_btn.is_visible(timeout=3000):
                await restaurant_btn.click()
                await page.wait_for_timeout(1000)
                # Click "View My Demo" if it appears
                view_btn = page.locator("text=View My Demo").first
                if await view_btn.is_visible(timeout=2000):
                    await view_btn.click()
                    await page.wait_for_timeout(2000)
            logger.info("Business type selected — modal dismissed")
        except Exception:
            logger.info("No business type modal found — continuing")

        for name in targets:
            info = PAGES.get(name)
            if not info:
                logger.warning("Unknown page: %s", name)
                continue

            url = f"{DEMO_BASE}{info['path']}"
            out_path = SCREENS_DIR / f"{name}.png"

            logger.info("Capturing: %s → %s", name, info["desc"])
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(info["wait"] * 1000)

                # Dismiss business type modal if it reappears on new page
                try:
                    modal = page.locator("text=What type of business are you?")
                    if await modal.is_visible(timeout=500):
                        restaurant = page.locator("text=Restaurant").first
                        await restaurant.click()
                        await page.wait_for_timeout(500)
                        view_btn = page.locator("text=View My Demo").first
                        if await view_btn.is_visible(timeout=1000):
                            await view_btn.click()
                            await page.wait_for_timeout(2000)
                except Exception:
                    pass

                await page.screenshot(path=str(out_path), full_page=False)
                logger.info("  Saved: %s (%s)", out_path.name, _file_size(out_path))
            except Exception as e:
                logger.warning("  Failed: %s — %s", name, e)

        await browser.close()

    logger.info("Done. %d screenshots in %s", len(targets), SCREENS_DIR)


def _file_size(path: Path) -> str:
    size = path.stat().st_size
    if size > 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} MB"
    return f"{size / 1024:.0f} KB"


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Capture Meridian demo screenshots")
    parser.add_argument("--page", help="Capture a specific page")
    parser.add_argument("--list", action="store_true", help="List available pages")
    args = parser.parse_args()

    if args.list:
        for name, info in PAGES.items():
            print(f"  {name:20s} — {info['desc']}")
        return

    pages = [args.page] if args.page else None
    await capture_all(pages)


if __name__ == "__main__":
    asyncio.run(main())
