/**
 * Select — a real listbox, not a native <select>.
 *
 * Native selects render as the OS widget: a white Aqua popup on macOS, a
 * full-screen wheel on iOS. On a dark dashboard that is the single loudest
 * "this was assembled, not designed" tell, and it is the one control we
 * cannot style our way out of.
 *
 * The cost of replacing it is that the browser stops giving us keyboard
 * behaviour for free, so it is all here and it is not optional: arrow keys,
 * Home/End, type-ahead, Escape, Tab-to-close, aria-activedescendant. A
 * prettier control that a keyboard user cannot operate is a downgrade.
 *
 * MOTION (SaaS dashboard → Emil primary, Jakub secondary):
 *  - Opening is occasional, so it earns a short enter: 150ms, opacity +
 *    4px rise + 0.98 scale, origin at the trigger edge so it grows out of
 *    the button rather than out of its own middle.
 *  - Exit is 90ms and translate-free. The user has already decided; the
 *    animation is only there to stop the panel vanishing between frames.
 *  - Moving the highlight with the arrow keys is NOT animated. Keyboard
 *    interactions want the answer, not a transition.
 *  - CSS transitions rather than keyframes, so a fast open/close/open
 *    retargets mid-flight instead of queueing.
 *  - Only transform, opacity and colour animate — no layout properties.
 *  - prefers-reduced-motion collapses every duration to zero. The panel
 *    still appears and disappears; it just stops moving.
 */
import {
  useCallback, useEffect, useId, useLayoutEffect, useRef, useState,
} from 'react'
import { Check, ChevronDown } from 'lucide-react'

export interface SelectOption {
  value: string
  label: string
  /** Second line, e.g. a duration or a price. Optional. */
  hint?: string
  disabled?: boolean
}

interface SelectProps {
  value: string
  onChange: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  disabled?: boolean
  className?: string
  /** Accessible name when there is no visible <label> pointing at this. */
  ariaLabel?: string
  id?: string
}

const ENTER_MS = 150
const EXIT_MS = 90

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined'
    && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

