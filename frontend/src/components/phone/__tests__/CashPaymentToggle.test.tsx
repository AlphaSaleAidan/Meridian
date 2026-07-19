/**
 * CashPaymentToggle — "Pay with Cash" warned opt-in.
 *
 * Contract:
 *  1. Turning it ON opens a warning modal with the EXACT required copy; the
 *     value only flips after the caller confirms.
 *  2. Cancel leaves it OFF (onChange never fires with true).
 *  3. Turning it OFF (already-on) is immediate — no warning modal.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import CashPaymentToggle, { CASH_WARNING_COPY } from '../CashPaymentToggle'

const EXACT_COPY =
  'By selecting this you are allowing potentially unpaid orders to reach your ' +
  'kitchen, are you sure you want to set this up?'

describe('CashPaymentToggle', () => {
  beforeEach(() => cleanup())
  afterEach(() => cleanup())

  it('exports the exact required warning copy', () => {
    expect(CASH_WARNING_COPY).toBe(EXACT_COPY)
  })

  it('enabling requires confirmation and shows the exact warning', () => {
    const onChange = vi.fn()
    render(<CashPaymentToggle enabled={false} onChange={onChange} />)

    fireEvent.click(screen.getByRole('switch', { name: /pay with cash/i }))

    // Modal is up with the exact copy; value has NOT changed yet.
    expect(screen.getByText(EXACT_COPY)).toBeTruthy()
    expect(onChange).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /yes, enable cash/i }))
    expect(onChange).toHaveBeenCalledWith(true)
  })

  it('cancel leaves it off (never enables)', () => {
    const onChange = vi.fn()
    render(<CashPaymentToggle enabled={false} onChange={onChange} />)

    fireEvent.click(screen.getByRole('switch', { name: /pay with cash/i }))
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))

    expect(onChange).not.toHaveBeenCalled()
    // Modal dismissed.
    expect(screen.queryByText(EXACT_COPY)).toBeNull()
  })

  it('turning OFF is immediate with no warning modal', () => {
    const onChange = vi.fn()
    render(<CashPaymentToggle enabled={true} onChange={onChange} />)

    fireEvent.click(screen.getByRole('switch', { name: /pay with cash/i }))

    expect(onChange).toHaveBeenCalledWith(false)
    expect(screen.queryByText(EXACT_COPY)).toBeNull()
  })
})
