/**
 * One trade, whatever wrote it down.
 *
 * `business_type` on an organization is written by three systems that never
 * agreed on a vocabulary: the rep portals write a deck slug (`ca-salon`),
 * Square detection writes a BusinessType (`coffee_shop`), and both fall back
 * to the literal "restaurant". packFor() matched pack keys and none of those,
 * so every account a rep created resolved to the generic pack — the merchant
 * bought a trade version and got the untailored portal, silently, because the
 * fallback is a working portal rather than an error.
 *
 * These are the tests that make the join real. The last one is the important
 * one: unknown text must STILL fall through, because that fallback is what
 * protects every merchant already in production with a value nobody planned.
 */
import { describe, expect, it } from 'vitest'
import {
  packFor, GENERIC_PACK, PACK_DECK_SLUGS, ALL_PACKS,
  SELLABLE_TRADES, SELLABLE_GROUPS, deckSlugFor,
} from '../niches'
import { verticalsByGroup } from '@/data/cadVerticals'
import { usVerticalsByGroup } from '@/data/usVerticals'

describe('what the rep picked is what the merchant gets', () => {
  it('resolves a deck slug from either market to the same pack', () => {
    for (const [pack, slugs] of Object.entries(PACK_DECK_SLUGS)) {
      for (const slug of slugs) {
        expect(packFor(slug).key, `${slug} should resolve to ${pack}`).toBe(pack)
      }
    }
  })

  it('gives a Canadian and an American shop of one trade the same product', () => {
    expect(packFor('ca-salon').key).toBe(packFor('us-salon').key)
    expect(packFor('ca-nailsalon').key).toBe(packFor('us-nailsalon').key)
    expect(packFor('ca-detailing').key).toBe(packFor('us-detailing').key)
  })

  it('still resolves what Square detection writes', () => {
    // A second, older path into the same field.
    for (const [detected, pack] of [
      ['coffee_shop', 'coffeeshop'], ['fast_food', 'quickservice'],
      ['auto_shop', 'autoshop'], ['smoke_shop', 'smokeshop'],
      ['restaurant', 'restaurant'],
    ]) {
      expect(packFor(detected).key, `${detected}`).toBe(pack)
    }
  })

  it('maps every slug to a pack that exists', () => {
    const keys = new Set(ALL_PACKS.map((p) => p.key))
    for (const pack of Object.keys(PACK_DECK_SLUGS)) {
      expect(keys.has(pack), `${pack} has deck slugs but no pack`).toBe(true)
    }
  })

  it('never maps one slug to two packs', () => {
    const seen = new Map<string, string>()
    for (const [pack, slugs] of Object.entries(PACK_DECK_SLUGS)) {
      for (const slug of slugs) {
        expect(seen.has(slug), `${slug} claimed by ${seen.get(slug)} and ${pack}`).toBe(false)
        seen.set(slug, pack)
      }
    }
  })

  it('names only slugs the deck catalogues actually contain', () => {
    // A typo here is invisible: the slug simply never matches and the
    // merchant quietly gets the generic portal.
    const real = new Set<string>()
    for (const g of verticalsByGroup()) for (const v of g.items) real.add(v.slug)
    for (const g of usVerticalsByGroup()) for (const v of g.items) real.add(v.slug)
    for (const [pack, slugs] of Object.entries(PACK_DECK_SLUGS)) {
      for (const slug of slugs) {
        expect(real.has(slug), `${pack} maps to ${slug}, which is in no catalogue`).toBe(true)
      }
    }
  })

  it('leaves anything unrecognised on the generic pack', () => {
    // The protection for every merchant already in production.
    for (const junk of ['ca-artgallery', 'us-vetclinic', 'not-a-trade', '']) {
      expect(packFor(junk).key, `${junk}`).toBe(GENERIC_PACK.key)
    }
    expect(packFor(null).key).toBe(GENERIC_PACK.key)
  })
})

describe('the rep can only sell what we built', () => {
  it('offers exactly the trades that have a product version', () => {
    // The picker listed all 43/45 proposal decks, so a rep could close an art
    // gallery or a vet clinic — a deck with no product behind it. That
    // merchant pays for a tailored portal and gets the generic one.
    const packKeys = new Set(ALL_PACKS.map((p) => p.key).filter((k) => k !== GENERIC_PACK.key))
    for (const trade of SELLABLE_TRADES) {
      expect(packKeys.has(trade.key), `${trade.key} is sellable with no pack`).toBe(true)
    }
    // And nothing we built is quietly unsellable.
    for (const key of packKeys) {
      expect(SELLABLE_TRADES.some((t) => t.key === key), `${key} is built but not sellable`).toBe(true)
    }
  })

  it('stores a value the portal resolves without translation', () => {
    // The whole point: what the rep picked IS what packFor reads.
    for (const trade of SELLABLE_TRADES) {
      expect(packFor(trade.key).key).toBe(trade.key)
    }
  })

  it('links a deck in both markets for every trade', () => {
    for (const trade of SELLABLE_TRADES) {
      for (const market of ['ca', 'us'] as const) {
        const slug = deckSlugFor(trade.key, market)
        expect(slug, `${trade.key} has no ${market} deck`).toBeTruthy()
      }
    }
  })

  it('puts every sellable trade in a group that renders', () => {
    for (const trade of SELLABLE_TRADES) {
      expect(SELLABLE_GROUPS).toContain(trade.group)
    }
  })

  it('does not offer the same trade twice', () => {
    const keys = SELLABLE_TRADES.map((t) => t.key)
    expect(new Set(keys).size).toBe(keys.length)
    const labels = SELLABLE_TRADES.map((t) => t.label)
    expect(new Set(labels).size).toBe(labels.length)
  })
})
