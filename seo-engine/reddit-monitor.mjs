#!/usr/bin/env node
// Meridian — Reddit brand-mention MONITOR (read-only).
//
// What it does: searches relevant subreddits for mentions of Meridian / POS-analytics
// terms and alerts you so a REAL human (you, disclosed as the founder) can reply.
//
// What it deliberately does NOT do: post, comment, upvote, or create accounts. Automated
// promotional posting/replying is astroturfing under Reddit's content policy and gets the
// domain site-banned. This tool only listens.
//
// Usage:
//   node reddit-monitor.mjs --dry-run   # print new mentions, don't send/persist
//   node reddit-monitor.mjs             # alert via configured transport, persist seen-state

import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { deliver, configuredTransports } from './lib/transports.mjs'

const HERE = dirname(fileURLToPath(import.meta.url))
const SEEN_PATH = join(HERE, '.reddit-seen.json')
const DRY = process.argv.slice(2).includes('--dry-run')

// Tune these to where your buyers actually hang out.
const SUBREDDITS = [
  'smallbusiness', 'CanadaSmallBusiness', 'restaurateur', 'Entrepreneur',
  'Restaurant_Managers', 'cafe', 'POS',
]
// Queries are matched against title+selftext. Keep them specific to cut noise.
const QUERIES = [
  'meridian intelligence', 'meridian.tips', 'pos analytics', 'restaurant analytics software',
  'pos data analytics canada',
]

async function loadSeen() {
  try { return new Set(JSON.parse(await readFile(SEEN_PATH, 'utf8'))) } catch { return new Set() }
}
async function saveSeen(set) {
  await writeFile(SEEN_PATH, JSON.stringify([...set].slice(-2000)), 'utf8')
}

async function searchSub(sub, query) {
  const url = `https://www.reddit.com/r/${sub}/search.json?q=${encodeURIComponent(query)}` +
    `&restrict_sr=1&sort=new&limit=15&t=week`
  try {
    const res = await fetch(url, { headers: { 'User-Agent': 'meridian-mention-monitor/1.0 (read-only)' } })
    if (!res.ok) return []
    const data = await res.json()
    return (data?.data?.children || []).map(c => c.data)
  } catch { return [] }
}

function relevant(post, query) {
  const hay = `${post.title || ''} ${post.selftext || ''}`.toLowerCase()
  return hay.includes(query.toLowerCase())
}

async function main() {
  const seen = await loadSeen()
  const fresh = []

  for (const sub of SUBREDDITS) {
    for (const q of QUERIES) {
      const posts = await searchSub(sub, q)
      for (const p of posts) {
        if (!p?.id || seen.has(p.id)) continue
        if (!relevant(p, q)) continue
        seen.add(p.id)
        fresh.push({
          sub, q,
          title: p.title,
          url: `https://www.reddit.com${p.permalink}`,
          author: p.author,
          score: p.num_comments,
        })
      }
      await new Promise(r => setTimeout(r, 600)) // be polite to Reddit
    }
  }

  if (!fresh.length) {
    console.log('No new mentions.')
    if (!DRY) await saveSeen(seen)
    return
  }

  const L = ['*Meridian — new Reddit mentions* 👀', '_Reply as yourself, disclosed as the founder. Do not astroturf._', '']
  for (const m of fresh.slice(0, 15)) {
    L.push(`• r/${m.sub} — "${m.title}"`)
    L.push(`  ${m.url}  (${m.score} comments)`)
  }
  const text = L.join('\n')

  if (DRY || configuredTransports().length === 0) {
    console.log('— DRY RUN —\n')
    console.log(text)
    return
  }

  const { sent, errors } = await deliver({ subject: 'Meridian — new Reddit mentions', text }, process.env)
  await saveSeen(seen)
  console.log(`Alerted via: ${sent.join(', ') || 'none'}`)
  if (errors.length) { console.error('Errors:', errors.join(' | ')); process.exitCode = 1 }
}

main().catch(e => { console.error(e); process.exit(1) })
