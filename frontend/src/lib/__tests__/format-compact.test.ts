// formatCentsCompact renders 45 stat tiles across both markets, and it picks
// its currency from window.location.pathname. It used to hardcode the "CA$"
// prefix on the K/M branches only, so a Canada stat row showed "CA$13.5K" next
// to a bare "$378" — same formatter, same row, two currencies implied. It also
// tested `dollars >= 1_000`, which no negative can satisfy, so a -$4,000
// refund fell through to the small-value branch and rendered unabbreviated.
import { describe, it, expect, beforeEach } from 'vitest'
import { formatCentsCompact } from '../format'

function at(path: string) {
  window.history.pushState({}, '', path)
}

describe('formatCentsCompact', () => {
  beforeEach(() => at('/'))

  describe('on a Canada surface', () => {
    beforeEach(() => at('/canada/merchant'))

    it('carries the CA$ prefix across every magnitude', () => {
      expect(formatCentsCompact(37_800)).toBe('CA$378')
      expect(formatCentsCompact(1_350_000)).toBe('CA$13.5K')
      expect(formatCentsCompact(660_100_000)).toBe('CA$6.6M')
    })

    it('never renders a bare $ next to an abbreviated CA$', () => {
      const small = formatCentsCompact(37_800)
      const large = formatCentsCompact(1_350_000)
      expect(small.startsWith('CA$')).toBe(true)
      expect(large.startsWith('CA$')).toBe(true)
    })

    it('puts the sign outside the prefix and still abbreviates', () => {
      expect(formatCentsCompact(-400_000)).toBe('-CA$4.0K')
      expect(formatCentsCompact(-37_800)).toBe('-CA$378')
    })

    it('renders a null amount as zero, not a blank', () => {
      expect(formatCentsCompact(null)).toBe('CA$0')
      expect(formatCentsCompact(undefined)).toBe('CA$0')
    })
  })

  describe('on a US surface', () => {
    beforeEach(() => at('/us/merchant'))

    it('keeps the plain $ prefix', () => {
      expect(formatCentsCompact(37_800)).toBe('$378')
      expect(formatCentsCompact(1_350_000)).toBe('$13.5K')
      expect(formatCentsCompact(-400_000)).toBe('-$4.0K')
    })
  })
})
