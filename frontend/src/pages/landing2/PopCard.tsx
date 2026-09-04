import { useRef, type ReactNode } from 'react'

/**
 * A light-register card with pop: a soft brand-blue radial that follows the
 * cursor (CSS vars, no re-render) and a gentle lift. The highlight lives on
 * an overlay so card content never repaints. Touch devices simply get the
 * lift on tap focus; reduced motion gets a static card.
 */
export default function PopCard({
  children,
  className = '',
  glow = 'rgba(26,143,214,0.10)',
}: {
  children: ReactNode
  className?: string
  glow?: string
}) {
  const ref = useRef<HTMLDivElement>(null)

  return (
    <div
      ref={ref}
      onMouseMove={(e) => {
        const el = ref.current
        if (!el) return
        const r = el.getBoundingClientRect()
        el.style.setProperty('--px', `${e.clientX - r.left}px`)
        el.style.setProperty('--py', `${e.clientY - r.top}px`)
      }}
      className={`group relative overflow-hidden rounded-2xl border border-[#EAE5DC] bg-white shadow-[0_8px_30px_rgba(23,26,32,0.06)] transition-transform duration-300 motion-safe:hover:-translate-y-1 hover:shadow-[0_18px_50px_rgba(23,26,32,0.12)] ${className}`}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: `radial-gradient(360px circle at var(--px, 50%) var(--py, 50%), ${glow}, transparent 70%)`,
        }}
      />
      <div className="relative">{children}</div>
    </div>
  )
}
