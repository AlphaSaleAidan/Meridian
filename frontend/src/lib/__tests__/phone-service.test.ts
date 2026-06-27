import { describe, it, expect } from 'vitest'
import { isValidE164 } from '../phone-service'

describe('isValidE164', () => {
  it('accepts well-formed E.164 numbers', () => {
    expect(isValidE164('+14165551234')).toBe(true) // CA/US 11 digits
    expect(isValidE164('+442071838750')).toBe(true) // UK
    expect(isValidE164('+919876543210')).toBe(true) // IN
  })

  it('trims surrounding whitespace before validating', () => {
    expect(isValidE164('  +14165551234  ')).toBe(true)
  })

  it('rejects numbers without a leading +', () => {
    expect(isValidE164('14165551234')).toBe(false)
  })

  it('rejects a leading-zero country code', () => {
    expect(isValidE164('+04165551234')).toBe(false)
  })

  it('rejects numbers that are too short or too long', () => {
    expect(isValidE164('+1234567')).toBe(false) // 7 digits, below E.164 minimum
    expect(isValidE164('+1234567890123456')).toBe(false) // 16 digits, above max
  })

  it('rejects non-digit characters and empty input', () => {
    expect(isValidE164('+1 (416) 555-1234')).toBe(false)
    expect(isValidE164('')).toBe(false)
    expect(isValidE164('+')).toBe(false)
  })
})
