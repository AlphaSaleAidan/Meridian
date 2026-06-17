// Regression guard for the Canada insights currency/slop bug: prose dollar
// figures must match the CAD-scaled impact badges, no placeholder/NaN leaks,
// and no coffee-specific template terms surviving into non-coffee verticals.
// Drives every generator under the /canada rate (1.38) for all 5 verticals.
import { describe, it, expect, vi, beforeEach } from 'vitest'

const CAD = 1.38
let BT = 'restaurant'

vi.mock('../demo-context', async (importActual) => {
  const actual = await importActual<typeof import('../demo-context')>()
  return {
    ...actual,
    getActiveBusinessType: () => BT,
    getCurrencyMultiplier: () => CAD,
    isCanadaPath: () => true,
  }
})

import { demoData } from '../demo-data'
import { generateTopActions, generateAgents } from '../agent-data'
import { formatCents } from '../format'

const VERTICALS = ['coffee_shop', 'restaurant', 'fast_food', 'auto_shop', 'smoke_shop']

// Pull "$1,234" / "$1,234.56" / "$184K" tokens out of prose.
function dollarTokens(s: string): string[] {
  return s.match(/\$[\d,]+(?:\.\d+)?[KkMm]?/g) || []
}
function dollarsToNum(tok: string): number {
  let t = tok.replace(/[$,]/g, '')
  let mult = 1
  if (/[Kk]$/.test(t)) { mult = 1000; t = t.slice(0, -1) }
  if (/[Mm]$/.test(t)) { mult = 1_000_000; t = t.slice(0, -1) }
  return parseFloat(t) * mult
}

const SLOP = /\bNaN\b|\$NaN|undefined|null|\[object Object\]|Item [A-N]\b/
// Coffee-specific words that must never survive into a non-coffee vertical —
// they signal an un-substituted template leak (e.g. "Ribeye Steak beans").
const COFFEE_LEAK = /\bbeans\b|\bflavou?rs?\b|\bbarista\b|\blatte\b/i

function scanText(label: string, s: string, findings: string[], coffeeLeak = false) {
  if (SLOP.test(s)) findings.push(`[SLOP] ${label}: matches placeholder/NaN -> ${s.slice(0, 120)}`)
  if (coffeeLeak && COFFEE_LEAK.test(s)) findings.push(`[LEAK] ${label}: coffee-specific term in non-coffee vertical -> ${s.slice(0, 120)}`)
}

describe('Canada insights diagnostic', () => {
  beforeEach(() => { vi.clearAllMocks() })

  for (const v of VERTICALS) {
    it(`vertical=${v}`, () => {
      BT = v
      const findings: string[] = []
      const leak = v !== 'coffee_shop'

      // ---- Insight cards ----
      const { insights } = demoData.insights(100)
      for (const ins of insights) {
        const head = `${ins.type}/${ins.title.slice(0, 40)}`
        scanText(`${head} title`, ins.title, findings, leak)
        scanText(`${head} summary`, ins.summary, findings, leak)

        // Headline $ in title vs impact badge (formatCents(impact_cents))
        const titleToks = dollarTokens(ins.title)
        if (titleToks.length && ins.impact_cents) {
          const headlineNum = dollarsToNum(titleToks[0])
          const badgeNum = dollarsToNum(formatCents(ins.impact_cents))
          const diff = Math.abs(headlineNum - badgeNum)
          if (diff > Math.max(1, badgeNum * 0.02)) {
            findings.push(`[MISMATCH] ${head}: title says ${titleToks[0]} but badge=${formatCents(ins.impact_cents)}`)
          }
        }

        // details.*_cents sanity: number, finite, non-negative
        const walk = (o: any, path = 'details') => {
          if (o == null) return
          if (typeof o === 'object') for (const k of Object.keys(o)) walk(o[k], `${path}.${k}`)
          if (/_cents$/.test(path) && (typeof o !== 'number' || !Number.isFinite(o) || o < 0))
            findings.push(`[BADCENTS] ${head}: ${path}=${o}`)
        }
        walk((ins as any).details)
      }

      // money_left component-sum check
      const ml = insights.find(i => i.type === 'money_left')
      if (ml) {
        const toks = dollarTokens(ml.summary).map(dollarsToNum)
        const headline = dollarsToNum(dollarTokens(ml.title)[0] || '$0')
        // components are the lines after the headline; check the 5 bullets sum near headline
        const comps = toks.filter(n => n < headline) // crude: bullet values are < total
        const sum = comps.slice(0, 5).reduce((a, b) => a + b, 0)
        if (headline && Math.abs(sum - headline) > headline * 0.05)
          findings.push(`[SUM] money_left: components≈${sum} vs headline ${headline}`)
      }

      // ---- Top actions ----
      for (const a of generateTopActions()) {
        const head = `action#${a.rank}/${a.title.slice(0, 36)}`
        scanText(`${head} title`, a.title, findings, leak)
        scanText(`${head} desc`, a.description, findings, leak)
        scanText(`${head} impact`, a.expectedImpact, findings, leak)
        const impToks = dollarTokens(a.expectedImpact)
        if (impToks.length && a.impactCents) {
          const textNum = dollarsToNum(impToks[0])
          const badgeNum = dollarsToNum(formatCents(a.impactCents))
          if (Math.abs(textNum - badgeNum) > Math.max(1, badgeNum * 0.02))
            findings.push(`[MISMATCH] ${head}: text ${impToks[0]} vs badge ${formatCents(a.impactCents)}`)
        }
      }

      // ---- Agents latest findings (slop only) ----
      for (const ag of generateAgents()) scanText(`agent ${ag.name}`, ag.latestFinding, findings, leak)

      if (findings.length) {
        console.log(`\n===== ${v}: ${findings.length} findings =====`)
        for (const f of findings) console.log(f)
      }
      expect(findings, `\n${findings.join('\n')}`).toEqual([])
    })
  }
})
