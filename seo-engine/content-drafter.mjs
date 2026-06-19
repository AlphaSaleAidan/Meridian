#!/usr/bin/env node
// Meridian SEO — autonomous content drafter (cron-driven).
//
// Picks the highest-priority queued topic, asks an LLM to draft it as a GuideData object,
// validates the JSON, and writes it to seo-engine/drafts/<slug>.json. It then marks the
// topic 'drafted' and records it in content-queue.json so the daily report surfaces it.
//
// It NEVER edits the live source (seo-guides.ts) and NEVER publishes. A human reviews the
// draft and promotes it into the site. Inert (exit 0) until an LLM endpoint is configured.
//
// Uses an OpenAI-compatible chat API (works with the local LiteLLM/Kimi gateway or any
// provider). Config via env:
//   SEO_LLM_BASE_URL   e.g. http://127.0.0.1:4000/v1   (OpenAI-compatible)
//   SEO_LLM_KEY        api key / gateway key
//   SEO_LLM_MODEL      e.g. claude-sonnet-4-6 / kimi-k2.6 / gpt-4o

import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
const DRAFTS = join(HERE, 'drafts')
const now = new Date()
const todayISO = now.toISOString().slice(0, 10)

const REQUIRED = [
  'slug', 'seoTitle', 'description', 'datePublished', 'heroTitle', 'heroAccent',
  'heroDescription', 'sections', 'faqs', 'relatedLinks', 'ctaHeadline', 'ctaDescription',
]

async function readJson(p, fb) { try { return JSON.parse(await readFile(p, 'utf8')) } catch { return fb } }

function buildPrompt(topic) {
  return `You are writing an SEO guide for Meridian Intelligence, an AI-powered POS analytics
platform. Meridian was one of the EARLIEST POS-analytics platforms to build a dedicated Canadian
product, compliance-first: designed around PIPEDA, built to support Quebec Law 25, with Canadian
data residency, CAD pricing, and support for Canadian POS systems (Moneris, Alice POS).

Write a guide on: "${topic.title}"
Target reader intent: ${topic.intent}

STRICT RULES — these are non-negotiable:
- Every factual claim must be TRUE and defensible. NEVER invent metrics, valuations, customer
  counts, earnings, or fake testimonials.
- Frame compliance carefully: "designed around" / "built to support" / "aligned with" — NEVER
  "certified" or "guarantees compliance". Compliance is a shared responsibility.
- Where the guide gives legal/compliance info, include a brief "general information, not legal
  advice" note in a tip field.
- Confident, helpful, plain-English tone. No hype, no filler.

Return ONLY a single JSON object (no markdown fences, no prose) matching this exact shape:
{
  "slug": "kebab-case-url-slug",
  "seoTitle": "... | Meridian",
  "description": "150-160 char meta description",
  "datePublished": "${todayISO}",
  "heroTitle": "short", "heroAccent": "short continuation",
  "heroDescription": "1-2 sentence hook",
  "sections": [ { "title": "...", "paragraphs": ["...","..."], "tip": "optional", "stat": {"value":"...","label":"..."} } ],
  "faqs": [ { "q": "...", "a": "..." } ],
  "relatedLinks": [ { "to": "/guides/...", "label": "..." } ],
  "ctaHeadline": "...", "ctaDescription": "..."
}
Provide 5-6 sections and 5 FAQs. Use slug "${topic.id ? topic.id : ''}" only as a hint; pick a clean descriptive slug.`
}

async function callLlm(prompt, env) {
  const base = env.SEO_LLM_BASE_URL, key = env.SEO_LLM_KEY, model = env.SEO_LLM_MODEL
  const res = await fetch(`${base.replace(/\/$/, '')}/chat/completions`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      temperature: 0.4,
      messages: [
        { role: 'system', content: 'You output only valid JSON. No markdown, no commentary.' },
        { role: 'user', content: prompt },
      ],
    }),
  })
  if (!res.ok) throw new Error(`LLM ${res.status}: ${await res.text().catch(() => '')}`)
  const data = await res.json()
  let txt = data?.choices?.[0]?.message?.content || ''
  txt = txt.trim().replace(/^```(?:json)?/i, '').replace(/```$/, '').trim()
  return JSON.parse(txt)
}

function validate(guide) {
  const missing = REQUIRED.filter(k => guide[k] == null)
  if (missing.length) throw new Error(`draft missing fields: ${missing.join(', ')}`)
  if (!Array.isArray(guide.sections) || guide.sections.length < 3) throw new Error('too few sections')
  if (!Array.isArray(guide.faqs) || guide.faqs.length < 3) throw new Error('too few faqs')
  if (!/^[a-z0-9-]+$/.test(guide.slug)) throw new Error(`bad slug: ${guide.slug}`)
}

async function main() {
  const env = process.env
  if (!env.SEO_LLM_BASE_URL || !env.SEO_LLM_KEY || !env.SEO_LLM_MODEL) {
    console.log('[drafter] LLM not configured (SEO_LLM_BASE_URL/KEY/MODEL) — skipping. exit 0')
    return
  }

  const topicsPath = join(HERE, 'topics.json')
  const queuePath = join(HERE, 'content-queue.json')
  const topics = await readJson(topicsPath, { topics: [] })
  const queue = await readJson(queuePath, { items: [] })

  const queued = (topics.topics || []).filter(t => t.status === 'queued')
    .sort((a, b) => (a.priority || 9) - (b.priority || 9))
  if (!queued.length) { console.log('[drafter] backlog empty — nothing to draft.'); return }

  const topic = queued[0]
  console.log(`[drafter] drafting: ${topic.title}`)

  let guide
  try {
    guide = await callLlm(buildPrompt(topic), env)
    validate(guide)
  } catch (e) {
    console.error(`[drafter] FAILED for "${topic.title}": ${e.message}`)
    process.exitCode = 1
    return
  }

  await mkdir(DRAFTS, { recursive: true })
  await writeFile(join(DRAFTS, `${guide.slug}.json`), JSON.stringify(guide, null, 2), 'utf8')

  topic.status = 'drafted'
  topic.draftedSlug = guide.slug
  await writeFile(topicsPath, JSON.stringify(topics, null, 2), 'utf8')

  queue.items = queue.items || []
  if (!queue.items.find(i => i.slug === guide.slug)) {
    queue.items.push({
      slug: guide.slug, title: guide.seoTitle.replace(/ \| Meridian$/, ''),
      type: topic.type || 'guide', status: 'drafted', draftedAt: todayISO,
      publishedAt: null, url: `https://meridian.tips/guides/${guide.slug}`,
      source: 'autonomous-drafter',
    })
    await writeFile(queuePath, JSON.stringify(queue, null, 2), 'utf8')
  }

  console.log(`[drafter] ✓ draft written: seo-engine/drafts/${guide.slug}.json (awaiting human review)`)
}

main().catch(e => { console.error(e); process.exit(1) })
