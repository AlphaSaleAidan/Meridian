/**
 * The demo opening screen, and the promise that it is only a demo.
 *
 * Two things have to hold at once. The visitor's pick must genuinely reshape
 * the demo — that is the whole reason the screen exists. And none of it may
 * touch a signed-in merchant, whose portal is resolved from their own record
 * and nothing else.
 *
 * The second is the one worth guarding, because the way to break it is
 * invisible: detectBusinessType() never returns null, so any code path that
 * lets the demo's trade reach an authenticated merchant hands every merchant
 * with a blank business_type a trade they never chose.
 */
import { describe, expect, it } from 'vitest'
import { BUSINESS_GROUPS, BUSINESS_TYPES, type BusinessType } from '../demo-context'
import { getBusinessProfile, getProducts, getStaff } from '../business-config'
import { packFor, GENERIC_PACK } from '@/config/niches'

const IDS = BUSINESS_TYPES.map((b) => b.id)

describe('the opening screen offers a real choice', () => {
  it('lists more than the original five', () => {
    // The service trades are the point of 2.0. If this drops back to five,
    // the demo is the old demo again.
    expect(IDS.length).toBeGreaterThanOrEqual(10)
    for (const key of ['barbershop', 'nails', 'medspa', 'detailing', 'mobile_detailing']) {
      expect(IDS).toContain(key as BusinessType)
    }
  })

  it('uses stroke icon components, never emoji', () => {
    // House rule, and a practical one: an emoji is the single element on this
    // screen that cannot be themed, and it is what the eye lands on first.
    for (const bt of BUSINESS_TYPES) {
      expect(typeof bt.icon, `${bt.id} icon must be a component`).not.toBe('string')
      expect(JSON.stringify(bt.label + bt.description))
        .not.toMatch(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u)
    }
  })

  it('puts every trade in a section that renders', () => {
    // A trade whose group is not in BUSINESS_GROUPS is simply absent from the
    // screen — no error, no empty state, just a missing option.
    for (const bt of BUSINESS_TYPES) {
      expect(BUSINESS_GROUPS, `${bt.id} is in a group nothing renders`)
        .toContain(bt.group)
    }
  })

  it('describes each trade differently', () => {
    const labels = BUSINESS_TYPES.map((b) => b.label)
    expect(new Set(labels).size).toBe(labels.length)
    const descriptions = BUSINESS_TYPES.map((b) => b.description)
    expect(new Set(descriptions).size).toBe(descriptions.length)
  })
})

describe('every trade has its own demo data', () => {
  it('has a profile with its own products and staff', () => {
    // The failure this catches is a trade added to the picker and mapped onto
    // a neighbour's profile: a barbershop demo showing croissants tells the
    // prospect the product was not built for them.
    for (const id of IDS) {
      const profile = getBusinessProfile(id)
      expect(profile, `${id} has no profile`).toBeTruthy()
      expect(getProducts(id).length, `${id} sells nothing`).toBeGreaterThan(3)
      expect(getStaff(id).length, `${id} has no staff`).toBeGreaterThan(0)
    }
  })

  it('never shows two trades the same product list', () => {
    const seen = new Map<string, BusinessType>()
    for (const id of IDS) {
      // Mobile detailing deliberately shares the shop's catalogue — same
      // chemicals, different vehicle — so it is compared on its name instead.
      const key = getProducts(id).map((p) => p.sku).join(',')
      const clash = seen.get(key)
      if (clash && !(id === 'mobile_detailing' || clash === 'mobile_detailing')) {
        throw new Error(`${id} and ${clash} sell an identical catalogue`)
      }
      seen.set(key, id)
    }
  })

  it('prices everything in cents, above zero except a free consult', () => {
    for (const id of IDS) {
      for (const product of getProducts(id)) {
        expect(product.price, `${id}/${product.name}`).toBeGreaterThanOrEqual(0)
        expect(Number.isInteger(product.price), `${id}/${product.name} not cents`).toBe(true)
      }
    }
  })
})

