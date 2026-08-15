/**
 * SegmentedControl — one control that both SHOWS a state and SETS it.
 *
 * Today's Book previously carried a status chip AND two separate action
 * buttons on every row: three elements saying one thing. A host scanning
 * forty rows had to read the chip to learn the state and then find the right
 * button to change it. A segment strip collapses that — the filled segment
 * IS the state, and tapping another one is the change.
 *
 * MOTION (SaaS dashboard → Emil primary, Jakub secondary):
 *  - The indicator slides between segments in 180ms. That is the one piece of
 *    motion here and it earns its place: it links "the thing I tapped" to
 *    "the state that is now true", which a hard cut leaves the eye to work
 *    out on its own.
 *  - translateX only. Every segment is the same width, so there is no width
 *    or left animation and nothing reflows.
 *  - The colour travels with the indicator, so seating a guest visibly moves
 *    from blue to teal rather than blinking.
 *  - Icons do not animate. They are re-rendered a few dozen times a shift and
 *    a pop on each one would become a tic.
 *  - prefers-reduced-motion removes the slide; the indicator still lands in
 *    the right place, instantly.
 */
import { useId, type ComponentType } from 'react'

export interface Segment<T extends string> {
  value: T
  label: string
  Icon?: ComponentType<{ className?: string }>
  /** Tailwind-ready hex for the filled state. Defaults to Meridian blue. */
  tint?: string
  disabled?: boolean
}

interface SegmentedControlProps<T extends string> {
  value: T
  segments: Segment<T>[]
  onChange: (value: T) => void
  disabled?: boolean
  ariaLabel: string
  className?: string
}

const DEFAULT_TINT = '#1A8FD6'

export function SegmentedControl<T extends string>({
  value, segments, onChange, disabled = false, ariaLabel, className = '',
}: SegmentedControlProps<T>) {
  const groupId = useId()
  const index = Math.max(0, segments.findIndex((s) => s.value === value))
  const current = segments[index]
  const tint = current?.tint || DEFAULT_TINT
  const width = 100 / Math.max(segments.length, 1)

  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={[
        'relative inline-flex items-center rounded-lg border border-[#1F1F23]',
        'bg-[#0E0E11] p-0.5',
        disabled ? 'opacity-50' : '',
        className,
      ].join(' ')}
    >
      {/* The travelling fill. aria-hidden — the radios below carry the state. */}
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0.5 left-0.5 rounded-[7px] border motion-safe:duration-[180ms]"
        style={{
          width: `calc(${width}% - 2px)`,
          transform: `translateX(${index * 100}%)`,
          background: `${tint}1F`,
          borderColor: `${tint}59`,
          // Named explicitly rather than `all`: `all` would also transition
          // width, which is a layout property and would reflow the strip.
          transitionProperty: 'transform, background-color, border-color',
          transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      />

      {segments.map((seg) => {
        const isActive = seg.value === value
        const segTint = seg.tint || DEFAULT_TINT
        return (
          <button
            key={seg.value}
            type="button"
            role="radio"
            aria-checked={isActive}
            aria-label={seg.label}
            id={`${groupId}-${seg.value}`}
            disabled={disabled || seg.disabled}
            onClick={() => !isActive && onChange(seg.value)}
            style={{ width: `${width}%`, color: isActive ? segTint : undefined }}
            className={[
              'relative z-10 inline-flex items-center justify-center gap-1 whitespace-nowrap',
              'rounded-[7px] px-2.5 py-1 text-xs font-medium',
              'transition-colors duration-150',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1A8FD6]/50',
              isActive ? '' : 'text-[#A1A1A8] hover:text-[#F5F5F7]',
              disabled || seg.disabled ? 'cursor-not-allowed' : 'cursor-pointer',
            ].join(' ')}
          >
            {seg.Icon && <seg.Icon className="h-3.5 w-3.5" />}
            {seg.label}
          </button>
        )
      })}
    </div>
  )
}

export default SegmentedControl
