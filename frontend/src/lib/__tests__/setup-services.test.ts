// Setup Services compose the one-time setup fee: the Website Buildout modules
// are fixed-price, Custom CRM build is rep-priced per deal. Whatever the rep
// types must land as a whole number — that sum becomes setup_fee_cents, the
// `setup=` onboarding param, the invoice, the SLA and Due Today, so a NaN or a
// fractional amount would leak into money on four surfaces.
import { describe, it, expect } from 'vitest'
import {
  CUSTOM_CRM_SERVICE,
  parseSetupServiceAmount,
  WEBSITE_MODULES,
} from '../proposal-plans'
import {
  CUSTOM_CRM_SERVICE as CA_CUSTOM_CRM_SERVICE,
  parseSetupServiceAmount as caParseSetupServiceAmount,
  WEBSITE_MODULES as CA_WEBSITE_MODULES,
} from '../canada-proposal-plans'

// Mirrors the composition both create-customer and both lead-detail pages do:
//   setupFee = (website ? websiteOneTime : 0) + (crm ? parsed(crmAmount) : 0)
function composeSetupFee(
  opts: { website?: boolean; crm?: boolean; crmAmount?: string },
  modules = WEBSITE_MODULES,
): number {
  const websiteOneTime = modules.filter(m => !m.monthly).reduce((t, m) => t + m.price, 0)
  return (opts.website ? websiteOneTime : 0) + (opts.crm ? parseSetupServiceAmount(opts.crmAmount) : 0)
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

  it('stays a whole number for every combination, in both markets', () => {
    for (const modules of [WEBSITE_MODULES, CA_WEBSITE_MODULES]) {
      for (const website of [true, false]) {
        for (const crmAmount of ['', '   ', 'abc', '-5', '1199.99', '1200']) {
          const total = composeSetupFee({ website, crm: true, crmAmount }, modules)
          expect(Number.isInteger(total)).toBe(true)
          expect(total).toBeGreaterThanOrEqual(0)
        }
      }
    }
  })
})