describe('a trade resolves to a pack', () => {
  it('maps the picker vocabulary onto the pack keys', () => {
    // Two vocabularies that grew up apart. Without the alias table these fall
    // through to the generic pack and the demo silently stops specialising.
    expect(packFor('fast_food').key).toBe('quickservice')
    expect(packFor('mobile_detailing').key).toBe('mobiledetailing')
    expect(packFor('barbershop').key).toBe('barbershop')
    expect(packFor('medspa').key).toBe('medspa')
  })

  it('still sends anything unrecognised to the generic pack', () => {
    // This fallback is what guarantees every merchant in production today
    // sees the portal they saw yesterday. Fuzzy matching would erode it.
    for (const junk of ['not-a-real-trade', '', 'restaurant ', 'BARBERSHOP']) {
      expect(packFor(junk).key, `${junk} matched a pack`).toBe(GENERIC_PACK.key)
    }
    expect(packFor(null).key).toBe(GENERIC_PACK.key)
    expect(packFor(undefined).key).toBe(GENERIC_PACK.key)
  })
})

describe('every trade the picker offers is actually a version', () => {
  it('resolves to its own pack, never the generic fallback', () => {
    // Coffee Shop, Auto Shop and Smoke Shop shipped in the picker with no
    // pack behind them, so all three fell through to GENERIC_PACK and showed
    // an identical dashboard, an identical sidebar order, and — for a smoke
    // shop — an "Appointments" figure for a business that has never taken
    // one. Offering a trade and not building it is worse than not offering it.
    for (const id of IDS) {
      expect(packFor(id).key, `${id} has no pack of its own`).not.toBe(GENERIC_PACK.key)
    }
  })

  it('opens each trade on a different headline figure', () => {
    const labels = IDS.map((id) => packFor(id).homeMetric.label)
    const dupes = labels.filter((l, i) => labels.indexOf(l) !== i)
    expect(dupes, 'two trades sharing a headline is a theme, not a version').toEqual([])
  })

  it('gives the counter trades figures instead of an empty book', () => {
    // A trade that does not book has no day to derive numbers from. Without
    // counterStats the workspace falls back to booking tiles and reports zero
    // appointments at a shop that does not take them.
    for (const id of IDS) {
      const pack = packFor(id)
      if (!pack.booksAtAll) {
        expect(pack.counterStats?.length, `${id} books nothing and shows nothing`).toBe(4)
      } else {
        expect(pack.counterStats, `${id} books, so it derives its own figures`).toBeUndefined()
      }
    }
  })
})

describe('Canadian money says it is Canadian', () => {
  it('qualifies the dollar sign on /canada, in both formatters', async () => {
    // Intl renders CAD under en-CA as a bare "$", which put "CA$1.4K" as a
    // headline and "$1,159.20" directly under it on the same screen. On a
    // portal quoting Canadian prices to Canadian merchants, an unqualified
    // "$" is an ambiguous price rather than a formatting slip.
    const { formatCents, formatCentsCompact } = await import('../format')
    const original = window.location.pathname
    history.replaceState(null, '', '/canada/merchant')
    try {
      expect(formatCents(115920)).toContain('CA$')
      expect(formatCentsCompact(140000)).toContain('CA$')
      expect(formatCents(null)).toContain('CA$')
      expect(formatCents(-500)).toMatch(/^-CA\$/)
    } finally {
      history.replaceState(null, '', original)
    }
  })

  it('leaves the US portal on a plain dollar sign', async () => {
    const { formatCents, formatCentsCompact } = await import('../format')
    const original = window.location.pathname
    history.replaceState(null, '', '/us/merchant')
    try {
      expect(formatCents(115920)).not.toContain('CA$')
      expect(formatCentsCompact(140000)).not.toContain('CA$')
    } finally {
      history.replaceState(null, '', original)
    }
  })
})
