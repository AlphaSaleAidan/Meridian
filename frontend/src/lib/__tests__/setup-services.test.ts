// Setup Services compose the one-time setup fee: the Website Buildout modules
// are fixed-price, Custom CRM build is rep-priced per deal. Whatever the rep
// types must land as a whole number — that sum becomes setup_fee_cents, the
// `setup=` onboarding param, the invoice, the SLA and Due Today, so a NaN or a
// fractional amount would leak into money on four surfaces.
import { describe, it, expect } from 'vitest'
import {
  AD_SPOT_AUDIO,
  AD_SPOT_PLACEMENTS,
  AD_SPOT_SERVICE,
  CUSTOM_CRM_SERVICE,
  parseSetupServiceAmount,
  WEBSITE_MODULES,
} from '../proposal-plans'
import {
  AD_SPOT_SERVICE as CA_AD_SPOT_SERVICE,
  AD_SPOT_PLACEMENTS as CA_AD_SPOT_PLACEMENTS,
  CAD_RATE,
  CUSTOM_CRM_SERVICE as CA_CUSTOM_CRM_SERVICE,
  parseSetupServiceAmount as caParseSetupServiceAmount,
  WEBSITE_MODULES as CA_WEBSITE_MODULES,
} from '../canada-proposal-plans'

// Mirrors the composition both create-customer and both lead-detail pages do:
//   setupFee = (website ? websiteOneTime : 0) + (crm ? parsed(crmAmount) : 0)
//            + (adSpot ? AD_SPOT_SERVICE.price : 0)
function composeSetupFee(
  opts: { website?: boolean; crm?: boolean; crmAmount?: string; adSpot?: boolean },
  modules = WEBSITE_MODULES,
  adSpot = AD_SPOT_SERVICE,
): number {
  const websiteOneTime = modules.filter(m => !m.monthly).reduce((t, m) => t + m.price, 0)
  return (opts.website ? websiteOneTime : 0)
    + (opts.crm ? parseSetupServiceAmount(opts.crmAmount) : 0)
    + (opts.adSpot ? adSpot.price : 0)
}

describe('parseSetupServiceAmount', () => {
  it('treats blank, whitespace, null and undefined as 0', () => {
    expect(parseSetupServiceAmount('')).toBe(0)
    expect(parseSetupServiceAmount('   ')).toBe(0)
    expect(parseSetupServiceAmount(null)).toBe(0)
    expect(parseSetupServiceAmount(undefined)).toBe(0)
  })

  it('treats unparseable input as 0, never NaN', () => {
    expect(parseSetupServiceAmount('abc')).toBe(0)
    expect(parseSetupServiceAmount('$1,200')).toBe(0)
    expect(Number.isNaN(parseSetupServiceAmount('abc'))).toBe(false)
  })

  it('floors negatives to 0 — a service can never discount the setup fee', () => {
    expect(parseSetupServiceAmount('-500')).toBe(0)
  })

  it('returns whole currency units', () => {
    expect(parseSetupServiceAmount('1200')).toBe(1200)
    expect(parseSetupServiceAmount(' 1200 ')).toBe(1200)
    expect(parseSetupServiceAmount('1199.99')).toBe(1199)
    expect(Number.isInteger(parseSetupServiceAmount('1199.99'))).toBe(true)
  })

  it('is shared verbatim with Canada — a rep-entered price has no FX to apply', () => {
    expect(caParseSetupServiceAmount).toBe(parseSetupServiceAmount)
    expect(CA_CUSTOM_CRM_SERVICE).toBe(CUSTOM_CRM_SERVICE)
  })
})

describe('Custom CRM build as a Setup Service', () => {
  it('does not collide with a Website Buildout module id', () => {
    expect(WEBSITE_MODULES.map(m => m.id)).not.toContain(CUSTOM_CRM_SERVICE.id)
  })

  it('carries no fixed price — the rep sets it', () => {
    expect(CUSTOM_CRM_SERVICE).not.toHaveProperty('price')
  })
})

