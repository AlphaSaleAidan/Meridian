/**
 * Demo copy must not leak between trades.
 *
 * The findings and actions started as one coffee shop's, pushed through a
 * find-and-replace over product names. Anything the table did not list came
 * through verbatim, so an auto detailer opened the portal and read "oat milk
 * consumption jumped 40% — possible over-portioning". A replacement table can
 * never be complete, because the PHRASING is trade-specific too.
 *
 * This walks every trade in the picker and fails on words that belong to
 * somebody else's shop. It is a blunt instrument on purpose: the failure mode
 * is a prospect reading one wrong noun and concluding the product was built
 * for a different business.
 */
import { describe, expect, it } from 'vitest'
import { BUSINESS_TYPES } from '../demo-context'
import { setActiveBusinessTypeForTest } from '../demo-context'
import { generateAnomalies, generateTopActions } from '../agent-data'

/** Words that give a trade away, and the trades allowed to use them. */
const OWNED: { word: RegExp; allowed: string[] }[] = [
  { word: /oat milk|barista|espresso|latte|croissant|pastry/i,
    allowed: ['coffee_shop'] },
  { word: /\bcovers?\b|dining room|kitchen pass|entr[ée]e/i,
    allowed: ['restaurant'] },
  { word: /drive-through|drive-thru/i,
    allowed: ['fast_food', 'coffee_shop'] },
  { word: /ingredient|over-portioning|portion/i,
    allowed: ['restaurant', 'fast_food', 'coffee_shop'] },
  { word: /\bbay\b|\bvehicle\b|windscreen|ceramic coating/i,
    allowed: ['auto_shop', 'detailing', 'mobile_detailing'] },
  { word: /injectable|filler|botox/i, allowed: ['medspa'] },
  { word: /\bchair\b|\bfade\b|pomade/i, allowed: ['barbershop'] },
  { word: /\blash\b|manicure|pedicure|acrylic/i, allowed: ['nails'] },
]

function textOf(trade: string): string {
  setActiveBusinessTypeForTest(trade as any)
  const parts: string[] = []
  for (const a of generateAnomalies()) parts.push(a.title, a.description)
  for (const t of generateTopActions()) {
    parts.push(t.title, t.description, t.expectedImpact)
    parts.push(t.reasoning.observation, t.reasoning.reasoning, t.reasoning.conclusion)
  }
  return parts.join('\n')
}

describe('demo findings belong to the trade showing them', () => {
  for (const bt of BUSINESS_TYPES) {
    it(`${bt.id} borrows nothing from another trade`, () => {
      const text = textOf(bt.id)
      const leaks: string[] = []
      for (const { word, allowed } of OWNED) {
        if (allowed.includes(bt.id)) continue
        const hit = text.match(word)
        if (hit) leaks.push(`"${hit[0]}" belongs to ${allowed.join('/')}`)
      }
      expect(leaks, `${bt.id} is reading another shop's copy`).toEqual([])
    })
  }

  it('names a real product from its own catalogue', () => {
    // The other half of the failure: substituting into a template but with
    // an empty catalogue, which produced "Item E".
    for (const bt of BUSINESS_TYPES) {
      expect(textOf(bt.id), `${bt.id} fell back to placeholder names`)
        .not.toMatch(/\bItem [A-N]\b/)
    }
  })

  it('gives every trade a scale of its own money', () => {
    // An unlisted trade silently scaled to 1 and quoted itself in cafe money.
    const totals = new Map<string, number>()
    for (const bt of BUSINESS_TYPES) {
      setActiveBusinessTypeForTest(bt.id as any)
      totals.set(bt.id, generateTopActions().reduce((s, a) => s + a.impactCents, 0))
    }
    // A med spa and a smoke shop must not quote the same monthly upside.
    expect(totals.get('medspa')).not.toBe(totals.get('smoke_shop'))
    for (const [, v] of totals) expect(v).toBeGreaterThan(0)
  })
})
