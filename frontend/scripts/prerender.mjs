#!/usr/bin/env node
// Post-build prerender for the Meridian SPA.
// Loads each public route in headless Chrome, lets React + react-helmet-async render
// the real per-page <title>/<meta>/content, and writes that HTML back into dist/<route>/
// index.html. nginx then serves unique, crawlable HTML per URL instead of one blank shell.
//
// Usage:
//   node scripts/prerender.mjs                 # prerender every route in the sitemap
//   node scripts/prerender.mjs --limit=8       # first N routes (verification)
//   node scripts/prerender.mjs --only=/guides  # only routes starting with a prefix
//   PRERENDER_BASE=http://127.0.0.1:4188 node scripts/prerender.mjs

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { chromium } from "playwright";

const HERE = dirname(fileURLToPath(import.meta.url));
const DIST = join(HERE, "..", "dist");
const BASE = process.env.PRERENDER_BASE || "http://127.0.0.1:4188";

const args = process.argv.slice(2);
const limit = Number((args.find((a) => a.startsWith("--limit=")) || "").split("=")[1]) || Infinity;
const only = (args.find((a) => a.startsWith("--only=")) || "").split("=")[1] || "";

async function routesFromSitemap() {
  const xml = await readFile(join(DIST, "sitemap.xml"), "utf8");
  const locs = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
  return locs
    .map((u) => new URL(u).pathname)
    // skip auth/app/private surfaces — only public marketing/SEO routes
    .filter((p) => !/^\/(app|admin|customer|us\/portal|canada\/portal|c\/|onboard)/.test(p))
    .filter((p) => p.startsWith(only || "/"));
}

function outPath(route) {
  if (route === "/") return join(DIST, "index.html");
  return join(DIST, route.replace(/^\//, "").replace(/\/$/, ""), "index.html");
}

async function main() {
  let routes = await routesFromSitemap();
  if (Number.isFinite(limit)) routes = routes.slice(0, limit);
  console.log(`[prerender] ${routes.length} routes via ${BASE}`);

  const browser = await chromium.launch();
  const page = await browser.newPage();
  let ok = 0, fail = 0;

  for (const route of routes) {
    try {
      await page.goto(BASE + route, { waitUntil: "networkidle", timeout: 30000 });
      // Wait until react-helmet has set a real title (or root has content).
      await page.waitForFunction(
        () => document.title && document.querySelector("#root")?.children.length > 0,
        { timeout: 15000 },
      ).catch(() => {});
      await page.waitForTimeout(400);

      const html = await page.content();
      const title = await page.title();
      const file = outPath(route);
      await mkdir(dirname(file), { recursive: true });
      await writeFile(file, html, "utf8");
      ok++;
      console.log(`  ✓ ${route}  —  "${title.slice(0, 60)}"`);
    } catch (e) {
      fail++;
      console.error(`  ✗ ${route}  —  ${e.message}`);
    }
  }

  await browser.close();
  console.log(`[prerender] done: ${ok} ok, ${fail} failed`);
  if (fail > ok) process.exitCode = 1;
}

main().catch((e) => { console.error(e); process.exit(1); });