describe('30-Second AI Advertisement as a Setup Service', () => {
  it('is US$1,000 / CA$1,400 — the price the rep quotes off', () => {
    expect(AD_SPOT_SERVICE.price).toBe(1000)
    expect(CA_AD_SPOT_SERVICE.price).toBe(1400)
    expect(CA_AD_SPOT_SERVICE.price).toBe(Math.round((AD_SPOT_SERVICE.price * CAD_RATE) / 50) * 50)
  })

  it('does not collide with a Website Buildout module or the CRM service id', () => {
    expect(WEBSITE_MODULES.map(m => m.id)).not.toContain(AD_SPOT_SERVICE.id)
    expect(AD_SPOT_SERVICE.id).not.toBe(CUSTOM_CRM_SERVICE.id)
  })

  it('keeps the sold runtime and the boarded shot count consistent', () => {
    // The backend generates SHOT_COUNT shots of SHOT_SECONDS each; if these
    // drift apart the rep sells 30 seconds and the pipeline builds something
    // else. src/api/routes/ad_spot.py holds the other half of this pair.
    expect(AD_SPOT_SERVICE.durationSeconds).toBe(30)
    expect(AD_SPOT_SERVICE.shotCount).toBe(6)
    expect(AD_SPOT_SERVICE.durationSeconds % AD_SPOT_SERVICE.shotCount).toBe(0)
  })

  it('is the same spot in both markets — only the price converts', () => {
    expect(CA_AD_SPOT_SERVICE.durationSeconds).toBe(AD_SPOT_SERVICE.durationSeconds)
    expect(CA_AD_SPOT_SERVICE.shotCount).toBe(AD_SPOT_SERVICE.shotCount)
    expect(CA_AD_SPOT_SERVICE.deliverables).toEqual(AD_SPOT_SERVICE.deliverables)
    // Placements are creative choices, not money — shared verbatim so a new
    // aspect ratio can never exist in one market and not the other.
    expect(CA_AD_SPOT_PLACEMENTS).toBe(AD_SPOT_PLACEMENTS)
  })

  it('offers placements and audio treatments the rep can actually pick', () => {
    expect(AD_SPOT_PLACEMENTS.length).toBeGreaterThan(0)
    expect(AD_SPOT_AUDIO.length).toBeGreaterThan(0)
    expect(new Set(AD_SPOT_PLACEMENTS.map(p => p.id)).size).toBe(AD_SPOT_PLACEMENTS.length)
    expect(new Set(AD_SPOT_AUDIO.map(a => a.id)).size).toBe(AD_SPOT_AUDIO.length)
  })
})

describe('setup fee composition', () => {
  const websiteOnly = composeSetupFee({ website: true })

  it('is 0 with no service toggled', () => {
    expect(composeSetupFee({})).toBe(0)
  })

  it('is unchanged by the CRM service when it is off', () => {
    expect(composeSetupFee({ website: true, crm: false, crmAmount: '1200' })).toBe(websiteOnly)
  })

  it('adds the rep-entered CRM price on top of the buildout', () => {
    expect(composeSetupFee({ website: true, crm: true, crmAmount: '1200' })).toBe(websiteOnly + 1200)
  })

  it('bills the CRM build on its own when the buildout is off', () => {
    expect(composeSetupFee({ crm: true, crmAmount: '1200' })).toBe(1200)
  })

  it('counts a toggled CRM build with a blank or junk price as 0', () => {
    expect(composeSetupFee({ website: true, crm: true, crmAmount: '' })).toBe(websiteOnly)
    expect(composeSetupFee({ website: true, crm: true, crmAmount: 'abc' })).toBe(websiteOnly)
  })

  it('adds the ad spot on top of everything else', () => {
    expect(composeSetupFee({ adSpot: true })).toBe(AD_SPOT_SERVICE.price)
    expect(composeSetupFee({ website: true, adSpot: true })).toBe(websiteOnly + AD_SPOT_SERVICE.price)
    expect(composeSetupFee({ website: true, crm: true, crmAmount: '1200', adSpot: true }))
      .toBe(websiteOnly + 1200 + AD_SPOT_SERVICE.price)
  })

  it('is unchanged by the ad spot when it is off', () => {
    expect(composeSetupFee({ website: true, adSpot: false })).toBe(websiteOnly)
  })

  it('bills the ad spot in CAD on the Canada page', () => {
    expect(composeSetupFee({ adSpot: true }, CA_WEBSITE_MODULES, CA_AD_SPOT_SERVICE))
      .toBe(CA_AD_SPOT_SERVICE.price)
  })

  it('stays a whole number for every combination, in both markets', () => {
    for (const [modules, adSpot] of [
      [WEBSITE_MODULES, AD_SPOT_SERVICE],
      [CA_WEBSITE_MODULES, CA_AD_SPOT_SERVICE],
    ] as const) {
      for (const website of [true, false]) {
        for (const spot of [true, false]) {
          for (const crmAmount of ['', '   ', 'abc', '-5', '1199.99', '1200']) {
            const total = composeSetupFee({ website, crm: true, crmAmount, adSpot: spot }, modules, adSpot)
            expect(Number.isInteger(total)).toBe(true)
            expect(total).toBeGreaterThanOrEqual(0)
          }
        }
      }
    }
  })
})
