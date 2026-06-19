#!/usr/bin/env node
// Meridian SEO — daily report.
// Compiles: content shipped/queued, live SEO page count, backlog status, and
// (optionally) Google Search Console metrics, then delivers via Telegram/email.
//
// Usage:
//   node daily-report.mjs            # send to configured transports, else dry-run
//   node daily-report.mjs --dry-run  # always just print, never send
//
// Env (all optional — system degrades gracefully):
//   TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
//   RESEND_API_KEY, REPORT_EMAIL_TO, REPORT_EMAIL_FROM
//   GSC_ACCESS_TOKEN, GSC_SITE_URL   (optional Search Console — see fetchGsc)

import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { deliver, configuredTransports } from './lib/transports.mjs'
import { getGscAccessToken } from './lib/gsc-auth.mjs'
import { buildHtml } from './lib/report-html.mjs'

const HERE = dirname(fileURLToPath(import.meta.url))
const FRONTEND = join(HERE, '..', 'frontend')

const args = process.argv.slice(2)
const DRY = args.includes('--dry-run')

// Date is passed in or stamped at call time by the scheduler. Scripts here avoid
// hardcoding "today" assumptions beyond a single new Date() at entry.
const now = new Date()
const todayISO = now.toISOString().slice(0, 10)

async function readJson(path, fallback) {
  try { return JSON.parse(await readFile(path, 'utf8')) } catch { return fallback }
}

// Count live, indexable SEO pages from the production sitemap.
async function countLivePages() {
  try {
    const xml = await readFile(join(FRONTEND, 'public', 'sitemap.xml'), 'utf8')
    const total = (xml.match(/<loc>/g) || []).length
    const guides = (xml.match(/\/guides\//g) || []).length
    return { total, guides }
  } catch { return { total: 0, guides: 0 } }
}

// Optional Google Search Console fetch. Auth via service account (GSC_SA_KEY_FILE) or a
// bearer token (GSC_ACCESS_TOKEN), plus the verified property (GSC_SITE_URL). Returns null
// if not configured so the report still works on day one without GSC wired up.
async function fetchGsc() {
  const site = process.env.GSC_SITE_URL
  if (!site) return null
  let token
  try {
    token = await getGscAccessToken(process.env, Math.floor(now.getTime() / 1000))
  } catch (e) {
    return { error: e.message }
  }
  if (!token) return null
  const end = todayISO
  const start = new Date(now.getTime() - 28 * 864e5).toISOString().slice(0, 10)
  try {
    const res = await fetch(
      `https://searchconsole.googleapis.com/webmasters/v3/sites/${encodeURIComponent(site)}/searchAnalytics/query`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ startDate: start, endDate: end, dimensions: ['query'], rowLimit: 10 }),
      },
    )
    if (!res.ok) return { error: `GSC ${res.status}` }
    const data = await res.json()
    const rows = data.rows || []
    const totals = rows.reduce(
      (a, r) => ({ clicks: a.clicks + (r.clicks || 0), impressions: a.impressions + (r.impressions || 0) }),
      { clicks: 0, impressions: 0 },
    )
    return {
      window: `${start} → ${end}`,
      clicks: totals.clicks,
      impressions: totals.impressions,
      topQueries: rows.slice(0, 5).map(r => ({
        q: r.keys?.[0], clicks: r.clicks, impressions: r.impressions, pos: r.position?.toFixed(1),
      })),
    }
  } catch (e) {
    return { error: e.message }
  }
}

// Derive the shared model that both the text and HTML renderers consume.
function computeModel({ queue, topics, pages, gsc }) {
  const items = queue.items || []
  const ts = topics.topics || []
  const queued = ts.filter(t => t.status === 'queued')
  return {
    todayISO,
    pages,
    gsc,
    shippedToday: items.filter(i => i.publishedAt === todayISO),
    draftedToday: items.filter(i => i.draftedAt === todayISO),
    awaitingReview: items.filter(i => i.status === 'drafted'),
    publishedCount: items.filter(i => i.status === 'published').length,
    queuedCount: queued.length,
    nextUp: queued.slice().sort((a, b) => (a.priority || 9) - (b.priority || 9)).slice(0, 3),
  }
}