export function Select({
  value, onChange, options, placeholder = 'Select…',
  disabled = false, className = '', ariaLabel, id,
}: SelectProps) {
  const [open, setOpen] = useState(false)
  // Kept mounted for the length of the exit so the panel can fade instead of
  // disappearing between two frames.
  const [mounted, setMounted] = useState(false)
  const [entered, setEntered] = useState(false)
  const [active, setActive] = useState(0)
  const [dropUp, setDropUp] = useState(false)

  const rootRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const typeahead = useRef({ buffer: '', at: 0 })
  const exitTimer = useRef<number>()

  const reactId = useId()
  const listId = `${id || reactId}-listbox`
  const selectedIndex = options.findIndex((o) => o.value === value)
  const selected = selectedIndex >= 0 ? options[selectedIndex] : undefined

  // ── open / close ──────────────────────────────────────────────────────
  const close = useCallback((focusTrigger = true) => {
    setOpen(false)
    if (focusTrigger) buttonRef.current?.focus()
  }, [])

  useEffect(() => {
    window.clearTimeout(exitTimer.current)
    if (open) {
      setMounted(true)
      // Two frames: one to mount at the start state, one to transition off
      // it. A single rAF lands in the same paint and the transition is
      // skipped entirely.
      const raf = requestAnimationFrame(() => requestAnimationFrame(() => setEntered(true)))
      return () => cancelAnimationFrame(raf)
    }
    setEntered(false)
    if (!mounted) return
    exitTimer.current = window.setTimeout(
      () => setMounted(false), prefersReducedMotion() ? 0 : EXIT_MS,
    )
    return () => window.clearTimeout(exitTimer.current)
  }, [open, mounted])

  // Open upward when the panel would otherwise run off the bottom. Measured
  // before paint so the panel never visibly jumps from one side to the other.
  useLayoutEffect(() => {
    if (!open || !buttonRef.current) return
    const rect = buttonRef.current.getBoundingClientRect()
    const needed = Math.min(options.length * 40 + 12, 280)
    setDropUp(rect.bottom + needed > window.innerHeight && rect.top > needed)
  }, [open, options.length])

  useEffect(() => {
    if (!open) return
    setActive(selectedIndex >= 0 ? selectedIndex : 0)
  }, [open, selectedIndex])

  useEffect(() => {
    if (!open) return
    const onPointer = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) close(false)
    }
    // pointerdown, not click: closing on click lets the press land on
    // whatever is underneath the panel.
    document.addEventListener('pointerdown', onPointer)
    return () => document.removeEventListener('pointerdown', onPointer)
  }, [open, close])

  // Keep the highlighted option in view without smooth-scrolling it — a
  // held-down arrow key should not animate a queue of scrolls.
  useEffect(() => {
    if (!open || !listRef.current) return
    listRef.current
      .querySelector<HTMLElement>(`[data-index="${active}"]`)
      ?.scrollIntoView({ block: 'nearest' })
  }, [open, active])

  const step = (from: number, dir: 1 | -1): number => {
    const n = options.length
    for (let i = 1; i <= n; i++) {
      const next = (from + dir * i + n * i) % n
      if (!options[next]?.disabled) return next
    }
    return from
  }

  const commit = (index: number) => {
    const opt = options[index]
    if (!opt || opt.disabled) return
    onChange(opt.value)
    close()
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return

    if (!open) {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) {
        e.preventDefault()
        setOpen(true)
      }
      return
    }

    switch (e.key) {
      case 'Escape':
        e.preventDefault()
        close()
        return
      case 'Tab':
        // Let focus move on, but don't leave an orphaned panel behind.
        close(false)
        return
      case 'ArrowDown':
        e.preventDefault()
        setActive((i) => step(i, 1))
        return
      case 'ArrowUp':
        e.preventDefault()
        setActive((i) => step(i, -1))
        return
      case 'Home':
        e.preventDefault()
        setActive(step(options.length - 1, 1))
        return
      case 'End':
        e.preventDefault()
        setActive(step(0, -1))
        return
      case 'Enter':
      case ' ':
        e.preventDefault()
        commit(active)
        return
    }

    // Type-ahead: "fa" jumps to Fade. The buffer resets after a second so a
    // later "f" starts a fresh search rather than extending a stale one.
    if (e.key.length === 1 && !e.metaKey && !e.ctrlKey && !e.altKey) {
      const now = Date.now()
      const t = typeahead.current
      t.buffer = now - t.at > 1000 ? e.key : t.buffer + e.key
      t.at = now
      const q = t.buffer.toLowerCase()
      const hit = options.findIndex(
        (o) => !o.disabled && o.label.toLowerCase().startsWith(q),
      )
      if (hit >= 0) setActive(hit)
    }
  }

  const reduced = prefersReducedMotion()
  const enterMs = reduced ? 0 : ENTER_MS
  const exitMs = reduced ? 0 : EXIT_MS

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        ref={buttonRef}
        id={id}
        type="button"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={() => !disabled && setOpen((o) => !o)}
        onKeyDown={onKeyDown}
        className={[
          'flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2',
          'text-left text-sm transition-colors duration-150',
          'border-[#1F1F23] bg-[#0E0E11] text-[#F5F5F7]',
          'hover:border-[#2A2A30]',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1A8FD6]/50 focus-visible:border-[#1A8FD6]/60',
          open ? 'border-[#1A8FD6]/60' : '',
          disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
        ].join(' ')}
      >
        <span className={`truncate ${selected ? '' : 'text-[#6B6B73]'}`}>
          {selected?.label || placeholder}
        </span>
        <ChevronDown
          className="h-4 w-4 shrink-0 text-[#A1A1A8] transition-transform"
          style={{
            transitionDuration: `${enterMs}ms`,
            transform: open ? 'rotate(180deg)' : 'none',
          }}
          aria-hidden="true"
        />
      </button>

      {mounted && (
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          tabIndex={-1}
          aria-activedescendant={`${listId}-${active}`}
          className={[
            'absolute z-50 max-h-[280px] w-full overflow-y-auto rounded-lg border p-1',
            'border-[#1F1F23] bg-[#111113] shadow-2xl shadow-black/50',
            dropUp ? 'bottom-full mb-1' : 'top-full mt-1',
          ].join(' ')}
          style={{
            // Grows out of the trigger edge, not out of its own middle.
            transformOrigin: dropUp ? 'bottom center' : 'top center',
            transitionProperty: 'opacity, transform',
            transitionDuration: `${entered ? enterMs : exitMs}ms`,
            transitionTimingFunction: entered
              ? 'cubic-bezier(0.16, 1, 0.3, 1)'   // decelerate into place
              : 'cubic-bezier(0.4, 0, 1, 1)',     // leave without lingering
            opacity: entered ? 1 : 0,
            transform: entered
              ? 'translateY(0) scale(1)'
              // Exit stays put and only fades — the panel has done its job and
              // a second slide would just be noise.
              : `translateY(${dropUp ? 4 : -4}px) scale(0.98)`,
          }}
        >
          {options.map((opt, i) => {
            const isSelected = opt.value === value
            const isActive = i === active
            return (
              <li
                key={opt.value}
                id={`${listId}-${i}`}
                data-index={i}
                role="option"
                aria-selected={isSelected}
                aria-disabled={opt.disabled || undefined}
                onPointerEnter={() => !opt.disabled && setActive(i)}
                onClick={() => commit(i)}
                className={[
                  'flex cursor-pointer items-center justify-between gap-3 rounded-md px-2.5 py-2 text-sm',
                  opt.disabled
                    ? 'cursor-not-allowed text-[#5A5A62]'
                    : isActive
                      ? 'bg-[#1A8FD6]/12 text-[#F5F5F7]'
                      : 'text-[#D4D4D8]',
                ].join(' ')}
              >
                <span className="min-w-0">
                  <span className="block truncate">{opt.label}</span>
                  {opt.hint && (
                    <span className="block truncate text-xs text-[#A1A1A8]">
                      {opt.hint}
                    </span>
                  )}
                </span>
                {isSelected && (
                  <Check className="h-4 w-4 shrink-0 text-[#1A8FD6]" aria-hidden="true" />
                )}
              </li>
            )
          })}
          {options.length === 0 && (
            <li className="px-2.5 py-2 text-sm text-[#6B6B73]">Nothing to choose from</li>
          )}
        </ul>
      )}
    </div>
  )
}

export default Select
