/**
 * Trade packs: the safety property first, the feature second.
 *
 * Every merchant in production today has no trade set. The single thing that
 * must be true before any of this ships is that those merchants see exactly
 * the portal they saw this morning — same modules, same order. Everything
 * else in this file is the feature working; the first two tests are the
 * promise that it cannot hurt anyone while it does.
 */
import { describe, expect, it } from 'vitest'
import { defaultModuleFlags, canadaModuleFlags, flagsForMerchant, flagsForPath } from '../moduleFlags'
import { orderPillars, merchantPillars } from '../merchantPillars'
import { packFor, ALL_PACKS, NICHE_PACKS } from '../niches'

describe('a merchant with no trade set', () => {
  it('gets exactly the flags the route gave them before', () => {
    for (const path of ['/canada/merchant', '/us/merchant', '/demo', '/app']) {
      expect(flagsForMerchant(path, packFor(null).modules))
        .toEqual(flagsForPath(path))
      expect(flagsForMerchant(path, packFor(undefined).modules))
        .toEqual(flagsForPath(path))
      expect(flagsForMerchant(path, packFor('not-a-real-trade').modules))
        .toEqual(flagsForPath(path))
    }
  })

  it('gets the pillars in their original order', () => {
    expect(orderPillars(merchantPillars, packFor(null).pillarOrder))
      .toEqual(merchantPillars)
  })
})

describe('the public demos', () => {
  it('get a Bookings tab, now that it has a book to show', () => {
    // Gated off while BookingsPage had no demo path — it called the real API
    // with the org id 'demo' and rendered an error in front of a prospect.
    // lib/demo-bookings.ts answers those calls now, and Bookings is the
    // pillar the service trades open on, so an absent tab is its own failure.
    for (const path of ['/demo', '/canada/demo']) {
      expect(flagsForPath(path).bookings).toBe(true)
    }
  })

  it('still get bookings on the real merchant portals', () => {
    for (const path of ['/canada/merchant', '/us/merchant', '/app']) {
      expect(flagsForPath(path).bookings).toBe(true)
    }
  })

  it('show exactly what the Canada portal shows', () => {
    // The demo's whole claim is that it is the product. Any module that is
    // on in one and off in the other makes that claim false.
    expect(flagsForPath('/demo')).toEqual(flagsForPath('/canada/merchant'))
    expect(flagsForPath('/canada/demo')).toEqual(flagsForPath('/canada/merchant'))
  })
})

describe('a pack may only turn modules OFF', () => {
  it('cannot resurrect a module its market cut', () => {
    // Canada deliberately cut these. A pack asking for them back must lose,
    // or the market trim silently stops meaning anything.
    const greedy = { insights: true, customers: true, spaces3D: true }
    const flags = flagsForMerchant('/canada/merchant', greedy)
    expect(flags.insights).toBe(false)
    expect(flags.customers).toBe(false)
    expect(flags.spaces3D).toBe(false)
    expect(canadaModuleFlags.insights).toBe(false)
  })

  it('turns off what it asks to turn off', () => {
    const flags = flagsForMerchant('/app', { inventory: false, camera: false })
    expect(flags.inventory).toBe(false)
    expect(flags.camera).toBe(false)
    // Untouched keys keep the base value.
    expect(flags.phoneCalls).toBe(defaultModuleFlags.phoneCalls)
  })
})

describe('margin tracking follows the product, not the pillar count', () => {
  it('every trade that sells or consumes product keeps Inventory', () => {
    // The earlier packs switched Inventory off for the service trades to
    // "simplify" them, which removed margin tracking from businesses that
    // sell retail and burn through consumables. A barbershop sells pomade; a
    // med spa stocks injectables with expiry dates.
    for (const key of ['barbershop', 'nails', 'detailing', 'mobiledetailing',
                       'medspa', 'restaurant', 'quickservice']) {
      const flags = flagsForMerchant('/app', packFor(key).modules)
      expect(flags.inventory, `${key} must keep Inventory`).toBe(true)
    }
  })

  it('drops Menu Matrix for everyone except the food trades', () => {
    for (const key of ['barbershop', 'nails', 'detailing', 'mobiledetailing', 'medspa']) {
      expect(packFor(key).hiddenViews).toContain('inventory/menu')
    }
    for (const key of ['restaurant', 'quickservice']) {
      expect(packFor(key).hiddenViews || []).not.toContain('inventory/menu')
    }
  })

  it('gives the food trades their camera back', () => {
    for (const key of ['restaurant', 'quickservice']) {
      expect(flagsForMerchant('/app', packFor(key).modules).camera).toBe(true)
    }
  })

  it('hides only views that exist', () => {
    const real = new Set(
      merchantPillars.flatMap((p) => p.segments.map((s) => `${p.path}/${s.view}`)))
    for (const pack of ALL_PACKS) {
      for (const view of pack.hiddenViews || []) {
        expect(real.has(view), `${pack.key} hides unknown view ${view}`).toBe(true)
      }
    }
  })

  it('never hides every segment of a pillar it keeps', () => {
    // A pillar with no segments left would render an empty page rather than
    // being absent, which is worse than either.
    for (const pack of ALL_PACKS) {
      const hidden = new Set(pack.hiddenViews || [])
      for (const pillar of merchantPillars) {
        const left = pillar.segments.filter((s) => !hidden.has(`${pillar.path}/${s.view}`))
        expect(left.length, `${pack.key} emptied ${pillar.path}`).toBeGreaterThan(0)
      }
    }
  })
})

describe('the packs themselves', () => {
  it('gives a takeout shop no booking module at all', () => {
    const pizza = packFor('quickservice')
    expect(pizza.booksAtAll).toBe(false)
    expect(flagsForMerchant('/us/merchant', pizza.modules).bookings).toBe(false)
  })

  it('keeps bookings for every trade that books', () => {
    for (const pack of ALL_PACKS.filter((p) => p.booksAtAll)) {
      expect(flagsForMerchant('/us/merchant', pack.modules).bookings).toBe(true)
    }
  })

  it('opens a barbershop on the book and a takeout shop on the phone', () => {
    const barber = orderPillars(merchantPillars, packFor('barbershop').pillarOrder)
    expect(barber[0].path).toBe('bookings')
    const pizza = orderPillars(merchantPillars, packFor('quickservice').pillarOrder)
    expect(pizza[0].path).toBe('phone')
  })

  it('never drops a pillar while reordering', () => {
    for (const pack of ALL_PACKS) {
      const ordered = orderPillars(merchantPillars, pack.pillarOrder)
      expect(ordered).toHaveLength(merchantPillars.length)
      expect(new Set(ordered.map((p) => p.path)))
        .toEqual(new Set(merchantPillars.map((p) => p.path)))
    }
  })

  it('gives every trade a different headline number', () => {
    // If two trades open on the same figure, one of them is a theme rather
    // than a version of the product.
    const labels = NICHE_PACKS.map((p) => p.homeMetric.label)
    expect(new Set(labels).size).toBe(labels.length)
  })

  it('names a pillar order that actually exists', () => {
    const paths = new Set(merchantPillars.map((p) => p.path))
    for (const pack of ALL_PACKS) {
      for (const path of pack.pillarOrder || []) {
        expect(paths.has(path)).toBe(true)
      }
    }
  })
})