function buildText(m) {
  const { pages, gsc, shippedToday, draftedToday, awaitingReview, nextUp } = m
  const queued = { length: m.queuedCount }

  const L = []
  L.push(`*Meridian SEO — Daily Report*`)
  L.push(`_${todayISO}_`)
  L.push('')
  L.push(`📄 *Live SEO pages:* ${pages.total} (${pages.guides} guides)`)
  L.push(`✍️ *Drafted today:* ${draftedToday.length}`)
  L.push(`🚀 *Published today:* ${shippedToday.length}`)
  L.push(`🕓 *Awaiting your review:* ${awaitingReview.length}`)
  L.push(`📚 *Backlog remaining:* ${queued.length} topics`)
  L.push('')

  if (draftedToday.length) {
    L.push(`*New drafts today*`)
    for (const i of draftedToday) L.push(`• ${i.title} — \`${i.status}\``)
    L.push('')
  }
  if (awaitingReview.length) {
    L.push(`*Awaiting approval (not yet live)*`)
    for (const i of awaitingReview.slice(0, 8)) L.push(`• ${i.title}`)
    L.push('')
  }
  if (nextUp.length) {
    L.push(`*Scheduled next*`)
    for (const t of nextUp) L.push(`• ${t.title}`)
    L.push('')
  }

  if (gsc && !gsc.error) {
    L.push(`*Search Console (${gsc.window})*`)
    L.push(`👁 ${gsc.impressions} impressions · 🖱 ${gsc.clicks} clicks`)
    if (gsc.topQueries?.length) {
      L.push(`Top queries:`)
      for (const q of gsc.topQueries) L.push(`• ${q.q} — pos ${q.pos}, ${q.clicks} clk`)
    }
    L.push('')
  } else if (gsc?.error) {
    L.push(`_Search Console: ${gsc.error}_`)
    L.push('')
  } else {
    L.push(`_Search Console not wired yet (add GSC_SA_KEY_FILE + GSC_SITE_URL)._`)
    L.push('')
  }

  L.push(`Review/approve drafts on branch \`feat/canada-compliance-seo\`.`)
  return L.join('\n')
}

async function main() {
  const [queue, topics, pages, gsc] = await Promise.all([
    readJson(join(HERE, 'content-queue.json'), { items: [] }),
    readJson(join(HERE, 'topics.json'), { topics: [] }),
    countLivePages(),
    fetchGsc(),
  ])

  const model = computeModel({ queue, topics, pages, gsc })
  const text = buildText(model)
  const html = buildHtml(model)
  const subject = `Meridian SEO — ${todayISO}`

  // --write-html dumps the HTML to a file for local visual inspection.
  const htmlOut = args.find(a => a.startsWith('--write-html='))
  if (htmlOut) {
    const { writeFile } = await import('node:fs/promises')
    await writeFile(htmlOut.split('=')[1], html, 'utf8')
    console.log(`HTML written to ${htmlOut.split('=')[1]}`)
  }

  if (DRY || configuredTransports().length === 0) {
    console.log('— DRY RUN (no transport configured or --dry-run) —\n')
    console.log(text)
    if (!DRY) console.log('\n[hint] configure TELEGRAM_* or RESEND_* env vars to deliver this.')
    return
  }

  const { sent, errors } = await deliver({ subject, text, html }, process.env)
  console.log(`Delivered via: ${sent.join(', ') || 'none'}`)
  if (errors.length) { console.error('Errors:', errors.join(' | ')); process.exitCode = 1 }
}

main().catch(e => { console.error(e); process.exit(1) })
